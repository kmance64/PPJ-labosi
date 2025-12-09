#!/usr/bin/env python3
import sys
from collections import defaultdict

# ===========================
# Node class for tree
# ===========================
class Node:
    def __init__(self, name, is_nonterminal=True, token=None, line=None, lexeme=None):
        self.name = name
        self.is_nonterminal = is_nonterminal
        self.children = []
        self.token = token
        self.line = line
        self.lexeme = lexeme
        # semantic attrs:
        self.typ = None      # string like 'int', 'char', 'void', 'func(void->int)', 'array(int)'
        self.lvalue = 0      # 1 if l-value
    def add(self, child):
        self.children.append(child)

# ===========================
# Parse SA output into tree
# ===========================
def parse_tree(lines):
    stack = []
    root = None

    for raw in lines:
        line = raw.rstrip("\n")
        if not line:
            continue

        if line == "$":
            finished = stack.pop()
            if stack:
                stack[-1].add(finished)
            else:
                root = finished
            continue

        if line.startswith("<") and line.endswith(">"):
            nt = Node(name=line, is_nonterminal=True)
            stack.append(nt)
            continue

        parts = line.split(" ", 2)
        if len(parts) == 1:
            tok = parts[0]
            term = Node(tok, is_nonterminal=False, token=tok, lexeme="")
        else:
            tok, lnum = parts[0], parts[1]
            lex = parts[2] if len(parts) > 2 else ""
            term = Node(tok, is_nonterminal=False, token=tok, line=lnum, lexeme=lex)

        if not stack:
            raise ValueError("Terminal without a nonterminal on stack")
        stack[-1].add(term)

    if root is None and stack:
        root = stack[0]

    return root

