#!/usr/bin/env python3
"""Patch du projet Scratch "Roblox Multiplayer" :
- choix du pseudo au démarrage
- choix clavier AZERTY / QWERTY (+ touche P pour basculer)
- mode admin par code secret (pouvoirs étendus + badge ★)
- chat rapide partagé, couleur de perso partagée, aide, panneau admin, musique, disco, etc.
- interface traduite en français
"""
import json, random, string, hashlib, os, sys, re, shutil

SRC = sys.argv[1]      # dossier sb3 décompressé
OUT = sys.argv[2]      # dossier de sortie (sera zippé ensuite)

shutil.rmtree(OUT, ignore_errors=True)
shutil.copytree(SRC, OUT)
P = json.load(open(os.path.join(OUT, 'project.json')))

ALPH = string.ascii_letters + string.digits + '!#%()*+,-./:;=?@[]^_`{|}~'
random.seed(2026)
def nid():
    return ''.join(random.choice(ALPH) for _ in range(20))

def target(name):
    for t in P['targets']:
        if t['name'] == name:
            return t
    raise KeyError(name)

STAGE = P['targets'][0]
assert STAGE['isStage']

# --------------------------------------------------------------------------
# Variables / listes globales
# --------------------------------------------------------------------------
def var_id(tgt, name):
    for k, v in tgt['variables'].items():
        if v[0] == name:
            return k
    for k, v in STAGE['variables'].items():
        if v[0] == name:
            return k
    raise KeyError('variable ' + name)

def list_id(tgt, name):
    for k, v in tgt['lists'].items():
        if v[0] == name:
            return k
    for k, v in STAGE['lists'].items():
        if v[0] == name:
            return k
    raise KeyError('list ' + name)

def add_var(tgt, name, value):
    i = nid()
    tgt['variables'][i] = [name, value]
    return i

def add_list(tgt, name, items, monitor=True, w=220, h=200, x=5, y=5):
    i = nid()
    tgt['lists'][i] = [name, items]
    if monitor:
        P['monitors'].append({
            'id': i, 'mode': 'list', 'opcode': 'data_listcontents',
            'params': {'LIST': name}, 'spriteName': None if tgt['isStage'] else tgt['name'],
            'value': list(items), 'width': w, 'height': h, 'x': x, 'y': y, 'visible': False})
    return i

for name, val in [
    ('*setup done', '0'), ('Clavier', 'AZERTY'), ('_ADMIN CODE', 'ANTOINE33'),
    ('_ADMIN SCRATCH', ''), ('God Mode', '0'), ('Vitesse', '0'), ('Super Saut', '0'),
    ('Disco Mode', '0'), ('Musique', '1'), ('*chat', '0'), ('chat timer', '0'),
    ('Couleur', '0'), ('Triche', '0'), ('*i', '0'), ('Panneau', '0'), ('Aide visible', '0'),
]:
    add_var(STAGE, name, val)

CHAT_MSGS = ['Salut !', 'GG !', 'Suis-moi !', "A l'aide !", 'mdr', 'Bien joué !',
             'Bienvenue !', 'Checkpoint !', 'Tour terminée ! 🏆', '★ Admin connecté ★']
add_list(STAGE, 'CHAT', CHAT_MSGS, monitor=False)
AIDE = [
    '=== AIDE (C pour masquer) ===',
    'Fleches / ZQSD (AZERTY) / WASD (QWERTY) : bouger',
    'P : basculer AZERTY <-> QWERTY',
    'R : reapparaitre au checkpoint',
    'R + X : recommencer la tour',
    '1 2 3 : emotes',
    '4 a 9 : messages rapides (chat)',
    'T : infos serveur    L : classement',
    'N : afficher / masquer les pseudos',
    'V : couper / remettre la musique',
    'C : cette aide',
]
add_list(STAGE, 'Aide', AIDE, w=330, h=250, x=70, y=40)
PANNEAU = [
    '=== PANNEAU ADMIN (M pour masquer) ===',
    'F : voler        G : flotter',
    'I : invincible   J : vitesse x2',
    'H : super saut   B : mode disco',
    'U : checkpoint suivant',
    'Y : checkpoint precedent',
    '0 : reinitialisation totale',
    '',
]
add_list(STAGE, 'Panneau Admin', PANNEAU, w=300, h=230, x=90, y=60)

# ★ dans la table d'encodage (index 9, auparavant vide) -> badge admin transmis en ligne
CODE = STAGE['lists'][list_id(STAGE, 'CODE')][1]
assert len(CODE) == 50 and '★' not in CODE
CODE.append('★')          # index 51 (2 chiffres : les index 1-9 casseraient l'encodage)
for m in P['monitors']:
    if m['opcode'] == 'data_listcontents' and m['params']['LIST'] == 'CODE':
        m['value'] = list(CODE)

