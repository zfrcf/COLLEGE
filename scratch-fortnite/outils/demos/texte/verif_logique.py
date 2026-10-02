#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification adversariale (logique, sans rendu) du moteur de texte : cas limites
— nombres négatifs, arrondi de −0.4, texte numérique, sélecteur de variation
(❤️), espace insécable, ligature ﬁ (> U+D7FF mais pas un substitut), couleur en
MAJUSCULES / inconnue / vide, alignements 1 et 2 (position finale du curseur),
tailles 10 et 60, texte fait d'espaces, troncature extrême et espace avant « … »,
interlettrage, émoji en début et en fin, deuxième sprite installé.

Usage : python3 verif_logique.py [sortie.sb3]   puis   node verif_logique.js [sortie.sb3]
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.dsl import *          # noqa: E402,F401
from royale import contrat, texte  # noqa: E402

sortie = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "verif_logique.sb3")

# --- vérifications côté Python -------------------------------------------------
P = Projet()
stage = Cible(P, "Stage", is_stage=True)
stage.costumes = [P.costume("scène", '<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360">'
                            '<rect width="480" height="360" fill="#123"/></svg>', 240, 180)]
contrat.declarer_globales(stage)
try:
    texte.installer(stage)
    raise SystemExit("installer(scène) aurait dû lever une erreur")
except ValueError:
    pass

