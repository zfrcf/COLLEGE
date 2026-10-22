# Diagnostic : position de chaque module après ouverture (W petit)
from sim import *
from gen_door import Door
import sys
W=int(sys.argv[1]); N=int(sys.argv[2]); T=int(sys.argv[3])
exec(open("t28.py").read().split("print(\"built bad\"")[0].split("d=Door(W=W,N=N); import os; B=d.build(fill=not os.environ.get('NOFILL'))")[1].replace("","",0), globals()) if False else None
d=Door(W=W,N=N); import os; B=d.build(fill=not os.environ.get('NOFILL'))
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
step(20)
def tile_rows(x):
    # rangées occupées par slime/miel dans le plan principal z=zo(x), colonne x
    z=d.zo(x); out=""
    for y in range(-2, d.P*(d.N-1)+d.D+8):
        q=W_((x,y,z))
        if "passed" in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} slime_block"): out+="S"
        elif "passed" in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} honey_block"): out+="H"
        elif "passed" in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} air"): out+="."
        else: out+="#"
    return out
for x in range(W): print("avant", x, tile_rows(x))
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
flip("open")
prev=0
for t in (20,60,200,T):
    step(t-prev); prev=t
    for x in range(W): print(t, x, tile_rows(x))
