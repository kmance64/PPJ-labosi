"""
stanja leksickog analizatora: list[str]

pocetno stanje (prvo nakon %X): str

pravila poredana po redu (zbog rjesavanja nejednoznacnosti): list[dict]
    stanje koje aktivira pravilo: str
    uniformni znak ili crtica za ignoriranje: str
    dodatne akcije (novi redak i slicno): list[str]
    sljedece stanje (za akciju UDI U STANJE): str ili None
    vracanje (za akciju VRATI SE): int ili 0
    redni br. automata koji koristi ovo pravilo: int
    redni br. pravila: int

pravila dostupna u pojedinom stanju, poredana po redu: dict[str, list[int]]

automati za svako pravilo: list[dict]
    pocetno stanje: int
    prihvatljivo stanje: int

prijelazi: dict[state_id, dict[symbol, set[state_id]]]
"""
