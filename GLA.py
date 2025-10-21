import re  # regurni izrazi
import sys
import os


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

        # faza = 1 > regularne definicije
        if faza == 1:
            if linija.startswith("%X"):  # ako linija pocinje s %X vraca true
                faza = 2
                continue
            # ([^}]+) hvata sve znakove jedno ili vise puta; \s+ razmaci,tabovi,novi red; (.*) ostatak linije
            m = re.match(r"\{([^}]+)\}\s+(.*)", linija)
            if m:           # ako je match true - dobivam m.group
                ime = m.group(1).strip()
                izraz = m.group(2).strip()
                regularne_definicije[ime] = izraz
            else:
                raise ValueError(f"Pogreška definicije: {linija}")

        # faza = 2 > stanja i uniformni znakovi
        elif faza == 2:
            if linija.startswith("%X"):
                stanja = linija.split()[1:]  # split, uzmi sve nakon prvog
            elif linija.startswith("%L"):
                uniformni_znakovi = linija.split()[1:]
                faza = 3

        # faza = 3 > pravila
        elif faza == 3:
            if linija.startswith("<"):
                # sva stanja pocinju sa <S_stanje>
                m = re.match(r"<([^>]+)>(.*)", linija)
                if not m:
                    raise ValueError(f"Neispravno pravilo: {linija}")
                stanje = m.group(1).strip()
                regex = m.group(2).strip()
                i += 1
                akcije = []  # unutar {} zagrada,  svka u novom redu
                if datoteka[i] != "{":
                    raise ValueError(
                        f"Nedostaje zagrada nakon pravila: {linija}")
                i += 1
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
    promijenjeno = True  # Kada se nista u definicija ne promijeni znaci da je sve promijenjeno
    while promijenjeno:
        promijenjeno = False
        # list radi kopiju definicija - inace dolazi do greske jer mijenjam rječnik kroz koji iteriram
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


def obogati_pravila(pravila):
    """Pretvori 'akcije' u:
       - uniformni_znak: str | '-'
       - dodatne_akcije: list[str] (npr. ['NOVI_REDAK'])
       - sljedece_stanje: str | None
       - vracanje: int
    """
    for p in pravila:
        akc = [x.strip() for x in p.get("akcije", []) if x.strip()]
        token = akc[0] if akc else "-"
        dodatne = []
        slj_stanje = None
        vracanje = 0

        for a in akc[1:]:
            if a == "NOVI_REDAK":
                dodatne.append("NOVI_REDAK")
            elif a.startswith("UDJI_U_STANJE"):
                # format: UDJI_U_STANJE S_ime
                parts = a.split()
                if len(parts) >= 2:
                    slj_stanje = parts[1]
            elif a.startswith("VRATI_SE"):
                # format: VRATI_SE k
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
        self.dodaj_prijelaz(a, b, '$')


