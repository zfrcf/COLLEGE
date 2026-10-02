#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur du projet Scratch « Royale 3D » : un jeu de tir multijoueur en 3D
(raycasting au stylo) synchronisé par variables cloud, inspiré de Fortnite.

Usage :  python3 generer_projet.py   →  produit « Royale 3D.sb3 » à côté du script.

Le script contient un petit DSL Python qui décrit les scripts Scratch, puis
sérialise le tout au format project.json (Scratch 3) dans une archive .sb3.
"""
import hashlib
import json
import math
import os
import random
import zipfile

ICI = os.path.dirname(os.path.abspath(__file__))
SORTIE = os.path.join(ICI, "Royale 3D.sb3")

# ---------------------------------------------------------------------------
#  Constantes du jeu
# ---------------------------------------------------------------------------
NB_JOUEURS = 6          # emplacements réseau (6 variables cloud ☁ J1..☁ J6)
TAILLE = 24             # carte TAILLE x TAILLE cases
COLONNES = 80           # colonnes de rendu 3D (480 px / 6 px)
LARGEUR_COL = 480 / COLONNES
NB_COFFRES = 8
DUREE_ZONE = 150        # secondes avant fermeture totale de la zone
DUREE_MANCHE = 200      # secondes avant nouvelle manche
LONGUEUR_PAQUET = 50    # longueur du paquet réseau (voir CHAMPS)

# Carte ASCII (ligne du haut = y le plus grand). 1 béton, 2 bois (construit),
# 3 brique, 4 métal. '.' = vide.
CARTE_ASCII = [
    "111111111111111111111111",
    "1......................1",
    "1.333.........44.......1",
    "1.3.3.........4........1",
    "1.333...1..............1",
    "1.......1.......222....1",
    "1.......1.......2.2....1",
    "1................2.....1",
    "1....1111..............1",
    "1....1..1.......1......1",
    "1....1..........1......1",
    "1..............33......1",
    "1......1.......3.......1",
    "1......1...............1",
    "1..444.........1111....1",
    "1..4.4.........1..1....1",
    "1..4...........1..1....1",
    "1..........1...........1",
    "1..........1....3333...1",
    "1....22....1....3..3...1",
    "1....2.2...............1",
    "1......................1",
    "1.........11...........1",
    "111111111111111111111111",
]
assert len(CARTE_ASCII) == TAILLE and all(len(l) == TAILLE for l in CARTE_ASCII)

# Coffres (x, y) en cases, placés dans des cellules libres
COFFRES = [(3.5, 20.5), (14.5, 19.5), (12.5, 4.5), (6.5, 13.5),
           (15.5, 10.5), (4.5, 7.5), (16.5, 6.5), (17.5, 3.5)]


def cellule_base(x, y):
    """Valeur de la carte de base en (x, y) entiers."""
    ligne = CARTE_ASCII[TAILLE - 1 - y]
    c = ligne[x]
    return 0 if c == "." else int(c)


for cx, cy in COFFRES:
    assert cellule_base(int(cx), int(cy)) == 0, (cx, cy)

# Paquet réseau : (nom, nb de chiffres). Le préfixe "1" évite la perte des zéros.
CHAMPS = [
    ("x", 4), ("y", 4), ("dir", 3), ("pv", 3), ("bouclier", 3),
    ("battement", 5), ("cible", 1), ("seq", 2), ("degats", 2), ("tueur", 1),
    ("morts", 1), ("arme", 1), ("etat", 1), ("nom", 16), ("elims", 2),
]
POS = {}
_p = 2
for _n, _l in CHAMPS:
    POS[_n] = (_p, _l)
    _p += _l
assert _p - 1 == LONGUEUR_PAQUET, _p

ALPHABET = list("abcdefghijklmnopqrstuvwxyz0123456789_-")

# ---------------------------------------------------------------------------
#  Mini DSL de blocs Scratch
# ---------------------------------------------------------------------------


class Var:
    def __init__(self, nom):
        self.nom = nom


class Lst:
    def __init__(self, nom):
        self.nom = nom


class Arg:
    def __init__(self, nom):
        self.nom = nom


class Node:
    def __init__(self, opcode, inputs=None, fields=None, mutation=None):
        self.opcode = opcode
        self.inputs = inputs or {}     # clé -> (kind, valeur)
        self.fields = fields or {}     # clé -> [valeur, id]
        self.mutation = mutation


# --- reporters ----------------------------------------------------------
def add(a, b): return Node("operator_add", {"NUM1": ("num", a), "NUM2": ("num", b)})
def sub(a, b): return Node("operator_subtract", {"NUM1": ("num", a), "NUM2": ("num", b)})
def mul(a, b): return Node("operator_multiply", {"NUM1": ("num", a), "NUM2": ("num", b)})
def div(a, b): return Node("operator_divide", {"NUM1": ("num", a), "NUM2": ("num", b)})
def mod(a, b): return Node("operator_mod", {"NUM1": ("num", a), "NUM2": ("num", b)})
def rnd(a): return Node("operator_round", {"NUM": ("num", a)})
def mathop(op, a): return Node("operator_mathop", {"NUM": ("num", a)}, {"OPERATOR": [op, None]})
def floor(a): return mathop("floor", a)
def absv(a): return mathop("abs", a)
def sqrt(a): return mathop("sqrt", a)
def sin(a): return mathop("sin", a)
def cos(a): return mathop("cos", a)
def hasard(a, b): return Node("operator_random", {"FROM": ("num", a), "TO": ("num", b)})
def join(a, b): return Node("operator_join", {"STRING1": ("str", a), "STRING2": ("str", b)})
def lettre(i, s): return Node("operator_letter_of", {"LETTER": ("int", i), "STRING": ("str", s)})
def longueur(s): return Node("operator_length", {"STRING": ("str", s)})
def lt(a, b): return Node("operator_lt", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def gt(a, b): return Node("operator_gt", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def eq(a, b): return Node("operator_equals", {"OPERAND1": ("str", a), "OPERAND2": ("str", b)})
def et(a, b): return Node("operator_and", {"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def ou(a, b): return Node("operator_or", {"OPERAND1": ("bool", a), "OPERAND2": ("bool", b)})
def non(a): return Node("operator_not", {"OPERAND": ("bool", a)})
def eq_txt(a, b):
    """Égalité de texte stricte : Scratch compare numériquement deux chaînes de chiffres
    (précision ~17 chiffres), on préfixe donc par un caractère non numérique."""
    return eq(join("#", a), join("#", b))


def ge(a, b): return non(lt(a, b))
def le(a, b): return non(gt(a, b))


def et3(a, b, c): return et(a, et(b, c))
def et4(a, b, c, d): return et(a, et(b, et(c, d)))


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


# --- instructions ---------------------------------------------------------
def setv(v, x): return Node("data_setvariableto", {"VALUE": ("str", x)}, {"VARIABLE": [v, None]})
def changev(v, x): return Node("data_changevariableby", {"VALUE": ("num", x)}, {"VARIABLE": [v, None]})
def remplacer(l, i, x): return Node("data_replaceitemoflist", {"INDEX": ("int", i), "ITEM": ("str", x)}, {"LIST": [l, None]})
def ajouter_liste(l, x): return Node("data_addtolist", {"ITEM": ("str", x)}, {"LIST": [l, None]})
def vider(l): return Node("data_deletealloflist", {}, {"LIST": [l, None]})


def si(cond, alors, sinon=None):
    if sinon is None:
        return Node("control_if", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", alors)})
    return Node("control_if_else", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", alors), "SUBSTACK2": ("stack", sinon)})


def repeter(n, corps): return Node("control_repeat", {"TIMES": ("int", n), "SUBSTACK": ("stack", corps)})
def repeter_jusqua(cond, corps): return Node("control_repeat_until", {"CONDITION": ("bool", cond), "SUBSTACK": ("stack", corps)})
def toujours(corps): return Node("control_forever", {"SUBSTACK": ("stack", corps)})
def attendre(s): return Node("control_wait", {"DURATION": ("num", s)})
def stop_script(): return Node("control_stop", {}, {"STOP_OPTION": ["this script", None]}, {"tagName": "mutation", "children": [], "hasnext": "false"})
def supprimer_clone(): return Node("control_delete_this_clone")
def cloner_moi(): return Node("control_create_clone_of", {"CLONE_OPTION": ("menu", ("control_create_clone_of_menu", "CLONE_OPTION", "_myself_"))})


def aller(x, y): return Node("motion_gotoxy", {"X": ("num", x), "Y": ("num", y)})
def mettre_x(x): return Node("motion_setx", {"X": ("num", x)})
def mettre_y(y): return Node("motion_sety", {"Y": ("num", y)})


def stylo_bas(): return Node("pen_penDown")
def stylo_haut(): return Node("pen_penUp")
def effacer(): return Node("pen_clear")
def taille_stylo(s): return Node("pen_setPenSizeTo", {"SIZE": ("num", s)})
def param_stylo(p, v): return Node("pen_setPenColorParamTo", {"COLOR_PARAM": ("menu", ("pen_menu_colorParam", "colorParam", p)), "VALUE": ("num", v)})
def couleur_stylo(hexa): return Node("pen_setPenColorToColor", {"COLOR": ("color", hexa)})


def couleur_hsbt(h, s, b, t=0):
    return [param_stylo("color", h), param_stylo("saturation", s),
            param_stylo("brightness", b), param_stylo("transparency", t)]


def ligne(x1, y1, x2, y2):
    return [stylo_haut(), aller(x1, y1), stylo_bas(), aller(x2, y2), stylo_haut()]


def montrer(): return Node("looks_show")
def cacher(): return Node("looks_hide")
def taille(s): return Node("looks_setsizeto", {"SIZE": ("num", s)})
def effet(nom, v): return Node("looks_seteffectto", {"VALUE": ("num", v)}, {"EFFECT": [nom, None]})
def dire(m): return Node("looks_say", {"MESSAGE": ("str", m)})
def costume(c): return Node("looks_switchcostumeto", {"COSTUME": ("menu", ("looks_costume", "COSTUME", c))})
def premier_plan(): return Node("looks_gotofrontback", {}, {"FRONT_BACK": ["front", None]})
def arriere_plan(): return Node("looks_gotofrontback", {}, {"FRONT_BACK": ["back", None]})


def diffuser(nom): return Node("event_broadcast", {"BROADCAST_INPUT": ("broadcast", nom)})
def diffuser_attendre(nom): return Node("event_broadcastandwait", {"BROADCAST_INPUT": ("broadcast", nom)})


def appel(nom, *args): return Node("procedures_call", {"__args__": ("args", args)}, mutation={"proccode": nom})


# hats
def quand_drapeau(): return Node("event_whenflagclicked")
def quand_clone(): return Node("control_start_as_clone")
def quand_message(nom): return Node("event_whenbroadcastreceived", {}, {"BROADCAST_OPTION": [nom, None]})


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

    def broadcast_id(self, nom):
        if nom not in self.broadcasts:
            self.broadcasts[nom] = "bc_" + str(len(self.broadcasts) + 1)
        return self.broadcasts[nom]

    def asset_svg(self, svg):
        data = svg.encode("utf-8")
        md5 = hashlib.md5(data).hexdigest()
        self.assets[md5 + ".svg"] = data
        return md5

    def costume(self, nom, svg, cx, cy):
        md5 = self.asset_svg(svg)
        return {"name": nom, "bitmapResolution": 1, "dataFormat": "svg", "assetId": md5,
                "md5ext": md5 + ".svg", "rotationCenterX": cx, "rotationCenterY": cy}

    def to_json(self):
        for t in [self.stage] + self.sprites:
            t.compile()
        targets = [self.stage.to_json(self)] + [s.to_json(self) for s in self.sprites]
        return {"targets": targets, "monitors": self.monitors, "extensions": ["pen"],
                "meta": {"semver": "3.0.0", "vm": "2.3.0", "agent": "generer_projet.py"}}


class Cible:
    def __init__(self, projet, nom, is_stage=False):
        self.projet = projet
        self.nom = nom
        self.is_stage = is_stage
        self.variables = {}   # nom -> (id, valeur, cloud)
        self.lists = {}       # nom -> (id, valeurs)
        self.blocks = {}
        self.costumes = []
        self.scripts = []     # (hat, corps)
        self.procs = {}       # nom -> (args, corps, warp)
        self.visible = True
        self.layer = 0
        self.x = 0
        self.y = 0
        self.size = 100
        self._n = 0
        self._y_script = 0
        if is_stage:
            projet.stage = self
        else:
            projet.sprites.append(self)

    # déclarations
    def var(self, nom, valeur=0, cloud=False):
        pref = "g" if self.is_stage else "l" + str(len(self.projet.sprites))
        self.variables[nom] = (pref + "_v" + str(len(self.variables) + 1), valeur, cloud)

    def liste(self, nom, valeurs=None):
        pref = "g" if self.is_stage else "l" + str(len(self.projet.sprites))
        self.lists[nom] = (pref + "_l" + str(len(self.lists) + 1), list(valeurs or []))

    def script(self, hat, corps):
        self.scripts.append((hat, corps))

    def proc(self, nom, args, corps, warp=True):
        """args : liste de (nom, 'n'|'s'|'b'). nom est le proccode sans les %s."""
        self.procs[nom] = (args, corps, warp)

    # résolution d'identifiants
    def var_id(self, nom):
        if nom in self.variables:
            return self.variables[nom][0]
        st = self.projet.stage
        if nom in st.variables:
            return st.variables[nom][0]
        raise KeyError("variable inconnue : %s (dans %s)" % (nom, self.nom))

    def list_id(self, nom):
        if nom in self.lists:
            return self.lists[nom][0]
        st = self.projet.stage
        if nom in st.lists:
            return st.lists[nom][0]
        raise KeyError("liste inconnue : %s (dans %s)" % (nom, self.nom))

    def nid(self):
        self._n += 1
        return "%s_%d" % ("S" if self.is_stage else "s%d" % self.projet.sprites.index(self), self._n)

    # --- compilation -----------------------------------------------------
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
            if isinstance(choix, str):
                return [1, sid]
            # reporter dans un menu (ex : costume dynamique)
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
        blk = {"opcode": node.opcode, "next": None, "parent": parent_id, "inputs": {}, "fields": {},
               "shadow": False, "topLevel": top}
        self.blocks[bid] = blk
        # champs
        for k, (v, i) in node.fields.items():
            if k == "VARIABLE":
                blk["fields"][k] = [v, self.var_id(v)]
            elif k == "LIST":
                blk["fields"][k] = [v, self.list_id(v)]
            elif k == "BROADCAST_OPTION":
                blk["fields"][k] = [v, self.projet.broadcast_id(v)]
            else:
                blk["fields"][k] = [v, i]
        # appel de bloc personnalisé
        if node.opcode == "procedures_call":
            nom = node.mutation["proccode"]
            args = node.inputs["__args__"][1]
            ids = self.arg_ids(nom)
            types = [t for _, t in self.procs[nom][0]]
            assert len(args) == len(ids), "mauvais nombre d'arguments pour %s" % nom
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
            if isinstance(node, list):
                sub = self.emit_stack(node, prev or parent_id)
                # aplatir : rattacher
                if sub is None:
                    continue
                if prev is None:
                    first = sub
                else:
                    self.blocks[prev]["next"] = sub
                    self.blocks[sub]["parent"] = prev
                # trouver la fin
                cur = sub
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
        x = 0
        for hat, corps in self.scripts:
            hid = self.emit_block(hat, None, top=True)
            self.blocks[hid]["x"] = x
            self.blocks[hid]["y"] = self._y_script
            self._y_script += 600
            first = self.emit_stack(corps, hid)
            if first:
                self.blocks[hid]["next"] = first
        x = 1200
        y = 0
        for nom, (args, corps, warp) in self.procs.items():
            did = self.nid()
            pid = self.nid()
            ids = self.arg_ids(nom)
            self.blocks[did] = {"opcode": "procedures_definition", "next": None, "parent": None,
                                "inputs": {"custom_block": [1, pid]}, "fields": {}, "shadow": False,
                                "topLevel": True, "x": x, "y": y}
            y += 800
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
        d = {
            "isStage": self.is_stage, "name": self.nom,
            "variables": {i: ([n, v, True] if c else [n, v]) for n, (i, v, c) in self.variables.items()},
            "lists": {i: [n, vals] for n, (i, vals) in self.lists.items()},
            "broadcasts": {i: n for n, i in projet.broadcasts.items()} if self.is_stage else {},
            "blocks": self.blocks, "comments": {}, "currentCostume": 0, "costumes": self.costumes,
            "sounds": [], "volume": 100, "layerOrder": self.layer,
        }
        if self.is_stage:
            d.update({"tempo": 60, "videoTransparency": 50, "videoState": "off", "textToSpeechLanguage": None})
        else:
            d.update({"visible": self.visible, "x": self.x, "y": self.y, "size": self.size, "direction": 90,
                      "draggable": False, "rotationStyle": "all around"})
        return d


# ---------------------------------------------------------------------------
#  Costumes SVG
# ---------------------------------------------------------------------------
def svg(w, h, contenu):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (w, h, w, h, contenu))


def svg_vide():
    return svg(4, 4, '<rect x="0" y="0" width="4" height="4" fill="none" stroke="none"/>')


def svg_texte(texte, couleur, taille_police=34, fond=None, sous_titre=None):
    w, h = 340, 100
    s = ""
    if fond:
        s += '<rect x="0" y="0" width="%d" height="%d" rx="14" fill="%s" fill-opacity="0.75"/>' % (w, h, fond)
    s += ('<text x="170" y="%d" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="%d" '
          'fill="%s" stroke="#1a1a2e" stroke-width="2" paint-order="stroke">%s</text>'
          % (50 if sous_titre else 62, taille_police, couleur, texte))
    if sous_titre:
        s += ('<text x="170" y="82" text-anchor="middle" font-family="Sans Serif" font-size="16" '
              'fill="#ffffff" stroke="#1a1a2e" stroke-width="1.5" paint-order="stroke">%s</text>' % sous_titre)
    return svg(w, h, s)


def svg_personnage(couleur_tenue="#3b82f6"):
    # Personnage façon battle royale : tête, torse, sac à dos, jambes (60 x 100)
    return svg(60, 100, """
