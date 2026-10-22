# Générateur de la porte en peigne (3 nappes) à machines volantes.
# Repère local : X = largeur (0..W-1 ouverture), Y = hauteur (0..H-1 ouverture, sol en y=-1), Z = profondeur (0 = face avant).
import json
from unit2 import Unit

FRAME = "minecraft:stone_bricks"
OBS = "minecraft:obsidian"

class Door:
    def __init__(s, unit_path="sol2_P6.json", W=67, N=12, P=6, ZP=6, shell=True):
        s.shell = shell
        s.u = Unit(unit_path, P); s.W, s.N, s.P, s.ZP = W, N, P, ZP
        s.D = P * N                      # course d'ouverture (vers le haut)
        s.H = P * N - 5                  # hauteur d'ouverture couverte (67 pour N=12)
        s.blocks = {}                    # (x,y,z) -> blockstate
        s.lampU = [c for c, g, k in s.u.sol if g == "U" and k == "lamp"][0]
        s.lampL = [c for c, g, k in s.u.sol if g == "L" and k == "lamp"][0]
        s.Ro = P * (N - 1) + s.lampU[2]          # rangée du déclencheur d'ouverture
        s.Rc = s.D + s.lampL[2]                  # rangée du déclencheur de fermeture
        s.ytop = P * (N - 1) + s.D + 8           # haut du logement
        s.ybot = -6
    def zo(s, x): return (x % 3) * s.ZP
    def A(s, x, c, base): return (x + c[0], base + c[2], s.zo(x) + c[1])
    def columns(s): return range(s.W)
    # ------------------------------------------------------------------
    def swept(s):
        sw = set()
        for x in s.columns():
            for j in range(s.N):
                for off in range(0, s.D + 2):
                    for c, g, k in s.u.sol:
                        for dl in ((0, 1) if g == "L" else (0,)):   # L monte d'1 en état compact
                            p = s.A(x, c, s.P * j + off)
                            sw.add((p[0], p[1] + dl, p[2]))
        return sw
    def units(s):
        out = {}
        for x in s.columns():
            for j in range(s.N):
                for c, g, b in s.u.blocks(j):
                    out[s.A(x, c, s.P * j)] = "minecraft:" + b
        return out
    def build(s, fill=True, keep=None):
        sw = s.swept()
        zmax = s.zo(2) + 5
        xmin, xmax = -6, s.W + 4
        special = {}
        # --- butées
        for x in s.columns():
            for c in s.u.down_stop_cells(): special[s.A(x, c, 0)] = OBS
            for c in s.u.up_stop_cells(): special[s.A(x, c, s.P * (s.N - 1) + s.D)] = OBS
        # --- déclencheurs (obsidienne tampon + répéteur + support), entrées en z+3
        s.inputs = {"open": [], "close": []}
        for x in s.columns():
            for kind, lamp, base, bdx in (("open", s.lampU, s.P * (s.N - 1), -1), ("close", s.lampL, s.D, +1)):
                b = (lamp[0] + bdx, lamp[1], lamp[2]); ob = s.A(x, b, base)
                special[ob] = OBS
                special[(ob[0], ob[1], ob[2] + 1)] = "minecraft:repeater[facing=south,delay=1]"
                special[(ob[0], ob[1] - 1, ob[2] + 1)] = OBS
                special[(ob[0], ob[1], ob[2] + 2)] = "minecraft:repeater[facing=south,delay=1]"   # relais (couche vide)
                special[(ob[0], ob[1] - 1, ob[2] + 2)] = OBS
                s.inputs[kind].append((ob[0], ob[1], ob[2] + 3))
        # --- lignes de poudre par nappe (z = zo+3), alimentées depuis l'ouest (x = -2)
        for k in range(3):
            zl = k * s.ZP + 4
            for kind, row in (("open", s.Ro), ("close", s.Rc)):
                ins = {p[0] for p in s.inputs[kind] if p[2] == zl}
                assert all(p[1] == row for p in s.inputs[kind] if p[2] == zl)
                xs = range(-2, s.W + 3)
                last_rep = -100
                for X in xs:
                    special[(X, row - 1, zl)] = OBS
                    if X not in ins and X - last_rep >= 13 and X > -2:
                        special[(X, row, zl)] = "minecraft:repeater[facing=west,delay=1]"; last_rep = X
                    else:
                        special[(X, row, zl)] = "minecraft:redstone_wire"
        # --- colonne d'alimentation (z variable) à x = -3, puis tours d'observateurs jusqu'au sol
        s.panel = {}
        for kind, row, xt in (("open", s.Ro, -4), ("close", s.Rc, -6)):
            # ligne de liaison le long de z à x=-3/-5 vers les 3 nappes
            xf = xt + 1
            for z in range(-2, zmax):
                special[(xf, row - 1, z)] = OBS
                special[(xf, row, z)] = "minecraft:redstone_wire"
            for k in (1, 2):                                   # régénération du signal avant chaque nappe
                special[(xf, row, k * s.ZP + 3)] = "minecraft:repeater[facing=north,delay=1]"
            for X in range(xf + 1, -2):
                for k in range(3):
                    zl = k * s.ZP + 4
                    special[(X, row - 1, zl)] = OBS; special[(X, row, zl)] = "minecraft:redstone_wire"
            # répéteur allongeur d'impulsion (8 ticks) en tête de la colonne de liaison
            special[(xf, row, -3)] = "minecraft:repeater[facing=north,delay=4]"
            special[(xf, row - 1, -3)] = OBS
            special[(xf, row, -4)] = OBS                       # bloc alimenté par le haut de la tour
            for y in range(2, row):                            # tour d'observateurs (signal montant)
                special[(xf, y, -4)] = "minecraft:observer[facing=down]"
            special[(xf, 0, -4)] = OBS
            special[(xf, 1, -4)] = "minecraft:lever[face=floor,facing=north]"
            s.panel[kind] = (xf, 1, -4)
        # --- structure : sol, murs, linteau/logement ; obsidienne au contact du balayage
        un = s.units()
        res = dict(special)
        for p, b in un.items(): res[p] = b
        def nb(p):
            x, y, z = p
            return [(x+1,y,z),(x-1,y,z),(x,y+1,z),(x,y-1,z),(x,y,z+1),(x,y,z-1)]
        for x in (range(xmin, xmax + 1) if fill else []):
            for z in range(-1, zmax + 1):
                for y in range(s.ybot, s.ytop + 1):
                    p = (x, y, z)
                    if p in res or p in sw: continue
                    if keep and not keep(p): continue
                    inside_open = 0 <= x < s.W and 0 <= y < s.H
                    if inside_open: continue                      # passage libre
                    # au-dessus de l'ouverture / sous le sol / murs latéraux : plein
                    # coque : sol (y<0), façade (z=-1) et faces extérieures ; intérieur du logement laissé vide
                    if s.shell and not (y < 0 or z in (-1, zmax) or x in (xmin, xmax) or y == s.ytop):
                        continue
                    # tout bloc fixe voisin du balayage doit être de l'obsidienne (sinon le slime l'arrache)
                    res[p] = OBS if any(q in sw for q in nb(p)) else FRAME
        # dégager l'accès au panneau de commande et l'espace des tours/liaisons (déjà en special)
        s.blocks = res
        return res
    def stats(s):
        from collections import Counter
        return Counter(b.split("[")[0] for b in s.blocks.values())
