# -*- coding: utf-8 -*-
"""
BANQUE D'ICÔNES ET D'ILLUSTRATIONS SVG de l'interface de Royale 3D.

Style Fortnite : formes nettes, contours sombres 2–3 px, couleurs vives, pas de texte
dans les icônes (sauf la carte complète et le logo). Chaque fonction renvoie une chaîne
SVG complète (racine <svg> avec viewBox, via royale.svg.svg) ; tout est déterministe
et rapide (pas d'aléatoire, pas de fichier).

API (tailles en px) :
  icone_objet(code) 48×48            contrat.OBJETS 1..11 (6 armes, 4 consommables, pioche)
  largage() 60×90  largage_pose() 60×34  lama_3d() 60×70   panneaux 3D de mod_largages (largage, largage posé, lama)
  icone_munitions(type) 32×32        "legeres" | "cartouches" | "lourdes"
  icone_materiau(code) 32×32         1 bois, 2 pierre, 3 métal
  personnage(skin, pose, style=0)    skin 1..10 (NOMS_SKINS), pose "debout" 60×100 | "aterre" 100×60 |
                                     "emote" 60×100 | "parachute" 80×120 ; style 1 = variante de couleur
  pioche(n) 48×48 (1..9)             planeur(n) 64×48 (1..9)       spray(n) 64×64 (contrat.SPRAYS)
  emote(n) 48×48 (contrat.EMOTES)    banniere(n) 40×40 (1..10)      division(n) 48×48 (1..7)
  medaille(rang) 48×48 (1..3)
  bus() 64×40  parachute_icone() 32×32  planeur_icone() 32×32  marqueur(couleur) 24×36
  carte_redeploiement() 32×40  balise() 40×60  coffre_ouvert() 60×50  boussole_curseur() 16×16
  jeton() etoile() cadenas() coche() croix() 24×24   fleche(direction) 24×24 (haut/bas/gauche/droite)
  icone_onglet(nom) 32×32 (contrat.ONGLETS)   icone_quete(type) 32×32 (quotidienne/hebdomadaire/histoire)
  icone_succes() 32×32   icone_ami(etat) 24×24 (enligne/enpartie/horsligne)   icone_haut_parleur(n) 24×24 (0..3)
  icone_oeil() icone_signaler() icone_zone() icone_bruit() 24×24   fleche_degats() 48×48
  cercle_interaction(pourcent) 64×64   barre(w, h, couleur, pourcent)   bouton(w, h, survol=False, couleur=…)
  panneau(w, h)   onglet_fond(actif) 120×40
  carte_complete(echelle=10) 320×320   carte_minimap(echelle=3.4) 109×109
  bus_carte() 30×18  parachute_carte() 14×16  coffre_carte() 8×8   (icônes de la carte plein écran)
  fond_ecran(variante) 480×360 (connexion/salon/matchmaking/chargement/victoire/defaite/fin/tempete/ciel)
  logo() 300×80

Arguments : les codes numériques acceptent int, float ou chaîne de chiffres ; une valeur hors
domaine (ou non numérique) lève KeyError. Les pourcentages sont bornés 0..100 (non numérique = 0),
les tailles w, h ont un minimum (8 px) pour ne jamais produire de dimension négative.

Centres de rotation conseillés : le centre du costume (w/2, h/2), sauf marqueur (12, 36 : la
pointe), fleche_degats (24, 24 : à faire tourner par le sprite) et personnage "debout"/"emote"
(30, 50) / "aterre" (50, 30) / "parachute" (40, 60).

Remarque sur le moteur SVG de Scratch (scratch-svg-renderer) : les attributs fill / stroke /
stroke-width / transform posés sur un <g> sont poussés sur les feuilles au chargement, et les
<path> transformés voient leur géométrie recalculée. On n'utilise donc ni dégradé sur un chemin
transformé, ni héritage d'attributs à l'intérieur d'un <mask>/<clipPath>.
"""
import math

from .svg import svg, echapper
from . import contrat as C

# ---------------------------------------------------------------------------
#  Palette
# ---------------------------------------------------------------------------
CONTOUR = "#151b2b"        # contour sombre standard
BLANC = "#f8fafc"
NOIR = "#111827"
JAUNE = "#fde047"
OR = "#f59e0b"
OR_FONCE = "#b45309"
ORANGE = "#fb923c"
ROUGE = "#ef4444"
ROUGE_FONCE = "#991b1b"
VERT = "#22c55e"
VERT_FONCE = "#15803d"
CYAN = "#22d3ee"
BLEU = "#3b82f6"
BLEU_FONCE = "#1d4ed8"
VIOLET = "#a855f7"
VIOLET_FONCE = "#6b21a8"
ROSE = "#ec4899"
GRIS = "#94a3b8"
GRIS_CLAIR = "#cbd5e1"
GRIS_FONCE = "#475569"
ARDOISE = "#1e293b"
PEAU = "#f1c27d"
BOIS = "#a16207"
BOIS_CLAIR = "#d4a054"
METAL = "#64748b"
METAL_CLAIR = "#94a3b8"

# Couleurs des matériaux de la carte (valeur de case -> remplissage, contour)
COULEURS_CASES = {1: ("#8d939c", "#4b5563"), 2: ("#a0622d", "#5b3a1a"), 3: ("#b4432f", "#6b1f14"), 4: ("#6b7f99", "#2f3f54")}

# Numéros et noms identiques à ceux du catalogue de mod_systemes (sys_SkinNoms, sys_PiocheNoms, sys_PlaneurNoms,
# sys_BanniereNoms) pour que le casier, la boutique et le passe affichent la bonne icône sous le bon nom.
NOMS_SKINS = ["Recrue", "Ranger", "Ombre", "Néon", "Chevalier", "Pirate", "Astronaute", "Ninja", "Robot", "Légende"]
NOMS_PIOCHES = ["Pioche de base", "Hache", "Marteau", "Faux", "Clé géante", "Katana", "Guitare", "Pelle dorée", "Sceptre"]
NOMS_PLANEURS = ["Parapluie", "Deltaplane", "Dragon", "Fusée", "Ballon", "Parachute militaire", "Aile de chauve-souris",
                 "Tapis volant", "OVNI"]
NOMS_BANNIERES = ["Étoile", "Lama", "Éclair", "Crâne", "Cœur", "Flamme", "Couronne", "Bouclier", "Diamant", "Trophée"]
NOMS_DIVISIONS = ["Bronze", "Argent", "Or", "Platine", "Diamant", "Champion", "Irréel"]
POSES = {"debout": (60, 100), "aterre": (100, 60), "emote": (60, 100), "parachute": (80, 120)}


# ---------------------------------------------------------------------------
#  Petits outils de dessin
# ---------------------------------------------------------------------------
def _n(v):
    """Nombre → texte SVG compact (entier si possible, sinon 2 décimales)."""
    if isinstance(v, bool):
        return str(v).lower()
    if isinstance(v, float):
        if abs(v - round(v)) < 1e-9:
            return str(int(round(v)))
        return ("%.2f" % v).rstrip("0").rstrip(".")
    return str(v)


def _attr(**kw):
    """Attributs supplémentaires : fill_opacity=0.5 → fill-opacity="0.5" (None = omis)."""
    s = ""
    for k, v in kw.items():
        if v is None:
            continue
        s += ' %s="%s"' % (k.replace("_", "-"), _n(v) if isinstance(v, (int, float)) else v)
    return s


def _trait(stroke, sw):
    if not stroke:
        return ' stroke="none"'
    return ' stroke="%s" stroke-width="%s" stroke-linejoin="round" stroke-linecap="round"' % (stroke, _n(sw))


def _rect(x, y, w, h, fill, rx=0, stroke=CONTOUR, sw=2, **kw):
    return '<rect x="%s" y="%s" width="%s" height="%s"%s fill="%s"%s%s/>' % (
        _n(x), _n(y), _n(w), _n(h), (' rx="%s"' % _n(rx)) if rx else "", fill, _trait(stroke, sw), _attr(**kw))


def _cercle(cx, cy, r, fill, stroke=CONTOUR, sw=2, **kw):
    return '<circle cx="%s" cy="%s" r="%s" fill="%s"%s%s/>' % (_n(cx), _n(cy), _n(r), fill, _trait(stroke, sw), _attr(**kw))


def _ellipse(cx, cy, rx, ry, fill, stroke=CONTOUR, sw=2, **kw):
    return '<ellipse cx="%s" cy="%s" rx="%s" ry="%s" fill="%s"%s%s/>' % (
        _n(cx), _n(cy), _n(rx), _n(ry), fill, _trait(stroke, sw), _attr(**kw))


def _chemin(d, fill, stroke=CONTOUR, sw=2, **kw):
    return '<path d="%s" fill="%s"%s%s/>' % (d, fill, _trait(stroke, sw), _attr(**kw))


def _pts(points):
    return " ".join("%s,%s" % (_n(x), _n(y)) for x, y in points)


def _poly(points, fill, stroke=CONTOUR, sw=2, **kw):
    return '<polygon points="%s" fill="%s"%s%s/>' % (_pts(points), fill, _trait(stroke, sw), _attr(**kw))


def _ligne(x1, y1, x2, y2, stroke=CONTOUR, sw=2, **kw):
    return '<line x1="%s" y1="%s" x2="%s" y2="%s"%s%s/>' % (_n(x1), _n(y1), _n(x2), _n(y2), _trait(stroke, sw), _attr(**kw))


def _trait_double(x1, y1, x2, y2, couleur, sw, contour=CONTOUR, marge=3):
    """Segment épais à bouts ronds, cerné d'un contour (bras, manches, jambes)."""
    return _ligne(x1, y1, x2, y2, contour, sw + marge) + _ligne(x1, y1, x2, y2, couleur, sw)


def _groupe(contenu, **kw):
    return "<g%s>%s</g>" % (_attr(**kw), contenu)


def _texte(x, y, t, taille, fill, ancre="middle", gras=True, contour=None, sw=0, italique=False, **kw):
    s = '<text x="%s" y="%s" font-family="Sans Serif" font-size="%s" text-anchor="%s" fill="%s"' % (
        _n(x), _n(y), _n(taille), ancre, fill)
    if gras:
        s += ' font-weight="bold"'
    if italique:
        s += ' font-style="italic"'
    if contour:
        s += ' stroke="%s" stroke-width="%s" stroke-linejoin="round" paint-order="stroke"' % (contour, _n(sw))
    return s + _attr(**kw) + ">" + echapper(t) + "</text>"


def _degrade(ident, arrets, x1=0, y1=0, x2=0, y2=1):
    """Dégradé linéaire ; arrets = [(position 0..1, couleur), ...] ou [couleur1, couleur2]."""
    if arrets and isinstance(arrets[0], str):
        arrets = [(i / float(len(arrets) - 1), c) for i, c in enumerate(arrets)]
    stops = "".join('<stop offset="%s" stop-color="%s"/>' % (_n(p), c) for p, c in arrets)
    return '<linearGradient id="%s" x1="%s" y1="%s" x2="%s" y2="%s">%s</linearGradient>' % (
        ident, _n(x1), _n(y1), _n(x2), _n(y2), stops)


def _radial(ident, arrets, cx=0.5, cy=0.5, r=0.5):
    if arrets and isinstance(arrets[0], str):
        arrets = [(i / float(len(arrets) - 1), c) for i, c in enumerate(arrets)]
    stops = "".join('<stop offset="%s" stop-color="%s"%s/>' % (_n(p), c[0] if isinstance(c, tuple) else c,
                                                               (' stop-opacity="%s"' % _n(c[1])) if isinstance(c, tuple) else "")
                    for p, c in arrets)
    return '<radialGradient id="%s" cx="%s" cy="%s" r="%s">%s</radialGradient>' % (ident, _n(cx), _n(cy), _n(r), stops)


def _defs(*elements):
    return "<defs>%s</defs>" % "".join(elements)


def _etoile_pts(cx, cy, r_ext, r_int, n=5, rotation=-90):
    pts = []
    for i in range(2 * n):
        a = math.radians(rotation + i * 180.0 / n)
        r = r_ext if i % 2 == 0 else r_int
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _polygone_regulier(cx, cy, r, n, rotation=-90):
    return [(cx + r * math.cos(math.radians(rotation + i * 360.0 / n)),
             cy + r * math.sin(math.radians(rotation + i * 360.0 / n))) for i in range(n)]


def _tourner(points, angle, cx, cy):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    return [(cx + (x - cx) * ca - (y - cy) * sa, cy + (x - cx) * sa + (y - cy) * ca) for x, y in points]


def _entier(v, libelle="valeur"):
    """int(v) tolérant ("3", 3.0) ; une valeur non numérique est un argument hors domaine → KeyError."""
    try:
        return int(float(v))
    except (TypeError, ValueError):
        raise KeyError("%s hors domaine : %r" % (libelle, v))


def _nombre(v, defaut=0.0):
    """float(v), ou `defaut` si v n'est pas numérique (None, texte vide…)."""
    try:
        return float(v)
    except (TypeError, ValueError):
        return float(defaut)


def _hex_rvb(hexa):
    """"#rgb" ou "#rrggbb" → (r, v, b) ; lève ValueError pour une couleur nommée."""
    h = str(hexa).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) != 6:
        raise ValueError("couleur non hexadécimale : %r" % hexa)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _rvb_hex(r, v, b):
    return "#%02x%02x%02x" % (max(0, min(255, int(round(r)))), max(0, min(255, int(round(v)))), max(0, min(255, int(round(b)))))


def eclaircir(hexa, f=0.3):
    """Mélange une couleur #rrggbb (ou #rgb) avec du blanc (f = part de blanc 0..1) ;
    une couleur nommée ("red") est renvoyée telle quelle."""
    try:
        r, v, b = _hex_rvb(hexa)
    except ValueError:
        return hexa
    return _rvb_hex(r + (255 - r) * f, v + (255 - v) * f, b + (255 - b) * f)


def assombrir(hexa, f=0.3):
    """Mélange une couleur #rrggbb (ou #rgb) avec du noir (f = part de noir 0..1) ;
    une couleur nommée est renvoyée telle quelle."""
    try:
        r, v, b = _hex_rvb(hexa)
    except ValueError:
        return hexa
    return _rvb_hex(r * (1 - f), v * (1 - f), b * (1 - f))


def _arc(cx, cy, r, a0, a1):
    """Chemin d'arc de cercle (angles en degrés, 0 = droite, sens horaire à l'écran) sans fermeture."""
    x0, y0 = cx + r * math.cos(math.radians(a0)), cy + r * math.sin(math.radians(a0))
    x1, y1 = cx + r * math.cos(math.radians(a1)), cy + r * math.sin(math.radians(a1))
    grand = 1 if (a1 - a0) % 360 > 180 else 0
    return "M%s %s A%s %s 0 %d 1 %s %s" % (_n(x0), _n(y0), _n(r), _n(r), grand, _n(x1), _n(y1))


def _plus(cx, cy, taille, epaisseur, fill, stroke=CONTOUR, sw=1.5):
    """Croix « + » pleine (soins)."""
    t, e = taille / 2.0, epaisseur / 2.0
    d = ("M%s %s h%s v%s h%s v%s h%s v%s h%s v%s h%s v%s h%s z"
         % (_n(cx - e), _n(cy - t), _n(2 * e), _n(t - e), _n(t - e), _n(2 * e), _n(-(t - e)), _n(t - e),
            _n(-2 * e), _n(-(t - e)), _n(-(t - e)), _n(-2 * e), _n(t - e)))
    return _chemin(d, fill, stroke, sw)


def _eclat(cx, cy, r, n=4, couleur=BLANC, sw=1.5, opacite=0.9):
    """Petit éclat (étincelle en croix)."""
    s = ""
    for i in range(n):
        a = math.radians(i * 180.0 / n)
        s += _ligne(cx - r * math.cos(a), cy - r * math.sin(a), cx + r * math.cos(a), cy + r * math.sin(a), couleur, sw, opacity=opacite)
    return s


# ---------------------------------------------------------------------------
#  Objets d'inventaire (48×48)
# ---------------------------------------------------------------------------
def _pistolet():
    return (
        _rect(6, 17, 4, 7, "#27272a", 1, sw=2)                       # chien
        + _rect(8, 14, 32, 10, "#3f3f46", 2, sw=2.5)                 # culasse
        + _rect(38, 16, 6, 6, "#52525b", 1, sw=2)                    # bouche du canon
        + _rect(10, 16, 26, 2.5, "#71717a", 1, None)                 # reflet
        + _rect(10, 23, 24, 5, "#27272a", 1, sw=2)                   # carcasse
        + _poly([(14, 27), (25, 27), (22, 42), (11, 42)], "#8a5a2b", sw=2.5)   # crosse
        + _rect(16, 31, 5, 8, "#a16207", 1, None)                    # plaquette
        + _chemin("M25 28 q8 0 8 6 q0 4 -4 4 h-3", "none", CONTOUR, 2.2)       # pontet
        + _rect(26, 29, 2, 5, "#27272a", 0, None)                    # détente
    )


