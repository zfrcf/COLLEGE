# Cycles supplémentaires + vérification du passage libre (porte déjà construite par t32)
from sim import *
from gen_door import Door
from collections import Counter
d=Door(W=67,N=12); B=d.build()
OX,OY,OZ=-40,-50,-30
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
units=d.units()
def check(off):
    bad=0
    for p,b in units.items():
        q=W_((p[0],p[1]+off,p[2]))
        if "passed" not in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} {b.split('[')[0]}"): bad+=1
    return bad
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
# zone de référence vide
RX,RY,RZ=400,0,400
r.cmd(f"forceload add {RX} {RZ} {RX+70} {RZ+20}")
r.cmd(f"fill {RX} {RY} {RZ} {RX+66} {RY+66} {RZ} air"); step(2)
def clear():
    nb=0
    for z in range(-4, 18):
        a=W_((0,0,z)); b=W_((66,66,z))
        if "passed" not in r.cmd(f"execute if blocks {a[0]} {a[1]} {a[2]} {b[0]} {b[1]} {b[2]} {RX} {RY} {RZ} all"): nb+=1; print("  tranche z",z,"non vide")
    return nb
print("fermée : tranches non vides", clear())
for c in (2,3):
    flip("open"); step(2500); print("cycle",c,"ouvert bad", check(d.D), "tranches non vides", clear())
    flip("close"); step(2500); print("cycle",c,"fermé bad", check(0))
