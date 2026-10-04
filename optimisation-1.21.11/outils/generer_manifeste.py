#!/usr/bin/env python3
"""Régénère pack-manifest.json pour la 1.21.11 à partir du manifeste 26.2 (métadonnées éditoriales)
et des fabric.mod.json des nouveaux jars (versions, dépendances, modules fournis)."""
import json, sys, zipfile, io, os
ancien = json.load(open(sys.argv[1], encoding="utf-8"))
dossier = sys.argv[2]
sortie = sys.argv[3]
IGNORES = {"minecraft", "fabricloader", "java"}

def lire_fmj(z):
    return json.loads(z.read("fabric.mod.json").decode("utf-8-sig"))

def fournit_de(z, fmj, acc):
    acc[fmj["id"]] = fmj["version"]
    for p in fmj.get("provides", []) or []:
        acc[p] = fmj["version"]
    for j in fmj.get("jars", []) or []:
        try:
            sub = zipfile.ZipFile(io.BytesIO(z.read(j["file"])))
            sfm = lire_fmj(sub)
            fournit_de(sub, sfm, acc)
        except KeyError:
            pass
    return acc

def normaliser_contrainte(v):
    if isinstance(v, list):
        return " || ".join(str(x) for x in v)
    return str(v)

jars = {}
for f in os.listdir(dossier):
    if f.endswith(".jar"):
        z = zipfile.ZipFile(os.path.join(dossier, f))
        fmj = lire_fmj(z)
        jars[fmj["id"]] = (f, z, fmj)

nouveau = {"version_pack": "1.0.0", "minecraft": "1.21.11", "categories": ancien["categories"], "mods": []}
manquants = []
for m in ancien["mods"]:
    if m["id"] not in jars:
        manquants.append(m["id"]); continue
    f, z, fmj = jars[m["id"]]
    n = dict(m)
    n["fichier"] = f
    n["version"] = fmj["version"]
    n["depends"] = {k: normaliser_contrainte(v) for k, v in (fmj.get("depends") or {}).items() if k not in IGNORES}
    n["breaks"] = {k: normaliser_contrainte(v) for k, v in (fmj.get("breaks") or {}).items() if k not in IGNORES}
    n["fournit"] = fournit_de(z, fmj, {})
    nouveau["mods"].append(n)
inconnus = sorted(set(jars) - {m["id"] for m in ancien["mods"]})
if manquants or inconnus:
    print("MANQUANTS:", manquants, "INCONNUS:", inconnus, file=sys.stderr)
json.dump(nouveau, open(sortie, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
print(f"{len(nouveau['mods'])} mods écrits dans {sortie}")
