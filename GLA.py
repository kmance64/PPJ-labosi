import re  # regularni izrazi
import sys

epsilon = '<<EPS>>'  # posebni znak za epsilon da se ne mijesa sa obicnim znakom dolara


def parsiranje():
    datoteka = [l.strip() for l in sys.stdin.readlines() if l.strip() != ""]
    regularne_definicije = {}
    stanja = []
    uniformni_znakovi = []
    pravila = []

    faza = 1
    i = 0
    while i < len(datoteka):
        linija = datoteka[i]

        # faza 1 - regularne definicije
        if faza == 1:
            if linija.startswith("%X"):  # ako linija pocinje s %X vraca true
                faza = 2
                continue
            # ([^}]+) hvata sve znakove jedno ili vise puta; \s+ razmaci,tabovi,novi red; (.*) ostatak linije
            m = re.match(r"\{([^}]+)\}\s+(.*)", linija)
            ime = m.group(1).strip()
            izraz = m.group(2).strip()
            regularne_definicije[ime] = izraz

        # faza 2 - stanja i uniformni znakovi
        elif faza == 2:
            if linija.startswith("%X"):
                stanja = linija.split()[1:]  # split, uzmi sve nakon prvog
            elif linija.startswith("%L"):
                uniformni_znakovi = linija.split()[1:]
                faza = 3

        # faza 3 - pravila
        elif faza == 3:
            if linija.startswith("<"):
                # sva stanja pocinju sa <S_stanje>
                m = re.match(r"<([^>]+)>(.*)", linija)
                stanje = m.group(1).strip()
                regex = m.group(2).strip()
                i += 2
                akcije = []  # unutar {} zagrada,  svka u novom redu
                while i < len(datoteka) and datoteka[i] != "}":
                    akcije.append(datoteka[i].strip())
                    i += 1
                pravila.append({
                    "stanje": stanje,
                    "regex": regex,
                    "akcije": akcije
                })
        i += 1
    return regularne_definicije, stanja, uniformni_znakovi, pravila


def prosiri_definicije(definicije):
    promijenjeno = True  # kada se nista u definicija ne promijeni znaci da je sve promijenjeno
    while promijenjeno:
        promijenjeno = False
        # list radi kopiju definicija - inace dolazi do greske jer mijenjam rjecnik kroz koji iteriram
        for ime, izraz in list(definicije.items()):
            novi_izraz = izraz
            # vraca listu svih matcheva
            matches = re.findall(r"\{([^}]+)\}", izraz)
            for m in matches:
                if m in definicije:
                    # replace i dodajem zagrade oko izraza da se ne promijeni redoslijed
                    novi_izraz = novi_izraz.replace(
                        f"{{{m}}}", f"({definicije[m]})")
                    # oznacim da se nesto promijenilo tako da opet prolazim kroz sve definicije
                    promijenjeno = True
                definicije[ime] = novi_izraz
    return definicije


def prosiri_pravila(pravila, definicije):  # prosljedujem prosirene definicije
    for pravilo in pravila:
        # pravilo izgleda ovako: {'stanje': 'S_a', 'regex': '\\n', 'akcije': ['-', 'NOVI_REDAK']}
        regex = pravilo["regex"]
        matches = re.findall(r"\{([^}]+)\}", regex)
        for m in matches:
            if m in definicije:
                regex = regex.replace(f"{{{m}}}", f"({definicije[m]})")
        pravilo["regex"] = regex
    return pravila


def formatiraj_pravila(pravila):
    # uniformni_znak je str ili '-', dodatne_akcije su list[str], sljedece_stanje je str ili None, vracanje je int
    for p in pravila:
        akc = [x.strip() for x in p.get("akcije", []) if x.strip()]
        token = akc[0] if akc else "-"
        dodatne = []
        slj_stanje = None
        vracanje = None

        for a in akc[1:]:
            if a == "NOVI_REDAK":
                dodatne.append("NOVI_REDAK")
            elif a.startswith("UDJI_U_STANJE"):
                parts = a.split()
                if len(parts) >= 2:
                    slj_stanje = parts[1]
            elif a.startswith("VRATI_SE"):
                parts = a.split()
                if len(parts) >= 2 and parts[1].isdigit():
                    vracanje = int(parts[1])

        p["uniformni_znak"] = token
        p["dodatne_akcije"] = dodatne
        p["sljedece_stanje"] = slj_stanje
        p["vracanje"] = vracanje

    return pravila


