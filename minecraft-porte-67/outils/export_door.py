# Export de la porte générée en .schem / .litematic / .nbt
import sys, glob
sys.path.insert(0, glob.glob("/root/.claude/skills/synced/*/minecraft-schematics/scripts")[0])
from builder import SchematicBuilder
from gen_door import Door
W=int(sys.argv[1]); N=int(sys.argv[2]); out=sys.argv[3]; fmts=sys.argv[4].split(",")
d=Door(W=W,N=N); B=d.build()
import json, ast
st=json.load(open("states_%d_%d.json"%(W,N)))
for k,v in st.items(): B[ast.literal_eval(k)]=v
import os
if os.environ.get("OBSPOW"):
    for p,v in B.items():
        if "observer[" in v: B[p]=v.replace("]",",powered=true]")
b=SchematicBuilder(name="porte_67x67" if W==67 else f"porte_{W}x{N}", author="Antoine", version="1.21.1")
for p,s in B.items():
    if not s.startswith("minecraft:"): s="minecraft:"+s
    b.set(p[0],p[1],p[2],s)
print(b.stats()["dimensions"], len(B))
print(b.bounds())
print(b.save_all(out, formats=fmts))
# Version de données du jeu visé (26.2 = 4903), pour éviter une conversion depuis une ancienne version
import nbtlib, os
DV=int(os.environ.get("DATAVERSION","4903"))
for path in [out+".schem", out+".litematic"]:
    if not os.path.exists(path): continue
    f=nbtlib.load(path)
    root=f.get("Schematic", f)
    key="MinecraftDataVersion" if path.endswith(".litematic") else "DataVersion"
    root[key]=nbtlib.tag.Int(DV); f.save()
    print(path, key, DV)