# --------------------------------------------------------------------------
# Mini-constructeur de blocs
# --------------------------------------------------------------------------
class B:
    def __init__(self, tgt):
        self.t = tgt
        self.bl = tgt['blocks']

    # ---- entrées
    def s(self, text):            # texte littéral
        return [1, [10, str(text)]]
    def n(self, num):             # nombre littéral
        return [1, [4, str(num)]]
    def v(self, name):            # variable
        return [3, [12, name, var_id(self.t, name)], [10, '']]
    def r(self, bid):             # reporter (bloc)
        return [3, bid, [10, '']]
    def b(self, bid):             # booléen (bloc)
        return [2, bid]
    def sub(self, first_id):      # substack
        return [2, first_id]

    def mk(self, opcode, inputs=None, fields=None, topLevel=False, x=0, y=0, mutation=None, shadow=False):
        i = nid()
        inputs = dict(inputs or {})
        for k, inp in list(inputs.items()):
            if isinstance(inp, str):          # id de bloc nu -> reporter
                inputs[k] = [3, inp, [10, '']]
        blk = {'opcode': opcode, 'next': None, 'parent': None,
               'inputs': inputs, 'fields': fields or {},
               'shadow': shadow, 'topLevel': topLevel}
        if topLevel:
            blk['x'], blk['y'] = x, y
        if mutation:
            blk['mutation'] = mutation
        self.bl[i] = blk
        for k, inp in blk['inputs'].items():
            if isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str):
                self.bl[inp[1]]['parent'] = i
        return i

    def menu(self, opcode, field, value, parent_inputs=None):
        i = nid()
        self.bl[i] = {'opcode': opcode, 'next': None, 'parent': None, 'inputs': {},
                      'fields': {field: [value, None]}, 'shadow': True, 'topLevel': False}
        return [1, i]

    # ---- reporters / booléens
    def key(self, k):
        return self.mk('sensing_keypressed', {'KEY_OPTION': self.menu('sensing_keyoptions', 'KEY_OPTION', k)})
    def eq(self, a, b):  return self.mk('operator_equals', {'OPERAND1': a, 'OPERAND2': b})
    def gt(self, a, b):  return self.mk('operator_gt', {'OPERAND1': a, 'OPERAND2': b})
    def lt(self, a, b):  return self.mk('operator_lt', {'OPERAND1': a, 'OPERAND2': b})
    def and_(self, a, b): return self.mk('operator_and', {'OPERAND1': self.b(a), 'OPERAND2': self.b(b)})
    def or_(self, a, b):  return self.mk('operator_or', {'OPERAND1': self.b(a), 'OPERAND2': self.b(b)})
    def not_(self, a):    return self.mk('operator_not', {'OPERAND': self.b(a)})
    def join(self, a, b): return self.mk('operator_join', {'STRING1': a, 'STRING2': b})
    def add(self, a, b):  return self.mk('operator_add', {'NUM1': a, 'NUM2': b})
    def sub_(self, a, b): return self.mk('operator_subtract', {'NUM1': a, 'NUM2': b})
    def mul(self, a, b):  return self.mk('operator_multiply', {'NUM1': a, 'NUM2': b})
    def mod(self, a, b):  return self.mk('operator_mod', {'NUM1': a, 'NUM2': b})
    def rnd(self, a, b):  return self.mk('operator_random', {'FROM': a, 'TO': b})
    def mathop(self, op, a): return self.mk('operator_mathop', {'NUM': a}, {'OPERATOR': [op, None]})
    def length(self, a):  return self.mk('operator_length', {'STRING': a})
    def round_(self, a):  return self.mk('operator_round', {'NUM': a})
    def letter(self, i, s): return self.mk('operator_letter_of', {'LETTER': i, 'STRING': s})
    def answer(self):     return self.mk('sensing_answer')
    def username(self):   return self.mk('sensing_username')
    def days(self):       return self.mk('sensing_dayssince2000')
    def item(self, lst, idx):
        return self.mk('data_itemoflist', {'INDEX': idx}, {'LIST': [lst, list_id(self.t, lst)]})
    def itemnum(self, lst, it):
        return self.mk('data_itemnumoflist', {'ITEM': it}, {'LIST': [lst, list_id(self.t, lst)]})
    def listlen(self, lst):
        return self.mk('data_lengthoflist', {}, {'LIST': [lst, list_id(self.t, lst)]})
    def eqv(self, name, val):   # variable == littéral
        return self.eq(self.v(name), self.s(val))

    # ---- commandes
    def setv(self, name, inp):
        return self.mk('data_setvariableto', {'VALUE': inp}, {'VARIABLE': [name, var_id(self.t, name)]})
    def changev(self, name, inp):
        return self.mk('data_changevariableby', {'VALUE': inp}, {'VARIABLE': [name, var_id(self.t, name)]})
    def ask(self, q):
        return self.mk('sensing_askandwait', {'QUESTION': q})
    def say(self, inp):
        return self.mk('looks_say', {'MESSAGE': inp})
    def wait(self, d):
        return self.mk('control_wait', {'DURATION': d})
    def wait_until(self, cond):
        return self.mk('control_wait_until', {'CONDITION': self.b(cond)})
    def if_(self, cond, stack):
        return self.mk('control_if', {'CONDITION': self.b(cond), 'SUBSTACK': self.sub(self.stack(stack))})
    def ifelse(self, cond, s1, s2):
        return self.mk('control_if_else', {'CONDITION': self.b(cond), 'SUBSTACK': self.sub(self.stack(s1)),
                                           'SUBSTACK2': self.sub(self.stack(s2))})
    def forever(self, stack):
        return self.mk('control_forever', {'SUBSTACK': self.sub(self.stack(stack))})
    def repeat(self, times, stack):
        return self.mk('control_repeat', {'TIMES': times, 'SUBSTACK': self.sub(self.stack(stack))})
    def broadcast(self, name):
        bid = [k for k, v in STAGE['broadcasts'].items() if v == name][0]
        return self.mk('event_broadcast', {'BROADCAST_INPUT': [1, [11, name, bid]]})
    def showlist(self, lst):
        return self.mk('data_showlist', {}, {'LIST': [lst, list_id(self.t, lst)]})
    def hidelist(self, lst):
        return self.mk('data_hidelist', {}, {'LIST': [lst, list_id(self.t, lst)]})
    def addtolist(self, lst, inp):
        return self.mk('data_addtolist', {'ITEM': inp}, {'LIST': [lst, list_id(self.t, lst)]})
    def dellist(self, lst):
        return self.mk('data_deletealloflist', {}, {'LIST': [lst, list_id(self.t, lst)]})
    def effect(self, eff, inp):
        return self.mk('looks_seteffectto', {'VALUE': inp}, {'EFFECT': [eff, None]})
    def changeeffect(self, eff, inp):
        return self.mk('looks_changeeffectby', {'CHANGE': inp}, {'EFFECT': [eff, None]})
    def cleareffects(self):
        return self.mk('looks_cleargraphiceffects')
    def volume(self, inp):
        return self.mk('sound_setvolumeto', {'VOLUME': inp})
    def stop_script(self):
        return self.mk('control_stop', {}, {'STOP_OPTION': ['this script', None]},
                       mutation={'tagName': 'mutation', 'children': [], 'hasnext': 'false'})

    # ---- chapeaux
    def hat_flag(self, x=0, y=0):
        return self.mk('event_whenflagclicked', topLevel=True, x=x, y=y)
    def hat_key(self, k, x=0, y=0):
        return self.mk('event_whenkeypressed', fields={'KEY_OPTION': [k, None]}, topLevel=True, x=x, y=y)
    def hat_receive(self, name, x=0, y=0):
        bid = [k for k, v in STAGE['broadcasts'].items() if v == name][0]
        return self.mk('event_whenbroadcastreceived', fields={'BROADCAST_OPTION': [name, bid]}, topLevel=True, x=x, y=y)

    # ---- chaînage
    def stack(self, ids):
        """Chaîne une liste d'ids (next/parent) et renvoie le premier."""
        ids = [i for i in ids if i]
        for a, b in zip(ids, ids[1:]):
            self.bl[a]['next'] = b
            self.bl[b]['parent'] = a
        return ids[0] if ids else None

    def script(self, hat, body, x=0, y=0):
        self.stack([hat] + body)
        return hat

    def last(self, bid):
        while self.bl[bid]['next']:
            bid = self.bl[bid]['next']
        return bid

    def insert_after(self, bid, new_ids):
        """Insère une pile de nouveaux blocs juste après le bloc bid."""
        nxt = self.bl[bid]['next']
        first = self.stack(new_ids)
        last = self.last(first)
        self.bl[bid]['next'] = first
        self.bl[first]['parent'] = bid
        self.bl[last]['next'] = nxt
        if nxt:
            self.bl[nxt]['parent'] = last

    def insert_substack_top(self, cblock, subname, new_ids):
        old = self.bl[cblock]['inputs'].get(subname)
        first = self.stack(new_ids)
        last = self.last(first)
        self.bl[cblock]['inputs'][subname] = [2, first]
        self.bl[first]['parent'] = cblock
        if old and isinstance(old[1], str):
            self.bl[last]['next'] = old[1]
            self.bl[old[1]]['parent'] = last

    def replace_input_block(self, parent, inputname, new_id):
        """Remplace le reporter dans parent.inputs[inputname] par new_id ; renvoie l'ancien id."""
        old = self.bl[parent]['inputs'][inputname]
        old_id = old[1] if isinstance(old[1], str) else None
        kind = old[0]
        if kind == 1:
            kind = 3
        if kind == 3:
            self.bl[parent]['inputs'][inputname] = [3, new_id, [10, '']]
        else:
            self.bl[parent]['inputs'][inputname] = [2, new_id]
        self.bl[new_id]['parent'] = parent
        return old_id

    def find_keyopt(self, keyname):
        """Renvoie (keypressed_id, parent_id, inputname) pour la touche donnée (occurrences)."""
        res = []
        for i, blk in self.bl.items():
            if blk.get('opcode') == 'sensing_keyoptions' and blk['fields']['KEY_OPTION'][0] == keyname:
                kp = blk['parent']
                par = self.bl[kp]['parent']
                for name, inp in self.bl[par]['inputs'].items():
                    if isinstance(inp, list) and len(inp) > 1 and inp[1] == kp:
                        res.append((kp, par, name))
        return res

