# -*- coding: utf-8 -*-
"""
Mini DSL Python → blocs Scratch 3, et sérialisation au format project.json / .sb3.

Principes :
- Un `Node` décrit un bloc (opcode, entrées, champs). Les reporters et les
  instructions sont tous des `Node`. `Var`, `Lst`, `Arg` désignent une variable,
  une liste ou un argument de bloc personnalisé.
- Une `Cible` (scène ou sprite) accumule des scripts (`script(hat, corps)`) et
  des blocs personnalisés (`proc(nom, args, corps)`), puis `compile()` produit les
  blocs JSON avec identifiants, parents et chaînage.
- `Projet.to_json()` assemble toutes les cibles ; `ecrire_sb3()` zippe le tout
  avec les costumes (SVG) et les sons (WAV).

Toutes les fonctions d'aide portent des noms français et correspondent à un
bloc Scratch précis (voir les commentaires).
"""
import hashlib
import json
import zipfile


class Var:
    """Référence à une variable (locale au sprite ou globale sur la scène)."""
    def __init__(self, nom):
        self.nom = nom


class Lst:
    """Référence à une liste (reporter : contenu joint par des espaces)."""
    def __init__(self, nom):
        self.nom = nom


class Arg:
    """Argument d'un bloc personnalisé (reporter d'argument)."""
    def __init__(self, nom):
        self.nom = nom


class Node:
    def __init__(self, opcode, inputs=None, fields=None, mutation=None):
        self.opcode = opcode
        self.inputs = inputs or {}     # clé -> (kind, valeur)
        self.fields = fields or {}     # clé -> [valeur, id]
        self.mutation = mutation


