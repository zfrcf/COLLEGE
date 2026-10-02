# -*- coding: utf-8 -*-
"""
Sprite « HUD » : l'interface en jeu, redessinée à chaque image après le rendu 3D.

Écrans concernés : « jeu », « prepartie », « spectateur », « pause » (le HUD complet ; en pause,
Menus dessine son panneau par-dessus), plus l'altimètre seul sur « parachute » / « bus ».
Rien sur les autres écrans. Le sprite n'appelle jamais « effacer » : Moteur3D (ou Partie)
possède le fond.

Disposition (coordonnées Scratch, (0,0) au centre, tout mis à l'échelle par param_tailleHUD
en gardant les ancrages aux bords) :
  - bas gauche   : vie, bouclier, surbouclier, endurance
  - bas centre   : barre d'inventaire (5 cases) + pioche
  - bas droite   : munitions / rechargement, puis matériaux (bois, pierre, métal)
  - sous la minicarte : joueurs restants, éliminations, équipes vivantes
  - haut centre  : boussole graduée (N = 90°, E = 0°), minuteur de tempête, temps de partie,
                   bandeaux d'état (pré-partie invulnérable, tempête), notifications
  - haut gauche  : panneau d'équipe puis journal d'éliminations
  - centre       : chiffres de dégâts, flèche de dégâts, bruits, barres d'interaction / de soin,
                   états à terre / mort, sous-titres
Options : param_afficherFPS, param_afficherPing, param_infosReseau, param_sousTitres,
param_daltonisme (couleurs des barres et des équipes).

Variables globales écrites : fps (mesure réelle des images par seconde), hud_glyphes (nombre de
glyphes tamponnés pendant la dernière image — budget ≤ 250 en jeu, ≈ 165 en situation courante).
Événements écoutés : evt degats (flèche), evt tir / evt degats / evt coffre / evt phase /
evt elimination (sous-titres).
Icônes : royale.svg_ui si disponible (import protégé, voir _svg_ui), sinon des SVG simples de
remplacement ; toutes normalisées dans un carré de 32 px (_normaliser).

Performance : le HUD coûte ≈ 4 ms d'interprétation par image (≈ 160 glyphes, ≈ 60 primitives).
Il ne se dessine qu'une fois par valeur de `chrono` (figé pendant un pas du séquenceur) : une fois par
image dans le navigateur, une seule fois par pas en VM sans rendu / mode turbo où le séquenceur
enchaîne plusieurs passes. Les textes posés sur une pilule sombre sont écrits sans ombre ; les textes
mesurés pour dimensionner leur pilule sont dessinés avec « txt_dessiner » (une seule mesure) ; le texte
tronqué du journal est mis en cache (listes locales hud_jt / hud_jw).
Mise au point : PROFIL = True ajoute la liste locale hud_profil ; HUD_SANS="section,…" (variable
d'environnement à la génération) retire des sections (voir SECTIONS dans « dessiner hud »).
"""
import os
import re

from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S
from . import texte

ORDRE = 40
V = Var
A = Arg
PROFIL = False      # True : mesure le temps par section (liste locale hud_profil) — outil de mise au point

ICONE = 32          # taille nominale (px) de toutes les icônes du HUD après normalisation
_TAILLES = {}       # nom de costume -> taille nominale (px) pour `icone()`


# ---------------------------------------------------------------------------
#  Icônes : svg_ui si possible, sinon un SVG de remplacement
# ---------------------------------------------------------------------------
def _svg_ui(nom, *args):
    try:
        from . import svg_ui
    except Exception:
        return None
    f = getattr(svg_ui, nom, None)
    if f is None:
        return None
    try:
        r = f(*args)
    except Exception:
        return None
    return r if isinstance(r, str) and "<svg" in r else None


def _s32(contenu):
    return S.svg(ICONE, ICONE, contenu)


def _objet_defaut(code):
    d = {
        1: '<rect x="4" y="11" width="22" height="7" rx="2" fill="#374151" stroke="#111" stroke-width="1.2"/>'
           '<rect x="7" y="17" width="7" height="10" rx="2" fill="#6b4f2a" stroke="#111" stroke-width="1.2" transform="rotate(10 10 22)"/>'
           '<rect x="22" y="12" width="7" height="4" fill="#4b5563"/>',
        2: '<rect x="2" y="13" width="28" height="6" rx="2" fill="#4b5563" stroke="#111" stroke-width="1.2"/>'
           '<rect x="2" y="16" width="10" height="7" rx="2" fill="#7c4a1e" stroke="#111" stroke-width="1.2"/>'
           '<rect x="16" y="18" width="9" height="4" rx="1" fill="#92400e"/>',
        3: '<rect x="1" y="15" width="30" height="4" rx="1" fill="#374151" stroke="#111" stroke-width="1"/>'
           '<rect x="2" y="18" width="9" height="6" rx="2" fill="#3f6212" stroke="#111" stroke-width="1"/>'
           '<rect x="11" y="9" width="10" height="4" rx="2" fill="#111"/><circle cx="12" cy="11" r="2" fill="#67e8f9"/>',
        4: '<rect x="6" y="10" width="20" height="12" rx="6" fill="#f3f4f6" stroke="#9ca3af" stroke-width="1.5"/>'
           '<path d="M8 16 H24" stroke="#9ca3af" stroke-width="1.5" stroke-dasharray="2 2"/>',
        5: '<rect x="5" y="8" width="22" height="18" rx="3" fill="#f9fafb" stroke="#9ca3af" stroke-width="1.5"/>'
           '<rect x="14" y="11" width="4" height="12" fill="#ef4444"/><rect x="10" y="15" width="12" height="4" fill="#ef4444"/>',
        6: '<rect x="13" y="6" width="6" height="5" fill="#93c5fd"/>'
           '<path d="M11 11 h10 v4 l4 8 a3 3 0 0 1 -3 4 h-12 a3 3 0 0 1 -3 -4 l4 -8 z" fill="#3b82f6" stroke="#1e3a8a" stroke-width="1.5"/>',
        7: '<rect x="12" y="3" width="8" height="6" fill="#93c5fd"/>'
           '<rect x="8" y="9" width="16" height="20" rx="4" fill="#2563eb" stroke="#1e3a8a" stroke-width="1.5"/>'
           '<rect x="11" y="14" width="10" height="8" rx="1" fill="#60a5fa"/>',
        8: '<rect x="14" y="8" width="4" height="22" rx="1" fill="#92400e" transform="rotate(-30 16 19)"/>'
           '<path d="M4 12 Q16 2 28 12 L26 15 Q16 8 6 15 Z" fill="#9ca3af" stroke="#374151" stroke-width="1.2"/>',
    }
    return _s32(d[code])


def _munitions_defaut(type_mun):
    if type_mun == "legeres":
        c = "".join('<rect x="%d" y="9" width="5" height="14" rx="2.5" fill="#facc15" stroke="#854d0e" stroke-width="1"/>' % x
                    for x in (6, 13, 20))
    elif type_mun == "cartouches":
        c = "".join('<rect x="%d" y="8" width="7" height="16" rx="1.5" fill="#dc2626" stroke="#450a0a" stroke-width="1"/>'
                    '<rect x="%d" y="19" width="7" height="5" fill="#d4a017"/>' % (x, x) for x in (6, 18))
    else:
        c = ('<rect x="11" y="4" width="10" height="24" rx="4" fill="#9ca3af" stroke="#1f2937" stroke-width="1.2"/>'
             '<rect x="11" y="20" width="10" height="8" fill="#d4a017"/>')
    return _s32(c)


def _materiau_defaut(code):
    if code == 1:
        c = ('<rect x="3" y="8" width="26" height="7" rx="1.5" fill="#b45309" stroke="#78350f" stroke-width="1"/>'
             '<rect x="3" y="17" width="26" height="7" rx="1.5" fill="#d97706" stroke="#78350f" stroke-width="1"/>')
    elif code == 2:
        c = ('<path d="M4 24 L8 12 L15 10 L20 14 L28 13 L29 24 Z" fill="#9ca3af" stroke="#374151" stroke-width="1.2"/>'
             '<path d="M12 24 L15 16 L21 24" fill="none" stroke="#6b7280" stroke-width="1"/>')
    else:
        c = ('<rect x="3" y="6" width="26" height="20" rx="2" fill="#64748b" stroke="#1e293b" stroke-width="1.2"/>'
             '<circle cx="8" cy="11" r="1.6" fill="#cbd5e1"/><circle cx="24" cy="11" r="1.6" fill="#cbd5e1"/>'
             '<circle cx="8" cy="21" r="1.6" fill="#cbd5e1"/><circle cx="24" cy="21" r="1.6" fill="#cbd5e1"/>')
    return _s32(c)


