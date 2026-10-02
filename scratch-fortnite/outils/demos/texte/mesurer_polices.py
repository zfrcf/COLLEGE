#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mesure les polices Scratch (scratch-render-fonts) pour le moteur de texte.

Pour chaque police et chaque caractère du jeu de glyphes : largeur d'avance
(hmtx) et boîte englobante du dessin, convertie en px pour une hauteur de
majuscule de 28 px (boîte de référence 40 px). Le résultat est imprimé sous
forme de dictionnaire Python à coller dans royale/texte.py (POLICES).

Usage :
    PYTHONPATH=<dossier contenant fontTools> python3 mesurer_polices.py
Dépendance : fontTools (pip install fonttools --target <dossier>).
"""
import os
import sys

from fontTools.pens.boundsPen import BoundsPen
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


if __name__ == "__main__":
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
