import sys


class Node:
    # cvorovi za stablo sa zavrsnim i nezavrsnim znakovima
    def __init__(self, nezavrsni=None, zavrsni=None, line=None, leksicka_jedinka=None):
        self.nezavrsni = nezavrsni
        self.children = []
        self.parent = None
        self.zavrsni = zavrsni
        self.line = line
        self.leksicka_jedinka = leksicka_jedinka

        self.tip = None
        self.l_izraz = 0

    def add(self, child):
        child.parent = self
        self.children.append(child)


def parse_input(lines):
    # parsiranje indentiranog izlaza sintaksnog analizatora
    root = None
    stack = []  # parovi (indent, node)

    for raw in lines:
        line = raw.rstrip("\n")
        if line == "":
            continue

        indent = len(line) - len(line.lstrip(' '))
        text = line.lstrip(' ')

        # prepoznaj nazvrsni znak
        if text.startswith("<") and text.endswith(">"):
            node = Node(nezavrsni=text)
        else:
            # list stabla: zavrsni_znak [line] [leksicka_jedinka]
            parts = text.split(" ", 2)
            if len(parts) == 1:
                zavr = parts[0]
                node = Node(zavrsni=zavr)
            elif len(parts) == 2:
                zavr, l = parts
                node = Node(zavrsni=zavr, line=l)
            else:
                zavr, l, lex = parts
                node = Node(zavrsni=zavr, line=l, leksicka_jedinka=lex)

        # ako nema root stavi prvi nezavrsni znak s najmanjim indentom kao root
        if not stack:
            stack.append((indent, node))
            root = node
            continue

        # ako nova linija ima veci indent od vrha stoga onda je dijete vrha
        # ako ima <= indent onda mici sa stoga dok ne nadjes roditelja s manjim indentom
        while stack and indent <= stack[-1][0]:
            stack.pop()

        parent_node = stack[-1][1]
        parent_node.add(node)

        stack.append((indent, node))

    return root


class Simbol:
    # varijable i funkcije unutar djelokruga
    def __init__(self, name, tip, kind="varijabla", definirana=False, params=None):
        self.name = name
        self.tip = tip
        self.is_global = False  # globalne varijable u arm kodu se pisu na dnu
        self.offset = None  # velicina u bajtovima, potrebno za arm kod (stog)
        self.is_param = False  # je li parametar funkcije


class Djelokrug:
    def __init__(self, parent=None):
        self.parent = parent
        self.table = {}  # name -> Simbol

    def deklarirano(self, simbol):
        # deklarira simbol u trenutnom djelokrugu ako vec nije
        if simbol.name in self.table:
            return False
        self.table[simbol.name] = simbol
        return True

    def u_lokalnom_djelokrugu(self, name):
        return self.table.get(name)

    def u_nekom_djelokrugu(self, name):
        djelokrug = self
        while djelokrug is not None:
            if name in djelokrug.table:
                return djelokrug.table[name]
            djelokrug = djelokrug.parent
        return None


# pomocne funkcije za provjeru tipova
T_INT = ("int",)
T_CHAR = ("char",)
T_VOID = ("void",)
def T_CONST(t): return ("const", t)
def T_NIZ(t): return ("niz", t)
def T_FUNKCIJA(params, ret): return ("funkcija", tuple(params), ret)


def is_const(t): return t is not None and t[0] == "const"
def is_niz(t): return t is not None and t[0] == "niz"
def is_fun(t): return t is not None and t[0] == "funkcija"


def strip_const(t):
    # micanje jednog consta
    if is_const(t):
        return t[1]
    return t


def moze_implicitno_pretvoriti(tip1, tip2):
    # relacija ~ iz uputa
    if tip1 == tip2:
        return True

    def direktne_pretvorbe(t):
        rez = []

        # const(T) -> T
        if is_const(t):
            rez.append(t[1])

        # T -> const(T) za int ili char
        if t == T_INT or t == T_CHAR:
            rez.append(T_CONST(t))

        # char -> int
        if t == T_CHAR:
            rez.append(T_INT)

        # niz(T) -> niz(const(T)) ako T nije const
        if is_niz(t):
            elem = t[1]
            if not is_const(elem):
                rez.append(T_NIZ(T_CONST(elem)))

        return rez

    # relacija je refleksivna i tranzitivna pa radimo BFS po dohvatljivim tipovima
    queue = [tip1]
    visited = {tip1}

    while queue:
        t = queue.pop(0)
        for u in direktne_pretvorbe(t):
            if u == tip2:
                return True
            if u not in visited:
                visited.add(u)
                queue.append(u)

    return False


# pomocne funkcije za provjeru znakova i produkcija
def je_nezavrsni(node, name):
    return node is not None and node.nezavrsni == name


def vrsta_znaka_gramatike(node):
    return node.nezavrsni if node.nezavrsni else node.zavrsni


def je_produkcija(node, pattern):
    # da znamo koja je produkcija iskoristena
    desna_strana_produkcije = [vrsta_znaka_gramatike(c) for c in node.children]
    return desna_strana_produkcije == pattern


def je_broj(t):
    t = strip_const(t)
    return t == T_INT or t == T_CHAR


def je_lizraz_tip(t):
    # l-izraz moze biti samo varijabla tipa T (int/char), bez const, bez niza, bez funkcije
    return t == T_INT or t == T_CHAR


INT_MIN = -2147483648
INT_MAX = 2147483647


def parse_const_exp(node):
    # vraca int vrijednost za BROJ ili ZNAK, inace None
    if node is None or node.zavrsni is None:
        return None
    if node.zavrsni == "BROJ":
        return int(node.leksicka_jedinka, 0)
    if node.zavrsni == "ZNAK":
        if not je_valid_char(node.leksicka_jedinka):
            return None
        body = node.leksicka_jedinka[1:-1]
        if body[0] != "\\":
            return ord(body)
        if len(body) != 2:
            return None
        esc = {"t": "\t", "n": "\n", "0": "\0", "'": "'", '"': '"', "\\": "\\"}
        ch = esc.get(body[1])
        return ord(ch) if ch is not None else None
    return None


def je_valid_char(lex):
    if lex is None or len(lex) < 3 or lex[0] != "'" or lex[-1] != "'":
        return False
    body = lex[1:-1]
    if body == "":
        return False
    if body[0] != "\\":
        return len(body) == 1
    if len(body) != 2:
        return False
    return body[1] in ["t", "n", "0", "'", '"', "\\"]


def je_valid_string(lex):
    if lex is None or len(lex) < 2 or lex[0] != '"' or lex[-1] != '"':
        return False
    s = lex[1:-1]
    i = 0
    while i < len(s):
        if s[i] == "\\":
            if i + 1 >= len(s):
                return False
            if s[i+1] not in ["t", "n", "0", "'", '"', "\\"]:
                return False
            i += 2
        else:
            i += 1
    return True


def semanticka_greska(node):
    n = node.nezavrsni
    desno = []
    for c in node.children:
        if c.nezavrsni:
            desno.append(c.nezavrsni)
        else:
            desno.append(
                f"{c.zavrsni}({c.line},{c.leksicka_jedinka})")

    print(f"{n} ::= " + " ".join(desno))
    sys.exit(0)


globalne_funkcije = {}
deklarirane_funkcije = set()
definirane_funkcije = set()
stog_povratnih_tipova = []  # stog povratnih tipova trenutne funkcije
dubina_petlje = 0
loop_continue = []
loop_break = []

# uredivanje za generator arm koda!!!!
arm_kod = []
globalne_varijable = {}
globalni_nizovi = {}
trenutna_funkcija = None
trenutna_velicina_okvira = 0  # koliko bajtova je zauzeto u trenutnoj funkciji
nemoj_generirati = False