def _planeur_defaut():
    return _s32('<path d="M2 16 Q16 1 30 16 Z" fill="#60a5fa" stroke="#1e3a8a" stroke-width="1.5"/>'
                '<path d="M6 16 L16 27 L26 16 M16 16 L16 27" fill="none" stroke="#e5e7eb" stroke-width="1.5"/>'
                '<rect x="13" y="26" width="6" height="4" rx="1" fill="#f1c27d"/>')


def _zone_defaut(rouge=False):
    col = "#f87171" if rouge else "#c4b5fd"
    return _s32('<circle cx="16" cy="16" r="11" fill="none" stroke="%s" stroke-width="3"/>'
                '<circle cx="16" cy="16" r="3.5" fill="%s"/>'
                '<path d="M16 2 V6 M16 26 V30 M2 16 H6 M26 16 H30" stroke="%s" stroke-width="2"/>' % (col, col, col))


ICONES_PROPRES = {
    "hud_bouclier": '<path d="M16 2 L28 6.5 V15 C28 22 23 27.5 16 30.5 C9 27.5 4 22 4 15 V6.5 Z" fill="#3b82f6" stroke="#dbeafe" stroke-width="2"/>'
                    '<path d="M16 7 V26" stroke="#93c5fd" stroke-width="1.5"/>',
    "hud_joueurs": '<circle cx="11" cy="10" r="5.5" fill="#fff"/><circle cx="23" cy="11.5" r="4.5" fill="#d1d5db"/>'
                   '<path d="M2 28 a9 9 0 0 1 18 0 z" fill="#fff"/><path d="M18 28 a7 7 0 0 1 13 0 z" fill="#d1d5db"/>',
    "hud_crane": '<circle cx="16" cy="13" r="10.5" fill="#fff"/><rect x="10" y="20" width="12" height="8" rx="2" fill="#fff"/>'
                 '<circle cx="12" cy="13" r="3" fill="#111"/><circle cx="20" cy="13" r="3" fill="#111"/>'
                 '<path d="M16 16 L14.5 19 H17.5 Z" fill="#111"/><rect x="13" y="24" width="2" height="4" fill="#111"/>'
                 '<rect x="17" y="24" width="2" height="4" fill="#111"/>',
    "hud_horloge": '<circle cx="16" cy="17" r="11" fill="none" stroke="#fff" stroke-width="3"/>'
                   '<path d="M16 10 V17 L21 20" stroke="#fff" stroke-width="3" fill="none" stroke-linecap="round"/>'
                   '<rect x="12" y="1.5" width="8" height="4" rx="1" fill="#fff"/>',
    "hud_infini": '<path d="M4 16 C4 9 13 9 16 16 C19 23 28 23 28 16 C28 9 19 9 16 16 C13 23 4 23 4 16 Z" '
                  'fill="none" stroke="#fff" stroke-width="3.5"/>',
    "hud_brique": '<rect x="3" y="8" width="26" height="16" fill="#b45309"/>'
                  '<path d="M3 16 H29 M11 8 V16 M21 8 V16 M7 16 V24 M16 16 V24 M25 16 V24" stroke="#78350f" stroke-width="2"/>',
    "hud_carte": '<rect x="8" y="3" width="16" height="26" rx="3" fill="#60a5fa" stroke="#1e3a8a" stroke-width="2"/>'
                 '<path d="M12 10 h8 M12 16 h8 M12 22 h5" stroke="#dbeafe" stroke-width="2"/>',
    "hud_micro": '<rect x="12" y="3" width="8" height="15" rx="4" fill="#fff"/>'
                 '<path d="M8 14 a8 8 0 0 0 16 0 M16 22 V28 M11 28 H21" stroke="#fff" stroke-width="2.5" fill="none"/>',
}

# Fonds tamponnés (taille réelle, pas de normalisation) : (nom, svg, cx, cy)
FONDS = [
    ("hud_case", S.svg(32, 32, '<rect x="1" y="1" width="30" height="30" rx="5" fill="#0f172a" fill-opacity="0.62" '
                              'stroke="#cbd5e1" stroke-opacity="0.55" stroke-width="1.5"/>'), 16, 16),
    ("hud_case_active", S.svg(32, 32, '<rect x="1" y="1" width="30" height="30" rx="5" fill="#334155" fill-opacity="0.75" '
                                     'stroke="#facc15" stroke-width="2.5"/>'), 16, 16),
    ("hud_rangee", S.svg(124, 24, '<rect x="0.5" y="0.5" width="123" height="23" rx="5" fill="#0f172a" fill-opacity="0.6" '
                                 'stroke="#64748b" stroke-opacity="0.5" stroke-width="1"/>'), 62, 12),
    ("hud_panneau", S.svg(150, 46, '<rect x="0.5" y="0.5" width="149" height="45" rx="5" fill="#0f172a" fill-opacity="0.7" '
                                  'stroke="#64748b" stroke-opacity="0.6" stroke-width="1"/>'), 75, 23),
]


def _normaliser(svg_txt, taille=ICONE):
    """Ramène un SVG quelconque dans un carré `taille` × `taille` (contenu centré, proportions gardées)."""
    m = re.search(r"<svg[^>]*>", svg_txt)
    if not m:
        return svg_txt
    ouverture = m.group(0)
    interieur = svg_txt[m.end():]
    fin = interieur.rfind("</svg>")
    if fin >= 0:
        interieur = interieur[:fin]
    vb = re.search(r'viewBox="([-\d.]+)[ ,]+([-\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)"', ouverture)
    if vb:
        x0, y0, w, h = [float(v) for v in vb.groups()]
    else:
        mw = re.search(r'width="([\d.]+)', ouverture)
        mh = re.search(r'height="([\d.]+)', ouverture)
        x0, y0 = 0.0, 0.0
        w = float(mw.group(1)) if mw else taille
        h = float(mh.group(1)) if mh else taille
    f = taille / max(w, h, 1.0)
    dx = (taille - w * f) / 2 - x0 * f
    dy = (taille - h * f) / 2 - y0 * f
    return S.svg(taille, taille, '<g transform="translate(%.3f %.3f) scale(%.4f)">%s</g>' % (dx, dy, f, interieur))


def _icones():
    """Liste (nom, svg 32×32) de toutes les icônes du HUD."""
    out = []
    for code in range(1, 9):
        out.append(("hud_obj%d" % code, _svg_ui("icone_objet", code) or _objet_defaut(code)))
    for n, t in [(1, "legeres"), (2, "cartouches"), (3, "lourdes")]:
        out.append(("hud_mun%d" % n, _svg_ui("icone_munitions", t) or _munitions_defaut(t)))
    for code in range(1, 4):
        out.append(("hud_mat%d" % code, _svg_ui("icone_materiau", code) or _materiau_defaut(code)))
    out.append(("hud_planeur", _svg_ui("planeur", 1) or _planeur_defaut()))
    out.append(("hud_zone", _svg_ui("icone_zone") or _zone_defaut()))
    out.append(("hud_zone_rouge", _zone_defaut(True)))
    out.append(("hud_carte", _svg_ui("carte_redeploiement") or _s32(ICONES_PROPRES["hud_carte"])))
    for nom, contenu in ICONES_PROPRES.items():
        if nom != "hud_carte":
            out.append((nom, _s32(contenu)))
    return [(nom, _normaliser(svg_txt)) for nom, svg_txt in out]


# ---------------------------------------------------------------------------
#  Aides de mise en page (expressions Scratch) — `s` = param_tailleHUD / 100
# ---------------------------------------------------------------------------
def sc(v):
    """Longueur mise à l'échelle."""
    return mul(v, V("s"))