def _pompe():
    return (
        _poly([(2, 24), (14, 20), (14, 31), (5, 35)], "#92400e", sw=2.5)        # crosse
        + _rect(13, 19, 15, 11, "#3f3f46", 2, sw=2.5)                            # boîtier
        + _rect(27, 19, 18, 5, "#52525b", 1, sw=2.2)                             # canon
        + _rect(27, 24, 16, 3.5, "#27272a", 1, sw=1.8)                           # tube magasin
        + _rect(44, 18, 3, 7, "#27272a", 1, sw=2)                                # bouche
        + _rect(29, 27, 12, 6, "#b45309", 2, sw=2.2)                             # pompe (bois)
        + _rect(31, 29, 8, 1.5, "#d97706", 0, None)
        + _poly([(16, 30), (23, 30), (21, 38), (15, 38)], "#8a5a2b", sw=2.2)     # poignée
        + _rect(15, 21, 11, 2, "#71717a", 1, None)                               # reflet
    )


def _sniper():
    return (
        _ligne(34, 27, 30, 37, "#27272a", 2.5) + _ligne(37, 27, 41, 37, "#27272a", 2.5)   # bipied
        + _poly([(2, 23), (10, 20), (10, 31), (4, 34)], "#365314", sw=2.5)               # crosse
        + _rect(9, 20, 18, 9, "#3f6212", 2, sw=2.5)                                      # boîtier
        + _rect(26, 22, 17, 4.5, "#52525b", 1, sw=2.2)                                   # canon
        + _rect(42, 20, 5, 8, "#27272a", 1, sw=2)                                        # frein de bouche
        + _rect(15, 16, 3, 4, "#27272a", 0, sw=1.5) + _rect(22, 16, 3, 4, "#27272a", 0, sw=1.5)   # montures
        + _rect(11, 10, 17, 7, "#1f2937", 3.5, sw=2.2)                                   # lunette
        + _cercle(27, 13.5, 2.3, "#38bdf8", CONTOUR, 1.2)                                # lentille
        + _rect(17, 29, 6, 7, "#27272a", 1, sw=2)                                        # chargeur
        + _poly([(10, 29), (16, 29), (14, 37), (8, 37)], "#1f2937", sw=2.2)              # poignée
        + _rect(11, 22, 14, 2, "#84cc16", 1, None, opacity=0.8)                          # reflet
    )


def _bandages():
    return (
        _poly([(18, 15), (44, 21), (44, 31), (18, 35)], "#f8fafc", sw=2.5)                # bande déroulée
        + _ligne(26, 19, 26, 33, "#cbd5e1", 1.5) + _ligne(33, 20, 33, 32, "#cbd5e1", 1.5)
        + _plus(38, 26, 7, 2.4, ROUGE, CONTOUR, 1.2)
        + _cercle(16, 25, 11.5, "#ffffff", CONTOUR, 2.5)                                 # rouleau
        + _cercle(16, 25, 7, "none", "#cbd5e1", 2)
        + _cercle(16, 25, 2.5, "#cbd5e1", CONTOUR, 1.2)
    )


def _medikit():
    return (
        _rect(18, 6, 12, 8, "none", 2.5, CONTOUR, 2.5)                                   # poignée
        + _rect(19, 7.5, 10, 2, "#9ca3af", 1, None)
        + _rect(5, 12, 38, 30, "#f8fafc", 4, sw=2.5)                                      # mallette
        + _rect(5, 12, 38, 8, "#e2e8f0", 4, None)
        + _ligne(5, 20, 43, 20, "#94a3b8", 1.5)
        + _plus(24, 29, 18, 7, ROUGE, CONTOUR, 1.8)
        + _rect(9, 14, 4, 5, "#64748b", 1, None) + _rect(35, 14, 4, 5, "#64748b", 1, None)   # fermoirs
    )


def _minipotion():
    return (
        _defs('<clipPath id="cp"><circle cx="24" cy="30" r="13"/></clipPath>')
        + _rect(19, 7, 10, 7, "#b45309", 1.5, sw=2.2)                                     # bouchon
        + _rect(19, 13, 10, 7, "#bfdbfe", 0, None)                                       # col (verre)
        + _cercle(24, 30, 13, "#93c5fd", None)                                           # verre
        + '<rect x="9" y="27" width="30" height="18" fill="#2563eb" clip-path="url(#cp)"/>'   # liquide
        + _cercle(28, 36, 1.8, "#bfdbfe", None, opacity=0.9) + _cercle(20, 33, 1.3, "#bfdbfe", None, opacity=0.8)
        + _cercle(31, 31, 1.2, "#bfdbfe", None, opacity=0.8)
        + _ellipse(18.5, 24, 2.3, 4.5, "#ffffff", None, opacity=0.55)                    # reflet
        + _ligne(19, 13, 29, 13, CONTOUR, 2) + _ligne(19, 13, 19, 20, CONTOUR, 2.2) + _ligne(29, 13, 29, 20, CONTOUR, 2.2)
        + _cercle(24, 30, 13, "none", CONTOUR, 2.5)
    )


def _potion():
    bouteille = "M15 16 h18 q7 7 7 14 v10 q0 6 -6 6 h-20 q-6 0 -6 -6 v-10 q0 -7 7 -14 z"
    return (
        _defs('<clipPath id="cp"><path d="%s"/></clipPath>' % bouteille)
        + _rect(18, 3, 12, 7, "#b45309", 1.5, sw=2.2)                                    # bouchon
        + _rect(18, 9, 12, 8, "#93c5fd", 0, None)                                       # col
        + _chemin(bouteille, "#93c5fd", None)                                            # verre
        + '<rect x="8" y="23" width="32" height="24" fill="#1d4ed8" clip-path="url(#cp)"/>'   # liquide
        + '<rect x="8" y="23" width="32" height="3" fill="#60a5fa" clip-path="url(#cp)"/>'
        + _cercle(27, 36, 2.2, "#bfdbfe", None, opacity=0.85) + _cercle(20, 40, 1.5, "#bfdbfe", None, opacity=0.8)
        + _cercle(31, 29, 1.4, "#bfdbfe", None, opacity=0.8)
        + _poly(_etoile_pts(24, 33, 5, 2.2), "#fde047", None, opacity=0.9)              # étiquette : éclat
        + _ellipse(14, 26, 2, 6, "#ffffff", None, opacity=0.5)                           # reflet
        + _ligne(18, 9, 30, 9, CONTOUR, 2) + _ligne(18, 9, 18, 16, CONTOUR, 2.2) + _ligne(30, 9, 30, 16, CONTOUR, 2.2)
        + _chemin(bouteille, "none", CONTOUR, 2.5)
    )


def _tete_pioche(couleur, bord=CONTOUR, clair=None):
    """Tête de pioche en croissant, perpendiculaire au manche (manche de (9,41) à (33,17))."""
    s = _chemin("M20 5 Q35 8 45 25 Q39 18 33 20 Q28 12 20 5 Z", couleur, bord, 2.5)
    if clair:
        s += _chemin("M23 8 Q34 10 41 20", "none", clair, 1.5)
    return s


def _pioche_defaut():
    return _trait_double(9, 41, 33, 17, "#92400e", 5.5, CONTOUR, 4) + _tete_pioche("#94a3b8", CONTOUR, "#e2e8f0") \
        + _cercle(33, 17, 2.2, "#475569", CONTOUR, 1.2)


def _assaut():
    return (
        _poly([(2, 22), (10, 20), (10, 30), (4, 33)], "#3f3f46", sw=2.5)                   # crosse
        + _rect(9, 19, 20, 10, "#3f3f46", 2, sw=2.5)                                     # boîtier
        + _rect(28, 21, 12, 6, "#6b4f2a", 1.5, sw=2.2)                                   # garde-main (bois)
        + _rect(39, 22, 7, 4, "#52525b", 1, sw=2)                                        # canon
        + _rect(14, 13, 12, 5, "#27272a", 2, sw=2)                                       # poignée de transport / viseur
        + _poly([(17, 28), (24, 28), (23, 39), (16, 39)], "#27272a", sw=2.2)             # chargeur courbe
        + _poly([(10, 28), (15, 28), (13, 35), (8, 35)], "#1f2937", sw=2.2)              # poignée
        + _rect(11, 21, 15, 2, "#71717a", 1, None)                                       # reflet
    )


def _pm():
    return (
        _rect(4, 20, 9, 5, "#52525b", 1.5, sw=2.2)                                       # crosse repliée
        + _rect(12, 17, 22, 11, "#3f3f46", 3, sw=2.5)                                    # corps compact
        + _rect(33, 20, 10, 5, "#52525b", 1.5, sw=2.2)                                   # canon court
        + _rect(42, 19, 4, 7, "#27272a", 1, sw=2)                                        # bouche
        + _rect(20, 27, 6, 15, "#1a1a1a", 1.5, sw=2.2)                                   # long chargeur droit
        + _poly([(13, 27), (19, 27), (17, 34), (11, 34)], "#5a4632", sw=2.2)             # poignée
        + _rect(14, 19, 18, 2, "#71717a", 1, None)                                       # reflet
        + _cercle(39, 22.5, 1.5, "#111827", None)
    )


def _lance():
    return (
        _poly([(2, 22), (11, 19), (11, 32), (4, 35)], "#4a3b2a", sw=2.5)                  # crosse épaisse
        + _rect(10, 16, 30, 14, "#c2410c", 5, sw=2.5)                                    # gros tube orange
        + _rect(38, 18, 8, 10, "#7c2d12", 3, sw=2.2)                                     # bouche évasée
        + _cercle(21, 23, 6, "#9a3412", CONTOUR, 2.2)                                    # barillet
        + _cercle(21, 23, 2.2, "#111827", None)
        + _rect(17, 30, 7, 9, "#27272a", 1.5, sw=2.2)                                    # poignée
        + _rect(30, 30, 5, 7, "#27272a", 1.5, sw=2)                                      # poignée avant
        + _rect(13, 18, 22, 2, "#fb923c", 1, None, opacity=0.85)                         # reflet
    )


def icone_objet(code):
    """Icône 48×48 d'un objet d'inventaire (contrat.OBJETS 1..11 : 1 pistolet, 2 fusil à pompe, 3 sniper, 4 fusil
    d'assaut, 5 pistolet-mitrailleur, 6 lance-grenades, 7 bandages, 8 médikit, 9 mini-potion, 10 potion, 11 pioche)."""
    code = _entier(code, "objet")
    dessins = {1: _pistolet, 2: _pompe, 3: _sniper, 4: _assaut, 5: _pm, 6: _lance, 7: _bandages, 8: _medikit,
               9: _minipotion, 10: _potion, 11: _pioche_defaut}
    if code not in dessins:
        raise KeyError("objet inconnu : %r (codes %s)" % (code, sorted(dessins)))
    return svg(48, 48, dessins[code]())


def largage():
    """Largage de ravitaillement 60×90 : caisse bleue suspendue sous un ballon (panneau 3D de mod_largages)."""
    return svg(60, 90, (
        _ellipse(30, 24, 22, 20, "#60a5fa", CONTOUR, 2.5)                                # ballon
        + _ellipse(22, 17, 6, 9, "#dbeafe", None, opacity=0.55, transform="rotate(-20 22 17)")   # reflet
        + _poly([(26, 43), (34, 43), (30, 49)], "#1d4ed8", CONTOUR, 2)                   # bec du ballon
        + _ligne(14, 50, 24, 62, "#e5e7eb", 1.5) + _ligne(46, 50, 36, 62, "#e5e7eb", 1.5)   # cordes
        + _ligne(30, 49, 30, 62, "#e5e7eb", 1.5)
        + _rect(10, 60, 40, 28, "#2563eb", 4, CONTOUR, 2.5)                              # caisse
        + _rect(10, 70, 40, 7, "#fbbf24", 0, None)                                       # bande jaune
        + _rect(27, 60, 6, 28, "#1e40af", 0, None)                                       # sangle
        + _poly(_etoile_pts(20, 73.5, 3.2, 1.4), "#ffffff", None, opacity=0.9)
        + _rect(10, 60, 40, 28, "none", 4, CONTOUR, 2.5)
    ))


def largage_pose():
    """Largage posé 60×34 : la caisse seule (ballon dégonflé), même échelle que largage()."""
    return svg(60, 34, (
        _chemin("M20 2 q10 -4 20 0 q-6 4 -10 4 q-6 0 -10 -4 z", "#60a5fa", CONTOUR, 2)       # ballon dégonflé
        + _rect(10, 5, 40, 28, "#2563eb", 4, CONTOUR, 2.5)
        + _rect(10, 15, 40, 7, "#fbbf24", 0, None)
        + _rect(27, 5, 6, 28, "#1e40af", 0, None)
        + _poly(_etoile_pts(20, 18.5, 3.2, 1.4), "#ffffff", None, opacity=0.9)
        + _rect(10, 5, 40, 28, "none", 4, CONTOUR, 2.5)
    ))


def lama_3d():
    """Lama à butin 60×70 violet (panneau 3D de mod_largages) : corps piñata rayé, cou, tête et pattes."""
    s = ""
    for x in (14, 22, 34, 42):
        s += _rect(x, 50, 6, 18, "#a21caf", 2, CONTOUR, 2)                               # pattes
    s += _poly([(12, 36), (4, 30), (12, 43)], "#c026d3", CONTOUR, 2)                      # queue
    s += _rect(10, 30, 40, 22, "#d946ef", 7, CONTOUR, 2.5)                                # corps
    s += _rect(13, 35, 34, 4, "#fde047", 0, None) + _rect(13, 41, 34, 4, "#22d3ee", 0, None) + _rect(13, 46, 34, 3, "#4ade80", 0, None)
    s += _rect(40, 12, 11, 24, "#d946ef", 4, CONTOUR, 2.5)                                # cou
    s += _poly([(44, 7), (46, 1), (49, 7)], "#d946ef", CONTOUR, 2) + _poly([(52, 7), (54, 1), (57, 7)], "#d946ef", CONTOUR, 2)   # oreilles
    s += _rect(40, 5, 20, 13, "#d946ef", 4, CONTOUR, 2.5)                                 # tête
    s += _rect(52, 8, 8, 9, "#f0abfc", 3, None)                                           # museau
    s += _cercle(47, 10.5, 1.8, NOIR, None)                                                # œil
    s += _rect(42, 24, 8, 3, "#fde047", 0, None) + _rect(42, 29, 8, 3, "#22d3ee", 0, None)   # rayures du cou
    return svg(60, 70, s)


# ---------------------------------------------------------------------------
#  Munitions (32×32) et matériaux (32×32)
# ---------------------------------------------------------------------------
def _balle(x, y, w, h, corps, pointe, bord=CONTOUR):
    """Cartouche verticale : étui (rect) + ogive (demi-ellipse) ; (x, y) coin haut-gauche de l'étui."""
    return (_chemin("M%s %s v%s h%s v%s a%s %s 0 0 0 %s 0 z" % (_n(x), _n(y + h * 0.35), _n(h * 0.65), _n(w), _n(-h * 0.65),
                                                                 _n(w / 2.0), _n(h * 0.35), _n(-w)), corps, bord, 1.8)
            + _chemin("M%s %s a%s %s 0 0 1 %s 0 z" % (_n(x), _n(y + h * 0.35), _n(w / 2.0), _n(h * 0.35), _n(w)), pointe, bord, 1.8)
            + _rect(x, y + h * 0.78, w, h * 0.1, assombrir(corps, 0.35), 0, None))


def icone_munitions(type_munitions):
    """Icône 32×32 : "legeres" (petites balles), "cartouches" (cartouches rouges), "lourdes" (grosses balles)."""
    t = str(type_munitions).strip().lower()
    if t == "legeres":
        s = _balle(4, 8, 6, 20, "#d4a017", "#fbbf24") + _balle(13, 5, 6, 23, "#d4a017", "#fbbf24") + _balle(22, 8, 6, 20, "#d4a017", "#fbbf24")
    elif t == "cartouches":
        s = ""
        for x in (6, 17):
            s += (_rect(x, 4, 9, 24, "#dc2626", 2, sw=2) + _rect(x, 21, 9, 7, "#d4a017", 1.5, sw=2)
                  + _rect(x + 1.5, 6.5, 2, 12, "#fca5a5", 1, None, opacity=0.8))
    elif t == "lourdes":
        s = _balle(5, 3, 9, 26, "#b45309", "#1f2937") + _balle(18, 3, 9, 26, "#b45309", "#1f2937") \
            + _rect(6.5, 15, 2, 8, "#fbbf24", 1, None, opacity=0.6) + _rect(19.5, 15, 2, 8, "#fbbf24", 1, None, opacity=0.6)
    else:
        raise KeyError("type de munitions inconnu : %r" % type_munitions)
    return svg(32, 32, s)


