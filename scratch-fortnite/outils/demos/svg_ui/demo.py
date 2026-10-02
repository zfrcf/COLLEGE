#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Planches de démonstration de la banque d'icônes (royale/svg_ui.py).

Génère demo.sb3 : un sprite « Planche » dont les costumes sont toutes les icônes ; selon la
variable globale `demo_planche` (1..N), il crée des clones placés en grille (≤ 120 par planche)
qui affichent chaque icône, et écrit titres et légendes au stylo (moteur de texte). Les clones
se suppriment d'eux-mêmes quand la planche change. planches.json liste les planches (dans l'ordre)
pour le script de capture demo.js.

    python3 outils/demos/svg_ui/demo.py
    node outils/capture.js outils/demos/svg_ui/demo.sb3 outils/demos/svg_ui/demo.js   → planche_*.png
"""
import json
import os
import re
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..", "..")))
from royale.dsl import *            # noqa: E402,F401
from royale import contrat, texte   # noqa: E402
from royale import svg_ui as UI     # noqa: E402
from royale.svg import svg          # noqa: E402

SORTIE = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ICI, "demo.sb3")

P = Projet()
stage = Cible(P, "Stage", is_stage=True)
# fond : bleu nuit avec un damier discret (pour voir les transparences)
damier = "".join('<rect x="%d" y="%d" width="20" height="20" fill="#202a4a"/>' % (x, y)
                 for y in range(0, 360, 20) for x in range(0, 480, 20) if (x // 20 + y // 20) % 2 == 0)
stage.costumes = [P.costume("scène", svg(480, 360, '<rect width="480" height="360" fill="#1b2340"/>' + damier), 240, 180)]
contrat.declarer_globales(stage)
stage.var("demo_planche", 1)

S = Cible(P, "Planche")
S.layer = contrat.CALQUES["Texte"]
S.visible = False
S.costumes = [P.costume("vide", '<svg xmlns="http://www.w3.org/2000/svg" width="4" height="4"/>', 2, 2)]
S.var("ma_planche", 0)
S.var("derniere", -1)

DIMS = {}      # nom de costume -> (largeur, hauteur)


def costume_ui(nom, svg_txt):
    """Enregistre un costume (centre de rotation au milieu) ; renvoie son nom."""
    if nom not in DIMS:
        m = re.search(r'width="(\d+)" height="(\d+)"', svg_txt)
        w, h = int(m.group(1)), int(m.group(2))
        S.costumes.append(P.costume(nom, svg_txt, w / 2.0, h / 2.0))
        DIMS[nom] = (w, h)
    return nom


def disposer(items, largeur_max=470, gap_x=10, gap_y=8, y_haut=140, y_bas=-172, largeur_mini=0):
    """Range des (nom, légende, taille %) en lignes centrées ; renvoie (nom, légende, %, x, y, w, h).
    largeur_mini : largeur de cellule minimale (place pour la légende)."""
    lignes, ligne, largeur = [], [], 0
    for nom, legende, pct in items:
        w, h = DIMS[nom][0] * pct / 100.0, DIMS[nom][1] * pct / 100.0
        cw = max(w, largeur_mini if legende else 0)
        lab = 12 if legende else 0
        if ligne and largeur + gap_x + cw > largeur_max:
            lignes.append(ligne)
            ligne, largeur = [], 0
        ligne.append((nom, legende, pct, w, h, lab, cw))
        largeur += (gap_x if len(ligne) > 1 else 0) + cw
    lignes.append(ligne)
    hauteurs = [max(h + lab for _, _, _, _, h, lab, _ in l) for l in lignes]
    total = sum(hauteurs) + gap_y * (len(lignes) - 1)
    dispo = y_haut - y_bas
    if total > dispo:
        print("  ATTENTION : planche trop haute (%d px pour %d)" % (total, dispo))
    y = y_haut - max(0, (dispo - total) / 2.0)
    out = []
    for l, rh in zip(lignes, hauteurs):
        rw = sum(cw for _, _, _, _, _, _, cw in l) + gap_x * (len(l) - 1)
        x = -rw / 2.0
        for nom, legende, pct, w, h, lab, cw in l:
            out.append((nom, legende, pct, round(x + cw / 2.0, 1), round(y - h / 2.0, 1), w, h))
            x += cw + gap_x
        y -= rh + gap_y
    return out


def corps_planche(n, titre, places):
    """Blocs : titre, un clone par icône, légendes."""
    corps = [setv("ma_planche", n)]
    if titre:
        assert texte.largeur_px(titre, 14) < 470, titre
        corps.append(texte.ecrire(titre, 0, 160, 14, "jaune", 1))
    assert len(places) <= 120, (titre, len(places))
    for nom, legende, pct, x, y, w, h in places:
        corps += [costume(nom), taille(pct), aller(x, y), cloner_moi()]
    for nom, legende, pct, x, y, w, h in places:
        if legende:
            corps.append(texte.ecrire(legende, x, y - h / 2.0 - 11, 10, "gris", 1))
    return corps


PLANCHES = []       # (nom de fichier, titre, places)


def ajouter(nom, titre, places):
    PLANCHES.append((nom, titre, places))


# ---------------------------------------------------------------------------
#  objets, munitions, matériaux
# ---------------------------------------------------------------------------
objets = [(costume_ui("objet%d" % c, UI.icone_objet(c)), contrat.OBJETS[c].replace("Potion de bouclier", "Potion boucl.").replace("Mini-potion", "Mini-pot."), 100) for c in range(1, 9)]
ajouter("objets", "Objets d'inventaire 48 px (×1 et ×2)", disposer(objets + [(n, "", 200) for n, _, _ in objets], gap_x=2, gap_y=10, largeur_mini=56))
munmat = [(costume_ui("mun_" + t, UI.icone_munitions(t)), t, 100) for t in ("legeres", "cartouches", "lourdes")]
munmat += [(costume_ui("mat%d" % c, UI.icone_materiau(c)), contrat.MATERIAUX[c], 100) for c in (1, 2, 3)]
ajouter("munitions_materiaux", "Munitions et matériaux 32 px (×1, ×2, ×2,5)",
        disposer(munmat + [(n, "", 200) for n, _, _ in munmat] + [(n, "", 250) for n, _, _ in munmat], gap_y=10, largeur_mini=60))

# ---------------------------------------------------------------------------
#  personnages : 10 skins × 4 poses (style 0 puis style 1)
# ---------------------------------------------------------------------------
for style in (0, 1):
    places = []
    for skin in range(1, 11):
        x = -207 + (skin - 1) * 46
        for pose, pct, y in (("debout", 50, 112), ("emote", 50, 50), ("parachute", 50, -20), ("aterre", 45, -108)):
            nom = costume_ui("skin%d_%s_%d" % (skin, pose, style), UI.personnage(skin, pose, style))
            w, h = DIMS[nom]
            places.append((nom, UI.NOMS_SKINS[skin - 1] if pose == "aterre" else "", pct, x, y, w * pct / 100.0, h * pct / 100.0))
    ajouter("personnages" if style == 0 else "personnages_style1",
            "Personnages style %d : debout, émote, parachute, à terre (×0,5)" % style, places)

# skins en grand (debout ×1, à terre ×0,7)
places = []
for skin in range(1, 11):
    col, rang = (skin - 1) % 5, (skin - 1) // 5
    x = -184 + col * 92
    places.append(("skin%d_debout_0" % skin, "", 100, x, 105 - rang * 105, 60, 100))
    places.append(("skin%d_aterre_0" % skin, UI.NOMS_SKINS[skin - 1], 70, x, -78 - rang * 57, 70, 42))
ajouter("skins", "Skins 1 à 10 : debout (×1) et à terre (×0,7)", places)

# ---------------------------------------------------------------------------
#  cosmétiques
# ---------------------------------------------------------------------------
COURT = {"Pioche de base": "Base", "Clé géante": "Clé", "Pelle dorée": "Pelle", "Parachute militaire": "Para. milit.",
         "Aile de chauve-souris": "Chauve-souris", "Tapis volant": "Tapis", "Deltaplane": "Delta"}   # légendes courtes (cellules étroites)
pioches = [(costume_ui("pioche%d" % n, UI.pioche(n)), COURT.get(UI.NOMS_PIOCHES[n - 1], UI.NOMS_PIOCHES[n - 1]), 100) for n in range(1, 10)]
planeurs = [(costume_ui("planeur%d" % n, UI.planeur(n)), COURT.get(UI.NOMS_PLANEURS[n - 1], UI.NOMS_PLANEURS[n - 1]), 100) for n in range(1, 10)]
sprays = [(costume_ui("spray%d" % n, UI.spray(n)), contrat.SPRAYS[n - 1], 100) for n in range(1, 7)]
emotes = [(costume_ui("emote%d" % n, UI.emote(n)), contrat.EMOTES[n - 1][0], 100) for n in range(1, 7)]
bannieres = [(costume_ui("banniere%d" % n, UI.banniere(n)), UI.NOMS_BANNIERES[n - 1], 100) for n in range(1, 11)]
divisions = [(costume_ui("division%d" % n, UI.division(n)), UI.NOMS_DIVISIONS[n - 1], 100) for n in range(1, 8)]
medailles = [(costume_ui("medaille%d" % n, UI.medaille(n)), ["Or", "Argent", "Bronze"][n - 1], 100) for n in range(1, 4)]
zoom = lambda liste, pct: [(n, "", pct) for n, _, _ in liste]  # noqa: E731
ajouter("cosmetiques_a", "9 pioches 48, 9 planeurs 64×48, 6 sprays 64 (×1)", disposer(pioches + planeurs + sprays, gap_x=8, gap_y=8, largeur_mini=66))
ajouter("cosmetiques_b", "Émotes 48, 10 bannières 40, divisions 48, médailles 48 (×1)",
        disposer(emotes + bannieres + divisions + medailles, gap_y=10, largeur_mini=54))
ajouter("zoom_pioches_emotes", "Pioches et émotes (×1,5)", disposer(zoom(pioches, 150) + zoom(emotes, 150), gap_x=6, gap_y=10))
ajouter("zoom_planeurs", "Planeurs (×1,5)", disposer(zoom(planeurs, 150), gap_x=6, gap_y=10))
ajouter("zoom_sprays", "Sprays et médailles (×1,5)", disposer(zoom(sprays, 150) + zoom(medailles, 150), gap_x=6, gap_y=10))
ajouter("zoom_badges", "Divisions et bannières (×1,5)", disposer(zoom(divisions, 150) + zoom(bannieres, 150), gap_x=6, gap_y=10))

# ---------------------------------------------------------------------------
#  icônes
# ---------------------------------------------------------------------------
petites = [(costume_ui("onglet_" + o, UI.icone_onglet(o)), o, 100) for o in contrat.ONGLETS]
petites += [(costume_ui("quete_" + q, UI.icone_quete(q)), lib, 100) for q, lib in (("quotidienne", "quotid."), ("hebdomadaire", "hebdo"), ("histoire", "histoire"))]
petites += [(costume_ui("succes", UI.icone_succes()), "succès", 100)]
petites += [(costume_ui("ami_" + e, UI.icone_ami(e)), lib, 100) for e, lib in (("enligne", "en ligne"), ("enpartie", "en partie"), ("horsligne", "hors ligne"))]
petites += [(costume_ui("hp%d" % n, UI.icone_haut_parleur(n)), "hp %d" % n, 100) for n in range(4)]
petites += [(costume_ui("hp%d" % n, UI.icone_haut_parleur(n)), "hp %d %%" % n, 100) for n in (34, 68, 102)]   # volume en %
petites += [(costume_ui("oeil", UI.icone_oeil()), "œil", 100), (costume_ui("signaler", UI.icone_signaler()), "signaler", 100),
            (costume_ui("zone", UI.icone_zone()), "zone", 100), (costume_ui("bruit", UI.icone_bruit()), "bruit", 100),
            (costume_ui("jeton", UI.jeton()), "jeton", 100), (costume_ui("etoile", UI.etoile()), "étoile", 100),
            (costume_ui("cadenas", UI.cadenas()), "cadenas", 100), (costume_ui("coche", UI.coche()), "coche", 100),
            (costume_ui("croix", UI.croix()), "croix", 100)]
petites += [(costume_ui("fleche_" + d, UI.fleche(d)), d, 100) for d in ("haut", "bas", "gauche", "droite")]
petites += [(costume_ui("boussole", UI.boussole_curseur()), "boussole", 100), (costume_ui("parachute_i", UI.parachute_icone()), "parachute", 100),
            (costume_ui("planeur_i", UI.planeur_icone()), "planeur", 100)]
grandes = [(costume_ui("bus", UI.bus()), "bus", 100)]
grandes += [(costume_ui("marqueur_" + c, UI.marqueur(coul)), "ping", 100) for c, coul in (("jaune", "#facc15"), ("rouge", "#ef4444"), ("bleu", "#3b82f6"))]
grandes += [(costume_ui("carte_redep", UI.carte_redeploiement()), "redéploi.", 100), (costume_ui("balise", UI.balise()), "balise", 100),
            (costume_ui("coffre_ouvert", UI.coffre_ouvert()), "coffre ouvert", 100), (costume_ui("fleche_degats", UI.fleche_degats()), "dégâts", 100),
            (costume_ui("bus_carte", UI.bus_carte()), "bus carte", 100), (costume_ui("parachute_carte", UI.parachute_carte()), "para. carte", 100),
            (costume_ui("coffre_carte", UI.coffre_carte()), "coffre carte", 100)]
ajouter("icones", "Petites icônes d'interface 24/32 px (×1)", disposer(petites, gap_y=10, largeur_mini=50))
ajouter("icones_grandes", "Bus, pings, carte, balise, coffre ouvert, dégâts (×1)", disposer(grandes, gap_y=10, largeur_mini=60))
ajouter("icones_grandes_x2", "Bus, pings, carte, balise, coffre ouvert, dégâts (×2)", disposer(zoom(grandes, 200), gap_x=8, gap_y=10))
ajouter("icones_x2a", "Icônes ×2 (onglets, quêtes, succès, amis, haut-parleur)", disposer(zoom(petites[:21], 200), gap_y=10))
ajouter("icones_x2b", "Icônes ×2 (divers, flèches, boussole, parachute, planeur)", disposer(zoom(petites[21:], 200), gap_y=10))
ajouter("icones_carte_x3", "Icônes de la carte plein écran (bus, parachute, coffre) ×1, ×2 et ×3",
        disposer(grandes[-3:] + zoom(grandes[-3:], 200) + zoom(grandes[-3:], 300), gap_x=20, gap_y=14, largeur_mini=70))

# ---------------------------------------------------------------------------
#  composants : cercle de progression, barres, boutons, onglets, panneau, logo
# ---------------------------------------------------------------------------
items = [(costume_ui("cercle%d" % p, UI.cercle_interaction(p)), "%d %%" % p, 100) for p in (0, 25, 60, 100)]
items += [(costume_ui("barre_vie", UI.barre(120, 14, "#22c55e", 100)), "vie 100", 100), (costume_ui("barre_bouclier", UI.barre(120, 14, "#3b82f6", 70)), "bouclier 70", 100),
          (costume_ui("barre_rouge", UI.barre(120, 14, "#ef4444", 35)), "vie 35", 100), (costume_ui("barre_or", UI.barre(200, 20, "#f59e0b", 80)), "XP 80", 100),
          (costume_ui("barre_vide", UI.barre(80, 10, "#22d3ee", 0)), "vide", 100)]
items += [(costume_ui("bouton", UI.bouton(120, 36)), "bouton", 100), (costume_ui("bouton_survol", UI.bouton(120, 36, True)), "survol", 100),
          (costume_ui("bouton_or", UI.bouton(160, 44, False, "#f59e0b")), "jouer", 100), (costume_ui("bouton_or_survol", UI.bouton(160, 44, True, "#f59e0b")), "jouer survol", 100)]
ajouter("composants", "Progression, barres, boutons", disposer(items, gap_y=12))
items = [(costume_ui("onglet_actif", UI.onglet_fond(True)), "onglet actif", 100), (costume_ui("onglet_inactif", UI.onglet_fond(False)), "onglet inactif", 100),
         (costume_ui("panneau", UI.panneau(200, 90)), "panneau 200×90", 100), (costume_ui("panneau_large", UI.panneau(440, 60)), "panneau 440×60", 100),
         (costume_ui("logo", UI.logo()), "logo 300×80", 100)]
ajouter("composants_b", "Onglets, panneaux, logo", disposer(items, gap_y=14))

# ---------------------------------------------------------------------------
#  cartes
# ---------------------------------------------------------------------------
carte = costume_ui("carte_complete", UI.carte_complete())
mini = costume_ui("carte_minimap", UI.carte_minimap())
ajouter("cartes", "Carte complète 320×320 (×1) — minicarte 109×109 (×1 et ×1,5)",
        [(carte, "", 100, -80, -10, 320, 320), (mini, "minicarte ×1", 100, 155, 95, 109, 109), (mini, "minicarte ×1,5", 150, 155, -72, 164, 164)])
carte5 = costume_ui("carte_complete5", UI.carte_complete(5))
carte7 = costume_ui("carte_complete7", UI.carte_complete(7))
ajouter("cartes_echelles", "Carte complète à 5 px/case (160, appel de Menus) et 7 px/case (224)",
        [(carte5, "échelle 5", 100, -150, 50, 160, 160), (carte7, "échelle 7", 100, 75, -8, 224, 224)])

# ---------------------------------------------------------------------------
#  fonds (×0,28) puis chaque fond en plein écran avec le logo
# ---------------------------------------------------------------------------
VARIANTES = ["connexion", "salon", "matchmaking", "chargement", "victoire", "defaite", "fin", "tempete", "ciel"]
fonds = [costume_ui("fond_" + v, UI.fond_ecran(v)) for v in VARIANTES]
places = []
for i, (v, nom) in enumerate(zip(VARIANTES, fonds)):
    col, rang = i % 3, i // 3
    places.append((nom, v, 23, -160 + col * 160, 100 - rang * 100, 110, 83))
ajouter("fonds", "Fonds d'écran 480×360 (×0,23)", places)
for v, nom in zip(VARIANTES, fonds):
    ajouter("fond_" + v, "", [(nom, "", 100, 0, 0, 480, 360), ("logo", "", 100, 0, 110, 300, 80)])

# ---------------------------------------------------------------------------
#  scripts
# ---------------------------------------------------------------------------
texte.installer(S)
V = Var
selection = []
for n, (nom, titre, places) in enumerate(PLANCHES, 1):
    selection.append(si(eq(V("derniere"), n), corps_planche(n, titre, places)))
S.script(quand_drapeau(), [
    cacher(), aller(0, 0), effacer_effets(), setv("derniere", -1), attendre(0.6),
    toujours([
        si(non(eq(V("demo_planche"), V("derniere"))), [
            setv("derniere", V("demo_planche")), attendre(0.15), effacer(),
            selection,
        ]),
    ]),
])
S.script(quand_clone(), [montrer(), attendre_jusqua(non(eq(V("demo_planche"), V("ma_planche")))), supprimer_clone()])

contrat.finaliser_textes(stage)
ecrire_sb3(P, SORTIE)
with open(os.path.join(ICI, "planches.json"), "w", encoding="utf-8") as f:
    json.dump([{"nom": nom, "titre": titre, "clones": len(places)} for nom, titre, places in PLANCHES], f, ensure_ascii=False, indent=1)
print("%s : %d costumes, %d planches (%s clones)" % (SORTIE, len(S.costumes), len(PLANCHES), "/".join(str(len(p)) for _, _, p in PLANCHES)))