# ===========================
# Symbol Table (scope stack)
# ===========================
class SymbolTable:
    def __init__(self):
        self.scopes = [dict()]  # each maps name -> {'type': typ, 'node': node, 'kind': 'var'|'func', ...}
        self.functions = {}     # name -> {ret, params:list, node}

    def push(self):
        self.scopes.append(dict())

    def pop(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare_var(self, name, typ, node):
        cur = self.scopes[-1]
        if name in cur:
            return False
        cur[name] = {"type": typ, "node": node, "kind": "var"}
        return True

    def lookup(self, name):
        for s in reversed(self.scopes):
            if name in s:
                return s[name]
        return None

    def declare_func(self, name, ret, params, node):
        if name in self.functions:
            return False
        self.functions[name] = {"ret": ret, "params": params, "node": node}
        return True

    def has_main(self):
        # main must be defined and have type function(void -> int)
        if "main" not in self.functions:
            return False
        f = self.functions["main"]
        # represent ret as string 'int' and params special marker [] or ['void']
        if f["ret"] != "int":
            return False
        if f["params"] != ["void"]:
            return False
        return True

# ===========================
# Utilities: type system helpers
# ===========================
def canonical(t):
    """Return canonical representation (strip const qualifiers)."""
    if not t:
        return None
    return t.replace("const ", "")

def is_numeric(t):
    t = canonical(t)
    return t in ("int", "char")

def can_implicitly_convert(src, dst):
    """Based on ppj rules: char -> int allowed; const removal allowed.
       Arrays / funcs: minimal handling (array -> pointer not fully modelled).
    """
    if src is None or dst is None:
        return False
    s = canonical(src)
    d = canonical(dst)
    if s == d:
        return True
    # char -> int
    if s == "char" and d == "int":
        return True
    # int/char to const-qualified counterpart already handled by canonical
    # allow char/int -> logical (logical is int)
    return False

# ===========================
# Semantic Analyzer
# ===========================
class SemanticAnalyzer:
    def __init__(self, root):
        self.root = root
        self.symtab = SymbolTable()
        self.current_function = None

    def production_str(self, node):
        parts = []
        for c in node.children:
            if c.is_nonterminal:
                parts.append(c.name)
            else:
                # print token as LEXEME(token) format when lexeme present, matching expected output style
                if c.lexeme:
                    parts.append(f"{c.token}({c.line},{c.lexeme})" if c.line else f"{c.token}({c.lexeme})")
                else:
                    parts.append(c.token)
        return f"{node.name} -> {' '.join(parts)}"

    def report_error(self, node, msg):
        # Print the production where error detected and then SEMANTICKA_POGRESKA to stderr
        print(self.production_str(node))
        print(f"SEMANTICKA_POGRESKA: {msg}", file=sys.stderr)
        sys.exit(0)

    # ---------------------------
    # Helpers to collect terminals / flatten
    # ---------------------------
    def collect_terminals(self, node):
        return [c for c in node.children if not c.is_nonterminal]

    def flatten_terminals(self, node):
        out = []
        def dfs(n):
            if not n.is_nonterminal:
                out.append(n)
            for ch in n.children:
                if ch.is_nonterminal:
                    dfs(ch)
                else:
                    out.append(ch)
        dfs(node)
        return out

    # quick checks for production shapes
    def is_var_declaration(self, node):
        terms = self.collect_terminals(node)
        if len(terms) >= 2 and terms[0].token.startswith("KR_") and terms[1].token == "IDN":
            all_lex = " ".join(t.lexeme for t in terms)
            if "(" in all_lex:
                return False
            return True
        return False

    def is_function_definition(self, node):
        terms = self.collect_terminals(node)
        found_kw = None
        found_id = None
        found_lpar = False

        for t in terms:
            if t.token.startswith("KR_") and found_kw is None:
                found_kw = t
            elif t.token == "IDN" and found_kw is not None and found_id is None:
                found_id = t
            elif t.token in ("L_ZAGRADA", "LPAREN"):
                found_lpar = True

        return found_kw and found_id and found_lpar

    def is_assignment(self, node):
        for c in node.children:
            if not c.is_nonterminal and c.token == "OP_PRIDRUZI":
                return True
            if c.is_nonterminal and self.is_assignment(c):
                return True
        return False

    # ---------------------------
    # Expression/type checker
    # This is a recursive evaluator that sets node.typ and node.lvalue
    # It handles common ppjC nonterminals used in expressions.
    # ---------------------------
    def check_expr(self, node):
        # if terminal node (tokens), handle constants and identifiers
        if not node.is_nonterminal:
            # terminals: IDN (identifier), BROJ, ZNAK, NIZ_ZNAKOVA, KR_TRUE/false? but map generic
            if node.token == "IDN":
                info = self.symtab.lookup(node.lexeme)
                if not info:
                    self.report_error(node, f"Uporaba nedefinirane varijable '{node.lexeme}'")
                # if function declaration, then primary expr is function designator
                if info.get("kind") == "var":
                    node.typ = info["type"]
                    # lvalue: only numeric (int/char) variables are l-values (no const handling here)
                    node.lvalue = 1 if is_numeric(node.typ) else 0
                else:
                    # function variable? treat as function type string stored in functions map
                    f = self.symtab.functions.get(node.lexeme)
                    if f:
                        node.typ = f"func({','.join(f['params'])} -> {f['ret']})"
                        node.lvalue = 0
                    else:
                        node.typ = info["type"]
                        node.lvalue = 0
                return node.typ, node.lvalue
            # numeric literal heuristics: if lexeme looks like number -> int
            if node.token in ("BROJ", "BROJ_ZA", "INTEGER", "CONST_INT"):
                node.typ = "int"
                node.lvalue = 0
                return node.typ, node.lvalue
            if node.token in ("ZNak", "ZNAK", "CONST_CHAR"):
                node.typ = "char"
                node.lvalue = 0
                return node.typ, node.lvalue
            # string literal
            if node.token in ("NIZ_ZNAKOVA", "STRING_LITERAL"):
                node.typ = "niz(char)"
                node.lvalue = 0
                return node.typ, node.lvalue
            # for keywords representing types, etc, just return None
            return None, 0

        # nonterminal handling by node.name (heuristic: check suffix/contains)
        name = node.name.lower()

        # Recurse children first (postorder)
        for c in node.children:
            if c.is_nonterminal:
                self.check_expr(c)

        # Primary expression
        if node.name == "<primarni_izraz>":
            # either IDN, literal or parenthesized
            terms = self.collect_terminals(node)
            if len(terms) == 1 and terms[0].token == "IDN":
                # use resolved info from terminal
                node.typ = terms[0].typ if hasattr(terms[0], "typ") else self.check_expr(terms[0])[0]
                node.lvalue = 1 if is_numeric(node.typ) else 0
                return node.typ, node.lvalue
            else:
                # parentheses or constants handled by children; find child nonterminal that set typ
                for ch in node.children:
                    if ch.is_nonterminal and getattr(ch, "typ", None):
                        node.typ = ch.typ
                        node.lvalue = 0
                        return node.typ, node.lvalue
            return node.typ, node.lvalue

        # Postfix: array indexing or function call or empty ()
        if node.name == "<postfiks_izraz>":
            # if the production is: <postfiks_izraz> L_UGL_ZAGRADA <izraz> D_UGL_ZAGRADA
            # or <postfiks_izraz> L_ZAGRADA D_ZAGRADA (call)
            # fallback: copy child's typ
            # find last nonterminal child with typ
            for ch in reversed(node.children):
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    node.typ = ch.typ
                    node.lvalue = 0
                    return node.typ, node.lvalue
            return node.typ, node.lvalue

        # Unary and cast
        if node.name in ("<unarni_izraz>", "<cast_izraz>"):
            # unary plus/minus etc: result numeric
            # if child has type, propagate numeric conversions
            for ch in node.children:
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    # unary operators: if operator is UNAROP with '!' then result int (logic)
                    node.typ = ch.typ
                    node.lvalue = 0
                    return node.typ, node.lvalue
            return node.typ, node.lvalue

        # Multiplicative: *, /, %
        if node.name == "<multiplikativni_izraz>":
            # children: either one multiplikativni + OP + cast or single cast
            # find first child's typ to start
            left = None
            for ch in node.children:
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    if left is None:
                        left = ch.typ
                    else:
                        right = ch.typ
                        # both must be numeric
                        if not is_numeric(left) or not is_numeric(right):
                            self.report_error(node, "Operator matematicki nad ne-numerickim tipom")
                        # result type: if any int -> int, else char promoted to int in expressions.
                        left = "int" if ("int" in (canonical(left), canonical(right)) or canonical(left)=="char" or canonical(right)=="char") else left
            node.typ = left
            node.lvalue = 0
            return node.typ, node.lvalue

        # Additive: +, -
        if node.name == "<aditivni_izraz>":
            left = None
            for ch in node.children:
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    if left is None:
                        left = ch.typ
                    else:
                        right = ch.typ
                        if not is_numeric(left) or not is_numeric(right):
                            self.report_error(node, "Operator + ili - nad ne-numerickim tipom")
                        left = "int"
            node.typ = left
            node.lvalue = 0
            return node.typ, node.lvalue

        # Relational and equality
        if node.name in ("<odnosni_izraz>", "<jednakosni_izraz>"):
            # operators like <, >, <=, >=, ==, != : operands must be numeric or pointers (we handle numeric)
            left = None
            for ch in node.children:
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    if left is None:
                        left = ch.typ
                    else:
                        right = ch.typ
                        if not (is_numeric(left) and is_numeric(right)):
                            self.report_error(node, "Operator odnosa nad nekompatibilnim tipovima")
                        left = "int"  # relational yields int (logical)
            node.typ = "int"
            node.lvalue = 0
            return node.typ, node.lvalue

        # Bitwise and logical
        if node.name in ("<bin_i_izraz>", "<bin_xili_izraz>", "<bin_ili_izraz>", "<log_i_izraz>", "<log_ili_izraz>"):
            # require numeric operands and produce int
            for ch in node.children:
                if ch.is_nonterminal and getattr(ch, "typ", None):
                    if not is_numeric(ch.typ):
                        self.report_error(node, "Operator bitovni/logicki nad ne-numerickim tipom")
            node.typ = "int"
            node.lvalue = 0
            return node.typ, node.lvalue

        # Assignment
        if node.name == "<izraz_pridruzivanja>":
            # find assignment operator if present
            terms = self.flatten_terminals(node)
            if any(t.token == "OP_PRIDRUZI" for t in terms):
                # lhs should be lvalue and types compatible
                # find left-most nonterminal with lvalue
                lhs_node = None
                rhs_node = None
                # heuristic: first IDN before OP_PRIDRUZI is lhs; everything after OP is rhs
                saw_op = False
                lhs_typ = None
                rhs_typ = None
                for t in terms:
                    if not saw_op:
                        if t.token == "OP_PRIDRUZI":
                            saw_op = True
                        else:
                            if t.token == "IDN" and lhs_typ is None:
                                info = self.symtab.lookup(t.lexeme)
                                if not info:
                                    self.report_error(node, f"Uporaba nedefinirane varijable '{t.lexeme}'")
                                lhs_typ = info["type"]
                                # check lvalue: only numeric non-const variables are l-values — simplified
                                # in our symbol table, var implies lvalue for numeric
                    else:
                        if t.token == "IDN" and rhs_typ is None:
                            info = self.symtab.lookup(t.lexeme)
                            if info:
                                rhs_typ = info["type"]
                            else:
                                rhs_typ = "int" if t.lexeme.isdigit() else None
                        elif t.token in ("BROJ", "CONST_INT"):
                            rhs_typ = "int"
                        elif t.token in ("ZNAK", "CONST_CHAR"):
                            rhs_typ = "char"
                # If RHS type wasn't found in flattened terminals, try child types
                # fallback: use type of last child nonterminal
                for ch in reversed(node.children):
                    if ch.is_nonterminal and getattr(ch, "typ", None):
                        rhs_typ = rhs_typ or ch.typ
                        break
                if lhs_typ is None or rhs_typ is None:
                    # conservatively allow if rhs unknown
                    return node.typ, node.lvalue
                if not can_implicitly_convert(rhs_typ, lhs_typ):
                    self.report_error(node, f"Nekompatibilni tipovi u pridruživanj u: {rhs_typ} -> {lhs_typ}")
                node.typ = lhs_typ
                node.lvalue = 0
                return node.typ, node.lvalue
            else:
                # just propagate child
                for ch in node.children:
                    if ch.is_nonterminal and getattr(ch, "typ", None):
                        node.typ = ch.typ
                        node.lvalue = ch.lvalue
                        return node.typ, node.lvalue
                return node.typ, node.lvalue

        # Fallback: propagate child's type if any
        for ch in node.children:
            if ch.is_nonterminal and getattr(ch, "typ", None):
                node.typ = ch.typ
                node.lvalue = ch.lvalue
                return node.typ, node.lvalue

        return node.typ, node.lvalue

    # ---------------------------
    # DFS visit
    # ---------------------------
    def visit(self, node):
        if node.is_nonterminal:

            # Function definition
            if self.is_function_definition(node):
                terms = self.collect_terminals(node)
                # return type is first KR_ token's lexeme (e.g., 'int' from KR_INT)
                ret = None
                name = None
                for t in terms:
                    if t.token.startswith("KR_") and ret is None:
                        # lexeme may be 'int' etc.
                        ret = t.lexeme
                    elif t.token == "IDN" and name is None:
                        name = t.lexeme
                if name:
                    ok = self.symtab.declare_func(name, ret, [], node)
                    if not ok:
                        self.report_error(node, f"Funkcija '{name}' već postoji.")
                    # push scope for function body and set current_function for return checks
                    self.symtab.push()
                    prev_func = self.current_function
                    self.current_function = {"name": name, "ret": ret}
                    # declare parameters would go here (not fully implemented)
                # continue traversal into body

            # Variable declaration
            elif self.is_var_declaration(node):
                terms = self.collect_terminals(node)
                typ = terms[0].lexeme
                name = terms[1].lexeme
                ok = self.symtab.declare_var(name, typ, node)
                if not ok:
                    self.report_error(node, f"Redeklaracija varijable '{name}'")

            # Visit children first (we need types computed)
        # Visit children
        for c in node.children:
            self.visit(c)

        # After children visited, perform expression/type checks on this node
        if node.is_nonterminal:
            # If node is some kind of expression nonterminal, run check_expr to compute types and detect type errors
            if node.name in (
                "<primarni_izraz>", "<postfiks_izraz>", "<unarni_izraz>", "<cast_izraz>",
                "<multiplikativni_izraz>", "<aditivni_izraz>", "<odnosni_izraz>",
                "<jednakosni_izraz>", "<bin_i_izraz>", "<bin_xili_izraz>",
                "<bin_ili_izraz>", "<log_i_izraz>", "<log_ili_izraz>", "<izraz_pridruzivanja>"
            ):
                try:
                    self.check_expr(node)
                except SystemExit:
                    raise
                except Exception as e:
                    # any internal error -> report generic semantic error
                    self.report_error(node, f"Interna greska pri provjeri izraza: {e}")

            # Assignment usage (if not caught by expression checker)
            if self.is_assignment(node):
                # handled in check_expr for <izraz_pridruzivanja>, but keep fallback
                pass

            # Specific check: return statements inside function bodies
            # search for return tokens in terminals of this node
            terms = self.flatten_terminals(node)
            for i, t in enumerate(terms):
                if t.token and t.token.startswith("KR_RETURN"):
                    # The returned expression is likely in a following nonterminal child
                    # find next nonterminal sibling in node.children
                    # For simplicity, look in subtree for first expression nonterminal after this terminal
                    returned_type = None
                    # search subtree nodes after this terminal
                    def find_expr_after(n):
                        # flatten subtree terminals sequence
                        ts = self.flatten_terminals(n)
                        saw = False
                        for tt in ts:
                            if tt is t:
                                saw = True
                                continue
                            if saw:
                                # try get type from parent nonterminal of this terminal
                                # naive: check next sibling nonterminal of the node that contains this terminal
                                pass
                        return None
                    # simpler heuristic: look for nearest expression nonterminal descendant of current node
                    ret_type = None
                    def search_for_expr(n):
                        nonlocal ret_type
                        if ret_type:
                            return
                        if n.name in ("<izraz_pridruzivanja>", "<log_ili_izraz>", "<aditivni_izraz>", "<primarni_izraz>") and getattr(n, "typ", None):
                            ret_type = n.typ
                            return
                        for ch in n.children:
                            if ch.is_nonterminal:
                                search_for_expr(ch)
                                if ret_type:
                                    return
                    search_for_expr(node)
                    if ret_type is None:
                        # void return (no expr)
                        ret_type = "void"
                    # check against current function return type
                    if self.current_function:
                        if not can_implicitly_convert(ret_type, self.current_function["ret"]):
                            self.report_error(node, f"Neispravan tip u return: {ret_type} ne moze u {self.current_function['ret']}")

        # Post-order cleanups: if function def end, pop scope
        if node.is_nonterminal and self.is_function_definition(node):
            # pop scope and restore current function
            self.symtab.pop()
            # nothing complex: functions are recorded earlier
            self.current_function = None

    # ---------------------------
    # Run analyzer
    # ---------------------------
    def run(self):
        self.visit(self.root)

        # After traversal, run final checks per spec: main() existence and function definitions
        if not self.symtab.has_main():
            print("main")
            sys.exit(0)

        # check every declared function has a definition (simple check: declared in functions map)
        # In our simplified model we assume declare_func was called only for defs; skip complex part.
        # If everything ok, exit silently
        return

# ===========================
# Main
# ===========================
def main():
    data = sys.stdin.read().splitlines()
    if not data:
        print("Empty input", file=sys.stderr)
        return
    root = parse_tree(data)
    sem = SemanticAnalyzer(root)
    sem.run()

if __name__ == "__main__":
    main()