def icone_materiau(code):
    """Icône 32×32 : 1 bois (bûches), 2 pierre (briques grises), 3 métal (plaques rivetées)."""
    code = _entier(code, "matériau")
    if code == 1:
        s = ""
        for cx, cy in [(10, 21), (22, 21), (16, 11)]:
            s += (_cercle(cx, cy, 7, "#c8893a", CONTOUR, 2.2) + _cercle(cx, cy, 4.3, "#e8b06a", "#8a5a2b", 1.5)
                  + _cercle(cx, cy, 1.6, "#8a5a2b", None))
    elif code == 2:
        s = _rect(2, 4, 28, 24, "#6b7280", 2, sw=2.2)
        for ligne_i, y in enumerate((5, 11, 17, 23)):
            dec = 0 if ligne_i % 2 == 0 else 7
            for x in range(3 - dec, 30, 14):
                x0, x1 = max(3, x), min(29, x + 12)
                if x1 - x0 > 2:
                    s += _rect(x0, y, x1 - x0, 5, "#9ca3af" if ligne_i % 2 else "#a8b0bb", 1, "#4b5563", 1.2)
    elif code == 3:
        s = _rect(2, 4, 28, 24, "#64748b", 2, sw=2.2)
        s += _rect(4, 6, 24, 9, "#94a3b8", 1, "#334155", 1.4) + _rect(4, 17, 24, 9, "#7d8da3", 1, "#334155", 1.4)
        s += _ligne(6, 8, 20, 8, "#cbd5e1", 1.2)
        for x in (7, 25):
            for y in (10.5, 21.5):
                s += _cercle(x, y, 1.6, "#334155", None)
    else:
        raise KeyError("matériau inconnu : %r (1 bois, 2 pierre, 3 métal)" % code)
    return svg(32, 32, s)


# ---------------------------------------------------------------------------
#  Personnages : 10 skins × 4 poses × 2 styles
# ---------------------------------------------------------------------------
SKINS = {
    # tenue, tenue2 (accent), pantalon, peau, tete (couvre-chef), coul_tete, sac, motif (torse) ; alt = style 1
    1: dict(tenue="#3b82f6", tenue2="#1e40af", pantalon="#2a2a3a", peau=PEAU, tete="cheveux", coul_tete="#222222", sac="#6b4f2a",
            motif="bande", alt=dict(tenue="#f97316", tenue2="#9a3412", coul_tete="#5b3a1a", sac="#3f3f46")),              # Recrue
    2: dict(tenue="#4d7c0f", tenue2="#365314", pantalon="#3f3f46", peau="#c68642", tete="casquette", coul_tete="#1f2937", sac="#166534",
            motif="camouflage", alt=dict(tenue="#a8a29e", tenue2="#57534e", coul_tete="#44403c", sac="#78716c")),         # Ranger
    3: dict(tenue="#1f2937", tenue2="#a855f7", pantalon="#111827", peau="#9ca3af", tete="capuche", coul_tete="#111827", sac="#312e81",
            motif="ombre", alt=dict(tenue="#450a0a", tenue2="#f97316", coul_tete="#1c1917", sac="#7f1d1d")),              # Ombre
    4: dict(tenue="#0f172a", tenue2="#22d3ee", pantalon="#0f172a", peau=PEAU, tete="visiere", coul_tete="#1e293b", sac="#164e63",
            motif="neon", alt=dict(tenue="#1e1b4b", tenue2="#f0abfc", coul_tete="#312e81", sac="#581c87")),               # Néon
    5: dict(tenue="#27272a", tenue2="#dc2626", pantalon="#18181b", peau=PEAU, tete="casque", coul_tete="#3f3f46", sac="#7f1d1d",
            motif="croix", alt=dict(tenue="#e2e8f0", tenue2="#2563eb", coul_tete="#cbd5e1", sac="#1e3a8a")),              # Chevalier
    6: dict(tenue="#7c3aed", tenue2="#fde047", pantalon="#1e1b4b", peau=PEAU, tete="tricorne", coul_tete="#111827", sac="#3b0764",
            motif="pirate", alt=dict(tenue="#0f766e", tenue2="#fde047", coul_tete="#134e4a", sac="#115e59")),             # Pirate
    7: dict(tenue="#e5e7eb", tenue2="#f97316", pantalon="#d1d5db", peau=PEAU, tete="bulle", coul_tete="#bae6fd", sac="#9ca3af",
            motif="astro", alt=dict(tenue="#0ea5e9", tenue2="#fde047", coul_tete="#fef08a", sac="#0369a1")),              # Astronaute
    8: dict(tenue="#ec4899", tenue2="#831843", pantalon="#1f2937", peau=PEAU, tete="bandeau", coul_tete="#1f2937", sac="#4a044e",
            motif="echarpe", alt=dict(tenue="#22c55e", tenue2="#14532d", coul_tete="#052e16", sac="#14532d")),            # Ninja
    9: dict(tenue="#94a3b8", tenue2="#22d3ee", pantalon="#475569", peau="#cbd5e1", tete="robot", coul_tete="#cbd5e1", sac="#334155",
            motif="robot", alt=dict(tenue="#fbbf24", tenue2="#ef4444", coul_tete="#f59e0b", sac="#78350f", peau="#fcd34d")),   # Robot
    10: dict(tenue="#fbbf24", tenue2="#f8fafc", pantalon="#78350f", peau=PEAU, tete="couronne", coul_tete="#7c2d12", sac="#b45309",
             motif="legende", alt=dict(tenue="#e2e8f0", tenue2="#fbbf24", coul_tete="#0f172a", sac="#475569")),           # Légende
}

def _skin(skin, style):
    skin = _entier(skin, "skin")
    if skin not in SKINS:
        raise KeyError("skin inconnu : %r (1..%d)" % (skin, len(SKINS)))
    sk = dict(SKINS[skin])
    alt = sk.pop("alt")
    if _nombre(style, 0) >= 1:          # style 1 (ou plus) = variante de couleur
        sk.update(alt)
    sk["num"] = skin
    return sk


def _coiffe(sk):
    """Couvre-chef / visage selon le skin (tête centrée en (30, 21), rayon 14)."""
    t, c, c2 = sk["tete"], sk["coul_tete"], sk["tenue2"]
    if t == "cheveux":
        return _chemin("M16 19 Q18 6 30 6 Q42 6 44 19 Q38 14 30 15 Q22 14 16 19 Z", c)
    if t == "casquette":
        return (_ellipse(30, 19.5, 18, 3.5, assombrir(c, 0.25)) + _chemin("M16 19 Q17 6 30 6 Q43 6 44 19 Z", c)
                + _cercle(30, 6.5, 1.8, assombrir(c, 0.3), None))
    if t == "casque":
        return (_chemin("M15 24 Q15 5 30 5 Q45 5 45 24 Q45 35 30 36 Q15 35 15 24 Z", c)
                + _rect(18, 16, 24, 8, c2, 3, sw=2) + _rect(21, 19, 18, 2, assombrir(c2, 0.5), 1, None)
                + _ligne(30, 6, 30, 14, assombrir(c, 0.4), 2.5))
    if t == "bulle":
        return (_cercle(30, 21, 17.5, c, CONTOUR, 2.2, fill_opacity=0.5)
                + _ellipse(22, 14, 2.5, 6, "#ffffff", None, opacity=0.6, transform="rotate(25 22 14)")
                + _rect(19, 35, 22, 5, c2, 2))
    if t == "bandeau":
        return (_chemin("M16 23 Q30 31 44 23 L44 30 Q30 39 16 30 Z", c)
                + _rect(15, 11, 30, 6, c2, 1) + _poly([(44, 12), (55, 9), (53, 15), (44, 17)], c2)
                + _poly([(44, 14), (54, 16), (50, 20), (44, 17)], assombrir(c2, 0.2)))
    if t == "capuche":
        # capuche sombre, visage dans l'ombre, yeux luisants de la couleur d'accent
        return (_chemin("M13 31 Q11 4 30 4 Q49 4 47 31 Q44 22 30 21 Q16 22 13 31 Z", c)
                + _ellipse(30, 26.5, 11, 9, "#020617", None, opacity=0.88)
                + _cercle(25, 25, 3.6, c2, None, opacity=0.3) + _cercle(35, 25, 3.6, c2, None, opacity=0.3)
                + _cercle(25, 25, 1.8, c2, None) + _cercle(35, 25, 1.8, c2, None))
    if t == "visiere":
        # casque fermé à visière lumineuse
        return (_chemin("M15 24 Q15 5 30 5 Q45 5 45 24 Q45 30 42 32 L18 32 Q15 30 15 24 Z", c)
                + _ligne(30, 6, 30, 13, c2, 2) + _rect(17, 15, 26, 8, c2, 3, sw=2)
                + _rect(19.5, 17, 21, 2, eclaircir(c2, 0.55), 1, None))
    if t == "couronne":
        return (_chemin("M16 19 Q18 6 30 6 Q42 6 44 19 Q38 14 30 15 Q22 14 16 19 Z", c)
                + _poly([(19, 11.5), (19, 3), (24, 7.5), (30, 2), (36, 7.5), (41, 3), (41, 11.5)], "#fbbf24", CONTOUR, 1.8)
                + _rect(19, 9.5, 22, 2.2, "#f59e0b", 0.5, None)
                + _cercle(24, 8.5, 1.2, ROUGE, None) + _cercle(30, 6.5, 1.4, "#22d3ee", None) + _cercle(36, 8.5, 1.2, ROUGE, None))
    if t == "tricorne":
        return (_ligne(16, 17, 44, 19, NOIR, 2) + _cercle(36, 22, 3.5, NOIR, CONTOUR, 1.5)
                + _chemin("M7 19 Q30 9 53 19 Q47 2 30 2 Q13 2 7 19 Z", c)
                + _chemin("M7 19 Q13 13 21 14 M53 19 Q47 13 39 14", "none", "#374151", 1.8)
                + _cercle(30, 9, 2.6, BLANC, None) + _ligne(26, 13, 34, 13, BLANC, 1.5))
    if t == "robot":
        return ""        # tête carrée dessinée dans _tete
    raise KeyError("coiffe inconnue : %r" % t)


def _tete(sk):
    """Tête (cercle ou tête de robot), cou, visage, coiffe."""
    s = _rect(25, 32, 10, 7, sk["peau"], 1.5)
    if sk["tete"] == "robot":
        c = sk["coul_tete"]
        s += (_ligne(30, 7, 30, 3.5, CONTOUR, 2.5) + _cercle(30, 3, 2.3, ROUGE, CONTOUR, 1.5)
              + _rect(12, 17, 4, 8, assombrir(c, 0.3), 1) + _rect(44, 17, 4, 8, assombrir(c, 0.3), 1)
              + _rect(16, 7, 28, 28, c, 5, sw=2.5)
              + _rect(20, 16, 7, 6, sk["tenue2"], 1.5, sw=1.5) + _rect(33, 16, 7, 6, sk["tenue2"], 1.5, sw=1.5)
              + _rect(23, 26, 14, 5, assombrir(c, 0.4), 1, None)
              + _ligne(27, 26, 27, 31, c, 1.2) + _ligne(30, 26, 30, 31, c, 1.2) + _ligne(33, 26, 33, 31, c, 1.2))
        return s
    s += _cercle(30, 21, 14, sk["peau"], CONTOUR, 2.5)
    if sk["tete"] not in ("casque", "visiere"):
        s += _cercle(25, 22, 1.9, NOIR, None) + _cercle(35, 22, 1.9, NOIR, None)
        if sk["tete"] != "bandeau":
            s += _ligne(27, 28.5, 33, 28.5, "#9a3412", 1.6, opacity=0.8)
    return s + _coiffe(sk)


def _detail_torse(sk):
    """Motif de la tenue (torse : x 12..48, y 38..72), selon sk["motif"]."""
    m, c2 = sk["motif"], sk["tenue2"]
    if m == "bande":            # Recrue : bande et fermeture
        return _rect(12, 46, 36, 6, c2, 0, None) + _rect(27, 54, 6, 10, c2, 1, None)
    if m == "camouflage":       # Ranger
        return (_ellipse(20, 48, 5, 3.5, c2, None) + _ellipse(38, 58, 6, 4, c2, None) + _ellipse(26, 62, 4, 3, c2, None)
                + _ellipse(42, 45, 3.5, 2.5, c2, None))
    if m == "ombre":            # Ombre : sceau violet luisant
        return (_poly([(30, 42), (41, 50), (36, 66), (30, 60), (24, 66), (19, 50)], c2, None, opacity=0.9)
                + _poly([(30, 46), (37, 51), (34, 61), (30, 57), (26, 61), (23, 51)], eclaircir(c2, 0.5), None, opacity=0.8))
    if m == "neon":             # Néon : chevrons lumineux
        d = "M15 46 L30 55 L45 46 M15 56 L30 65 L45 56"
        return _chemin(d, "none", c2, 6, opacity=0.3) + _chemin(d, "none", c2, 2.2) + _cercle(30, 43.5, 2.5, c2, None)
    if m == "croix":            # Chevalier
        return _plus(30, 52, 16, 5, c2, CONTOUR, 1.5)
    if m == "pirate":           # Pirate : jabot, ceinture et boucle
        return (_poly([(23, 38), (37, 38), (30, 50)], BLANC, CONTOUR, 1.5) + _rect(12, 62, 36, 5, c2, 0, None)
                + _rect(27, 61, 6, 7, "#78350f", 1, CONTOUR, 1.2))
    if m == "astro":            # Astronaute : plastron, bouton, cartouche
        return _rect(20, 44, 20, 12, c2, 2, sw=1.5) + _cercle(42, 62, 3.5, "#2563eb", CONTOUR, 1.2) + _rect(14, 60, 10, 4, "#9ca3af", 1, None)
    if m == "echarpe":          # Ninja : écharpe en diagonale
        return _poly([(12, 40), (20, 40), (48, 66), (48, 72), (40, 72), (12, 46)], c2, None)
    if m == "robot":            # Robot : voyant et panneau
        return (_cercle(30, 50, 5, c2, CONTOUR, 1.5) + _rect(16, 60, 28, 6, assombrir(sk["tenue"], 0.3), 1, None)
                + _rect(18, 61.5, 4, 3, c2, 0, None) + _rect(24, 61.5, 4, 3, c2, 0, None))
    if m == "legende":          # Légende : étoile et ceinture claire
        return (_poly(_etoile_pts(30, 48, 7, 3), c2, CONTOUR, 1.2) + _rect(12, 57, 36, 5, c2, 0, None)
                + _rect(12, 62, 36, 1.5, "#b45309", 0, None, opacity=0.6))
    return ""


def _bras(sk, haut):
    """Deux bras (traits épais cernés) et mains ; haut=True : bras levés."""
    t, p = sk["tenue"], sk["peau"]
    if haut:
        g, d = ((11, 45), (3, 20)), ((49, 45), (57, 20))
    else:
        g, d = ((11, 46), (7, 71)), ((49, 46), (53, 71))
    s = ""
    for (x0, y0), (x1, y1) in (g, d):
        s += _trait_double(x0, y0, x1, y1, t, 8, CONTOUR, 4) + _cercle(x1, y1, 4.5, p, CONTOUR, 2)
    return s


def _figure(sk, bras_haut=False):
    """Personnage debout dans une boîte 60×100 (pieds en y = 98)."""
    s = _rect(1, 40, 13, 30, sk["sac"], 4, sw=2.2) + _rect(3, 44, 9, 4, assombrir(sk["sac"], 0.3), 1, None)      # sac à dos
    s += _rect(16, 70, 12, 24, sk["pantalon"], 3, sw=2.2) + _rect(32, 70, 12, 24, sk["pantalon"], 3, sw=2.2)      # jambes
    s += _rect(14, 90, 15, 8, "#1f2937", 3, sw=2.2) + _rect(31, 90, 15, 8, "#1f2937", 3, sw=2.2)                  # chaussures
    s += _bras(sk, bras_haut)
    s += _rect(12, 38, 36, 34, sk["tenue"], 6, sw=2.5)                                                               # torse
    s += _detail_torse(sk)
    s += _rect(12, 65, 36, 5, "#1f2937", 1, None) + _rect(27, 64.5, 6, 6, "#fbbf24", 1, CONTOUR, 1.2)               # ceinture
    s += _rect(12, 38, 36, 34, "none", 6, CONTOUR, 2.5)                                                           # contour du torse
    s += _tete(sk)
    return s


