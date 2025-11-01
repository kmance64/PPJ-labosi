import sys

# podaci iz generatora - produkcije, sinkronizacijski_znakovi, tablica akcija i tablica novoStanje

produkcije = []  # produkcije = [("<A>", ["<B>", "c"]), ("<B>", ["$"]), ...]
sinkronizacijski_znakovi = []  # sinkronizacijski_znakovi = ["TOCKAZAREZ", "ZAREZ"]
# akcija = { (0,"IDN"):("p",5), (3,"TOCKAZAREZ"):("r",7), (s,"$"):("prihvati",) }
akcija = {}
novoStanje = {}  # novoStanje = { (0,"<A>"):1, (4,"<B>"):9, ... }

EPS = "$"


class Cvor:
    # cvor generativnog stabla
    def __init__(self, oznaka, djeca=None, ime_leksicke_jedinke=None, linija=None, leksicka_jedinka=None):
        self.oznaka = oznaka       # <nezavrsni znak> ili zavrsni znak/epsilon
        self.djeca = djeca or []   # lista cvorova
        self.ime_leksicke_jedinke = ime_leksicke_jedinke
        self.linija = linija
        self.leksicka_jedinka = leksicka_jedinka


def ispisi_stablo(korijen):
    def rekurzija(n, dubina):
        if n.oznaka.startswith("<"):
            print("  " * dubina + n.oznaka)
        elif n.ime_leksicke_jedinke:
            print("  " * dubina +
                  f"{n.ime_leksicke_jedinke} {n.linija} {n.leksicka_jedinka}")
        else:
            print("  " * dubina + n.oznaka)
        for d in n.djeca:
            rekurzija(d, dubina + 1)
    rekurzija(korijen, 0)


def zapocinje(znak, znakom):
    # algoritam iz udzbenika, vraca true ili false

    # skup svih znakova
    znakovi = set()
    for A, alfa in produkcije:
        znakovi.add(A)
        for s in alfa:
            if s != EPS:
                znakovi.add(s)
    znakovi = sorted(znakovi)

    idx = {z: i for i, z in enumerate(znakovi)}
    n = len(znakovi)

    # nezavrsni znakovi koji imaju epsilon produkciju
    ide_u_eps = set()
    promjena = True
    while promjena:
        promjena = False
        for A, alfa in produkcije:
            if A in ide_u_eps:
                continue
            if alfa == [EPS] or len(alfa) == 0:
                ide_u_eps.add(A)
                promjena = True
            else:
                ok = True
                for s in alfa:
                    if s == EPS:  # ignoriraj izriciti EPS u mijesanim desnim stranama
                        continue
                    if s not in ide_u_eps:
                        ok = False
                        break
                if ok:
                    ide_u_eps.add(A)
                    promjena = True

    # popunjavanje tablice zapocinjeIzravnoZnakom
    zapocinjeIzravnoZnakom = [[False]*n for _ in range(n)]
    for A, alfa in produkcije:
        if not alfa or alfa == [EPS]:
            continue
        j = 0
        while j < len(alfa):
            Xj = alfa[j]
            if Xj == EPS:
                j += 1
                continue
            # dodaj brid A -> Xj
            if A in idx and Xj in idx:
                zapocinjeIzravnoZnakom[idx[A]][idx[Xj]] = True
            # stani cim Xj ne moze eps
            if Xj not in ide_u_eps:
                break
            j += 1

    # refleksivno i tranzitivno okruzenje
    R = [row[:] for row in zapocinjeIzravnoZnakom]
    for i in range(n):
        R[i][i] = True
    for k in range(n):
        for i in range(n):
            if not R[i][k]:
                continue
            row_i = R[i]
            row_k = R[k]
            for j in range(n):
                if row_k[j] and not row_i[j]:
                    row_i[j] = True

    if znak not in idx or znakom not in idx:
        return False
    return R[idx[znak]][idx[znakom]]


def ocekivani_za_stanje(stanje):
    # ocekivani znakovi koji ne bi izazvali pogresku
    return sorted({t for (s, t) in akcija.keys() if s == stanje})


def main():
    ulaz = []
    for line in sys.stdin.read().splitlines():
        red = line.split(" ", 2)
        ime_leksicke_jedinke, linija, leksicka_jedinka = red[0], int(
            red[1]), red[2]
        ulaz.append((ime_leksicke_jedinke, linija, leksicka_jedinka))

    stog = [0]
    cvorovi = []

    i = 0
    while True:
        s = stog[-1]
        ime_leksicke_jedinke, linija, leksicka_jedinka = ulaz[i]
        akc = akcija.get((s, ime_leksicke_jedinke))

        if akc is None:
            # oporavak od pogreske - ispis na stderr, preskakanje do prvog sinkronizacijskog znaka
            ocekivano = ocekivani_za_stanje(s)
            print(
                f"Sintaksna pogreska u retku {linija}: ocekivalo se {', '.join(ocekivano)}; a procitano je {ime_leksicke_jedinke} ({leksicka_jedinka})", file=sys.stderr)

            while i < len(ulaz) and ulaz[i][0] not in sinkronizacijski_znakovi:
                i += 1
            if i >= len(ulaz):
                return

            # micanje stanja sa stoga dok ne dode do nekog stanja s u kojem je definirana akcija sa sinkronizacijskim znakom
            sinkronizacijski_znak = ulaz[i][0]
            while stog and akcija.get((stog[-1], sinkronizacijski_znak)) is None:
                stog.pop()
                if cvorovi:
                    cvorovi.pop()
                if not stog:
                    return
            continue

        vrsta_akcije = akc[0]
        if vrsta_akcije == "p":
            s2 = akc[1]
            cvorovi.append(
                Cvor(ime_leksicke_jedinke, djeca=[], ime_leksicke_jedinke=ime_leksicke_jedinke, linija=linija, leksicka_jedinka=leksicka_jedinka))
            stog.append(s2)
            i += 1
        elif vrsta_akcije == "r":
            br_produkcija = akc[1]
            A, alfa = produkcije[br_produkcija]
            if alfa == [EPS]:
                k = 0
            else:
                k = len(alfa)

            if k > 0:
                # skini k stvari sa stoga
                for a in range(k):
                    stog.pop()
                djeca = cvorovi[-k:]
                del cvorovi[-k:]
            else:
                # epsilon list
                djeca = [Cvor(EPS, djeca=[], ime_leksicke_jedinke=None)]

            novi = Cvor(A, djeca=list(djeca))
            cvorovi.append(novi)

            s3 = stog[-1]
            sljedece_stanje = novoStanje.get((s3, A))
            stog.append(sljedece_stanje)
        elif vrsta_akcije == "prihvati":
            ispisi_stablo(cvorovi[-1])
            return


if __name__ == "__main__":
    main()
