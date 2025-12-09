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
        self.scopes = [dict()]
        self.functions = {}

    def push(self):
        self.scopes.append(dict())

    def pop(self):
        if len(self.scopes) > 1:
            self.scopes.pop()

    def declare_var(self, name, typ, node):
        cur = self.scopes[-1]
        if name in cur:
            return False
        cur[name] = {"type": typ, "node": node}
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
        return "main" in self.functions

# ===========================
# Semantic Analyzer
# ===========================
class SemanticAnalyzer:
    def __init__(self, root):
        self.root = root
        self.symtab = SymbolTable()

    def production_str(self, node):
        parts = []
        for c in node.children:
            if c.is_nonterminal:
                parts.append(c.name)
            else:
                parts.append(c.lexeme if c.lexeme else c.token)
        return f"{node.name} -> {' '.join(parts)}"

    def report_error(self, node, msg):
        print(self.production_str(node))
        print(f"SEMANTICKA_POGRESKA: {msg}", file=sys.stderr)
        sys.exit(0)

    # ---------------------------
    # Helper recognizers
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
    # DFS visit
    # ---------------------------
    def visit(self, node):
        if node.is_nonterminal:

            # Function definition
            if self.is_function_definition(node):
                terms = self.collect_terminals(node)
                ret = terms[0].lexeme
                name = None
                for t in terms:
                    if t.token == "IDN":
                        name = t.lexeme
                        break
                if name:
                    ok = self.symtab.declare_func(name, ret, [], node)
                    if not ok:
                        self.report_error(node, f"Funkcija '{name}' već postoji.")
                self.symtab.push()

            # Variable declaration
            elif self.is_var_declaration(node):
                terms = self.collect_terminals(node)
                typ = terms[0].lexeme
                name = terms[1].lexeme
                ok = self.symtab.declare_var(name, typ, node)
                if not ok:
                    self.report_error(node, f"Redeklaracija varijable '{name}'")

            # Assignment
            elif self.is_assignment(node):
                terms = self.flatten_terminals(node)
                lhs = None
                for t in terms:
                    if t.token == "IDN":
                        lhs = t.lexeme
                        break
                    if t.token == "OP_PRIDRUZI":
                        break
                if lhs:
                    if not self.symtab.lookup(lhs):
                        self.report_error(node, f"Uporaba nedefinirane varijable '{lhs}'")

            # New block = new scope
            if node.name in ("<SLOZENA_NAREDBA>", "<BLOCK>"):
                self.symtab.push()

        # Visit children
        for c in node.children:
            self.visit(c)

        # Post-order
        if node.is_nonterminal:
            if self.is_function_definition(node):
                self.symtab.pop()
            if node.name in ("<SLOZENA_NAREDBA>", "<BLOCK>"):
                self.symtab.pop()

    # ---------------------------
    # Run analyzer
    # ---------------------------
    def run(self):
        self.visit(self.root)

        # Provjera za main()
        if not self.symtab.has_main():
            print("main")
            sys.exit(0)

        # Ako je sve ok, ne ispisujemo ništa
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
