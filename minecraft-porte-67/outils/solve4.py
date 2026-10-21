# CP-SAT search, v4: column pitch 2 in X (lane of column c touches main plane of column c+1, lockstep),
# lamps on back face (z = ZM) so frame can power them from z = ZM+1.
import sys, itertools, json
from ortools.sat.python import cp_model

P = int(sys.argv[1]); ZM = int(sys.argv[2]); TL = float(sys.argv[3])
LAMPBACK = (sys.argv[4] == "1") if len(sys.argv) > 4 else True
OUT = sys.argv[5] if len(sys.argv) > 5 else f"sol4_P{P}_Z{ZM}.json"
YL, YH = -3, P + 3
D = [0, 1]
cells = [(d, z, y) for d in D for z in range(ZM + 1) for y in range(YL, YH + 1)]
cellset = set(cells)
DIRS = {"up": (0, 0, 1), "down": (0, 0, -1), "south": (0, 1, 0), "north": (0, -1, 0), "east": (1, 0, 0)}
def add(c, v): return (c[0] + v[0], c[1] + v[1], c[2] + v[2])
NB = [(0, 0, 1), (0, 0, -1), (0, 1, 0), (0, -1, 0), (1, 0, 0), (-1, 0, 0)]
OBSD = list(DIRS)
G = ["U", "L"]
m = cp_model.CpModel()
S = {g: {c: m.NewBoolVar("") for c in cells} for g in G}
PL = {g: {c: m.NewBoolVar("") for c in cells} for g in G}
LAMP = {g: {c: m.NewBoolVar("") for c in cells} for g in G}
RS = {g: {c: m.NewBoolVar("") for c in cells} for g in G}
spd = {c: m.NewBoolVar("") for c in cells}
spu = {c: m.NewBoolVar("") for c in cells}
ou = {(c, k): m.NewBoolVar("") for c in cells for k in OBSD}
ol = {(c, k): m.NewBoolVar("") for c in cells for k in OBSD}
for X in (spd, spu, ou, ol): m.AddExactlyOne(X.values())
for g in G:
    m.AddExactlyOne(LAMP[g].values()); m.AddExactlyOne(RS[g].values())
    for c in cells: m.Add(LAMP[g][c] + RS[g][c] <= PL[g][c])
def NS(g, c):
    if g == "U": return [PL["U"][c], spd[c]] + [ou[(c, k)] for k in OBSD]
    return [PL["L"][c], spu[c]] + [ol[(c, k)] for k in OBSD]
occ, nso = {}, {}
for g in G:
    for c in cells:
        v = m.NewBoolVar(""); m.Add(sum(NS(g, c)) + S[g][c] == v); occ[(g, c)] = v
        w = m.NewBoolVar(""); m.Add(sum(NS(g, c)) == w); nso[(g, c)] = w
for c in cells:
    m.Add(occ[("U", c)] + occ[("L", c)] <= 1)
    for k in OBSD:
        w = add(c, DIRS[k])
        if w not in cellset or (c[0] == 1 and k == "east"):
            m.Add(ou[(c, k)] == 0); m.Add(ol[(c, k)] == 0)
for y in range(P): m.Add(S["U"][(0, 0, y)] == 1)
# pistons
for c in cells:
    f = add(c, (0, 0, -1)); a = add(c, (0, 0, -2))
    if f in cellset and a in cellset:
        m.Add(occ[("U", f)] + occ[("L", f)] == 0).OnlyEnforceIf(spd[c]); m.AddImplication(spd[c], S["L"][a])
    else: m.Add(spd[c] == 0)
    f = add(c, (0, 0, 1)); a = add(c, (0, 0, 2))
    if f in cellset and a in cellset:
        m.Add(occ[("U", f)] + occ[("L", f)] == 0).OnlyEnforceIf(spu[c]); m.AddImplication(spu[c], S["U"][a])
    else: m.Add(spu[c] == 0)
for c in cells:
    for k in OBSD:
        b = add(c, tuple(-x for x in DIRS[k]))
        if b in cellset and k != "down": m.AddImplication(ou[(c, k)], spd[b])
        else: m.Add(ou[(c, k)] == 0)
        if b in cellset and k != "up": m.AddImplication(ol[(c, k)], spu[b])
        else: m.Add(ol[(c, k)] == 0)
        w = add(c, DIRS[k])
        if w in cellset:
            m.AddImplication(ou[(c, k)], LAMP["U"][w]); m.AddImplication(ol[(c, k)], LAMP["L"][w])