def set_literal(tgt, bid, inputname, text):
    inp = tgt['blocks'][bid]['inputs'][inputname]
    inp[1][1] = text

# ==========================================================================
# 1) STAGE
# ==========================================================================
st = B(STAGE)
blk = STAGE['blocks']

# -- Script "when flag clicked" de configuration : on remplace l'ancien
#    (Fly Mode / ___owner = NormanTheGamer / ___username = username)
old_owner_block = 'n0.PYCB7qugf`F0_vfw['
old_user_block = 'Eh$;lubP-J,WM3JX`y+#'
old_if = 'b5H,kYz_+S]vpLuNHa7T'
# on détache la suite (if owner -> boucle F) pour la rebrancher après
flyloop_if = old_if
fly_prev = 'Z~z8uL+7[{.Egs=9h8=Q'   # set Fly Mode 0
# supprimer les deux blocs (et leurs enfants reporters)
def delete_block(tgt, bid):
    b = tgt['blocks'].pop(bid)
    for k, inp in b.get('inputs', {}).items():
        if isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str):
            delete_block(tgt, inp[1])
delete_block(STAGE, old_owner_block)
delete_block(STAGE, old_user_block)

setup = [
    st.setv('*setup done', st.s('0')),
    st.setv('___owner', st.s('0')),
    st.setv('God Mode', st.s('0')), st.setv('Vitesse', st.s('0')), st.setv('Super Saut', st.s('0')),
    st.setv('Disco Mode', st.s('0')), st.setv('Musique', st.s('1')), st.setv('*chat', st.s('0')),
    st.setv('Triche', st.s('0')), st.setv('Panneau', st.s('0')), st.setv('Aide visible', st.s('0')),
    st.hidelist('Aide'), st.hidelist('Panneau Admin'),
    # ---- pseudo
    st.ask(st.s('👤 Ton pseudo ? (lettres, chiffres, _ - . ; 12 max)')),
    st.setv('___username', st.s('')),
    st.setv('*i', st.s('1')),
    st.repeat(st.length(st.answer()), [
        st.if_(st.and_(st.and_(
                st.gt(st.itemnum('CODE', st.letter(st.v('*i'), st.answer())), st.s('9')),
                st.lt(st.itemnum('CODE', st.letter(st.v('*i'), st.answer())), st.s('51'))),
                st.lt(st.length(st.v('___username')), st.s('12'))),
            [st.setv('___username', st.join(st.v('___username'),
                st.item('CODE', st.itemnum('CODE', st.letter(st.v('*i'), st.answer())))))]),
        st.changev('*i', st.s('1')),
    ]),
    st.if_(st.eqv('___username', ''), [
        st.setv('___username', st.join(st.s('joueur'), st.rnd(st.n(1), st.n(999))))]),
    # ---- clavier
    st.ask(st.s('⌨️ Clavier : tape 1 pour AZERTY (ZQSD) ou 2 pour QWERTY (WASD)')),
    st.ifelse(st.or_(st.or_(st.eq(st.answer(), st.s('2')), st.eq(st.answer(), st.s('qwerty'))),
                     st.eq(st.answer(), st.s('q'))),
              [st.setv('Clavier', st.s('QWERTY'))],
              [st.setv('Clavier', st.s('AZERTY'))]),
    # ---- couleur
    st.ask(st.s('🎨 Couleur de ton perso ? (0 à 199, Entrée = normal)')),
    st.setv('Couleur', st.mod(st.mathop('abs', st.round_(st.answer())), st.n(200))),
    # ---- admin
    st.ask(st.s('🔑 Code admin ? (Entrée pour passer)')),
    st.if_(st.or_(st.and_(st.gt(st.answer(), st.s('')), st.eq(st.answer(), st.v('_ADMIN CODE'))),
                  st.and_(st.gt(st.username(), st.s('')), st.eq(st.username(), st.v('_ADMIN SCRATCH')))),
           [st.setv('___owner', st.s('1')),
            st.setv('___username', st.join(st.v('___username'), st.s('★'))),
            st.showlist('Panneau Admin'), st.setv('Panneau', st.s('1'))]),
    # ---- fin
    st.setv('*setup done', st.s('1')),
    st.ifelse(st.eqv('___owner', '1'),
              [st.setv('*chat', st.s('10'))],
              [st.setv('*chat', st.s('7'))]),
    st.setv('chat timer', st.days()),
]
# rebrancher : fly_prev -> setup... -> old_if
first = st.stack(setup)
blk[fly_prev]['next'] = first
blk[first]['parent'] = fly_prev
last = st.last(first)
blk[last]['next'] = old_if
blk[old_if]['parent'] = last

