#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Projet de test (logique, sans rendu) du moteur de texte : chaque appel range son
résultat dans la liste locale « resultats », vérifiée par test_vm.js dans scratch-vm.

Usage : python3 test.py [sortie.sb3]   puis   node test_vm.js [sortie.sb3]
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "test.sb3")

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#123"/></svg>', 240, 180)]
contrat.declarer_globales(stage)
S = Cible(P, "Demo")
S.layer = contrat.CALQUES["Texte"]
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2),
              P.costume("autre", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(S)
S.liste("resultats", [])

R = "resultats"
G = "txt_glyphes"
dernier = item(G, long_liste(G))
S.script(quand_drapeau(), [
    vider(R),
    # 1. largeur de « Jouer » à 20 px
    appel("largeur texte", "Jouer", 20), ajouter_liste(R, Var("txt_largeur")),
    # 2. caractère inconnu (espace insécable) ignoré : 2 glyphes
    appel("largeur texte", "a b", 40), ajouter_liste(R, long_liste(G)),
    # 3. émoji (paire de substitution) : 1 glyphe, numéro du costume g_👍
    appel("largeur texte", "👍", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 4. majuscule et minuscule : costumes différents
    appel("largeur texte", "Aa", 40), ajouter_liste(R, joins(item(G, 1), "/", item(G, 2))),
    # 5. espace : 0 dans la liste, avance 0.3 × taille
    appel("largeur texte", " ", 40), ajouter_liste(R, joins(item(G, 1), "/", Var("txt_largeur"))),
    # 6. troncature : largeur finale ≤ 100, dernier glyphe = « … »
    appel("ecrire tronque", "Ceci est un très long titre de quête", 0, 0, 20, "blanc", 0, 100),
    ajouter_liste(R, joins(Var("txt_largeur"), "/", dernier, "/", long_liste(G))),
    # 7. pas de troncature si ça tient
    appel("ecrire tronque", "Court", 0, 0, 20, "blanc", 0, 300), ajouter_liste(R, joins(long_liste(G), "/", dernier)),
    # 8. nombre arrondi : 12.000000001 → « 12 » (2 glyphes)
    appel("ecrire nombre", 12.000000001, 0, 0, 20, "jaune", 1), ajouter_liste(R, long_liste(G)),
    # 9. écriture complète : facteur txt_k = 0.5 pour 20 px, 4 entrées pour « Hé ! » (l'espace compte)
    appel("ecrire", "Hé !", 0, 0, 20, "or", 2), ajouter_liste(R, joins(Var("txt_k"), "/", long_liste(G))),
    # 10. texte vide : rien
    appel("ecrire", "", 0, 0, 20, "or", 1), ajouter_liste(R, joins(long_liste(G), "/", Var("txt_largeur"))),
    # 11. largeur Python (texte.largeur_px) = largeur Scratch pour un texte mixte
    appel("largeur texte", "Royale 3D — 12 €", 30),
    ajouter_liste(R, joins(Var("txt_largeur"), "/", round(texte.largeur_px("Royale 3D — 12 €", 30), 3))),
])
contrat.finaliser_textes(stage)
ecrire_sb3(P, sortie)
print(sortie)
