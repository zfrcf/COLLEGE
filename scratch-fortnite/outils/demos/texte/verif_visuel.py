#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification adversariale VISUELLE du moteur de texte : tailles 10 / 13 / 60,
alignements 1 et 2 sur un repère, nombres négatifs, ❤️ (sélecteur de variation),
espace insécable, texte qui déborde du bord droit (doit être coupé proprement,
pas empilé), symboles à 14 px et 60 px, ponctuation spéciale, noir / couleurs
sur fond gris, texte écrit par un deuxième sprite installé.

Usage : python3 verif_visuel.py [sortie.sb3]
Puis  : node outils/capture.js <sortie.sb3> outils/demos/texte/verif_visuel.js
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "verif_visuel.sb3")

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#1b2130"/>'
                            '<rect y="275" width="480" height="85" fill="#8c919b"/></svg>', 240, 180)]
contrat.declarer_globales(stage)

S = Cible(P, "Demo")
S.layer = contrat.CALQUES["Texte"]
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(S)

A = Cible(P, "Autre")
A.layer = contrat.CALQUES["Texte"] - 1
A.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(A)

XR = 150   # repère d'alignement
S.script(quand_drapeau(), [
    cacher(), attendre(0.5), effacer(),
    # taille 60 centrée
    texte.ecrire("Royale 60", 0, 128, 60, "or", 1),
    # petites tailles
    texte.ecrire("Taille 10 : Hxg Éj Jouer 0123456789 àéèçù œ Dès Noël, où un zéphyr", -236, 105, 10, "blanc", 0),
    texte.ecrire("Taille 13 : Hxg Éj Jouer 0123456789 àéèçù œ Portez ce vieux whisky", -236, 90, 13, "cyan", 0),
    texte.ecrire("Taille 16 : Hxg Éj Jouer 0123456789 àéèçù œ ambiguë", -236, 72, 16, "jaune", 0),
    # alignements sur le repère magenta x = XR
    couleur_stylo("#ff00ff"), taille_stylo(1), ligne(XR, 62, XR, -6),
    texte.ecrire("gauche", XR, 50, 18, "blanc", 0),
    texte.ecrire("centré", XR, 28, 18, "vert", 1),
    texte.ecrire("droite", XR, 6, 18, "rose", 2),
    # nombres négatifs / arrondis
    texte.ecrire("Solde :", -236, 50, 16, "blanc", 0),
    texte.ecrire_nombre(-42, -170, 50, 16, "jaune", 0),
    texte.ecrire_nombre(-0.4, -130, 50, 16, "jaune", 0),
    texte.ecrire_nombre(-1234567.5, -100, 50, 16, "jaune", 0),
    texte.ecrire_nombre(div(1, 3), 0, 50, 16, "jaune", 0),
    # sélecteur de variation, espace insécable, ligature
    texte.ecrire("❤️ 100", -236, 28, 16, "rose", 0),
    texte.ecrire("Prix : 12 €", -150, 28, 16, "blanc", 0),
    texte.ecrire("[ﬁn]", -40, 28, 16, "cyan", 0),
    texte.ecrire("a b", 30, 28, 16, "vert", 0),
    # débordement à gauche puis à droite (le texte doit être coupé au bord, pas empilé)
    texte.ecrire("Débordement à gauche : ce texte est bien trop long", -400, 6, 16, "orange", 0),
    texte.ecrire("Débordement à droite : ce texte est bien trop long pour tenir", 60, -16, 16, "blanc", 0),
    # symboles à 14 px, ponctuation à 16 px
    texte.ecrire("★☆♥❤●○✔✘→←↑↓▶◀▲▼■□👍 × 14 px", -236, -38, 14, "blanc", 0),
    texte.ecrire("25 °C  10 m²  3 €  « Oui »…  50 %  #1  @  a/b  {x}  ~  |  ‘’“”  –  —", -236, -60, 16, "blanc", 0),
    # symboles à 44 px (à gauche, sous la ponctuation sans jambage) et texte entièrement hors scène (rien)
    texte.ecrire("★✔👍→♥", -100, -92, 44, "cyan", 1),
    texte.ecrire("invisible", 0, 230, 20, "rouge", 1),
    texte.ecrire("invisible", 0, -250, 20, "rouge", 1),
    texte.ecrire("invisible", 300, 0, 20, "rouge", 0),
    # fond gris : noir à 16 et 10 px, couleurs
    texte.ecrire("Noir 16 : Hxg Éj 0123 àéèçù — Score : -42", -236, -115, 16, "noir", 0),
    texte.ecrire("Noir 10 : Hxg Éj 0123 àéèçù Victoire Royale ! ★ 3 ✔ Quête ✘ Échec", -236, -131, 10, "noir", 0),
    setv("txt_ombre", 0),
    texte.ecrire("sans ombre : noir", 60, -131, 12, "noir", 0),
    setv("txt_ombre", 1),
    texte.ecrire("bleu", -236, -152, 18, "bleu", 0), texte.ecrire("violet", -180, -152, 18, "violet", 0),
    texte.ecrire("vert", -110, -152, 18, "vert", 0), texte.ecrire("rouge", -60, -152, 18, "rouge", 0),
    texte.ecrire("orange", 10, -152, 18, "orange", 0), texte.ecrire("cyan", 90, -152, 18, "cyan", 0),
    texte.ecrire("rose", 150, -152, 18, "rose", 0),
    texte.ecrire("gris", -236, -172, 18, "gris", 0), texte.ecrire("blanc", -180, -172, 18, "blanc", 0),
    texte.ecrire("jaune", -110, -172, 18, "jaune", 0), texte.ecrire("or", -40, -172, 18, "or", 0),
])
A.script(quand_drapeau(), [
    cacher(), attendre(1.0),
    texte.ecrire("2e sprite ✔", 236, -172, 18, "vert", 2),
])
contrat.finaliser_textes(stage)
ecrire_sb3(P, sortie)
print(sortie)
