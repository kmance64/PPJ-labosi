import sys

# podaci iz generatora


def prijelaz(br_pravilo, stanje, znak):
    # vrati sva stanja u koja se moze doci iz stanje citajuci znak
    return set(prijelazi.get(br_pravilo, {}).get(stanje, {}).get(znak, []))


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
    # razlioka izmedu znaka dolara i epsilon prijelaza
    if znak == '$':
        return set()

    rez = set()
    for s in stanja:
        rez |= prijelaz(br_pravilo, s, znak)
    return rez


def akcija(br_pravilo):
    # vraca koliko znakova unatrag se trebamo vratiti, procitan znak, jesmo li presli u novi redak, novo stanje ako postoji UDI U STANJE)
    pravilo = pravila[br_pravilo]
    vracanje = pravilo.get('vracanje', None)

    if pravilo.get('uniformni_znak') == '-':
        ime_leksicke_jedinke = None
    else:
        ime_leksicke_jedinke = pravilo.get('uniformni_znak')

    novi_red = 'NOVI_REDAK' in (pravilo.get('dodatne_akcije') or [])
    sljedece_stanje = pravilo.get('sljedece_stanje', None)

    return vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje


def prihvatljivo(br_pravilo, stanja):
    # vraca jesmo li dosli do prihvatljivog stanja u nekom automatu
    br_automata = pravila[br_pravilo]['br_automat']
    prihvati = automati[br_automata]['prihvatljivo']
    return prihvati in stanja


def main():
    kod = sys.stdin.read()  # cijeli ulazni program

    # da mi se ne prikazuju errori na windowsima
    kod = kod.replace('\r\n', '\n').replace('\r', '\n')

    # micanje zadnjeg znaka za novi red da se ne baca error bezveze
    if kod.endswith('\n'):
        kod = kod[:-1]

    n = len(kod)

    # stanja leksickog analizatora
    trenutno_stanje = pocetno_stanje
    redak = 1

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
            poc_stanje = automati[br_automat]['pocetno']
            aktivna_stanja[br_pravilo] = epsilon_okruzenje(
                br_pravilo, {poc_stanje})

        prihvaceno_min = {}
        prihvaceno_maks = {}

        zavrsetak = pocetak
        zadnje_prihvaceno = None

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
                        i = zavrsetak + 1
                        if br_pravilo not in prihvaceno_min:
                            prihvaceno_min[br_pravilo] = i
                        prihvaceno_maks[br_pravilo] = i

                        redoslijed = redoslijed_pravila_za_stanje[br_pravilo]
                        kandidat = (i, -redoslijed, br_pravilo)
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
                f"Leksička pogreška u retku {redak}: izbacujem {repr(krivo)}", file=sys.stderr)
            if krivo == '\n':
                redak += 1
            pocetak += 1
            continue

        # primijeni najbolje pronadeno pravilo
        kraj, po_redu, koristeno_pravilo = zadnje_prihvaceno
        vracanje, ime_leksicke_jedinke, novi_red, sljedece_stanje = akcija(
            koristeno_pravilo)

        maks = prihvaceno_maks[koristeno_pravilo]
        mini = prihvaceno_min[koristeno_pravilo]

        if vracanje is None:
            kraj = maks
        else:
            kraj = min(pocetak + vracanje, maks)

        # da se izbjegne beaskonacna petlja
        if kraj <= pocetak and not sljedece_stanje:
            kraj = min(pocetak + 1, n)

        leksicka_jedinka = kod[pocetak:kraj]

        # ispis jednog retka rjesenja ako je prepoznata leksicka jedinka
        if ime_leksicke_jedinke is not None:
            print(f"{ime_leksicke_jedinke} {linija} {leksicka_jedinka}")

        if novi_red:
            dodaj = leksicka_jedinka.count('\n')
            if dodaj == 0:
                dodaj = 1  # jer da nije bilo niti jednog novog reda, ne bi bio postavljen flag
            redak += dodaj

        if sljedece_stanje:
            trenutno_stanje = sljedece_stanje

        pocetak = kraj


if __name__ == "__main__":
    main()
