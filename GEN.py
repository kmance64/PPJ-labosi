import sys
from collections import defaultdict

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


if __name__ == "__main__":
    gramatika = parse_san_input()
    gramatika["produkcije"] = dict(gramatika["produkcije"]) #pretvaram u normalan rječnik

    print("Nezavršni:", gramatika["nezavrsni"])
    print("Završni:", gramatika["zavrsni"])
    print("Sinkronizacijski:", gramatika["syn"])
    print("Produkcije:", gramatika["produkcije"])