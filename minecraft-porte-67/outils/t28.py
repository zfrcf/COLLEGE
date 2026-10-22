# Coller une section de porte générée dans le serveur et la piloter via les leviers
from sim import *
from gen_door import Door
import sys, time
W=int(sys.argv[1]); N=int(sys.argv[2]); T=int(sys.argv[3])
d=Door(W=W,N=N); import os; K=os.environ.get('KEEP'); B=d.build(fill=not os.environ.get('NOFILL'), keep=(eval('lambda p:'+K) if K else None))
OX,OY,OZ=-40,-50,-30
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
xs=[p[0] for p in B]; ys=[p[1] for p in B]; zs=[p[2] for p in B]
# nettoyage
for y0 in range(min(ys)-1, max(ys)+2, 8):
    r.cmd(f"fill {OX+min(xs)-1} {OY+y0} {OZ+min(zs)-1} {OX+max(xs)+1} {OY+min(y0+7,max(ys)+1)} {OZ+max(zs)+1} air")
step(2)
units=d.units()
tower={p for p,b in B.items() if p[2]==-4 and "observer" in b}
feedrep={p for p,b in B.items() if "delay=4" in b}
def put(p,b): r.cmd("setblock %d %d %d %s"%(W_(p)+(b,)))
order1=[p for p in B if p not in units and p not in tower and p not in feedrep]
for p in order1: put(p,B[p])
un=sorted(units, key=lambda p: "observer" in units[p])
for p in un: put(p,B[p])
for p in sorted(tower, key=lambda p:p[1]): put(p,B[p])
step(300)
for p in feedrep: put(p,B[p])
step(20)
from collections import Counter
def check(off):
    bad=Counter()
    for p,b in units.items():
        q=W_((p[0],p[1]+off,p[2]))
        if "passed" not in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} {b.split('[')[0]}"): bad[p[0]]+=1
    return sum(bad.values()), dict(sorted(bad.items()))
print("built bad", check(0), "units", len(units))
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
flip("open"); step(T); print("open bad", check(d.D))
flip("close"); step(T); print("closed bad", check(0))