def _canopee(sk):
    """Voile de parachute (80 px de large, sommet y = 4, bord y = 38) en gores alternés."""
    cx, cy, rx, ry = 40, 38, 36, 34
    angles = [180 - i * 36 for i in range(6)]       # de gauche à droite

    def pt(a):
        return cx + rx * math.cos(math.radians(a)), cy - ry * math.sin(math.radians(a))
    s = ""
    for i in range(5):
        (x0, y0), (x1, y1) = pt(angles[i]), pt(angles[i + 1])
        coul = sk["tenue"] if i % 2 == 0 else BLANC
        s += _chemin("M%s %s L%s %s A%s %s 0 0 1 %s %s Z" % (_n(cx), _n(cy), _n(x0), _n(y0), _n(rx), _n(ry), _n(x1), _n(y1)),
                     coul, CONTOUR, 1.5)
    s += _chemin("M4 38 A36 34 0 0 1 76 38 Z", "none", CONTOUR, 2.5)
    return s


def personnage(skin, pose, style=0):
    """Personnage SVG : skin 1..10, pose "debout" (60×100), "aterre" (100×60), "emote" (60×100,
    bras levés), "parachute" (80×120, sous une voile) ; style 1 = variante de couleur."""
    sk = _skin(skin, style)
    pose = str(pose).strip().lower()
    if pose == "debout":
        return svg(60, 100, _ellipse(30, 97, 20, 2.5, "#000000", None, opacity=0.25) + _figure(sk, False))
    if pose == "emote":
        return svg(60, 100, _ellipse(30, 97, 20, 2.5, "#000000", None, opacity=0.25) + _figure(sk, True))
    if pose == "aterre":
        # personnage couché : la figure debout tournée de −90° (tête à gauche), ombre au sol et étoiles
        s = _ellipse(50, 55, 46, 4.5, "#000000", None, opacity=0.3)
        s += _groupe(_figure(sk, False), transform="translate(0 60) rotate(-90)")
        for (ex, ey, r) in ((9, 10, 4), (19, 4, 3), (4, 22, 2.6)):
            s += _poly(_etoile_pts(ex, ey, r, r * 0.45), JAUNE, CONTOUR, 1.2)
        return svg(100, 60, s)
    if pose == "parachute":
        s = _canopee(sk)
        for x0 in (6, 23, 40, 57, 74):
            s += _ligne(x0, 38 if x0 in (6, 74) else 38, 31 if x0 < 40 else 49, 87, "#e5e7eb", 1.2)
            s += _ligne(x0, 38, 31 if x0 < 40 else 49, 87, CONTOUR, 0.6, opacity=0.5)
        s += _groupe(_figure(sk, True), transform="translate(23.5 63) scale(0.55)")
        return svg(80, 120, s)
    raise KeyError("pose inconnue : %r (debout, aterre, emote, parachute)" % pose)


# ---------------------------------------------------------------------------
#  Cosmétiques : pioches, planeurs, sprays, émotes, bannières, divisions, médailles
# ---------------------------------------------------------------------------
def _manche(couleur, contour=CONTOUR, rayures=None):
    s = _trait_double(9, 41, 33, 17, couleur, 5.5, contour, 4)
    if rayures:
        for t in (0.25, 0.45, 0.65):
            x, y = 9 + 24 * t, 41 - 24 * t
            s += _ligne(x - 2.4, y - 2.4, x + 2.4, y + 2.4, rayures, 1.8)
    return s


def pioche(n):
    """Icône 48×48 d'une pioche (NOMS_PIOCHES : 1 Pioche de base, 2 Hache, 3 Marteau, 4 Faux, 5 Clé géante,
    6 Katana, 7 Guitare, 8 Pelle dorée, 9 Sceptre)."""
    n = _entier(n, "pioche")
    if n == 1:
        s = _pioche_defaut()
    elif n == 2:    # hache
        s = (_manche("#3f3f46", CONTOUR, "#78350f") + _poly([(24, 4), (46, 12), (43, 31), (31, 21)], "#dc2626", CONTOUR, 2.5)
             + _ligne(45, 13, 42.5, 30, "#fca5a5", 2) + _poly([(26, 20), (34, 26), (22, 30)], "#7f1d1d", CONTOUR, 2))
    elif n == 3:    # marteau
        s = (_manche("#3f3f46", CONTOUR, "#1d4ed8")
             + _rect(21, 10, 24, 14, "#2563eb", 3, CONTOUR, 2.5, transform="rotate(45 33 17)")
             + _rect(21, 10, 5, 14, "#1e3a8a", 1, None, transform="rotate(45 33 17)")
             + _rect(40, 10, 5, 14, "#1e3a8a", 1, None, transform="rotate(45 33 17)")
             + _rect(27, 12, 12, 2.5, "#93c5fd", 1, None, transform="rotate(45 33 17)"))
    elif n == 4:    # faux
        s = (_manche("#1e1b4b", CONTOUR, "#a855f7") + _chemin("M30 16 Q50 6 46 32 Q43 18 32 22 Z", "#a855f7", CONTOUR, 2.5)
             + _chemin("M34 15 Q46 10 45 26", "none", "#e9d5ff", 1.8) + _cercle(33, 18, 2.5, "#4c1d95", CONTOUR, 1.2))
    elif n == 5:    # clé géante (clé mixte : œil fermé en bas, mâchoire ouverte en haut)
        s = (_manche("#64748b", CONTOUR, "#cbd5e1")
             + _cercle(9, 41, 5.5, "#94a3b8", CONTOUR, 2.2) + _cercle(9, 41, 2, "#334155", None)
             + _cercle(35, 15, 9.5, "#cbd5e1", CONTOUR, 2.5)
             + _poly(_tourner([(35, 12.2), (47, 12.2), (47, 17.8), (35, 17.8)], -45, 35, 15), CONTOUR, None)
             + _chemin(_arc(35, 15, 6, 150, 240), "none", "#f8fafc", 1.6, opacity=0.8))
    elif n == 6:    # katana
        lame = "M18 30 L41 7 Q45 3 44.5 8 L21.5 33 Z"
        s = (_trait_double(6, 44, 15, 35, "#1e1b4b", 5, CONTOUR, 3.5)
             + _ligne(8, 42, 10, 40, "#fbbf24", 1.6) + _ligne(11, 39, 13, 37, "#fbbf24", 1.6)
             + _ellipse(17, 33, 5.5, 2.4, "#f59e0b", CONTOUR, 1.8, transform="rotate(-45 17 33)")
             + _chemin(lame, "#e2e8f0", CONTOUR, 2.2) + _ligne(21, 30, 41.5, 9.5, "#ffffff", 1.3, opacity=0.9)
             + _eclat(44, 4, 3, 2, BLANC, 1.4))
    elif n == 7:    # guitare électrique
        s = (_trait_double(21, 27, 40, 8, "#92400e", 5, CONTOUR, 3.5)
             + _rect(36, 2, 10, 8, "#5b3a1a", 2, CONTOUR, 2, transform="rotate(45 41 6)")
             + _cercle(38.5, 4.5, 1.2, "#e5e7eb", None) + _cercle(42.5, 8.5, 1.2, "#e5e7eb", None)
             + _cercle(14, 34, 10.5, "#dc2626", CONTOUR, 2.5) + _cercle(21, 26, 7.5, "#dc2626", CONTOUR, 2.5)
             + _cercle(14, 34, 9.2, "#dc2626", None) + _cercle(21, 26, 6.2, "#dc2626", None)
             + _ellipse(11, 38, 5.5, 3.2, "#fde68a", None, opacity=0.6, transform="rotate(-45 11 38)")
             + _cercle(17, 31, 3.3, "#1f2937", CONTOUR, 1.5)
             + _ligne(12, 36, 36, 12, "#fde68a", 0.9) + _ligne(14.5, 38, 38, 14.5, "#fde68a", 0.9)
             + _rect(8, 38, 8, 2.4, "#1f2937", 0.5, None, transform="rotate(-45 12 39)"))
    elif n == 8:    # pelle dorée
        fer = _tourner([(0, -13), (-8, -4), (-7, 7), (7, 7), (8, -4)], 45, 34, 16)
        s = (_trait_double(9, 41, 28, 22, "#b45309", 5, "#78350f", 3.5)
             + _cercle(8, 42, 4.5, "none", "#78350f", 4) + _cercle(8, 42, 4.5, "none", "#fbbf24", 2)
             + _poly(fer, "#fbbf24", "#78350f", 2.5) + _ligne(28, 22, 40, 10, "#fef3c7", 1.8, opacity=0.9)
             + _eclat(44, 7, 3.5, 2, BLANC, 1.5) + _eclat(24, 12, 2.4, 2, BLANC, 1.2))
    elif n == 9:    # sceptre
        s = (_manche("#312e81", CONTOUR, "#fbbf24")
             + _cercle(37, 11, 9.5, "#a855f7", None, opacity=0.25)
             + _poly([(31, 17), (43, 17), (40.5, 21.5), (33.5, 21.5)], "#f59e0b", "#78350f", 1.8)
             + _poly([(37, 2), (44.5, 11), (37, 19.5), (29.5, 11)], "#c084fc", "#581c87", 2)
             + _poly([(37, 2), (44.5, 11), (37, 11)], "#f3e8ff", None, opacity=0.8)
             + _eclat(45, 3, 3, 2, BLANC, 1.4) + _eclat(28, 7, 2.2, 2, BLANC, 1.2))
    else:
        raise KeyError("pioche inconnue : %r (1..%d)" % (n, len(NOMS_PIOCHES)))
    return svg(48, 48, s)


_AILES_CHAUVE_SOURIS = ("M32 12 Q20 2 4 10 Q10 16 4 28 Q14 22 18 34 Q26 26 32 36 Q38 26 46 34 Q50 22 60 28 "
                        "Q54 16 60 10 Q44 2 32 12 Z")
_VOILE = "M3 27 Q32 -6 61 27 Q53.75 22 46.5 27 Q39.25 22 32 27 Q24.75 22 17.5 27 Q10.25 22 3 27 Z"


def planeur(n):
    """Icône 64×48 d'un planeur (NOMS_PLANEURS : 1 Parapluie, 2 Deltaplane, 3 Dragon, 4 Fusée, 5 Ballon,
    6 Parachute militaire, 7 Aile de chauve-souris, 8 Tapis volant, 9 OVNI)."""
    n = _entier(n, "planeur")
    if n == 1:      # parapluie
        s = (_chemin(_VOILE, "#ef4444", CONTOUR, 2.5)
             + _chemin("M32 10.5 Q22 12 17.5 27 Q24.75 22 32 27 Z", "#fde047", None)
             + _chemin("M32 10.5 Q52 13 61 27 Q53.75 22 46.5 27 Z", "#fde047", None)
             + _chemin("M3 27 Q32 -6 61 27", "none", CONTOUR, 2.5)
             + _ligne(32, 10.5, 32, 27, CONTOUR, 1.2) + _cercle(32, 9, 2.3, "#fde047", CONTOUR, 1.5)
             + _chemin("M32 27 V39 q0 6 -5.5 6 q-5.5 0 -5.5 -6", "none", CONTOUR, 5) + _chemin("M32 27 V39 q0 6 -5.5 6 q-5.5 0 -5.5 -6", "none", "#78350f", 2.5))
    elif n == 2:    # deltaplane
        s = (_chemin("M32 5 L3 31 Q32 20 61 31 Z", "#3b82f6", CONTOUR, 2.5)
             + _chemin("M32 5 L20 25 Q26 21 32 20 Z", BLANC, None, opacity=0.9) + _chemin("M32 5 L44 25 Q38 21 32 20 Z", BLANC, None, opacity=0.9)
             + _ligne(32, 5, 32, 20, CONTOUR, 1.5)
             + _ligne(32, 22, 20, 42, "#334155", 2.5) + _ligne(32, 22, 44, 42, "#334155", 2.5) + _ligne(20, 42, 44, 42, "#334155", 3)
             + _ligne(32, 20, 32, 26, CONTOUR, 2.5))
    elif n == 3:    # dragon
        s = (_chemin(_AILES_CHAUVE_SOURIS, "#16a34a", CONTOUR, 2.5)
             + _ligne(31, 15, 12, 13, "#15803d", 1.5) + _ligne(31, 16, 17, 29, "#15803d", 1.5)
             + _ligne(33, 15, 52, 13, "#15803d", 1.5) + _ligne(33, 16, 47, 29, "#15803d", 1.5)
             + _poly([(27, 13), (25, 3), (31, 10)], "#fde68a", CONTOUR, 1.5) + _poly([(37, 13), (39, 3), (33, 10)], "#fde68a", CONTOUR, 1.5)
             + _ellipse(32, 22, 7, 11, "#22c55e", CONTOUR, 2.2)
             + _poly([(25.5, 28), (38.5, 28), (32, 41)], "#4ade80", CONTOUR, 1.8)
             + _poly([(28.5, 29), (30, 33), (31.5, 29)], BLANC, None) + _poly([(32.5, 29), (34, 33), (35.5, 29)], BLANC, None)
             + _cercle(28.8, 19, 2, "#fde047", CONTOUR, 1) + _cercle(35.2, 19, 2, "#fde047", CONTOUR, 1)
             + _cercle(28.8, 19, 0.8, NOIR, None) + _cercle(35.2, 19, 0.8, NOIR, None))
    elif n == 4:    # fusée
        s = (_poly([(22, 26), (11, 40), (22, 38)], "#ef4444", CONTOUR, 2) + _poly([(42, 26), (53, 40), (42, 38)], "#ef4444", CONTOUR, 2)
             + _ellipse(32, 43.5, 4.5, 3.5, "#fb923c", None) + _ellipse(32, 43, 2.2, 2.2, "#fde047", None)
             + _rect(25, 36, 14, 4, "#475569", 1, CONTOUR, 1.8)
             + _chemin("M32 3 Q43 14 42 37 H22 Q21 14 32 3 Z", "#e5e7eb", CONTOUR, 2.5)
             + _chemin("M32 3 Q39 9 40.2 16 H23.8 Q25 9 32 3 Z", "#ef4444", CONTOUR, 1.5)
             + _cercle(32, 23, 4.5, "#38bdf8", CONTOUR, 1.8) + _cercle(30.5, 21.5, 1.3, "#ffffff", None, opacity=0.8)
             + _ligne(26, 20, 26, 33, "#ffffff", 1.3, opacity=0.6))
    elif n == 5:    # ballon (montgolfière)
        s = (_cercle(32, 17, 14, "#ef4444", CONTOUR, 2.5) + _ellipse(32, 17, 5, 14, "#fde047", None)
             + _ellipse(22.5, 17, 2.2, 12, "#fde047", None, opacity=0.6) + _ellipse(41.5, 17, 2.2, 12, "#fde047", None, opacity=0.6)
             + _cercle(32, 17, 14, "none", CONTOUR, 2.5)
             + _poly([(25, 28), (28, 35), (36, 35), (39, 28)], "#b91c1c", CONTOUR, 1.8)
             + _ligne(28.5, 35, 27.5, 40, CONTOUR, 1.2) + _ligne(35.5, 35, 36.5, 40, CONTOUR, 1.2)
             + _rect(25.5, 39.5, 13, 6.5, "#a16207", 1.5, CONTOUR, 1.8) + _ligne(25.5, 42.5, 38.5, 42.5, "#78350f", 1))
    elif n == 6:    # parachute militaire
        s = (_chemin(_VOILE, "#4d7c0f", CONTOUR, 2.5)
             + _chemin("M32 10.5 Q22 12 17.5 27 Q24.75 22 32 27 Z", "#65a30d", None)
             + _chemin("M32 10.5 Q52 13 61 27 Q53.75 22 46.5 27 Z", "#65a30d", None)
             + _chemin("M3 27 Q32 -6 61 27", "none", CONTOUR, 2.5))
        for x in (5, 18, 32, 46, 59):
            s += _ligne(x, 27, 32, 42, "#d6d3d1", 1.4) + _ligne(x, 27, 32, 42, CONTOUR, 0.6, opacity=0.5)
        s += _rect(27.5, 40, 9, 6, "#3f3f46", 2, CONTOUR, 1.6)
    elif n == 7:    # aile de chauve-souris
        s = (_chemin(_AILES_CHAUVE_SOURIS, "#581c87", CONTOUR, 2.5)
             + _ligne(31, 15, 12, 13, "#7e22ce", 1.5) + _ligne(31, 16, 17, 29, "#7e22ce", 1.5)
             + _ligne(33, 15, 52, 13, "#7e22ce", 1.5) + _ligne(33, 16, 47, 29, "#7e22ce", 1.5)
             + _poly([(27, 14), (28, 6), (32, 12)], "#3b0764", CONTOUR, 1.5) + _poly([(37, 14), (36, 6), (32, 12)], "#3b0764", CONTOUR, 1.5)
             + _ellipse(32, 24, 6.5, 11, "#3b0764", CONTOUR, 2.2)
             + _cercle(29.5, 19, 1.7, "#ef4444", None) + _cercle(34.5, 19, 1.7, "#ef4444", None))
    elif n == 8:    # tapis volant
        tapis = ("M4 20 Q12 12 20 20 Q28 28 36 20 Q44 12 52 20 Q56 24 60 18 L60 30 Q56 36 52 32 Q44 24 36 32 "
                 "Q28 40 20 32 Q12 24 4 32 Z")
        s = (_ligne(4, 20, 1.5, 14, "#fbbf24", 2) + _ligne(60, 18, 62.5, 12, "#fbbf24", 2)
             + _ligne(4, 32, 1.5, 38, "#fbbf24", 2) + _ligne(60, 30, 62.5, 36, "#fbbf24", 2)
             + _chemin(tapis, "#dc2626", CONTOUR, 2.5)
             + _chemin("M7 26 Q13 19 20 26 Q28 33 36 26 Q44 19 52 26 Q55 29 57.5 24.5", "none", "#fbbf24", 2)
             + _poly([(20, 22.5), (23, 26), (20, 29.5), (17, 26)], "#fde68a", None) + _poly([(36, 22.5), (39, 26), (36, 29.5), (33, 26)], "#fde68a", None)
             + _poly([(52, 22.5), (55, 26), (52, 29.5), (49, 26)], "#fde68a", None))
    elif n == 9:    # OVNI
        s = (_poly([(23, 32), (41, 32), (52, 47), (12, 47)], "#a5f3fc", None, opacity=0.22)
             + _cercle(32, 20, 11, "#67e8f9", CONTOUR, 2.2) + _ellipse(28, 15, 3, 4.5, "#ffffff", None, opacity=0.6)
             + _ellipse(32, 29, 27, 8.5, "#9ca3af", CONTOUR, 2.5) + _ellipse(32, 27, 22, 4.5, "#cbd5e1", None, opacity=0.9))
        for i, x in enumerate((12, 22, 32, 42, 52)):
            s += _cercle(x, 32, 2.1, JAUNE if i % 2 == 0 else ROUGE, CONTOUR, 1)
    else:
        raise KeyError("planeur inconnu : %r (1..%d)" % (n, len(NOMS_PLANEURS)))
    return svg(64, 48, s)