<rect x="12" y="38" width="36" height="34" rx="6" fill="%s" stroke="#111" stroke-width="2"/>
<rect x="4" y="42" width="10" height="26" rx="3" fill="#6b4f2a" stroke="#111" stroke-width="2"/>
<rect x="46" y="42" width="10" height="26" rx="3" fill="%s" stroke="#111" stroke-width="2"/>
<rect x="16" y="72" width="12" height="26" rx="3" fill="#2a2a3a" stroke="#111" stroke-width="2"/>
<rect x="32" y="72" width="12" height="26" rx="3" fill="#2a2a3a" stroke="#111" stroke-width="2"/>
<circle cx="30" cy="22" r="15" fill="#f1c27d" stroke="#111" stroke-width="2"/>
<path d="M15 20 Q30 0 45 20 Z" fill="#222" />
<rect x="20" y="20" width="20" height="6" rx="3" fill="#111"/>
<rect x="46" y="54" width="14" height="6" rx="2" fill="#444" stroke="#111" stroke-width="1"/>
""" % (couleur_tenue, couleur_tenue))


def svg_coffre():
    return svg(60, 50, """
<rect x="3" y="18" width="54" height="30" rx="4" fill="#b8860b" stroke="#3b2a00" stroke-width="3"/>
<path d="M3 20 Q30 0 57 20 Z" fill="#daa520" stroke="#3b2a00" stroke-width="3"/>
<rect x="3" y="18" width="54" height="6" fill="#8b6508"/>
<rect x="25" y="20" width="10" height="12" rx="2" fill="#ffd700" stroke="#3b2a00" stroke-width="2"/>
<circle cx="30" cy="30" r="2" fill="#3b2a00"/>
""")


def svg_viseur(touche=False):
    c = "#ff3b3b" if touche else "#ffffff"
    extra = ('<path d="M12 12 L22 22 M48 12 L38 22 M12 48 L22 38 M48 48 L38 38" stroke="#ff3b3b" stroke-width="3"/>'
             if touche else "")
    return svg(60, 60, """
