import sys
from collections import defaultdict, deque


def parsiraj_san():
    podaci = {
        "nezavrsni": [],
        "zavrsni": [],
        "syn": [],
        # svaki novi kljuc automatski dobiva praznu listu kao vrijednost
        "produkcije": defaultdict(list)
    }

    lijevi_znak = None  # spremanje nezavrsnog znaka s lijeve strane produkcije

    for line in sys.stdin:
        line = line.rstrip("\n")  # brisanje novog reda na kraju linije
        if line.startswith("%V"):
            podaci["nezavrsni"] = line.split()[1:]
        elif line.startswith("%T"):
            podaci["zavrsni"] = line.split()[1:]
        elif line.startswith("%Syn"):
            podaci["syn"] = line.split()[1:]
        # nova lijeva strana produkcije
        elif line.startswith("<") and not line.startswith(" "):
            lijevi_znak = line
        elif line.startswith(" "):
            desno = line.strip().split()
            if desno == ["$"]:
                desno = []
            podaci["produkcije"][lijevi_znak].append(desno)
    return podaci


def prosiri_gramatiku(gramatika):
    # dodavanje novog pocetnog znaka s'
    pocetni_znak = gramatika["nezavrsni"][0]
    novi_pocetni = "<S'>"
    gramatika["nezavrsni"].insert(0, novi_pocetni)  # dodajem nezavrsni znak
    gramatika["produkcije"][novi_pocetni] = [
        [pocetni_znak]]  # dodajem novu produkciju
    return gramatika, novi_pocetni


def skupovi_zapocinje(gramatika):
    # skup zapocinje za sve zavrsne i nezavrsne znakove
    zapocinje = defaultdict(set)
    epsilon = "$"
    for t in gramatika["zavrsni"]:
        zapocinje[t].add(t)

    promjena = True  # vrti se do god se ne izvrti bez promjene
    while promjena:
        promjena = False
        for A, produkcije in gramatika["produkcije"].items():
            for prod in produkcije:
                size_prije = len(zapocinje[A])
                if len(prod) == 0:
                    zapocinje[A].add(epsilon)
                else:
                    for znak in prod:
                        zapocinje[A] |= (zapocinje[znak] - {epsilon})
                        if epsilon not in zapocinje[znak]:
                            break
                    else:
                        zapocinje[A].add(epsilon)
                if len(zapocinje[A]) != size_prije:
                    promjena = True
    return zapocinje


class LR1_stavka:
    # lr(1) produkcije s tockom
    def __init__(self, lijevo, desno, pozicija_tocke, iza_produkcije):
        self.lijevo = lijevo
        self.desno = desno
        self.pozicija_tocke = pozicija_tocke
        # znak koji je iza produkcije, da znamo kad se moze napraviti redukcija
        self.iza_produkcije = frozenset(iza_produkcije)

    # simbol nakon tocke ili None
    def sljedeci_znak(self):
        if self.pozicija_tocke < len(self.desno):
            return self.desno[self.pozicija_tocke]
        return None

    # stavi tocku na sljedece mjesto
    def dalje(self):
        return LR1_stavka(self.lijevo, self.desno, self.pozicija_tocke + 1, self.iza_produkcije)

    def __eq__(self, other):
        return (
            isinstance(other, LR1_stavka) and
            self.lijevo == other.lijevo and
            self.desno == other.desno and
            self.pozicija_tocke == other.pozicija_tocke and
            self.iza_produkcije == other.iza_produkcije
        )

    def __hash__(self):
        return hash((self.lijevo, tuple(self.desno), self.pozicija_tocke, self.iza_produkcije))


def grupa(lr_stavke, gramatika, zapocinje):
    # grupira sve stavke koje mogu nastati iz nezavrsnih znakova poslije tocke
    rez = set(lr_stavke)
    dodano = True
    while dodano:
        dodano = False
        nove = set()
        for stavka in list(rez):
            X = stavka.sljedeci_znak()
            if X and X in gramatika["nezavrsni"]:
                beta = stavka.desno[stavka.pozicija_tocke + 1:]

                # skup zapocinje od niza beta, bez epsilona
                la = set()
                for znak in beta:
                    la |= (zapocinje[znak] - {"$"})
                    if "$" not in zapocinje[znak]:
                        break
                else:
                    # ako beta ide u epsilon
                    la |= stavka.iza_produkcije

                for desno in gramatika["produkcije"][X]:
                    for a in la:
                        nova = LR1_stavka(X, desno, 0, {a})
                        if nova not in rez:
                            nove.add(nova)
        if nove:
            rez |= nove
            dodano = True
    return rez


