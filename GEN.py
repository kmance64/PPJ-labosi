import sys
from collections import defaultdict, deque
from copy import deepcopy

def parse_san_input():
    data = {
        "nezavrsni": [],
        "zavrsni": [],
        "syn": [],
        "produkcije": defaultdict(list) #svaki novi ključ automatski dobiva praznu listu kao vrijednost
    }

    current_left = None #spremanje nezavrsnog znaka s lijeve strane produkcije

    for line in sys.stdin:
        line = line.rstrip("\n") #brisanje novog reda na kraju linije
        if line.startswith("%V"):
            data["nezavrsni"] = line.split()[1:]
        elif line.startswith("%T"):
            data["zavrsni"] = line.split()[1:]
        elif line.startswith("%Syn"):
            data["syn"] = line.split()[1:]
        elif line.startswith("<") and not line.startswith(" "):   # nova lijeva strana produkcije
            current_left = line
        elif line.startswith(" "):
            right = line.strip().split()
            data["produkcije"][current_left].append(right)
    return data

def prosiri_gramatiku(grammar):
    start_symbol = grammar["nezavrsni"][0]
    new_start = "<S'>"
    grammar["nezavrsni"].insert(0, new_start) #dodajem nezavrsni znak
    grammar["produkcije"][new_start] = [[start_symbol]] #dodajem novu produkciju
    return grammar, new_start

def izgradi_first(grammar):
    first = defaultdict(set)
    epsilon = "$"
    for t in grammar["zavrsni"]:
        first[t].add(t)

    promjena = True #vrti se do god se ne izvrti bez promjene
    while promjena:
        promjena = False
        for A, prods in grammar["produkcije"].items():
            for prod in prods:
                old_size = len(first[A])
                if len(prod) == 0:
                    first[A].add(epsilon)
                else:
                    for symbol in prod:
                        first[A] |= (first[symbol] - {epsilon})
                        if epsilon not in first[symbol]:
                            break
                    else:
                        first[A].add(epsilon)
                if len(first[A]) != old_size:
                    promjena = True
    return first

def zapocinje_niz(beta, lookahead, first):
    result = set()
    for symbol in beta:
        result |= (first[symbol] - {"$"})
        if "$" not in first[symbol]:
            break
    else:
        result |= lookahead
    return result

class Item:
    def __init__(self, left, right, dot_pos, lookahead):
        self.left = left
        self.right = right
        self.dot_pos = dot_pos
        self.lookahead = frozenset(lookahead)

    def next_symbol(self):
        if self.dot_pos < len(self.right):
            return self.right[self.dot_pos]
        return None

    def advance(self):
        return Item(self.left, self.right, self.dot_pos + 1, self.lookahead)

    def __eq__(self, other):
        return (self.left == other.left and
                self.right == other.right and
                self.dot_pos == other.dot_pos and
                self.lookahead == other.lookahead)

    def __hash__(self):
        return hash((self.left, tuple(self.right), self.dot_pos, self.lookahead))

    def __repr__(self):
        right = self.right.copy()
        right.insert(self.dot_pos, "·")
        return f"{self.left} -> {' '.join(right)}, {{{','.join(self.lookahead)}}}"

def closure(items, grammar, first):
    closure_set = set(items)
    added = True
    while added:
        added = False
        new_items = set()
        for item in list(closure_set):
            X = item.next_symbol()
            if X and X in grammar["nezavrsni"]:
                beta = item.right[item.dot_pos + 1:]
                for prod in grammar["produkcije"][X]:
                    la = zapocinje_niz(beta, item.lookahead, first)
                    for a in la:
                        new_item = Item(X, prod, 0, {a})
                        if new_item not in closure_set:
                            new_items.add(new_item)
        if new_items:
            closure_set |= new_items
            added = True
    return closure_set

def goto(items, X, grammar, first):
    moved = {item.advance() for item in items if item.next_symbol() == X}
    return closure(moved, grammar, first)

def izgradi_dka(grammar, first, start_symbol):
    start_item = Item("<S'>", [start_symbol], 0, {"$"})
    I0 = closure({start_item}, grammar, first)

    stanja = [I0]
    prijelazi = dict()
    neoznacena = deque([I0])

    while neoznacena:
        I = neoznacena.popleft()
        for X in grammar["nezavrsni"] + grammar["zavrsni"]:
            J = goto(I, X, grammar, first)
            if not J:
                continue
            # ako je novo stanje, dodaj ga
            if J not in stanja:
                stanja.append(J)
                neoznacena.append(J)
            prijelazi[(stanja.index(I), X)] = stanja.index(J)

    return stanja, prijelazi


# --- 10. ISPIS DKA ---
def ispisi_dka(stanja, prijelazi):
    for i, stanje in enumerate(stanja):
        print(f"\nI{i}:")
        for it in stanje:
            print(" ", it)
        for (src, symbol), dest in prijelazi.items():
            if src == i:
                print(f"  [ {symbol} ] -> I{dest}")


if __name__ == "__main__":
    gramatika = parse_san_input()
    gramatika["produkcije"] = dict(gramatika["produkcije"]) #pretvaram u normalan rječnik
    gramatika, pocetni = prosiri_gramatiku(gramatika)

    print("Proširena gramatika:")
    for A, prods in gramatika["produkcije"].items():
        for p in prods:
            print(f"  {A} -> {' '.join(p)}")

    first = izgradi_first(gramatika)
    print("\nFIRST skupovi:")
    for k, v in first.items():
        print(f"  {k}: {v}")

    # početna stavka
    start_item = Item("<S'>", [gramatika["produkcije"]["<S'>"][0][0]], 0, {"$"})
    I0 = closure({start_item}, gramatika, first)

    print("\nCLOSURE(I0):")
    for it in I0:
        print(" ", it)

    # test goto
    for simbol in gramatika["nezavrsni"] + gramatika["zavrsni"]:
        I1 = goto(I0, simbol, gramatika, first)
        if I1:
            print(f"\nGOTO(I0, {simbol}):")
            for it in I1:
                print(" ", it)

    print("DKA________________________")
    stanja, prijelazi = izgradi_dka(gramatika, first, gramatika["produkcije"]["<S'>"][0][0])
    ispisi_dka(stanja, prijelazi)