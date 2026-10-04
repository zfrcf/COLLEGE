#!/usr/bin/env python3
"""Assemble le jar tout-en-un : jar du pack (Gradle) + mods imbriqués + pack-manifest.json.
Usage : assembler.py <optimisation-pack-1.0.0.jar> <dossier mods> <pack-manifest.json> <sortie.jar>"""
import json, sys, zipfile
pack, dossier, manifeste, sortie = sys.argv[1:5]
man = json.load(open(manifeste, encoding="utf-8"))
src = zipfile.ZipFile(pack)
with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as out:
    for info in src.infolist():
        data = src.read(info.filename)
        if info.filename == "fabric.mod.json":
            fmj = json.loads(data.decode("utf-8"))
            fmj["jars"] = [{"file": "META-INF/jars/" + m["fichier"]} for m in man["mods"]]
            data = json.dumps(fmj, indent=2, ensure_ascii=False).encode("utf-8")
        out.writestr(info.filename, data)
    out.writestr("pack-manifest.json", json.dumps(man, indent=2, ensure_ascii=False).encode("utf-8"))
    out.writestr("META-INF/LICENCE-mods.txt",
                 "Les mods embarqués conservent leurs licences respectives (voir chaque jar dans META-INF/jars).\n".encode("utf-8"))
    for m in man["mods"]:
        out.write(f"{dossier}/{m['fichier']}", "META-INF/jars/" + m["fichier"])
print("écrit", sortie)
