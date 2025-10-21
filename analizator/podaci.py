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


stanja = ['S_a']

pocetno_stanje = 'S_a'

pravila = [{'stanje': 'S_a', 'regex': '\\n', 'akcije': ['-', 'NOVI_REDAK'], 'uniformni_znak': '-', 'dodatne_akcije': ['NOVI_REDAK'], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 0}, {'stanje': 'S_a', 'regex': '(\\_)', 'akcije': ['-'], 'uniformni_znak': '-', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 1}, {'stanje': 'S_a', 'regex': '(a)', 'akcije': ['A'], 'uniformni_znak': 'A', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 2}, {'stanje': 'S_a', 'regex': '((x|y|z)abc)', 'akcije': ['B'], 'uniformni_znak': 'B', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 3}, {'stanje': 'S_a', 'regex': '((x|y|z)abc)((x|y|z)abc)', 'akcije': ['C'], 'uniformni_znak': 'C', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 4}, {'stanje': 'S_a', 'regex': 'o((x|y|z)abc)*', 'akcije': ['D'], 'uniformni_znak': 'D', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 5}, {'stanje': 'S_a', 'regex': 't(((x|y|z)abc)(a))', 'akcije': ['T'], 'uniformni_znak': 'T', 'dodatne_akcije': [], 'sljedece_stanje': None, 'vracanje': 0, 'br_automat': 6}]

pravila_po_stanju = {'S_a': [0, 1, 2, 3, 4, 5, 6]}

automati = [{'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}, {'pocetno': 0, 'prihvatljivo': 1}]

prijelazi = {0: {0: {'$': [2]}, 1: {}, 2: {'\n': [3]}, 3: {'$': [1]}}, 1: {0: {'$': [2]}, 1: {}, 2: {'$': [4]}, 3: {'$': [1]}, 4: {' ': [5]}, 5: {'$': [3]}}, 2: {0: {'$': [2]}, 1: {}, 2: {'$': [4]}, 3: {'$': [1]}, 4: {'a': [5]}, 5: {'$': [3]}}, 3: {0: {'$': [2]}, 1: {}, 2: {'$': [4]}, 3: {'$': [1]}, 4: {'$': [6, 10]}, 5: {'$': [20]}, 6: {'$': [8]}, 7: {'$': [5]}, 8: {'x': [9]}, 9: {'$': [7]}, 10: {'$': [12, 16]}, 11: {'$': [5]}, 12: {'$': [14]}, 13: {'$': [11]}, 14: {'y': [15]}, 15: {'$': [13]}, 16: {'$': [18]}, 17: {'$': [11]}, 18: {'z': [19]}, 19: {'$': [17]}, 20: {'a': [21]}, 21: {'$': [22]}, 22: {'b': [23]}, 23: {'$': [24]}, 24: {'c': [25]}, 25: {'$': [3]}}, 4: {0: {'$': [2]}, 1: {}, 2: {'$': [4]}, 3: {'$': [26]}, 4: {'$': [6, 10]}, 5: {'$': [20]}, 6: {'$': [8]}, 7: {'$': [5]}, 8: {'x': [9]}, 9: {'$': [7]}, 10: {'$': [12, 16]}, 11: {'$': [5]}, 12: {'$': [14]}, 13: {'$': [11]}, 14: {'y': [15]}, 15: {'$': [13]}, 16: {'$': [18]}, 17: {'$': [11]}, 18: {'z': [19]}, 19: {'$': [17]}, 20: {'a': [21]}, 21: {'$': [22]}, 22: {'b': [23]}, 23: {'$': [24]}, 24: {'c': [25]}, 25: {'$': [3]}, 26: {'$': [28]}, 27: {'$': [1]}, 28: {'$': [30, 34]}, 29: {'$': [44]}, 30: {'$': [32]}, 31: {'$': [29]}, 32: {'x': [33]}, 33: {'$': [31]}, 34: {'$': [36, 40]}, 35: {'$': [29]}, 36: {'$': [38]}, 37: {'$': [35]}, 38: {'y': [39]}, 39: {'$': [37]}, 40: {'$': [42]}, 41: {'$': [35]}, 42: {'z': [43]}, 43: {'$': [41]}, 44: {'a': [45]}, 45: {'$': [46]}, 46: {'b': [47]}, 47: {'$': [48]}, 48: {'c': [49]}, 49: {'$': [27]}}, 5: {0: {'$': [2]}, 1: {}, 2: {'o': [3]}, 3: {'$': [28]}, 4: {'$': [6]}, 5: {'$': [29, 4]}, 6: {'$': [8, 12]}, 7: {'$': [22]}, 8: {'$': [10]}, 9: {'$': [7]}, 10: {'x': [11]}, 11: {'$': [9]}, 12: {'$': [14, 18]}, 13: {'$': [7]}, 14: {'$': [16]}, 15: {'$': [13]}, 16: {'y': [17]}, 17: {'$': [15]}, 18: {'$': [20]}, 19: {'$': [13]}, 20: {'z': [21]}, 21: {'$': [19]}, 22: {'a': [23]}, 23: {'$': [24]}, 24: {'b': [25]}, 25: {'$': [26]}, 26: {'c': [27]}, 27: {'$': [5]}, 28: {'$': [4, 29]}, 29: {'$': [1]}}, 6: {0: {'$': [2]}, 1: {}, 2: {'t': [3]}, 3: {'$': [4]}, 4: {'$': [6]}, 5: {'$': [1]}, 6: {'$': [8]}, 7: {'$': [30]}, 8: {'$': [10, 14]}, 9: {'$': [24]}, 10: {'$': [12]}, 11: {'$': [9]}, 12: {'x': [13]}, 13: {'$': [11]}, 14: {'$': [16, 20]}, 15: {'$': [9]}, 16: {'$': [18]}, 17: {'$': [15]}, 18: {'y': [19]}, 19: {'$': [17]}, 20: {'$': [22]}, 21: {'$': [15]}, 22: {'z': [23]}, 23: {'$': [21]}, 24: {'a': [25]}, 25: {'$': [26]}, 26: {'b': [27]}, 27: {'$': [28]}, 28: {'c': [29]}, 29: {'$': [7]}, 30: {'$': [32]}, 31: {'$': [5]}, 32: {'a': [33]}, 33: {'$': [31]}}}