<circle cx="30" cy="30" r="2.5" fill="%s"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="%s" stroke-width="3" stroke-linecap="round"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="#000" stroke-opacity="0.4" stroke-width="5" stroke-linecap="round"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="%s" stroke-width="2.5" stroke-linecap="round"/>
%s""" % (c, c, c, extra))


def svg_lunette():
    return svg(480, 360, """
<defs><mask id="m"><rect width="480" height="360" fill="#fff"/><circle cx="240" cy="180" r="150" fill="#000"/></mask></defs>
<rect width="480" height="360" fill="#000" mask="url(#m)"/>
<circle cx="240" cy="180" r="150" fill="none" stroke="#111" stroke-width="8"/>
<path d="M240 30 L240 330 M90 180 L390 180" stroke="#000" stroke-width="2"/>
<circle cx="240" cy="180" r="40" fill="none" stroke="#000" stroke-width="1.5"/>
""")


def svg_arme(type_arme):
    if type_arme == "pistolet":
        corps = """
<rect x="60" y="40" width="110" height="34" rx="8" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="150" y="48" width="60" height="16" rx="4" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="70" y="70" width="34" height="60" rx="6" transform="rotate(12 87 100)" fill="#5a4632" stroke="#111" stroke-width="3"/>
<rect x="104" y="72" width="14" height="22" rx="3" fill="#222"/>
<rect x="90" y="40" width="8" height="40" fill="#1a1a1a"/>"""
    elif type_arme == "pompe":
        corps = """
<rect x="20" y="60" width="90" height="40" rx="10" fill="#6b4a2b" stroke="#111" stroke-width="3"/>
<rect x="100" y="44" width="120" height="32" rx="6" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="140" y="76" width="60" height="22" rx="6" fill="#8a5c33" stroke="#111" stroke-width="3"/>
<rect x="200" y="50" width="40" height="18" rx="4" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="110" y="96" width="16" height="22" rx="3" fill="#222"/>"""
    else:
        corps = """
<rect x="10" y="66" width="100" height="36" rx="10" fill="#3a5a2a" stroke="#111" stroke-width="3"/>
<rect x="100" y="52" width="150" height="26" rx="6" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="110" y="30" width="80" height="20" rx="8" fill="#222" stroke="#111" stroke-width="3"/>
<circle cx="112" cy="40" r="8" fill="#66ccff" stroke="#111" stroke-width="2"/>
<rect x="250" y="56" width="20" height="18" rx="3" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="118" y="92" width="14" height="24" rx="3" fill="#222"/>
<rect x="150" y="80" width="18" height="34" rx="3" fill="#1a1a1a"/>"""
    main = '<ellipse cx="80" cy="120" rx="34" ry="24" fill="#f1c27d" stroke="#111" stroke-width="3"/>'
    return svg(280, 150, corps + main)


def svg_flash():
    return svg(80, 80, """
