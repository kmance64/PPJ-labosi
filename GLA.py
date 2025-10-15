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


if __name__ == "__main__":
    defs, stanja, u_znakovi, pravila = parsiranje()
    print("DEF: ", defs)
    print("STANJA: ", stanja)
    print("U_ZNAKOVI: ", u_znakovi)
    print("PRAVILA: ", pravila)