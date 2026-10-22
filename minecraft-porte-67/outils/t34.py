# Collage WorldEdit (serveur Fabric) via bot, puis pilotage
import os, subprocess, sys
os.environ["RCON_PORT"]="25576"
from sim import *
from gen_door import Door
from collections import Counter
T=int(sys.argv[1]); schem=sys.argv[2]
d=Door(W=67,N=12); B=d.build()
OX,OY,OZ=-40,-50,-30
def W_(p): return (OX+p[0], OY+p[1], OZ+p[2])
r.cmd("forceload add -100 -50 40 0"); r.cmd("gamerule randomTickSpeed 0"); r.cmd("tick freeze"); r.cmd(f"tick rate {RATE}")
r.cmd("op Testeur"); r.cmd("defaultgamemode creative")
xs=[p[0] for p in B]; ys=[p[1] for p in B]; zs=[p[2] for p in B]
mn=W_((0,0,0))
r.cmd("setblock %d %d %d glass"%(mn[0],mn[1]-1,mn[2]))
pr=subprocess.Popen(["node","../bot/paste.js",str(mn[0]),str(mn[1]),str(mn[2]),schem],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
import time
for i in range(60):
    if "Testeur" in r.cmd("list"): break
    time.sleep(0.5)
print(r.cmd("op Testeur")); r.cmd("gamemode creative Testeur")
o,_=pr.communicate(timeout=120); print("\n".join(l for l in o.splitlines() if l.startswith(("MSG","DONE","KICK","ERR"))))
units=d.units()
def check(off):
    bad=0
    for p,b in units.items():
        q=W_((p[0],p[1]+off,p[2]))
        if "passed" not in r.cmd(f"execute if block {q[0]} {q[1]} {q[2]} {b.split('[')[0]}"): bad+=1
    return bad
lev=W_(d.panel["open"]); print("levier présent :", "passed" in r.cmd("execute if block %d %d %d lever"%lev))
print("collé (tick 0) bad", check(0))
step(300); print("après 300 ticks bad", check(0))
def flip(kind):
    p=W_(d.panel[kind])
    on="passed" in r.cmd(f"execute if block {p[0]} {p[1]} {p[2]} lever[powered=true]")
    r.cmd(f"setblock {p[0]} {p[1]} {p[2]} lever[face=floor,facing=north,powered={'false' if on else 'true'}]")
flip("open"); step(T); print("open bad", check(d.D))
flip("close"); step(T); print("closed bad", check(0))
