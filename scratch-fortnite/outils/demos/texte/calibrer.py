#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mini-projet de calibration du moteur de texte : tamponne « H » (rouge pur, sans
effet) à l'origine, puis « Hxg » et un repère, pour mesurer dans Chromium la
position réelle de la ligne de base et du bord gauche (voir calibrer.js).

Usage : python3 calibrer.py [police]  →  /tmp/.../calibrer.sb3 (chemin affiché)
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

police = sys.argv[1] if len(sys.argv) > 1 else "Sans Serif"
P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#202830"/></svg>', 240, 180)]
contrat.declarer_globales(stage)
S = Cible(P, "Demo")
S.layer = contrat.CALQUES["Texte"]          # layerOrder doit être ≥ 1 pour un sprite
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(S, police)
S.script(quand_drapeau(), [
    cacher(), attendre(1), effacer(), setv("txt_ombre", 0),      # attendre le chargement asynchrone des images SVG
    # repère vert : ligne de base y = 0 et verticale x = 0
    couleur_stylo("#00ff00"), taille_stylo(1),
    ligne(-200, 0, 200, 0), ligne(0, -100, 0, 100),
    # « H » tamponné brut (rouge pur) à l'origine, taille 40 (100 %)
    appel("largeur texte", "H", 40),
    appel("txt_passe", 0, 0, 40),
    # contrôle visuel : plusieurs tailles sur la même ligne de base
    appel("ecrire", "Hxg Éj", -230, 100, 40, "blanc", 0),
    appel("ecrire", "Hxg Éj", -230, 60, 20, "jaune", 0),
    appel("ecrire", "Hxg Éj", -230, 40, 10, "cyan", 0),
    appel("ecrire", "Hxg Éj", 60, -60, 60, "vert", 0),
])
contrat.finaliser_textes(stage)
sortie = os.environ.get("SORTIE", "/tmp/calibrer.sb3")
ecrire_sb3(P, sortie)
print(sortie)