S = Cible(P, "Demo")
S.layer = contrat.CALQUES["Texte"]
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2),
              P.costume("autre", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
try:
    texte.installer(S, "Comic Sans")
    raise SystemExit("police inconnue acceptée")
except KeyError:
    pass
texte.installer(S)
n_costumes = len(S.costumes)
texte.installer(S)                                   # idempotent
assert len(S.costumes) == n_costumes, "installer() n'est pas idempotent"
noms = [c["name"] for c in S.costumes]
assert len(set(noms)) == len(noms), "noms de costumes en double : %r" % [n for n in noms if noms.count(n) > 1]
assert len(S.lists["txt_largeurs"][1]) == len(S.costumes), "txt_largeurs n'a pas une entrée par costume"
assert all(n.startswith("g_") for n in noms[2:]), "costume de glyphe sans préfixe g_"
assert set(texte.couleurs()) == {"blanc", "noir", "gris", "rouge", "orange", "jaune", "or", "vert", "cyan", "bleu", "violet", "rose"}
for c in "ABCabc019éèêëàâçùûôîïÉÈÀÇ.,:;!?'\"-_/()[]+*=%#&<>@°²★☆♥●○✔✘×→←↑↓▶◀▲▼■□👍":
    assert ("g_" + c) in noms, "glyphe manquant : %r" % c
S.liste("resultats", [])

A = Cible(P, "Autre")                                # deuxième sprite : ses propres blocs et costumes
A.layer = contrat.CALQUES["Texte"] - 1
A.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
texte.installer(A)
A.liste("resultats", [])

R = "resultats"
G = "txt_glyphes"
dernier = item(G, long_liste(G))
avant_dernier = item(G, sub(long_liste(G), 1))
S.script(quand_drapeau(), [
    vider(R),
    # 1. nombre négatif : « -42 » → 3 glyphes, le premier = g_-
    appel("ecrire nombre", -42, 0, 0, 20, "jaune", 0), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 2. −0.4 arrondi → « 0 » (1 glyphe g_0), pas « -0 »
    appel("ecrire nombre", -0.4, 0, 0, 20, "jaune", 0), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 3. nombre non numérique → 0 → 1 glyphe
    appel("ecrire nombre", "abc", 0, 0, 20, "jaune", 0), ajouter_liste(R, long_liste(G)),
    # 4. sélecteur de variation U+FE0F (❤️) : ignoré SANS avaler l'espace qui suit → ❤, espace, 1, 0, 0
    appel("largeur texte", "❤️ 100", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 2), "/", Var("txt_largeur"))),
    # 5. espace insécable traité comme un espace → 3 entrées, largeur a + 12 + b
    appel("largeur texte", "a b", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 2), "/", Var("txt_largeur"))),
    # 6. ligature ﬁ (U+FB01 > U+D7FF, pas un substitut) : ignorée sans avaler le « n »
    appel("largeur texte", "ﬁn", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 7. couleur en majuscules / inconnue / vide → index 9 (rouge) / 0 (blanc) / 0
    appel("ecrire", "x", 0, 0, 20, "ROUGE", 0), ajouter_liste(R, Var("txt_n")),
    appel("ecrire", "x", 0, 0, 20, "inconnue", 0), ajouter_liste(R, Var("txt_n")),
    appel("ecrire", "x", 0, 0, 20, "", 0), ajouter_liste(R, Var("txt_n")),
    # 8. alignement 2 sur x = 100 : le curseur finit en 100 ; alignement 1 sur 0 : finit en largeur/2
    appel("ecrire", "Jouer", 100, 0, 20, "blanc", 2), ajouter_liste(R, Var("txt_x")),
    appel("ecrire", "Jouer", 0, 0, 20, "blanc", 1), ajouter_liste(R, joins(Var("txt_x"), "/", Var("txt_largeur"))),
    # 9. tailles 10 et 60 : largeur proportionnelle, txt_k = 0.25 / 1.5
    appel("largeur texte", "Jouer", 10), ajouter_liste(R, joins(Var("txt_largeur"), "/", Var("txt_k"))),
    appel("largeur texte", "Jouer", 60), ajouter_liste(R, joins(Var("txt_largeur"), "/", Var("txt_k"))),
    # 10. que des espaces → 3 entrées à 0, largeur 36
    appel("largeur texte", "   ", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 3), "/", Var("txt_largeur"))),
    # 11. troncature extrême (largeurMax 5) : il reste « … » seul, pas de plantage
    appel("ecrire tronque", "Victoire", 0, 0, 20, "blanc", 0, 5), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 12. troncature « ab cd ef gh » à 100 px (taille 40) → a, b, … (l'espace avant … est retiré), largeur 78.58
    appel("ecrire tronque", "ab cd ef gh", 0, 0, 40, "blanc", 0, 100),
    ajouter_liste(R, joins(long_liste(G), "/", dernier, "/", avant_dernier, "/", Var("txt_largeur"))),
    # 13. interlettrage txt_espacement = 4 → « ab » = 22.51 + 4 + 24.31 + 4
    setv("txt_espacement", 4), appel("largeur texte", "ab", 40), ajouter_liste(R, Var("txt_largeur")), setv("txt_espacement", 0),
    # 14. texte numérique (42) → 2 glyphes
    appel("ecrire", 42, 0, 0, 20, "blanc", 0), ajouter_liste(R, long_liste(G)),
    # 15. émoji en fin et en début de texte
    appel("largeur texte", "ok 👍", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 4))),
    appel("largeur texte", "👍 ok", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1), "/", item(G, 2))),
    # 16. accents : « Dès » → 2e glyphe = g_è
    appel("largeur texte", "Dès", 40), ajouter_liste(R, item(G, 2)),
    # 17. « 0 » n'est pas un espace ; « 00 » = 2 glyphes g_0
    appel("largeur texte", "00", 40), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1))),
    # 18. texte hors scène à droite (x = 300) : aucun tampon ne doit être fait → txt_x avance quand même
    appel("ecrire", "Hors", 300, 0, 20, "blanc", 0), ajouter_liste(R, Var("txt_x")),
    # 19. largeur Python = largeur Scratch pour « ❤️ 100 » et « Prix : 12 € » (espace insécable)
    appel("largeur texte", "Prix : 12 €", 24),
    ajouter_liste(R, joins(Var("txt_largeur"), "/", round(texte.largeur_px("Prix : 12 €", 24), 3))),
])
A.script(quand_drapeau(), [
    vider(R),
    appel("ecrire", "Autre", 0, 0, 20, "vert", 0), ajouter_liste(R, joins(long_liste(G), "/", item(G, 1), "/", Var("txt_largeur"))),
])
contrat.finaliser_textes(stage)
ecrire_sb3(P, sortie)
print(sortie)
