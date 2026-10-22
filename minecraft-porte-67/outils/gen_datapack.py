# Datapack vanilla 1.21.1 qui construit la porte dans l'ordre validé (évite les déclenchements parasites)
import sys, os, json, shutil
from gen_door import Door
W=int(sys.argv[1]); N=int(sys.argv[2]); out=sys.argv[3]
d=Door(W=W,N=N); B=d.build()
units=d.units()
tower={p for p,b in B.items() if p[2]==-4 and "observer" in b}
feedrep={p for p,b in B.items() if "delay=4" in b}
xs=[p[0] for p in B]; ys=[p[1] for p in B]; zs=[p[2] for p in B]
x0,x1,y0,y1,z0,z1=min(xs),max(xs),min(ys),max(ys),min(zs),max(zs)
def sb(p,b): return "setblock ~%d ~%d ~%d %s" % (p[0],p[1],p[2],b)
fn=os.path.join(out,"data","porte","function")
shutil.rmtree(out, ignore_errors=True); os.makedirs(fn)
json.dump({"pack":{"description":"Porte géante %dx%d à machines volantes"%(W,d.H),
    "pack_format":48, "supported_formats":{"min_inclusive":48,"max_inclusive":999},
    "min_format":48, "max_format":999}}, open(os.path.join(out,"pack.mcmeta"),"w"), ensure_ascii=False, indent=1)
# message au chargement, pour vérifier que le pack est bien actif
tg=os.path.join(out,"data","minecraft","tags","function"); os.makedirs(tg)
json.dump({"values":["porte:charge"]}, open(os.path.join(tg,"load.json"),"w"))
open(os.path.join(fn,"charge.mcfunction"),"w").write('tellraw @a {"text":"[Porte] Datapack chargé. Place-toi au coin bas-gauche de l\'ouverture et tape /function porte:construire","color":"aqua"}\n')
L=["# Lancer debout au coin bas-gauche de l'ouverture (côté façade). La porte s'étend vers l'est (+X) et le sud (+Z).",
   "kill @e[type=marker,tag=porte_origine]",
   "summon marker ~ ~ ~ {Tags:[\"porte_origine\"]}"]
# 1) vider le volume
step=max(1, 32000//((x1-x0+1)*(z1-z0+1)))
y=y0
while y<=y1:
    L.append("fill ~%d ~%d ~%d ~%d ~%d ~%d air"%(x0,y,z0,x1,min(y+step-1,y1),z1)); y+=step
# 2) cadre et composants fixes, 3) modules (observateurs en dernier), 4) tours d'observateurs
for p in [p for p in B if p not in units and p not in tower and p not in feedrep]: L.append(sb(p,B[p]))
for p in sorted(units, key=lambda p: "observer" in units[p]): L.append(sb(p,B[p]))
for p in sorted(tower, key=lambda p:p[1]): L.append(sb(p,B[p]))
L.append("schedule function porte:finir 15s")
L.append("tellraw @a {\"text\":\"Porte : construction en cours, finalisation dans 15 s...\",\"color\":\"yellow\"}")
open(os.path.join(fn,"construire.mcfunction"),"w").write("\n".join(L)+"\n")
F=["execute as @e[type=marker,tag=porte_origine,limit=1] at @s run function porte:finir_ici"]
open(os.path.join(fn,"finir.mcfunction"),"w").write("\n".join(F)+"\n")
G=[sb(p,B[p]) for p in feedrep]
G.append("tellraw @a {\"text\":\"Porte prête : levier de gauche = ouvrir, levier de droite = fermer.\",\"color\":\"green\"}")
open(os.path.join(fn,"finir_ici.mcfunction"),"w").write("\n".join(G)+"\n")
print(len(L), "commandes ; panneau", d.panel)
