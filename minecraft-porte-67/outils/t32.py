# Construire via le datapack puis piloter
from sim import *
from gen_door import Door
from collections import Counter
import sys
W=int(sys.argv[1]); N=int(sys.argv[2]); T=int(sys.argv[3])
d=Door(W=W,N=N); B=d.build()
OX,OY,OZ=-40,-50,-30
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
print(r.cmd("reload")); step(5)
print(r.cmd("datapack list enabled"))
# remplir de pierre pour vérifier que le datapack vide bien le volume
print(r.cmd("execute positioned %d %d %d run function porte:construire"%(OX,OY,OZ)))
step(320)
units=d.units()
def check(off):
    bad=Counter()
    for p,b in units.items():
        q=W_((p[0],p[1]+off,p[2]))
        if "passed" not in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} {b.split('[')[0]}"): bad[p[0]]+=1
    return sum(bad.values()), dict(sorted(bad.items()))
fr=[p for p in d.blocks if "delay=4" in d.blocks[p]]
print("répéteurs finaux posés:", all("passed" in r.cmd("execute if block %d %d %d repeater"%W_(p)) for p in fr))
print("built bad", check(0))
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
flip("open"); step(T); print("open bad", check(d.D))
flip("close"); step(T); print("closed bad", check(0))