# -- Protéger les boucles de touches (t, l, g) contre la saisie des réponses
def guard_after(tgt, bid):
    b = B(tgt)
    b.insert_after(bid, [b.wait_until(b.eqv('*setup done', '1'))])
guard_after(STAGE, 'eEiyvoKhWqs[KeNm*_.O')   # boucle T (le hat) -> insérer après le hat
guard_after(STAGE, 'jv22Qd_-h8@i(I?H)v`X')   # boucle L (après set Leaderboard 0)
guard_after(STAGE, '!LEyZ`K)XA_wrgsXUm25')   # boucle G (après set Float 0)

# -- Les gardes "username > ''" (affichage classement) -> ___username
for bid in ['M3$~n_g`^LfJfZ+0Oow#', '-?/uQF(;y`H(xNaWk_c8']:
    cond = blk[bid]['inputs']['CONDITION'][1]
    old = blk[cond]['inputs']['OPERAND1'][1]
    blk[cond]['inputs']['OPERAND1'] = st.v('___username')
    del blk[old]

# -- Traduction des libellés Server Data
set_literal(STAGE, 'y4|_7n=wKDA,/9s*$cW|', 'ITEM', 'Appuie sur T pour masquer')
for bid, txt in [('kO#,So2o*:s=}ly!(7Xs', 'morts : '), ('zZ!%Xqj:?3K`n+[bRc_Z', 'joueurs actifs : '),
                 ('L*6m+uHT4D:S#|w8-o5=', 'plus rapide : '), (')+EtU%+O`Mf4=mT263vI', 'record perso : ')]:
    j = blk[bid]['inputs']['ITEM'][1]
    blk[j]['inputs']['STRING1'][1][1] = txt