def pretvori(izraz, automat):
    def je_operator(izraz, i):
        br = 0
        while i - 1 >= 0 and izraz[i - 1] == '\\':
            br = br + 1
            i = i - 1
        return br % 2 == 0

    def interpretiraj_escape(znak):
        if znak == 't':
            return '\t'
        elif znak == 'n':
            return '\n'
        elif znak == '_':
            return ' '
        else:
            return znak

    def nadji_zatvorenu_zagradu(izraz, i):
        br = 0
        for j in range(i, len(izraz)):
            if izraz[j] == '(' and je_operator(izraz, j):
                br += 1
            elif izraz[j] == ')' and je_operator(izraz, j):
                br -= 1
                if br == 0:
                    return j
        raise ValueError("Nedostaje zatvorena zagrada!")

    def spoji_izbore(izbori, ostatak, automat):
        if ostatak:
            izbori.append(ostatak)
        lijevo_stanje = automat.novo_stanje()
        desno_stanje = automat.novo_stanje()
        for dio in izbori:
            (a, b) = pretvori(dio, automat)
            automat.dodaj_epsilon_prijelaz(lijevo_stanje, a)
            automat.dodaj_epsilon_prijelaz(b, desno_stanje)
        return (lijevo_stanje, desno_stanje)

    izbori = []
    br_zagrada = 0
    for i in range(len(izraz)):
        if izraz[i] == '(' and je_operator(izraz, i):
            br_zagrada = br_zagrada + 1
        elif izraz[i] == ')' and je_operator(izraz, i):
            br_zagrada = br_zagrada - 1
        elif br_zagrada == 0 and izraz[i] == '|' and je_operator(izraz, i):
            izbori.append(izraz[:i])
            ostatak = izraz[i + 1:]
            return spoji_izbore(izbori, ostatak, automat)
    lijevo_stanje = automat.novo_stanje()
    desno_stanje = automat.novo_stanje()
    prefiksirano = False
    zadnje_stanje = lijevo_stanje
    i = 0
    while i < len(izraz):
        if prefiksirano:
            prefiksirano = False
            prijelazni_znak = interpretiraj_escape(izraz[i])
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            automat.dodaj_prijelaz(a, b, prijelazni_znak)
        elif izraz[i] == '\\':
            prefiksirano = True
            i += 1
            continue
        elif izraz[i] != '(':
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            if izraz[i] == '$':
                automat.dodaj_epsilon_prijelaz(a, b)
            else:
                automat.dodaj_prijelaz(a, b, izraz[i])
        else:
            j = nadji_zatvorenu_zagradu(izraz, i)
            podizraz = izraz[i + 1:j]
            (a, b) = pretvori(podizraz, automat)
            i = j
        if i + 1 < len(izraz) and izraz[i + 1] == '*':
            x = a
            y = b
            a = automat.novo_stanje()
            b = automat.novo_stanje()
            automat.dodaj_epsilon_prijelaz(a, x)
            automat.dodaj_epsilon_prijelaz(y, b)
            automat.dodaj_epsilon_prijelaz(a, b)
            automat.dodaj_epsilon_prijelaz(y, x)
            i += 1
        automat.dodaj_epsilon_prijelaz(zadnje_stanje, a)
        zadnje_stanje = b
        i += 1
    automat.dodaj_epsilon_prijelaz(zadnje_stanje, desno_stanje)
    return (lijevo_stanje, desno_stanje)

def generiraj_la_py(stanja, pravila, automati, prijelazi):
    """
    Generira analizator/LA.py iz predloška tako da umetne sve potrebne podatke.
    """
    with open("analizator/predlozak.py", "r", encoding="utf-8") as f:
        predlozak = f.read()

    if "import podaci" in predlozak:
        predlozak = predlozak.replace("import podaci", "# Podaci ugrađeni iz generatora ispod ↓")

    umetni_iza = "# Podaci ugrađeni iz generatora ispod ↓"

    pocetno_stanje = stanja[0] if stanja else None
    pravila_po_stanju = {}
    for idx, p in enumerate(pravila):
        s = p["stanje"]
        pravila_po_stanju.setdefault(s, []).append(idx)
    for s in stanja:
        pravila_po_stanju.setdefault(s, [])

    podaci_code = f"""
# ================== Ugrađeni podaci (generirano iz GLA.py) ==================
stanja = {repr(stanja)}
pocetno_stanje = {repr(pocetno_stanje)}
pravila = {repr(pravila)}
pravila_po_stanju = {repr(pravila_po_stanju)}
automati = {repr(automati)}
prijelazi = {repr(prijelazi)}
# ===========================================================================

"""
    rezultat = predlozak.replace(umetni_iza, umetni_iza + "\n" + podaci_code)

    os.makedirs("analizator", exist_ok=True)
    with open("analizator/LA.py", "w", encoding="utf-8") as f:
        f.write(rezultat)

    print("✅ Datoteka analizator/LA.py uspješno generirana.")

if __name__ == "__main__":
    defs, stanja, u_znakovi, pravila = parsiranje()
    defs = prosiri_definicije(defs)
    pravila = prosiri_pravila(pravila, defs)
    pravila = obogati_pravila(pravila)

    automati = []
    prijelazi = {}

    for idx, p in enumerate(pravila):
        a = Automat()
        s, e = pretvori(p["regex"], a)
        automati.append({"pocetno": s, "prihvatljivo": e})
        prijelazi[idx] = a.prijelazi
        pravila[idx]["br_automat"] = idx

    generiraj_la_py(stanja, pravila, automati, prijelazi)