def _splat(couleur):
    """Fond de spray : grande tache et gouttes."""
    s = _cercle(32, 32, 27, couleur, None, opacity=0.28)
    for (x, y, r) in ((6, 14, 3), (58, 10, 2.5), (60, 50, 3.5), (8, 54, 2.5), (30, 62, 2)):
        s += _cercle(x, y, r, couleur, None, opacity=0.4)
    return s


def spray(n):
    """Spray 64×64 (contrat.SPRAYS : 1 Lama, 2 Éclair, 3 Cœur, 4 Crâne, 5 Étoile, 6 Flamme)."""
    n = _entier(n, "spray")
    if n == 1:
        s = _splat("#f0abfc")
        for x in (16, 23, 33, 40):
            s += _rect(x, 44, 5.5, 12, "#c026d3", 2, CONTOUR, 2)
        s += _poly([(14, 33), (7, 28), (14, 39)], "#c026d3", CONTOUR, 2)
        s += _rect(13, 30, 31, 16, "#d946ef", 6, CONTOUR, 2.5)
        s += _rect(15, 34, 27, 3, "#fde047", 0, None) + _rect(15, 39, 27, 3, "#22d3ee", 0, None) + _rect(15, 43, 27, 2, "#4ade80", 0, None)
        s += _rect(36, 14, 10, 20, "#d946ef", 4, CONTOUR, 2.5)
        s += _poly([(40, 9), (42, 2), (45, 9)], "#d946ef", CONTOUR, 2) + _poly([(48, 9), (50, 2), (53, 9)], "#d946ef", CONTOUR, 2)
        s += _rect(36, 8, 20, 11, "#d946ef", 4, CONTOUR, 2.5)
        s += _rect(48, 11, 8, 8, "#f0abfc", 3, None) + _cercle(44, 12.5, 1.6, NOIR, None)
    elif n == 2:
        s = (_splat("#fef08a") + _poly([(36, 3), (13, 36), (29, 36), (24, 61), (51, 25), (35, 25)], "#fde047", CONTOUR, 2.5)
             + _poly([(35, 10), (21, 32), (32, 32), (29, 48), (43, 29), (32, 29)], "#fef9c3", None, opacity=0.9))
    elif n == 3:
        s = (_splat("#fca5a5") + _chemin("M32 57 C8 40 6 24 14 15 C21 8 30 12 32 19 C34 12 43 8 50 15 C58 24 56 40 32 57 Z", "#ef4444", CONTOUR, 2.5)
             + _ellipse(22, 23, 3.5, 6, "#ffffff", None, opacity=0.55, transform="rotate(-30 22 23)"))
    elif n == 4:
        s = (_splat("#e2e8f0") + _rect(21, 37, 22, 13, "#f8fafc", 5, CONTOUR, 2.5)
             + _ligne(26, 42, 26, 48, CONTOUR, 1.6) + _ligne(30.5, 42, 30.5, 49, CONTOUR, 1.6) + _ligne(35, 42, 35, 49, CONTOUR, 1.6) + _ligne(39, 42, 39, 48, CONTOUR, 1.6)
             + _cercle(32, 25, 19, "#f8fafc", CONTOUR, 2.5)
             + _cercle(24.5, 24, 5.5, "#111827", None) + _cercle(39.5, 24, 5.5, "#111827", None)
             + _poly([(32, 29), (29, 35), (35, 35)], "#111827", None))
    elif n == 5:
        s = (_splat("#fde68a") + _poly(_etoile_pts(32, 33, 27, 12), "#facc15", CONTOUR, 2.5)
             + _poly(_etoile_pts(32, 33, 14, 6), "#fef08a", None, opacity=0.9))
    elif n == 6:
        s = (_splat("#fdba74") + _chemin("M32 3 Q47 18 47 36 Q47 54 32 61 Q17 54 17 36 Q17 25 26 15 Q26 24 30 26 Q29 13 32 3 Z", "#f97316", CONTOUR, 2.5)
             + _chemin("M32 29 Q41 38 39 48 Q37 57 32 59 Q27 57 25 48 Q23 40 32 29 Z", "#fde047", None)
             + _ellipse(32, 51, 3, 5, "#fffbeb", None, opacity=0.9))
    else:
        raise KeyError("spray inconnu : %r (1..%d)" % (n, len(C.SPRAYS)))
    return svg(64, 64, s)


def emote(n):
    """Émote 48×48 (contrat.EMOTES : 1 Salut, 2 Danse, 3 Rire, 4 Pouce, 5 Applaudir, 6 Boude)."""
    n = _entier(n, "émote")
    if n == 1:
        s = ""
        for x, y, h in ((13, 9, 16), (18.5, 5, 20), (24, 5, 20), (29.5, 9, 16)):
            s += _rect(x, y, 4.8, h, PEAU, 2.4, CONTOUR, 2)
        s += _rect(8, 24, 6, 13, PEAU, 3, CONTOUR, 2, transform="rotate(30 11 24)")
        s += _rect(13, 20, 21.5, 20, PEAU, 7, CONTOUR, 2.2)
        s += _rect(13, 38, 21.5, 7, BLEU, 2, CONTOUR, 2)
        s += _chemin("M39 14 Q44 22 39 30", "none", CONTOUR, 4) + _chemin("M39 14 Q44 22 39 30", "none", JAUNE, 2)
        s += _chemin("M43 9 Q50 22 43 35", "none", CONTOUR, 4) + _chemin("M43 9 Q50 22 43 35", "none", JAUNE, 2)
    elif n == 2:
        s = (_poly([(17, 9), (38, 5), (38, 12), (17, 16)], BLANC, CONTOUR, 2)
             + _trait_double(18.5, 37, 18.5, 12, BLANC, 2.6, CONTOUR, 2.4) + _trait_double(36.5, 33, 36.5, 8, BLANC, 2.6, CONTOUR, 2.4)
             + _ellipse(14.5, 38, 6, 4.3, BLANC, CONTOUR, 2.2, transform="rotate(-20 14.5 38)")
             + _ellipse(32.5, 34, 6, 4.3, BLANC, CONTOUR, 2.2, transform="rotate(-20 32.5 34)")
             + _eclat(43, 20, 3, 2, JAUNE, 1.8) + _eclat(6, 24, 2.5, 2, JAUNE, 1.5))
    elif n == 3:
        s = (_cercle(24, 24, 19, "#fde047", CONTOUR, 2.5)
             + _chemin("M13 19 q4.5 -6 9 0", "none", CONTOUR, 2.6) + _chemin("M26 19 q4.5 -6 9 0", "none", CONTOUR, 2.6)
             + _chemin("M12 27 Q24 46 36 27 Z", "#7f1d1d", CONTOUR, 2.2)
             + _chemin("M17 33 Q24 41 31 33 Q24 36 17 33 Z", "#f87171", None)
             + _chemin("M14 29 Q24 31 34 29 L33 27 L15 27 Z", "#ffffff", None)
             + _chemin("M9 22 q-4 4 -1 7 q3 -2 1 -7 Z", "#60a5fa", CONTOUR, 1.2) + _chemin("M39 22 q4 4 1 7 q-3 -2 -1 -7 Z", "#60a5fa", CONTOUR, 1.2))
    elif n == 4:
        s = (_rect(7, 27, 9, 15, BLEU, 2, CONTOUR, 2)
             + _rect(14, 24, 22, 18, PEAU, 5, CONTOUR, 2.5)
             + _rect(19.5, 5, 9.5, 22, PEAU, 4.7, CONTOUR, 2.5, transform="rotate(-18 24 27)")
             + _ligne(16, 30, 34, 30, CONTOUR, 1.4, opacity=0.5) + _ligne(16, 35, 34, 35, CONTOUR, 1.4, opacity=0.5)
             + _ligne(16, 40, 30, 40, CONTOUR, 1.4, opacity=0.5)
             + _eclat(40, 12, 3, 2, JAUNE, 1.8))
    elif n == 5:
        s = (_rect(5, 17, 13, 23, PEAU, 5, CONTOUR, 2.5, transform="rotate(14 11.5 28.5)")
             + _rect(30, 17, 13, 23, PEAU, 5, CONTOUR, 2.5, transform="rotate(-14 36.5 28.5)")
             + _rect(3, 36, 12, 8, BLEU, 2, CONTOUR, 2, transform="rotate(14 9 40)") + _rect(33, 36, 12, 8, BLEU, 2, CONTOUR, 2, transform="rotate(-14 39 40)")
             + _ligne(9, 20, 9, 32, CONTOUR, 1.3, opacity=0.5) + _ligne(39, 20, 39, 32, CONTOUR, 1.3, opacity=0.5)
             + _trait_double(24, 6, 24, 13, JAUNE, 2.2, CONTOUR, 2) + _trait_double(17, 9, 20, 15, JAUNE, 2.2, CONTOUR, 2)
             + _trait_double(31, 9, 28, 15, JAUNE, 2.2, CONTOUR, 2) + _trait_double(24, 38, 24, 44, JAUNE, 2.2, CONTOUR, 2))
    elif n == 6:
        s = (_cercle(24, 24, 19, "#fbbf24", CONTOUR, 2.5)
             + _ligne(17, 10, 17, 17, "#60a5fa", 2, opacity=0.8) + _ligne(22, 8, 22, 15, "#60a5fa", 2, opacity=0.8) + _ligne(27, 9, 27, 16, "#60a5fa", 2, opacity=0.8)
             + _ligne(13, 18, 21, 22, CONTOUR, 2.6) + _ligne(35, 18, 27, 22, CONTOUR, 2.6)
             + _cercle(18, 26, 2, NOIR, None) + _cercle(30, 26, 2, NOIR, None)
             + _chemin("M15 37 Q24 29 33 37", "none", CONTOUR, 2.6))
    else:
        raise KeyError("émote inconnue : %r (1..%d)" % (n, len(C.EMOTES)))
    return svg(48, 48, s)


def banniere(n):
    """Bannière / badge 40×40 (NOMS_BANNIERES : 1 Étoile, 2 Lama, 3 Éclair, 4 Crâne, 5 Cœur, 6 Flamme,
    7 Couronne, 8 Bouclier, 9 Diamant, 10 Trophée) ; chaque écusson a sa forme et sa couleur."""
    n = _entier(n, "bannière")
    ecu = "M20 3 L35 8 V20 Q35 32 20 37 Q5 32 5 20 V8 Z"
    ecu_int = "M20 7 L31 10.5 V20 Q31 29 20 33 Q9 29 9 20 V10.5 Z"
    if n == 1:      # écu bleu, étoile
        s = _chemin(ecu, "#2563eb", CONTOUR, 2.5) + _chemin(ecu_int, "none", "#93c5fd", 1.5) + _poly(_etoile_pts(20, 20, 8, 3.5), BLANC, None)
    elif n == 2:    # disque magenta, lama
        s = (_cercle(20, 20, 16.5, "#c026d3", CONTOUR, 2.5) + _cercle(20, 20, 12.5, "none", "#f0abfc", 1.5)
             + _rect(10, 19, 16, 8, BLANC, 3, None) + _rect(22, 10, 5, 11, BLANC, 2, None) + _rect(21, 8, 10, 5.5, BLANC, 2.5, None)
             + _poly([(23, 8.5), (24, 4.5), (26, 8.5)], BLANC, None) + _poly([(27, 8.5), (28, 4.5), (30, 8.5)], BLANC, None))
        for x in (11, 15, 20, 24):
            s += _rect(x, 26, 3, 6, BLANC, 1, None)
        s += _cercle(28.3, 10.5, 0.9, "#c026d3", None)
    elif n == 3:    # disque rouge, éclair
        s = _cercle(20, 20, 16.5, "#dc2626", CONTOUR, 2.5) + _cercle(20, 20, 12.5, "none", "#fca5a5", 1.5) \
            + _poly([(22, 8), (13, 22), (19, 22), (17, 32), (27, 17), (21, 17)], JAUNE, CONTOUR, 1.5)
    elif n == 4:    # hexagone gris, crâne
        s = (_poly(_polygone_regulier(20, 20, 17, 6), "#475569", CONTOUR, 2.5) + _poly(_polygone_regulier(20, 20, 13, 6), "none", "#94a3b8", 1.5)
             + _cercle(20, 17, 7, BLANC, None) + _rect(16, 21, 8, 5, BLANC, 1.5, None)
             + _cercle(17.3, 16.5, 2, "#1f2937", None) + _cercle(22.7, 16.5, 2, "#1f2937", None)
             + _poly([(20, 19), (19, 21), (21, 21)], "#1f2937", None)
             + _ligne(18, 23, 18, 25.5, "#475569", 1) + _ligne(20, 23, 20, 25.5, "#475569", 1) + _ligne(22, 23, 22, 25.5, "#475569", 1))
    elif n == 5:    # écu noir, cœur rose
        s = _chemin(ecu, "#111827", CONTOUR, 2.5) + _chemin(ecu_int, "none", "#ec4899", 1.5) \
            + _chemin("M20 30 C9 22 8 15 12 12 C15 9.5 19 11.5 20 14.5 C21 11.5 25 9.5 28 12 C32 15 31 22 20 30 Z", "#ec4899", None)
    elif n == 6:    # fanion orange, flamme
        s = (_poly([(6, 4), (34, 4), (34, 24), (20, 36), (6, 24)], "#ea580c", CONTOUR, 2.5) + _rect(6, 4, 28, 5, "#fdba74", 0, None)
             + _chemin("M20 10 Q27 17 27 23.5 Q27 30 20 33 Q13 30 13 23.5 Q13 19.5 17 15.5 Q17 19.5 19 20.5 Q18 14.5 20 10 Z", "#fde047", CONTOUR, 1.3)
             + _chemin("M20 21 Q24 25 23 28.5 Q22 31.5 20 32 Q18 31.5 17 28.5 Q16 25.5 20 21 Z", "#fff7ed", None))
    elif n == 7:    # pentagone cyan, couronne
        s = _poly(_polygone_regulier(20, 21, 17, 5), "#06b6d4", CONTOUR, 2.5) + _poly(_polygone_regulier(20, 21, 12.5, 5), "none", "#a5f3fc", 1.5) \
            + _poly([(13, 27), (13, 17), (18, 21), (20, 14), (22, 21), (27, 17), (27, 27)], JAUNE, CONTOUR, 1.5)
    elif n == 8:    # losange violet, bouclier
        s = (_poly([(20, 3), (37, 20), (20, 37), (3, 20)], "#7c3aed", CONTOUR, 2.5) + _poly([(20, 8), (32, 20), (20, 32), (8, 20)], "none", "#d8b4fe", 1.5)
             + _chemin("M20 10.5 L27 13 V18.5 Q27 25 20 28.5 Q13 25 13 18.5 V13 Z", BLANC, "#4c1d95", 1)
             + _rect(19.2, 13, 1.6, 12.5, "#7c3aed", 0, None) + _rect(15, 17.3, 10, 1.6, "#7c3aed", 0, None))
    elif n == 9:    # hexagone turquoise, diamant
        s = (_poly(_polygone_regulier(20, 20, 17, 6, 0), "#0d9488", CONTOUR, 2.5) + _poly(_polygone_regulier(20, 20, 13, 6, 0), "none", "#5eead4", 1.5)
             + _poly([(20, 11), (28, 18), (20, 30), (12, 18)], "#ecfeff", "#0f766e", 1.2)
             + _chemin("M12 18 H28 M20 11 L16.5 18 L20 30 M20 11 L23.5 18 L20 30", "none", "#5eead4", 1))
    elif n == 10:   # écu doré, trophée
        s = (_chemin(ecu, "#f59e0b", CONTOUR, 2.5) + _chemin(ecu_int, "none", "#fde68a", 1.5)
             + _chemin("M14 10 H26 V16 Q26 22 20 23 Q14 22 14 16 Z", NOIR, None, opacity=0.85)
             + _chemin("M14 12 Q9 12 10.5 17 Q11.5 19 14 18.5", "none", NOIR, 2, opacity=0.85)
             + _chemin("M26 12 Q31 12 29.5 17 Q28.5 19 26 18.5", "none", NOIR, 2, opacity=0.85)
             + _rect(18.8, 23, 2.4, 3, NOIR, 0, None, opacity=0.85) + _rect(15, 26, 10, 2.8, NOIR, 0.8, None, opacity=0.85))
    else:
        raise KeyError("bannière inconnue : %r (1..%d)" % (n, len(NOMS_BANNIERES)))
    return svg(40, 40, s)


