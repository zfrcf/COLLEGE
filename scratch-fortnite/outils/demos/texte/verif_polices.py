#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification visuelle des 7 polices Scratch : un sprite par police (installer(S, police)),
chacun écrit une ligne à 20 px et une à 12 px avec accents, « × » (vectoriel de secours pour
les polices qui ne l'ont pas), symboles et chiffres.

Usage : python3 verif_polices.py [sortie.sb3]
Puis  : node outils/capture.js <sortie.sb3> outils/demos/texte/verif_polices.js
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "verif_polices.sb3")

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#1b2130"/></svg>', 240, 180)]
contrat.declarer_globales(stage)

y = 160
for i, police in enumerate(texte.POLICES):
    S = Cible(P, "Police " + police)
    S.layer = contrat.CALQUES["Texte"] - i
    S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
    texte.installer(S, police)
    assert "g_×" in [c["name"] for c in S.costumes], police
    S.script(quand_drapeau(), [
        cacher(), attendre(0.5),
        si(eq(i, 0), [effacer()]),
        texte.ecrire("%s : Royale 3D × 2 ✔ Éé ç « 12 € » ★👍 Hxg" % police, -236, y - 17, 20, "blanc", 0),
        texte.ecrire("12 px : Dès Noël, où un zéphyr haï me vêt de glaçons 0123456789 ×", -236, y - 36, 12, "jaune", 0),
        couleur_stylo("#ff00ff"), taille_stylo(1), ligne(-236, y - 17, -232, y - 17),   # repère de ligne de base
    ])
    y -= 50
contrat.finaliser_textes(stage)
ecrire_sb3(P, sortie)
print(sortie)
