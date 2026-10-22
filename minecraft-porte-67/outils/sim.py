import time
from rcon import Rcon
import os
r=Rcon(port=int(os.environ.get("RCON_PORT","25575")))
RATE=100
r.cmd(f'tick rate {RATE}')
import re as _re
def gametime():
    return int(_re.search(r"(\d+)", r.cmd("time query gametime")).group(1))
def step(n=1):
    g0 = gametime()
    r.cmd(f"tick step {n}")
    while gametime() < g0 + n:
        time.sleep(0.02)
def blk(x,y,z):
    # identify block via a list of candidates
    for b in ["air","slime_block","honey_block","observer","sticky_piston","piston","piston_head","moving_piston","stone","obsidian","redstone_block","white_concrete","smooth_stone","redstone_wire","repeater","target","note_block","glass"]:
        if "passed" in r.cmd(f"execute if block {x} {y} {z} {b}"): return b
    return "?"
def state(x,y,z,prop,vals):
    for v in vals:
        pass
def dump(x0,y0,z0,x1,y1,z1,ab=None):
    ab = ab or {"air":".","slime_block":"S","honey_block":"H","observer":"O","sticky_piston":"T","piston":"P","piston_head":"h","moving_piston":"m","stone":"#","obsidian":"X","redstone_block":"R","white_concrete":"W","glass":"g","target":"t","note_block":"n"}
    out=[]
    for y in range(y1,y0-1,-1):
        rows=[]
        for z in range(z0,z1+1):
            rows.append("".join(ab.get(blk(x,y,z),"?") for x in range(x0,x1+1)))
        out.append(f"y{y-y0}: "+" | ".join(rows))
    return "\n".join(out)
AB={"air":".","slime_block":"S","honey_block":"H","observer":"O","sticky_piston":"T","piston":"P","piston_head":"h","moving_piston":"m","stone":"#","obsidian":"X","redstone_block":"R","white_concrete":"W","glass":"g","target":"t","note_block":"n","black_concrete":"K","white_glazed_terracotta":"G"}
def col(x,y0,y1,z):
    return "".join(AB.get(blk(x,y,z),"?") for y in range(y0,y1+1))
