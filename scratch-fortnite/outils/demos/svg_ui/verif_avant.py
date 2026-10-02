#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vérification adversariale (avant corrections) : carte_complete(5) comme l'appelle mod_menus,
icônes à dégradé passées par mod_menus._normaliser (g transform), haut-parleur n*34."""
import os, sys
ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..", "..")))
from royale.dsl import *
from royale import contrat
from royale import svg_ui as UI
from royale.svg import svg
from royale.mod_menus import _normaliser

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", svg(480, 360, '<rect width="480" height="360" fill="#1b2340"/>'), 240, 180)]
contrat.declarer_globales(stage)
S = Cible(P, "Demo"); S.visible = False; S.layer = 1
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
items = []
def ajout(nom, s, x, y, pct=100):
    import re
    m = re.search(r'width="(\d+)" height="(\d+)"', s); w, h = int(m.group(1)), int(m.group(2))
    S.costumes.append(P.costume(nom, s, w / 2.0, h / 2.0)); items.append((nom, x, y, pct))
ajout("carte5", UI.carte_complete(5), -150, 90)
ajout("carte5_norm", _normaliser(UI.carte_complete(5), 160), 30, 90)
ajout("div3_norm", _normaliser(UI.division(3), 32), -200, -30, 200)
ajout("div5_norm", _normaliser(UI.division(5), 32), -150, -30, 200)
ajout("med1_norm", _normaliser(UI.medaille(1), 100), -80, -30)
ajout("logo_norm", _normaliser(UI.logo(), 300), 150, -40)
ajout("div3", UI.division(3), -200, -110)
ajout("med1", UI.medaille(1), -150, -110)
for i, n in enumerate((0, 34, 68, 102)):
    ajout("hp%d" % n, UI.icone_haut_parleur(n), -60 + i * 40, -130, 150)
ajout("pot_norm", _normaliser(UI.icone_objet(7), 32), 120, -130, 150)
ajout("pot", UI.icone_objet(7), 160, -130)
ajout("mini_norm", _normaliser(UI.carte_minimap(), 54), 210, -130)
corps = []
for nom, x, y, pct in items:
    corps += [costume(nom), taille(pct), aller(x, y), cloner_moi()]
S.script(quand_drapeau(), [cacher(), attendre(0.3)] + corps)
S.script(quand_clone(), [montrer()])
contrat.finaliser_textes(stage)
ecrire_sb3(P, os.path.join(ICI, "verif_avant.sb3"))
print("ok", len(items))
