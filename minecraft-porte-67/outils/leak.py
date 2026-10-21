# BFS for a 1x1x2 entity through the closed comb door (no gravity = conservative)
import json, sys
from collections import deque
from unit2 import Unit
u=Unit("sol2_P6.json",6); P=6
ZW=int(sys.argv[1]) if len(sys.argv)>1 else 4   # zone pitch in Z
NCOL=12; N=12
solid=set()
for x in range(NCOL):
    zone=x%3; z0=zone*ZW
    for j in range(N):
        for (c,g,k) in u.sol:
            d,z,y=c
            solid.add((x+d, y+P*j, z0+z))
XS=range(0,NCOL); YS=range(2,60); ZS=range(-1, 3*ZW+1)
def free(x,y,z): return (x,y,z) not in solid and (x,y+1,z) not in solid
start=[(x,y,-1) for x in XS for y in YS]
seen=set(start); q=deque(start); hit=None
while q:
    x,y,z=q.popleft()
    if z==3*ZW: hit=(x,y,z); break
    for dx,dy,dz in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1)):
        n=(x+dx,y+dy,z+dz)
        if n[0] in XS and n[1] in YS and n[2] in ZS and n not in seen and free(*n):
            seen.add(n); q.append(n)
print("LEAK" if hit else "SEALED", hit)