def ax(ancre, d=0):
    """Ancre fixe + décalage mis à l'échelle."""
    if d == 0:
        return ancre
    return add(ancre, mul(d, V("s")))


ay = ax


def T(txt, x, y, taille_px, couleur="blanc", al=0):
    return appel("txt", txt, x, y, taille_px, couleur, al)


def TT(txt, x, y, taille_px, couleur, al, lmax):
    """Texte tronqué ; `lmax` en px absolus (non mis à l'échelle : garde les colonnes séparées à 120 %)."""
    return appel("txtt", txt, x, y, taille_px, couleur, al, lmax)


def M(txt, taille_px):
    """Mesure `txt` (→ variable w, et txt_glyphes prêt pour `D`)."""
    return appel("mesure", txt, taille_px)


def D(x, y, taille_px, couleur="blanc", al=0):
    """Dessine le dernier texte mesuré par `M` (évite une seconde passe de mesure)."""
    return appel("dessine", x, y, taille_px, couleur, al)


def O(*blocs):
    """Blocs écrits avec ombre portée (textes posés directement sur le rendu 3D)."""
    return [setv("txt_ombre", 1)] + list(blocs) + [setv("txt_ombre", 0)]


def icone(nom, x, y, px):
    """Tamponne l'icône `nom` (taille `px` avant mise à l'échelle) centrée en (x, y)."""
    base = _TAILLES.get(nom, ICONE)
    return [costume(nom), taille(mul(100.0 * px / base, V("s"))), aller(x, y), tampon()]


def fond(x1, y, x2, h, lum=6, transp=42):
    """Pilule sombre (ligne épaisse) de (x1, y) à (x2, y), épaisseur h (déjà à l'échelle)."""
    return [couleur_hsbt(0, 0, lum, transp), taille_stylo(h), ligne(x1, y, x2, y)]


def barre(x, y, l, h, p, teinte, sat, lum):
    return appel("barre", x, y, l, h, p, teinte, sat, lum)


def ecran_hud():
    return ou(ou(eq(V("ecran"), "jeu"), eq(V("ecran"), "prepartie")),
              ou(eq(V("ecran"), "spectateur"), eq(V("ecran"), "pause")))


def ecran_altimetre():
    return ou(eq(V("ecran"), "parachute"), eq(V("ecran"), "bus"))


def mode_equipe():
    return ou3(eq(V("mode"), 2), eq(V("mode"), 3), eq(V("mode"), 4))


def tr(fr, en):
    return C.tr(fr, en)


