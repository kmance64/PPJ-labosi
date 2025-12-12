#!/usr/bin/env python3
import sys
import re

# Node klasa: koristi se i za nonterm i za terminale
class Node:
    def __init__(self, name, is_nonterminal=True, token=None, line=None, lexeme=None):
        self.name = name
        self.is_nonterminal = is_nonterminal
        self.children = []
        self.parent = None
        self.token = token
        self.line = line
        self.lexeme = lexeme
    def add(self, child):
        child.parent = self
        self.children.append(child)

# Pomocna: broj vodecih razmaka
def leading_spaces(s):
    return len(s) - len(s.lstrip(' '))

# Parsiranje indentiranog SA izlaza
def parse_indented(lines):
    root = None
    stack = []  # parovi (indent, node)

    for raw in lines:
        line = raw.rstrip("\n")
        if line == "":
            continue

        indent = leading_spaces(line)
        text = line.lstrip(' ')

        # Prepoznaj neneterminal: linija počinje sa '<' i završava sa '>'
        if text.startswith("<") and text.endswith(">"):
            node = Node(name=text, is_nonterminal=True)
        else:
            # terminalna linija: TOKEN [line] [lexeme...]
            parts = text.split(" ", 2)
            if len(parts) == 1:
                tok = parts[0]
                node = Node(name=tok, is_nonterminal=False, token=tok, line=None, lexeme=None)
            elif len(parts) == 2:
                tok, lnum = parts
                node = Node(name=tok, is_nonterminal=False, token=tok, line=lnum, lexeme=None)
            else:
                tok, lnum, lex = parts
                node = Node(name=tok, is_nonterminal=False, token=tok, line=lnum, lexeme=lex)

        # Ako nema root, postavi prvi neneterminal s najmanjim indentom kao root
        if not stack:
            stack.append((indent, node))
            root = node
            continue

        # Ako nova linija ima već indent od vrha stoga -> dijete vrha
        # Ako ima manji ili jednak indent -> pop dok ne nađeš roditelja s manjim indentom
        while stack and indent <= stack[-1][0]:
            stack.pop()

        if stack:
            parent_node = stack[-1][1]
            parent_node.add(node)
        else:
            # nema roditelja (nova top-level grana)
            # tretiraj kao novi root sibling — ali držimo jedinstveni root: umjesto toga,
            # stvorimo virtualni root ako je potrebno
            # ovo rješenje: ako postoje više top-level neneterminala, stvorit ćemo virtualni root
            if root is None:
                root = node
            else:
                # stvori virtualni root ako već nije
                if root.name != "<VIRTUAL_ROOT>":
                    virt = Node("<VIRTUAL_ROOT>", is_nonterminal=True)
                    virt.add(root)
                    root = virt
                root.add(node)

        stack.append((indent, node))

    return root

# Uljepsani ispis - isti kao ulaz
# def print_tree(node, indent=0):
#     sp = " " * indent
#     if node.is_nonterminal:
#         print(f"{sp}{node.name}")
#         for ch in node.children:
#             print_tree(ch, indent + 1)
#     else:
#         # format terminala: token line lexeme (ako postoje)
#         if node.line is not None and node.lexeme is not None:
#             print(f"{sp}{node.token} {node.line} {node.lexeme}")
#         elif node.line is not None:
#             print(f"{sp}{node.token} {node.line}")
#         else:
#             print(f"{sp}{node.token}")

# Ispis stabla u preglednom obliku
def print_tree(node, depth=0):
    indent = "  " * depth

    print(f"{indent}Node(")
    print(f"{indent}  name={node.name!r},")
    print(f"{indent}  is_nonterminal={node.is_nonterminal},")
    print(f"{indent}  token={node.token!r}, line={node.line!r}, lexeme={node.lexeme!r},")

    print(f"{indent}  children=[")
    for child in node.children:
        print_tree(child, depth + 2)
    print(f"{indent}  ]")
    print(f"{indent})")


def main():
    data = sys.stdin.read().splitlines()
    if not data:
        print("Nema ulaznih podataka.", file=sys.stderr)
        return
    root = parse_indented(data)
    print_tree(root)

if __name__ == "__main__":
    main()
