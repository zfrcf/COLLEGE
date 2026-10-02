# -*- coding: utf-8 -*-
"""
Démo de la banque de sons : génère outils/demos/sons/demo.sb3.

Au drapeau vert, le sprite « Demo » :
  1. pose ecran = salon et diffuse « demarrer » (le sprite Sons lance la musique du salon) ;
  2. diffuse « son <nom> » pour chacun des 28 sons toutes les 0,6 s, avec un pan alterné
     (-70 / 0 / 70) et un volume relatif de 100 ou 60 ; il affiche la carte (forme d'onde)
     du son courant et tamponne une pastille colorée par son joué (bleu effets, orange voix,
     vert musique) ;
  3. passe à ecran = jeu (la musique doit s'arrêter), revient au salon (elle reprend),
     diffuse « son stop tout » (tout coupé, la musique reprend d'elle-même) puis
     « son stop musique » (silence jusqu'au prochain changement d'écran).

    python3 outils/demos/sons/demo.py
"""
import os
import sys

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..", "..")))
from royale.dsl import *  # noqa: E402,F401
from royale import contrat, sons  # noqa: E402
from royale.svg import svg, echapper, svg_vide, svg_cercle  # noqa: E402

COULEURS = {"effets": "#4cc9f0", "voix": "#f9a826", "musique": "#7bd389"}


def carte(nom, ech, rate):
    """Carte 440x200 : nom, catégorie, taux, durée, pic et forme d'onde (enveloppe min/max par colonne)."""
    colonnes, x0, cy, amp = 400, 20, 116, 60      # forme d'onde entre y = 56 et 176 : titre au-dessus, infos en dessous
    n = len(ech)
    pas = n / float(colonnes)
    segments = []
    for c in range(colonnes):
        a = int(c * pas)
        b = max(a + 1, int((c + 1) * pas))
        tranche = ech[a:b]
        y1 = cy - max(tranche) * amp
        y2 = cy - min(tranche) * amp
        if y2 - y1 < 1:
            y2 = y1 + 1
        segments.append("M%d %.1fV%.1f" % (x0 + c, y1, y2))
    cat = sons.categorie(nom)
    coul = COULEURS[cat]
    return svg(440, 200, (
        '<rect width="440" height="200" rx="16" fill="#16213e" stroke="%s" stroke-width="3"/>' % coul
        + '<text x="22" y="40" font-family="Sans Serif" font-weight="bold" font-size="26" fill="#ffffff">%s</text>' % echapper(nom)
        + '<text x="418" y="191" text-anchor="end" font-family="Sans Serif" font-size="14" fill="#c8d3f5">%s · %d Hz · %.2f s · pic %.2f</text>'
        % (cat, rate, n / rate, max(abs(v) for v in ech))
        + '<line x1="20" y1="%d" x2="420" y2="%d" stroke="#2f3b63" stroke-width="1"/>' % (cy, cy)
        + '<path d="%s" stroke="%s" stroke-width="1" fill="none"/>' % ("".join(segments), coul)))


def scene():
    legende = ""
    for i, (cat, coul) in enumerate(COULEURS.items()):
        legende += '<circle cx="%d" cy="343" r="6" fill="%s"/><text x="%d" y="348" font-family="Sans Serif" font-size="13" fill="#c8d3f5">%s</text>' % (
            40 + i * 110, coul, 52 + i * 110, cat)
    return svg(480, 360, (
        '<rect width="480" height="360" fill="#0b1021"/>'
        '<text x="240" y="36" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="22" fill="#ffffff">Royale 3D — banque de sons (démo)</text>'
        '<text x="240" y="58" text-anchor="middle" font-family="Sans Serif" font-size="13" fill="#8fa3d9">un son toutes les 0,6 s · pan -70 / 0 / 70 · volume 100 ou 60</text>'
        + legende))


def construire(chemin):
    P = Projet()
    stage = Cible(P, "Stage", is_stage=True)
    stage.costumes = [P.costume("scène", scene(), 240, 180)]
    contrat.declarer_globales(stage)
    banque = sons.fabriquer_sons()
    sons.installer(P, banque)

    D = Cible(P, "Demo")
    D.layer = 50
    D.visible = False
    D.costumes = [P.costume("vide", svg_vide(), 2, 2)]
    for nom in contrat.SONS:
        ech, rate = sons.generer(nom)
        D.costumes.append(P.costume(nom, carte(nom, ech, rate), 220, 100))
    for cat, coul in COULEURS.items():
        D.costumes.append(P.costume("point_" + cat, svg_cercle(12, coul, 1.0, "#ffffff", 1), 6, 6))

    corps = [effacer(), cacher(), effacer_effets(), costume("vide"), taille(100), aller(0, 8),
             setv("ecran", "salon"), setv("son_volume", 100), setv("son_pan", 0),
             diffuser("demarrer"), montrer(), dire("ecran = salon : la musique démarre"), attendre(0.8)]
    for k, nom in enumerate(contrat.SONS):
        pan = (-70, 0, 70)[k % 3]
        vol = 60 if k % 4 == 3 else 100
        corps += [
            setv("son_pan", pan), setv("son_volume", vol), diffuser("son " + nom),
            costume("point_" + sons.categorie(nom)), aller(-216 + 16 * k, -128), tampon(),
            costume(nom), aller(0, 8), dire("%d/28 · pan %d · volume %d" % (k + 1, pan, vol)),
            attendre(0.6),
        ]
    corps += [
        setv("ecran", "jeu"), dire("ecran = jeu : la musique s'arrête"), attendre(1.5),
        setv("ecran", "salon"), dire("ecran = salon : la musique reprend"), attendre(1.5),
        diffuser("son stop tout"), dire("son stop tout : la musique reprend d'elle-même"), attendre(1.5),
        diffuser("son stop musique"), dire("son stop musique : silence jusqu'au prochain écran"),
    ]
    D.script(quand_drapeau(), corps)

    contrat.finaliser_textes(stage)
    ecrire_sb3(P, chemin)
    return os.path.getsize(chemin)


if __name__ == "__main__":
    chemin = os.path.join(ICI, "demo.sb3")
    taille_sb3 = construire(chemin)
    print("écrit %s (%.0f Ko)" % (chemin, taille_sb3 / 1024))