# ---------------------------------------------------------------------------
#  Construction du sprite
# ---------------------------------------------------------------------------
def construire(P):
    H = Cible(P, "HUD")
    H.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    H.visible = False
    H.layer = C.CALQUES["HUD"]
    texte.installer(H)                  # glyphes d'abord : la recherche de costume par nom est plus courte
    for nom, svg_txt in _icones():
        H.costumes.append(P.costume(nom, svg_txt, ICONE // 2, ICONE // 2))
        _TAILLES[nom] = ICONE
    for nom, svg_txt, cx, cy in FONDS:
        H.costumes.append(P.costume(nom, svg_txt, cx, cy))

    P.stage.var("hud_glyphes", 0)
    H.liste("hud_jt", [""] * 6)      # journal : texte source par ligne
    H.liste("hud_jw", [""] * 6)      # journal : texte tronqué correspondant
    for v in ["s", "k", "i", "n", "m", "x", "y", "w", "h", "p", "a", "rel", "dist", "dx", "dy", "x1", "x2", "yb", "hw",
              "t", "e", "c", "lig", "rows", "fin", "rest", "mmss", "txt", "cMin", "q", "reserve",
              "angleDeg", "degatsFin", "sousTitre", "sousTitreFin", "fpsN", "fpsT", "dernierDessin",
              "tVie", "tBouclier", "tSur", "tEndu", "tEquipe", "tEnnemi", "cEquipe", "cEnnemi", "cVie", "teinteZone", "yTop"]:
        H.var(v, 0)

    s = V("s")
    chr_ = chrono()

    # --- enveloppes du moteur de texte : taille × s et comptage des glyphes --------------------
    H.proc("txt", [("texte", "s"), ("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("al", "n")], [
        appel("ecrire", A("texte"), A("x"), A("y"), mul(A("taille"), s), A("couleur"), A("al")),
        changev("hud_glyphes", long_liste("txt_glyphes")),
    ])
    H.proc("txtt", [("texte", "s"), ("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("al", "n"), ("lmax", "n")], [
        appel("ecrire tronque", A("texte"), A("x"), A("y"), mul(A("taille"), s), A("couleur"), A("al"), A("lmax")),
        changev("hud_glyphes", long_liste("txt_glyphes")),
    ])

    H.proc("mesure", [("texte", "s"), ("taille", "n")], [
        appel("largeur texte", A("texte"), mul(A("taille"), s)),
        setv("w", V("txt_largeur")),
    ])
    H.proc("dessine", [("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("al", "n")], [
        appel("txt_dessiner", A("x"), A("y"), mul(A("taille"), s), A("couleur"), A("al")),
        changev("hud_glyphes", long_liste("txt_glyphes")),
    ])
    # tronque `texte` à `lmax` px (taille 11) avec « … » → variable e (coûteux : seulement quand une ligne change)
    H.proc("tronquer", [("texte", "s"), ("lmax", "n")], [
        setv("e", A("texte")), appel("mesure", V("e"), 11),
        si(gt(V("w"), A("lmax")), [
            setv("n", longueur(A("texte"))),
            repeter_jusqua(ou(non(gt(V("w"), A("lmax"))), lt(V("n"), 2)), [
                changev("n", -1), setv("e", ""), setv("i", 1),
                repeter(V("n"), [setv("e", join(V("e"), lettre(V("i"), A("texte")))), changev("i", 1)]),
                setv("e", join(V("e"), "…")),
                appel("mesure", V("e"), 11),
            ]),
        ]),
    ])

    # --- barre de progression : ombre, fond, remplissage (x, y, l, h déjà à l'échelle) ------------
    H.proc("barre", [("x", "n"), ("y", "n"), ("l", "n"), ("h", "n"), ("p", "n"), ("teinte", "n"), ("sat", "n"), ("lum", "n")], [
        setv("x1", add(A("x"), div(A("h"), 2))),
        setv("x2", sub(add(A("x"), A("l")), div(A("h"), 2))),
        couleur_hsbt(0, 0, 0, 45), taille_stylo(add(A("h"), 3)), ligne(V("x1"), A("y"), V("x2"), A("y")),
        couleur_hsbt(0, 0, 22, 20), taille_stylo(A("h")), ligne(V("x1"), A("y"), V("x2"), A("y")),
        setv("p", A("p")),
        si(gt(V("p"), 1), [setv("p", 1)]),
        si(gt(V("p"), 0), [
            couleur_hsbt(A("teinte"), A("sat"), A("lum"), 0),
            ligne(V("x1"), A("y"), add(V("x1"), mul(sub(V("x2"), V("x1")), V("p"))), A("y")),
        ]),
    ])

    # --- chevron pointant dans la direction `ang` (0 = haut, 90 = droite), rayon r ------------------
    H.proc("chevron", [("x", "n"), ("y", "n"), ("ang", "n"), ("r", "n"), ("ep", "n")], [
        taille_stylo(A("ep")),
        ligne(add(A("x"), mul(mul(A("r"), 0.74), sin(sub(A("ang"), 20)))), add(A("y"), mul(mul(A("r"), 0.74), cos(sub(A("ang"), 20)))),
              add(A("x"), mul(A("r"), sin(A("ang")))), add(A("y"), mul(A("r"), cos(A("ang"))))),
        ligne(add(A("x"), mul(A("r"), sin(A("ang")))), add(A("y"), mul(A("r"), cos(A("ang")))),
              add(A("x"), mul(mul(A("r"), 0.74), sin(add(A("ang"), 20)))), add(A("y"), mul(mul(A("r"), 0.74), cos(add(A("ang"), 20))))),
    ])

    # --- angle relatif vers (x, y) : rel ∈ [-180, 180] (positif = à gauche), dist ------------------
    H.proc("angle relatif", [("x", "n"), ("y", "n")], [
        setv("dx", sub(A("x"), V("px"))), setv("dy", sub(A("y"), V("py"))),
        si(lt(absv(V("dx")), 0.0001), [
            si(gt(V("dy"), 0), [setv("a", 90)], [setv("a", 270)]),
        ], [
            setv("a", atan(div(V("dy"), V("dx")))),
            si(lt(V("dx"), 0), [changev("a", 180)]),
        ]),
        setv("rel", sub(mod(add(sub(V("a"), V("dir")), 180), 360), 180)),
        setv("dist", sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
    ])

    # --- mm:ss ---------------------------------------------------------------------------------
    H.proc("mmss", [("n", "n")], [
        setv("n", rnd(A("n"))),
        si(lt(V("n"), 0), [setv("n", 0)]),
        si(gt(V("n"), 5999), [setv("n", 5999)]),
        setv("mmss", join(C.rembourrer(floor(div(V("n"), 60)), 2), join(":", C.rembourrer(mod(V("n"), 60), 2)))),
    ])

    # --- palette (daltonisme) ---------------------------------------------------------------------
    H.proc("palette", [], [
        setv("tVie", 33), setv("tBouclier", 62), setv("tSur", 50), setv("tEndu", 15), setv("tEquipe", 36), setv("tEnnemi", 0),
        setv("cEquipe", "vert"), setv("cEnnemi", "rouge"), setv("teinteZone", 78),
        si(ou(eq(V("param_daltonisme"), 1), eq(V("param_daltonisme"), 2)), [
            setv("tVie", 48), setv("tBouclier", 70), setv("tSur", 56), setv("tEndu", 12), setv("tEquipe", 66), setv("tEnnemi", 9),
            setv("cEquipe", "bleu"), setv("cEnnemi", "orange"), setv("teinteZone", 52),
        ]),
        si(eq(V("param_daltonisme"), 3), [
            setv("tBouclier", 88), setv("tSur", 93), setv("tEquipe", 33), setv("tEnnemi", 0), setv("teinteZone", 12),
            setv("cEquipe", "vert"), setv("cEnnemi", "rouge"),
        ]),
        setv("cVie", "blanc"),
        si(lt(V("❤ PV"), 30), [setv("cVie", "rouge")]),
    ])

    # =============================================================================================
    #  Bas gauche : vie / bouclier / surbouclier / endurance  (ancre (-235, -178))
    # =============================================================================================
    H.proc("etat vital", [], [
        # vie
        O(T("❤", ax(-235, 4), ay(-178, 9), 13, "rouge", 0),
          T(rnd(V("❤ PV")), ax(-235, 20), ay(-178, 8), 15, V("cVie"), 0)),
        barre(ax(-235, 58), ay(-178, 13), sc(93), sc(10), div(V("❤ PV"), 100), V("tVie"), 85, 85),
        # bouclier
        icone("hud_bouclier", ax(-235, 10), ay(-178, 30), 13),
        O(T(rnd(V("🛡 Bouclier")), ax(-235, 20), ay(-178, 25), 15, "blanc", 0)),
        barre(ax(-235, 58), ay(-178, 30), sc(93), sc(10), div(V("🛡 Bouclier"), 100), V("tBouclier"), 80, 95),
        # surbouclier (fine, cyan) si > 0
        si(gt(V("surbouclier"), 0), [
            O(T(join("+", rnd(V("surbouclier"))), ax(-235, 20), ay(-178, 39), 11, "cyan", 0)),
            barre(ax(-235, 58), ay(-178, 42), sc(93), sc(4), div(V("surbouclier"), 50), V("tSur"), 70, 100),
        ]),
        # endurance (fine, jaune) si < 100
        si(lt(V("endurance"), 100), [
            barre(ax(-235, 58), ay(-178, 50), sc(93), sc(4), div(V("endurance"), 100), V("tEndu"), 90, 100),
        ]),
    ])

    # =============================================================================================
    #  Barre d'inventaire : 5 cases de 32 px, pas 36 px  (ancre (-70, -178))
    # =============================================================================================
    H.proc("inventaire", [], [
        # pioche à gauche de la barre, surlignée si équipée
        si(eq(V("armeNum"), 8), [
            couleur_hsbt(15, 90, 100, 20), taille_stylo(sc(22)), ligne(ax(-70, -11), ay(-178, 24), ax(-70, -11), ay(-178, 24)),
        ]),
        icone("hud_obj8", ax(-70, -11), ay(-178, 24), 17),
        setv("k", 1),
        repeter(5, [
            setv("x", add(ax(-70, 18), mul(mul(sub(V("k"), 1), 36), s))),
            setv("y", ay(-178, 24)),
            si(eq(V("slotActif"), V("k")), [costume("hud_case_active")], [costume("hud_case")]),
            taille(mul(100, s)), aller(V("x"), V("y")), tampon(),
            si(gt(item("Inventaire", V("k")), 0), [
                costume(join("hud_obj", item("Inventaire", V("k")))), taille(mul(68, s)),
                aller(add(V("x"), sc(1)), add(V("y"), sc(2))), tampon(),
                T(item("Quantites", V("k")), add(V("x"), sc(14)), sub(V("y"), sc(14)), 11, "blanc", 2),
            ]),
            T(V("k"), sub(V("x"), sc(13)), add(V("y"), sc(6)), 11, "gris", 0),
            changev("k", 1),
        ]),
    ])

    # =============================================================================================
    #  Munitions (ancre bas droite (235, -122)) et matériaux (ancre (235, -70))
    # =============================================================================================
    H.proc("munitions", [], [
        si(et(gt(V("armeNum"), 0), lt(V("armeNum"), 4)), [
            si(eq(V("armeNum"), 1), [setv("reserve", V("munitions_legeres"))]),
            si(eq(V("armeNum"), 2), [setv("reserve", V("munitions_cartouches"))]),
            si(eq(V("armeNum"), 3), [setv("reserve", V("munitions_lourdes"))]),
            si(eq(V("ltm"), 4), [setv("txt", join(item("Quantites", V("slotActif")), " | "))],
               [setv("txt", join(item("Quantites", V("slotActif")), join(" | ", V("reserve"))))]),
            M(V("txt"), 16),
            fond(sub(ax(235, -4), add(V("w"), sc(26))), ay(-122, 42), ax(235, -4), sc(19)),
            D(ax(235, -4), ay(-122, 37), 16, "blanc", 2),
            si(eq(V("ltm"), 4), [icone("hud_infini", ax(235, -11), ay(-122, 42), 14)]),
            costume(join("hud_mun", V("armeNum"))), taille(mul(50, s)),
            aller(sub(ax(235, -4), add(V("w"), sc(14))), ay(-122, 42)), tampon(),
            # libellé : nom de l'arme, ou rechargement avec barre
            si(gt(V("rechargeFin"), 0), [
                O(T(tr("RECHARGEMENT", "RELOADING"), ax(235, -4), ay(-122, 22), 11, "orange", 2)),
                barre(ax(235, -82), ay(-122, 10), sc(78), sc(4),
                      div(sub(chr_, V("rechargeDebut")), maximum(sub(V("rechargeFin"), V("rechargeDebut")), 0.1)), 9, 90, 100),
            ], [
                O(T(item("ObjetNoms", V("armeNum")), ax(235, -4), ay(-122, 22), 11, "gris", 2)),
            ]),
        ], [
            si(et(gt(V("armeNum"), 3), lt(V("armeNum"), 8)), [
                setv("txt", join("×", item("Quantites", V("slotActif")))),
                O(T(V("txt"), ax(235, -4), ay(-122, 37), 16, "blanc", 2),
                  T(item("ObjetNoms", V("armeNum")), ax(235, -4), ay(-122, 22), 11, "gris", 2)),
            ], [
                si(eq(V("armeNum"), 8), O(T(tr("Pioche", "Pickaxe"), ax(235, -4), ay(-122, 22), 11, "gris", 2)),
                   O(T(tr("Mains nues", "Unarmed"), ax(235, -4), ay(-122, 22), 11, "gris", 2))),
            ]),
        ]),
    ])

    def rangee_materiau(m, var, dy):
        y = ay(-70, dy)
        return [
            si(eq(V("materiauActif"), m), [
                couleur_hsbt(15, 85, 100, 0), taille_stylo(sc(17)), ligne(ax(235, -73), y, ax(235, -11), y),
                couleur_hsbt(0, 0, 10, 10), taille_stylo(sc(14)), ligne(ax(235, -73), y, ax(235, -11), y),
            ], [
                couleur_hsbt(0, 0, 8, 42), taille_stylo(sc(14)), ligne(ax(235, -73), y, ax(235, -11), y),
            ]),
            icone("hud_mat%d" % m, ax(235, -71), y, 13),
            T(V(var), ax(235, -6), sub(y, sc(4)), 12, "blanc", 2),
        ]

    H.proc("materiaux", [], [
        si(eq(V("modeConstruction"), 1), [
            O(T(join(tr("CONSTRUCTION  -", "BUILD  -"), C.COUT_MUR), ax(235, -4), ay(-70, 51), 11, "jaune", 2)),
        ], [
            icone("hud_brique", ax(235, -40), ay(-70, 55), 12),
            O(T(V("🧱 Matériaux"), ax(235, -4), ay(-70, 51), 11, "gris", 2)),
        ]),
        rangee_materiau(1, "mat_bois", 38),
        rangee_materiau(2, "mat_pierre", 22),
        rangee_materiau(3, "mat_metal", 6),
    ])

    # =============================================================================================
    #  Sous la minicarte : joueurs restants, éliminations, équipes  (ancre (235, 40))
    # =============================================================================================
    H.proc("compteurs", [], [
        fond(ax(235, -82), ay(40, 17), ax(235, -10), sc(18)),
        icone("hud_joueurs", ax(235, -80), ay(40, 17), 13),
        T(V("vivants"), ax(235, -70), ay(40, 12), 14, "blanc", 0),
        icone("hud_crane", ax(235, -44), ay(40, 17), 13),
        T(V("💀 Éliminations"), ax(235, -34), ay(40, 12), 14, "blanc", 0),
        si(mode_equipe(), [
            O(T(join(V("equipesVivantes"), tr(" équipes", " teams")), ax(235, -6), ay(40, -1), 11, "gris", 2)),
        ]),
    ])

    # =============================================================================================
    #  Boussole (centre haut) : bande 240 × 24, 2 px par degré
    # =============================================================================================
    def point_boussole(teinte, taille_pt):
        return [
            setv("x", mul(V("rel"), -2)),
            si(gt(V("x"), 98), [setv("x", 98)]), si(lt(V("x"), -98), [setv("x", -98)]),
            couleur_hsbt(teinte, 90, 100, 0), taille_stylo(sc(taille_pt)),
            ligne(V("x"), add(V("yb"), sc(9)), V("x"), add(V("yb"), sc(9))),
        ]

    # la bande garde 240 px de large (2 px par degré) quelle que soit l'échelle : elle ne doit pas mordre
    # sur la minicarte (x ≥ 136) ; seules les épaisseurs et les lettres sont mises à l'échelle
    H.proc("boussole", [], [
        setv("yb", ay(176, -12)), setv("hw", 104),
        fond(add(mul(V("hw"), -1), sc(12)), V("yb"), sub(V("hw"), sc(12)), sc(24), 6, 38),
        # repère central (sous les lettres)
        couleur_hsbt(0, 0, 100, 20), taille_stylo(sc(1.5)),
        ligne(0, sub(V("yb"), sc(12)), 0, add(V("yb"), sc(12))),
        setv("a", mul(plafond(div(sub(V("dir"), 60), 15)), 15)),
        repeter(9, [
            setv("rel", sub(V("a"), V("dir"))),
            si(lt(absv(V("rel")), 48.5), [
                setv("x", mul(V("rel"), -2)),
                setv("m", mod(V("a"), 360)),
                si(eq(mod(V("m"), 90), 0), [
                    couleur_hsbt(0, 0, 100, 0), taille_stylo(sc(2)),
                    ligne(V("x"), sub(V("yb"), sc(11)), V("x"), sub(V("yb"), sc(6))),
                    si(eq(V("m"), 0), [T("E", V("x"), sub(V("yb"), sc(5)), 12, "blanc", 1)]),
                    si(eq(V("m"), 90), [T("N", V("x"), sub(V("yb"), sc(5)), 12, "jaune", 1)]),
                    si(eq(V("m"), 180), [T(tr("O", "W"), V("x"), sub(V("yb"), sc(5)), 12, "blanc", 1)]),
                    si(eq(V("m"), 270), [T("S", V("x"), sub(V("yb"), sc(5)), 12, "blanc", 1)]),
                ], [
                    couleur_hsbt(0, 0, 85, 15), taille_stylo(sc(1.5)),
                    si(eq(mod(V("m"), 45), 0),
                       ligne(V("x"), sub(V("yb"), sc(11)), V("x"), sub(V("yb"), sc(6))),
                       ligne(V("x"), sub(V("yb"), sc(11)), V("x"), sub(V("yb"), sc(8)))),
                ]),
            ]),
            changev("a", 15),
        ]),
        # centre de la zone
        si(ge(V("phase"), 2), [
            appel("angle relatif", V("zoneX"), V("zoneY")),
            point_boussole(V("teinteZone"), 7),
        ]),
        # pings (k xxxx yyyy eeeeee)
        setv("k", 1),
        repeter(long_liste("Pings"), [
            setv("e", item("Pings", V("k"))),
            si(gt(C.sous_chaine(V("e"), 10, 6), mul(chr_, 10)), [
                appel("angle relatif", div(C.sous_chaine(V("e"), 2, 4), 100), div(C.sous_chaine(V("e"), 6, 4), 100)),
                point_boussole(15, 5),
            ]),
            changev("k", 1),
        ]),
        # coéquipiers
        si(gt(V("monEquipe"), 0), [
            setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et4(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_equipe", V("k")), V("monEquipe")),
                       ou(eq(item("E_etat", V("k")), 1), eq(item("E_etat", V("k")), 3))), [
                    appel("angle relatif", item("E_x", V("k")), item("E_y", V("k"))),
                    point_boussole(V("tEquipe"), 5),
                ]),
                changev("k", 1),
            ]),
        ]),
    ])

    # =============================================================================================
    #  Minuteur de tempête + temps de partie (sous la boussole, y ≈ 136)
    # =============================================================================================
    H.proc("texte minuteur", [], [
        setv("cMin", "blanc"),
        si(ou(eq(V("ecran"), "prepartie"), eq(V("phase"), 0)), [
            setv("txt", joins(tr("Décollage dans ", "Takeoff in "), rnd(V("tempsPhase")), " s")), setv("cMin", "jaune"),
        ], [
            si(eq(V("phase"), 1), [
                setv("txt", tr("Largage en cours", "Drop in progress")), setv("cMin", "cyan"),
            ], [
                si(ge(V("phase"), 8), [
                    setv("txt", tr("Partie terminée", "Match over")), setv("cMin", "gris"),
                ], [
                    si(eq(V("zoneEnMouvement"), 1), [
                        appel("mmss", V("tempsPhase")),
                        setv("txt", join(tr("Zone en mouvement   ", "Zone moving   "), V("mmss"))), setv("cMin", "violet"),
                    ], [
                        si(gt(V("tempsAvantZone"), 0), [
                            appel("mmss", V("tempsAvantZone")),
                            setv("txt", join(tr("Zone se referme dans   ", "Zone closes in   "), V("mmss"))),
                        ], [
                            appel("mmss", V("tempsPhase")),
                            setv("txt", join(tr("La zone se referme !   ", "The zone is closing!   "), V("mmss"))), setv("cMin", "orange"),
                        ]),
                    ]),
                ]),
            ]),
        ]),
    ])

    H.proc("minuteur", [], [
        appel("texte minuteur"),
        M(V("txt"), 12),
        setv("y", ay(176, -42)),
        fond(sub(mul(V("w"), -0.5), sc(18)), V("y"), add(mul(V("w"), 0.5), sc(8)), sc(18)),
        si(ge(V("phase"), 2), [
            si(eq(V("horsZone"), 1), [icone("hud_zone_rouge", sub(mul(V("w"), -0.5), sc(8)), V("y"), 13)],
               [icone("hud_zone", sub(mul(V("w"), -0.5), sc(8)), V("y"), 13)]),
        ], [
            icone("hud_horloge", sub(mul(V("w"), -0.5), sc(8)), V("y"), 12),
        ]),
        D(sc(4), sub(V("y"), sc(4)), 12, V("cMin"), 1),
        # temps de partie : petit, à droite de la bande de boussole (x ∈ [110, 148] reste hors de la minicarte)
        si(gt(V("tempsPartie"), 0), [
            appel("mmss", V("tempsPartie")),
            fond(sub(146, sc(34)), ay(176, -12), sub(146, sc(4)), sc(15), 6, 40),
            T(V("mmss"), sub(146, sc(7)), ay(176, -16), 11, "gris", 2),
        ]),
    ])

    # =============================================================================================
    #  Haut gauche : panneau d'équipe puis journal d'éliminations  (ancre (-235, 176))
    # =============================================================================================
    H.proc("equipe", [], [
        setv("lig", 0),
        si(gt(V("monEquipe"), 0), [
            setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_equipe", V("k")), V("monEquipe"))), [
                    setv("y", sub(ay(176, -15), mul(mul(V("lig"), 26), s))),
                    costume("hud_rangee"), taille(mul(100, s)), aller(ax(-235, 65), V("y")), tampon(),
                    TT(item("E_nom", V("k")), ax(-235, 7), sub(V("y"), sc(4)), 11, V("cEquipe"), 0, 54),
                    si(eq(item("E_etat", V("k")), 3), [
                        T(tr("À TERRE", "KNOCKED"), ax(-235, 123), sub(V("y"), sc(4)), 11, "orange", 2),
                    ], [
                        si(eq(item("E_etat", V("k")), 2), [
                            T(tr("MORT", "DEAD"), ax(-235, 123), sub(V("y"), sc(4)), 11, "rouge", 2),
                            si(contient("CartesRamassees", V("k")), [icone("hud_carte", ax(-235, 76), V("y"), 14)]),
                        ], [
                            si(gt(item("E_altitude", V("k")), 0), [
                                T(tr("EN L'AIR", "AIRBORNE"), ax(-235, 123), sub(V("y"), sc(4)), 11, "cyan", 2),
                            ], [
                                barre(ax(-235, 64), add(V("y"), sc(3)), sc(58), sc(5), div(item("E_pv", V("k")), 100), V("tVie"), 85, 85),
                                barre(ax(-235, 64), sub(V("y"), sc(4)), sc(58), sc(5), div(item("E_bouclier", V("k")), 100), V("tBouclier"), 80, 95),
                            ]),
                        ]),
                    ]),
                    changev("lig", 1),
                ]),
                changev("k", 1),
            ]),
        ]),
        setv("rows", V("lig")),
    ])

    H.proc("journal", [], [
        setv("y", sub(176, mul(add(mul(V("rows"), 26), 14), s))),
        setv("k", sub(long_liste("Journal"), 4)), si(lt(V("k"), 1), [setv("k", 1)]),
        repeter_jusqua(gt(V("k"), long_liste("Journal")), [
            si(gt(item("JournalFin", V("k")), chr_), [
                setv("e", item("Journal", V("k"))),
                setv("c", "blanc"),
                si(ou3(et(gt(longueur(V("monNom")), 0), contient_texte(V("e"), V("monNom"))),
                       contient_texte(V("e"), tr("Tu ", "You ")), contient_texte(V("e"), tr("t'a ", " you"))), [setv("c", "jaune")]),
                # texte tronqué mis en cache (hud_jt : source, hud_jw : tronqué) : recalculé quand la ligne change
                si(non(eq_txt(item("hud_jt", V("k")), join(V("s"), V("e")))), [
                    remplacer("hud_jt", V("k"), join(V("s"), V("e"))),
                    appel("tronquer", V("e"), 125),
                    remplacer("hud_jw", V("k"), V("e")),
                ]),
                M(item("hud_jw", V("k")), 11),
                fond(ax(-235, 6), add(V("y"), sc(4)), add(ax(-235, 6), add(V("w"), sc(4))), sc(14), 4, 45),
                D(ax(-235, 6), V("y"), 11, V("c"), 0),
                changev("y", mul(-14, s)),
            ]),
            changev("k", 1),
        ]),
    ])

    # =============================================================================================
    #  Centre : notifications, chiffres de dégâts, flèche de dégâts, bruits
    # =============================================================================================
    H.proc("notifications", [], [
        setv("n", long_liste("Notifications")),
        setv("k", sub(V("n"), 2)), si(lt(V("k"), 1), [setv("k", 1)]),
        setv("y", V("yTop")),
        repeter_jusqua(gt(V("k"), V("n")), [
            si(gt(item("NotificationsFin", V("k")), chr_), [
                M(item("Notifications", V("k")), 13),
                fond(sub(mul(V("w"), -0.5), sc(6)), add(V("y"), sc(4)), add(mul(V("w"), 0.5), sc(6)), sc(17), 5, 35),
                D(0, V("y"), 13, "blanc", 1),
                changev("y", mul(-17, s)),
            ]),
            changev("k", 1),
        ]),
    ])

    H.proc("chiffres degats", [], [
        setv("k", 1),
        repeter(long_liste("DegatsAffiches"), [
            setv("e", item("DegatsAffiches", V("k"))),
            setv("fin", div(C.sous_chaine(V("e"), 12, 6), 10)),
            si(gt(V("fin"), chr_), [
                setv("rest", sub(V("fin"), chr_)), si(gt(V("rest"), 1), [setv("rest", 1)]),
                setv("x", sub(C.sous_chaine(V("e"), 4, 4), 2000)),
                setv("y", add(sub(C.sous_chaine(V("e"), 8, 4), 2000), mul(sub(1, V("rest")), 25))),
                setv("n", mul(C.sous_chaine(V("e"), 1, 3), 1)),
                setv("c", "blanc"), si(eq(lettre(18, V("e")), 1), [setv("c", "bleu")]),
                si(lt(V("rest"), 0.3), [setv("c", "gris")]),
                setv("t", 16), si(ge(V("n"), 70), [setv("t", 20)]),
                O(T(V("n"), V("x"), V("y"), V("t"), V("c"), 1),
                  si(ge(V("n"), 70), [
                      T("!", add(V("x"), add(div(V("txt_largeur"), 2), sc(2))), V("y"), V("t"), "rouge", 0),
                  ])),
            ]),
            changev("k", 1),
        ]),
    ])

    H.proc("fleche degats", [], [
        si(gt(V("degatsFin"), chr_), [
            couleur_hsbt(0, 95, 100, mul(sub(1.2, sub(V("degatsFin"), chr_)), 60)),
            appel("chevron", 0, 0, V("angleDeg"), sc(40), sc(4)),
            couleur_hsbt(0, 95, 100, add(mul(sub(1.2, sub(V("degatsFin"), chr_)), 50), 30)),
            appel("chevron", 0, 0, V("angleDeg"), sc(48), sc(3)),
        ]),
    ])

    H.proc("bruits", [], [
        setv("k", 1),
        repeter(long_liste("Bruits"), [
            setv("e", item("Bruits", V("k"))),
            si(gt(C.sous_chaine(V("e"), 4, 6), mul(chr_, 10)), [
                setv("a", mul(C.sous_chaine(V("e"), 1, 3), 1)),
                setv("t", lettre(10, V("e"))),
                si(eq(V("t"), 1), couleur_hsbt(0, 0, 100, 15) + [taille_stylo(sc(7))], [
                    si(eq(V("t"), 3), couleur_hsbt(14, 90, 100, 20) + [taille_stylo(sc(6))],
                       couleur_hsbt(0, 0, 75, 45) + [taille_stylo(sc(4))]),
                ]),
                ligne(mul(sin(sub(V("a"), 9)), sc(60)), mul(cos(sub(V("a"), 9)), sc(60)), mul(sin(V("a")), sc(61)), mul(cos(V("a")), sc(61))),
                ligne(mul(sin(V("a")), sc(61)), mul(cos(V("a")), sc(61)), mul(sin(add(V("a"), 9)), sc(60)), mul(cos(add(V("a"), 9)), sc(60))),
            ]),
            changev("k", 1),
        ]),
    ])

    # =============================================================================================
    #  Centre : interaction, soin, à terre, mort, bandeaux haut (invulnérable / tempête), sous-titres
    # =============================================================================================
    H.proc("interaction", [], [
        si(gt(V("interactionType"), 0), [
            setv("p", div(sub(chr_, V("interactionDebut")), maximum(V("interactionDuree"), 0.1))),
            si(eq(V("interactionType"), 1), [setv("txt", tr("Ouvrir le coffre", "Open the chest"))]),
            si(eq(V("interactionType"), 2), [setv("txt", join(tr("Réanimer ", "Revive "), item("E_nom", V("interactionCible"))))]),
            si(eq(V("interactionType"), 3), [setv("txt", join(tr("Redéployer ", "Reboot "), item("E_nom", V("interactionCible"))))]),
            fond(sc(-72), ay(-40, 2), sc(72), sc(30), 5, 35),
            T(V("txt"), 0, ay(-40, 4), 12, "blanc", 1),
            barre(sc(-62), ay(-40, -7), sc(124), sc(6), V("p"), 15, 85, 100),
        ]),
        si(gt(V("utilisationFin"), 0), [
            setv("p", div(sub(chr_, V("utilisationDebut")), maximum(sub(V("utilisationFin"), V("utilisationDebut")), 0.1))),
            setv("y", ay(-62, 0)),
            si(gt(V("interactionType"), 0), [setv("y", ay(-40, 28))]),
            O(T(item("ObjetNoms", V("utilisationObjet")), 0, add(V("y"), sc(6)), 11, "vert", 1)),
            barre(sc(-50), sub(V("y"), sc(2)), sc(100), sc(5), V("p"), 33, 85, 90),
        ]),
    ])

    # bandeaux du haut (pré-partie invulnérable, tempête) : empilés sous le minuteur ; yTop = prochaine ligne libre
    H.proc("bandeaux", [], [
        setv("y", ay(176, -62)), setv("yTop", ay(100, -8)),
        si(et(eq(V("invulnerable"), 1), non(eq(V("etat"), 2))), [
            setv("txt", tr("PRÉ-PARTIE — invulnérable", "PRE-GAME — invulnerable")),
            M(V("txt"), 12),
            fond(sub(mul(V("w"), -0.5), sc(8)), add(V("y"), sc(4)), add(mul(V("w"), 0.5), sc(8)), sc(16), 5, 35),
            D(0, V("y"), 12, "jaune", 1),
            changev("y", mul(-20, s)),
            setv("yTop", sub(V("y"), sc(14))),
        ]),
        si(et(eq(V("horsZone"), 1), ou(eq(V("etat"), 1), eq(V("etat"), 3))), [
            appel("angle relatif", V("zoneX"), V("zoneY")),
            setv("txt", joins(tr("Zone à ", "Zone "), rnd(sub(V("dist"), V("zoneR"))), " m")),
            M(V("txt"), 12),
            fond(sub(mul(V("w"), -0.5), sc(28)), sub(V("y"), sc(6)), add(mul(V("w"), 0.5), sc(28)), sc(34), 5, 35),
            D(sc(-4), sub(V("y"), sc(14)), 12, "blanc", 1),
            T(joins(tr("TEMPÊTE  -", "STORM  -"), V("zoneDegats"), "/s"), 0, add(V("y"), sc(2)), 14, "rouge", 1),
            couleur_hsbt(V("teinteZone"), 70, 100, 0),
            appel("chevron", add(mul(V("w"), 0.5), sc(12)), sub(V("y"), sc(10)), mul(V("rel"), -1), sc(8), sc(2.5)),
            setv("yTop", sub(V("y"), sc(38))),
        ]),
    ])

    H.proc("etats", [], [
        # à terre
        si(eq(V("etat"), 3), [
            fond(sc(-112), 32, sc(112), sc(26), 5, 35),
            T(join(tr("À TERRE — ", "KNOCKED — "), rnd(V("pvAterre"))), 0, 27, 16, "orange", 1),
            barre(sc(-92), 14, sc(184), sc(6), div(V("pvAterre"), 100), 9, 90, 100),
            si(gt(V("reanimationProgres"), 0), [
                O(T(tr("Réanimation en cours…", "Being revived…"), 0, -4, 12, "vert", 1)),
                barre(sc(-92), -14, sc(184), sc(6), div(V("reanimationProgres"), 4.5), V("tVie"), 85, 90),
            ]),
        ]),
        # mort
        si(eq(V("etat"), 2), [
            si(eq(V("mode"), 5), [
                setv("n", plafond(sub(V("respawnT"), chr_))), si(lt(V("n"), 0), [setv("n", 0)]),
                O(T(joins(tr("Réapparition dans ", "Respawn in "), V("n"), " s"), 0, -20, 15, "blanc", 1)),
            ], [
                si(mode_equipe(), [
                    # un coéquipier me redéploie ? (il publie reanime = mon emplacement) — la progression
                    # exacte (redeploiementProgres) est locale au sprite Joueur : barre animée
                    setv("n", 0), setv("k", 1),
                    repeter(C.NB_JOUEURS, [
                        si(et3(eq(item("E_actif", V("k")), 1), eq(item("E_equipe", V("k")), V("monEquipe")),
                               eq(item("E_reanime", V("k")), V("monSlot"))), [setv("n", V("k"))]),
                        changev("k", 1),
                    ]),
                    si(gt(V("n"), 0), [
                        O(T(join(tr("Redéploiement par ", "Rebooted by "), item("E_nom", V("n"))), 0, -20, 14, "cyan", 1)),
                        barre(sc(-80), -34, sc(160), sc(6), add(0.5, mul(0.5, sin(mul(chr_, 240)))), 50, 80, 100),
                    ], [
                        O(T(tr("En attente d'un coéquipier…", "Waiting for a teammate…"), 0, -20, 14, "gris", 1)),
                    ]),
                ]),
            ]),
        ]),
        # sous-titres
        si(et(eq(V("param_sousTitres"), 1), gt(V("sousTitreFin"), chr_)), [
            M(V("sousTitre"), 12),
            fond(sub(mul(V("w"), -0.5), sc(6)), ay(-105, 4), add(mul(V("w"), 0.5), sc(6)), sc(16), 3, 25),
            D(0, ay(-105, 0), 12, "blanc", 1),
        ]),
    ])

    # =============================================================================================
    #  Options : FPS / ping, infos réseau
    # =============================================================================================
    H.proc("options", [], [
        si(ou(eq(V("param_afficherFPS"), 1), eq(V("param_afficherPing"), 1)), [
            setv("txt", ""),
            si(eq(V("param_afficherFPS"), 1), [setv("txt", join(rnd(V("fps")), " FPS"))]),
            si(eq(V("param_afficherPing"), 1), [
                si(eq(V("param_afficherFPS"), 1), [setv("txt", join(V("txt"), "   "))]),
                setv("txt", joins(V("txt"), tr("Réseau ", "Net "), rnd(V("latence")), " ms")),
            ]),
            O(T(V("txt"), 0, ay(-178, 54), 11, "gris", 1)),
        ]),
        si(eq(V("param_infosReseau"), 1), [
            costume("hud_panneau"), taille(mul(100, s)), aller(ax(-235, 77), -35), tampon(),
            T(joins(tr("Empl. ", "Slot "), V("monSlot"), "  ·  ", rnd(V("latence")), " ms"),
              ax(-235, 7), -25, 11, "blanc", 0),
            T(joins("↑", V("paquetsEnvoyes"), "  ↓", V("paquetsRecus"), "  ·  ", V("👥 Joueurs"), tr(" joueurs", " players")),
              ax(-235, 7), -38, 11, "gris", 0),
            T(joins(item("ModeNoms", add(V("mode"), mul(6, V("param_langue")))), "  ·  ", tr("phase ", "phase "), V("phase"),
                    "  ·  ", V("colonnes"), tr(" col.", " col.")),
              ax(-235, 7), -51, 11, "gris", 0),
        ]),
    ])

    # =============================================================================================
    #  Spectateur : bandeau bas
    # =============================================================================================
    H.proc("bandeau spectateur", [], [
        setv("txt", joins(tr("SPECTATEUR : ", "SPECTATING: "), item("E_nom", V("spectSlot")),
                          tr("     ← →  changer de joueur     P : menu", "     ← →  switch player     P: menu"))),
        M(V("txt"), 12),
        fond(sub(mul(V("w"), -0.5), sc(14)), ay(-178, 20), add(mul(V("w"), 0.5), sc(14)), sc(24), 5, 30),
        D(0, ay(-178, 16), 12, "blanc", 1),
    ])

    # =============================================================================================
    #  Altimètre (parachute / bus) : à droite, x ≈ 225
    # =============================================================================================
    def y_alt(v):
        return add(sc(-110), mul(sc(220), div(v, 99)))

    # Partie écrit l'altitude en grand à gauche (x ≈ −200) et « Zone dans » / « En vie » centrés en x ≈ 200 :
    # la piste se colle au bord droit (x = 232), graduations 0/50/99 (+ seuil 30) à gauche sur des hauteurs
    # libres, curseur-pilule à gauche de la piste, planeur plus à gauche (x ≈ 172).
    H.proc("altimetre", [], [
        setv("hud_glyphes", 0), setv("txt_ombre", 1),
        setv("s", div(V("param_tailleHUD"), 100)),
        si(lt(V("s"), 0.6), [setv("s", 0.6)]), si(gt(V("s"), 1.6), [setv("s", 1.6)]),
        setv("x", ax(235, -3)),
        couleur_hsbt(0, 0, 0, 35), taille_stylo(sc(12)), ligne(V("x"), sc(-114), V("x"), sc(114)),
        couleur_hsbt(0, 0, 85, 0), taille_stylo(sc(5)), ligne(V("x"), sc(-110), V("x"), sc(110)),
        # graduations 0, 50, 99 (gris) et seuil du planeur 30 (cyan), étiquettes à gauche
        setv("k", 1),
        repeter(3, [
            si(eq(V("k"), 1), [setv("n", 0)]), si(eq(V("k"), 2), [setv("n", 50)]), si(eq(V("k"), 3), [setv("n", 99)]),
            couleur_hsbt(0, 0, 100, 0), taille_stylo(sc(2)),
            ligne(sub(V("x"), sc(6)), y_alt(V("n")), add(V("x"), sc(6)), y_alt(V("n"))),
            T(V("n"), sub(V("x"), sc(9)), sub(y_alt(V("n")), sc(4)), 11, "gris", 2),
            changev("k", 1),
        ]),
        couleur_hsbt(50, 80, 100, 0), taille_stylo(sc(2.5)),
        ligne(sub(V("x"), sc(8)), y_alt(30), add(V("x"), sc(8)), y_alt(30)),
        T("30", sub(V("x"), sc(10)), sub(y_alt(30), sc(4)), 11, "cyan", 2),
        # curseur : trait blanc sur la piste + pilule orange à gauche avec l'altitude
        setv("y", y_alt(V("altitude"))),
        si(lt(V("y"), sc(-110)), [setv("y", sc(-110))]), si(gt(V("y"), sc(110)), [setv("y", sc(110))]),
        couleur_hsbt(0, 0, 100, 0), taille_stylo(sc(3)), ligne(sub(V("x"), sc(7)), V("y"), add(V("x"), sc(7)), V("y")),
        couleur_hsbt(0, 0, 0, 30), taille_stylo(sc(19)), ligne(sub(V("x"), sc(27)), V("y"), sub(V("x"), sc(13)), V("y")),
        couleur_hsbt(12, 90, 100, 0), taille_stylo(sc(15)), ligne(sub(V("x"), sc(27)), V("y"), sub(V("x"), sc(13)), V("y")),
        setv("txt_ombre", 0),
        T(rnd(V("altitude")), sub(V("x"), sc(20)), sub(V("y"), sc(5)), 13, "noir", 1),
        setv("txt_ombre", 1),
        # planeur ouvert sous 30 : icône + libellé plus à gauche
        si(et(lt(V("altitude"), 30), gt(V("altitude"), 0)), [
            icone("hud_planeur", sub(V("x"), sc(60)), add(V("y"), sc(6)), 22),
            T(tr("PLANEUR", "GLIDER"), sub(V("x"), sc(60)), sub(V("y"), sc(16)), 11, "cyan", 1),
        ]),
    ])

    # =============================================================================================
    #  Assemblage
    # =============================================================================================
    SECTIONS = ["etat vital", "inventaire", "munitions", "materiaux", "compteurs", "boussole", "minuteur", "bandeaux",
                "equipe", "journal", "notifications", "chiffres degats", "fleche degats", "bruits", "interaction", "etats",
                "options", "bandeau spectateur"]
    if PROFIL:   # instrumentation (temps cumulé par section dans hud_profil, en secondes)
        H.liste("hud_profil", [0] * len(SECTIONS))
        H.var("t0", 0)

    sans = [n for n in os.environ.get("HUD_SANS", "").split(",") if n]   # mise au point : sections retirées

    def section(nom):
        if nom in sans:
            return []
        if not PROFIL:
            return appel(nom)
        i = SECTIONS.index(nom) + 1
        return [setv("t0", chr_), appel(nom), remplacer("hud_profil", i, add(item("hud_profil", i), sub(chr_, V("t0"))))]

    H.proc("dessiner hud", [], [
        setv("hud_glyphes", 0),
        setv("s", div(V("param_tailleHUD"), 100)),
        si(lt(V("s"), 0.6), [setv("s", 0.6)]), si(gt(V("s"), 1.6), [setv("s", 1.6)]),
        setv("txt_ombre", 0),          # ombre seulement hors des pilules sombres (voir O())
        appel("palette"),
        si(eq(V("ecran"), "spectateur"), [
            section("boussole"), section("minuteur"), section("bandeaux"), section("compteurs"), section("equipe"), section("journal"),
            section("notifications"), section("bandeau spectateur"),
        ], [
            section("etat vital"), section("inventaire"), section("munitions"), section("materiaux"), section("compteurs"),
            section("boussole"), section("minuteur"), section("bandeaux"), section("equipe"), section("journal"),
            section("notifications"), section("chiffres degats"), section("fleche degats"), section("bruits"),
            section("interaction"), section("etats"),
        ]),
        section("options"),
    ])

    H.script(quand_drapeau(), [
        cacher(), aller(0, 0), effacer_effets(),
        setv("fpsN", 0), setv("fpsT", chr_), setv("degatsFin", 0), setv("sousTitreFin", 0), setv("sousTitre", ""),
        setv("hud_glyphes", 0), setv("angleDeg", 0), setv("dernierDessin", -1),
        toujours([
            # Une image = une valeur de chrono (figé pendant un pas du séquenceur) : on ne dessine qu'une fois par
            # image, même si le séquenceur enchaîne plusieurs passes (mode turbo, VM sans rendu).
            si(non(eq(chr_, V("dernierDessin"))), [
                setv("dernierDessin", chr_),
                changev("fpsN", 1),
                si(gt(sub(chr_, V("fpsT")), 1), [
                    setv("fps", rnd(div(V("fpsN"), sub(chr_, V("fpsT"))))),
                    setv("fpsN", 0), setv("fpsT", chr_),
                ]),
                si(ecran_hud(), [appel("dessiner hud")], [
                    si(ecran_altimetre(), [appel("altimetre")]),
                ]),
            ]),
        ]),
    ])

    # --- événements : flèche de dégâts, sous-titres ----------------------------------------------
    def sous_titre(txt):
        return [si(eq(V("param_sousTitres"), 1), [setv("sousTitre", txt), setv("sousTitreFin", add(chr_, 1.5))])]

    H.script(quand_message("evt degats"), [
        si(ge(V("evt_angle"), 0), [setv("angleDeg", V("evt_angle")), setv("degatsFin", add(chr_, 1.2))]),
    ] + sous_titre(tr("[Dégâts]", "[Damage]")))
    H.script(quand_message("evt tir"), sous_titre(tr("[Coup de feu]", "[Gunshot]")))
    H.script(quand_message("evt coffre"), sous_titre(tr("[Coffre]", "[Chest]")))
    H.script(quand_message("evt phase"), sous_titre(tr("[Annonce]", "[Announcement]")))
    H.script(quand_message("evt elimination"), sous_titre(tr("[Élimination]", "[Elimination]")))
    return H