# ajout pseudo / clavier / admin dans Server Data (après 'morts')
st.insert_after('kO#,So2o*:s=}ly!(7Xs', [
    st.addtolist('Server Data', st.join(st.s('pseudo : '), st.v('___username'))),
    st.addtolist('Server Data', st.join(st.s('clavier : '), st.v('Clavier'))),
    st.addtolist('Server Data', st.join(st.s('couleur : '), st.v('Couleur'))),
    st.if_(st.eqv('___owner', '1'), [st.addtolist('Server Data', st.s('ADMIN : oui ★'))]),
    st.if_(st.eqv('Triche', '1'), [st.addtolist('Server Data', st.s('(pouvoirs admin utilises : record non enregistre)'))]),
])
# détection triche (pouvoirs admin) dans INFINITE TICK
st.insert_after('jxplgP|tv_|p}yEqt{ac', [
    st.if_(st.or_(st.or_(st.eqv('Fly Mode', '1'), st.eqv('God Mode', '1')),
                  st.or_(st.eqv('Vitesse', '1'), st.eqv('Super Saut', '1'))),
           [st.setv('Triche', st.s('1'))]),
])

# -- Nouvelles touches (Stage) ----------------------------------------------
Y = 900
def toggle_loop(b, key, var, extra=None, admin=False, x=0, y=0):
    """Boucle 'wait until not key / wait until key / toggle var' comme l'original."""
    body = [b.wait_until(b.not_(b.key(key))), b.wait_until(b.key(key)),
            b.setv(var, b.sub_(b.s('1'), b.v(var)))] + (extra or [])
    loop = b.forever(body)
    inner = [b.wait_until(b.eqv('*setup done', '1'))]
    if admin:
        inner.append(b.wait_until(b.eqv('___owner', '1')))
    return b.script(b.hat_flag(x, y), inner + [loop])

toggle_loop(st, 'i', 'God Mode', admin=True, x=1200, y=0)
toggle_loop(st, 'j', 'Vitesse', admin=True, x=1200, y=300)
toggle_loop(st, 'h', 'Super Saut', admin=True, x=1200, y=600)
toggle_loop(st, 'b', 'Disco Mode', admin=True, x=1200, y=900)
toggle_loop(st, 'm', 'Panneau', admin=True, x=1500, y=0, extra=[
    st.ifelse(st.eqv('Panneau', '1'), [st.showlist('Panneau Admin')], [st.hidelist('Panneau Admin')])])
toggle_loop(st, 'c', 'Aide visible', x=1500, y=300, extra=[
    st.ifelse(st.eqv('Aide visible', '1'), [st.showlist('Aide')], [st.hidelist('Aide')])])
toggle_loop(st, 'v', 'Musique', x=1500, y=600, extra=[
    st.ifelse(st.eqv('Musique', '0'), [st.volume(st.n(0))],
              [st.if_(st.eqv('*Song', '0'), [st.volume(st.n(30))])])])
