import sys
import podaci


def prijelaz(br_pravilo, stanje, znak):
    # vraca sva stanja u koja se moze doci iz stanje citajuci znak
    return set(podaci.prijelazi.get(br_pravilo, {}).get(stanje, {}).get(znak, []))


def epsilon_okruzenje(br_pravilo, trenutna_stanja):
    # algoritam iz udzbenika
    Y = set(trenutna_stanja)
    stog = list(trenutna_stanja)

    while stog:
        stanje = stog.pop()
        # znak dolara oznacava epsilon prijelaz
        for st in prijelaz(br_pravilo, stanje, '$'):
            if st not in Y:
                Y.add(st)
                stog.append(st)
    return Y


def pomak(br_pravilo, stanja, znak):
    # pomak iz svih aktivnih stanja u sljedeca stanja citanjem znaka
    rez = set()
    for s in stanja:
        rez |= prijelaz(br_pravilo, s, znak)
    return rez


def akcija(br_pravilo):
    # vraca koliko znakova unatrag se trebamo vratiti, procitan znak, jesmo li presli u novi redak, novo stanje ako postoji UDI U STANJE)
    pravilo = podaci.pravila[br_pravilo]
    vracanje = pravilo.get('vracanje', 0) or 0

    if pravilo.get('uniformni_znak') == '-':
        ime_leksicke_jedinke = None
    else:
        ime_leksicke_jedinke = pravilo.get('uniformni_znak')

    if pravilo.get('dodatne_akcije') == 'NOVI_REDAK':
        novi_red = True
    else:
        novi_red = False

    sljedece_stanje = pravilo.get('sljedece_stanje', None)

    return vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje


def prihvatljivo(br_pravilo, stanja):
    # vraca jesmo li dosli do prihvatljivog stanja u nekom automatu
    br_automata = podaci.pravila[br_pravilo]['br_automat']
    prihvati = podaci.automati[br_automata]['prihvatljivo']
    return prihvati in stanja


def main():
    kod = sys.stdin.read()  # cijeli ulazni program
    n = len(kod)

    # stanja leksickog analizatora
    trenutno_stanje = podaci.pocetno_stanje
    redak = 1

    pravila = podaci.pravila
    automati = podaci.automati
    pravila_po_stanju = podaci.pravila_po_stanju

    redoslijed_pravila_za_stanje = {}
    for stanje, lista_pravila in pravila_po_stanju.items():
        for k, br_pravila in enumerate(lista_pravila):
            redoslijed_pravila_za_stanje[br_pravila] = k

    pocetak = 0  # pocetak neobradenog dijela niza
    zavrsetak = None  # zadnji procitani znak

    # algoritam obrade ulaza
    while pocetak < n:
        linija = redak  # spremamo na kojoj liniji pocinje leksicka jedinka

        # u aktivna stanja staviti samo ona za cije su automate pravila aktivna
        aktivna_stanja = {}
        for br_pravilo in pravila_po_stanju[trenutno_stanje]:
            br_automat = pravila[br_pravilo]['br_automat']
            pocetno_stanje = automati[br_automat]['pocetno']
            aktivna_stanja[br_pravilo] = epsilon_okruzenje(
                br_pravilo, {pocetno_stanje})

        zavrsetak = pocetak
        zadnje_prihvaceno = None  # (zadnja pozicija, -br_po_redu, br_pravilo)

        while zavrsetak < n and aktivna_stanja:
            znak = kod[zavrsetak]

            # pomak u svim automatima nakon citanja znaka
            sljedeca_stanja = {}
            for br_pravilo, stanja in aktivna_stanja.items():
                stanja2 = epsilon_okruzenje(
                    br_pravilo, pomak(br_pravilo, stanja, znak))
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

        if zadnje_prihvaceno is None:
            # oporavak od pogreske
            krivo = kod[pocetak]
            print(
                f"Leksička pogreška na liniji {redak}: {krivo}", file=sys.stderr)
            if krivo == '\n':
                redak += 1
            pocetak += 1
            continue

        # primijeni najbolje pronadeno pravilo
        kraj, po_redu, koristeno_pravilo = zadnje_prihvaceno
        vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje = akcija(
            koristeno_pravilo)

        if vracanje:
            kraj -= vracanje
            if kraj < pocetak:
                kraj = pocetak

        leksicka_jedinka = kod[pocetak:kraj]

        # ispis jednog retka rjesenja ako je prepoznata leksicka jedinka
        if ime_leksicke_jedinke is not None:
            print(f"{ime_leksicke_jedinke} {linija} {leksicka_jedinka}")

        if novi_red:
            redak += leksicka_jedinka.count('\n')

        if sljedece_stanje:
            trenutno_stanje = sljedece_stanje

        pocetak = kraj


if __name__ == "__main__":
    main()
