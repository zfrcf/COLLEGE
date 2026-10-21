# CP-SAT v12: K unit types side by side (pitch 1, period K in X), all lockstep. Each type t: main plane at X=t,
# may use lanes d in DL (relative X). Tile 1-wide at its main plane z=0 => watertight door face.
import sys, itertools, json
from ortools.sat.python import cp_model
P = int(sys.argv[1]); ZM = int(sys.argv[2]); TL = float(sys.argv[3]); K = int(sys.argv[4])
LAMPBACK = sys.argv[5] == "1"
OUT = sys.argv[6]
DL = [int(v) for v in sys.argv[7].split(",")] if len(sys.argv) > 7 else [-1, 0, 1]
TZ = [int(v) for v in sys.argv[8].split(",")] if len(sys.argv) > 8 else [0] * K
YL, YH = -3, P + 3
cells = [(d, z, y) for d in DL for z in range(ZM + 1) for y in range(YL, YH + 1)]
cellset = set(cells)
DIRS = {"up": (0, 0, 1), "down": (0, 0, -1), "south": (0, 1, 0), "north": (0, -1, 0), "east": (1, 0, 0), "west": (-1, 0, 0)}
OBSD = list(DIRS)
def add(c, v): return (c[0] + v[0], c[1] + v[1], c[2] + v[2])
NB = list(DIRS.values())
G = ["U", "L"]
m = cp_model.CpModel()
T = range(K)
S = {(t, g): {c: m.NewBoolVar("") for c in cells} for t in T for g in G}
PL = {(t, g): {c: m.NewBoolVar("") for c in cells} for t in T for g in G}
LAMP = {(t, g): {c: m.NewBoolVar("") for c in cells} for t in T for g in G}
RS = {(t, g): {c: m.NewBoolVar("") for c in cells} for t in T for g in G}
spd = {t: {c: m.NewBoolVar("") for c in cells} for t in T}
spu = {t: {c: m.NewBoolVar("") for c in cells} for t in T}
ou = {t: {(c, k): m.NewBoolVar("") for c in cells for k in OBSD} for t in T}
ol = {t: {(c, k): m.NewBoolVar("") for c in cells for k in OBSD} for t in T}
occ, nso = {}, {}
for t in T:
    for X_ in (spd[t], spu[t], ou[t], ol[t]): m.AddExactlyOne(X_.values())
    for g in G:
        m.AddExactlyOne(LAMP[(t, g)].values()); m.AddExactlyOne(RS[(t, g)].values())
        for c in cells: m.Add(LAMP[(t, g)][c] + RS[(t, g)][c] <= PL[(t, g)][c])
    for g in G:
        for c in cells:
            ns = [PL[(t, g)][c]] + ([spd[t][c]] + [ou[t][(c, k)] for k in OBSD] if g == "U" else [spu[t][c]] + [ol[t][(c, k)] for k in OBSD])
            v = m.NewBoolVar(""); m.Add(sum(ns) + S[(t, g)][c] == v); occ[(t, g, c)] = v
            w = m.NewBoolVar(""); m.Add(sum(ns) == w); nso[(t, g, c)] = w
    for c in cells:
        m.Add(occ[(t, "U", c)] + occ[(t, "L", c)] <= 1)
    for y in range(P): m.Add(S[(t, "U")][(0, TZ[t], y)] == 1)
    for c in cells:
        f = add(c, (0, 0, -1)); a = add(c, (0, 0, -2))
        if f in cellset and a in cellset:
            m.Add(occ[(t, "U", f)] + occ[(t, "L", f)] == 0).OnlyEnforceIf(spd[t][c]); m.AddImplication(spd[t][c], S[(t, "L")][a])
        else: m.Add(spd[t][c] == 0)
        f = add(c, (0, 0, 1)); a = add(c, (0, 0, 2))
        if f in cellset and a in cellset:
            m.Add(occ[(t, "U", f)] + occ[(t, "L", f)] == 0).OnlyEnforceIf(spu[t][c]); m.AddImplication(spu[t][c], S[(t, "U")][a])
        else: m.Add(spu[t][c] == 0)
        for k in OBSD:
            b = add(c, tuple(-x for x in DIRS[k])); w = add(c, DIRS[k])
            if b in cellset and k != "down" and w in cellset:
                m.AddImplication(ou[t][(c, k)], spd[t][b]); m.AddImplication(ou[t][(c, k)], LAMP[(t, "U")][w])
            else: m.Add(ou[t][(c, k)] == 0)
            if b in cellset and k != "up" and w in cellset:
                m.AddImplication(ol[t][(c, k)], spu[t][b]); m.AddImplication(ol[t][(c, k)], LAMP[(t, "L")][w])
            else: m.Add(ol[t][(c, k)] == 0)
        if LAMPBACK and c[1] != ZM:
            for g in G: m.Add(LAMP[(t, g)][c] == 0)
    for g in G:
        for c in cells:
            nbs = [S[(t, g)][add(c, v)] for v in NB if add(c, v) in cellset]
            m.Add(sum(nbs) >= 1).OnlyEnforceIf(nso[(t, g, c)])
        lvl = {c: m.NewIntVar(0, 60, "") for c in cells}
        for c in cells:
            a = add(c, (0, 0, -2)) if g == "U" else add(c, (0, 0, 2))
            root = (spu[t][a] if g == "U" else spd[t][a]) if a in cellset else None
            if root is not None: m.Add(lvl[c] == 0).OnlyEnforceIf(root)
            cand = []
            for v in NB:
                n = add(c, v)
                if n in cellset:
                    b = m.NewBoolVar(""); m.AddImplication(b, S[(t, g)][n]); m.Add(lvl[n] < lvl[c]).OnlyEnforceIf(b); cand.append(b)
            m.AddBoolOr(cand + ([root] if root is not None else []) + [S[(t, g)][c].Not()])
    # lamps lit at rest by neighbour unit of same type/column
    for a_ in cells:
        lu, ll = [], []
        for v in NB:
            n = add(a_, v)
            q = (n[0], n[1], n[2] - P)
            if q in cellset: lu.append(RS[(t, "L")][q])
            q = (n[0], n[1], n[2] + P)
            if q in cellset: ll.append(RS[(t, "U")][q])
        m.AddBoolOr(lu + [LAMP[(t, "U")][a_].Not()]); m.AddBoolOr(ll + [LAMP[(t, "L")][a_].Not()])
    m.Add(sum(occ[(t, "U", c)] for c in cells) <= 12); m.Add(sum(occ[(t, "L", c)] for c in cells) <= 12)