# P : bascule clavier
st.script(st.hat_flag(1500, 900), [
    st.wait_until(st.eqv('*setup done', '1')),
    st.forever([
        st.wait_until(st.not_(st.key('p'))), st.wait_until(st.key('p')),
        st.ifelse(st.eqv('Clavier', 'AZERTY'), [st.setv('Clavier', st.s('QWERTY'))],
                  [st.setv('Clavier', st.s('AZERTY'))]),
        st.setv('*chat', st.s('0')),
    ])])
# U / Y : téléportation checkpoint (admin) ; EXIT='tp' relance la boucle sans compter une mort
st.script(st.hat_flag(1800, 0), [
    st.wait_until(st.eqv('*setup done', '1')), st.wait_until(st.eqv('___owner', '1')),
    st.forever([
        st.wait_until(st.not_(st.or_(st.key('u'), st.key('y')))),
        st.wait_until(st.or_(st.key('u'), st.key('y'))),
        st.ifelse(st.key('u'),
                  [st.if_(st.lt(st.v('Checkpoint'), st.s('6')), [st.changev('Checkpoint', st.s('1'))])],
                  [st.if_(st.gt(st.v('Checkpoint'), st.s('1')), [st.changev('Checkpoint', st.s('-1'))])]),
        st.setv('Triche', st.s('1')),
        st.setv('EXIT', st.s('tp')),
    ])])
# Chat rapide : touches 4..9
for i, k in enumerate(['4', '5', '6', '7', '8', '9']):
    st.script(st.hat_key(k, 1800, 400 + i * 120), [
        st.if_(st.eqv('*setup done', '1'), [
            st.setv('*chat', st.s(str(i + 1))), st.setv('chat timer', st.days())])])
# Message auto à la victoire
st.script(st.hat_receive('GAME WIN', 1800, 1200), [
    st.setv('*chat', st.s('9')), st.setv('chat timer', st.days())])
# Reset du drapeau triche quand on recommence la tour / hard reset
st.script(st.hat_receive('Hard Reset', 1800, 1350), [st.setv('Triche', st.s('0'))])

# ==========================================================================
# 2) PLAYER
# ==========================================================================
PL = target('Player')
pl = B(PL)
pb = PL['blocks']

# -- gate "Play Game" sur la fin de la configuration
pl.insert_after('_S6dQAN+3NNZ9K(BDr^X', [pl.wait_until(pl.eqv('*setup done', '1'))])

# -- AZERTY / QWERTY : touche a -> (a & QWERTY) | (q & AZERTY) ; w -> (w & QWERTY) | (z & AZERTY)
def layout_key(b, qwerty_kp, parent, inputname, azerty_key):
    new = b.or_(b.and_(qwerty_kp, b.eqv('Clavier', 'QWERTY')),
                b.and_(b.key(azerty_key), b.eqv('Clavier', 'AZERTY')))
    b.bl[parent]['inputs'][inputname] = [2, new]
    b.bl[new]['parent'] = parent
# combo "reset data" : R + Q devient R + X (Q sert à aller à gauche en AZERTY) — AVANT d'ajouter q
(kp_q, par_q, in_q), = pl.find_keyopt('q')
pb[pb[kp_q]['inputs']['KEY_OPTION'][1]]['fields']['KEY_OPTION'] = ['x', None]
(kp_a, par_a, in_a), = pl.find_keyopt('a')
layout_key(pl, kp_a, par_a, in_a, 'q')
(kp_w, par_w, in_w), = pl.find_keyopt('w')
layout_key(pl, kp_w, par_w, in_w, 'z')

# -- Vitesse admin : 1.9 -> 1.9 + 0.8*Vitesse
acc = pb['316X.O]RiL#7+C./5vhS']['inputs']['VALUE'][1]
assert pb[acc]['opcode'] == 'operator_multiply'
pb[acc]['inputs']['NUM1'] = pl.r(pl.add(pl.n(1.9), pl.mul(pl.n(0.8), pl.v('Vitesse'))))
pb[pb[acc]['inputs']['NUM1'][1]]['parent'] = acc

# -- Super saut : 20 -> 20 + 6*Super Saut
jmp = '8)w.tW0~H{[uOq}#0lMe'
nb = pl.add(pl.n(20), pl.mul(pl.n(6), pl.v('Super Saut')))
pb[jmp]['inputs']['VALUE'] = pl.r(nb)
pb[nb]['parent'] = jmp

# -- God mode : (dangers | reset) -> ((dangers & God=0) | reset)
death_if = '_Ngi;e}e[AS9yL{pBB%d'
A = pb[death_if]['inputs']['CONDITION'][1]          # and(or(...), immunity>5)
O1 = pb[A]['inputs']['OPERAND1'][1]                 # or(touch danger, or(touch moving, reset=1))
O2 = pb[O1]['inputs']['OPERAND2'][1]                # or(touch moving, reset=1)
reset_eq = pb[O2]['inputs']['OPERAND2'][1]          # reset = 1
touch_moving = pb[O2]['inputs']['OPERAND1'][1]
# O2 devient : touch_moving seul ? -> on réécrit : O2 = and(or(touchD, touchM), God=0) ; O1 = or(O2', reset)
touch_danger = pb[O1]['inputs']['OPERAND1'][1]
dangers = pl.or_(touch_danger, touch_moving)
safe = pl.and_(dangers, pl.eqv('God Mode', '0'))
newO1 = pl.or_(safe, reset_eq)
pb[A]['inputs']['OPERAND1'] = [2, newO1]
pb[newO1]['parent'] = A
del pb[O1]; del pb[O2]