def analyze(node, djelokrug):
    global dubina_petlje
    global loop_continue
    global loop_break
    global trenutna_funkcija
    global nemoj_generirati
    global trenutna_velicina_okvira
    if node is None:
        return
    if node.zavrsni == "$":
        return

    # pomocna funkcija za analizu binarnih operatora jer imaju ista semanticka pravila
    def bin_op(node, child_left_i, child_right_i, result_type=T_INT, require_int=True):
        analyze(node.children[child_left_i], djelokrug)
        analyze(node.children[child_right_i], djelokrug)
        tl = node.children[child_left_i].tip
        tr = node.children[child_right_i].tip
        if require_int:
            if not moze_implicitno_pretvoriti(tl, T_INT):
                semanticka_greska(node)
            if not moze_implicitno_pretvoriti(tr, T_INT):
                semanticka_greska(node)
            node.tip = result_type
            node.l_izraz = 0
        return

    # pomocna funkcija za odredivanje niza znakova
    def je_niz_znakova(node):
        cur = node
        while True:
            if cur.zavrsni is not None:
                return cur.zavrsni == "NIZ_ZNAKOVA"

            if len(cur.children) == 1:
                cur = cur.children[0]
                continue

            if cur.nezavrsni == "<primarni_izraz>" and \
                    je_produkcija(cur, ["L_ZAGRADA", "<izraz>", "D_ZAGRADA"]):
                cur = cur.children[1]
                continue

            return False

    # pomocna funkcija za odredivanje duljine niza znakova
    def duljina_niza_znakova(lex):
        if lex is None:
            return 0
        s = lex
        if len(s) >= 2 and s[0] == '"' and s[-1] == '"':
            s = s[1:-1]

        i = 0
        n = 0
        while i < len(s):
            if s[i] == '\\' and i + 1 < len(s):
                # escape znakovi se ne broje
                i += 2
                n += 1
            else:
                i += 1
                n += 1
        return n

    # <primarni_izraz>
    if je_nezavrsni(node, "<primarni_izraz>"):
        if je_produkcija(node, ["IDN"]):
            idn = node.children[0].leksicka_jedinka
            sym = djelokrug.u_nekom_djelokrugu(idn)
            if sym is None:
                semanticka_greska(node)
            node.tip = sym.tip

            node.l_izraz = 1 if je_lizraz_tip(node.tip) else 0

            # arm kod za ucitavanje varijable i pohranu na stog
            if trenutna_funkcija is not None and not nemoj_generirati:
                if is_fun(node.tip):
                    return
                # globalne varijable se ucitavaju iz .data na dnu arm koda
                if is_niz(node.tip):
                    # za niz vracamo adresu
                    if getattr(sym, "is_global", False):
                        arm_kod.append(f"    LDR R5, ={idn}")
                        arm_kod.append("    MOV R6, R5")
                    elif getattr(sym, "is_param", False):
                        arm_kod.append(f"    LDR R6, [R4, #{sym.offset}]")
                    else:
                        if sym.offset is None:
                            semanticka_greska(node)
                        if sym.offset < 0:
                            arm_kod.append(f"    SUB R6, R4, #{-sym.offset}")
                        else:
                            arm_kod.append(f"    ADD R6, R4, #{sym.offset}")
                    arm_kod.append("    PUSH {R6}")
                    return
                if getattr(sym, "is_global", False):
                    arm_kod.append(f"    LDR R5, ={idn}")
                    arm_kod.append("    LDR R6, [R5]")
                else:
                    if sym.offset is None:
                        semanticka_greska(node)
                    arm_kod.append(f"    LDR R6, [R4, #{sym.offset}]")
                arm_kod.append("    PUSH {R6}")
            return

        if je_produkcija(node, ["BROJ"]):
            try:
                v = int(node.children[0].leksicka_jedinka, 0)
            except:
                semanticka_greska(node)
            if v < INT_MIN or v > INT_MAX:
                semanticka_greska(node)
            node.tip = T_INT
            node.l_izraz = 0

            # pohrana broja na stog
            if trenutna_funkcija is not None and not nemoj_generirati:
                arm_kod.append(f"    LDR R6, ={v}")
                arm_kod.append("    PUSH {R6}")
            return

        if je_produkcija(node, ["ZNAK"]):
            if not je_valid_char(node.children[0].leksicka_jedinka):
                semanticka_greska(node)
            node.tip = T_CHAR
            node.l_izraz = 0
            # pohrana znaka na stog
            if trenutna_funkcija is not None and not nemoj_generirati:
                v = parse_const_exp(node.children[0])
                if v is None:
                    semanticka_greska(node)
                arm_kod.append(f"    MOV R6, #{v}")
                arm_kod.append("    PUSH {R6}")
            return

        if je_produkcija(node, ["NIZ_ZNAKOVA"]):
            if not je_valid_string(node.children[0].leksicka_jedinka):
                semanticka_greska(node)
            node.tip = T_NIZ(T_CONST(T_CHAR))
            node.l_izraz = 0
            return

        if je_produkcija(node, ["L_ZAGRADA", "<izraz>", "D_ZAGRADA"]):
            analyze(node.children[1], djelokrug)
            node.tip = node.children[1].tip
            node.l_izraz = node.children[1].l_izraz
            return

        semanticka_greska(node)

    # <postfiks_izraz>
    if je_nezavrsni(node, "<postfiks_izraz>"):
        if je_produkcija(node, ["<primarni_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return

        # ideksiranje nizova, a[nesto]
        if je_produkcija(node, ["<postfiks_izraz>", "L_UGL_ZAGRADA", "<izraz>", "D_UGL_ZAGRADA"]):
            prev_nemoj_generirati = nemoj_generirati
            nemoj_generirati = True  # da se prepozna da je array
            analyze(node.children[0], djelokrug)
            nemoj_generirati = prev_nemoj_generirati
            analyze(node.children[2], djelokrug)

            t0 = node.children[0].tip
            tI = node.children[2].tip

            if not is_niz(t0):
                semanticka_greska(node)
            if not moze_implicitno_pretvoriti(tI, T_INT):
                semanticka_greska(node)

            elem = t0[1]
            node.tip = elem
            node.l_izraz = 1 if je_lizraz_tip(elem) else 0

            # arm kod: ucitaj vrijednost elementa niza
            if trenutna_funkcija is not None and not nemoj_generirati:
                # indeks je na stogu (iz analyze <izraz>)
                arm_kod.append("    POP {R0}")
                # pronadi ime arraya
                base = node.children[0]
                while base is not None and len(base.children) == 1 and base.nezavrsni != "<primarni_izraz>":
                    base = base.children[0]
                if base is None or base.nezavrsni != "<primarni_izraz>" or \
                        not je_produkcija(base, ["IDN"]):
                    semanticka_greska(node)
                ime = base.children[0].leksicka_jedinka

                # je li globalni ili lokalni array
                sym = djelokrug.u_nekom_djelokrugu(ime)
                if sym is None:
                    semanticka_greska(node)
                if getattr(sym, "is_global", False):
                    arm_kod.append(f"    LDR R5, ={ime}")
                else:
                    if sym.offset is None:
                        semanticka_greska(node)
                    if getattr(sym, "is_param", False) and is_niz(sym.tip):
                        arm_kod.append(f"    LDR R5, [R4, #{sym.offset}]")
                    else:
                        if sym.offset < 0:
                            arm_kod.append(f"    SUB R5, R4, #{-sym.offset}")
                        else:
                            arm_kod.append(f"    ADD R5, R4, #{sym.offset}")
                arm_kod.append("    ADD R5, R5, R0, LSL #2")
                arm_kod.append("    LDR R6, [R5]")
                arm_kod.append("    PUSH {R6}")
            return

        # pozivanje funkcija bez parametara, f()
        if je_produkcija(node, ["<postfiks_izraz>", "L_ZAGRADA", "D_ZAGRADA"]):
            prev_nemoj_generirati = nemoj_generirati
            nemoj_generirati = True
            analyze(node.children[0], djelokrug)
            nemoj_generirati = prev_nemoj_generirati
            t0 = node.children[0].tip
            if not is_fun(t0):
                semanticka_greska(node)
            # ne smije imati parametara
            if len(list(t0[1])) != 0:
                semanticka_greska(node)
            node.tip = t0[2]
            node.l_izraz = 0
            if trenutna_funkcija is not None:
                base = node.children[0]
                while base is not None and len(base.children) == 1 and base.nezavrsni != "<primarni_izraz>":
                    base = base.children[0]
                if base is None or base.nezavrsni != "<primarni_izraz>" or \
                        not je_produkcija(base, ["IDN"]):
                    semanticka_greska(node)
                fname = base.children[0].leksicka_jedinka
                arm_kod.append(f"    BL F_{fname.upper()}")
                arm_kod.append("    PUSH {R6}")
            return

        # pozivanje funkcije s parametrima, f(args)
        if je_produkcija(node, ["<postfiks_izraz>", "L_ZAGRADA", "<lista_argumenata>", "D_ZAGRADA"]):
            prev_nemoj_generirati = nemoj_generirati
            nemoj_generirati = True
            analyze(node.children[0], djelokrug)
            nemoj_generirati = prev_nemoj_generirati
            analyze(node.children[2], djelokrug)

            t0 = node.children[0].tip
            if not is_fun(t0):
                semanticka_greska(node)

            param_types = list(t0[1])
            # postavljeno u <lista_argumenata>
            arg_types = node.children[2].tipovi

            if len(param_types) != len(arg_types):
                semanticka_greska(node)

            for a, p in zip(arg_types, param_types):
                if not moze_implicitno_pretvoriti(a, p):
                    semanticka_greska(node)

            node.tip = t0[2]
            node.l_izraz = 0
            if trenutna_funkcija is not None:
                n = len(arg_types)
                max_reg = min(4, n)
                for i in range(max_reg):
                    offset = 4 * (n - 1 - i)
                    arm_kod.append(f"    LDR R{i}, [SP, #{offset}]")

                base = node.children[0]
                while base is not None and len(base.children) == 1 and base.nezavrsni != "<primarni_izraz>":
                    base = base.children[0]
                if base is None or base.nezavrsni != "<primarni_izraz>" or \
                        not je_produkcija(base, ["IDN"]):
                    semanticka_greska(node)
                fname = base.children[0].leksicka_jedinka
                arm_kod.append(f"    BL F_{fname.upper()}")

                # nakon poziva makni sve argumente sa stoga
                arm_kod.append(f"    ADD SP, SP, #{4 * n}")
                arm_kod.append("    PUSH {R6}")
            return

        if je_produkcija(node, ["<postfiks_izraz>", "OP_INC"]) or \
           je_produkcija(node, ["<postfiks_izraz>", "OP_DEC"]):
            analyze(node.children[0], djelokrug)
            if node.children[0].l_izraz != 1:
                semanticka_greska(node)
            if not moze_implicitno_pretvoriti(node.children[0].tip, T_INT):
                semanticka_greska(node)
            node.tip = T_INT
            node.l_izraz = 0

            # arm kod za postfiksni ++ i --
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")   # stara vrijednost
                arm_kod.append("    MOV R7, R6")  # kopija za rezultat izraza

                if node.children[1].zavrsni == "OP_INC":
                    arm_kod.append("    ADD R6, R6, #1")
                else:
                    arm_kod.append("    SUB R6, R6, #1")

                child = node.children[0]
                if je_nezavrsni(child, "<postfiks_izraz>") and \
                        je_produkcija(child, ["<primarni_izraz>"]) and \
                        je_produkcija(child.children[0], ["IDN"]):

                    ime = child.children[0].children[0].leksicka_jedinka
                    sym = djelokrug.u_nekom_djelokrugu(ime)

                    if getattr(sym, "is_global", False):
                        arm_kod.append(f"    LDR R5, ={ime}")
                        arm_kod.append("    STR R6, [R5]")
                    else:
                        arm_kod.append(f"    STR R6, [R4, #{sym.offset}]")

                arm_kod.append("    PUSH {R7}")

            return

        semanticka_greska(node)

    # <lista_argumenata>
    if je_nezavrsni(node, "<lista_argumenata>"):
        if je_produkcija(node, ["<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            node.tipovi = [node.children[0].tip]
            return

        if je_produkcija(node, ["<lista_argumenata>", "ZAREZ", "<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            analyze(node.children[2], djelokrug)
            node.tipovi = node.children[0].tipovi + [node.children[2].tip]
            return

        semanticka_greska(node)

    # <unarni_izraz>
    if je_nezavrsni(node, "<unarni_izraz>"):
        if je_produkcija(node, ["<postfiks_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return

        # ++u, --u
        if je_produkcija(node, ["OP_INC", "<unarni_izraz>"]) or \
           je_produkcija(node, ["OP_DEC", "<unarni_izraz>"]):
            analyze(node.children[1], djelokrug)
            if node.children[1].l_izraz != 1:
                semanticka_greska(node)
            if not moze_implicitno_pretvoriti(node.children[1].tip, T_INT):
                semanticka_greska(node)
            node.tip = T_INT
            node.l_izraz = 0

            # arm kod za prefiksni ++ i --
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")

                if node.children[0].zavrsni == "OP_INC":
                    arm_kod.append("    ADD R6, R6, #1")
                else:
                    arm_kod.append("    SUB R6, R6, #1")

                child = node.children[1]
                if je_nezavrsni(child, "<unarni_izraz>") and \
                        je_produkcija(child, ["<postfiks_izraz>"]) and \
                        je_produkcija(child.children[0], ["<primarni_izraz>"]) and \
                        je_produkcija(child.children[0].children[0], ["IDN"]):

                    ime = child.children[0].children[0].children[0].leksicka_jedinka
                    sym = djelokrug.u_nekom_djelokrugu(ime)

                    if getattr(sym, "is_global", False):
                        arm_kod.append(f"    LDR R5, ={ime}")
                        arm_kod.append("    STR R6, [R5]")
                    else:
                        arm_kod.append(f"    STR R6, [R4, #{sym.offset}]")

                arm_kod.append("    PUSH {R6}")

            return

        if je_produkcija(node, ["<unarni_operator>", "<cast_izraz>"]):
            # analyze(node.children[0], djelokrug)
            analyze(node.children[1], djelokrug)
            t = node.children[1].tip
            if not moze_implicitno_pretvoriti(t, T_INT):
                semanticka_greska(node)
            node.tip = T_INT
            node.l_izraz = 0
            # arm kod za unarne operatore
            if trenutna_funkcija is not None:
                op = node.children[0].children[0].zavrsni
                arm_kod.append("    POP {R6}")

                if op in ["PLUS", "OP_PLUS"]:
                    pass
                elif op in ["MINUS", "OP_MINUS"]:
                    arm_kod.append("    RSBS R6, R6, #0")
                elif op == "OP_NEG":
                    arm_kod.append("    CMP R6, #0")
                    lbl = len(arm_kod)
                    arm_kod.append(f"    BEQ NEG_TRUE_{lbl}")
                    arm_kod.append("    MOV R6, #0")
                    arm_kod.append(f"    B NEG_END_{lbl}")
                    arm_kod.append(f"NEG_TRUE_{lbl}:")
                    arm_kod.append("    MOV R6, #1")
                    arm_kod.append(f"NEG_END_{lbl}:")
                elif op == "OP_TILDA":
                    arm_kod.append("    MVN R6, R6")

                arm_kod.append("    PUSH {R6}")

            return

        semanticka_greska(node)

    # <unarni_operator>
    if je_nezavrsni(node, "<unarni_operator>"):
        # u stablu se pojavljuje kao jedan nezavrsni znak PLUS/MINUS ili OP_PLUS/OP_MINUS, OP_TILDA, OP_NEG
        if len(node.children) != 1 or node.children[0].zavrsni is None:
            semanticka_greska(node)
        op = node.children[0].zavrsni
        if op not in ["PLUS", "MINUS", "OP_PLUS", "OP_MINUS", "OP_TILDA", "OP_NEG"]:
            semanticka_greska(node)
        return

    # <cast_izraz>
    if je_nezavrsni(node, "<cast_izraz>"):
        if je_produkcija(node, ["<unarni_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return

        # (ime_tipa)izraz
        if je_produkcija(node, ["L_ZAGRADA", "<ime_tipa>", "D_ZAGRADA", "<cast_izraz>"]):
            analyze(node.children[1], djelokrug)
            analyze(node.children[3], djelokrug)
            tdst = node.children[1].tip
            tsrc = node.children[3].tip
            if not je_broj(tdst) or not je_broj(tsrc):
                semanticka_greska(node)
            node.tip = tdst
            node.l_izraz = 0
            return

        semanticka_greska(node)

    # <ime_tipa>
    if je_nezavrsni(node, "<ime_tipa>"):
        if je_produkcija(node, ["<specifikator_tipa>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            return

        if je_produkcija(node, ["KR_CONST", "<specifikator_tipa>"]):
            analyze(node.children[1], djelokrug)
            if node.children[1].tip == T_VOID:
                semanticka_greska(node)   # zabranjuje const void
            node.tip = T_CONST(node.children[1].tip)
            return

        semanticka_greska(node)

    # <specifikator_tipa>
    if je_nezavrsni(node, "<specifikator_tipa>"):
        if je_produkcija(node, ["KR_INT"]):
            node.tip = T_INT
            return
        if je_produkcija(node, ["KR_CHAR"]):
            node.tip = T_CHAR
            return
        if je_produkcija(node, ["KR_VOID"]):
            node.tip = T_VOID
            return
        semanticka_greska(node)

    # <multiplikativni_izraz>
    if je_nezavrsni(node, "<multiplikativni_izraz>"):
        if je_produkcija(node, ["<cast_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return
        if je_produkcija(node, ["<multiplikativni_izraz>", "OP_PUTA", "<cast_izraz>"]) or \
           je_produkcija(node, ["<multiplikativni_izraz>", "OP_DIJELI", "<cast_izraz>"]) or \
           je_produkcija(node, ["<multiplikativni_izraz>", "OP_MOD", "<cast_izraz>"]):
            bin_op(node, 0, 2, T_INT, True)

            # arm kod za mnozenje, dijeljenje i mod
            if trenutna_funkcija is not None:
                op = node.children[1].zavrsni
                arm_kod.append("    POP {R0}")  # desni operand (divisor)
                arm_kod.append("    POP {R1}")  # lijevi operand (dividend)")
                if op == "OP_PUTA":
                    arm_kod.append("    MUL R6, R1, R0")
                elif op == "OP_DIJELI":
                    lbl = len(arm_kod)
                    # R1 = dividend, R0 = divisor
                    arm_kod.append("    MOV R2, #0")   # sign
                    arm_kod.append("    MOV R3, R0")   # abs(divisor)")
                    # abs(dividend) u R1
                    arm_kod.append("    CMP R1, #0")
                    arm_kod.append(f"    BGE DIV_ABS_DIV_{lbl}")
                    arm_kod.append("    RSBS R1, R1, #0")
                    arm_kod.append("    EOR R2, R2, #1")
                    arm_kod.append(f"DIV_ABS_DIV_{lbl}:")
                    # abs(divisor) u R3
                    arm_kod.append("    CMP R3, #0")
                    arm_kod.append(f"    BGE DIV_ABS_DIVISOR_{lbl}")
                    arm_kod.append("    RSBS R3, R3, #0")
                    arm_kod.append("    EOR R2, R2, #1")
                    arm_kod.append(f"DIV_ABS_DIVISOR_{lbl}:")
                    arm_kod.append("    MOV R6, #0")   # quotient
                    arm_kod.append(f"DIV_LOOP_{lbl}:")
                    arm_kod.append("    CMP R1, R3")
                    arm_kod.append(f"    BLT DIV_DONE_{lbl}")
                    arm_kod.append("    SUB R1, R1, R3")
                    arm_kod.append("    ADD R6, R6, #1")
                    arm_kod.append(f"    B DIV_LOOP_{lbl}")
                    arm_kod.append(f"DIV_DONE_{lbl}:")
                    arm_kod.append("    CMP R2, #0")
                    arm_kod.append(f"    BEQ DIV_END_{lbl}")
                    arm_kod.append("    RSBS R6, R6, #0")
                    arm_kod.append(f"DIV_END_{lbl}:")
                else:  # OP_MOD
                    lbl = len(arm_kod)
                    # Sačuvaj originalne operande
                    arm_kod.append("    PUSH {R1}")     # original dividend
                    arm_kod.append("    PUSH {R0}")     # original divisor

                    # izračunaj kvocijent kao kod OP_DIJELI (trunciranje prema 0)
                    arm_kod.append("    MOV R2, #0")   # sign
                    arm_kod.append("    MOV R3, R0")   # abs(divisor)")
                    # abs(dividend) u R1
                    arm_kod.append("    CMP R1, #0")
                    arm_kod.append(f"    BGE MOD_ABS_DIV_{lbl}")
                    arm_kod.append("    RSBS R1, R1, #0")
                    arm_kod.append("    EOR R2, R2, #1")
                    arm_kod.append(f"MOD_ABS_DIV_{lbl}:")
                    # abs(divisor) u R3
                    arm_kod.append("    CMP R3, #0")
                    arm_kod.append(f"    BGE MOD_ABS_DIVISOR_{lbl}")
                    arm_kod.append("    RSBS R3, R3, #0")
                    arm_kod.append("    EOR R2, R2, #1")
                    arm_kod.append(f"MOD_ABS_DIVISOR_{lbl}:")
                    arm_kod.append("    MOV R6, #0")   # quotient
                    arm_kod.append(f"MOD_DIV_LOOP_{lbl}:")
                    arm_kod.append("    CMP R1, R3")
                    arm_kod.append(f"    BLT MOD_DIV_DONE_{lbl}")
                    arm_kod.append("    SUB R1, R1, R3")
                    arm_kod.append("    ADD R6, R6, #1")
                    arm_kod.append(f"    B MOD_DIV_LOOP_{lbl}")
                    arm_kod.append(f"MOD_DIV_DONE_{lbl}:")
                    arm_kod.append("    CMP R2, #0")
                    arm_kod.append(f"    BEQ MOD_DIV_END_{lbl}")
                    arm_kod.append("    RSBS R6, R6, #0")  # kvocijent sa znakom
                    arm_kod.append(f"MOD_DIV_END_{lbl}:")

                    # R6 = kvocijent; vrati originalne operande
                    arm_kod.append("    POP {R2}")       # original divisor
                    arm_kod.append("    POP {R3}")       # original dividend

                    # remainder = dividend - quotient*divisor
                    arm_kod.append("    MUL R0, R6, R2")  # R0 = quotient * divisor
                    arm_kod.append("    SUB R6, R3, R0")  # remainder
                arm_kod.append("    PUSH {R6}")
            return
        semanticka_greska(node)

    # <aditivni_izraz>
    if je_nezavrsni(node, "<aditivni_izraz>"):
        if je_produkcija(node, ["<multiplikativni_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return
        if je_produkcija(node, ["<aditivni_izraz>", "PLUS", "<multiplikativni_izraz>"]) or \
           je_produkcija(node, ["<aditivni_izraz>", "MINUS", "<multiplikativni_izraz>"]):
            bin_op(node, 0, 2, T_INT, True)

            # arm kod za zbrajanje i oduzimanje
            if trenutna_funkcija is not None:
                op = node.children[1].zavrsni
                arm_kod.append("    POP {R0}")
                arm_kod.append("    POP {R1}")
                if op == "PLUS":
                    arm_kod.append("    ADD R6, R1, R0")
                else:
                    arm_kod.append("    SUB R6, R1, R0")
                arm_kod.append("    PUSH {R6}")
            return
        semanticka_greska(node)

    # relacijski izrazi koji imaju slicna semanticka pravila
    rel_ops = [
        "<odnosni_izraz>",
        "<jednakosni_izraz>",
        "<bin_i_izraz>",
        "<bin_xili_izraz>",
        "<bin_ili_izraz>",
        "<log_i_izraz>",
        "<log_ili_izraz>",
    ]
    if node.nezavrsni in rel_ops:
        if node.nezavrsni == "<log_i_izraz>" and \
                len(node.children) == 3 and \
                node.children[1].zavrsni == "OP_I":

            analyze(node.children[0], djelokrug)
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ LOGI_FALSE_{lbl}")

            analyze(node.children[2], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ LOGI_FALSE_{lbl}")

                arm_kod.append("    MOV R6, #1")
                arm_kod.append(f"    B LOGI_END_{lbl}")

                arm_kod.append(f"LOGI_FALSE_{lbl}:")
                arm_kod.append("    MOV R6, #0")

                arm_kod.append(f"LOGI_END_{lbl}:")
                arm_kod.append("    PUSH {R6}")

            node.tip = T_INT
            node.l_izraz = 0
            return
            # logicki ili (||)
        if node.nezavrsni == "<log_ili_izraz>" and \
                len(node.children) == 3 and \
                node.children[1].zavrsni == "OP_ILI":

            analyze(node.children[0], djelokrug)
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BNE LOGILI_TRUE_{lbl}")

            analyze(node.children[2], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BNE LOGILI_TRUE_{lbl}")

                arm_kod.append("    MOV R6, #0")
                arm_kod.append(f"    B LOGILI_END_{lbl}")

                arm_kod.append(f"LOGILI_TRUE_{lbl}:")
                arm_kod.append("    MOV R6, #1")

                arm_kod.append(f"LOGILI_END_{lbl}:")
                arm_kod.append("    PUSH {R6}")

            node.tip = T_INT
            node.l_izraz = 0
            return

        # slucajevi kad produkcija samo ide u sljedeci nezavrsni znak
        if je_produkcija(node, ["<aditivni_izraz>"]) or \
           je_produkcija(node, ["<odnosni_izraz>"]) or \
           je_produkcija(node, ["<jednakosni_izraz>"]) or \
           je_produkcija(node, ["<bin_i_izraz>"]) or \
           je_produkcija(node, ["<bin_xili_izraz>"]) or \
           je_produkcija(node, ["<bin_ili_izraz>"]) or \
           je_produkcija(node, ["<log_i_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return

        # izrazi s operatorima
        if len(node.children) == 3:
            op = node.children[1].zavrsni
            if op == "OP_I" or op == "OP_ILI":
                semanticka_greska(node)
            bin_op(node, 0, 2, T_INT, True)

            if trenutna_funkcija is not None:
                op = node.children[1].zavrsni

                arm_kod.append("    POP {R0}")  # desni operand
                arm_kod.append("    POP {R1}")  # lijevi operand

                # bitovni operatori
                if op == "OP_BIN_I":  # &
                    arm_kod.append("    AND R6, R1, R0")
                    arm_kod.append("    PUSH {R6}")
                    return

                if op == "OP_BIN_XILI":  # ^
                    arm_kod.append("    EOR R6, R1, R0")
                    arm_kod.append("    PUSH {R6}")
                    return

                if op == "OP_BIN_ILI":  # |
                    arm_kod.append("    ORR R6, R1, R0")
                    arm_kod.append("    PUSH {R6}")
                    return

                # relacijski i logicki operatori
                arm_kod.append("    CMP R1, R0")

                lbl = len(arm_kod)

                if op == "OP_EQ":
                    arm_kod.append(f"    BEQ TRUE_{lbl}")
                elif op == "OP_NEQ":
                    arm_kod.append(f"    BNE TRUE_{lbl}")
                elif op == "OP_GT":
                    arm_kod.append(f"    BGT TRUE_{lbl}")
                elif op == "OP_LT":
                    arm_kod.append(f"    BLT TRUE_{lbl}")
                elif op == "OP_GTE":
                    arm_kod.append(f"    BGE TRUE_{lbl}")
                elif op == "OP_LTE":
                    arm_kod.append(f"    BLE TRUE_{lbl}")
                else:
                    arm_kod.append(f"    B FALSE_{lbl}")

                arm_kod.append(f"FALSE_{lbl}:")
                arm_kod.append("    MOV R6, #0")
                arm_kod.append(f"    B END_{lbl}")

                arm_kod.append(f"TRUE_{lbl}:")
                arm_kod.append("    MOV R6, #1")

                arm_kod.append(f"END_{lbl}:")
                arm_kod.append("    PUSH {R6}")

            return

        semanticka_greska(node)

    # <izraz_pridruzivanja>
    if je_nezavrsni(node, "<izraz_pridruzivanja>"):
        if je_produkcija(node, ["<log_ili_izraz>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return

        if je_produkcija(node, ["<postfiks_izraz>", "OP_PRIDRUZI", "<izraz_pridruzivanja>"]):
            nemoj_generirati = True
            analyze(node.children[0], djelokrug)
            nemoj_generirati = False
            lijevo = node.children[0]
            is_lval = False
            if je_nezavrsni(lijevo, "<postfiks_izraz>"):
                if je_produkcija(lijevo, ["<primarni_izraz>"]) and \
                        je_produkcija(lijevo.children[0], ["IDN"]):
                    is_lval = True
                if je_produkcija(lijevo, ["<postfiks_izraz>", "L_UGL_ZAGRADA", "<izraz>", "D_UGL_ZAGRADA"]):
                    is_lval = True
            if lijevo.l_izraz == 1:
                is_lval = True
            if not is_lval:
                semanticka_greska(node)

            analyze(node.children[2], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[2].tip, node.children[0].tip):
                semanticka_greska(node)

            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")

                # lijeva strana moze biti IDN ili element niza
                lijevo = node.children[0]
                if je_nezavrsni(lijevo, "<postfiks_izraz>") and \
                        je_produkcija(lijevo, ["<primarni_izraz>"]):
                    ime = lijevo.children[0].children[0].leksicka_jedinka
                    sym = djelokrug.u_nekom_djelokrugu(ime)
                    if getattr(sym, "is_global", False):
                        arm_kod.append(f"    LDR R5, ={ime}")
                        arm_kod.append("    STR R6, [R5]")
                    else:
                        arm_kod.append(f"    STR R6, [R4, #{sym.offset}]")
                elif je_nezavrsni(lijevo, "<postfiks_izraz>") and \
                        je_produkcija(lijevo, ["<postfiks_izraz>", "L_UGL_ZAGRADA", "<izraz>", "D_UGL_ZAGRADA"]):
                    # izracunaj adresu elementa niza
                    # sacuvaj desnu stranu jer izracun indeksa koristi R6
                    arm_kod.append("    PUSH {R6}")
                    analyze(lijevo.children[2], djelokrug)
                    arm_kod.append("    POP {R0}")
                    arm_kod.append("    POP {R6}")
                    base = lijevo.children[0]
                    while base is not None and len(base.children) == 1 and base.nezavrsni != "<primarni_izraz>":
                        base = base.children[0]
                    if base is None or base.nezavrsni != "<primarni_izraz>" or \
                            not je_produkcija(base, ["IDN"]):
                        semanticka_greska(node)
                    ime = base.children[0].leksicka_jedinka
                    sym = djelokrug.u_nekom_djelokrugu(ime)
                    if getattr(sym, "is_global", False):
                        arm_kod.append(f"    LDR R5, ={ime}")
                    else:
                        if getattr(sym, "is_param", False) and is_niz(sym.tip):
                            arm_kod.append(f"    LDR R5, [R4, #{sym.offset}]")
                        else:
                            if sym.offset < 0:
                                arm_kod.append(
                                    f"    SUB R5, R4, #{-sym.offset}")
                            else:
                                arm_kod.append(
                                    f"    ADD R5, R4, #{sym.offset}")
                    arm_kod.append("    ADD R5, R5, R0, LSL #2")
                    arm_kod.append("    STR R6, [R5]")
                else:
                    semanticka_greska(node)

                arm_kod.append("    PUSH {R6}")

            node.tip = node.children[0].tip
            node.l_izraz = 0
            return

        semanticka_greska(node)

    # <izraz>
    if je_nezavrsni(node, "<izraz>"):
        if je_produkcija(node, ["<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            node.l_izraz = node.children[0].l_izraz
            return
        if je_produkcija(node, ["<izraz>", "ZAREZ", "<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            analyze(node.children[2], djelokrug)
            node.tip = node.children[2].tip
            node.l_izraz = 0
            return
        semanticka_greska(node)

    # <slozena_naredba>, oznacava novi djelokrug osim ako je tijelo funkcije
    if je_nezavrsni(node, "<slozena_naredba>"):
        if getattr(node, "je_tijelo_funkcije", False):
            novi = djelokrug  # parametri i tijelo funkcije dijele isti djelokrug
        else:
            novi = Djelokrug(djelokrug)

        for c in node.children:
            analyze(c, novi)
        return

    # <lista_naredbi>
    if je_nezavrsni(node, "<lista_naredbi>"):
        for c in node.children:
            analyze(c, djelokrug)
        return

    # <naredba>
    if je_nezavrsni(node, "<naredba>"):
        for c in node.children:
            analyze(c, djelokrug)
        return

    # <izraz_naredba>
    if je_nezavrsni(node, "<izraz_naredba>"):
        if je_produkcija(node, ["TOCKAZAREZ"]):
            node.tip = T_INT
            return
        if je_produkcija(node, ["<izraz>", "TOCKAZAREZ"]):
            analyze(node.children[0], djelokrug)
            node.tip = node.children[0].tip
            return
        semanticka_greska(node)

    # <naredba_grananja>
    if je_nezavrsni(node, "<naredba_grananja>"):
        if je_produkcija(node, ["KR_IF", "L_ZAGRADA", "<izraz>", "D_ZAGRADA", "<naredba>"]):
            analyze(node.children[2], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[2].tip, T_INT):
                semanticka_greska(node)
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ END_IF_{lbl}")
            analyze(node.children[4], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append(f"END_IF_{lbl}:")
            return
        if je_produkcija(node, ["KR_IF", "L_ZAGRADA", "<izraz>", "D_ZAGRADA", "<naredba>", "KR_ELSE", "<naredba>"]):
            analyze(node.children[2], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[2].tip, T_INT):
                semanticka_greska(node)
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ ELSE_{lbl}")
            analyze(node.children[4], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append(f"    B END_IF_{lbl}")
                arm_kod.append(f"ELSE_{lbl}:")
            analyze(node.children[6], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append(f"END_IF_{lbl}:")
            return
        semanticka_greska(node)

    # <naredba_petlje>
    if je_nezavrsni(node, "<naredba_petlje>"):
        if je_produkcija(node, ["KR_WHILE", "L_ZAGRADA", "<izraz>", "D_ZAGRADA", "<naredba>"]):
            lbl = None
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                start_lbl = f"WHILE_{lbl}"
                end_lbl = f"END_WHILE_{lbl}"
                arm_kod.append(f"{start_lbl}:")
                loop_continue.append(start_lbl)
                loop_break.append(end_lbl)

            analyze(node.children[2], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[2].tip, T_INT):
                semanticka_greska(node)

            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ {loop_break[-1]}")

            dubina_petlje += 1
            try:
                analyze(node.children[4], djelokrug)
            finally:
                dubina_petlje -= 1

            if trenutna_funkcija is not None:
                arm_kod.append(f"    B {loop_continue[-1]}")
                arm_kod.append(f"{loop_break[-1]}:")
                loop_continue.pop()
                loop_break.pop()
            return

        if je_produkcija(node, ["KR_FOR", "L_ZAGRADA", "<izraz_naredba>", "<izraz_naredba>", "D_ZAGRADA", "<naredba>"]):
            # init
            analyze(node.children[2], djelokrug)
            if trenutna_funkcija is not None and \
                    je_produkcija(node.children[2], ["<izraz>", "TOCKAZAREZ"]):
                arm_kod.append("    POP {R6}")

            lbl = None
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                start_lbl = f"FOR_{lbl}"
                end_lbl = f"END_FOR_{lbl}"
                arm_kod.append(f"{start_lbl}:")
                loop_continue.append(start_lbl)
                loop_break.append(end_lbl)

            # condition (izraz_naredba)
            analyze(node.children[3], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[3].tip, T_INT):
                semanticka_greska(node)
            if trenutna_funkcija is not None and \
                    je_produkcija(node.children[3], ["<izraz>", "TOCKAZAREZ"]):
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ {loop_break[-1]}")

            dubina_petlje += 1
            try:
                analyze(node.children[5], djelokrug)
            finally:
                dubina_petlje -= 1

            if trenutna_funkcija is not None:
                arm_kod.append(f"    B {loop_continue[-1]}")
                arm_kod.append(f"{loop_break[-1]}:")
                loop_continue.pop()
                loop_break.pop()
            return

        if je_produkcija(node, ["KR_FOR", "L_ZAGRADA", "<izraz_naredba>", "<izraz_naredba>", "<izraz>", "D_ZAGRADA", "<naredba>"]):
            # init
            analyze(node.children[2], djelokrug)
            if trenutna_funkcija is not None and \
                    je_produkcija(node.children[2], ["<izraz>", "TOCKAZAREZ"]):
                arm_kod.append("    POP {R6}")

            lbl = None
            if trenutna_funkcija is not None:
                lbl = len(arm_kod)
                start_lbl = f"FOR_{lbl}"
                inc_lbl = f"FOR_INC_{lbl}"
                end_lbl = f"END_FOR_{lbl}"
                arm_kod.append(f"{start_lbl}:")
                loop_continue.append(inc_lbl)
                loop_break.append(end_lbl)

            # condition (izraz_naredba)
            analyze(node.children[3], djelokrug)
            if not moze_implicitno_pretvoriti(node.children[3].tip, T_INT):
                semanticka_greska(node)
            if trenutna_funkcija is not None and \
                    je_produkcija(node.children[3], ["<izraz>", "TOCKAZAREZ"]):
                arm_kod.append("    POP {R6}")
                arm_kod.append("    CMP R6, #0")
                arm_kod.append(f"    BEQ {loop_break[-1]}")

            dubina_petlje += 1
            try:
                analyze(node.children[6], djelokrug)
            finally:
                dubina_petlje -= 1

            # increment expr
            if trenutna_funkcija is not None:
                arm_kod.append(f"{loop_continue[-1]}:")
            analyze(node.children[4], djelokrug)
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")

            if trenutna_funkcija is not None:
                arm_kod.append(f"    B {start_lbl}")
                arm_kod.append(f"{loop_break[-1]}:")
                loop_continue.pop()
                loop_break.pop()
            return

        semanticka_greska(node)

    # <naredba_skoka>
    if je_nezavrsni(node, "<naredba_skoka>"):
        if je_produkcija(node, ["KR_CONTINUE", "TOCKAZAREZ"]) or \
                je_produkcija(node, ["KR_BREAK", "TOCKAZAREZ"]):
            if dubina_petlje <= 0:
                semanticka_greska(node)
            if trenutna_funkcija is not None:
                if je_produkcija(node, ["KR_CONTINUE", "TOCKAZAREZ"]):
                    arm_kod.append(f"    B {loop_continue[-1]}")
                else:
                    arm_kod.append(f"    B {loop_break[-1]}")
            return

        if je_produkcija(node, ["KR_RETURN", "TOCKAZAREZ"]):
            if not stog_povratnih_tipova:
                semanticka_greska(node)
            pov = stog_povratnih_tipova[-1]
            if pov != T_VOID:
                semanticka_greska(node)
            return

        if je_produkcija(node, ["KR_RETURN", "<izraz>", "TOCKAZAREZ"]):
            if not stog_povratnih_tipova:
                semanticka_greska(node)
            analyze(node.children[1], djelokrug)
            pov = stog_povratnih_tipova[-1]
            if not moze_implicitno_pretvoriti(node.children[1].tip, pov):
                semanticka_greska(node)

            # arm kod za return naredbu
            if trenutna_funkcija is not None:
                arm_kod.append("    POP {R6}")
                arm_kod.append("    MOV SP, R4")
                arm_kod.append("    POP {R4, PC}")
            return

        semanticka_greska(node)

    # <prijevodna_jedinica>
    if je_nezavrsni(node, "<prijevodna_jedinica>"):
        if je_produkcija(node, ["<vanjska_deklaracija>"]):
            analyze(node.children[0], djelokrug)
            return
        if je_produkcija(node, ["<prijevodna_jedinica>", "<vanjska_deklaracija>"]):
            analyze(node.children[0], djelokrug)
            analyze(node.children[1], djelokrug)
            return
        semanticka_greska(node)

    # <vanjska_deklaracija>
    if je_nezavrsni(node, "<vanjska_deklaracija>"):
        analyze(node.children[0], djelokrug)
        return

    # <definicija_funkcije>
    if je_nezavrsni(node, "<definicija_funkcije>"):
        if je_produkcija(node, ["<ime_tipa>", "IDN", "L_ZAGRADA", "KR_VOID", "D_ZAGRADA", "<slozena_naredba>"]):
            analyze(node.children[0], djelokrug)
            ret = node.children[0].tip
            if is_const(ret):
                semanticka_greska(node)
            ime = node.children[1].leksicka_jedinka
            tfun = T_FUNKCIJA([], ret)

            deklarirane_funkcije.add((ime, tfun))
            if djelokrug is not None and djelokrug.parent is None:
                if ime in globalne_funkcije and globalne_funkcije[ime] != tfun:
                    semanticka_greska(node)
                globalne_funkcije[ime] = tfun
            key = (ime, tfun)
            if key in definirane_funkcije:
                semanticka_greska(node)
            definirane_funkcije.add((ime, tfun))

            # definiraj u trenutnom djelokrugu
            djelokrug.deklarirano(Simbol(ime, tfun))

            # novi djelokrug tijela funkcije, zapocni novu funkciju u arm kodu (za sad samo main)
            stog_povratnih_tipova.append(ret)
            if trenutna_funkcija is None:
                trenutna_funkcija = ime
                trenutna_velicina_okvira = 0
                arm_kod.append("")
                arm_kod.append(f"F_{ime.upper()}:")
                arm_kod.append("    PUSH {LR, R4}")
                arm_kod.append("    MOV R4, SP")
            node.children[5].je_tijelo_funkcije = True
            analyze(node.children[5], Djelokrug(djelokrug))
            stog_povratnih_tipova.pop()
            if trenutna_funkcija == ime and ret == T_VOID:
                arm_kod.append("    MOV SP, R4")
                arm_kod.append("    POP {R4, PC}")
            if trenutna_funkcija == ime:
                trenutna_funkcija = None
            return

        if je_produkcija(node, ["<ime_tipa>", "IDN", "L_ZAGRADA", "<lista_parametara>", "D_ZAGRADA", "<slozena_naredba>"]):
            analyze(node.children[0], djelokrug)
            ret = node.children[0].tip
            if is_const(ret):
                semanticka_greska(node)
            ime = node.children[1].leksicka_jedinka

            analyze(node.children[3], djelokrug)
            params = node.children[3].tipovi
            pnames = node.children[3].imena
            tfun = T_FUNKCIJA(params, ret)

            deklarirane_funkcije.add((ime, tfun))
            if djelokrug is not None and djelokrug.parent is None:
                if ime in globalne_funkcije and globalne_funkcije[ime] != tfun:
                    semanticka_greska(node)
                globalne_funkcije[ime] = tfun
            key = (ime, tfun)
            if key in definirane_funkcije:
                semanticka_greska(node)
            definirane_funkcije.add((ime, tfun))

            djelokrug.deklarirano(Simbol(ime, tfun))

            # novi djelokrug funkcije i deklariranje parametara funkcije
            fscope = Djelokrug(djelokrug)
            for nm, tp in zip(pnames, params):
                ps = Simbol(nm, tp)
                ps.is_param = True
                if not fscope.deklarirano(ps):
                    semanticka_greska(node)

            stog_povratnih_tipova.append(ret)
            if trenutna_funkcija is None:
                trenutna_funkcija = ime
                trenutna_velicina_okvira = 0
                arm_kod.append("")
                arm_kod.append(f"F_{ime.upper()}:")
                arm_kod.append("    PUSH {R4, LR}")
                arm_kod.append("    MOV R4, SP")
                # spremi parametre (prva 4 iz registara, ostale sa stoga)
                n = len(pnames)
                for idx, nm in enumerate(pnames):
                    sym = fscope.u_lokalnom_djelokrugu(nm)
                    if sym is None:
                        semanticka_greska(node)
                    trenutna_velicina_okvira += 4
                    sym.offset = -trenutna_velicina_okvira
                    arm_kod.append("    SUB SP, SP, #4")
                    if idx < 4:
                        arm_kod.append(f"    STR R{idx}, [R4, #{sym.offset}]")
                    else:
                        extra_off = 8 + 4 * (n - 1 - idx)
                        arm_kod.append(f"    LDR R6, [R4, #{extra_off}]")
                        arm_kod.append(f"    STR R6, [R4, #{sym.offset}]")
            node.children[5].je_tijelo_funkcije = True
            analyze(node.children[5], fscope)
            stog_povratnih_tipova.pop()
            if trenutna_funkcija == ime and ret == T_VOID:
                arm_kod.append("    MOV SP, R4")
                arm_kod.append("    POP {R4, PC}")
            if trenutna_funkcija == ime:
                trenutna_funkcija = None
            return

        semanticka_greska(node)

    # <lista_parametara>
    if je_nezavrsni(node, "<lista_parametara>"):
        if je_produkcija(node, ["<deklaracija_parametra>"]):
            analyze(node.children[0], djelokrug)
            node.tipovi = [node.children[0].tip]
            node.imena = [node.children[0].ime]
            return
        if je_produkcija(node, ["<lista_parametara>", "ZAREZ", "<deklaracija_parametra>"]):
            analyze(node.children[0], djelokrug)
            analyze(node.children[2], djelokrug)
            if node.children[2].ime in node.children[0].imena:
                semanticka_greska(node)
            node.tipovi = node.children[0].tipovi + [node.children[2].tip]
            node.imena = node.children[0].imena + [node.children[2].ime]
            return
        semanticka_greska(node)

    # <deklaracija_parametra>
    if je_nezavrsni(node, "<deklaracija_parametra>"):
        if je_produkcija(node, ["<ime_tipa>", "IDN"]):
            analyze(node.children[0], djelokrug)
            t = node.children[0].tip
            if t == T_VOID:
                semanticka_greska(node)
            node.tip = t
            node.ime = node.children[1].leksicka_jedinka
            return

        if je_produkcija(node, ["<ime_tipa>", "IDN", "L_UGL_ZAGRADA", "D_UGL_ZAGRADA"]):
            analyze(node.children[0], djelokrug)
            t = node.children[0].tip
            if t == T_VOID:
                semanticka_greska(node)
            node.tip = T_NIZ(t)
            node.ime = node.children[1].leksicka_jedinka
            return

        semanticka_greska(node)

    # <lista_deklaracija>
    if je_nezavrsni(node, "<lista_deklaracija>"):
        for c in node.children:
            analyze(c, djelokrug)
        return

    # <deklaracija>
    if je_nezavrsni(node, "<deklaracija>"):
        if je_produkcija(node, ["<ime_tipa>", "<lista_init_deklaratora>", "TOCKAZAREZ"]):
            analyze(node.children[0], djelokrug)
            t = node.children[0].tip
            node.children[1].inh_tip = t
            analyze(node.children[1], djelokrug)
            return
        semanticka_greska(node)

    # <lista_init_deklaratora>
    if je_nezavrsni(node, "<lista_init_deklaratora>"):
        inh = getattr(node, "inh_tip", None)
        if inh is None:
            semanticka_greska(node)

        if je_produkcija(node, ["<init_deklarator>"]):
            node.children[0].inh_tip = inh
            analyze(node.children[0], djelokrug)
            return

        if je_produkcija(node, ["<lista_init_deklaratora>", "ZAREZ", "<init_deklarator>"]):
            node.children[0].inh_tip = inh
            analyze(node.children[0], djelokrug)
            node.children[2].inh_tip = inh
            analyze(node.children[2], djelokrug)
            return

        semanticka_greska(node)

    # <init_deklarator>
    if je_nezavrsni(node, "<init_deklarator>"):
        inh = getattr(node, "inh_tip", None)
        if inh is None:
            semanticka_greska(node)

        if je_produkcija(node, ["<izravni_deklarator>"]):
            node.children[0].inh_tip = inh
            analyze(node.children[0], djelokrug)
            t = node.children[0].tip

            # const(T) i niz(const(T)) moraju biti inicijalizirani
            if is_const(t) or (is_niz(t) and is_const(t[1])):
                semanticka_greska(node)

            node.tip = t
            return

        if je_produkcija(node, ["<izravni_deklarator>", "OP_PRIDRUZI", "<inicijalizator>"]):
            node.children[0].inh_tip = inh
            analyze(node.children[0], djelokrug)
            # za lokalne nizove s inicijalizatorom { ... } generiramo kod po elementu
            local_array = djelokrug is not None and djelokrug.parent is not None and \
                trenutna_funkcija is not None and is_niz(node.children[0].tip)
            if local_array and not je_niz_znakova(node.children[2]):
                prev_nemoj_generirati = nemoj_generirati
                prev_trenutna_funkcija = trenutna_funkcija
                nemoj_generirati = True
                trenutna_funkcija = None
                analyze(node.children[2], djelokrug)
                nemoj_generirati = prev_nemoj_generirati
                trenutna_funkcija = prev_trenutna_funkcija
            else:
                analyze(node.children[2], djelokrug)

            tdecl = node.children[0].tip

            # inicijalizacija broja
            if not is_niz(tdecl):
                if not moze_implicitno_pretvoriti(node.children[2].tip, tdecl):
                    semanticka_greska(node)
            else:
                # inicijalizacija polja
                elem = tdecl[1]

                tipovi = getattr(node.children[2], "tipovi", None)
                if tipovi is None:
                    # inicijalizator nije { ... } niti "string" poseban slucaj
                    semanticka_greska(node)

                if len(tipovi) > getattr(node.children[0], "br_elem", 10**9):
                    semanticka_greska(node)
                for tt in tipovi:
                    if not moze_implicitno_pretvoriti(tt, elem):
                        semanticka_greska(node)

            node.tip = tdecl

            # za generiranje arm koda za globalnu inicijalizaciju: int/char IDN = konstanta;
            if djelokrug is not None and djelokrug.parent is None and tdecl in [T_INT, T_CHAR]:
                name = node.children[0].ime
                val = None
                cur = node.children[2]

                # 1) jednostavan literal (BROJ ili ZNAK)
                tmp = cur
                while tmp is not None and tmp.zavrsni is None and len(tmp.children) == 1:
                    tmp = tmp.children[0]
                if tmp is not None:
                    v0 = parse_const_exp(tmp)
                    if v0 is not None:
                        val = v0

                # 2) unarni operator nad konstantom: +k, -k, ~k, !k
                if val is None:
                    u = cur
                    while u is not None and u.zavrsni is None:
                        if je_produkcija(u, ["<unarni_operator>", "<cast_izraz>"]):
                            op = u.children[0].children[0].zavrsni
                            tmp2 = u.children[1]
                            while tmp2 is not None and tmp2.zavrsni is None and len(tmp2.children) == 1:
                                tmp2 = tmp2.children[0]
                            base = parse_const_exp(tmp2)
                            if base is not None:
                                if op == "OP_PLUS":
                                    val = base
                                elif op == "OP_MINUS" or op == "MINUS":
                                    val = -base
                                elif op == "OP_TILDA":
                                    val = ~base
                                elif op == "OP_NEG":
                                    val = 0 if base else 1
                            break
                        if len(u.children) == 1:
                            u = u.children[0]
                        else:
                            break

                # 3) binarni + između konstanti: k1 + k2
                if val is None:
                    u = cur
                    while u is not None and u.zavrsni is None:
                        if len(u.children) == 3 and u.children[1].zavrsni == "PLUS":
                            l = u.children[0]
                            r = u.children[2]
                            while l is not None and l.zavrsni is None and len(l.children) == 1:
                                l = l.children[0]
                            while r is not None and r.zavrsni is None and len(r.children) == 1:
                                r = r.children[0]
                            lv = parse_const_exp(l) if l is not None else None
                            rv = parse_const_exp(r) if r is not None else None
                            if lv is not None and rv is not None:
                                val = lv + rv
                            break
                        if len(u.children) == 1:
                            u = u.children[0]
                        else:
                            break

                if val is not None:
                    globalne_varijable[name] = val

            if djelokrug is not None and djelokrug.parent is None and is_niz(tdecl) and tdecl[1] in [T_INT, T_CHAR]:
                name = node.children[0].ime
                n = getattr(node.children[0], "br_elem", 0)
                values = [0] * n

                list_node = None
                cur = node.children[2]
                while cur is not None:
                    # string literal inicijalizacija
                    if je_nezavrsni(cur, "<inicijalizator>") and je_niz_znakova(cur):
                        # pronadi NIZ_ZNAKOVA i dekodiraj u niz vrijednosti
                        s = None
                        stack = [cur]
                        while stack:
                            x = stack.pop()
                            if x.zavrsni == "NIZ_ZNAKOVA":
                                s = x.leksicka_jedinka
                                break
                            stack.extend(x.children)
                        if s is not None and len(s) >= 2 and s[0] == '"' and s[-1] == '"':
                            body = s[1:-1]
                            vals = []
                            i = 0
                            while i < len(body):
                                if body[i] == "\\" and i + 1 < len(body):
                                    esc = body[i + 1]
                                    if esc == "t":
                                        vals.append(ord("\t"))
                                    elif esc == "n":
                                        vals.append(ord("\n"))
                                    elif esc == "0":
                                        vals.append(0)
                                    elif esc == "'":
                                        vals.append(ord("'"))
                                    elif esc == '"':
                                        vals.append(ord('"'))
                                    elif esc == "\\":
                                        vals.append(ord("\\"))
                                    else:
                                        vals.append(ord(esc))
                                    i += 2
                                else:
                                    vals.append(ord(body[i]))
                                    i += 1
                            vals.append(0)
                            for i in range(min(len(vals), n)):
                                values[i] = vals[i]
                        globalni_nizovi[name] = values
                        list_node = None
                        break
                    if je_nezavrsni(cur, "<inicijalizator>") and \
                            je_produkcija(cur, ["L_VIT_ZAGRADA", "<lista_izraza_pridruzivanja>", "D_VIT_ZAGRADA"]):
                        list_node = cur.children[1]
                        break
                    if len(cur.children) == 1:
                        cur = cur.children[0]
                    else:
                        break

                if list_node is not None and n > 0:
                    stack = []
                    cur = list_node
                    while cur is not None:
                        if je_produkcija(cur, ["<lista_izraza_pridruzivanja>", "ZAREZ", "<izraz_pridruzivanja>"]):
                            stack.append(cur.children[2])
                            cur = cur.children[0]
                            continue
                        if je_produkcija(cur, ["<izraz_pridruzivanja>"]):
                            stack.append(cur.children[0])
                        break
                    exprs = list(reversed(stack))

                    for i in range(min(len(exprs), n)):
                        expr = exprs[i]
                        val = None

                        tmp = expr
                        while tmp is not None and tmp.zavrsni is None and len(tmp.children) == 1:
                            tmp = tmp.children[0]
                        if tmp is not None:
                            val = parse_const_exp(tmp)

                        if val is None:
                            u = expr
                            while u is not None and u.zavrsni is None:
                                if je_produkcija(u, ["<unarni_operator>", "<cast_izraz>"]):
                                    op = u.children[0].children[0].zavrsni
                                    tmp2 = u.children[1]
                                    while tmp2 is not None and tmp2.zavrsni is None and len(tmp2.children) == 1:
                                        tmp2 = tmp2.children[0]
                                    base = parse_const_exp(tmp2)
                                    if base is not None:
                                        if op == "OP_PLUS":
                                            val = base
                                        elif op == "OP_MINUS" or op == "MINUS":
                                            val = -base
                                        elif op == "OP_TILDA":
                                            val = ~base
                                        elif op == "OP_NEG":
                                            val = 0 if base else 1
                                    break
                                if len(u.children) == 1:
                                    u = u.children[0]
                                else:
                                    break

                        if val is None:
                            b = expr
                            while b is not None and b.zavrsni is None:
                                if len(b.children) == 3 and b.children[1].zavrsni in ["OP_PUTA", "PLUS", "MINUS"]:
                                    op = b.children[1].zavrsni
                                    l = b.children[0]
                                    r = b.children[2]
                                    while l is not None and l.zavrsni is None and len(l.children) == 1:
                                        l = l.children[0]
                                    while r is not None and r.zavrsni is None and len(r.children) == 1:
                                        r = r.children[0]
                                    lv = None
                                    rv = None
                                    if l is not None and l.zavrsni == "BROJ":
                                        lv = int(l.leksicka_jedinka, 0)
                                    if r is not None and r.zavrsni == "BROJ":
                                        rv = int(r.leksicka_jedinka, 0)
                                    if lv is not None and rv is not None:
                                        if op == "OP_PUTA":
                                            val = lv * rv
                                        elif op == "PLUS":
                                            val = lv + rv
                                        elif op == "MINUS":
                                            val = lv - rv
                                    break
                                if len(b.children) == 1:
                                    b = b.children[0]
                                else:
                                    break

                        if val is None:
                            val = 0
                        values[i] = val

                globalni_nizovi[name] = values
            # lokalna inicijalizacija, spremi vrijednost u lokalnu varijablu
            if djelokrug is not None and djelokrug.parent is not None and trenutna_funkcija is not None:
                name = node.children[0].ime
                sym = djelokrug.u_nekom_djelokrugu(name)
                if sym is not None and not getattr(sym, "is_global", False) and sym.offset is not None:
                    if is_niz(sym.tip):
                        # string literal inicijalizator: vrijednosti su vec na stogu
                        if je_niz_znakova(node.children[2]):
                            tipovi = getattr(node.children[2], "tipovi", None)
                            if tipovi is not None:
                                for i in range(len(tipovi) - 1, -1, -1):
                                    arm_kod.append("    POP {R6}")
                                    arm_kod.append(
                                        f"    STR R6, [R4, #{sym.offset + i * 4}]")
                        else:
                            # inicijalizator { ... } s ovisnostima: evaluiraj i spremaj po elementu
                            list_node = None
                            cur = node.children[2]
                            while cur is not None:
                                if je_nezavrsni(cur, "<inicijalizator>") and \
                                        je_produkcija(cur, ["L_VIT_ZAGRADA", "<lista_izraza_pridruzivanja>", "D_VIT_ZAGRADA"]):
                                    list_node = cur.children[1]
                                    break
                                if len(cur.children) == 1:
                                    cur = cur.children[0]
                                else:
                                    break
                            if list_node is not None:
                                stack = []
                                cur = list_node
                                while cur is not None:
                                    if je_produkcija(cur, ["<lista_izraza_pridruzivanja>", "ZAREZ", "<izraz_pridruzivanja>"]):
                                        stack.append(cur.children[2])
                                        cur = cur.children[0]
                                        continue
                                    if je_produkcija(cur, ["<izraz_pridruzivanja>"]):
                                        stack.append(cur.children[0])
                                    break
                                exprs = list(reversed(stack))
                                for i in range(min(len(exprs), getattr(node.children[0], "br_elem", len(exprs)))):
                                    prev_nemoj_generirati = nemoj_generirati
                                    nemoj_generirati = False
                                    analyze(exprs[i], djelokrug)
                                    nemoj_generirati = prev_nemoj_generirati
                                    arm_kod.append("    POP {R6}")
                                    arm_kod.append(
                                        f"    STR R6, [R4, #{sym.offset + i * 4}]")
                    else:
                        arm_kod.append("    POP {R6}")
                        arm_kod.append(f"    STR R6, [R4, #{sym.offset}]")
            return

        semanticka_greska(node)

    # <izravni_deklarator>
    if je_nezavrsni(node, "<izravni_deklarator>"):
        inh = getattr(node, "inh_tip", None)

        if je_produkcija(node, ["IDN"]):
            ime = node.children[0].leksicka_jedinka
            if inh == T_VOID:
                semanticka_greska(node)
            sym = Simbol(ime, inh)
            sym.is_global = djelokrug is not None and djelokrug.parent is None
            if not djelokrug.deklarirano(sym):
                semanticka_greska(node)
            node.tip = inh
            node.ime = ime

            # za arm kod, rezerviraj mjesto za globalne varijable bez inicijalizacije
            if sym.is_global and inh in [T_INT, T_CHAR]:
                if ime not in globalne_varijable:
                    globalne_varijable[ime] = 0

            if sym.is_global and is_niz(inh) and inh[1] in [T_INT, T_CHAR]:
                if ime not in globalni_nizovi:
                    globalni_nizovi[ime] = [0] * getattr(node, "br_elem", 0)
            # rezerviraj mjesto na stogu za lokalne varijable
            if not sym.is_global and trenutna_funkcija is not None and inh in [T_INT, T_CHAR]:
                trenutna_velicina_okvira += 4
                sym.offset = -trenutna_velicina_okvira
                arm_kod.append("    SUB SP, SP, #4")
            return

        if je_produkcija(node, ["IDN", "L_UGL_ZAGRADA", "BROJ", "D_UGL_ZAGRADA"]):
            ime = node.children[0].leksicka_jedinka
            if inh == T_VOID:
                semanticka_greska(node)
            # ogranicenje velicine polja na 1..1024
            try:
                n = int(node.children[2].leksicka_jedinka)
            except:
                semanticka_greska(node)
            if n < 1 or n > 1024:
                semanticka_greska(node)

            tarr = T_NIZ(inh)
            sym = Simbol(ime, tarr)
            sym.is_global = djelokrug is not None and djelokrug.parent is None
            if not djelokrug.deklarirano(sym):
                semanticka_greska(node)

            node.tip = tarr
            node.ime = ime
            node.br_elem = n

            if sym.is_global and inh in [T_INT, T_CHAR]:
                if ime not in globalni_nizovi:
                    globalni_nizovi[ime] = [0] * n
            # rezerviraj mjesto na stogu za lokalni array
            if not sym.is_global and trenutna_funkcija is not None and inh in [T_INT, T_CHAR]:
                trenutna_velicina_okvira += 4 * n
                sym.offset = -trenutna_velicina_okvira
                arm_kod.append(f"    SUB SP, SP, #{4 * n}")
            return

        # deklaracija funkcije bez parametara
        if je_produkcija(node, ["IDN", "L_ZAGRADA", "KR_VOID", "D_ZAGRADA"]):
            ime = node.children[0].leksicka_jedinka
            if inh == T_VOID:
                pass
            tfun = T_FUNKCIJA([], inh)

            # uskladivanje s globalnom tablicom funkcija
            deklarirane_funkcije.add((ime, tfun))
            if djelokrug is not None and djelokrug.parent is None:
                if ime in globalne_funkcije and globalne_funkcije[ime] != tfun:
                    semanticka_greska(node)
                globalne_funkcije[ime] = tfun

            # deklaracija simbola u trenutnom djelokrugu
            prev = djelokrug.u_lokalnom_djelokrugu(ime)
            if prev is not None and prev.tip != tfun:
                semanticka_greska(node)
            djelokrug.deklarirano(Simbol(ime, tfun))

            node.tip = tfun
            node.ime = ime
            return

        # deklaracija funkcije s parametrima
        if je_produkcija(node, ["IDN", "L_ZAGRADA", "<lista_parametara>", "D_ZAGRADA"]):
            ime = node.children[0].leksicka_jedinka
            analyze(node.children[2], djelokrug)
            params = node.children[2].tipovi
            tfun = T_FUNKCIJA(params, inh)

            deklarirane_funkcije.add((ime, tfun))
            if djelokrug is not None and djelokrug.parent is None:
                if ime in globalne_funkcije and globalne_funkcije[ime] != tfun:
                    semanticka_greska(node)
                globalne_funkcije[ime] = tfun

            prev = djelokrug.u_lokalnom_djelokrugu(ime)
            if prev is not None and prev.tip != tfun:
                semanticka_greska(node)
            djelokrug.deklarirano(Simbol(ime, tfun))

            node.tip = tfun
            node.ime = ime
            node.param_imena = node.children[2].imena
            node.param_tipovi = params
            return

        semanticka_greska(node)

    # <inicijalizator>
    if je_nezavrsni(node, "<inicijalizator>"):
        if je_produkcija(node, ["<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)

            if je_niz_znakova(node.children[0]):
                cur = node.children[0]
                while cur.nezavrsni is not None:
                    if cur.nezavrsni == "<primarni_izraz>" and \
                            je_produkcija(cur, ["L_ZAGRADA", "<izraz>", "D_ZAGRADA"]):
                        cur = cur.children[1]
                    elif len(cur.children) == 1:
                        cur = cur.children[0]
                    else:
                        break

                def pronadi_niz_znakova(n):
                    if n.zavrsni == "NIZ_ZNAKOVA":
                        return n
                    for ch in n.children:
                        r = pronadi_niz_znakova(ch)
                        if r:
                            return r
                    return None

                tnode = pronadi_niz_znakova(node.children[0])
                if tnode is None:
                    semanticka_greska(node)

                L = duljina_niza_znakova(tnode.leksicka_jedinka) + 1
                node.br_elem = L
                node.tipovi = [T_CHAR] * L
                node.tip = None

                # arm kod za inicijalizaciju lokalnog niza iz string literal
                if trenutna_funkcija is not None and not nemoj_generirati:
                    s = tnode.leksicka_jedinka
                    body = s[1:-
                             1] if len(s) >= 2 and s[0] == '"' and s[-1] == '"' else ""
                    vals = []
                    i = 0
                    while i < len(body):
                        if body[i] == "\\" and i + 1 < len(body):
                            esc = body[i + 1]
                            if esc == "t":
                                vals.append(ord("\t"))
                            elif esc == "n":
                                vals.append(ord("\n"))
                            elif esc == "0":
                                vals.append(0)
                            elif esc == "'":
                                vals.append(ord("'"))
                            elif esc == '"':
                                vals.append(ord('"'))
                            elif esc == "\\":
                                vals.append(ord("\\"))
                            else:
                                vals.append(ord(esc))
                            i += 2
                        else:
                            vals.append(ord(body[i]))
                            i += 1
                    vals.append(0)
                    for v in vals:
                        arm_kod.append(f"    MOV R6, #{v}")
                        arm_kod.append("    PUSH {R6}")
                return

            node.tip = node.children[0].tip
            return

        if je_produkcija(node, ["L_VIT_ZAGRADA", "<lista_izraza_pridruzivanja>", "D_VIT_ZAGRADA"]):
            analyze(node.children[1], djelokrug)
            node.br_elem = node.children[1].br_elem
            node.tipovi = node.children[1].tipovi
            node.tip = None
            return

        semanticka_greska(node)

    # <lista_izraza_pridruzivanja>
    if je_nezavrsni(node, "<lista_izraza_pridruzivanja>"):

        if je_produkcija(node, ["<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            node.tipovi = [node.children[0].tip]
            node.br_elem = 1
            return

        if je_produkcija(node, ["<lista_izraza_pridruzivanja>", "ZAREZ", "<izraz_pridruzivanja>"]):
            analyze(node.children[0], djelokrug)
            analyze(node.children[2], djelokrug)
            node.tipovi = node.children[0].tipovi + [node.children[2].tip]
            node.br_elem = node.children[0].br_elem + 1
            return

        semanticka_greska(node)


def main():
    data = sys.stdin.read().splitlines()
    root = parse_input(data)

    arm_kod.append(".text")
    arm_kod.append(".global _start")
    arm_kod.append("")
    arm_kod.append("_start:")
    arm_kod.append("    LDR SP, =0x20000")
    arm_kod.append("    BL F_MAIN")
    arm_kod.append("    MOV R0, R6")
    arm_kod.append("    SWI 0")

    globalni_djelokrug = Djelokrug(None)
    analyze(root, globalni_djelokrug)

    # provjera da li postoji main kao funkcija(void -> int)
    if "main" not in globalne_funkcije or globalne_funkcije["main"] != T_FUNKCIJA([], T_INT):
        print("main")
        return

    # provjera je li svaka deklarirana funkcija definirana
    for key in deklarirane_funkcije:
        if key not in definirane_funkcije:
            print("funkcija")
            return

    # pisanje globalnih definicja varijabli na kraj arm koda
    if globalne_varijable or globalni_nizovi:
        arm_kod.append("")
        arm_kod.append(".data")
        for name, val in globalne_varijable.items():
            arm_kod.append(f"{name}: .word {val}")
        for name, vals in globalni_nizovi.items():
            if not vals:
                arm_kod.append(f"{name}: .word 0")
            else:
                arm_kod.append(f"{name}: .word " +
                               ", ".join(str(v) for v in vals))

    with open("a.s", "w") as f:
        f.write("\n".join(arm_kod) + "\n")


if __name__ == "__main__":
    main()