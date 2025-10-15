import re #regurni izrazi
import sys, io

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
            if linija.startswith("%X"): #ako linija pocinje s %X vraca true
                faza = 2
                continue
            m = re.match(r"\{([^}]+)\}\s+(.*)", linija) # ([^}]+) hvata sve znakove jedno ili vise puta; \s+ razmaci,tabovi,novi red; (.*) ostatak linije
            if m:           # ako je match true - dobivam m.group
                ime = m.group(1).strip()
                izraz = m.group(2).strip()
                regularne_definicije[ime] = izraz
            else:
                raise ValueError(f"Pogreška definicije: {linija}")
            
        # faza = 2 > stanja i uniformni znakovi
        elif faza == 2:
            if linija.startswith("%X"):
                stanja = linija.split()[1:] # split, uzmi sve nakon prvog
            elif linija.startswith("%L"):
                uniformni_znakovi = linija.split()[1:]
                faza = 3

        # faza = 3 > pravila
        elif faza == 3:
            if linija.startswith("<"):
                m = re.match(r"<([^>]+)>(.*)", linija) #sva stanja pocinju sa <S_stanje>
                if not m:
                    raise ValueError(f"Neispravno pravilo: {linija}")
                stanje = m.group(1).strip()
                regex = m.group(2).strip()
                i += 1
                akcije = [] #unutar {} zagrada,  svka u novom redu
                if datoteka[i] != "{":
                    raise ValueError(f"Nedostaje zagrada nakon pravila: {linija}")
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
        for ime, izraz in list(definicije.items()): #list radi kopiju definicija - inace dolazi do greske jer mijenjam rječnik kroz koji iteriram
            novi_izraz = izraz
            matches = re.findall(r"\{([^}]+)\}", izraz) # vraca listu svih matcheva
            for m in matches:
                if m in definicije:
                    novi_izraz = novi_izraz.replace(f"{{{m}}}", f"({definicije[m]})") #replace i dodajem zagrade oko izraza da se ne promijeni redoslijed
                    promijenjeno = True #oznacim da se nesto promijenilo tako da opet prolazim kroz sve definicije
                definicije[ime] = novi_izraz
    return definicije

def prosiri_pravila(pravila, definicije): #prosljedujem prosirene definicije
    for pravilo in pravila:
        regex = pravilo["regex"] # pravilo izgleda ovako: {'stanje': 'S_a', 'regex': '\\n', 'akcije': ['-', 'NOVI_REDAK']}
        matches = re.findall(r"\{([^}]+)\}", regex)
        for m in matches:
            if m in definicije:
                regex = regex.replace(f"{{{m}}}", f"({definicije[m]})")
        pravilo["regex"] = regex
    return pravila

if __name__ == "__main__":
    defs, stanja, u_znakovi, pravila = parsiranje()
    print("DEF: ", defs)
    print("STANJA: ", stanja)
    print("U_ZNAKOVI: ", u_znakovi)
    print("PRAVILA: ", pravila)

    defs = prosiri_definicije(defs)
    pravila = prosiri_pravila(pravila, defs)

    print("DEF: ", defs)
    print("STANJA: ", stanja)
    print("U_ZNAKOVI: ", u_znakovi)
    print("PRAVILA: ", pravila)