# Enveloppe réelle balayée par une colonne (sans cadre) comparée à swept()
from sim import *
from gen_door import Door
import sys
N=int(sys.argv[1])
d=Door(W=1,N=N); B=d.build(fill=False)
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
static=set(B)-set(units)
cells=[(x,y,z) for x in range(-2,3) for z in range(-1,4) for y in range(-3,d.ytop+2) if (x,y,z) not in static]
seen=set()
def scan():
    for p in cells:
        q=W_(p)
        if "passed" not in r.cmd("execute if block %d %d %d air"%q): seen.add(p)
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
scan(); flip("open")
for t in range(int(sys.argv[2])): step(1); scan()
sw=d.swept()
extra=sorted(seen-sw)
print("cellules hors swept:", extra)