class Automat:
    def __init__(self):  # konstruktor
        self.prijelazi = {}
        self.br_stanja = 0

    def novo_stanje(self):  # stvara novo stanje automata
        s = self.br_stanja
        self.br_stanja += 1
        # stvaram kljuc vrijednost za novo stanje u rijecniku - prijelazi
        self.prijelazi[s] = {}
        return s

    def dodaj_prijelaz(self, a, b, simbol):
        if a not in self.prijelazi:  # ako ne postoji stvaram kljuc-vrijednost
            self.prijelazi[a] = {}
        if simbol not in self.prijelazi[a]:
            self.prijelazi[a][simbol] = []
        self.prijelazi[a][simbol].append(b)  # unutra stavljam b

    def dodaj_epsilon_prijelaz(self, a, b):
        # dodaje prijalaz bez da cita znak, $ = epsilon
        self.dodaj_prijelaz(a, b, epsilon)


def pretvori(izraz, automat):
    SVI_ZNAKOVI = [chr(c) for c in range(32, 127)] + \
        ['\t']  # asci kodovi bez novog reda da se ne mijesa sa novim redovima

    def je_operator(izraz, i):
        # vraca true ako znak nije escapean
        br = 0
        k = i - 1
        while k >= 0 and izraz[k] == '\\':
            br += 1
            k -= 1
        return (br % 2) == 0

    def nadji_zatvorenu_zagradu(izraz, i):
        # vraca indeks uparene zatvorene zagrade
        br = 0
        u_klasi = False
        j = i
        while j < len(izraz):
            c = izraz[j]
            if c == '[' and je_operator(izraz, j) and not u_klasi:
                u_klasi = True
            elif c == ']' and je_operator(izraz, j) and u_klasi:
                u_klasi = False
            elif not u_klasi and c == '(' and je_operator(izraz, j):
                br += 1
            elif not u_klasi and c == ')' and je_operator(izraz, j):
                br -= 1
                if br == 0:
                    return j
            j += 1
        return None

    def nadji_kraj_klase(izraz, i):
        # i pokazuje na [ i pokusava pronac zatvorenu ], ako ne nadje onda je otvorena zagrada obican znak
        j = i + 1
        while j < len(izraz):
            if izraz[j] == ']' and je_operator(izraz, j):
                return j
            j += 1
        return None

    def procitaj_escape(izraz, i):
        if i + 1 >= len(izraz):
            return '\\', i + 1
        nxt = izraz[i + 1]
        if nxt == 't':
            return '\t', i + 2
        if nxt == 'n':
            return '\n', i + 2
        if nxt == '_':
            return ' ', i + 2
        return nxt, i + 2

    def napravi_klasu(izraz, i):
        # dozvoljeni znakovi za pojedinu klasu
        j = nadji_kraj_klase(izraz, i)
        if j is None:
            # obicni znak [
            return {'['}, i + 1

        s = i + 1
        negirano = False
        if s < j and izraz[s] == '^' and je_operator(izraz, s):
            negirano = True
            s += 1

        dozvoljeno = set()
        k = s
        while k < j:
            if izraz[k] == '\\':
                ch, k = procitaj_escape(izraz, k)
                dozvoljeno.add(ch)
            else:
                dozvoljeno.add(izraz[k])
                k += 1

        if negirano:
            zabranjeno = dozvoljeno | {'\n'}
            dozvoljeno = set(SVI_ZNAKOVI) - zabranjeno

        return dozvoljeno, j + 1

    def spoji_izbore(izbori, ostatak):
        if ostatak:
            izbori.append(ostatak)
        lijevo = automat.novo_stanje()
        desno = automat.novo_stanje()
        for dio in izbori:
            a, b = pretvori(dio, automat)
            automat.dodaj_epsilon_prijelaz(lijevo, a)
            automat.dodaj_epsilon_prijelaz(b, desno)
        return lijevo, desno

    # odvoji prema znaku |
    izbori = []
    br_zagrada = 0
    u_klasi = False
    for i in range(len(izraz)):
        c = izraz[i]
        if c == '[' and je_operator(izraz, i) and not u_klasi:
            u_klasi = True
        elif c == ']' and je_operator(izraz, i) and u_klasi:
            u_klasi = False
        elif not u_klasi and c == '(' and je_operator(izraz, i):
            br_zagrada += 1
        elif not u_klasi and c == ')' and je_operator(izraz, i):
            br_zagrada -= 1
        elif not u_klasi and br_zagrada == 0 and c == '|' and je_operator(izraz, i):
            izbori.append(izraz[:i])
            ostatak = izraz[i + 1:]
            return spoji_izbore(izbori, ostatak)

    lijevo_stanje = automat.novo_stanje()
    desno_stanje = automat.novo_stanje()
    zadnje = lijevo_stanje
    i = 0

    while i < len(izraz):
        a = b = None

        if izraz[i] == '\\':
            ch, i2 = procitaj_escape(izraz, i)
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            automat.dodaj_prijelaz(a, b, ch)
            i = i2
        elif izraz[i] == '(' and je_operator(izraz, i):
            j = nadji_zatvorenu_zagradu(izraz, i)
            pod = izraz[i + 1:j]
            a, b = pretvori(pod, automat)
            i = j + 1
        elif izraz[i] == '[' and je_operator(izraz, i):
            dozv, i2 = napravi_klasu(izraz, i)
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            for ch in dozv:
                automat.dodaj_prijelaz(a, b, ch)
            i = i2
        else:
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            if izraz[i] == '$' and je_operator(izraz, i):
                automat.dodaj_epsilon_prijelaz(a, b)
            else:
                automat.dodaj_prijelaz(a, b, izraz[i])
            i += 1

        if i < len(izraz) and izraz[i] == '*' and je_operator(izraz, i):
            x, y = a, b
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            automat.dodaj_epsilon_prijelaz(a, x)
            automat.dodaj_epsilon_prijelaz(y, b)
            automat.dodaj_epsilon_prijelaz(a, b)
            automat.dodaj_epsilon_prijelaz(y, x)
            i += 1

        automat.dodaj_epsilon_prijelaz(zadnje, a)
        zadnje = b

    automat.dodaj_epsilon_prijelaz(zadnje, desno_stanje)
    return lijevo_stanje, desno_stanje


