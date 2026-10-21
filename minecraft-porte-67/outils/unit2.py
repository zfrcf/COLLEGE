import json
D={"up":(0,0,1),"down":(0,0,-1),"south":(0,1,0),"north":(0,-1,0),"east":(1,0,0)}
def add(a,b): return tuple(x+y for x,y in zip(a,b))
class Unit:
    def __init__(s, path, P):
        s.P=P; s.sol=[(tuple(c),g,k) for c,g,k in json.load(open(path))]
        s.occ={c:g for c,g,k in s.sol}
        s.ou=[(c,k) for c,g,k in s.sol if g=="U" and k.startswith("obs")][0]
        s.ol=[(c,k) for c,g,k in s.sol if g=="L" and k.startswith("obs")][0]
        s.rsU=[c for c,g,k in s.sol if g=="U" and k=="rs"]
        s.rsL=[c for c,g,k in s.sol if g=="L" and k=="rs"]
    def blocks(s, j, par=0):
        m=(par+j)%2
        um="slime_block" if m==0 else "honey_block"; lm="honey_block" if m==0 else "slime_block"
        out=[]
        for c,g,k in s.sol:
            if k=="S": b= um if g=="U" else lm
            elif k=="P": b="light_gray_concrete" if g=="U" else "gray_concrete"
            elif k=="lamp": b="redstone_lamp"
            elif k=="rs": b="redstone_block"
            elif k=="spd": b="sticky_piston[facing=down]"
            elif k=="spu": b="sticky_piston[facing=up]"
            else: b=f"observer[facing={k[4:]}]"
            out.append((c,g,b))
        return out
    def up_stop_cells(s):   # cells (unit-j coords) of phantom j+1 that block L_j at C(0)
        P=s.P; res=[]
        for c,g in s.occ.items():
            if g=="L":
                t=add(c,(0,0,1)); p=add(t,(0,0,-P))
                if p in s.occ: res.append(t)
        return res
    def down_stop_cells(s): # cells (unit-0 coords) of phantom -1 that block U_0 at C(-1)
        P=s.P; res=[]
        for c,g in s.occ.items():
            if g=="U":
                t=add(c,(0,0,-1)); q=add(t,(0,0,P))
                if q in s.occ: res.append(t)
        return res
    def phantom_up_rs(s):   # redstone of phantom j+1 (L) in unit-j coords
        return [add(c,(0,0,s.P)) for c in s.rsL]
    def phantom_dn_rs(s):   # redstone of phantom j-1 (U) in unit-0 coords
        return [add(c,(0,0,-s.P)) for c in s.rsU]
