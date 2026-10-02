#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démo du moteur de texte (royale/texte.py) : pangrammes accentués en 3 tailles,
12 couleurs, alignements gauche/centre/droite (repère vertical au stylo), nombre
arrondi, texte tronqué, symboles vectoriels, texte noir sur fond gris.

Usage : python3 demo.py [police] [sortie.sb3]
Puis  : node outils/capture.js outils/demos/texte/demo.sb3 outils/demos/texte/demo.js
        → outils/demos/texte/demo.png
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

police = sys.argv[1] if len(sys.argv) > 1 else "Sans Serif"
sortie = sys.argv[2] if len(sys.argv) > 2 else os.path.join(ICI, "demo.sb3")

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
# fond : bleu nuit en haut, bande grise en bas (y < -95) pour tester le noir sur gris
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#1b2130"/>'
                            '<rect y="275" width="480" height="85" fill="#8c919b"/></svg>', 240, 180)]
contrat.declarer_globales(stage)

S = Cible(P, "Demo")
S.layer = contrat.CALQUES["Texte"]          # layerOrder doit être ≥ 1 pour un sprite
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(S, police)


def mots_colores(mots, x, y, t):
    """Écrit chaque mot dans la couleur de son nom, à la suite."""
    corps = []
    for m in mots:
        corps.append(texte.ecrire(m, x, y, t, m, 0))
        x += texte.largeur_px(m + " ", t, police)
    return corps


PANGRAMME_1 = "Dès Noël, où un zéphyr haï me vêt de glaçons"
PANGRAMME_2 = "Portez ce vieux whisky au juge blond qui fume. Voix ambiguë d'un cœur."
assert texte.largeur_px(PANGRAMME_1, 18, police) < 470, texte.largeur_px(PANGRAMME_1, 18, police)
assert texte.largeur_px(PANGRAMME_2, 13, police) < 470, texte.largeur_px(PANGRAMME_2, 13, police)

XA = 60   # abscisse du repère d'alignement

S.script(quand_drapeau(), [
    cacher(), attendre(0.5),                 # laisse les images SVG se charger (banc de capture)
    effacer(),
    # --- pangrammes : 3 tailles -------------------------------------------------
    texte.ecrire("Victoire Royale !", 0, 148, 36, "or", 1),
    texte.ecrire(PANGRAMME_1, 0, 118, 18, "blanc", 1),
    setv("txt_ombre", 0),
    texte.ecrire(PANGRAMME_2, 0, 98, 13, "cyan", 1),
    setv("txt_ombre", 1),
    # --- 12 couleurs (mot écrit dans sa couleur) ------------------------------
    mots_colores(["rouge", "orange", "jaune", "or", "vert", "cyan"], -230, 72, 20),
    mots_colores(["bleu", "violet", "rose", "gris", "blanc"], -230, 48, 20),
    # --- alignements : repère vertical magenta en x = XA -------------------------
    couleur_stylo("#ff00ff"), taille_stylo(1),
    ligne(XA, 30, XA, -40),
    texte.ecrire("gauche →", XA, 18, 16, "jaune", 0),
    texte.ecrire("← centré →", XA, -2, 16, "vert", 1),
    texte.ecrire("← droite", XA, -22, 16, "rose", 2),
    # --- nombre arrondi et largeur texte ----------------------------------------
    texte.ecrire("Score", -230, 18, 16, "blanc", 0),
    texte.ecrire_nombre(12345.678, -170, 18, 16, "jaune", 0),
    texte.ecrire("7/3×3 =", -80, 18, 16, "blanc", 0),
    texte.ecrire_nombre(mul(div(7, 3), 3), -10, 18, 16, "jaune", 0),
    texte.ecrire("largeur(Jouer, 20) =", -230, -2, 13, "gris", 0),
    texte.largeur_texte("Jouer", 20),                                   # → txt_largeur (écrasée par toute écriture)
    texte.ecrire_nombre(Var("txt_largeur"), -100, -2, 13, "blanc", 0),
    # --- texte tronqué : crochets aux bornes [-230, -90] = 140 px ----------------
    couleur_stylo("#ff8800"),
    ligne(-230, -32, -230, -16), ligne(-90, -32, -90, -16), ligne(-230, -32, -90, -32),
    texte.ecrire_tronque("Ceci est un très long titre de quête", -230, -22, 14, "orange", 0, 140),
    # --- symboles ---------------------------------------------------------------
    texte.ecrire("★☆♥●○✔✘×→←↑↓▶◀▲▼■□👍", 0, -58, 22, "blanc", 1),
    texte.ecrire("✔ Quête", -230, -82, 16, "vert", 0),
    texte.ecrire("✘ Échec", -130, -82, 16, "rouge", 0),
    texte.ecrire("♥ 100", -30, -82, 16, "rose", 0),
    texte.ecrire("★ 3", 50, -82, 16, "or", 0),
    texte.ecrire("👍 Bien joué !", 110, -82, 16, "cyan", 0),
    # --- fond gris : noir et couleurs claires ------------------------------------
    mots_colores(["noir", "blanc", "gris", "jaune", "or", "violet"], -230, -118, 20),
    mots_colores(["vert", "bleu", "rouge", "cyan", "rose", "orange"], -230, -143, 20),
    texte.ecrire("Texte noir ombré sur fond gris : 0123456789 ÀÉÈÇ àéèêëîïôùû ç œ", 0, -166, 13, "noir", 1),
])
contrat.finaliser_textes(stage)
ecrire_sb3(P, sortie)
print(sortie)
