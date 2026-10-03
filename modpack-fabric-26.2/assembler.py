#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Assemble le mod unique « Optimisation 26.2 » :
    jar compilé (mod-unique/build/libs/optimisation-pack-<version>.jar)
  + tous les mods du catalogue imbriqués dans META-INF/jars/ (jar-in-jar Fabric)
  + pack-manifest.json (métadonnées lues par le mod dans le jeu)
  + fabric.mod.json dont la liste "jars" = mods actifs par défaut.

Usage : python assembler.py [--sortie fichier.jar] [--jar-mod chemin]
Les jars des mods sont pris dans .cache/ (téléchargés si absents) et mods-perso/.
"""

import argparse
import json
import re
import sys
import zipfile
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))
import gestionnaire as G  # noqa: E402

VERROUILLES = {
    "modmenu": "donne accès à cet écran",
    "cloth-config": "affiche cet écran",
    "fabric-api": "requis par Mod Menu et le gestionnaire",
}


def aplatir(contraintes: dict) -> dict:
    """Une liste de contraintes (= OU) devient une chaîne « a || b » comprise par Fabric et par le mod."""
    res = {}
    for k, v in contraintes.items():
        res[k] = " || ".join(str(x) for x in v) if isinstance(v, list) else str(v)
    return res


def nom_sur(nom: str) -> str:
    base = re.sub(r"[^A-Za-z0-9._+\-]+", "-", nom).strip("-")
    return re.sub(r"-+", "-", base)


def main() -> int:
    p = argparse.ArgumentParser(description="Assemble le mod unique Optimisation 26.2")
    p.add_argument("--sortie", help="Jar final (défaut : Optimisation-26.2-tout-en-un.jar)")
    p.add_argument("--jar-mod", help="Jar compilé du gestionnaire (défaut : dernier build Gradle)")
    args = p.parse_args()

    catalogue = G.charger_json(G.CHEMIN_CATALOGUE)
    verrou = G.charger_json(G.CHEMIN_VERROU) or {"mods": {}}
    version_pack = catalogue.get("version_pack", "1.0.0")
    mc = catalogue.get("minecraft", "26.2")
    sortie = Path(args.sortie) if args.sortie else RACINE / f"Optimisation-{mc}-tout-en-un.jar"

    if args.jar_mod:
        jar_mod = Path(args.jar_mod)
    else:
        candidats = sorted((RACINE / "mod-unique" / "build" / "libs").glob("optimisation-pack-*.jar"))
        candidats = [c for c in candidats if "-sources" not in c.name]
        if not candidats:
            print("Jar du gestionnaire introuvable : lance d'abord « gradle build » dans mod-unique/.", file=sys.stderr)
            return 1
        jar_mod = candidats[-1]
    print(f"Gestionnaire : {jar_mod.name}")

    cache = RACINE / ".cache"
    cache.mkdir(exist_ok=True)
    manifeste = {
        "version_pack": version_pack,
        "minecraft": mc,
        "categories": catalogue["categories"],
        "mods": [],
    }
    jars_a_embarquer = []  # (chemin local, nom dans le jar)
    actifs_par_defaut = []
    for entree in catalogue["mods"]:
        ident = entree["id"]
        v = verrou["mods"].get(ident, {})
        if entree.get("fichier"):
            local = G.DOSSIER_MODS_PERSO / entree["fichier"]
        else:
            if not v:
                print(f"  ! {ident} absent du verrou, ignoré", file=sys.stderr)
                continue
            local = cache / v["fichier"]
            if not local.exists() or G.empreintes(local)["sha512"] != v["sha512"]:
                print(f"  téléchargement : {v['fichier']}")
                G.telecharger(v["url"], local, v["sha512"])
        meta = G.lire_meta_jar(local)
        if meta is None:
            print(f"  ! {local.name} : fabric.mod.json illisible, ignoré", file=sys.stderr)
            continue
        nom_jar = nom_sur(local.name)
        if not nom_jar.endswith(".jar"):
            nom_jar += ".jar"
        jars_a_embarquer.append((local, nom_jar))
        par_defaut = bool(entree.get("par_defaut", True))
        if par_defaut:
            actifs_par_defaut.append(nom_jar)
        manifeste["mods"].append({
            "id": meta.id,
            "fichier": nom_jar,
            "nom": entree.get("nom", meta.nom),
            "version": meta.version,
            "categorie": entree.get("categorie", "autre"),
            "description": entree.get("description", meta.description),
            "bibliotheque": bool(entree.get("bibliotheque", False)),
            "par_defaut": par_defaut,
            "verrouille": meta.id in VERROUILLES,
            "raison_verrou": VERROUILLES.get(meta.id, ""),
            "depends": aplatir(meta.depends),
            "breaks": aplatir(meta.breaks),
            "fournit": meta.fournit,
            "fichiers": list(entree.get("fichiers", [])),
        })
        print(f"  + {meta.id:24} {meta.version:22} {'actif' if par_defaut else 'optionnel'}")

    # dépendances automatiques du verrou (ex. placeholder-api pour spark)
    for ident, v in verrou["mods"].items():
        if not v.get("auto"):
            continue
        local = cache / v["fichier"]
        if not local.exists():
            G.telecharger(v["url"], local, v["sha512"])
        meta = G.lire_meta_jar(local)
        if not meta:
            continue
        nom_jar = nom_sur(local.name)
        jars_a_embarquer.append((local, nom_jar))
        manifeste["mods"].append({
            "id": meta.id, "fichier": nom_jar, "nom": v.get("titre", meta.nom), "version": meta.version,
            "categorie": "bibliotheque", "description": "Bibliothèque requise par un mod optionnel.",
            "bibliotheque": True, "par_defaut": False, "verrouille": False, "raison_verrou": "",
            "depends": aplatir(meta.depends), "breaks": aplatir(meta.breaks), "fournit": meta.fournit, "fichiers": [],
        })
        print(f"  + {meta.id:24} {meta.version:22} optionnel (auto)")

    # vérification de cohérence du jeu par défaut
    fournis = {}
    for m in manifeste["mods"]:
        if m["par_defaut"]:
            fournis.update(m["fournit"])
    problemes = []
    for m in manifeste["mods"]:
        if not m["par_defaut"]:
            continue
        for d, c in m["depends"].items():
            if d not in fournis:
                problemes.append(f"{m['nom']} a besoin de « {d} » absent du jeu par défaut")
            elif not G.contrainte_satisfaite(fournis[d], c):
                problemes.append(f"{m['nom']} demande « {d} » {c}, version embarquée {fournis[d]}")
    if problemes:
        print("Incohérences :\n  - " + "\n  - ".join(problemes), file=sys.stderr)
        return 1

    # écriture du jar final
    with zipfile.ZipFile(jar_mod) as src, zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as dst:
        for info in src.infolist():
            if info.filename == "fabric.mod.json":
                fmj = json.loads(src.read(info).decode("utf-8"))
                fmj["jars"] = [{"file": f"META-INF/jars/{n}"} for n in actifs_par_defaut]
                fmj["version"] = version_pack
                texte = json.dumps(fmj, ensure_ascii=False, indent=2)
                dst.writestr("fabric.mod.json", texte)
            else:
                dst.writestr(info, src.read(info))
        dst.writestr("pack-manifest.json", json.dumps(manifeste, ensure_ascii=False, indent=2))
        for local, nom_jar in jars_a_embarquer:
            dst.write(local, f"META-INF/jars/{nom_jar}", compress_type=zipfile.ZIP_STORED)
    taille = sortie.stat().st_size / 1e6
    print(f"\nJar final : {sortie}  ({taille:.1f} Mo, {len(jars_a_embarquer)} mods embarqués, "
          f"{len(actifs_par_defaut)} actifs par défaut)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