# ---------------------------------------------------------------------------
#  Reporters : opérateurs
# ---------------------------------------------------------------------------
def add(a, b): return Node("operator_add", {"NUM1": ("num", a), "NUM2": ("num", b)})
def sub(a, b): return Node("operator_subtract", {"NUM1": ("num", a), "NUM2": ("num", b)})
def mul(a, b): return Node("operator_multiply", {"NUM1": ("num", a), "NUM2": ("num", b)})
def div(a, b): return Node("operator_divide", {"NUM1": ("num", a), "NUM2": ("num", b)})
def mod(a, b): return Node("operator_mod", {"NUM1": ("num", a), "NUM2": ("num", b)})
def rnd(a): return Node("operator_round", {"NUM": ("num", a)})
def mathop(op, a): return Node("operator_mathop", {"NUM": ("num", a)}, {"OPERATOR": [op, None]})
def floor(a): return mathop("floor", a)
def plafond(a): return mathop("ceiling", a)
def absv(a): return mathop("abs", a)
def sqrt(a): return mathop("sqrt", a)
def sin(a): return mathop("sin", a)
def cos(a): return mathop("cos", a)
def atan(a): return mathop("atan", a)
def ln(a): return mathop("ln", a)
def hasard(a, b): return Node("operator_random", {"FROM": ("num", a), "TO": ("num", b)})
def join(a, b): return Node("operator_join", {"STRING1": ("str", a), "STRING2": ("str", b)})
def lettre(i, s): return Node("operator_letter_of", {"LETTER": ("int", i), "STRING": ("str", s)})
def longueur(s): return Node("operator_length", {"STRING": ("str", s)})
def contient_texte(s, x): return Node("operator_contains", {"STRING1": ("str", s), "STRING2": ("str", x)})
def lt(a, b): return Node("operator_lt", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def gt(a, b): return Node("operator_gt", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def eq(a, b): return Node("operator_equals", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def et(a, b): return Node("operator_and", {"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def ou(a, b): return Node("operator_or", {"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def non(a): return Node("operator_not", {"OPERAND": ("bool", a)})
def ge(a, b): return non(lt(a, b))
def le(a, b): return non(gt(a, b))


def eq_txt(a, b):
    """Égalité de texte stricte : Scratch compare numériquement deux chaînes de
    chiffres (précision ~17 chiffres) ; on préfixe par un caractère non numérique."""
    return eq(join("#", a), join("#", b))


def et3(a, b, c): return et(a, et(b, c))
def et4(a, b, c, d): return et(a, et(b, et(c, d)))
def ou3(a, b, c): return ou(a, ou(b, c))


def joins(*parties):
    """join(a, join(b, join(c, ...))) pour n morceaux."""
    parties = list(parties)
    if len(parties) == 1:
        return parties[0]
    return join(parties[0], joins(*parties[1:]))


def minimum(a, b):
    """min(a, b) sans variable temporaire : (a + b - |a - b|) / 2."""
    return div(sub(add(a, b), absv(sub(a, b))), 2)


def maximum(a, b):
    return div(add(add(a, b), absv(sub(a, b))), 2)


# ---------------------------------------------------------------------------
#  Reporters : données, capteurs, apparence, mouvement
# ---------------------------------------------------------------------------
def item(l, i): return Node("data_itemoflist", {"INDEX": ("int", i)}, {"LIST": [l, None]})
def num_item(l, x): return Node("data_itemnumoflist", {"ITEM": ("str", x)}, {"LIST": [l, None]})
def long_liste(l): return Node("data_lengthoflist", {}, {"LIST": [l, None]})
def contient(l, x): return Node("data_listcontainsitem", {"ITEM": ("str", x)}, {"LIST": [l, None]})


def touche(k): return Node("sensing_keypressed", {"KEY_OPTION": ("menu", ("sensing_keyoptions", "KEY_OPTION", k))})
def souris_bas(): return Node("sensing_mousedown")
def souris_x(): return Node("sensing_mousex")
def souris_y(): return Node("sensing_mousey")
def chrono(): return Node("sensing_timer")
def jours2000(): return Node("sensing_dayssince2000")
def pseudo(): return Node("sensing_username")
def reponse(): return Node("sensing_answer")
def date_actuelle(quoi): return Node("sensing_current", {}, {"CURRENTMENU": [quoi, None]})   # YEAR MONTH DATE DAYOFWEEK HOUR MINUTE SECOND
def souris_sur_moi(): return Node("sensing_touchingobject", {"TOUCHINGOBJECTMENU": ("menu", ("sensing_touchingobjectmenu", "TOUCHINGOBJECTMENU", "_mouse_"))})


def taille_actuelle(): return Node("looks_size")
def costume_numero(): return Node("looks_costumenumbername", {}, {"NUMBER_NAME": ["number", None]})
def costume_nom(): return Node("looks_costumenumbername", {}, {"NUMBER_NAME": ["name", None]})
def position_x(): return Node("motion_xposition")
def position_y(): return Node("motion_yposition")
def direction_actuelle(): return Node("motion_direction")


# ---------------------------------------------------------------------------
#  Instructions : données
# ---------------------------------------------------------------------------
def setv(v, x): return Node("data_setvariableto", {"VALUE": ("str", x)}, {"VARIABLE": [v, None]})
def changev(v, x): return Node("data_changevariableby", {"VALUE": ("num", x)}, {"VARIABLE": [v, None]})
def montrer_variable(v): return Node("data_showvariable", {}, {"VARIABLE": [v, None]})
def cacher_variable(v): return Node("data_hidevariable", {}, {"VARIABLE": [v, None]})
def remplacer(l, i, x): return Node("data_replaceitemoflist", {"INDEX": ("int", i), "ITEM": ("str", x)}, {"LIST": [l, None]})
def ajouter_liste(l, x): return Node("data_addtolist", {"ITEM": ("str", x)}, {"LIST": [l, None]})
def inserer(l, i, x): return Node("data_insertatlist", {"ITEM": ("str", x), "INDEX": ("int", i)}, {"LIST": [l, None]})
def supprimer(l, i): return Node("data_deleteoflist", {"INDEX": ("int", i)}, {"LIST": [l, None]})
def vider(l): return Node("data_deletealloflist", {}, {"LIST": [l, None]})
def montrer_liste(l): return Node("data_showlist", {}, {"LIST": [l, None]})
def cacher_liste(l): return Node("data_hidelist", {}, {"LIST": [l, None]})


# ---------------------------------------------------------------------------
#  Instructions : contrôle
# ---------------------------------------------------------------------------
def si(cond, alors, sinon=None):
    if sinon is None:
        return Node("control_if", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", alors)})
    return Node("control_if_else", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", alors), "SUBSTACK2": ("stack", sinon)})


def repeter(n, corps): return Node("control_repeat", {"TIMES": ("int", n), "SUBSTACK": ("stack", corps)})
def repeter_jusqua(cond, corps): return Node("control_repeat_until", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", corps)})
def toujours(corps): return Node("control_forever", {"SUBSTACK": ("stack", corps)})
def attendre(s): return Node("control_wait", {"DURATION": ("num", s)})
def attendre_jusqua(cond): return Node("control_wait_until", {"CONDITION": ("bool", cond)})
def stop_script(): return Node("control_stop", {}, {"STOP_OPTION": ["this script", None]}, {"tagName": "mutation", "children": [], "hasnext": "false"})
def stop_tout(): return Node("control_stop", {}, {"STOP_OPTION": ["all", None]}, {"tagName": "mutation", "children": [], "hasnext": "false"})
def stop_autres(): return Node("control_stop", {}, {"STOP_OPTION": ["other scripts in sprite", None]}, {"tagName": "mutation", "children": [], "hasnext": "true"})
def supprimer_clone(): return Node("control_delete_this_clone")
def cloner_moi(): return Node("control_create_clone_of", {"CLONE_OPTION": ("menu", ("control_create_clone_of_menu", "CLONE_OPTION", "_myself_"))})
def cloner(nom): return Node("control_create_clone_of", {"CLONE_OPTION": ("menu", ("control_create_clone_of_menu", "CLONE_OPTION", nom))})


# ---------------------------------------------------------------------------
#  Instructions : mouvement, stylo, apparence, son, événements, capteurs
# ---------------------------------------------------------------------------
def aller(x, y): return Node("motion_gotoxy", {"X": ("num", x), "Y": ("num", y)})
def mettre_x(x): return Node("motion_setx", {"X": ("num", x)})
def mettre_y(y): return Node("motion_sety", {"Y": ("num", y)})
def changer_x(x): return Node("motion_changexby", {"DX": ("num", x)})
def changer_y(y): return Node("motion_changeyby", {"DY": ("num", y)})
def pointer(d): return Node("motion_pointindirection", {"DIRECTION": ("angle", d)})
def tourner(d): return Node("motion_turnright", {"DEGREES": ("num", d)})


def stylo_bas(): return Node("pen_penDown")
def stylo_haut(): return Node("pen_penUp")
def effacer(): return Node("pen_clear")
def tampon(): return Node("pen_stamp")
def taille_stylo(s): return Node("pen_setPenSizeTo", {"SIZE": ("num", s)})
def param_stylo(p, v): return Node("pen_setPenColorParamTo", {"COLOR_PARAM": ("menu", ("pen_menu_colorParam", "colorParam", p)), "VALUE": ("num", v)})
def couleur_stylo(hexa): return Node("pen_setPenColorToColor", {"COLOR": ("color", hexa)})


def couleur_hsbt(h, s, b, t=0):
    """Couleur du stylo par teinte (0-100), saturation, luminosité, transparence."""
    return [param_stylo("color", h), param_stylo("saturation", s),
            param_stylo("brightness", b), param_stylo("transparency", t)]


def ligne(x1, y1, x2, y2):
    return [stylo_haut(), aller(x1, y1), stylo_bas(), aller(x2, y2), stylo_haut()]


def rectangle(x1, y1, x2, y2, epaisseur):
    """Rectangle plein dessiné par bandes horizontales (x1<x2, y1<y2 en px)."""
    return [stylo_haut(), taille_stylo(epaisseur), aller(x1, y1), stylo_bas(), aller(x2, y1), stylo_haut()]


def montrer(): return Node("looks_show")
def cacher(): return Node("looks_hide")
def taille(s): return Node("looks_setsizeto", {"SIZE": ("num", s)})
def changer_taille(s): return Node("looks_changesizeby", {"CHANGE": ("num", s)})
def effet(nom, v): return Node("looks_seteffectto", {"VALUE": ("num", v)}, {"EFFECT": [nom, None]})   # COLOR FISHEYE WHIRL PIXELATE MOSAIC BRIGHTNESS GHOST
def changer_effet(nom, v): return Node("looks_changeeffectby", {"CHANGE": ("num", v)}, {"EFFECT": [nom, None]})
def effacer_effets(): return Node("looks_cleargraphiceffects")
def dire(m): return Node("looks_say", {"MESSAGE": ("str", m)})
def dire_pendant(m, s): return Node("looks_sayforsecs", {"MESSAGE": ("str", m), "SECS": ("num", s)})
def penser(m): return Node("looks_think", {"MESSAGE": ("str", m)})
def costume(c): return Node("looks_switchcostumeto", {"COSTUME": ("menu", ("looks_costume", "COSTUME", c))})
def costume_suivant(): return Node("looks_nextcostume")
def premier_plan(): return Node("looks_gotofrontback", {}, {"FRONT_BACK": ["front", None]})
def arriere_plan(): return Node("looks_gotofrontback", {}, {"FRONT_BACK": ["back", None]})
def avancer_plan(n): return Node("looks_goforwardbackwardlayers", {"NUM": ("int", n)}, {"FORWARD_BACKWARD": ["forward", None]})


def son(nom): return Node("sound_play", {"SOUND_MENU": ("menu", ("sound_sounds_menu", "SOUND_MENU", nom))})
def son_attendre(nom): return Node("sound_playuntildone", {"SOUND_MENU": ("menu", ("sound_sounds_menu", "SOUND_MENU", nom))})
def stop_sons(): return Node("sound_stopallsounds")
def volume(v): return Node("sound_setvolumeto", {"VOLUME": ("num", v)})
def effet_son(nom, v): return Node("sound_seteffectto", {"VALUE": ("num", v)}, {"EFFECT": [nom, None]})   # PITCH PAN


def diffuser(nom): return Node("event_broadcast", {"BROADCAST_INPUT": ("broadcast", nom)})
def diffuser_attendre(nom): return Node("event_broadcastandwait", {"BROADCAST_INPUT": ("broadcast", nom)})
def demander(q): return Node("sensing_askandwait", {"QUESTION": ("str", q)})
def reinitialiser_chrono(): return Node("sensing_resettimer")


def appel(nom, *args): return Node("procedures_call", {"__args__": ("args", args)}, mutation={"proccode": nom})


# chapeaux
def quand_drapeau(): return Node("event_whenflagclicked")
def quand_clone(): return Node("control_start_as_clone")
def quand_message(nom): return Node("event_whenbroadcastreceived", {}, {"BROADCAST_OPTION": [nom, None]})
def quand_touche(k): return Node("event_whenkeypressed", {}, {"KEY_OPTION": [k, None]})
def quand_clique(): return Node("event_whenthisspriteclicked")


# ---------------------------------------------------------------------------
#  Projet / cibles / sérialisation
# ---------------------------------------------------------------------------
PRIMITIFS = {"num": 4, "int": 7, "str": 10, "color": 9, "angle": 8}


class Projet:
    def __init__(self):
        self.stage = None
        self.sprites = []
        self.broadcasts = {}
        self.assets = {}     # md5ext -> bytes
        self.monitors = []
        self._costumes_cache = {}

    def broadcast_id(self, nom):
        if nom not in self.broadcasts:
            self.broadcasts[nom] = "bc_" + str(len(self.broadcasts) + 1)
        return self.broadcasts[nom]

    def asset(self, data, ext):
        md5 = hashlib.md5(data).hexdigest()
        self.assets[md5 + "." + ext] = data
        return md5

    def costume(self, nom, svg, cx, cy):
        """Costume SVG. `cx, cy` = centre de rotation (px depuis le coin haut-gauche)."""
        md5 = self.asset(svg.encode("utf-8"), "svg")
        return {"name": nom, "bitmapResolution": 1, "dataFormat": "svg", "assetId": md5,
                "md5ext": md5 + ".svg", "rotationCenterX": cx, "rotationCenterY": cy}

    def son(self, nom, wav_bytes, rate, sample_count):
        md5 = self.asset(wav_bytes, "wav")
        return {"name": nom, "assetId": md5, "dataFormat": "wav", "format": "", "rate": rate,
                "sampleCount": sample_count, "md5ext": md5 + ".wav"}

    def sprite(self, nom):
        for s in self.sprites:
            if s.nom == nom:
                return s
        raise KeyError("sprite inconnu : " + nom)

    def to_json(self):
        for t in [self.stage] + self.sprites:
            t.compile()
        targets = [self.stage.to_json(self)] + [s.to_json(self) for s in self.sprites]
        return {"targets": targets, "monitors": self.monitors, "extensions": ["pen"],
                "meta": {"semver": "3.0.0", "vm": "2.3.0", "agent": "royale/generer_projet.py"}}


class Cible:
    def __init__(self, projet, nom, is_stage=False):
        self.projet = projet
        self.nom = nom
        self.is_stage = is_stage
        self.variables = {}   # nom -> (id, valeur, cloud)
        self.lists = {}       # nom -> (id, valeurs)
        self.blocks = {}
        self.costumes = []
        self.sounds = []
        self.scripts = []     # (hat, corps)
        self.procs = {}       # nom -> (args, corps, warp)
        self.visible = True
        self.layer = 0
        self.x = 0
        self.y = 0
        self.size = 100
        self.direction = 90
        self.rotation_style = "all around"
        self._n = 0
        self._compiled = False
        if is_stage:
            projet.stage = self
            self.index = -1
        else:
            projet.sprites.append(self)
            self.index = len(projet.sprites) - 1

    # --- déclarations --------------------------------------------------------
    def var(self, nom, valeur=0, cloud=False):
        """Déclare une variable. Idempotent. Refuse une locale qui masquerait une globale."""
        if nom in self.variables:
            return
        if not self.is_stage and self.projet.stage and nom in self.projet.stage.variables:
            raise KeyError("la variable locale « %s » (sprite %s) masquerait la globale du même nom" % (nom, self.nom))
        pref = "g" if self.is_stage else "l%d" % self.index
        self.variables[nom] = (pref + "_v" + str(len(self.variables) + 1), valeur, cloud)

    def liste(self, nom, valeurs=None):
        if nom in self.lists:
            return
        if not self.is_stage and self.projet.stage and nom in self.projet.stage.lists:
            raise KeyError("la liste locale « %s » (sprite %s) masquerait la globale du même nom" % (nom, self.nom))
        pref = "g" if self.is_stage else "l%d" % self.index
        self.lists[nom] = (pref + "_l" + str(len(self.lists) + 1), list(valeurs or []))

    def script(self, hat, corps):
        self.scripts.append((hat, corps))

    def proc(self, nom, args, corps, warp=True):
        """Bloc personnalisé. args : liste de (nom, 'n'|'s'|'b'). warp=True = sans rafraîchissement."""
        if nom in self.procs:
            raise KeyError("bloc personnalisé déjà défini : %s (sprite %s)" % (nom, self.nom))
        self.procs[nom] = (args, corps, warp)

    def costume_svg(self, nom, svg, cx, cy):
        c = self.projet.costume(nom, svg, cx, cy)
        self.costumes.append(c)
        return c

    def son_wav(self, nom, wav_bytes, rate, sample_count):
        self.sounds.append(self.projet.son(nom, wav_bytes, rate, sample_count))

    # --- résolution d'identifiants --------------------------------------------
    def var_id(self, nom):
        if nom in self.variables:
            return self.variables[nom][0]
        st = self.projet.stage
        if nom in st.variables:
            return st.variables[nom][0]
        raise KeyError("variable inconnue : « %s » (dans %s)" % (nom, self.nom))

    def list_id(self, nom):
        if nom in self.lists:
            return self.lists[nom][0]
        st = self.projet.stage
        if nom in st.lists:
            return st.lists[nom][0]
        raise KeyError("liste inconnue : « %s » (dans %s)" % (nom, self.nom))

    def nid(self):
        self._n += 1
        return "%s_%d" % ("S" if self.is_stage else "s%d" % self.index, self._n)

    # --- compilation ------------------------------------------------------------
    def proccode(self, nom):
        args = self.procs[nom][0]
        return nom + "".join(" %b" if t == "b" else " %s" for _, t in args)

    def arg_ids(self, nom):
        h = hashlib.md5(nom.encode("utf-8")).hexdigest()[:8]
        return ["arg_%s_%d" % (h, i) for i in range(len(self.procs[nom][0]))]

    def emit_input(self, kind, val, parent_id):
        if kind == "bool":
            if val is None:
                return None
            bid = self.emit_block(val, parent_id)
            return [2, bid]
        if kind == "stack":
            if not val:
                return None
            first = self.emit_stack(val, parent_id)
            return [2, first] if first else None
        if kind == "menu":
            opcode, field, choix = val
            sid = self.nid()
            self.blocks[sid] = {"opcode": opcode, "next": None, "parent": parent_id, "inputs": {},
                                "fields": {field: [choix, None]}, "shadow": True, "topLevel": False}
            if isinstance(choix, (str, int, float)):
                self.blocks[sid]["fields"][field] = [str(choix), None]
                return [1, sid]
            self.blocks[sid]["fields"][field] = ["", None]
            bid = self.emit_block(choix, parent_id)
            return [3, bid, sid]
        if kind == "broadcast":
            return [1, [11, val, self.projet.broadcast_id(val)]]
        code = PRIMITIFS[kind]
        defaut = "#000000" if kind == "color" else ""
        if isinstance(val, Var):
            return [3, [12, val.nom, self.var_id(val.nom)], [code, defaut]]
        if isinstance(val, Lst):
            return [3, [13, val.nom, self.list_id(val.nom)], [code, defaut]]
        if isinstance(val, (Node, Arg)):
            bid = self.emit_block(val, parent_id)
            return [3, bid, [code, defaut]]
        if isinstance(val, bool):
            val = "true" if val else "false"
        if isinstance(val, float):
            val = repr(val)
        return [1, [code, str(val)]]

    def emit_block(self, node, parent_id, top=False):
        bid = self.nid()
        if isinstance(node, Arg):
            self.blocks[bid] = {"opcode": "argument_reporter_string_number", "next": None, "parent": parent_id,
                                "inputs": {}, "fields": {"VALUE": [node.nom, None]}, "shadow": False, "topLevel": False}
            return bid
        if isinstance(node, Var):
            self.blocks[bid] = {"opcode": "data_variable", "next": None, "parent": parent_id, "inputs": {},
                                "fields": {"VARIABLE": [node.nom, self.var_id(node.nom)]}, "shadow": False, "topLevel": False}
            return bid
        if isinstance(node, Lst):
            self.blocks[bid] = {"opcode": "data_listcontents", "next": None, "parent": parent_id, "inputs": {},
                                "fields": {"LIST": [node.nom, self.list_id(node.nom)]}, "shadow": False, "topLevel": False}
            return bid
        if not isinstance(node, Node):
            raise TypeError("élément de script invalide dans %s : %r" % (self.nom, node))
        blk = {"opcode": node.opcode, "next": None, "parent": parent_id, "inputs": {}, "fields": {},
               "shadow": False, "topLevel": top}
        self.blocks[bid] = blk
        for k, (v, i) in node.fields.items():
            if k == "VARIABLE":
                blk["fields"][k] = [v, self.var_id(v)]
            elif k == "LIST":
                blk["fields"][k] = [v, self.list_id(v)]
            elif k == "BROADCAST_OPTION":
                blk["fields"][k] = [v, self.projet.broadcast_id(v)]
            else:
                blk["fields"][k] = [v, i]
        if node.opcode == "procedures_call":
            nom = node.mutation["proccode"]
            if nom not in self.procs:
                raise KeyError("appel d'un bloc personnalisé inconnu « %s » dans le sprite %s" % (nom, self.nom))
            args = node.inputs["__args__"][1]
            ids = self.arg_ids(nom)
            types = [t for _, t in self.procs[nom][0]]
            if len(args) != len(ids):
                raise ValueError("mauvais nombre d'arguments pour « %s » dans %s : %d attendus, %d donnés"
                                 % (nom, self.nom, len(ids), len(args)))
            for aid, a, t in zip(ids, args, types):
                inp = self.emit_input("bool" if t == "b" else "str", a, bid)
                if inp is not None:
                    blk["inputs"][aid] = inp
            blk["mutation"] = {"tagName": "mutation", "children": [], "proccode": self.proccode(nom),
                               "argumentids": json.dumps(ids), "warp": "true" if self.procs[nom][2] else "false"}
            return bid
        for k, (kind, v) in node.inputs.items():
            inp = self.emit_input(kind, v, bid)
            if inp is not None:
                blk["inputs"][k] = inp
        if node.mutation:
            blk["mutation"] = dict(node.mutation)
        return bid

    def emit_stack(self, corps, parent_id):
        first = None
        prev = None
        for node in corps:
            if node is None:
                continue
            if isinstance(node, (list, tuple)):
                sub_first = self.emit_stack(node, prev or parent_id)
                if sub_first is None:
                    continue
                if prev is None:
                    first = sub_first
                else:
                    self.blocks[prev]["next"] = sub_first
                    self.blocks[sub_first]["parent"] = prev
                cur = sub_first
                while self.blocks[cur]["next"]:
                    cur = self.blocks[cur]["next"]
                prev = cur
                continue
            bid = self.emit_block(node, prev or parent_id)
            if prev is None:
                first = bid
            else:
                self.blocks[prev]["next"] = bid
            prev = bid
        return first

    def compile(self):
        if self._compiled:
            return
        self._compiled = True
        y = 0
        for hat, corps in self.scripts:
            hid = self.emit_block(hat, None, top=True)
            self.blocks[hid]["x"] = 0
            self.blocks[hid]["y"] = y
            y += 600
            first = self.emit_stack(corps, hid)
            if first:
                self.blocks[hid]["next"] = first
        x = 1400
        y = 0
        for nom, (args, corps, warp) in self.procs.items():
            did = self.nid()
            pid = self.nid()
            ids = self.arg_ids(nom)
            self.blocks[did] = {"opcode": "procedures_definition", "next": None, "parent": None,
                                "inputs": {"custom_block": [1, pid]}, "fields": {}, "shadow": False,
                                "topLevel": True, "x": x, "y": y}
            y += 800
            if y > 20000:
                y = 0
                x += 1400
            proto_inputs = {}
            for aid, (an, at) in zip(ids, args):
                rid = self.nid()
                self.blocks[rid] = {"opcode": "argument_reporter_boolean" if at == "b" else "argument_reporter_string_number",
                                    "next": None, "parent": pid, "inputs": {}, "fields": {"VALUE": [an, None]},
                                    "shadow": True, "topLevel": False}
                proto_inputs[aid] = [1, rid]
            self.blocks[pid] = {"opcode": "procedures_prototype", "next": None, "parent": did, "inputs": proto_inputs,
                                "fields": {}, "shadow": True, "topLevel": False,
                                "mutation": {"tagName": "mutation", "children": [], "proccode": self.proccode(nom),
                                             "argumentids": json.dumps(ids),
                                             "argumentnames": json.dumps([a for a, _ in args]),
                                             "argumentdefaults": json.dumps(["false" if t == "b" else "" for _, t in args]),
                                             "warp": "true" if warp else "false"}}
            first = self.emit_stack(corps, did)
            if first:
                self.blocks[did]["next"] = first

    def to_json(self, projet):
        self.compile()
        d = {
            "isStage": self.is_stage, "name": self.nom,
            "variables": {i: ([n, v, True] if c else [n, v]) for n, (i, v, c) in self.variables.items()},
            "lists": {i: [n, vals] for n, (i, vals) in self.lists.items()},
            "broadcasts": {i: n for n, i in projet.broadcasts.items()} if self.is_stage else {},
            "blocks": self.blocks, "comments": {}, "currentCostume": 0, "costumes": self.costumes,
            "sounds": self.sounds, "volume": 100, "layerOrder": self.layer,
        }
        if self.is_stage:
            d.update({"tempo": 60, "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None})
        else:
            d.update({"visible": self.visible, "x": self.x, "y": self.y, "size": self.size,
                      "direction": self.direction, "draggable": False, "rotationStyle": self.rotation_style})
        return d


def ecrire_sb3(projet, chemin):
    data = projet.to_json()
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        for nom, contenu in projet.assets.items():
            z.writestr(nom, contenu)
    return data
