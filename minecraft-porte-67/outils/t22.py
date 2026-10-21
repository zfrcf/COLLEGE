from sim import *
from unit2 import *
import sys
NAMES=["air","slime_block","honey_block","observer[powered=true]","observer","sticky_piston[extended=true]","sticky_piston","piston_head","moving_piston","obsidian","light_gray_concrete","gray_concrete","redstone_lamp[lit=true]","redstone_lamp","redstone_block"]
CH={"air":".","slime_block":"S","honey_block":"H","observer[powered=true]":"Ø","observer":"O","sticky_piston[extended=true]":"E","sticky_piston":"T","piston_head":"h","moving_piston":"m","obsidian":"X","light_gray_concrete":"f","gray_concrete":"n","redstone_lamp[lit=true]":"*","redstone_lamp":"l","redstone_block":"R"}
def blk(x,y,z):
    for b in NAMES:
        if "passed" in r.cmd(f"execute if block {x} {y} {z} {b}"): return CH[b]
    return "?"
u=Unit(sys.argv[1] if len(sys.argv)>1 else "sol2_P6.json",6); P=6
X,Y,Z=20,-40,20
ys=range(Y-2,Y+10)
def line(): return " ".join("".join(blk(X+d,y,Z+z) for y in ys) for d,z in ((0,1),(0,2),(1,1),(1,2)))
r.cmd(f"fill {X-1} {Y-12} {Z-1} {X+2} {Y+30} {Z+7} air"); step(2)
def A(c,base): return (X+c[0], base+c[2], Z+c[1])
for c in u.up_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,Y))
for c in u.down_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,Y))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y))
if "nodn" not in sys.argv:
    for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y))
for (c,g,b) in sorted(u.blocks(0), key=lambda t:"observer" in t[2]): r.cmd("setblock %d %d %d %s"%(A(c,Y)+(b,)))
step(30); print("cols: d0z1 d0z2 d1z1 d1z2 ; built", line())
for c in u.up_stop_cells(): r.cmd("setblock %d %d %d air"%A(c,Y))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d air"%A(c,Y))
if 'nolamp' in u.__dict__.get('path','') or len(sys.argv)>2:
    c,k=u.ou; w=add(c,D[k[4:]]); a=A(w,Y); r.cmd('setblock %d %d %d air'%a); r.cmd('setblock %d %d %d stone'%a)
for i in range(22): step(1); print(f"{i:3d}", line())