def generiraj_la_py(stanja, pravila, automati, prijelazi):
    # generira LA.py iz predloška tako da unutra stavi sve potrebne podatke
    with open("analizator/predlozak.py", "r", encoding="utf-8") as f:
        predlozak = f.read()

    pocetno_stanje = stanja[0] if stanja else None
    pravila_po_stanju = {}
    for idx, p in enumerate(pravila):
        s = p["stanje"]
        pravila_po_stanju.setdefault(s, []).append(idx)
    for s in stanja:
        pravila_po_stanju.setdefault(s, [])

    podaci_code = f"""
stanja = {repr(stanja)}
pocetno_stanje = {repr(pocetno_stanje)}
pravila = {repr(pravila)}
pravila_po_stanju = {repr(pravila_po_stanju)}
automati = {repr(automati)}
prijelazi = {repr(prijelazi)}
"""
    rezultat = predlozak.replace("# podaci iz generatora", podaci_code)

    with open("analizator/LA.py", "w", encoding="utf-8") as f:
        f.write(rezultat)


if __name__ == "__main__":
    defs, stanja, u_znakovi, pravila = parsiranje()
    defs = prosiri_definicije(defs)
    pravila = prosiri_pravila(pravila, defs)
    pravila = formatiraj_pravila(pravila)

    automati = []
    prijelazi = {}

    for idx, p in enumerate(pravila):
        a = Automat()
        s, e = pretvori(p["regex"], a)
        automati.append({"pocetno": s, "prihvatljivo": e})
        prijelazi[idx] = a.prijelazi
        pravila[idx]["br_automat"] = idx

    generiraj_la_py(stanja, pravila, automati, prijelazi)