<polygon points="40,4 48,28 72,20 56,40 76,52 50,50 46,76 36,52 10,62 26,42 6,30 32,30" fill="#ffd166" stroke="#ff8800" stroke-width="2"/>
<circle cx="40" cy="40" r="10" fill="#fff6c4"/>""")


def svg_plein(couleur):
    return svg(480, 360, '<rect width="480" height="360" fill="%s"/>' % couleur)


def svg_scene():
    return svg(480, 360, '<rect width="480" height="360" fill="#0b1021"/>')


# ---------------------------------------------------------------------------
#  Construction du projet
# ---------------------------------------------------------------------------
def construire_projet():
    P = Projet()
    stage = Cible(P, "Stage", is_stage=True)
    stage.costumes = [P.costume("scène", svg_scene(), 240, 180)]

    # ---- variables cloud -------------------------------------------------
    for k in range(1, NB_JOUEURS + 1):
        stage.var("☁ J%d" % k, 0, cloud=True)
    stage.var("☁ Construction", 0, cloud=True)
    stage.var("☁ Partie", 0, cloud=True)

    # ---- variables HUD (moniteurs) ----------------------------------------
    HUD = ["❤ PV", "🛡 Bouclier", "🔫 Munitions", "🧱 Matériaux", "💀 Éliminations", "⏱ Zone", "👥 Joueurs", "🎯 Arme"]
    for v in HUD:
        stage.var(v, 0)

    # ---- état partagé ----------------------------------------------------
    for v in ["px", "py", "dir", "hauteur", "horizon", "plan", "monSlot", "zoneX", "zoneY", "zoneR", "horsZone",
              "etat", "maintenant", "message", "flash", "tirAnim", "armeNum", "rechargeFin", "toucheFin",
              "paquet", "_ext", "_pad", "_i", "nomCode", "debut", "tempsManche", "rang", "finManche"]:
        stage.var(v, 0)

    # ---- listes globales --------------------------------------------------
    carte = [cellule_base(x, y) for y in range(TAILLE) for x in range(TAILLE)]
    stage.liste("Carte", carte)
    stage.liste("CarteBase", carte)
    stage.liste("Profondeur", [30] * COLONNES)
    stage.liste("Alphabet", ALPHABET)
    for l in ["E_x", "E_y", "E_dir", "E_pv", "E_bouclier", "E_battement", "E_cible", "E_seq", "E_degats", "E_tueur",
              "E_morts", "E_arme", "E_etat", "E_nom", "E_elims", "E_actif", "E_paquet", "E_dernierSeq", "E_dernierMorts"]:
        stage.liste(l, [0] * NB_JOUEURS)
    stage.liste("ArmeNoms", ["Pistolet", "Fusil à pompe", "Sniper"])
    stage.liste("ArmeDegats", [20, 70, 95])
    stage.liste("ArmeCadence", [0.25, 0.9, 1.4])
    stage.liste("ArmePortee", [14, 5, 40])
    stage.liste("ArmeTolerance", [0.45, 0.9, 0.35])
    stage.liste("Chargeurs", [12, 5, 3])
    stage.liste("ChargeursMax", [12, 5, 3])
    stage.liste("CoffresX", [c[0] for c in COFFRES])
    stage.liste("CoffresY", [c[1] for c in COFFRES])
    stage.liste("CoffresPris", [])

    # Moniteurs HUD
    positions = {"❤ PV": (5, 300), "🛡 Bouclier": (5, 330), "🔫 Munitions": (345, 330), "🎯 Arme": (345, 300),
                 "🧱 Matériaux": (345, 270), "💀 Éliminations": (360, 5), "👥 Joueurs": (360, 32), "⏱ Zone": (360, 59)}
    for v in HUD:
        vid = stage.variables[v][0]
        x, y = positions[v]
        P.monitors.append({"id": vid, "mode": "default", "opcode": "data_variable", "params": {"VARIABLE": v},
                           "spriteName": None, "value": 0, "width": 0, "height": 0, "x": x, "y": y,
                           "visible": True, "sliderMin": 0, "sliderMax": 100, "isDiscrete": True})

    V = Var
    L = Lst
    A = Arg

    def cellule(x, y):
        return item("Carte", add(mul(floor(y), TAILLE), add(floor(x), 1)))

    def index_cellule(x, y):
        return add(mul(floor(y), TAILLE), add(floor(x), 1))

    def ecart(a, b):
        """Différence signée a - b sur un cadran de 100000 s (tolère les horloges décalées)."""
        return sub(mod(add(sub(a, b), 50000), 100000), 50000)

    # =======================================================================
    #  Sprite Joueur : logique de jeu + réseau
    # =======================================================================
    J = Cible(P, "Joueur")
    J.costumes = [P.costume("vide", svg_vide(), 2, 2)]
    J.visible = False
    J.layer = 9
    for v in ["k", "dx", "dy", "f", "r", "meilleur", "meilleurDist", "cible", "seq", "degats", "tueur", "morts",
              "dernierTireur", "prochainTir", "dernierEnvoye", "dernierEnvoiT", "velY", "respawnT",
              "dernierConstruction", "prochaineConstruction", "prochainDegatZone", "dernierDebut", "cx", "cy",
              "nx", "ny", "ok", "d", "base", "age", "premiere", "n"]:
        J.var(v, 0)

    # --- lire / écrire un emplacement cloud ---------------------------------
    J.proc("lire paquet", [("n", "n")],
           [si(eq(A("n"), k), [setv("paquet", V("☁ J%d" % k))]) for k in range(1, NB_JOUEURS + 1)])
    J.proc("ecrire paquet", [("n", "n"), ("valeur", "s")],
           [si(eq(A("n"), k), [setv("☁ J%d" % k, A("valeur"))]) for k in range(1, NB_JOUEURS + 1)])

    # --- utilitaires chaînes -------------------------------------------------
    J.proc("extraire", [("debut", "n"), ("longueur", "n")], [
        setv("_ext", ""), setv("_i", A("debut")),
        repeter(A("longueur"), [setv("_ext", join(V("_ext"), lettre(V("_i"), V("paquet")))), changev("_i", 1)]),
    ])
    J.proc("ajouter", [("valeur", "n"), ("chiffres", "n")], [
        setv("_pad", rnd(A("valeur"))),
        si(lt(V("_pad"), 0), [setv("_pad", 0)]),
        repeter_jusqua(ge(longueur(V("_pad")), A("chiffres")), [setv("_pad", join("0", V("_pad")))]),
        setv("paquet", join(V("paquet"), V("_pad"))),
    ])
    J.proc("maintenant", [], [
        setv("maintenant", mod(floor(mul(jours2000(), 86400)), 100000)),
    ])

    # --- encodage de mon paquet -------------------------------------------
    J.proc("encoder", [], [
        setv("paquet", "1"),
        appel("ajouter", rnd(mul(V("px"), 100)), 4),
        appel("ajouter", rnd(mul(V("py"), 100)), 4),
        appel("ajouter", mod(rnd(V("dir")), 360), 3),
        appel("ajouter", V("❤ PV"), 3),
        appel("ajouter", V("🛡 Bouclier"), 3),
        appel("ajouter", V("maintenant"), 5),
        appel("ajouter", V("cible"), 1),
        appel("ajouter", V("seq"), 2),
        appel("ajouter", V("degats"), 2),
        appel("ajouter", V("tueur"), 1),
        appel("ajouter", V("morts"), 1),
        appel("ajouter", V("armeNum"), 1),
        appel("ajouter", V("etat"), 1),
        setv("paquet", join(V("paquet"), V("nomCode"))),
        appel("ajouter", mod(V("💀 Éliminations"), 100), 2),
    ])
    J.proc("envoyer", [("force", "n")], [
        appel("encoder"),
        si(et(non(eq_txt(V("paquet"), V("dernierEnvoye"))),
              ou(eq(A("force"), 1), gt(sub(chrono(), V("dernierEnvoiT")), 0.1))), [
            appel("ecrire paquet", V("monSlot"), V("paquet")),
            setv("dernierEnvoye", V("paquet")),
            setv("dernierEnvoiT", chrono()),
        ]),
    ])

    # --- nom du joueur → code numérique ----------------------------------
    J.proc("coder nom", [], [
        setv("nomCode", ""), setv("_i", 1),
        repeter(8, [
            setv("_pad", num_item("Alphabet", lettre(V("_i"), pseudo()))),
            si(lt(V("_pad"), 10), [setv("_pad", join("0", V("_pad")))]),
            setv("nomCode", join(V("nomCode"), V("_pad"))),
            changev("_i", 1),
        ]),
    ])

    # --- décodage d'un autre joueur ----------------------------------------
    def ext(nom):
        p, l = POS[nom]
        return appel("extraire", p, l)

    J.proc("decoder", [("n", "n")], [
        appel("lire paquet", A("n")),
        si(non(eq_txt(V("paquet"), item("E_paquet", A("n")))), [
            setv("premiere", 0),
            si(eq(item("E_paquet", A("n")), 0), [setv("premiere", 1)]),
            si(lt(longueur(V("paquet")), LONGUEUR_PAQUET), [
                remplacer("E_paquet", A("n"), V("paquet")),
                remplacer("E_battement", A("n"), -100000),
            ], [
                ext("x"), remplacer("E_x", A("n"), div(V("_ext"), 100)),
                ext("y"), remplacer("E_y", A("n"), div(V("_ext"), 100)),
                ext("dir"), remplacer("E_dir", A("n"), mul(V("_ext"), 1)),
                ext("pv"), remplacer("E_pv", A("n"), mul(V("_ext"), 1)),
                ext("bouclier"), remplacer("E_bouclier", A("n"), mul(V("_ext"), 1)),
                ext("battement"), remplacer("E_battement", A("n"), mul(V("_ext"), 1)),
                ext("cible"), remplacer("E_cible", A("n"), mul(V("_ext"), 1)),
                ext("seq"), remplacer("E_seq", A("n"), mul(V("_ext"), 1)),
                ext("degats"), remplacer("E_degats", A("n"), mul(V("_ext"), 1)),
                ext("tueur"), remplacer("E_tueur", A("n"), mul(V("_ext"), 1)),
                ext("morts"), remplacer("E_morts", A("n"), mul(V("_ext"), 1)),
                ext("arme"), remplacer("E_arme", A("n"), mul(V("_ext"), 1)),
                ext("etat"), remplacer("E_etat", A("n"), mul(V("_ext"), 1)),
                ext("elims"), remplacer("E_elims", A("n"), mul(V("_ext"), 1)),
                # nom : 8 paires de chiffres
                setv("_pad", ""), setv("_i", POS["nom"][0]),
                repeter(8, [
                    setv("nx", join(lettre(V("_i"), V("paquet")), lettre(add(V("_i"), 1), V("paquet")))),
                    si(gt(V("nx"), 0), [setv("_pad", join(V("_pad"), item("Alphabet", V("nx"))))]),
                    changev("_i", 2),
                ]),
                si(eq(longueur(V("_pad")), 0), [setv("_pad", join("J", A("n")))]),
                remplacer("E_nom", A("n"), V("_pad")),
                # événements
                si(eq(V("premiere"), 1), [
                    remplacer("E_dernierSeq", A("n"), item("E_seq", A("n"))),
                    remplacer("E_dernierMorts", A("n"), item("E_morts", A("n"))),
                ], [
                    si(et(eq(item("E_cible", A("n")), V("monSlot")),
                          non(eq(item("E_seq", A("n")), item("E_dernierSeq", A("n"))))), [
                        remplacer("E_dernierSeq", A("n"), item("E_seq", A("n"))),
                        si(eq(V("etat"), 1), [
                            setv("dernierTireur", A("n")),
                            appel("prendre degats", item("E_degats", A("n"))),
                        ]),
                    ]),
                    si(non(eq(item("E_morts", A("n")), item("E_dernierMorts", A("n")))), [
                        remplacer("E_dernierMorts", A("n"), item("E_morts", A("n"))),
                        si(eq(item("E_tueur", A("n")), V("monSlot")), [
                            changev("💀 Éliminations", 1),
                            setv("message", "elimination"), setv("toucheFin", add(chrono(), 0.3)),
                        ]),
                    ]),
                ]),
                remplacer("E_paquet", A("n"), V("paquet")),
            ]),
        ]),
        # activité (battement de cœur < 15 s)
        setv("age", absv(ecart(V("maintenant"), item("E_battement", A("n"))))),
        si(et(lt(V("age"), 15), ge(longueur(item("E_paquet", A("n"))), LONGUEUR_PAQUET)),
           [remplacer("E_actif", A("n"), 1)], [remplacer("E_actif", A("n"), 0)]),
    ])

    # --- dégâts / mort / réapparition ---------------------------------------
    J.proc("mourir", [("par", "n")], [
        setv("❤ PV", 0), setv("etat", 2), setv("tueur", A("par")),
        setv("morts", mod(add(V("morts"), 1), 10)),
        setv("message", "elimine"), setv("respawnT", add(chrono(), 5)),
        setv("flash", add(chrono(), 0.6)),
        appel("envoyer", 1),
    ])
    J.proc("prendre degats", [("quantite", "n")], [
        setv("n", A("quantite")),
        setv("flash", add(chrono(), 0.35)),
        si(gt(V("🛡 Bouclier"), 0), [
            si(gt(V("n"), V("🛡 Bouclier")), [
                setv("n", sub(V("n"), V("🛡 Bouclier"))), setv("🛡 Bouclier", 0),
            ], [
                changev("🛡 Bouclier", mul(V("n"), -1)), setv("n", 0),
            ]),
        ]),
        changev("❤ PV", mul(V("n"), -1)),
        si(le(V("❤ PV"), 0), [appel("mourir", V("dernierTireur"))]),
    ])
    J.proc("reapparaitre", [], [
        setv("ok", 0),
        repeter(80, [
            si(eq(V("ok"), 0), [
                setv("nx", add(hasard(1, TAILLE - 2), 0.5)), setv("ny", add(hasard(1, TAILLE - 2), 0.5)),
                si(et(eq(cellule(V("nx"), V("ny")), 0),
                      lt(sqrt(add(mul(sub(V("nx"), V("zoneX")), sub(V("nx"), V("zoneX"))),
                                  mul(sub(V("ny"), V("zoneY")), sub(V("ny"), V("zoneY"))))),
                         sub(V("zoneR"), 1))), [setv("ok", 1)]),
            ]),
        ]),
        si(eq(V("ok"), 0), [  # pas trouvé dans la zone : n'importe où de libre
            repeter_jusqua(eq(cellule(V("nx"), V("ny")), 0), [
                setv("nx", add(hasard(1, TAILLE - 2), 0.5)), setv("ny", add(hasard(1, TAILLE - 2), 0.5)),
            ]),
        ]),
        setv("px", V("nx")), setv("py", V("ny")), setv("dir", hasard(0, 359)),
        setv("❤ PV", 100), setv("etat", 1), setv("hauteur", 0), setv("velY", 0), setv("rechargeFin", 0),
        remplacer("Chargeurs", 1, item("ChargeursMax", 1)),
        remplacer("Chargeurs", 2, item("ChargeursMax", 2)),
        remplacer("Chargeurs", 3, item("ChargeursMax", 3)),
    ])

    # --- déplacement avec collisions ---------------------------------------
    J.proc("deplacer", [("dx", "n"), ("dy", "n")], [
        setv("nx", add(V("px"), A("dx"))),
        si(et(eq(cellule(add(V("nx"), 0.25), V("py")), 0), eq(cellule(sub(V("nx"), 0.25), V("py")), 0)),
           [setv("px", V("nx"))]),
        setv("ny", add(V("py"), A("dy"))),
        si(et(eq(cellule(V("px"), add(V("ny"), 0.25)), 0), eq(cellule(V("px"), sub(V("ny"), 0.25)), 0)),
           [setv("py", V("ny"))]),
    ])

    # --- tir ----------------------------------------------------------------
    J.proc("tirer", [], [
        remplacer("Chargeurs", V("armeNum"), sub(item("Chargeurs", V("armeNum")), 1)),
        setv("prochainTir", add(chrono(), item("ArmeCadence", V("armeNum")))),
        setv("tirAnim", 4),
        setv("meilleur", 0), setv("meilleurDist", item("ArmePortee", V("armeNum"))),
        setv("k", 1),
        repeter(NB_JOUEURS, [
            si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_etat", V("k")), 1)), [
                setv("dx", sub(item("E_x", V("k")), V("px"))),
                setv("dy", sub(item("E_y", V("k")), V("py"))),
                setv("f", add(mul(V("dx"), cos(V("dir"))), mul(V("dy"), sin(V("dir"))))),
                setv("r", sub(mul(V("dx"), sin(V("dir"))), mul(V("dy"), cos(V("dir"))))),
                si(et4(gt(V("f"), 0.3), lt(V("f"), V("meilleurDist")),
                       lt(absv(V("r")), item("ArmeTolerance", V("armeNum"))),
                       gt(item("Profondeur", COLONNES // 2), sub(V("f"), 0.3))), [
                    setv("meilleur", V("k")), setv("meilleurDist", V("f")),
                ]),
            ]),
            changev("k", 1),
        ]),
        si(gt(V("meilleur"), 0), [
            setv("cible", V("meilleur")),
            setv("seq", mod(add(V("seq"), 1), 100)),
            setv("degats", item("ArmeDegats", V("armeNum"))),
            si(eq(V("armeNum"), 2), [
                setv("degats", rnd(mul(V("degats"), sub(1, div(V("meilleurDist"), 6))))),
                si(lt(V("degats"), 10), [setv("degats", 10)]),
            ]),
            setv("toucheFin", add(chrono(), 0.25)),
            appel("envoyer", 1),
        ]),
    ])

    # --- construction -------------------------------------------------------
    J.proc("construire", [], [
        si(ge(V("🧱 Matériaux"), 10), [
            setv("cx", floor(add(V("px"), mul(cos(V("dir")), 1.6)))),
            setv("cy", floor(add(V("py"), mul(sin(V("dir")), 1.6)))),
            si(et3(eq(cellule(V("cx"), V("cy")), 0),
                   non(et(eq(V("cx"), floor(V("px"))), eq(V("cy"), floor(V("py"))))),
                   lt(longueur(V("☁ Construction")), 250)), [
                remplacer("Carte", index_cellule(V("cx"), V("cy")), 2),
                changev("🧱 Matériaux", -10),
                setv("base", V("☁ Construction")),
                si(lt(longueur(V("base")), 1), [setv("base", "1")]),
                si(eq(V("base"), 0), [setv("base", "1")]),
                setv("_pad", V("cx")), si(lt(V("_pad"), 10), [setv("_pad", join("0", V("_pad")))]),
                setv("base", join(V("base"), V("_pad"))),
                setv("_pad", V("cy")), si(lt(V("_pad"), 10), [setv("_pad", join("0", V("_pad")))]),
                setv("base", join(V("base"), V("_pad"))),
                setv("☁ Construction", V("base")),
                setv("dernierConstruction", V("base")),
            ]),
        ]),
    ])
    J.proc("copier carte", [], [
        setv("_i", 1),
        repeter(TAILLE * TAILLE, [remplacer("Carte", V("_i"), item("CarteBase", V("_i"))), changev("_i", 1)]),
    ])
    J.proc("synchroniser construction", [], [
        si(non(eq_txt(V("☁ Construction"), V("dernierConstruction"))), [
            si(lt(longueur(V("☁ Construction")), longueur(V("dernierConstruction"))), [appel("copier carte")]),
            setv("_i", 2),
            repeter(floor(div(sub(longueur(V("☁ Construction")), 1), 4)), [
                setv("cx", join(lettre(V("_i"), V("☁ Construction")), lettre(add(V("_i"), 1), V("☁ Construction")))),
                setv("cy", join(lettre(add(V("_i"), 2), V("☁ Construction")), lettre(add(V("_i"), 3), V("☁ Construction")))),
                si(eq(cellule(V("cx"), V("cy")), 0), [remplacer("Carte", index_cellule(V("cx"), V("cy")), 2)]),
                changev("_i", 4),
            ]),
            setv("dernierConstruction", V("☁ Construction")),
        ]),
    ])

    # --- manche / zone -----------------------------------------------------
    J.proc("manche", [], [
        setv("debut", V("☁ Partie")),
        setv("tempsManche", ecart(V("maintenant"), V("debut"))),
        si(ou(eq(V("debut"), 0), ou(gt(V("tempsManche"), DUREE_MANCHE), lt(V("tempsManche"), -5))), [
            setv("☁ Partie", V("maintenant")), setv("☁ Construction", 1),
            setv("debut", V("maintenant")), setv("tempsManche", 0),
        ]),
        si(non(eq(V("debut"), V("dernierDebut"))), [
            setv("dernierDebut", V("debut")),
            setv("zoneX", add(4.5, mod(V("debut"), 15))),
            setv("zoneY", add(4.5, mod(floor(div(V("debut"), 7)), 15))),
            setv("zoneR", 22),
            setv("💀 Éliminations", 0), setv("🧱 Matériaux", 50), setv("🛡 Bouclier", 0),
            setv("finManche", 0), vider("CoffresPris"),
            appel("copier carte"), setv("dernierConstruction", ""),
            appel("reapparaitre"),
            setv("message", "zone"),
        ]),
        si(lt(V("tempsManche"), 40), [setv("zoneR", 22)], [
            si(lt(V("tempsManche"), DUREE_ZONE), [
                setv("zoneR", sub(22, mul(div(sub(V("tempsManche"), 40), DUREE_ZONE - 40), 20))),
            ], [setv("zoneR", 2)]),
        ]),
        setv("⏱ Zone", sub(DUREE_ZONE, V("tempsManche"))),
        si(lt(V("⏱ Zone"), 0), [setv("⏱ Zone", 0)]),
        # fin de manche : classement
        si(et(ge(V("tempsManche"), DUREE_ZONE), eq(V("finManche"), 0)), [
            setv("finManche", 1), setv("rang", 1), setv("k", 1),
            repeter(NB_JOUEURS, [
                si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1),
                       gt(item("E_elims", V("k")), V("💀 Éliminations"))), [changev("rang", 1)]),
                changev("k", 1),
            ]),
            si(eq(V("rang"), 1), [setv("message", "victoire")], [setv("message", "defaite")]),
        ]),
        # tempête
        setv("d", sqrt(add(mul(sub(V("px"), V("zoneX")), sub(V("px"), V("zoneX"))),
                           mul(sub(V("py"), V("zoneY")), sub(V("py"), V("zoneY")))))),
        si(gt(V("d"), V("zoneR")), [setv("horsZone", 1)], [setv("horsZone", 0)]),
        si(et3(eq(V("horsZone"), 1), eq(V("etat"), 1), gt(chrono(), V("prochainDegatZone"))), [
            setv("prochainDegatZone", add(chrono(), 1)),
            si(gt(V("tempsManche"), 120), [changev("❤ PV", -10)], [changev("❤ PV", -5)]),
            setv("flash", add(chrono(), 0.3)),
            si(le(V("❤ PV"), 0), [appel("mourir", 0)]),
        ]),
    ])

    # --- coffres ----------------------------------------------------------
    J.proc("coffres", [], [
        setv("k", 1),
        repeter(NB_COFFRES, [
            si(et3(non(contient("CoffresPris", V("k"))),
                   lt(absv(sub(V("px"), item("CoffresX", V("k")))), 0.6),
                   lt(absv(sub(V("py"), item("CoffresY", V("k")))), 0.6)), [
                ajouter_liste("CoffresPris", V("k")),
                changev("🛡 Bouclier", 50), si(gt(V("🛡 Bouclier"), 100), [setv("🛡 Bouclier", 100)]),
                changev("🧱 Matériaux", 30),
                remplacer("Chargeurs", 1, item("ChargeursMax", 1)),
                remplacer("Chargeurs", 2, item("ChargeursMax", 2)),
                remplacer("Chargeurs", 3, item("ChargeursMax", 3)),
                setv("message", "coffre"),
            ]),
            changev("k", 1),
        ]),
    ])

    # --- entrées clavier/souris --------------------------------------------
    def avance(signe):
        return appel("deplacer", mul(cos(V("dir")), 0.07 * signe), mul(sin(V("dir")), 0.07 * signe))

    def lateral(signe):   # vecteur droite = (sin, -cos)
        return appel("deplacer", mul(sin(V("dir")), 0.06 * signe), mul(cos(V("dir")), -0.06 * signe))

    J.proc("changer arme", [("num", "n")], [
        si(non(eq(V("armeNum"), A("num"))), [
            setv("armeNum", A("num")), setv("rechargeFin", 0),
            setv("🎯 Arme", item("ArmeNoms", V("armeNum"))),
        ]),
    ])
    J.proc("entrees", [], [
        si(eq(V("etat"), 1), [
            si(ou(touche("z"), ou(touche("w"), touche("up arrow"))), [avance(1)]),
            si(ou(touche("s"), touche("down arrow")), [avance(-1)]),
            si(ou(touche("q"), touche("a")), [lateral(-1)]),
            si(touche("d"), [lateral(1)]),
            si(touche("left arrow"), [changev("dir", 3)]),
            si(touche("right arrow"), [changev("dir", -3)]),
            si(et(lt(absv(souris_x()), 241), lt(absv(souris_y()), 181)), [
                si(gt(souris_x(), 90), [changev("dir", div(sub(90, souris_x()), 30))]),
                si(lt(souris_x(), -90), [changev("dir", div(sub(-90, souris_x()), 30))]),
            ]),
            setv("dir", mod(V("dir"), 360)),
            si(et(touche("space"), eq(V("hauteur"), 0)), [setv("velY", 9)]),
            si(touche("1"), [appel("changer arme", 1)]),
            si(touche("2"), [appel("changer arme", 2)]),
            si(touche("3"), [appel("changer arme", 3)]),
            si(et(touche("c"), eq(V("armeNum"), 3)), [setv("plan", 0.22)], [setv("plan", 0.66)]),
            si(et3(touche("r"), eq(V("rechargeFin"), 0),
                   lt(item("Chargeurs", V("armeNum")), item("ChargeursMax", V("armeNum")))), [
                setv("rechargeFin", add(chrono(), 1.5)), setv("message", "recharge"),
            ]),
            si(et(gt(V("rechargeFin"), 0), gt(chrono(), V("rechargeFin"))), [
                remplacer("Chargeurs", V("armeNum"), item("ChargeursMax", V("armeNum"))), setv("rechargeFin", 0),
            ]),
            si(et3(souris_bas(), gt(chrono(), V("prochainTir")), eq(V("rechargeFin"), 0)), [
                si(gt(item("Chargeurs", V("armeNum")), 0), [appel("tirer")], [
                    setv("rechargeFin", add(chrono(), 1.5)), setv("message", "recharge"),
                ]),
            ]),
            si(et(touche("b"), gt(chrono(), V("prochaineConstruction"))), [
                appel("construire"), setv("prochaineConstruction", add(chrono(), 0.3)),
            ]),
            appel("coffres"),
        ], [
            si(gt(chrono(), V("respawnT")), [appel("reapparaitre")]),
        ]),
        # saut (gravité)
        si(ou(gt(V("hauteur"), 0), gt(V("velY"), 0)), [
            changev("hauteur", V("velY")), changev("velY", -0.8),
            si(lt(V("hauteur"), 0), [setv("hauteur", 0), setv("velY", 0)]),
        ]),
        setv("horizon", mul(V("hauteur"), -1)),
        si(gt(V("tirAnim"), 0), [changev("tirAnim", -1)]),
        setv("🔫 Munitions", item("Chargeurs", V("armeNum"))),
    ])

    # --- réseau --------------------------------------------------------------
    J.proc("reseau", [], [
        setv("👥 Joueurs", 1), setv("k", 1),
        repeter(NB_JOUEURS, [
            si(non(eq(V("k"), V("monSlot"))), [
                appel("decoder", V("k")),
                si(eq(item("E_actif", V("k")), 1), [changev("👥 Joueurs", 1)]),
            ]),
            changev("k", 1),
        ]),
        appel("envoyer", 0),
    ])
    J.proc("rejoindre", [], [
        appel("maintenant"), setv("monSlot", 0), setv("k", 1),
        repeter(NB_JOUEURS, [
            si(eq(V("monSlot"), 0), [
                appel("lire paquet", V("k")),
                si(lt(longueur(V("paquet")), LONGUEUR_PAQUET), [setv("monSlot", V("k"))], [
                    appel("extraire", POS["battement"][0], POS["battement"][1]),
                    si(gt(absv(ecart(V("maintenant"), V("_ext"))), 15), [setv("monSlot", V("k"))]),
                ]),
            ]),
            changev("k", 1),
        ]),
    ])
    J.proc("initialiser", [], [
        setv("etat", 2), setv("monSlot", 0), setv("message", "connexion"), setv("plan", 0.66),
        setv("px", TAILLE / 2), setv("py", TAILLE / 2), setv("dir", 0), setv("hauteur", 0), setv("horizon", 0),
        setv("velY", 0), setv("armeNum", 1), setv("🎯 Arme", item("ArmeNoms", 1)),
        setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("🧱 Matériaux", 50), setv("💀 Éliminations", 0),
        setv("👥 Joueurs", 1), setv("⏱ Zone", DUREE_ZONE), setv("zoneX", TAILLE / 2), setv("zoneY", TAILLE / 2),
        setv("zoneR", 22), setv("horsZone", 0), setv("flash", 0), setv("tirAnim", 0), setv("toucheFin", 0),
        setv("rechargeFin", 0), setv("cible", 0), setv("seq", 0), setv("degats", 0), setv("tueur", 0),
        setv("morts", 0), setv("dernierTireur", 0), setv("prochainTir", 0), setv("dernierEnvoye", ""),
        setv("dernierEnvoiT", 0), setv("respawnT", 0), setv("dernierConstruction", ""),
        setv("prochaineConstruction", 0), setv("prochainDegatZone", 0), setv("dernierDebut", -1),
        setv("finManche", 0), setv("rang", 1), vider("CoffresPris"),
        remplacer("Chargeurs", 1, item("ChargeursMax", 1)),
        remplacer("Chargeurs", 2, item("ChargeursMax", 2)),
        remplacer("Chargeurs", 3, item("ChargeursMax", 3)),
        appel("copier carte"),
        setv("_i", 1), repeter(NB_JOUEURS, [
            remplacer("E_paquet", V("_i"), 0), remplacer("E_actif", V("_i"), 0),
            remplacer("E_battement", V("_i"), -100000), remplacer("E_nom", V("_i"), join("J", V("_i"))),
            changev("_i", 1)]),
        appel("coder nom"),
    ])

    J.script(quand_drapeau(), [
        cacher(),
        appel("initialiser"),
        diffuser("demarrer"),
        appel("rejoindre"),
        si(eq(V("monSlot"), 0), [setv("message", "plein"), stop_script()]),
        appel("maintenant"), appel("manche"),
        appel("envoyer", 1),
        setv("message", "zone"),
        toujours([
            appel("maintenant"),
            appel("manche"),
            appel("entrees"),
            appel("synchroniser construction"),
            appel("reseau"),
        ]),
    ])

    # =======================================================================
    #  Sprite Moteur3D : rendu raycasting au stylo
    # =======================================================================
    M = Cible(P, "Moteur3D")
    M.costumes = [P.costume("vide", svg_vide(), 2, 2)]
    M.visible = False
    M.layer = 1
    for v in ["i", "camX", "rayX", "rayY", "mapX", "mapY", "deltaX", "deltaY", "stepX", "stepY", "sideX", "sideY",
              "hit", "side", "perp", "h", "sx", "pas", "a", "b", "c", "disc", "t", "s", "cosD", "sinD",
              "planeX", "planeY", "lum", "ang", "bx", "by", "k", "ox", "oy"]:
        M.var(v, 0)

    OX, OY, ECH = -232, 96, 3.1   # minicarte : origine et échelle (px par case)

    M.proc("ciel et sol", [], [
        effacer(),
        # ciel
        si(eq(V("horsZone"), 1), couleur_hsbt(78, 55, 45), couleur_hsbt(60, 45, 92)),
        taille_stylo(sub(180, V("horizon"))),
        ligne(-250, div(add(180, V("horizon")), 2), 250, div(add(180, V("horizon")), 2)),
        # sol lointain puis proche
        couleur_hsbt(30, 45, 38),
        taille_stylo(add(V("horizon"), 180)),
        ligne(-250, div(sub(V("horizon"), 180), 2), 250, div(sub(V("horizon"), 180), 2)),
        couleur_hsbt(30, 50, 55),
        taille_stylo(div(add(V("horizon"), 180), 2)),
        ligne(-250, sub(V("horizon"), mul(add(V("horizon"), 180), 0.75)), 250, sub(V("horizon"), mul(add(V("horizon"), 180), 0.75))),
    ])

    M.proc("colonne", [], [
        setv("camX", add(div(V("i"), COLONNES / 2), -1 + 1 / COLONNES)),
        setv("rayX", add(V("cosD"), mul(V("planeX"), V("camX")))),
        setv("rayY", add(V("sinD"), mul(V("planeY"), V("camX")))),
        setv("mapX", floor(V("px"))), setv("mapY", floor(V("py"))),
        setv("deltaX", absv(div(1, V("rayX")))), setv("deltaY", absv(div(1, V("rayY")))),
        si(lt(V("rayX"), 0), [setv("stepX", -1), setv("sideX", mul(sub(V("px"), V("mapX")), V("deltaX")))],
           [setv("stepX", 1), setv("sideX", mul(sub(add(V("mapX"), 1), V("px")), V("deltaX")))]),
        si(lt(V("rayY"), 0), [setv("stepY", -1), setv("sideY", mul(sub(V("py"), V("mapY")), V("deltaY")))],
           [setv("stepY", 1), setv("sideY", mul(sub(add(V("mapY"), 1), V("py")), V("deltaY")))]),
        setv("hit", 0), setv("pas", 0),
        repeter_jusqua(ou(gt(V("hit"), 0), gt(V("pas"), 48)), [
            si(lt(V("sideX"), V("sideY")), [
                changev("sideX", V("deltaX")), changev("mapX", V("stepX")), setv("side", 0),
            ], [
                changev("sideY", V("deltaY")), changev("mapY", V("stepY")), setv("side", 1),
            ]),
            setv("hit", item("Carte", add(mul(V("mapY"), TAILLE), add(V("mapX"), 1)))),
            changev("pas", 1),
        ]),
        si(eq(V("side"), 0), [setv("perp", sub(V("sideX"), V("deltaX")))], [setv("perp", sub(V("sideY"), V("deltaY")))]),
        si(lt(V("perp"), 0.05), [setv("perp", 0.05)]),
        remplacer("Profondeur", add(V("i"), 1), V("perp")),
        setv("h", div(320, V("perp"))),
        si(gt(V("h"), 900), [setv("h", 900)]),
        setv("lum", sub(100, mul(V("perp"), 3.2))),
        si(lt(V("lum"), 30), [setv("lum", 30)]),
        si(eq(V("side"), 1), [setv("lum", mul(V("lum"), 0.72))]),
        si(eq(V("hit"), 2), couleur_hsbt(8, 70, V("lum")), [
            si(eq(V("hit"), 3), couleur_hsbt(2, 60, V("lum")), [
                si(eq(V("hit"), 4), couleur_hsbt(58, 45, V("lum")), couleur_hsbt(0, 0, V("lum"))),
            ]),
        ]),
        setv("sx", add(-240 + LARGEUR_COL / 2, mul(V("i"), LARGEUR_COL))),
        ligne(V("sx"), add(V("horizon"), div(V("h"), 2)), V("sx"), sub(V("horizon"), div(V("h"), 2))),
        # mur de tempête (intersection rayon / cercle de zone)
        setv("bx", sub(V("px"), V("zoneX"))), setv("by", sub(V("py"), V("zoneY"))),
        setv("a", add(mul(V("rayX"), V("rayX")), mul(V("rayY"), V("rayY")))),
        setv("b", mul(2, add(mul(V("rayX"), V("bx")), mul(V("rayY"), V("by"))))),
        setv("c", sub(add(mul(V("bx"), V("bx")), mul(V("by"), V("by"))), mul(V("zoneR"), V("zoneR")))),
        setv("disc", sub(mul(V("b"), V("b")), mul(4, mul(V("a"), V("c"))))),
        si(gt(V("disc"), 0), [
            setv("s", sqrt(V("disc"))),
            setv("t", div(sub(mul(V("b"), -1), V("s")), mul(2, V("a")))),
            si(le(V("t"), 0.1), [setv("t", div(add(mul(V("b"), -1), V("s")), mul(2, V("a"))))]),
            si(et(gt(V("t"), 0.1), lt(V("t"), V("perp"))), [
                setv("h", div(320, V("t"))), si(gt(V("h"), 900), [setv("h", 900)]),
                couleur_hsbt(80, 75, 85, 55),
                ligne(V("sx"), add(V("horizon"), div(V("h"), 2)), V("sx"), sub(V("horizon"), div(V("h"), 2))),
            ]),
        ]),
    ])

    def mm_x(x): return add(OX, mul(x, ECH))
    def mm_y(y): return add(OY, mul(y, ECH))

    M.proc("minicarte", [], [
        couleur_hsbt(60, 30, 10, 35), taille_stylo(108),
        ligne(mm_x(TAILLE / 2), mm_y(TAILLE / 2), mm_x(TAILLE / 2), mm_y(TAILLE / 2)),
        # cercle de zone
        si(lt(V("zoneR"), 18), [
            couleur_hsbt(80, 80, 95, 0), taille_stylo(2), setv("ang", 0), stylo_haut(),
            aller(mm_x(add(V("zoneX"), mul(V("zoneR"), cos(0)))), mm_y(add(V("zoneY"), mul(V("zoneR"), sin(0))))),
            stylo_bas(),
            repeter(24, [
                changev("ang", 15),
                aller(mm_x(add(V("zoneX"), mul(V("zoneR"), cos(V("ang"))))),
                      mm_y(add(V("zoneY"), mul(V("zoneR"), sin(V("ang")))))),
            ]),
            stylo_haut(),
        ]),
        # autres joueurs
        couleur_hsbt(0, 90, 100, 0), taille_stylo(5), setv("k", 1),
        repeter(NB_JOUEURS, [
            si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_etat", V("k")), 1)), [
                ligne(mm_x(item("E_x", V("k"))), mm_y(item("E_y", V("k"))), mm_x(item("E_x", V("k"))), mm_y(item("E_y", V("k")))),
            ]),
            changev("k", 1),
        ]),
        # moi + direction
        couleur_hsbt(0, 0, 100, 0), taille_stylo(5),
        ligne(mm_x(V("px")), mm_y(V("py")), mm_x(V("px")), mm_y(V("py"))),
        taille_stylo(2),
        ligne(mm_x(V("px")), mm_y(V("py")), add(mm_x(V("px")), mul(cos(V("dir")), 9)), add(mm_y(V("py")), mul(sin(V("dir")), 9))),
    ])

    M.proc("rendu", [], [
        setv("cosD", cos(V("dir"))), setv("sinD", sin(V("dir"))),
        setv("planeX", mul(V("sinD"), V("plan"))), setv("planeY", mul(V("cosD"), mul(V("plan"), -1))),
        appel("ciel et sol"),
        taille_stylo(LARGEUR_COL + 1),
        setv("i", 0),
        repeter(COLONNES, [appel("colonne"), changev("i", 1)]),
        appel("minicarte"),
    ])
    M.script(quand_drapeau(), [cacher(), aller(0, 0), toujours([appel("rendu")])])

    # =======================================================================
    #  Sprites à panneaux (billboards) : Ennemi et Coffre
    # =======================================================================
    def billboard(cible, ex, ey, taille_num, decal_y, condition, avant=None):
        """Place le sprite comme panneau 3D (ex, ey : position monde)."""
        for v in ["dx", "dy", "f", "r", "sx", "col"]:
            cible.var(v, 0)
        cible.proc("afficher", [], [
            si(condition, [
                setv("dx", sub(ex, V("px"))), setv("dy", sub(ey, V("py"))),
                setv("f", add(mul(V("dx"), cos(V("dir"))), mul(V("dy"), sin(V("dir"))))),
                setv("r", sub(mul(V("dx"), sin(V("dir"))), mul(V("dy"), cos(V("dir"))))),
                si(gt(V("f"), 0.25), [
                    setv("sx", mul(div(div(V("r"), V("f")), V("plan")), 240)),
                    setv("col", add(floor(div(add(V("sx"), 240), LARGEUR_COL)), 1)),
                    si(lt(V("col"), 1), [setv("col", 1)]), si(gt(V("col"), COLONNES), [setv("col", COLONNES)]),
                    si(et(lt(absv(V("sx")), 300), gt(item("Profondeur", V("col")), sub(V("f"), 0.15))), [
                        taille(div(taille_num, V("f"))),
                        aller(V("sx"), sub(V("horizon"), div(decal_y, V("f")))),
                        montrer(),
                    ] + (avant or []), [cacher()]),
                ], [cacher()]),
            ], [cacher()]),
        ])

    E = Cible(P, "Ennemi")
    E.costumes = [P.costume("perso", svg_personnage(), 30, 50)]
    E.visible = False
    E.layer = 2
    E.var("monIndex", 0)
    billboard(E, item("E_x", V("monIndex")), item("E_y", V("monIndex")), 224, 48,
              et3(non(eq(V("monIndex"), V("monSlot"))), eq(item("E_actif", V("monIndex")), 1),
                  eq(item("E_etat", V("monIndex")), 1)),
              avant=[dire(join(item("E_nom", V("monIndex")), join(" ❤", item("E_pv", V("monIndex")))))])
    E.script(quand_drapeau(), [cacher()])
    E.script(quand_message("demarrer"), [
        cacher(), setv("monIndex", 0),
        repeter(NB_JOUEURS, [changev("monIndex", 1), cloner_moi()]),
    ])
    E.script(quand_clone(), [
        effet("COLOR", mul(V("monIndex"), 35)),
        toujours([arriere_plan(), appel("afficher")]),
    ])

    C = Cible(P, "Coffre")
    C.costumes = [P.costume("coffre", svg_coffre(), 30, 25)]
    C.visible = False
    C.layer = 3
    C.var("monIndex", 0)
    billboard(C, item("CoffresX", V("monIndex")), item("CoffresY", V("monIndex")), 300, 85,
              non(contient("CoffresPris", V("monIndex"))))
    C.script(quand_drapeau(), [cacher()])
    C.script(quand_message("demarrer"), [
        cacher(), setv("monIndex", 0),
        repeter(NB_COFFRES, [changev("monIndex", 1), cloner_moi()]),
    ])
    C.script(quand_clone(), [toujours([arriere_plan(), appel("afficher")])])

    # =======================================================================
    #  Overlays : tempête, dégâts, arme, viseur, messages
    # =======================================================================
    T = Cible(P, "Tempête")
    T.costumes = [P.costume("violet", svg_plein("#7c3aed"), 240, 180)]
    T.visible = False
    T.layer = 4
    T.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([si(eq(V("horsZone"), 1), [effet("GHOST", 72), montrer()], [cacher()])]),
    ])

    D = Cible(P, "Dégâts")
    D.costumes = [P.costume("rouge", svg_plein("#ef4444"), 240, 180)]
    D.visible = False
    D.layer = 5
    D.var("g", 0)
    D.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([
            si(gt(V("flash"), chrono()), [
                setv("g", sub(100, mul(sub(V("flash"), chrono()), 180))),
                si(lt(V("g"), 45), [setv("g", 45)]),
                effet("GHOST", V("g")), montrer(),
            ], [
                si(et(lt(V("❤ PV"), 30), eq(V("etat"), 1)), [effet("GHOST", 85), montrer()], [cacher()]),
            ]),
        ]),
    ])

    W = Cible(P, "Arme")
    W.costumes = [P.costume("pistolet", svg_arme("pistolet"), 140, 75),
                  P.costume("pompe", svg_arme("pompe"), 140, 75),
                  P.costume("sniper", svg_arme("sniper"), 140, 75),
                  P.costume("flash", svg_flash(), 40, 40)]
    W.visible = False
    W.layer = 6
    W.script(quand_drapeau(), [
        cacher(), taille(100),
        toujours([
            si(et(eq(V("etat"), 1), gt(V("plan"), 0.5)), [
                costume(V("armeNum")),
                aller(add(130, mul(V("tirAnim"), 4)), add(-105, mul(V("tirAnim"), 6))),
                si(gt(V("rechargeFin"), 0), [mettre_y(-170)]),
                montrer(),
            ], [cacher()]),
        ]),
    ])

    F = Cible(P, "Flash")
    F.costumes = [P.costume("flash", svg_flash(), 40, 40)]
    F.visible = False
    F.layer = 7
    F.script(quand_drapeau(), [
        cacher(), aller(40, -45), taille(120),
        toujours([si(et(gt(V("tirAnim"), 2), gt(V("plan"), 0.5)), [montrer()], [cacher()])]),
    ])

    H = Cible(P, "Viseur")
    H.costumes = [P.costume("viseur", svg_viseur(False), 30, 30),
                  P.costume("touche", svg_viseur(True), 30, 30),
                  P.costume("lunette", svg_lunette(), 240, 180)]
    H.visible = False
    H.layer = 8
    H.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([
            si(eq(V("etat"), 1), [
                si(lt(V("plan"), 0.5), [costume("lunette")], [
                    si(gt(V("toucheFin"), chrono()), [costume("touche")], [costume("viseur")]),
                ]),
                montrer(),
            ], [cacher()]),
        ]),
    ])

    Msg = Cible(P, "Message")
    textes = {
        "vide": None,
        "connexion": ("Connexion au serveur…", "#ffffff", None),
        "plein": ("SERVEUR PLEIN", "#f87171", "Réessaie dans un instant (6 joueurs max)"),
        "elimine": ("ÉLIMINÉ !", "#f87171", "Réapparition dans 5 secondes"),
        "elimination": ("ÉLIMINATION !", "#fbbf24", None),
        "recharge": ("Rechargement…", "#e5e7eb", None),
        "victoire": ("VICTOIRE ROYALE !", "#fbbf24", "Tu termines n°1 de la manche"),
        "defaite": ("MANCHE TERMINÉE", "#e5e7eb", "Prochaine manche dans quelques secondes"),
        "zone": ("NOUVELLE ZONE", "#a78bfa", "Reste dans le cercle et élimine les autres"),
        "coffre": ("COFFRE OUVERT", "#fbbf24", "+50 bouclier, +30 matériaux, munitions"),
    }
    Msg.costumes = [P.costume("vide", svg_vide(), 2, 2)]
    for cle, val in textes.items():
        if val:
            Msg.costumes.append(P.costume(cle, svg_texte(val[0], val[1], 34, "#111827", val[2]), 170, 50))
    Msg.visible = False
    Msg.layer = 10
    Msg.var("dernier", "")
    Msg.var("fin", 0)
    Msg.script(quand_drapeau(), [
        aller(20, 60), cacher(), setv("dernier", ""), setv("fin", 0),
        toujours([
            si(non(eq(V("message"), V("dernier"))), [
                setv("dernier", V("message")),
                si(eq(V("message"), ""), [costume("vide"), cacher()], [
                    costume(V("message")), setv("fin", add(chrono(), 3)), montrer(),
                ]),
                si(ou(eq(V("message"), "plein"), eq(V("message"), "connexion")), [setv("fin", add(chrono(), 9999))]),
            ]),
            si(gt(chrono(), V("fin")), [cacher(), setv("message", ""), setv("dernier", "")]),
        ]),
    ])

    return P


def ecrire_sb3(P, chemin):
    data = P.to_json()
    with zipfile.ZipFile(chemin, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")))
        for nom, contenu in P.assets.items():
            z.writestr(nom, contenu)
    return data


if __name__ == "__main__":
    projet = construire_projet()
    donnees = ecrire_sb3(projet, SORTIE)
    nb_blocs = sum(len(t["blocks"]) for t in donnees["targets"])
    print("Écrit : %s (%d sprites, %d blocs, %d costumes)" % (
        SORTIE, len(donnees["targets"]) - 1, nb_blocs, len(projet.assets)))