def _chevrons(nb, couleur, sw=4, bas=32):
    s = ""
    for i in range(nb):
        y = bas - i * 6
        s += _chemin("M14 %s L24 %s L34 %s" % (_n(y), _n(y - 8), _n(y)), "none", couleur, sw)
    return s


def division(n):
    """Division d'Arène 48×48 (1 Bronze, 2 Argent, 3 Or, 4 Platine, 5 Diamant, 6 Champion, 7 Irréel)."""
    n = _entier(n, "division")
    palettes = {1: ("#f6ad55", "#b45309", "#7c2d12"), 2: ("#f1f5f9", "#94a3b8", "#475569"), 3: ("#fef08a", "#f59e0b", "#92400e"),
                4: ("#ccfbf1", "#2dd4bf", "#0f766e"), 5: ("#dbeafe", "#60a5fa", "#1d4ed8"), 6: ("#f3e8ff", "#a855f7", "#6b21a8"),
                7: ("#fbcfe8", "#a78bfa", "#0891b2")}
    if n not in palettes:
        raise KeyError("division inconnue : %r (1..7)" % n)
    clair, moyen, fonce = palettes[n]
    badge = [(24, 3), (42, 12), (42, 32), (24, 45), (6, 32), (6, 12)]
    interieur = [(24, 8), (38, 15), (38, 30), (24, 40), (10, 30), (10, 15)]
    s = _defs(_degrade("dg", [(0, clair), (0.5, moyen), (1, fonce)], 0, 0, 1, 1))
    s += _poly(badge, "url(#dg)", CONTOUR, 2.5) + _poly(interieur, "none", clair, 1.5, opacity=0.7)
    blanc = "#ffffff"
    if n == 1:
        s += _chevrons(1, blanc, 4, 28)
    elif n == 2:
        s += _chevrons(2, blanc, 4, 31)
    elif n == 3:
        s += _chevrons(3, blanc, 4, 34)
    elif n == 4:
        s += _chevrons(3, blanc, 3, 35) + _poly(_etoile_pts(24, 13, 4, 1.8), blanc, None)
    elif n == 5:
        s += (_poly([(24, 12), (34, 21), (24, 37), (14, 21)], blanc, fonce, 1.5, opacity=0.95)
              + _chemin("M14 21 H34 M24 12 L20 21 L24 37 M24 12 L28 21 L24 37", "none", moyen, 1.2, opacity=0.8))
    elif n == 6:
        s += (_poly([(12, 32), (12, 18), (19, 25), (24, 15), (29, 25), (36, 18), (36, 32)], JAUNE, CONTOUR, 2)
              + _rect(12, 30, 24, 5, "#f59e0b", 1, CONTOUR, 1.5) + _cercle(24, 15, 2, "#ef4444", None) + _cercle(12, 18, 1.8, "#22d3ee", None)
              + _cercle(36, 18, 1.8, "#22d3ee", None))
    elif n == 7:
        s += (_poly([(15, 24), (4, 14), (9, 24), (4, 34)], blanc, fonce, 1.2) + _poly([(33, 24), (44, 14), (39, 24), (44, 34)], blanc, fonce, 1.2)
              + _poly(_etoile_pts(24, 24, 10, 4.5), blanc, fonce, 1.5) + _eclat(24, 9, 3, 2, blanc, 1.5) + _eclat(24, 40, 2.5, 2, blanc, 1.3))
    return svg(48, 48, s)


def medaille(rang):
    """Médaille 48×48 : 1 or, 2 argent, 3 bronze (ruban bleu/rouge)."""
    rang = _entier(rang, "rang")
    metaux = {1: ("#fde68a", "#f59e0b", "#92400e"), 2: ("#f8fafc", "#cbd5e1", "#64748b"), 3: ("#f6ad55", "#d97706", "#7c2d12")}
    if rang not in metaux:
        raise KeyError("rang inconnu : %r (1 or, 2 argent, 3 bronze)" % rang)
    clair, moyen, fonce = metaux[rang]
    s = _defs(_radial("mg", [(0, clair), (0.6, moyen), (1, fonce)], 0.4, 0.35, 0.7))
    s += _poly([(13, 2), (23, 2), (27, 23), (16, 27)], "#1d4ed8", CONTOUR, 2) + _poly([(25, 2), (35, 2), (32, 27), (21, 23)], "#dc2626", CONTOUR, 2)
    s += _cercle(24, 32, 13.5, "url(#mg)", fonce, 2.5) + _cercle(24, 32, 9.5, "none", clair, 1.5, opacity=0.8)
    s += _poly(_etoile_pts(24, 32, 6.5, 3), clair if rang != 2 else "#ffffff", fonce, 1.2)
    for i in range(rang):
        s += _cercle(24 + (i - (rang - 1) / 2.0) * 5, 44.5, 1.6, fonce, None)
    return svg(48, 48, s)


# ---------------------------------------------------------------------------
#  Icônes de jeu et d'interface
# ---------------------------------------------------------------------------
def bus():
    """Bus de combat 64×40 (bleu, suspendu à un ballon)."""
    s = _ligne(28, 14, 21, 19, CONTOUR, 1.5) + _ligne(36, 14, 43, 19, CONTOUR, 1.5)
    s += _cercle(32, 8, 7, "#60a5fa", CONTOUR, 2) + _chemin("M25.4 9.5 Q32 12.5 38.6 9.5", "none", BLANC, 2)
    s += _ellipse(29.5, 5.5, 1.6, 2.6, "#ffffff", None, opacity=0.6)
    s += _rect(29, 13.5, 6, 3.5, "#1e40af", 1, CONTOUR, 1.5)
    s += _cercle(16, 34, 4.5, NOIR, CONTOUR, 2) + _cercle(48, 34, 4.5, NOIR, CONTOUR, 2)
    s += _rect(5, 17, 54, 17, "#2563eb", 3, CONTOUR, 2.5) + _rect(5, 17, 54, 3.5, "#1e40af", 2, None)
    for x in (8, 18, 28, 38, 48):
        s += _rect(x, 21.5, 8, 6, "#bae6fd", 1, CONTOUR, 1.5)
    s += _rect(5, 30.5, 54, 3.5, "#1e3a8a", 1, None) + _cercle(57, 29, 1.6, JAUNE, None) + _cercle(7, 29, 1.6, ROUGE, None)
    s += _cercle(16, 34, 2, GRIS, None) + _cercle(48, 34, 2, GRIS, None)
    return svg(64, 40, s)


def parachute_icone():
    """Parachute 32×32 (voile rouge et blanche)."""
    s = _chemin("M3 15 Q16 -4 29 15 Q22.5 12 16 15 Q9.5 12 3 15 Z", ROUGE, CONTOUR, 2)
    s += _chemin("M16 5.5 Q9 7 3 15 Q9.5 12 16 15 Z", BLANC, None, opacity=0.92) + _chemin("M16 5.5 Q23 7 29 15 Q22.5 12 16 15 Z", BLANC, None, opacity=0.92)
    s += _chemin("M3 15 Q16 -4 29 15", "none", CONTOUR, 2)
    s += _ligne(4, 15, 16, 27, CONTOUR, 1.2) + _ligne(16, 15, 16, 27, CONTOUR, 1.2) + _ligne(28, 15, 16, 27, CONTOUR, 1.2)
    s += _cercle(16, 27.5, 3.2, JAUNE, CONTOUR, 1.8)
    return svg(32, 32, s)


def planeur_icone():
    """Planeur 32×32 (aile delta bleue)."""
    s = _chemin("M16 4 L2 19 Q16 13 30 19 Z", BLEU, CONTOUR, 2)
    s += _chemin("M16 4 L10 15 Q13 13 16 13 Z", BLANC, None, opacity=0.92) + _chemin("M16 4 L22 15 Q19 13 16 13 Z", BLANC, None, opacity=0.92)
    s += _ligne(16, 4, 16, 13, CONTOUR, 1.2)
    s += _ligne(16, 14, 9, 27, "#334155", 2) + _ligne(16, 14, 23, 27, "#334155", 2) + _ligne(9, 27, 23, 27, "#334155", 2.5)
    return svg(32, 32, s)


def marqueur(couleur):
    """Épingle de ping 24×36 (pointe en (12, 36)) ; `couleur` CSS (#rrggbb), jaune si vide."""
    couleur = str(couleur).strip() if couleur else JAUNE
    s = _ellipse(12, 33.5, 5, 1.8, "#000000", None, opacity=0.3)
    s += _chemin("M12 34 C12 34 2 21 2 12 A10 10 0 0 1 22 12 C22 21 12 34 12 34 Z", couleur, CONTOUR, 2)
    s += _cercle(12, 12, 4.2, BLANC, CONTOUR, 1.5)
    return svg(24, 36, s)


def carte_redeploiement():
    """Carte de redéploiement 32×40 (carte bleue, silhouette blanche)."""
    s = _rect(3, 3, 26, 34, "#2563eb", 3, CONTOUR, 2.2) + _rect(6, 6, 20, 28, "#3b82f6", 2, None)
    s += _rect(6, 6, 20, 5, JAUNE, 1, None) + _rect(8, 31, 16, 2, "#1e3a8a", 1, None)
    s += _cercle(16, 18, 4, BLANC, None) + _chemin("M9 30 Q9 23 16 23 Q23 23 23 30 Z", BLANC, None)
    return svg(32, 40, s)


def balise():
    """Borne de redéploiement 40×60 (pilier bleu, lumière cyan)."""
    s = _ellipse(20, 54, 19, 5.5, "#38bdf8", None, opacity=0.3) + _ellipse(20, 53, 15, 4.5, "#1e3a8a", CONTOUR, 2)
    s += _rect(8, 44, 24, 10, "#334155", 2, CONTOUR, 2.2) + _rect(13, 14, 14, 32, "#2563eb", 3, CONTOUR, 2.5)
    s += _rect(16, 18, 8, 22, "#67e8f9", 2, CONTOUR, 1.5)
    for y in (23, 28, 33):
        s += _ligne(18, y, 22, y, "#0e7490", 1.3)
    s += _rect(11, 8, 18, 8, "#0ea5e9", 3, CONTOUR, 2.2)
    s += _cercle(20, 6, 6.5, "#a5f3fc", None, opacity=0.45) + _cercle(20, 6, 3.8, "#ecfeff", CONTOUR, 1.8)
    return svg(40, 60, s)


def coffre_ouvert():
    """Coffre ouvert 60×50 (variante de svg.svg_coffre, couvercle relevé et lueur)."""
    s = _rect(6, 2, 48, 18, "#daa520", 4, "#3b2a00", 3) + _rect(10, 5, 40, 11, "#8b6508", 2, None)
    s += _poly([(12, 22), (48, 22), (45, 8), (15, 8)], "#fff7ae", None, opacity=0.65)
    s += _eclat(20, 13, 3, 2, BLANC, 1.6) + _eclat(40, 11, 2.5, 2, BLANC, 1.4) + _eclat(30, 16, 2, 2, JAUNE, 1.4)
    s += _rect(3, 22, 54, 26, "#b8860b", 4, "#3b2a00", 3) + _rect(3, 22, 54, 6, "#8b6508", 0, None)
    for x in (16, 26, 36, 46):
        s += _cercle(x, 22.5, 4, "#fde047", "#3b2a00", 1.5)
    s += _rect(25, 30, 10, 10, "#ffd700", 2, "#3b2a00", 2) + _cercle(30, 34, 2, "#3b2a00", None)
    return svg(60, 50, s)


def bus_carte():
    """Bus de combat vu de dessus 30×18, pointant vers +x (direction Scratch 90), pour la carte."""
    s = _ellipse(13, 9, 12, 8, "#a855f7", None, opacity=0.35)                    # ombre du ballon
    s += _rect(2, 4, 22, 10, "#2563eb", 3, CONTOUR, 1.5)
    for x in (5, 11, 17):
        s += _rect(x, 6, 4, 3, "#dbeafe", 0.5, None)
    s += _rect(2, 12, 22, 2, "#1e3a8a", 0.5, None)
    s += _poly([(24, 4), (29, 9), (24, 14)], "#fbbf24", CONTOUR, 1.2)             # avant / sens de marche
    s += _cercle(9, 9, 3.6, "#93c5fd", CONTOUR, 1.2, opacity=0.95)                # ballon
    return svg(30, 18, s)


def parachute_carte():
    """Parachute miniature 14×16 (position du joueur en vol sur la carte)."""
    s = _chemin("M1 7 A6 6 0 0 1 13 7 L7 8.5 Z", ROUGE, CONTOUR, 1.2)
    s += _chemin("M4 6.5 Q7 4 10 6.5 L7 8.5 Z", BLANC, None, opacity=0.9)
    s += _ligne(2, 7.5, 7, 14, CONTOUR, 0.9) + _ligne(12, 7.5, 7, 14, CONTOUR, 0.9)
    s += _cercle(7, 14, 1.7, JAUNE, CONTOUR, 0.9)
    return svg(14, 16, s)


def coffre_carte():
    """Coffre miniature 8×8 (coffres restants sur la carte)."""
    s = _rect(0.8, 1.5, 6.4, 5.5, "#facc15", 1, "#713f12", 1.2)
    s += _rect(3, 1.5, 2, 5.5, "#a16207", 0, None) + _rect(0.8, 1.5, 6.4, 1.6, "#d97706", 0, None, opacity=0.8)
    return svg(8, 8, s)


def boussole_curseur():
    """Curseur de boussole 16×16 (pointe vers le haut)."""
    s = _poly([(8, 1), (14, 15), (8, 11), (2, 15)], BLANC, None) + _poly([(8, 1), (8, 11), (2, 15)], "#cbd5e1", None)
    s += _poly([(8, 1), (14, 15), (8, 11), (2, 15)], "none", CONTOUR, 1.5)
    return svg(16, 16, s)


def jeton():
    """Jeton 24×24 (pièce dorée frappée d'un V)."""
    s = _cercle(12, 12, 11, "#f59e0b", "#78350f", 2) + _cercle(12, 12, 8, "#fbbf24", "#d97706", 1.2)
    s += _chemin("M7.5 8 L12 16.5 L16.5 8", "none", "#78350f", 3)
    s += _chemin("M4.5 9 A8.5 8.5 0 0 1 9 4.3", "none", "#fef3c7", 1.5, opacity=0.8)
    return svg(24, 24, s)


def etoile():
    """Étoile 24×24 (jaune)."""
    return svg(24, 24, _poly(_etoile_pts(12, 12.5, 11, 4.8), JAUNE, "#92400e", 2) + _poly(_etoile_pts(12, 12.5, 5.5, 2.4), "#fef9c3", None, opacity=0.8))


def cadenas():
    """Cadenas 24×24 (anse grise, corps doré)."""
    anse = "M7 11 V8 a5 5 0 0 1 10 0 V11"
    s = _chemin(anse, "none", CONTOUR, 5.5) + _chemin(anse, "none", "#94a3b8", 3)
    s += _rect(4, 10.5, 16, 11.5, "#f59e0b", 3, CONTOUR, 2) + _rect(6, 12.5, 12, 3, "#fbbf24", 1.5, None)
    s += _cercle(12, 15.5, 2, CONTOUR, None) + _rect(11, 16, 2, 4, CONTOUR, 0, None)
    return svg(24, 24, s)


