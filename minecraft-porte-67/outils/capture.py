# Construit la porte de façon ordonnée (comme t28), puis capture les états réels au repos -> states_W_N.json
from sim import *
from gen_door import Door
import sys, json
W=int(sys.argv[1]); N=int(sys.argv[2])
d=Door(W=W,N=N); B=d.build()
OX,OY,OZ=-40,-50,-30
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
xs=[p[0] for p in B]; ys=[p[1] for p in B]; zs=[p[2] for p in B]
for y0 in range(min(ys)-1, max(ys)+2, 8):
    r.cmd(f"fill {OX+min(xs)-1} {OY+y0} {OZ+min(zs)-1} {OX+max(xs)+1} {OY+min(y0+7,max(ys)+1)} {OZ+max(zs)+1} air")
step(2)
units=d.units()
tower={p for p,b in B.items() if p[2]==-4 and "observer" in b}
feedrep={p for p,b in B.items() if "delay=4" in b}
def put(p,b): r.cmd("setblock %d %d %d %s"%(W_(p)+(b,)))
for p in [p for p in B if p not in units and p not in tower and p not in feedrep]: put(p,B[p])
for p in sorted(units, key=lambda p: "observer" in units[p]): put(p,B[p])
for p in sorted(tower, key=lambda p:p[1]): put(p,B[p])
step(300)
for p in feedrep: put(p,B[p])
step(40)
def has(p, st):
    q=W_(p); return "passed" in r.cmd("execute if block %d %d %d %s"%(q+(st,)))
out={}
for p,b in B.items():
    base=b.split("[")[0]
    if base.endswith("redstone_lamp"):
        out[str(p)]="minecraft:redstone_lamp[lit=%s]"%("true" if has(p,"redstone_lamp[lit=true]") else "false")
    elif base.endswith("redstone_wire"):
        props=[]
        for side in ("north","south","east","west"):
            v=[c for c in ("none","side","up") if has(p,"redstone_wire[%s=%s]"%(side,c))]
            props.append("%s=%s"%(side,v[0]))
        pw=[k for k in range(16) if has(p,"redstone_wire[power=%d]"%k)][0]
        props.append("power=%d"%pw)
        out[str(p)]="minecraft:redstone_wire["+",".join(props)+"]"
    elif base.endswith("repeater"):
        if has(p,"repeater[powered=true]"): out[str(p)]=b.replace("]",",powered=true]")
    elif base.endswith("observer"):
        if has(p,"observer[powered=true]"): print("observateur alimenté au repos", p)
lit=sum(1 for v in out.values() if "lit=true" in v); print("lampes allumées", lit, "/", sum(1 for v in out.values() if "lamp" in v))
print("répéteurs alimentés", sum(1 for v in out.values() if "powered=true" in v))
json.dump(out, open("states_%d_%d.json"%(W,N),"w"))
