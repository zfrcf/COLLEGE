#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur du projet Scratch « Royale 3D » (FPS multijoueur 3D façon Fortnite, variables cloud).

    python3 generer_projet.py            → écrit « Royale 3D.sb3 »
    python3 generer_projet.py --sans mod_menus,mod_hud   → sans certains modules (débogage)

Assemblage : scène + contrat → modules de base (joueur, moteur3d, overlays) → modules
découverts royale/mod_*.py (chacun expose construire(P), et éventuellement ORDRE) → sons →
textes traduits → .sb3. Voir royale/contrat.py pour le contrat partagé.
"""
import importlib
import os
import pkgutil
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ICI)

from royale.dsl import Projet, Cible, ecrire_sb3  # noqa: E402
from royale import contrat, svg, joueur, moteur3d, overlays  # noqa: E402
import royale  # noqa: E402

SORTIE = os.path.join(ICI, "Royale 3D.sb3")


def modules_optionnels(exclus):
    mods = []
    for info in pkgutil.iter_modules(royale.__path__):
        if info.name.startswith("mod_") and info.name not in exclus:
            mods.append(importlib.import_module("royale." + info.name))
    mods.sort(key=lambda m: (getattr(m, "ORDRE", 50), m.__name__))
    return mods


def construire_projet(exclus=()):
    P = Projet()
    stage = Cible(P, "Stage", is_stage=True)
    stage.costumes = [P.costume("scène", svg.svg_scene(), 240, 180)]
    contrat.declarer_globales(stage)

    joueur.construire(P)
    moteur3d.construire(P)
    overlays.construire(P)
    for m in modules_optionnels(exclus):
        m.construire(P)
    try:
        from royale import sons
        if "sons" not in exclus:
            sons.installer(P)
    except ImportError:
        print("  (module sons absent : projet sans audio)")
    contrat.finaliser_textes(stage)
    return P


if __name__ == "__main__":
    exclus = ()
    if "--sans" in sys.argv:
        exclus = tuple(sys.argv[sys.argv.index("--sans") + 1].split(","))
    projet = construire_projet(exclus)
    donnees = ecrire_sb3(projet, SORTIE)
    nb_blocs = sum(len(t["blocks"]) for t in donnees["targets"])
    taille = os.path.getsize(SORTIE) / 1024
    print("Écrit : %s (%d sprites, %d blocs, %d ressources, %.0f Ko)" % (
        SORTIE, len(donnees["targets"]) - 1, nb_blocs, len(projet.assets), taille))
    contrat.exporter_json()
