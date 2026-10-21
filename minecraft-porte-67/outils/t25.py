# full-height column test (no per-tick printing): open then close, compare
from sim import *
from unit2 import *
import sys, time
NAMES=["air","slime_block","honey_block","observer","sticky_piston","piston_head","moving_piston","obsidian","light_gray_concrete","gray_concrete","stone","redstone_lamp","redstone_block"]
def blk(x,y,z):
    for b in NAMES:
        if "passed" in r.cmd(f"execute if block {x} {y} {z} {b}"): return b
    return "?"
path=sys.argv[1]; P=int(sys.argv[2]); N=int(sys.argv[3]); H=int(sys.argv[4]); T=int(sys.argv[5])
u=Unit(path,P)
X,Y,Z=10,-58,10
top=Y+P*N
def A(c,base): return (X+c[0], base+c[2], Z+c[1])
def unitcells(base):
    return {A(c,base):b for (c,g,b) in u.blocks(0)}
def check(bases):
    bad=0
    for j,base in enumerate(bases):
        for (c,g,b) in u.blocks(j):
            p=A(c,base); name=b.split("[")[0]
            if blk(*p)!=name: bad+=1
    return bad
r.cmd(f"fill {X-1} {Y-6} {Z-1} {X+2} {top+H+10} {Z+4} air"); step(2)
topbase=Y+P*(N-1)
for c in u.up_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,topbase+H))
for c in u.down_stop_cells(): r.cmd("setblock %d %d %d obsidian"%A(c,Y))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,topbase))
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y))
for j in range(N):
    for (c,g,b) in sorted(u.blocks(j), key=lambda t:"observer" in t[2]):
        r.cmd("setblock %d %d %d %s"%(A(c,Y+P*j)+(b,)))
step(30)
bases=[Y+P*j for j in range(N)]
print("built bad:",check(bases))
# open: ON-edge pulse on top unit's U lamp via a temporary redstone block at phantom position, 20 ticks
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d air"%A(c,Y))
for c in u.phantom_up_rs(): r.cmd("setblock %d %d %d air"%A(c,topbase))
t0=time.time(); step(T); time.sleep(1)
print("open bad:",check([b+H for b in bases]), "elapsed",round(time.time()-t0,1))
CH={"air":".","slime_block":"S","honey_block":"H","observer":"O","sticky_piston":"T","piston_head":"h","moving_piston":"m","obsidian":"X","light_gray_concrete":"f","gray_concrete":"n","stone":"#","redstone_lamp":"L","redstone_block":"R"}
for d,z in ((0,0),(0,1),(0,2),(1,0),(1,1),(1,2)):
    print(d,z,"".join(CH.get(blk(X+d,y,Z+z),"?") for y in range(Y-5,top+H+6)))
if "stop" in sys.argv: sys.exit()
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d redstone_block"%A(c,Y+H))
step(10)
for c in u.phantom_dn_rs(): r.cmd("setblock %d %d %d air"%A(c,Y+H))
step(T); time.sleep(1)
print("closed bad:",check(bases))