def sljedeca_grupa(lr_stavke, X, gramatika, zapocinje):
    pomak = {prod.dalje()
             for prod in lr_stavke if prod.sljedeci_znak() == X}
    return grupa(pomak, gramatika, zapocinje)


def izgradi_dka(gramatika, zapocinje, pocetni_znak):
    pocetna_stavka = LR1_stavka("<S'>", [pocetni_znak], 0, {"$"})
    I0 = grupa({pocetna_stavka}, gramatika, zapocinje)

    stanja = [I0]
    prijelazi = dict()
    neoznacena = deque([I0])

    while neoznacena:
        I = neoznacena.popleft()
        for X in gramatika["nezavrsni"] + gramatika["zavrsni"]:
            J = sljedeca_grupa(I, X, gramatika, zapocinje)
            if not J:
                continue
            # ako je novo stanje, dodaj ga
            if J not in stanja:
                stanja.append(J)
                neoznacena.append(J)
            prijelazi[(stanja.index(I), X)] = stanja.index(J)

    return stanja, prijelazi


def numeriraj_produkcije(gramatika):
    # dodjeljuje brojeve produkcijama da se kasnije moze napraviti tablica akcija i poreda ih po redu za rjwesavanje reduciraj/reduciraj proturjecja
    redoslijed = []
    br_produkcije = {}
    # ide po trenutno redoslijedu produkcija gramatike
    for lijevo in gramatika["produkcije"]:
        for desno in gramatika["produkcije"][lijevo]:
            br = len(redoslijed)
            redoslijed.append((lijevo, desno))
            br_produkcije[(lijevo, tuple(desno))] = br
    return redoslijed, br_produkcije


def izgradi_tablice(gramatika, zapocinje, stanja, prijelazi):
    # tablice akcija i novoStanje za lr1 parser
    zavrsni = set(gramatika["zavrsni"])
    nezavrsni = set(gramatika["nezavrsni"])

    redoslijed, br_produkcije = numeriraj_produkcije(gramatika)

    akcija = {}
    novoStanje = {}

    # akcije iz dka
    for (src, X), dest in prijelazi.items():
        if X in zavrsni:
            akcija[(src, X)] = ("p", dest)
        elif X in nezavrsni:
            novoStanje[(src, X)] = dest

    # akcije prihvati ili odbaci za produkcije s tockom na kraju
    for i, stanje in enumerate(stanja):
        for it in stanje:
            if it.pozicija_tocke != len(it.desno):
                continue

            if it.lijevo == "<S'>" and "$" in it.iza_produkcije:
                akcija[(i, "$")] = ("prihvati",)
                continue

            k = br_produkcije[(it.lijevo, tuple(it.desno))]
            for a in it.iza_produkcije:
                akc = akcija.get((i, a))
                if akc is None:
                    akcija[(i, a)] = ("r", k)
                else:
                    if akc[0] == "r":
                        # reduciraj/reduciraj proturjecje, izaberi akciju koja je prije definirana
                        akcija[(i, a)] = ("r", min(akc[1], k))

    return redoslijed, akcija, novoStanje


def generiraj_sa(gramatika, produkcije, akcija, novoStanje, path="analizator/SA.py"):
    # ubacuje tablice u predlozak i generira SA.py
    sinkron = gramatika.get("syn", [])

    podaci = f"""
produkcije = {repr(produkcije)}
sinkronizacijski_znakovi = {repr(sinkron)}
akcija = {repr(akcija)}
novoStanje = {repr(novoStanje)}
"""

    with open("analizator/predlozak.py", "r", encoding="utf-8") as f:
        predlozak = f.read()

    nakon = "import sys"
    parts = predlozak.split(nakon, 1)
    rez = parts[0] + nakon + "\n\n" + podaci + parts[1]

    with open(path, "w", encoding="utf-8") as f:
        f.write(rez)


if __name__ == "__main__":
    gramatika = parsiraj_san()
    # pretvaram u normalan rjecnik
    gramatika["produkcije"] = dict(gramatika["produkcije"])
    gramatika, pocetni = prosiri_gramatiku(gramatika)

    zapocinje = skupovi_zapocinje(gramatika)

    stanja, prijelazi = izgradi_dka(
        gramatika, zapocinje, gramatika["produkcije"]["<S'>"][0][0])

    produkcije_po_redu, akcija, novoStanje = izgradi_tablice(
        gramatika, zapocinje, stanja, prijelazi)

    generiraj_sa(gramatika, produkcije_po_redu, akcija,
                 novoStanje, path="analizator/SA.py")