# -- Chat : affichage du message au-dessus du joueur (fin de la procédure "tick")
tick_last = pl.last('c`S{X7},@^d8V8;_9XSl')
pl.insert_after(tick_last, [
    pl.if_(pl.gt(pl.v('*chat'), pl.s('0')), [
        pl.ifelse(pl.gt(pl.mul(pl.sub_(pl.days(), pl.v('chat timer')), pl.n(86400)), pl.n(4)),
                  [pl.setv('*chat', pl.s('0')), pl.say(pl.s(''))],
                  [pl.say(pl.item('CHAT', pl.v('*chat')))])]),
])
# -- Couleur du perso (fin de la procédure costume)
cost_last = pl.last('0F5SuiZ*$kT6UgDA`WGf')
pl.insert_after(cost_last, [pl.effect('COLOR', pl.v('Couleur'))])

# -- Encodage : '' -> *chat, puis Couleur
enc_call = 'DpL_ikxJ-{j}_jX@$E93'
pb[enc_call]['inputs']['kq:hEcruw1^B`X_=zy/5'] = pl.v('*chat')
col_call = pl.mk('procedures_call', {'kq:hEcruw1^B`X_=zy/5': pl.v('Couleur')},
                 mutation=dict(pb[enc_call]['mutation']))
pl.insert_after(enc_call, [col_call])

# -- "reset data" remet Triche à 0
pl.insert_after('|oiT-+wEmpbF|RU8SS`/', [pl.setv('Triche', pl.s('0'))])

# ==========================================================================
# 3) OPPONENTS : décodage chat + couleur, nom mémorisé
# ==========================================================================
OP = target('Opponents')
op = B(OP)
ob = OP['blocks']
OP['variables'][nid()] = ['oname', '']
OP['variables'][nid()] = ['onscreen', '0']
# après la lecture du pseudo
op.insert_after('wNi?r|vXwz5f_ajE8{hw', [op.setv('oname', op.v('value'))])
# marquer onscreen dans les deux branches du if/else "hors écran ?"
op.insert_substack_top('02E=b%83!bXDT]=eveD=', 'SUBSTACK', [op.setv('onscreen', op.s('0'))])
op.insert_substack_top('02E=b%83!bXDT]=eveD=', 'SUBSTACK2', [op.setv('onscreen', op.s('1'))])
# après la dernière lecture (= chat) : bulle + couleur
op.insert_after('-.L;]xfS[RsZx#;Hsw8e', [
    op.if_(op.and_(op.and_(op.eqv('onscreen', '1'), op.eqv('*names', '1')),
                   op.and_(op.gt(op.v('value'), op.s('0')), op.lt(op.v('value'), op.s('11')))),
           [op.say(op.join(op.v('oname'), op.join(op.s(' : '), op.item('CHAT', op.v('value')))))]),
    op.mk('procedures_call', mutation=dict(ob['-.L;]xfS[RsZx#;Hsw8e']['mutation'])),
    op.if_(op.eqv('onscreen', '1'), [op.effect('COLOR', op.v('value'))]),
])
# boucle N protégée
guard_after(OP, 'z^cJdje+SX0dY?mRX94M')

# ==========================================================================
# 4) Autres sprites
# ==========================================================================
# Intro Text : attendre la configuration
IT = target('Intro Text')
guard_after(IT, '[`tgkUUnT~mCOW8d)Wtj')
# Mobile Button : attendre la configuration ; garde username -> ___username
MB = target('Mobile Button')
mb = B(MB)
mb.insert_substack_top('w#jz$#;rWk~/Ms0[;lV#', 'SUBSTACK', [mb.wait_until(mb.eqv('*setup done', '1'))])
cond = MB['blocks']['ccXB7AIg1:_EtMx/!c_`']['inputs']['CONDITION'][1]
old = MB['blocks'][cond]['inputs']['OPERAND1'][1]
MB['blocks'][cond]['inputs']['OPERAND1'] = mb.v('___username')
del MB['blocks'][old]
# Checkpoints : message "Checkpoint !"
CK = target('Checkpoints')
ck = B(CK)
ck.insert_after('VoI^UhNG9S]-a9r6Hfp!', [ck.setv('*chat', ck.s('8')), ck.setv('chat timer', ck.days())])
# Text : le record n'est pas enregistré si des pouvoirs admin ont été utilisés
TX = target('Text')
tx = B(TX)
win_if = 'Ec?sJ^Dow;L1C:BC[l/Y'
oldcond = TX['blocks'][win_if]['inputs']['CONDITION'][1]
newcond = tx.and_(oldcond, tx.eqv('Triche', '0'))
TX['blocks'][win_if]['inputs']['CONDITION'] = [2, newcond]
TX['blocks'][newcond]['parent'] = win_if
# Leaderboard : libellé
LB = target('Leaderboard')
set_literal(LB, 'KGXF*V5YUa);3j;ww,Pl', 'ITEM', 'Appuie sur L pour masquer')
# Background : mode disco
BG = target('Background')
bg = B(BG)
bg.insert_after('6Y5G6TGK2uM|@!L=hJDw', [
    bg.ifelse(bg.eqv('Disco Mode', '1'), [bg.changeeffect('COLOR', bg.n(4))], [bg.effect('COLOR', bg.n(0))])])
