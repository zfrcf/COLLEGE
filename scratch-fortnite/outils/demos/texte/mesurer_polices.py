#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mesure les polices Scratch (scratch-render-fonts) pour le moteur de texte.

Pour chaque police et chaque caractère du jeu de glyphes : largeur d'avance
(hmtx) et boîte englobante du dessin, convertie en px pour une hauteur de
majuscule de 28 px (boîte de référence 40 px). Le résultat est imprimé sous
forme de dictionnaire Python à coller dans royale/texte.py (POLICES).

Usage :
    PYTHONPATH=<dossier contenant fontTools> python3 mesurer_polices.py             → table POLICES (stdout)
    PYTHONPATH=<dossier contenant fontTools> python3 mesurer_polices.py --contours  → royale/texte_glyphes.json
Dépendance : fontTools (pip install fonttools --target <dossier>).

Le mode --contours extrait le tracé vectoriel (attribut « d » d'un <path>) de chaque
glyphe, en px pour une majuscule de 28 px, origine au début de la ligne de base, y vers
le bas. texte.py s'en sert pour fabriquer les costumes sans balise <text> : les SVG
restent minuscules (pas de police de 450 Ko injectée dans chaque image par
scratch-svg-renderer) et se chargent instantanément.
"""
import os
import sys

import json

from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ICI = os.path.dirname(os.path.abspath(__file__))
DOSSIER_POLICES = os.path.join(ICI, "..", "..", "node_modules", "scratch-render-fonts", "src")

# Fichier de chaque police Scratch (voir scratch-render-fonts/src/index.js).
POLICES = {
    "Sans Serif": "NotoSans-Medium.ttf",
    "Serif": "SourceSerifPro-Regular.otf",
    "Handwriting": "handlee-regular.ttf",
    "Marker": "Knewave.ttf",
    "Curly": "Griffy-Regular.ttf",
    "Pixel": "Grand9K-Pixel.ttf",
    "Scratch": "Scratch.ttf",
}

sys.path.insert(0, os.path.join(ICI, "..", "..", ".."))
from royale.texte import CARACTERES_POLICE, CAP_REFERENCE  # noqa: E402


def mesurer(nom):
    fichier = POLICES[nom]
    f = TTFont(os.path.join(DOSSIER_POLICES, fichier))
    upm = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    glyphes = f.getGlyphSet()
    hmtx = f["hmtx"]

    def bornes(g):
        p = BoundsPen(glyphes)
        glyphes[g].draw(p)
        return p.bounds  # (xMin, yMin, xMax, yMax) ou None

    # hauteur de majuscule mesurée sur « H »
    bH = bornes(cmap[ord("H")])
    cap = bH[3] / upm
    fs = CAP_REFERENCE / cap            # taille de police (px) pour une majuscule de 28 px
    larg = {}
    y_max = 0.0
    y_min = 0.0
    x_min = 0.0
    manquants = []
    for c in CARACTERES_POLICE:
        if ord(c) not in cmap:
            manquants.append(c)
            continue
        g = cmap[ord(c)]
        larg[c] = round(hmtx[g][0] / upm * fs, 2)
        b = bornes(g)
        if b:
            y_max = max(y_max, b[3] / upm * fs)
            y_min = min(y_min, b[1] / upm * fs)
            x_min = min(x_min, b[0] / upm * fs)
    return {"fichier": fichier, "fs": round(fs, 2), "montee": round(y_max, 1),
            "descente": round(-y_min, 1), "debord_gauche": round(-x_min, 1), "largeurs": larg,
            "manquants": manquants}


def _nombre(v):
    """Nombre compact à 1 décimale (« 12.5 », « -3 ») : 0,05 px d'erreur au plus à la taille 40."""
    t = "%.1f" % v
    t = t.rstrip("0").rstrip(".")
    return "0" if t in ("-0", "") else t


def contours(nom):
    """Tracés SVG (px, origine ligne de base, y vers le bas) de chaque caractère de la police."""
    f = TTFont(os.path.join(DOSSIER_POLICES, POLICES[nom]))
    upm = f["head"].unitsPerEm
    cmap = f.getBestCmap()
    glyphes = f.getGlyphSet()
    bH = BoundsPen(glyphes)
    glyphes[cmap[ord("H")]].draw(bH)
    k = CAP_REFERENCE / (bH.bounds[3] / upm) / upm     # unités de police → px
    out = {}
    for c in CARACTERES_POLICE:
        if ord(c) not in cmap:
            continue
        pen = SVGPathPen(glyphes, ntos=_nombre)
        glyphes[cmap[ord(c)]].draw(TransformPen(pen, (k, 0, 0, -k, 0, 0)))
        d = pen.getCommands()
        if d:
            out[c] = d
    return out


if __name__ == "__main__":
    if "--contours" in sys.argv:
        chemin = os.path.join(ICI, "..", "..", "..", "royale", "texte_glyphes.json")
        data = {nom: contours(nom) for nom in POLICES}
        with open(chemin, "w", encoding="utf-8") as fichier:
            json.dump(data, fichier, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        print("contours écrits :", os.path.normpath(chemin), "—", sum(len(v) for v in data.values()), "glyphes,",
              os.path.getsize(chemin) // 1024, "Ko")
        sys.exit(0)
    print("# Généré par outils/demos/texte/mesurer_polices.py — ne pas éditer à la main.")
    print("POLICES = {")
    for nom in POLICES:
        m = mesurer(nom)
        print("    %r: {" % nom)
        for cle in ("fs", "montee", "descente", "debord_gauche"):
            print("        %r: %r," % (cle, m[cle]))
        print("        'largeurs': {")
        items = sorted(m["largeurs"].items())
        ligne = "           "
        for c, w in items:
            morceau = " %r: %r," % (c, w)
            if len(ligne) + len(morceau) > 110:
                print(ligne)
                ligne = "           "
            ligne += morceau
        print(ligne)
        print("        },")
        print("    },")
        if m["manquants"]:
            print("    # %s : glyphes absents de la police : %s" % (nom, "".join(m["manquants"])), file=sys.stderr)
    print("}")