# lamps on back face
if LAMPBACK:
    for g in G:
        for c in cells:
            if c[1] != ZM: m.Add(LAMP[g][c] == 0)
# holders + connectivity
for g in G:
    for c in cells:
        nbs = [S[g][add(c, v)] for v in NB if add(c, v) in cellset]
        m.Add(sum(nbs) >= 1).OnlyEnforceIf(nso[(g, c)])
for g in G:
    lvl = {c: m.NewIntVar(0, 60, "") for c in cells}
    for c in cells:
        a = add(c, (0, 0, -2)) if g == "U" else add(c, (0, 0, 2))
        root = (spu[a] if g == "U" else spd[a]) if a in cellset else None
        if root is not None: m.Add(lvl[c] == 0).OnlyEnforceIf(root)
        cand = []
        for v in NB:
            n = add(c, v)
            if n in cellset:
                b = m.NewBoolVar(""); m.AddImplication(b, S[g][n]); m.Add(lvl[n] < lvl[c]).OnlyEnforceIf(b); cand.append(b)
        m.AddBoolOr(cand + ([root] if root is not None else []) + [S[g][c].Not()])

def ustate(prog, up=True):
    if up: h = prog; return (h // 2, h // 2) if h % 2 == 0 else ((h - 1) // 2, (h + 1) // 2)
    g = prog; return (-(g // 2), -(g // 2)) if g % 2 == 0 else (-((g + 1) // 2), -((g - 1) // 2))
configs = {((0, 0), (0, 0)), ((-1, 0), (0, 0)), ((0, 0), (0, 1)), (ustate(0), ustate(1)), (ustate(1, False), ustate(0, False))}
for h0 in (0, 1):
    for dd in (1, 2, 3): configs.add((ustate(h0), ustate(h0 + dd)))
for g1 in (0, 1):
    for dd in (1, 2, 3): configs.add((ustate(g1 + dd, False), ustate(g1, False)))
configs = sorted(configs)

def mat(g, unit, col): return ((1 if g == "L" else 0) + unit + col) % 2
def build_insts(cfg, single=False):
    (u0, l0), (u1, l1) = cfg
    ins = []
    for col in (0, 1):     # column c and its right neighbour c+1 (lockstep)
        ins += [(("U", 0, col), (2 * col, u0)), (("L", 0, col), (2 * col, l0))]
        if not single: ins += [(("U", 1, col), (2 * col, u1 + P)), (("L", 1, col), (2 * col, l1 + P))]
    return ins
def pc(a, off): return (a[0] - off[0], a[1], a[2] - off[1])
ABS = [(d, z, y) for d in range(-1, 5) for z in range(ZM + 1) for y in range(YL - 4, YH + P + 6)]
def constrain(cfg, single=False):
    ins = build_insts(cfg, single); rest = (cfg == ((0, 0), (0, 0))) and not single
    for a in ABS:
        vs = [occ[(gi[0], pc(a, o))] for gi, o in ins if pc(a, o) in cellset]
        if len(vs) > 1: m.Add(sum(vs) <= 1)
    for a in ABS:
        for v in NB:
            b = add(a, v)
            for (gi1, o1) in ins:
                p1 = pc(a, o1)
                if p1 not in cellset: continue
                for (gi2, o2) in ins:
                    p2 = pc(b, o2)
                    if p2 not in cellset: continue
                    # redstone rules (also same instance? no: own pieces never touch lamp/piston by separate rule below)
                    if gi1 != gi2:
                        pis = spd[p2] if gi2[0] == "U" else spu[p2]
                        m.AddBoolOr([RS[gi1[0]][p1].Not(), pis.Not()])
                        p3 = pc(add(b, (0, 0, -1)), o2)
                        if p3 in cellset:
                            m.AddBoolOr([RS[gi1[0]][p1].Not(), (spd[p3] if gi2[0] == "U" else spu[p3]).Not()])
                        allowed = rest and gi1[2] == gi2[2] and ((gi1[:2] == ("L", 1) and gi2[:2] == ("U", 0)) or (gi1[:2] == ("U", 0) and gi2[:2] == ("L", 1)))
                        if not allowed: m.AddBoolOr([RS[gi1[0]][p1].Not(), LAMP[gi2[0]][p2].Not()])
                    if v not in [(0, 0, 1), (0, 1, 0), (1, 0, 0)] or gi1 == gi2: continue
                    s1, n1, s2, n2 = S[gi1[0]][p1], nso[(gi1[0], p1)], S[gi2[0]][p2], nso[(gi2[0], p2)]
                    for sv, nv, sg, ng, scell, ncell, no in ((s1, n2, gi1, gi2, a, b, o2), (s2, n1, gi2, gi1, b, a, o1)):
                        if sg[1:] == ng[1:] and sg[0] != ng[0]:
                            face = (0, 0, -1) if ng[0] == "U" else (0, 0, 1)
                            if add(ncell, face) == scell:
                                pcn = pc(ncell, no); piston = spd if ng[0] == "U" else spu
                                m.AddBoolOr([sv.Not(), nv.Not(), piston[pcn]]); continue
                        m.AddBoolOr([sv.Not(), nv.Not()])
                    if mat(*gi1) == mat(*gi2): m.AddBoolOr([s1.Not(), s2.Not()])
for cfg in configs: constrain(cfg)
for st in ((0, 0), (0, 1)): constrain((st, (0, 0)), single=True)
# own redstone never next to own lamp / own pistons (both states)
for g in G:
    for c in cells:
        for v in NB:
            n = add(c, v)
            if n in cellset:
                for g2 in G:
                    for dy in ((0,) if g == g2 else (0, 1, -1)):
                        n2 = (n[0], n[1], n[2] + dy)
                        if n2 in cellset:
                            m.AddBoolOr([RS[g][c].Not(), LAMP[g2][n2].Not()])
# lamp lit at rest by neighbour unit (same column)
for a_ in cells:
    lu, ll = [], []
    for v in NB:
        n = add(a_, v)
        t = (n[0], n[1], n[2] - P)
        if t in cellset: lu.append(RS["L"][t])
        t = (n[0], n[1], n[2] + P)
        if t in cellset: ll.append(RS["U"][t])
    m.AddBoolOr(lu + [LAMP["U"][a_].Not()]); m.AddBoolOr(ll + [LAMP["L"][a_].Not()])
# stops
def coll(A, B):
    bs = []
    for a in ABS:
        for (gA, oA) in A:
            pa = (a[0], a[1], a[2] - oA)
            if pa not in cellset: continue
            for (gB, oB) in B:
                pb = (a[0], a[1], a[2] - oB)
                if pb not in cellset: continue
                b = m.NewBoolVar(""); m.AddBoolAnd([occ[(gA, pa)], occ[(gB, pb)]]).OnlyEnforceIf(b); bs.append(b)
    return bs
m.AddBoolOr(coll([("L", 1)], [("U", P), ("L", P)]))
m.AddBoolOr(coll([("U", P - 1)], [("U", 0), ("L", 0)]))
m.Add(sum(occ[("U", c)] for c in cells) <= 12); m.Add(sum(occ[("L", c)] for c in cells) <= 12)
m.Minimize(sum(occ[(g, c)] for g in G for c in cells))
sol = cp_model.CpSolver(); sol.parameters.max_time_in_seconds = TL; sol.parameters.num_workers = 8
r = sol.Solve(m); print(sol.StatusName(r))
if r in (cp_model.OPTIMAL, cp_model.FEASIBLE):
    out = []
    for c in cells:
        for g in G:
            if sol.Value(S[g][c]): out.append((c, g, "S"))
            if sol.Value(LAMP[g][c]): out.append((c, g, "lamp"))
            elif sol.Value(RS[g][c]): out.append((c, g, "rs"))
            elif sol.Value(PL[g][c]): out.append((c, g, "P"))
        if sol.Value(spd[c]): out.append((c, "U", "spd"))
        if sol.Value(spu[c]): out.append((c, "L", "spu"))
        for k in OBSD:
            if sol.Value(ou[(c, k)]): out.append((c, "U", "obs-" + k))
            if sol.Value(ol[(c, k)]): out.append((c, "L", "obs-" + k))
    json.dump(out, open(OUT, "w"))
    sym = {"S": None, "P": "pi", "lamp": "L*", "rs": "Rr", "spd": "vv", "spu": "^^"}
    for d in D:
        print("plane", d)
        for y in range(YH, YL - 1, -1):
            row = ""
            for z in range(ZM + 1):
                ch = "."
                for (c, g, k) in out:
                    if c == (d, z, y):
                        i = 0 if g == "U" else 1
                        if k == "S": ch = "UH"[i] if True else ""
                        elif k.startswith("obs"): ch = "Oo"[i]
                        else: ch = sym[k][i]
                row += ch
            print(f"  y{y:3d} {row}")
