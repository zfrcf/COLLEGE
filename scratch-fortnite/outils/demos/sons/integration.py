# -*- coding: utf-8 -*-
"""
Intégration de sons.installer dans le PROJET COMPLET (generer_projet.construire_projet), écrit dans un
fichier à part (le « Royale 3D.sb3 » du dépôt n'est pas touché) :

    python3 outils/demos/sons/integration.py [sortie.sb3]

Vérifie : sprite Sons présent, 28 sons, calque CALQUES['Sons'] unique parmi les sprites, locales son_*,
aucune globale son_* autre que celles du contrat, taille du .sb3, puis affiche le chemin pour vm_lib.
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.abspath(os.path.join(ICI, "..", "..", ".."))
sys.path.insert(0, RACINE)
import generer_projet  # noqa: E402
from royale import contrat  # noqa: E402
from royale.dsl import ecrire_sb3  # noqa: E402


def main(sortie):
    P = generer_projet.construire_projet()
    donnees = ecrire_sb3(P, sortie)
    cibles = donnees["targets"]
    sons = [t for t in cibles if t["name"] == "Sons"]
    erreurs = []
    if len(sons) != 1:
        erreurs.append("sprite Sons : %d trouvé(s)" % len(sons))
    else:
        s = sons[0]
        noms = [x["name"] for x in s["sounds"]]
        if noms != list(contrat.SONS):
            erreurs.append("sons du sprite ≠ contrat.SONS : %s" % noms)
        if s["visible"] or s["layerOrder"] != contrat.CALQUES["Sons"]:
            erreurs.append("Sons visible=%s layerOrder=%s" % (s["visible"], s["layerOrder"]))
        calques = [t["layerOrder"] for t in cibles if not t["isStage"]]
        if calques.count(contrat.CALQUES["Sons"]) != 1:
            erreurs.append("calque %d partagé par %d sprites" % (contrat.CALQUES["Sons"], calques.count(contrat.CALQUES["Sons"])))
        locales = sorted(v[0] for v in s["variables"].values())
        if any(not n.startswith("son_") for n in locales):
            erreurs.append("locales sans préfixe son_ : %s" % locales)
        globales_son = sorted(v[0] for v in cibles[0]["variables"].values() if v[0].startswith("son_"))
        if globales_son != ["son_pan", "son_volume"]:
            erreurs.append("globales son_* inattendues : %s" % globales_son)
        print("Sons : %d sons, %d blocs, calque %d, locales %s" % (len(noms), len(s["blocks"]), s["layerOrder"], locales))
    taille = os.path.getsize(sortie)
    print("projet complet : %d sprites, %d ressources, %.0f Ko → %s" % (len(cibles) - 1, len(P.assets), taille / 1024, sortie))
    if taille > 5_000_000:
        erreurs.append("projet de %.1f Mo (limite Scratch : 5 Mo)" % (taille / 1e6))
    if erreurs:
        print("ERREURS :\n - " + "\n - ".join(erreurs))
        return 1
    print("Intégration OK.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "integration.sb3")))
