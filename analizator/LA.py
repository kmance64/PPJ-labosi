import sys

# Podaci ugrađeni iz generatora ispod ↓

# ================== Ugrađeni podaci (generirano iz GLA.py) ==================
stanja = ['S_a']
pocetno_stanje = 'S_a'
pravila = [{'stanje': 'S_a', 'regex': '\\n', 'akcije': ['-', 'NOVI_REDAK'], 'uniformni_znak': '-', 'dodatne_akcije': ['NOVI_REDAK'], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 0}, {'stanje': 'S_a', 'regex': '\\_', 'akcije': ['-'], 'uniformni_znak': '-', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 1}, {'stanje': 'S_a', 'regex': 'x(a|b|c)*', 'akcije': ['A'], 'uniformni_znak': 'A', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 2}, {'stanje': 'S_a', 'regex': 'o(ab|bc|ca)*', 'akcije': ['B'], 'uniformni_znak': 'B', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 3}, {'stanje': 'S_a', 'regex': 'ab(abc|$)ccc', 'akcije': ['C'], 'uniformni_znak': 'C', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 4}, {'stanje': 'S_a', 'regex': 'ya((xx|yy)(dd|ad)|$)z', 'akcije': ['D'], 'uniformni_znak': 'D', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 5}]
pravila_po_stanju = {'S_a': [0, 1, 2, 3, 4, 5]}
automati = [{'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}]
prijelazi = {0: {0: {'$': [2]}, 1: {}, 2: {'\n': [3]}, 3: {'$': [1]}}, 1: {0: {'$': [2]}, 1: {}, 2: {' ': [3]}, 3: {'$': [1]}}, 2: {0: {'$': [2]}, 1: {}, 2: {'x': [3]}, 3: {'$': [20]}, 4: {'$': [6, 10]}, 5: {'$': [21, 4]}, 6: {'$': [8]}, 7: {'$': [5]}, 8: {'a': [9]}, 9: {'$': [7]}, 10: {'$': [12, 16]}, 11: {'$': [5]}, 12: {'$': [14]}, 13: {'$': [11]}, 14: {'b': [15]}, 15: {'$': [13]}, 16: {'$': [18]}, 17: {'$': [11]}, 18: {'c': [19]}, 19: {'$': [17]}, 20: {'$': [4, 21]}, 21: {'$': [1]}}, 3: {0: {'$': [2]}, 1: {}, 2: {'o': [3]}, 3: {'$': [26]}, 4: {'$': [6, 12]}, 5: {'$': [27, 4]}, 6: {'$': [8]}, 7: {'$': [5]}, 8: {'a': [9]}, 9: {'$': [10]}, 10: {'b': [11]}, 11: {'$': [7]}, 12: {'$': [14, 20]}, 13: {'$': [5]}, 14: {'$': [16]}, 15: {'$': [13]}, 16: {'b': [17]}, 17: {'$': [18]}, 18: {'c': [19]}, 19: {'$': [15]}, 20: {'$': [22]}, 21: {'$': [13]}, 22: {'c': [23]}, 23: {'$': [24]}, 24: {'a': [25]}, 25: {'$': [21]}, 26: {'$': [4, 27]}, 27: {'$': [1]}}, 4: {0: {'$': [2]}, 1: {}, 2: {'a': [3]}, 3: {'$': [4]}, 4: {'b': [5]}, 5: {'$': [6]}, 6: {'$': [8, 16]}, 7: {'$': [20]}, 8: {'$': [10]}, 9: {'$': [7]}, 10: {'a': [11]}, 11: {'$': [12]}, 12: {'b': [13]}, 13: {'$': [14]}, 14: {'c': [15]}, 15: {'$': [9]}, 16: {'$': [18]}, 17: {'$': [7]}, 18: {'$': [19]}, 19: {'$': [17]}, 20: {'c': [21]}, 21: {'$': [22]}, 22: {'c': [23]}, 23: {'$': [24]}, 24: {'c': [25]}, 25: {'$': [1]}}, 5: {0: {'$': [2]}, 1: {}, 2: {'y': [3]}, 3: {'$': [4]}, 4: {'a': [5]}, 5: {'$': [6]}, 6: {'$': [8, 38]}, 7: {'$': [42]}, 8: {'$': [10]}, 9: {'$': [7]}, 10: {'$': [12, 18]}, 11: {'$': [24]}, 12: {'$': [14]}, 13: {'$': [11]}, 14: {'x': [15]}, 15: {'$': [16]}, 16: {'x': [17]}, 17: {'$': [13]}, 18: {'$': [20]}, 19: {'$': [11]}, 20: {'y': [21]}, 21: {'$': [22]}, 22: {'y': [23]}, 23: {'$': [19]}, 24: {'$': [26, 32]}, 25: {'$': [9]}, 26: {'$': [28]}, 27: {'$': [25]}, 28: {'d': [29]}, 29: {'$': [30]}, 30: {'d': [31]}, 31: {'$': [27]}, 32: {'$': [34]}, 33: {'$': [25]}, 34: {'a': [35]}, 35: {'$': [36]}, 36: {'d': [37]}, 37: {'$': [33]}, 38: {'$': [40]}, 39: {'$': [7]}, 40: {'$': [41]}, 41: {'$': [39]}, 42: {'z': [43]}, 43: {'$': [1]}}}
# ===========================================================================


# (GLA.py će ovdje umetnuti stvarne podatke: stanja, pravila, automati, prijelaze, ...)


def prijelaz(br_pravilo, stanje, znak):
    """Vrati sva stanja u koja se može doći iz 'stanje' čitajući 'znak'."""
    return set(prijelazi.get(br_pravilo, {}).get(stanje, {}).get(znak, []))


def epsilon_okruzenje(br_pravilo, trenutna_stanja):
    """Algoritam za pronalazak epsilon-okruženja (ε-closure)."""
    Y = set(trenutna_stanja)
    stog = list(trenutna_stanja)

    while stog:
        stanje = stog.pop()
        for st in prijelaz(br_pravilo, stanje, '$'):
            if st not in Y:
                Y.add(st)
                stog.append(st)
    return Y


def pomak(br_pravilo, stanja, znak):
    """Pomak iz svih aktivnih stanja u sljedeća stanja čitanjem znaka."""
    if znak == '$':
        return set()

    rez = set()
    for s in stanja:
        rez |= prijelaz(br_pravilo, s, znak)
    return rez


def akcija(br_pravilo):
    """Vrati (vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje)."""
    pravilo = pravila[br_pravilo]
    vracanje = pravilo.get('vracanje', 0) or 0

    if pravilo.get('uniformni_znak') == '-':
        ime_leksicke_jedinke = None
    else:
        ime_leksicke_jedinke = pravilo.get('uniformni_znak')

    novi_red = 'NOVI_REDAK' in (pravilo.get('dodatne_akcije') or [])
    sljedece_stanje = pravilo.get('sljedece_stanje', None)

    return vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje


def prihvatljivo(br_pravilo, stanja):
    """Provjeri je li neko stanje prihvatljivo u automatima."""
    br_automata = pravila[br_pravilo]['br_automat']
    prihvati = automati[br_automata]['prihvatljivo']
    return prihvati in stanja


def main():
    kod = sys.stdin.read()
    kod = kod.replace('\r\n', '\n').replace('\r', '\n')
    if kod.endswith('\n'):
        kod = kod[:-1]

    n = len(kod)
    trenutno_stanje = pocetno_stanje
    redak = 1

    redoslijed_pravila_za_stanje = {}
    for stanje, lista_pravila in pravila_po_stanju.items():
        for k, br_pravila in enumerate(lista_pravila):
            redoslijed_pravila_za_stanje[br_pravila] = k

    pocetak = 0
    while pocetak < n:
        linija = redak
        aktivna_stanja = {}

        # aktivna pravila za trenutno stanje
        for br_pravilo in pravila_po_stanju[trenutno_stanje]:
            br_automat = pravila[br_pravilo]['br_automat']
            poc_stanje = automati[br_automat]['pocetno']
            aktivna_stanja[br_pravilo] = epsilon_okruzenje(br_pravilo, {poc_stanje})

        zavrsetak = pocetak
        zadnje_prihvaceno = None

        # prolazak kroz znakove
        while zavrsetak < n and aktivna_stanja:
            znak = kod[zavrsetak]
            sljedeca_stanja = {}

            for br_pravilo, stanja in aktivna_stanja.items():
                stanja2 = epsilon_okruzenje(br_pravilo, pomak(br_pravilo, stanja, znak))
                if stanja2:
                    sljedeca_stanja[br_pravilo] = stanja2
                    if prihvatljivo(br_pravilo, stanja2):
                        redoslijed = redoslijed_pravila_za_stanje[br_pravilo]
                        kandidat = (zavrsetak + 1, -redoslijed, br_pravilo)
                        if (zadnje_prihvaceno is None) or (kandidat > zadnje_prihvaceno):
                            zadnje_prihvaceno = kandidat

            if not sljedeca_stanja:
                break

            aktivna_stanja = sljedeca_stanja
            zavrsetak += 1

        # ako ništa nije prihvaćeno
        if zadnje_prihvaceno is None:
            krivo = kod[pocetak]
            print(f"Leksička pogreška u retku {redak}: {repr(krivo)} (ord={ord(krivo)})", file=sys.stderr)
            if krivo == '\n':
                redak += 1
            pocetak += 1
            continue

        # primjena pravila
        kraj, po_redu, koristeno_pravilo = zadnje_prihvaceno
        vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje = akcija(koristeno_pravilo)

        if vracanje:
            kraj = min(pocetak + vracanje, n)
            if kraj < pocetak:
                kraj = pocetak

        leksicka_jedinka = kod[pocetak:kraj]

        if ime_leksicke_jedinke is not None:
            print(f"{ime_leksicke_jedinke} {linija} {leksicka_jedinka}")

        if novi_red:
            dodaj = leksicka_jedinka.count('\n')
            if dodaj == 0:
                dodaj = 1
            redak += dodaj

        if sljedece_stanje:
            trenutno_stanje = sljedece_stanje

        pocetak = kraj


if __name__ == "__main__":
    main()
