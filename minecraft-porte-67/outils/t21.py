from sim import *
from unit2 import *
import sys
AB.update({"light_gray_concrete":"f","gray_concrete":"n","redstone_lamp":"L","redstone_block":"R"})
NAMES=["air","slime_block","honey_block","observer","sticky_piston","piston_head","moving_piston","obsidian","light_gray_concrete","gray_concrete","stone","redstone_lamp","redstone_block"]
def blk(x,y,z):
    for b in NAMES:
        if "passed" in r.cmd(f"execute if block {x} {y} {z} {b}"): return b
    return "?"
path=sys.argv[1]; P=int(sys.argv[2]); N=int(sys.argv[3]); H=int(sys.argv[4]); T=int(sys.argv[5]); every=int(sys.argv[6])
u=Unit(path,P)
X,Y,Z=20,-40,20
top=Y+P*N
ys=range(Y-4,top+H+4)
def line():
    return " || ".join(" ".join("".join(AB.get(blk(X+d,y,Z+z),"?") for y in ys) for z in range(3)) for d in (0,1))
r.cmd(f"fill {X-1} {Y-12} {Z-1} {X+2} {top+H+12} {Z+7} air"); step(2)
def A(c,base): return (X+c[0], base+c[2], Z+c[1])
topbase=Y+P*(N-1)
for c in u.up_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,topbase))
for c in u.down_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,Y))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,topbase))
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y))
for j in range(N):
    for (c,g,b) in sorted(u.blocks(j), key=lambda t:"observer" in t[2]):
        r.cmd("setblock %d %d %d %s"%(A(c,Y+P*j)+(b,)))
step(30); s0=line(); print("built", s0)
mode=sys.argv[7] if len(sys.argv)>7 else "both"
def go(lbl):
    for i in range(T):
        step(1)
        if every and i%every==0: print(f"{i:4d} ", line())
    print(lbl, line())
# OPEN (up)
for c in u.up_stop_cells(): r.cmd("setblock %d %d %d air"%A(c,topbase)); r.cmd("setblock %d %d %d obsidian"%A(c,topbase+H))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d air"%A(c,topbase))
go("open ")
if mode=="up": sys.exit()
# CLOSE (down): phantom below unit0 at open position: place redstone, wait, remove
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d air"%A(c,Y))
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y+H))
step(10)
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d air"%A(c,Y+H))
go("close")
s1=line(); print("SAME AS BUILT:", s1==s0)
