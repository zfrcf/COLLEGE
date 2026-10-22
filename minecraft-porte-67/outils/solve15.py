# solve15 : module plan unique pour colonnes jointives (pas 1) en synchronisme strict.
# Les voisins latéraux sont des copies (matériaux inversés), donc aucun contact latéral collant.
# Relâchements : face couverte modulo P par U ou L ; lampes en z=0 (déclenchement par l'avant) ou z=ZM (par l'arrière).
# Pattern coords: (d, z, y). d=0 main plane (tile at z=0), d=1 private lane. Unit in gapped state at offset 0.
import sys, itertools, json, os
OFF=set(os.environ.get('OFF','').split(','))
from ortools.sat.python import cp_model

P = int(sys.argv[1]) if len(sys.argv) > 1 else 6
ZM = int(sys.argv[2]) if len(sys.argv) > 2 else 5
YL, YH = -5, P + 5
D = [0]
cells = [(d, z, y) for d in D for z in range(ZM + 1) for y in range(YL, YH + 1)]
cellset = set(cells)
DIRS = {"up": (0, 0, 1), "down": (0, 0, -1), "south": (0, 1, 0), "north": (0, -1, 0), "east": (1, 0, 0), "west": (-1, 0, 0)}
def add(c, v): return (c[0] + v[0], c[1] + v[1], c[2] + v[2])
NB = [v for v in DIRS.values()]

m = cp_model.CpModel()
G = ["U", "L"]
S = {g: {c: m.NewBoolVar(f"s{g}{c}") for c in cells} for g in G}   # sticky
PL = {g: {c: m.NewBoolVar(f"p{g}{c}") for c in cells} for g in G}  # plain non-sticky
LAMP = {g: {c: m.NewBoolVar(f"lamp{g}{c}") for c in cells} for g in G}
RS = {g: {c: m.NewBoolVar(f"rs{g}{c}") for c in cells} for g in G}
for g in G:
    m.AddExactlyOne(LAMP[g].values()); m.AddExactlyOne(RS[g].values())
    for c in cells: m.Add(LAMP[g][c] + RS[g][c] <= PL[g][c])
spd = {c: m.NewBoolVar(f"spd{c}") for c in cells}   # U sticky piston facing down
spu = {c: m.NewBoolVar(f"spu{c}") for c in cells}   # L sticky piston facing up
OBSD = ["up", "down", "south", "north"]
ou = {(c, k): m.NewBoolVar(f"ou{c}{k}") for c in cells for k in OBSD}
ol = {(c, k): m.NewBoolVar(f"ol{c}{k}") for c in cells for k in OBSD}
m.AddExactlyOne(spd.values()); m.AddExactlyOne(spu.values())
m.AddExactlyOne(ou.values()); m.AddExactlyOne(ol.values())

def NS(g, c):  # non-sticky occupancy expression list
    if c not in cellset: return []
    if g == "U": return [PL["U"][c], spd[c]] + [ou[(c, k)] for k in OBSD]
    return [PL["L"][c], spu[c]] + [ol[(c, k)] for k in OBSD]
def ST(g, c): return [S[g][c]] if c in cellset else []
def OCC(g, c): return NS(g, c) + ST(g, c)

occ = {}
for g in G:
    for c in cells:
        v = m.NewBoolVar(f"occ{g}{c}"); m.Add(sum(OCC(g, c)) == v); occ[(g, c)] = v
nso = {}
for g in G:
    for c in cells:
        v = m.NewBoolVar(f"ns{g}{c}"); m.Add(sum(NS(g, c)) == v); nso[(g, c)] = v
for c in cells:
    m.Add(occ[("U", c)] + occ[("L", c)] <= 1)
    # observers in lane may not face east (buffer); main plane east ok (lane)
    if c[0] == 1:
        m.Add(ou[(c, "east")] == 0); m.Add(ol[(c, "east")] == 0)
    # observers watched cell must be inside grid
    for k in OBSD:
        if add(c, DIRS[k]) not in cellset:
            m.Add(ou[(c, k)] == 0); m.Add(ol[(c, k)] == 0)

# face : chaque rangée couverte (modulo P) en z=0 par U ou L
for y in range(P):
    opts=[]
    for k in range(-3, 4):
        c=(0,0,y+k*P)
        if c in cellset: opts += [occ[("U",c)], occ[("L",c)]]
    m.AddBoolOr(opts)