def coche():
    """Coche 24×24 (disque vert)."""
    return svg(24, 24, _cercle(12, 12, 10.5, "#22c55e", CONTOUR, 2) + _chemin("M6.5 12.5 L10.5 16.5 L17.5 8.5", "none", "#ffffff", 3))


def croix():
    """Croix 24×24 (disque rouge)."""
    return svg(24, 24, _cercle(12, 12, 10.5, "#ef4444", CONTOUR, 2) + _chemin("M8 8 L16 16 M16 8 L8 16", "none", "#ffffff", 3))


def fleche(direction):
    """Flèche 24×24 : "haut", "bas", "gauche", "droite"."""
    angles = {"haut": 0, "droite": 90, "bas": 180, "gauche": 270}
    direction = str(direction).strip().lower()
    if direction not in angles:
        raise KeyError("direction inconnue : %r (haut, bas, gauche, droite)" % direction)
    pts = [(12, 2.5), (21.5, 13), (15.5, 13), (15.5, 21.5), (8.5, 21.5), (8.5, 13), (2.5, 13)]
    pts = _tourner(pts, angles[direction], 12, 12)
    return svg(24, 24, _poly(pts, BLANC, CONTOUR, 2))


def _engrenage(cx, cy, R, r, dents):
    pts = []
    for k in range(dents):
        base = k * 360.0 / dents
        for da, rr in ((-13, r), (-7, R), (7, R), (13, r)):
            a = math.radians(base + da)
            pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    return pts


def icone_onglet(nom):
    """Icône 32×32 d'un onglet du salon (contrat.ONGLETS)."""
    nom = str(nom)
    if nom == "accueil":
        s = (_rect(22, 5, 4, 8, "#9ca3af", 0.5, CONTOUR, 1.5) + _rect(6, 15, 20, 14, "#fde68a", 1, CONTOUR, 2)
             + _poly([(16, 3), (30, 16.5), (2, 16.5)], "#f87171", CONTOUR, 2)
             + _rect(13, 20, 6, 9, "#92400e", 1, CONTOUR, 1.5) + _rect(21, 19, 4, 4, "#60a5fa", 0.5, CONTOUR, 1.2))
    elif nom == "passe":
        s = (_poly([(9, 22), (15, 22), (13, 30), (7, 30)], "#7c3aed", CONTOUR, 1.5) + _poly([(17, 22), (23, 22), (25, 30), (19, 30)], "#7c3aed", CONTOUR, 1.5)
             + _rect(5, 3, 22, 22, "#a855f7", 5, CONTOUR, 2.2) + _rect(8, 6, 16, 16, "none", 3, "#d8b4fe", 1.2)
             + _poly(_etoile_pts(16, 14.5, 7.5, 3.3), BLANC, None))
    elif nom == "boutique":
        s = (_chemin("M11 12 V9 a5 5 0 0 1 10 0 V12", "none", CONTOUR, 2.5)
             + _chemin("M5.5 12 H26.5 L24.5 29.5 H7.5 Z", "#22d3ee", CONTOUR, 2.2)
             + _rect(8, 15, 3, 11, "#ffffff", 1.5, None, opacity=0.5) + _cercle(21.5, 22, 2.8, JAUNE, CONTOUR, 1.3))
    elif nom == "casier":
        s = (_chemin("M16 2 a2 2 0 1 1 2 2 L16 5.5", "none", CONTOUR, 1.6)
             + _poly([(5, 11), (11, 6), (14, 8), (18, 8), (21, 6), (27, 11), (24, 16), (21, 14), (21, 28), (11, 28), (11, 14), (8, 16)], "#3b82f6", CONTOUR, 2)
             + _chemin("M14 8 Q16 11 18 8", "none", CONTOUR, 1.5) + _poly(_etoile_pts(16, 19, 3.5, 1.5), JAUNE, None))
    elif nom == "quetes":
        s = _rect(6, 4, 20, 24, "#fef3c7", 2, CONTOUR, 2.2) + _rect(6, 4, 20, 4, "#fbbf24", 1, None)
        for i, y in enumerate((10, 16, 22)):
            if i == 0:
                s += _rect(9, y, 4.5, 4.5, "#22c55e", 1, CONTOUR, 1.3) + _chemin("M9.8 12.3 L11 13.5 L13 11", "none", "#ffffff", 1.3)
            else:
                s += _rect(9, y, 4.5, 4.5, "#ffffff", 1, "#92400e", 1.3)
            s += _ligne(16, y + 2.3, 23, y + 2.3, "#92400e", 1.8)
    elif nom == "carriere":
        s = (_ligne(4, 28, 28, 28, CONTOUR, 2) + _rect(6, 18, 5.5, 10, "#3b82f6", 1, CONTOUR, 1.8)
             + _rect(13.5, 12, 5.5, 16, "#22c55e", 1, CONTOUR, 1.8) + _rect(21, 5, 5.5, 23, "#fde047", 1, CONTOUR, 1.8))
    elif nom == "parametres":
        s = _poly(_engrenage(16, 16, 13.5, 10, 8), "#94a3b8", CONTOUR, 2) + _cercle(16, 16, 4.5, "#1e293b", CONTOUR, 2)
    else:
        raise KeyError("onglet inconnu : %r (%s)" % (nom, ", ".join(C.ONGLETS)))
    return svg(32, 32, s)


def icone_quete(type_quete):
    """Icône 32×32 : "quotidienne" (soleil), "hebdomadaire" (calendrier), "histoire" (livre) ;
    accepte aussi le code numérique du contrat (1 quotidienne, 2 hebdomadaire, 3 histoire)."""
    t = str(type_quete).strip().lower()
    t = {"1": "quotidienne", "1.0": "quotidienne", "2": "hebdomadaire", "2.0": "hebdomadaire",
         "3": "histoire", "3.0": "histoire", "quotidien": "quotidienne", "hebdo": "hebdomadaire"}.get(t, t)
    if t == "quotidienne":
        s = ""
        for i in range(8):
            a = math.radians(i * 45)
            x0, y0, x1, y1 = 16 + 10.5 * math.cos(a), 16 + 10.5 * math.sin(a), 16 + 14.5 * math.cos(a), 16 + 14.5 * math.sin(a)
            s += _ligne(x0, y0, x1, y1, CONTOUR, 4.5) + _ligne(x0, y0, x1, y1, JAUNE, 2.5)
        s += _cercle(16, 16, 7.5, "#fde047", CONTOUR, 2.2) + _cercle(13.5, 13.5, 2, "#fffbeb", None, opacity=0.8)
    elif t == "hebdomadaire":
        s = (_rect(4, 7, 24, 21, "#f8fafc", 3, CONTOUR, 2.2) + _rect(4, 7, 24, 7, "#ef4444", 3, None) + _rect(4, 11, 24, 3, "#ef4444", 0, None)
             + _rect(8.5, 3.5, 3, 7, "#64748b", 1, CONTOUR, 1.3) + _rect(20.5, 3.5, 3, 7, "#64748b", 1, CONTOUR, 1.3))
        for yy in (17, 22):
            for xx in (8, 14, 20):
                s += _rect(xx, yy, 4, 3, "#60a5fa" if (xx, yy) == (14, 17) else "#94a3b8", 0.5, None)
    elif t == "histoire":
        s = (_rect(5, 5, 22, 22, "#7c3aed", 2, CONTOUR, 2.2) + _rect(5, 5, 5, 22, "#5b21b6", 2, None) + _rect(8, 5, 2, 22, "#5b21b6", 0, None)
             + _rect(24, 8, 2, 16, "#f1f5f9", 0, None) + _poly(_etoile_pts(17.5, 16, 5.5, 2.4), JAUNE, None)
             + _poly([(20, 5), (24, 5), (24, 13), (22, 11), (20, 13)], "#ef4444", None))
    else:
        raise KeyError("type de quête inconnu : %r (quotidienne, hebdomadaire, histoire)" % type_quete)
    return svg(32, 32, s)


def icone_succes():
    """Succès 32×32 (trophée doré)."""
    s = ""
    for d in ("M9 7 Q3 7 4.5 13 Q5.5 16 9 15", "M23 7 Q29 7 27.5 13 Q26.5 16 23 15"):
        s += _chemin(d, "none", CONTOUR, 4.2) + _chemin(d, "none", "#fbbf24", 2)
    s += _chemin("M9 4 H23 V13 Q23 21 16 22 Q9 21 9 13 Z", "#fbbf24", CONTOUR, 2.2)
    s += _ligne(11.8, 7, 11.8, 14, "#fef3c7", 1.5, opacity=0.8) + _poly(_etoile_pts(16, 12.5, 4, 1.8), BLANC, None, opacity=0.9)
    s += _rect(14, 22, 4, 4, "#d97706", 0.5, CONTOUR, 1.6) + _rect(9, 25.5, 14, 4, "#92400e", 1, CONTOUR, 1.8)
    return svg(32, 32, s)


def icone_ami(etat):
    """Ami 24×24 : "enligne" (vert), "enpartie" (orange), "horsligne" (gris)."""
    couleurs = {"enligne": "#22c55e", "enpartie": "#f97316", "horsligne": "#6b7280"}
    etat = str(etat).strip().lower().replace(" ", "").replace("_", "").replace("-", "")
    etat = {"online": "enligne", "ingame": "enpartie", "offline": "horsligne"}.get(etat, etat)
    if etat not in couleurs:
        raise KeyError("état inconnu : %r (enligne, enpartie, horsligne)" % etat)
    s = _chemin("M3 22 Q3 13 12 13 Q21 13 21 22 Z", "#e2e8f0", CONTOUR, 2) + _cercle(12, 7.5, 5, "#e2e8f0", CONTOUR, 2)
    s += _cercle(18.5, 18.5, 4.5, couleurs[etat], CONTOUR, 1.6)
    return svg(24, 24, s)


def icone_haut_parleur(n):
    """Haut-parleur 24×24 : n = 0 (muet, croix rouge), 1, 2 ou 3 ondes.
    n > 3 est lu comme un volume en % (1..50 une onde, 51..84 deux, au-delà trois) ;
    une valeur non numérique vaut 0."""
    p = _nombre(n, 0)
    if p <= 0:
        n = 0
    elif p <= 3:
        n = max(1, int(round(p)))
    else:
        n = 1 if p <= 50 else (2 if p <= 84 else 3)
    s = _poly([(1, 9), (5.5, 9), (11, 4), (11, 20), (5.5, 15), (1, 15)], "#e2e8f0", CONTOUR, 2)
    ondes = ["M14 9 Q16.5 12 14 15", "M17 6.5 Q20.5 12 17 17.5", "M19.5 4.5 Q23 12 19.5 19.5"]
    for d in ondes[:n]:
        s += _chemin(d, "none", CONTOUR, 4) + _chemin(d, "none", "#e2e8f0", 2)
    if n == 0:
        s += _ligne(14, 8.5, 21, 15.5, CONTOUR, 4) + _ligne(21, 8.5, 14, 15.5, CONTOUR, 4)
        s += _ligne(14, 8.5, 21, 15.5, ROUGE, 2.2) + _ligne(21, 8.5, 14, 15.5, ROUGE, 2.2)
    return svg(24, 24, s)


def icone_oeil():
    """Œil 24×24 (spectateur)."""
    s = _chemin("M2 12 Q12 2 22 12 Q12 22 2 12 Z", "#f8fafc", CONTOUR, 2)
    s += _cercle(12, 12, 4.5, "#3b82f6", CONTOUR, 1.5) + _cercle(12, 12, 2, NOIR, None) + _cercle(13.6, 10.4, 1, "#ffffff", None)
    return svg(24, 24, s)


def icone_signaler():
    """Signaler 24×24 (drapeau rouge)."""
    s = _poly([(6.5, 4), (21, 4), (18, 9), (21, 14), (6.5, 14)], "#ef4444", CONTOUR, 2)
    s += _ligne(6.5, 3, 6.5, 22, CONTOUR, 3.5) + _ligne(6.5, 3, 6.5, 22, "#e2e8f0", 1.6)
    s += _rect(11.5, 6, 2.2, 4.5, "#ffffff", 1, None) + _cercle(12.6, 12, 1.2, "#ffffff", None)
    return svg(24, 24, s)


def icone_zone():
    """Zone de tempête 24×24 (cercle violet)."""
    s = _cercle(12, 12, 10, "#a855f7", CONTOUR, 2, fill_opacity=0.35) + _cercle(12, 12, 7, "none", "#e9d5ff", 1.5)
    s += _cercle(12, 12, 1.6, "#ffffff", None)
    return svg(24, 24, s)


def icone_bruit():
    """Indicateur de bruit 24×24 (ondes sonores)."""
    s = _cercle(5.5, 12, 2.6, JAUNE, CONTOUR, 1.8)
    for d in ("M9.5 7.5 Q13.5 12 9.5 16.5", "M13 5 Q18.5 12 13 19", "M16.5 2.5 Q23.5 12 16.5 21.5"):
        s += _chemin(d, "none", CONTOUR, 4) + _chemin(d, "none", JAUNE, 2)
    return svg(24, 24, s)


def fleche_degats():
    """Chevron rouge 48×48 pointant vers le haut (le sprite le fait tourner autour de (24, 24))."""
    s = _chemin("M24 3 L41 20 L34.5 25 L24 14.5 L13.5 25 L7 20 Z", "#ef4444", "#7f1d1d", 2.2, fill_opacity=0.9)
    s += _chemin("M24 8 L36 20 L34 21.5 L24 11.5 L14 21.5 L12 20 Z", "#fca5a5", None, opacity=0.7)
    return svg(48, 48, s)


def cercle_interaction(pourcent):
    """Cercle de progression 64×64 (arc jaune pour pourcent ∈ 0..100, borné ; non numérique = 0)."""
    p = max(0.0, min(100.0, _nombre(pourcent, 0)))
    s = _cercle(32, 32, 19, "#0f172a", None, opacity=0.45) + _cercle(32, 32, 24, "none", "#1e293b", 7, opacity=0.85)
    s += _cercle(32, 32, 28, "none", CONTOUR, 1.2) + _cercle(32, 32, 20, "none", CONTOUR, 1.2)
    if p >= 100:
        s += _cercle(32, 32, 24, "none", JAUNE, 6)
    elif p > 0:
        s += _chemin(_arc(32, 32, 24, -90, -90 + 3.6 * p), "none", JAUNE, 6)
    s += _cercle(32, 32, 3, "#ffffff", CONTOUR, 1.5)
    return svg(64, 64, s)


def barre(w, h, couleur, pourcent):
    """Barre w×h (w ≥ 8, h ≥ 6) : fond sombre, contour, remplissage `couleur` à `pourcent` %
    (borné 0..100 ; non numérique = 0)."""
    w, h = max(8, _entier(w, "largeur")), max(6, _entier(h, "hauteur"))
    p = max(0.0, min(100.0, _nombre(pourcent, 0)))
    rx = min(4, h / 3.0)
    s = _rect(1, 1, w - 2, h - 2, "#0b1021", rx, "#3b4a6b", 2, fill_opacity=0.85)
    if p > 0:
        lw = max(2.0, (w - 6) * p / 100.0)
        s += _rect(3, 3, lw, h - 6, couleur, max(1, rx - 1), None)
        s += _rect(3, 3, lw, (h - 6) / 2.0, "#ffffff", max(1, rx - 1), None, opacity=0.22)
    return svg(w, h, s)


def bouton(w, h, survol=False, couleur="#2b6cb0"):
    """Fond de bouton w×h (w, h ≥ 8 ; parallélogramme façon Fortnite), variante survol plus claire à bord blanc."""
    w, h = max(8, _entier(w, "largeur")), max(8, _entier(h, "hauteur"))
    k = h * 0.22

    def xg(t):
        return k + 1 - t * (k - 0.5)

    def xd(t):
        return w - 1.5 - t * (k - 0.5)

    def y(t):
        return 1.5 + t * (h - 3)
    pts = [(xg(0), y(0)), (xd(0), y(0)), (xd(1), y(1)), (xg(1), y(1))]
    fond = eclaircir(couleur, 0.25) if survol else couleur
    s = ""
    if survol:
        s += _poly(pts, "none", "#ffffff", 6, opacity=0.25)
    s += _poly(pts, fond, None)
    s += _poly([(xg(0.05) + 1, y(0.05)), (xd(0.05) - 1, y(0.05)), (xd(0.45) - 1, y(0.45)), (xg(0.45) + 1, y(0.45))], "#ffffff", None, opacity=0.18)
    s += _poly([(xg(0.78) + 1, y(0.78)), (xd(0.78) - 1, y(0.78)), (xd(0.95) - 1, y(0.95)), (xg(0.95) + 1, y(0.95))], "#000000", None, opacity=0.22)
    s += _poly(pts, "none", "#ffffff" if survol else CONTOUR, 2.5 if survol else 2)
    return svg(w, h, s)