def ustate(prog, up=True):
    if up: h = prog; return (h // 2, h // 2) if h % 2 == 0 else ((h - 1) // 2, (h + 1) // 2)
    g = prog; return (-(g // 2), -(g // 2)) if g % 2 == 0 else (-((g + 1) // 2), -((g - 1) // 2))
configs = {((0, 0), (0, 0)), ((-1, 0), (0, 0)), ((0, 0), (0, 1)), (ustate(0), ustate(1)), (ustate(1, False), ustate(0, False))}
for h0 in (0, 1):
    for dd in (1, 2, 3): configs.add((ustate(h0), ustate(h0 + dd)))
for g1 in (0, 1):
    for dd in (1, 2, 3): configs.add((ustate(g1 + dd, False), ustate(g1, False)))
configs = sorted(configs)
COLS = list(range(-1, K + 1))     # absolute column positions considered (type = col mod K)
def mat(g, unit, col): return ((1 if g == "L" else 0) + unit + col) % 2
def insts(cfg, single=False):
    (u0, l0), (u1, l1) = cfg; ins = []
    for col in COLS:
        t = col % K
        ins += [((t, "U", 0, col), (col, u0)), ((t, "L", 0, col), (col, l0))]
        if not single: ins += [((t, "U", 1, col), (col, u1 + P)), ((t, "L", 1, col), (col, l1 + P))]
    return ins
def pc(a, off): return (a[0] - off[0], a[1], a[2] - off[1])
XS = range(min(COLS) + min(DL) - 1, max(COLS) + max(DL) + 2)
ABS = [(x, z, y) for x in XS for z in range(ZM + 1) for y in range(YL - 4, YH + P + 6)]
def piston(t, g, p): return spd[t][p] if g == "U" else spu[t][p]
def constrain(cfg, single=False):
    ins = insts(cfg, single); rest = (cfg == ((0, 0), (0, 0))) and not single
    # only enforce pair constraints that involve at least one instance of the central period (cols 0..K-1)
    for a in ABS:
        vs = [occ[(gi[0], gi[1], pc(a, o))] for gi, o in ins if pc(a, o) in cellset]
        if len(vs) > 1: m.Add(sum(vs) <= 1)
    for a in ABS:
        for v in NB:
            b = add(a, v)
            for (gi1, o1) in ins:
                p1 = pc(a, o1)
                if p1 not in cellset: continue
                for (gi2, o2) in ins:
                    if gi1 == gi2: continue
                    p2 = pc(b, o2)
                    if p2 not in cellset: continue
                    if not (0 <= gi1[3] < K or 0 <= gi2[3] < K): continue
                    t1, g1, u1_, c1 = gi1; t2, g2, u2_, c2 = gi2
                    m.AddBoolOr([RS[(t1, g1)][p1].Not(), piston(t2, g2, p2).Not()])
                    p3 = pc(add(b, (0, 0, -1)), o2)
                    if p3 in cellset: m.AddBoolOr([RS[(t1, g1)][p1].Not(), piston(t2, g2, p3).Not()])
                    allowed = rest and c1 == c2 and ((g1, u1_) == ("L", 1) and (g2, u2_) == ("U", 0) or (g1, u1_) == ("U", 0) and (g2, u2_) == ("L", 1))
                    if not allowed: m.AddBoolOr([RS[(t1, g1)][p1].Not(), LAMP[(t2, g2)][p2].Not()])
                    if v not in [(0, 0, 1), (0, 1, 0), (1, 0, 0)]: continue
                    s1, n1, s2, n2 = S[(t1, g1)][p1], nso[(t1, g1, p1)], S[(t2, g2)][p2], nso[(t2, g2, p2)]
                    for sv, nv, sg, ng, scell, ncell, no in ((s1, n2, gi1, gi2, a, b, o2), (s2, n1, gi2, gi1, b, a, o1)):
                        if sg[2:] == ng[2:] and sg[1] != ng[1]:
                            face = (0, 0, -1) if ng[1] == "U" else (0, 0, 1)
                            if add(ncell, face) == scell:
                                m.AddBoolOr([sv.Not(), nv.Not(), piston(ng[0], ng[1], pc(ncell, no))]); continue
                        m.AddBoolOr([sv.Not(), nv.Not()])
                    if mat(g1, u1_, c1) == mat(g2, u2_, c2): m.AddBoolOr([s1.Not(), s2.Not()])
for cfg in configs: constrain(cfg)
for st in ((0, 0), (0, 1)): constrain((st, (0, 0)), single=True)
# own redstone never next to own lamps
for t in T:
    for g in G:
        for c in cells:
            for v in NB:
                n = add(c, v)
                for g2 in G:
                    for dy in ((0,) if g == g2 else (0, 1, -1)):
                        n2 = (n[0], n[1], n[2] + dy)
                        if n2 in cellset: m.AddBoolOr([RS[(t, g)][c].Not(), LAMP[(t, g2)][n2].Not()])
def coll(t, A, B):
    bs = []
    for a in [(d, z, y) for d in DL for z in range(ZM + 1) for y in range(YL - 4, YH + P + 6)]:
        for (gA, oA) in A:
            pa = (a[0], a[1], a[2] - oA)
            if pa not in cellset: continue
            for (gB, oB) in B:
                pb = (a[0], a[1], a[2] - oB)
                if pb not in cellset: continue
                b = m.NewBoolVar(""); m.AddBoolAnd([occ[(t, gA, pa)], occ[(t, gB, pb)]]).OnlyEnforceIf(b); bs.append(b)
    return bs
for t in T:
    m.AddBoolOr(coll(t, [("L", 1)], [("U", P), ("L", P)]))
    m.AddBoolOr(coll(t, [("U", P - 1)], [("U", 0), ("L", 0)]))
m.Minimize(sum(occ.values()))
sol = cp_model.CpSolver(); sol.parameters.max_time_in_seconds = TL; sol.parameters.num_workers = 8
r = sol.Solve(m); print(sol.StatusName(r))
if r in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    out = {}
    for t in T:
        lst = []
        for c in cells:
            for g in G:
                if sol.Value(S[(t, g)][c]): lst.append((c, g, "S"))
                if sol.Value(LAMP[(t, g)][c]): lst.append((c, g, "lamp"))
                elif sol.Value(RS[(t, g)][c]): lst.append((c, g, "rs"))
                elif sol.Value(PL[(t, g)][c]): lst.append((c, g, "P"))
            if sol.Value(spd[t][c]): lst.append((c, "U", "spd"))
            if sol.Value(spu[t][c]): lst.append((c, "L", "spu"))
            for k in OBSD:
                if sol.Value(ou[t][(c, k)]): lst.append((c, "U", "obs-" + k))
                if sol.Value(ol[t][(c, k)]): lst.append((c, "L", "obs-" + k))
        out[t] = lst
    json.dump(out, open(OUT, "w"))
    print(json.dumps(out)[:3000])
