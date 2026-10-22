# Coller le .nbt via /place template puis piloter les leviers
from sim import *
from gen_door import Door
from collections import Counter
import sys
W=int(sys.argv[1]); N=int(sys.argv[2]); T=int(sys.argv[3]); name=sys.argv[4]
d=Door(W=W,N=N); B=d.build()
OX,OY,OZ=-40,-50,-30
xs=[p[0] for p in B]; ys=[p[1] for p in B]; zs=[p[2] for p in B]
mn=(min(xs),min(ys),min(zs))
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
for y0 in range(min(ys)-1, max(ys)+2, 8):
    r.cmd(f"fill {OX+min(xs)-1} {OY+y0} {OZ+min(zs)-1} {OX+max(xs)+1} {OY+min(y0+7,max(ys)+1)} {OZ+max(zs)+1} air")
step(2)
q=W_(mn); print(r.cmd("place template minecraft:%s %d %d %d"%((name,)+q)))
step(300)
units=d.units()
def check(off):
    bad=Counter()
    for p,b in units.items():
        q=W_((p[0],p[1]+off,p[2]))
        if "passed" not in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} {b.split('[')[0]}"): bad[p[0]]+=1
    return sum(bad.values()), dict(sorted(bad.items()))
print("built bad", check(0))
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
flip("open"); step(T); print("open bad", check(d.D))
flip("close"); step(T); print("closed bad", check(0))