# lampes accessibles au cadre (avant z=0 ou arrière z=ZM)
for g in G:
    for c in cells:
        if c[1] not in (0, ZM): m.Add(LAMP[g][c] == 0)
# nothing of the unit in front (z<0) - grid starts at z=0 so fine.

def g_occ(g, c): return occ[(g, c)] if c in cellset else None

# pistons: gap + actor sticky
for c in cells:
    f = add(c, (0, 0, -1)); a = add(c, (0, 0, -2))
    if f not in cellset or a not in cellset: m.Add(spd[c] == 0)
    else:
        m.Add(occ[("U", f)] + occ[("L", f)] == 0).OnlyEnforceIf(spd[c])
        m.Add(S["L"][a] == 1).OnlyEnforceIf(spd[c])
    f = add(c, (0, 0, 1)); a = add(c, (0, 0, 2))
    if f not in cellset or a not in cellset: m.Add(spu[c] == 0)
    else:
        m.Add(occ[("U", f)] + occ[("L", f)] == 0).OnlyEnforceIf(spu[c])
        m.Add(S["U"][a] == 1).OnlyEnforceIf(spu[c])
# observers: back adjacent to own piston (direct power); not on piston face side
for c in cells:
    for k in OBSD:
        b = add(c, tuple(-x for x in DIRS[k]))
        if b in cellset and k != "down": m.AddImplication(ou[(c, k)], spd[b])
        else: m.Add(ou[(c, k)] == 0)
        if b in cellset and k != "up": m.AddImplication(ol[(c, k)], spu[b])
        else: m.Add(ol[(c, k)] == 0)
# holders
for g in G:
    for c in cells:
        nbs = [S[g][add(c, v)] for v in NB if add(c, v) in cellset]
        m.Add(sum(nbs) >= 1).OnlyEnforceIf(nso[(g, c)])
# connectivity of stickies to root (levels)
MAXL = 40
for g in G:
    lvl = {c: m.NewIntVar(0, MAXL, f"lv{g}{c}") for c in cells}
    root = {c: m.NewBoolVar(f"root{g}{c}") for c in cells}
    for c in cells:
        if g == "U":
            a = add(c, (0, 0, -2))  # spu at a => root at c
            m.Add(root[c] == (spu[a] if a in cellset else 0))
        else:
            a = add(c, (0, 0, 2))
            m.Add(root[c] == (spd[a] if a in cellset else 0))
    for c in cells:
        m.Add(lvl[c] == 0).OnlyEnforceIf(root[c])
        # non-root sticky needs a sticky neighbor with lower level
        cand = []
        for v in NB:
            n = add(c, v)
            if n in cellset:
                b = m.NewBoolVar("")
                m.AddImplication(b, S[g][n]); m.Add(lvl[n] < lvl[c]).OnlyEnforceIf(b)
                cand.append(b)
        m.AddBoolOr(cand + [root[c], S[g][c].Not()])