# Radio : suit la coupure musique
RD = target('Radio')
rd = B(RD)
rd.script(rd.hat_key('v', 600, 0), [rd.wait(rd.n(0.1)), rd.volume(rd.mul(rd.n(30), rd.v('Musique')))])

# ==========================================================================
# 5) Costumes SVG : traduction des textes
# ==========================================================================
def retext(tgt, costume_name, replacements, tspans=None):
    for c in tgt['costumes']:
        if c['name'] == costume_name:
            break
    else:
        raise KeyError(costume_name)
    path = os.path.join(OUT, c['md5ext'])
    svg = open(path, encoding='utf-8').read()
    if tspans is not None:
        # remplace l'ensemble des tspans du 1er <text> par une nouvelle liste
        m = re.search(r'(<text[^>]*>)(.*?)(</text>)', svg, re.S)
        first = re.search(r'<tspan x="0" dy="0">', m.group(2))
        dy = re.search(r'dy="([^"]+)"', m.group(2)[first.end():])
        dyv = dy.group(1) if dy else '48px'
        body = ''.join(f'<tspan x="0" dy="{"0" if i == 0 else dyv}">{t}</tspan>' for i, t in enumerate(tspans))
        svg = svg[:m.start(2)] + body + svg[m.end(2):]
    for a, b_ in replacements:
        assert a in svg, (costume_name, a)
        svg = svg.replace(a, b_)
    os.remove(path)
    data = svg.encode('utf-8')
    md5 = hashlib.md5(data).hexdigest()
    c['assetId'] = md5
    c['md5ext'] = md5 + '.svg'
    open(os.path.join(OUT, c['md5ext']), 'wb').write(data)

retext(IT, '1', [], tspans=['Bienvenue dans Tower Obby !', 'Flèches / ZQSD / WASD pour bouger.',
                            'L : classement   T : infos   C : aide', 'R : réapparaître   4 à 9 : chat'])
retext(IT, '4', [], tspans=['Bienvenue dans Tower Obby !', 'Flèches / ZQSD / WASD pour bouger.',
                            'L : classement   T : infos   C : aide', 'R : réapparaître   4 à 9 : chat',
                            'Connecte-toi à Scratch pour le multi.'])
retext(IT, '2', [('Press any for PC', 'Touche clavier = PC')])
retext(IT, '3', [], tspans=['Bienvenue dans Tower Obby !', 'Clique sur les côtés pour bouger.'])
CN = target('Connnect')
retext(CN, 'Connecting', [('Connecting...', 'Connexion...')])
retext(CN, 'Connected', [('Connected!', 'Connecté !')])
retext(CN, 'Full', [('Full :(', 'Complet :(')])
retext(CN, 'Timeout', [('Timeout!', 'Déconnecté !'), ('Click green flag to play again!', 'Clique sur le drapeau vert pour rejouer !')])
retext(MB, '3', [('Restart', 'Relancer')])
retext(MB, '4', [('Times', 'Temps')])

# ==========================================================================
# 6) Vérifications de cohérence + écriture
# ==========================================================================
def check(tgt):
    bl = tgt['blocks']
    for i, b in bl.items():
        if isinstance(b, list):
            continue
        if b['next']:
            assert b['next'] in bl, (tgt['name'], i, 'next manquant')
            assert bl[b['next']]['parent'] == i, (tgt['name'], i, 'parent du next incohérent', b['opcode'], bl[b['next']]['opcode'])
        if b['parent']:
            assert b['parent'] in bl, (tgt['name'], i, 'parent manquant', b['opcode'])
        for k, inp in b['inputs'].items():
            if isinstance(inp, list) and len(inp) > 1 and isinstance(inp[1], str):
                assert inp[1] in bl, (tgt['name'], i, k, 'input manquant')
                assert bl[inp[1]]['parent'] == i, (tgt['name'], i, k, 'parent input incohérent')
        if not b['topLevel'] and not b['shadow']:
            assert b['parent'] is not None, (tgt['name'], i, b['opcode'], 'orphelin')
for t in P['targets']:
    check(t)

P['meta']['agent'] = 'patch-fr'
json.dump(P, open(os.path.join(OUT, 'project.json'), 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print('OK — blocs :', {t['name']: len(t['blocks']) for t in P['targets']})