def panneau(w, h):
    """Fond de panneau w×h (≥ 8) semi-transparent arrondi avec bordure."""
    w, h = max(8, _entier(w, "largeur")), max(8, _entier(h, "hauteur"))
    s = _rect(1.5, 1.5, w - 3, h - 3, "#0b1021", min(10, h / 3.0), "#3b4a6b", 2, fill_opacity=0.78)
    if w > 30:
        s += _ligne(12, 4.5, w - 12, 4.5, "#ffffff", 1, opacity=0.15)
    return svg(w, h, s)


def onglet_fond(actif):
    """Fond d'onglet 120×40 : actif (jaune) ou inactif (sombre)."""
    if actif:
        s = _rect(2, 2, 116, 36, JAUNE, 6, CONTOUR, 2) + _rect(8, 32, 104, 3, "#b45309", 1.5, None)
    else:
        s = _rect(2, 2, 116, 36, "#1e293b", 6, "#475569", 2, fill_opacity=0.75)
    return svg(120, 40, s)


# ---------------------------------------------------------------------------
#  Cartes (rendu de contrat.CARTE_ASCII)
# ---------------------------------------------------------------------------
def _runs_carte():
    """Segments horizontaux de murs : liste de (ligne écran r, x0, x1 inclus, valeur)."""
    runs = []
    for r, ligne in enumerate(C.CARTE_ASCII):
        x = 0
        while x < C.TAILLE:
            c = ligne[x]
            if c == ".":
                x += 1
                continue
            x0 = x
            while x + 1 < C.TAILLE and ligne[x + 1] == c:
                x += 1
            runs.append((r, x0, x, int(c)))
            x += 1
    return runs


def _carte(echelle, textes, grille, texture):
    e = max(1.0, _nombre(echelle, 10))
    T = C.TAILLE
    W = int(round(T * e))
    s = ""
    if texture:
        s += _defs('<pattern id="herbe" width="8" height="8" patternUnits="userSpaceOnUse"><rect width="8" height="8" fill="#3f8f3a"/>'
                   '<path d="M1 5 l2 -2 M5 2 l2 -2 M4 7.5 l1 -1" stroke="#357d30" stroke-width="1" fill="none"/></pattern>')
        s += _rect(0, 0, W, W, "url(#herbe)", 0, None)
        for (x, y, rx, ry) in ((8, 24, 5, 3), (22, 6, 6, 3), (14, 14, 4, 2.5), (26, 18, 3, 2), (4, 4, 3, 2)):
            s += _ellipse(x * e, (T - y) * e, rx * e, ry * e, "#4a9d44", None, opacity=0.5)
    else:
        s += _rect(0, 0, W, W, "#3f8f3a", 0, None)
    runs = _runs_carte()
    d = e * 0.25
    for r, x0, x1, v in runs:
        s += _rect(x0 * e + d, r * e + d, (x1 - x0 + 1) * e, e, "#000000", 0, None, opacity=0.35)
    sw = max(0.6, e * 0.1)
    for r, x0, x1, v in runs:
        fill, bord = COULEURS_CASES[v]
        s += _rect(x0 * e, r * e, (x1 - x0 + 1) * e, e, fill, 0, bord, sw)
        if e >= 6:
            s += _ligne(x0 * e + 1, r * e + 1, (x1 + 1) * e - 1, r * e + 1, eclaircir(fill, 0.35), 1)
    # tailles de police proportionnelles à l'échelle (11 px à 10 px/case), bornées pour rester lisibles
    k = min(1.0, e / 10.0)
    if grille:
        for i in range(1, 8):
            s += _ligne(i * W / 8.0, 0, i * W / 8.0, W, "#ffffff", 1, opacity=0.18)
            s += _ligne(0, i * W / 8.0, W, i * W / 8.0, "#ffffff", 1, opacity=0.18)
        tg = max(6.0, 9 * k)
        for i in range(8):
            s += _texte((i + 0.5) * W / 8.0, tg + 2, "ABCDEFGH"[i], tg, "#ffffff", "middle", True, "#0f172a", max(1.2, tg * 0.22), opacity=0.9)
            s += _texte(3, (i + 0.5) * W / 8.0 + tg * 0.38, str(i + 1), tg, "#ffffff", "start", True, "#0f172a", max(1.2, tg * 0.22), opacity=0.9)
    if textes:
        tl = max(6.5, 11 * k)
        for fr, en, x, y, r in C.LIEUX:
            demi = 0.3 * tl * len(fr) + 3            # demi-largeur estimée du libellé (gras ≈ 0,6 em par lettre)
            tx = min(max(x * e, demi), W - demi)     # garde le nom dans le cadre
            s += _texte(tx, (T - y) * e + tl * 0.36, fr, tl, "#ffffff", "middle", True, "#0f172a", max(1.5, tl * 0.27))
    s += _rect(1.5, 1.5, W - 3, W - 3, "none", 0, "#0f172a", 3)
    return svg(W, W, s)


def carte_complete(echelle=10):
    """Carte complète (TAILLE × TAILLE cases à `echelle` px/case, 320×320 par défaut) : sol texturé,
    murs colorés par matériau avec ombre, noms des lieux, quadrillage A–H / 1–8.
    Les polices suivent l'échelle (11 px à 10 px/case, 6,5 px minimum) et les noms restent dans le cadre."""
    return _carte(echelle, True, True, True)


def carte_minimap(echelle=3.4):
    """Minicarte (109×109 par défaut) : même rendu sans texte ni quadrillage."""
    return _carte(echelle, False, False, False)


# ---------------------------------------------------------------------------
#  Fonds d'écran 480×360
# ---------------------------------------------------------------------------
def _pseudo(graine):
    """Générateur pseudo-aléatoire déterministe (LCG) de flottants dans [0, 1[."""
    x = int(graine) & 0x7fffffff
    while True:
        x = (x * 1103515245 + 12345) & 0x7fffffff
        yield x / float(0x80000000)


def _etoiles(nb, graine, ymax=250):
    g = _pseudo(graine)
    s = ""
    for _ in range(nb):
        x, y, r, o = next(g) * 480, next(g) * ymax, 0.6 + next(g) * 1.2, 0.4 + next(g) * 0.6
        s += _cercle(x, y, r, "#ffffff", None, opacity=o)
    return s


def _nuage(x, y, k, couleur="#ffffff", opacite=0.9):
    return (_ellipse(x, y, 34 * k, 14 * k, couleur, None, opacity=opacite) + _ellipse(x - 18 * k, y + 2 * k, 20 * k, 11 * k, couleur, None, opacity=opacite)
            + _ellipse(x + 20 * k, y + 3 * k, 22 * k, 11 * k, couleur, None, opacity=opacite) + _ellipse(x + 2 * k, y - 9 * k, 20 * k, 13 * k, couleur, None, opacity=opacite))


def fond_ecran(variante):
    """Fond 480×360 : "connexion", "salon", "matchmaking", "chargement", "victoire", "defaite", "fin",
    "tempete", "ciel"."""
    v = str(variante).strip().lower()
    if v == "connexion":
        s = _defs(_degrade("ciel", [(0, "#070b1a"), (0.6, "#0f1f4d"), (1, "#1e3a8a")]))
        s += _rect(0, 0, 480, 360, "url(#ciel)", 0, None) + _etoiles(70, 7, 240)
        s += _ellipse(240, 300, 330, 80, "#3b82f6", None, opacity=0.22)
        s += _chemin("M400 42 A26 26 0 1 0 400 94 A20 20 0 1 1 400 42 Z", "#fef3c7", None, opacity=0.95)
        s += _rect(0, 282, 480, 78, "#0c2353", 0, None)
        s += _chemin("M40 300 Q100 232 160 262 Q195 198 250 240 Q290 188 335 250 Q385 226 440 300 Z", "#14532d", "#052e16", 2)
        s += _chemin("M110 300 Q150 262 190 282 Q240 244 300 276 Q340 256 380 300 Z", "#166534", None)
        for (x, y) in ((176, 280), (236, 270), (292, 278), (330, 286)):
            s += _cercle(x, y, 1.6, "#fde047", None, opacity=0.9)
        s += _ellipse(240, 316, 150, 8, "#ffffff", None, opacity=0.07)
    elif v == "salon":
        s = _defs(_degrade("fond", [(0, "#1e3a8a"), (0.55, "#4c1d95"), (1, "#701a75")], 0, 0, 1, 1),
                  _degrade("bas", [(0, "#0b1021"), (1, "#0b1021")]))
        s += _rect(0, 0, 480, 360, "url(#fond)", 0, None)
        for x0 in (-260, -120, 20, 160, 300):
            s += _poly([(x0, 0), (x0 + 60, 0), (x0 + 60 + 250, 360), (x0 + 250, 360)], "#ffffff", None, opacity=0.06)
        s += _cercle(400, 90, 130, "none", "#ffffff", 30, opacity=0.04) + _cercle(80, 320, 90, "none", "#ffffff", 20, opacity=0.04)
        s += _rect(0, 290, 480, 70, "#0b1021", 0, None, opacity=0.35)
    elif v == "chargement":
        s = _defs('<pattern id="raye" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M-6 6 L6 -6 M0 24 L24 0 M18 30 L30 18" stroke="#1e293b" stroke-width="7" fill="none"/></pattern>',
                  _radial("vignette", [(0, ("#000000", 0)), (0.7, ("#000000", 0.1)), (1, ("#000000", 0.6))], 0.5, 0.5, 0.75))
        s += _rect(0, 0, 480, 360, "#0b1021", 0, None) + _rect(0, 0, 480, 360, "url(#raye)", 0, None, opacity=0.7)
        s += _rect(0, 0, 480, 360, "url(#vignette)", 0, None)
    elif v == "victoire":
        s = _defs(_radial("sol", [(0, "#fff7cc"), (0.45, "#fbbf24"), (1, "#b45309")], 0.5, 0.5, 0.7))
        s += _rect(0, 0, 480, 360, "url(#sol)", 0, None)
        for i in range(0, 360, 30):
            a0, a1 = math.radians(i), math.radians(i + 15)
            s += _poly([(240, 180), (240 + 420 * math.cos(a0), 180 + 420 * math.sin(a0)), (240 + 420 * math.cos(a1), 180 + 420 * math.sin(a1))],
                       "#ffffff", None, opacity=0.16)
        g = _pseudo(42)
        couleurs = ["#ef4444", "#3b82f6", "#22c55e", "#ffffff", "#a855f7", "#22d3ee"]
        for i in range(60):
            x, y, a = next(g) * 480, next(g) * 360, next(g) * 180
            s += _rect(x, y, 7, 3.5, couleurs[i % 6], 0.5, None, opacity=0.85, transform="rotate(%s %s %s)" % (_n(a), _n(x), _n(y)))
    elif v == "defaite":
        s = _defs(_degrade("gris", [(0, "#475569"), (0.6, "#1e293b"), (1, "#0f172a")]))
        s += _rect(0, 0, 480, 360, "url(#gris)", 0, None)
        g = _pseudo(9)
        for _ in range(45):
            x, y, lg = next(g) * 500 - 10, next(g) * 360, 14 + next(g) * 22
            s += _ligne(x, y, x - lg * 0.25, y + lg, "#94a3b8", 1.2, opacity=0.3)
        s += _ellipse(240, 380, 330, 90, "#000000", None, opacity=0.45)
    elif v == "tempete":
        s = _defs(_degrade("violet", [(0, "#2e1065"), (0.5, "#5b21b6"), (1, "#2e1065")]))
        s += _rect(0, 0, 480, 360, "url(#violet)", 0, None)
        for r in (60, 120, 180, 240, 300):
            s += _ellipse(240, 180, r * 1.3, r, "none", "#a855f7", 10, opacity=0.14)
        for (x, k) in ((70, 1.1), (250, 1.4), (430, 1.0)):
            s += _nuage(x, 40, k, "#3b0764", 0.85)
        eclair = [(300, 40), (262, 140), (292, 136), (250, 250), (320, 120), (290, 124), (326, 40)]
        s += _poly(eclair, "none", "#e879f9", 14, opacity=0.25) + _poly(eclair, "#f5d0fe", "#c026d3", 2, opacity=0.95)
        s += _poly([(118, 90), (100, 140), (114, 138), (94, 190), (126, 130), (112, 132), (130, 90)], "#f5d0fe", "#c026d3", 1.5, opacity=0.7)
    elif v == "matchmaking":
        # indigo profond, radar concentrique et balayage : recherche de partie
        s = _defs(_degrade("fond", [(0, "#0b1021"), (0.6, "#1e1b4b"), (1, "#312e81")], 0, 0, 1, 1))
        s += _rect(0, 0, 480, 360, "url(#fond)", 0, None)
        for x0 in (-200, -40, 120, 280):
            s += _poly([(x0, 0), (x0 + 50, 0), (x0 + 50 + 250, 360), (x0 + 250, 360)], "#ffffff", None, opacity=0.04)
        cx, cy = 300, 200
        for r in (50, 100, 150, 200, 260):
            s += _cercle(cx, cy, r, "none", "#818cf8", 1.5, opacity=0.22)
        s += _ligne(cx - 270, cy, cx + 270, cy, "#818cf8", 1, opacity=0.18) + _ligne(cx, cy - 270, cx, cy + 270, "#818cf8", 1, opacity=0.18)
        s += _chemin("M%s %s L%s %s A260 260 0 0 1 %s %s Z" % (cx, cy, cx + 260, cy, _n(cx + 260 * math.cos(math.radians(-40))),
                                                               _n(cy + 260 * math.sin(math.radians(-40)))), "#a5b4fc", None, opacity=0.14)
        s += _ligne(cx, cy, cx + 260, cy, "#c7d2fe", 2, opacity=0.6)
        for (x, y, r) in ((380, 150, 4), (210, 120, 3), (250, 260, 3.5), (420, 250, 3), (140, 210, 2.5)):
            s += _cercle(x, y, r + 4, "#22d3ee", None, opacity=0.25) + _cercle(x, y, r, "#67e8f9", None, opacity=0.9)
        s += _cercle(cx, cy, 5, "#e0e7ff", None, opacity=0.9)
    elif v == "fin":
        # crépuscule gris-bleu avec horizon lumineux : écran de fin de partie
        s = _defs(_degrade("fond", [(0, "#111827"), (0.55, "#1f2937"), (1, "#374151")]),
                  _radial("halo", [(0, ("#fbbf24", 0.35)), (0.5, ("#f59e0b", 0.12)), (1, ("#f59e0b", 0))], 0.5, 1.0, 0.6))
        s += _rect(0, 0, 480, 360, "url(#fond)", 0, None) + _etoiles(40, 3, 160)
        s += _rect(0, 0, 480, 360, "url(#halo)", 0, None)
        s += _chemin("M0 300 Q60 262 120 282 Q180 236 250 270 Q320 240 380 272 Q430 250 480 286 V360 H0 Z", "#0b1021", None, opacity=0.9)
        s += _ligne(0, 300, 480, 300, "#fbbf24", 1.5, opacity=0.25)
    elif v == "ciel":
        s = _defs(_degrade("ciel", [(0, "#1d8ad8"), (0.55, "#7dd3fc"), (1, "#e0f2fe")]))
        s += _rect(0, 0, 480, 360, "url(#ciel)", 0, None)
        s += _cercle(400, 62, 44, "#fde68a", None, opacity=0.35) + _cercle(400, 62, 28, "#fef3c7", None)
        for (x, y, k, o) in ((80, 90, 1.1, 0.92), (260, 150, 0.8, 0.85), (420, 190, 1.0, 0.9), (150, 260, 1.3, 0.95), (360, 300, 0.9, 0.9)):
            s += _nuage(x, y, k, "#ffffff", o)
    else:
        raise KeyError("fond inconnu : %r (connexion, salon, matchmaking, chargement, victoire, defaite, fin, tempete, ciel)" % variante)
    return svg(480, 360, s)


# ---------------------------------------------------------------------------
#  Logo 300×80
# ---------------------------------------------------------------------------
def logo():
    """Titre « ROYALE 3D » : lettres épaisses jaunes inclinées, contour bleu, ombre."""
    s = _defs(_degrade("or", [(0, "#fff9c4"), (0.45, "#fde047"), (1, "#f59e0b")]))
    commun = dict(gras=True, italique=True, ancre="middle")
    s += _texte(154, 62, "ROYALE 3D", 48, "#0f172a", contour="#0f172a", sw=12, letter_spacing=1, **commun)
    s += _texte(150, 58, "ROYALE 3D", 48, "url(#or)", contour="#1d4ed8", sw=7, letter_spacing=1, **commun)
    s += _texte(150, 58, "ROYALE 3D", 48, "url(#or)", letter_spacing=1, **commun)
    return svg(300, 80, s)