# configurations: group instance offsets (dy) for (unit j: U,L ; unit j+1: U,L)
def ustate(prog, up=True):
    if up:
        h = prog
        return (h // 2, h // 2) if h % 2 == 0 else ((h - 1) // 2, (h + 1) // 2)
    g = prog
    return (-(g // 2), -(g // 2)) if g % 2 == 0 else (-((g + 1) // 2), -((g - 1) // 2))
configs = set()
configs.add(((0, 0), (0, 0)))
for h0 in (0, 1):
    for dd in (1, 2, 3):
        configs.add((ustate(h0), ustate(h0 + dd)))
configs.add((ustate(0), ustate(1)))
for g1 in (0, 1):
    for dd in (1, 2, 3):
        configs.add((ustate(g1 + dd, False), ustate(g1, False)))
configs.add((ustate(1, False), ustate(0, False)))
# approach-free configs
configs.add(((-1, 0), (0, 0)))   # j at C(-1) up-approach vs j+1 rest
configs.add(((0, 0), (0, 1)))    # j+1 at C(0) down-approach vs j rest
configs = sorted(configs)
print("configs", configs)

MATS = {("U", 0): 0, ("L", 0): 1, ("U", 1): 1, ("L", 1): 0} if (len(sys.argv) <= 4 or sys.argv[4] == "alt") else {("U", 0): 0, ("L", 0): 1, ("U", 1): 0, ("L", 1): 1}
def compatible_sticky(gi1, gi2): return MATS[gi1] != MATS[gi2]

def pattern_cell(a, off): return (a[0], a[1], a[2] - off)

def add_config_constraints(cfg, single=False):
    (u0, l0), (u1, l1) = cfg
    insts = [(("U", 0), u0), (("L", 0), l0)]
    if not single: insts += [(("U", 1), u1 + P), (("L", 1), l1 + P)]
    # absolute cells range
    ys = range(YL - 4, YH + P + 6)
    abscells = [(d, z, y) for d in D for z in range(ZM + 1) for y in ys]
    def occ_at(gi, off, a):
        p = pattern_cell(a, off)
        return occ[(gi[0], p)] if p in cellset else None
    def st_at(gi, off, a):
        p = pattern_cell(a, off)
        return S[gi[0]][p] if p in cellset else None
    def ns_at(gi, off, a):
        p = pattern_cell(a, off)
        return nso[(gi[0], p)] if p in cellset else None
    for a in abscells:
        vs = [occ_at(gi, off, a) for gi, off in insts]
        vs = [v for v in vs if v is not None]
        if len(vs) > 1: m.Add(sum(vs) <= 1)
    for a in abscells:
        for v in [(0, 0, 1), (0, 1, 0), (1, 0, 0)]:
            b = add(a, v)
            for (gi1, o1), (gi2, o2) in itertools.permutations(insts, 2):
                if gi1 == gi2: continue
                s1 = st_at(gi1, o1, a); n1 = ns_at(gi1, o1, a)
                s2 = st_at(gi2, o2, b); n2 = ns_at(gi2, o2, b)
                if s1 is None and n1 is None: continue
                if s2 is None and n2 is None: continue
                # sticky vs nonsticky -> glue, unless actor exception
                for sv, nv, sg, ng, scell, ncell, so, no in ((s1, n2, gi1, gi2, a, b, o1, o2), (s2, n1, gi2, gi1, b, a, o2, o1)):
                    if sv is None or nv is None: continue
                    if sg[1] == ng[1] and sg[0] != ng[0]:
                        # same unit, other half: allowed only if nonsticky is the piston whose face is the sticky cell
                        pc = pattern_cell(ncell, no)
                        face = (0, 0, -1) if ng[0] == "U" else (0, 0, 1)
                        piston = spd if ng[0] == "U" else spu
                        if add(ncell, face) == scell and pc in cellset:
                            # forbid nonsticky other than that piston
                            other = m.NewBoolVar("")
                            m.Add(other == nv - piston[pc]) if False else None
                            m.AddBoolOr([sv.Not(), nv.Not(), piston[pc]])
                            continue
                    m.AddBoolOr([sv.Not(), nv.Not()])
                if s1 is not None and s2 is not None and not compatible_sticky(gi1, gi2):
                    m.AddBoolOr([s1.Not(), s2.Not()])

if 'cfg' not in OFF:
  for cfg in configs: add_config_constraints(cfg)
if 'single' not in OFF:
  for st in ((0, 0), (0, 1)): add_config_constraints((st, (0, 0)), single=True)

# sensors: observers watch own lamp; lamp lit at rest by neighbour unit redstone block
for c in cells:
    for k in OBSD:
        w = add(c, DIRS[k])
        if w in cellset:
            m.AddImplication(ou[(c, k)], LAMP["U"][w]); m.AddImplication(ol[(c, k)], LAMP["L"][w])
        else:
            m.Add(ou[(c, k)] == 0); m.Add(ol[(c, k)] == 0)
for a_ in cells:
    lits=[]; litl=[]
    for v in NB:
        n = add(a_, v)
        t = (n[0], n[1], n[2] - P)
        if t in cellset: lits.append(RS["L"][t])
        t = (n[0], n[1], n[2] + P)
        if t in cellset: litl.append(RS["U"][t])
    if 'lit' not in OFF:
      m.AddBoolOr(lits + [LAMP["U"][a_].Not()])
      m.AddBoolOr(litl + [LAMP["L"][a_].Not()])
# redstone/lamp/piston adjacency rules over configs
def rule_configs(cfg, single=False, rest=False):
    (u0, l0), (u1, l1) = cfg
    insts = [(("U", 0), u0), (("L", 0), l0)]
    if not single: insts += [(("U", 1), u1 + P), (("L", 1), l1 + P)]
    ys = range(YL - 4, YH + P + 6)
    for a_ in [(d, z, y) for d in D for z in range(ZM + 1) for y in ys]:
        for v in NB:
            b_ = add(a_, v)
            for (gi1, o1) in insts:
                p1 = pattern_cell(a_, o1)
                if p1 not in cellset: continue
                for (gi2, o2) in insts:
                    p2 = pattern_cell(b_, o2)
                    if p2 not in cellset: continue
                    # redstone next to piston (any) or next to the cell above a piston (quasi-connectivity)
                    pis = spd[p2] if gi2[0] == "U" else spu[p2]
                    m.AddBoolOr([RS[gi1[0]][p1].Not(), pis.Not()])
                    p3 = pattern_cell(add(b_, (0, 0, -1)), o2)
                    if p3 in cellset:
                        pis3 = spd[p3] if gi2[0] == "U" else spu[p3]
                        m.AddBoolOr([RS[gi1[0]][p1].Not(), pis3.Not()])
                    # redstone next to lamp: only allowed intended pairs at rest
                    allowed = rest and ((gi1 == ("L", 1) and gi2 == ("U", 0)) or (gi1 == ("U", 0) and gi2 == ("L", 1)))
                    if not allowed:
                        m.AddBoolOr([RS[gi1[0]][p1].Not(), LAMP[gi2[0]][p2].Not()])
if 'rules' not in OFF:
  for cfg in configs: rule_configs(cfg, rest=(cfg == ((0, 0), (0, 0))))
  for st in ((0, 0), (0, 1)): rule_configs((st, (0, 0)), single=True)

# stops
def collision(insA, insB):
    bs = []
    ys = range(YL - 4, YH + P + 6)
    for a in [(d, z, y) for d in D for z in range(ZM + 1) for y in ys]:
        for (gA, oA) in insA:
            pa = pattern_cell(a, oA)
            if pa not in cellset: continue
            for (gB, oB) in insB:
                pb = pattern_cell(a, oB)
                if pb not in cellset: continue
                b = m.NewBoolVar(""); m.AddBoolAnd([occ[(gA, pa)], occ[(gB, pb)]]).OnlyEnforceIf(b)
                bs.append(b)
    return bs
# up-stop: j at C(0) (L +1) vs j+1 rest: L_j collides
if 'stops' not in OFF: m.AddBoolOr(collision([("L", 1)], [("U", P), ("L", P)]))
# down-stop: j+1 at C(-1) (U at P-1) vs j rest: U_{j+1} collides
if 'stops' not in OFF: m.AddBoolOr(collision([("U", P - 1)], [("U", 0), ("L", 0)]))

# budget
if 'budget' not in OFF:
  m.Add(sum(occ[("U", c)] for c in cells) <= 12)
  m.Add(sum(occ[("L", c)] for c in cells) <= 12)
tot = sum(occ[(g, c)] for g in G for c in cells)
lane = sum(occ[(g, c)] for g in G for c in cells if c[0] == 1)
pass  # faisabilité seule

sol = cp_model.CpSolver()
sol.parameters.max_time_in_seconds = float(sys.argv[3]) if len(sys.argv) > 3 else 120
sol.parameters.num_workers = 2
sol.parameters.log_search_progress = False
r = sol.Solve(m)
print(sol.StatusName(r))
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
    json.dump(out, open(f"sol15_P{P}_Z{ZM}_{sys.argv[4] if len(sys.argv)>4 else 'alt'}.json", "w"))
    for d in D:
        print(f"plane d={d}  (rows top->bottom, cols z=0..{ZM})")
        for y in range(YH, YL - 1, -1):
            row = ""
            for z in range(ZM + 1):
                ch = "."
                for (c, g, k) in out:
                    if c == (d, z, y):
                        if k == "S": ch = "U" if g == "U" else "l"
                        elif k == "P": ch = "u" if g == "U" else "i"
                        elif k == "lamp": ch = "L" if g == "U" else "*"
                        elif k == "rs": ch = "R" if g == "U" else "r"
                        elif k == "spd": ch = "v"
                        elif k == "spu": ch = "^"
                        else: ch = "O" if g == "U" else "o"
                row += ch
            print(f"  y{y:3d} {row}")
    print("U count", sum(1 for o in out if o[1] == "U"), "L count", sum(1 for o in out if o[1] == "L"))
    print([o for o in out if "obs" in o[2] or o[2] in ("spd", "spu")])
