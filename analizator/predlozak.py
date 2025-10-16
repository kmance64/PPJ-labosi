import sys
from typing import Set, Dict
import podaci


def prijelaz(stanje, znak) -> Set:
    # vraca sva stanja u koja se moze doci iz stanje citajuci znak
    return set(podaci.prijelazi.get(stanje, {}).get(znak, set()))


def epsilon_okruzenje(trenutna_stanja) -> Set:
    # algoritam iz udzbenika
    Y: Set = set(trenutna_stanja)
    stog = list(trenutna_stanja)

    while stog:
        stanje = stog.pop()
        for st in prijelaz(stanje, '$'):
            if st not in Y:
                Y.add(st)
                stog.append(st)
    return Y


def pomak(stanja: Set, znak) -> Set:
    # pomak iz svih aktivnih stanja u sljedeca stanja citanjem znaka
    rez = set()
    for s in stanja:
        rez |= prijelaz(s, znak)
    return rez


def akcija(br_pravilo, znak, br_reda):
    # vraca koliko znakova unatrag, dodavanje broja retka, novo stanje, preskakanje znaka)
    rez = (0, 0, None, None)
    if podaci.pravila[br_pravilo]['vracanje']:
        rez[0] = podaci.pravila[br_pravilo]['vracanje']
    if podaci.pravila[br_pravilo]['dodatne_akcije'] == 'NOVI_REDAK':
        rez[1] = br_reda + 1
    if podaci.pravila[br_pravilo]['sljedece_stanje']:
        rez[2] = podaci.pravila[br_pravilo]['sljedece_stanje']
    if podaci.pravila[br_pravilo]['uniformni_znak'] == '-':
        rez[3] = znak
    return rez


def prihvatljivo(br_pravilo, stanja: Set) -> bool:
    # vraca jesmo li dosli do prihvatljivog stanja u nekom automatu
    br_automata = podaci.pravila[br_pravilo]['br_automat']
    prihvati = podaci.automati[br_automata]['prihvatljivo_stanje']
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

    pocetak = 0  # pocetak neobradenog dijela niza
    zavrsetak = None  # zadnji procitani znak
    posljednji = None  # zadnji znak najduljeg prepoznatog prefiksa

    # algoritam obrade ulaza
    while pocetak < n:
        # u aktivna stanja staviti samo ona za cije su automate pravila aktivna
        aktivna_stanja: Dict[int, Set] = {}
        for br_pravilo in pravila_po_stanju[trenutno_stanje]:
            br_automat = pravila[br_pravilo]['br_automat']
            pocetno_stanje = podaci.automati[br_automat]['pocetno_stanje']
            aktivna_stanja[br_pravilo] = epsilon_okruzenje({pocetno_stanje})

        zavrsetak = pocetak
        zadnje_prihvaceno = None  # (zadnja pozicija, br_po_redu, br_pravilo)

        while zavrsetak < n and aktivna_stanja:
            znak = kod[zavrsetak]

            # pomak u svim automatima nakon citanja znaka
            sljedeca_stanja: Dict[int, Set] = {}
            for br_pravilo, stanja in aktivna_stanja.items():
                stanja2 = epsilon_okruzenje(pomak(stanja, znak))
                if stanja2:
                    sljedeca_stanja[br_pravilo] = stanja2
                    if prihvatljivo(br_pravilo, stanja2):
                        redoslijed = pravila[br_pravilo]['br_pravilo']
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

        # nastaviti ------------------------------


if __name__ == "__main__":
    main()
