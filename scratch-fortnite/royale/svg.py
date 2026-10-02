# -*- coding: utf-8 -*-
"""
Fabrique de costumes SVG : personnages, armes, coffres, viseurs, bannières, aplats.
Les icônes d'interface (inventaire, badges, skins, pioches, planeurs, sprays,
émotes, bus, parachute, boussole) sont dans svg_ui.py.

Toute fonction renvoie une chaîne SVG complète (racine <svg ... viewBox>).
Le centre de rotation du costume est passé à part lors de l'enregistrement.
"""
from xml.sax.saxutils import escape


def echapper(texte):
    """Échappe &, <, > pour insertion dans un SVG."""
    return escape(str(texte))


def svg(w, h, contenu):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (w, h, w, h, contenu))


def svg_vide():
    return svg(4, 4, '<rect x="0" y="0" width="4" height="4" fill="none" stroke="none"/>')


def svg_texte(texte, couleur, taille_police=34, fond=None, sous_titre=None):
    w, h = 340, 100
    s = ""
    if fond:
        s += '<rect x="0" y="0" width="%d" height="%d" rx="14" fill="%s" fill-opacity="0.75"/>' % (w, h, fond)
    s += ('<text x="170" y="%d" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="%d" '
          'fill="%s" stroke="#1a1a2e" stroke-width="2" paint-order="stroke">%s</text>'
          % (50 if sous_titre else 62, taille_police, couleur, texte))
    if sous_titre:
        s += ('<text x="170" y="82" text-anchor="middle" font-family="Sans Serif" font-size="16" '
              'fill="#ffffff" stroke="#1a1a2e" stroke-width="1.5" paint-order="stroke">%s</text>' % sous_titre)
    return svg(w, h, s)


def svg_personnage(couleur_tenue="#3b82f6"):
    # Personnage façon battle royale : tête, torse, sac à dos, jambes (60 x 100)
    return svg(60, 100, """
<rect x="12" y="38" width="36" height="34" rx="6" fill="%s" stroke="#111" stroke-width="2"/>
<rect x="4" y="42" width="10" height="26" rx="3" fill="#6b4f2a" stroke="#111" stroke-width="2"/>
<rect x="46" y="42" width="10" height="26" rx="3" fill="%s" stroke="#111" stroke-width="2"/>
<rect x="16" y="72" width="12" height="26" rx="3" fill="#2a2a3a" stroke="#111" stroke-width="2"/>
<rect x="32" y="72" width="12" height="26" rx="3" fill="#2a2a3a" stroke="#111" stroke-width="2"/>
<circle cx="30" cy="22" r="15" fill="#f1c27d" stroke="#111" stroke-width="2"/>
<path d="M15 20 Q30 0 45 20 Z" fill="#222" />
<rect x="20" y="20" width="20" height="6" rx="3" fill="#111"/>
<rect x="46" y="54" width="14" height="6" rx="2" fill="#444" stroke="#111" stroke-width="1"/>
""" % (couleur_tenue, couleur_tenue))


def svg_coffre():
    return svg(60, 50, """
<rect x="3" y="18" width="54" height="30" rx="4" fill="#b8860b" stroke="#3b2a00" stroke-width="3"/>
<path d="M3 20 Q30 0 57 20 Z" fill="#daa520" stroke="#3b2a00" stroke-width="3"/>
<rect x="3" y="18" width="54" height="6" fill="#8b6508"/>
<rect x="25" y="20" width="10" height="12" rx="2" fill="#ffd700" stroke="#3b2a00" stroke-width="2"/>
<circle cx="30" cy="30" r="2" fill="#3b2a00"/>
""")


def svg_viseur(touche=False):
    c = "#ff3b3b" if touche else "#ffffff"
    extra = ('<path d="M12 12 L22 22 M48 12 L38 22 M12 48 L22 38 M48 48 L38 38" stroke="#ff3b3b" stroke-width="3"/>'
             if touche else "")
    return svg(60, 60, """
<circle cx="30" cy="30" r="2.5" fill="%s"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="%s" stroke-width="3" stroke-linecap="round"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="#000" stroke-opacity="0.4" stroke-width="5" stroke-linecap="round"/>
<path d="M30 8 L30 20 M30 40 L30 52 M8 30 L20 30 M40 30 L52 30" stroke="%s" stroke-width="2.5" stroke-linecap="round"/>
%s""" % (c, c, c, extra))


def svg_lunette():
    return svg(480, 360, """
<defs><mask id="m"><rect width="480" height="360" fill="#fff"/><circle cx="240" cy="180" r="150" fill="#000"/></mask></defs>
<rect width="480" height="360" fill="#000" mask="url(#m)"/>
<circle cx="240" cy="180" r="150" fill="none" stroke="#111" stroke-width="8"/>
<path d="M240 30 L240 330 M90 180 L390 180" stroke="#000" stroke-width="2"/>
<circle cx="240" cy="180" r="40" fill="none" stroke="#000" stroke-width="1.5"/>
""")


def svg_arme(type_arme):
    if type_arme == "pistolet":
        corps = """
<rect x="60" y="40" width="110" height="34" rx="8" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="150" y="48" width="60" height="16" rx="4" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="70" y="70" width="34" height="60" rx="6" transform="rotate(12 87 100)" fill="#5a4632" stroke="#111" stroke-width="3"/>
<rect x="104" y="72" width="14" height="22" rx="3" fill="#222"/>
<rect x="90" y="40" width="8" height="40" fill="#1a1a1a"/>"""
    elif type_arme == "pompe":
        corps = """
<rect x="20" y="60" width="90" height="40" rx="10" fill="#6b4a2b" stroke="#111" stroke-width="3"/>
<rect x="100" y="44" width="120" height="32" rx="6" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="140" y="76" width="60" height="22" rx="6" fill="#8a5c33" stroke="#111" stroke-width="3"/>
<rect x="200" y="50" width="40" height="18" rx="4" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="110" y="96" width="16" height="22" rx="3" fill="#222"/>"""
    else:
        corps = """
<rect x="10" y="66" width="100" height="36" rx="10" fill="#3a5a2a" stroke="#111" stroke-width="3"/>
<rect x="100" y="52" width="150" height="26" rx="6" fill="#2f2f38" stroke="#111" stroke-width="3"/>
<rect x="110" y="30" width="80" height="20" rx="8" fill="#222" stroke="#111" stroke-width="3"/>
<circle cx="112" cy="40" r="8" fill="#66ccff" stroke="#111" stroke-width="2"/>
<rect x="250" y="56" width="20" height="18" rx="3" fill="#44444f" stroke="#111" stroke-width="3"/>
<rect x="118" y="92" width="14" height="24" rx="3" fill="#222"/>
<rect x="150" y="80" width="18" height="34" rx="3" fill="#1a1a1a"/>"""
    main = '<ellipse cx="80" cy="120" rx="34" ry="24" fill="#f1c27d" stroke="#111" stroke-width="3"/>'
    return svg(280, 150, corps + main)


def svg_flash():
    return svg(80, 80, """
<polygon points="40,4 48,28 72,20 56,40 76,52 50,50 46,76 36,52 10,62 26,42 6,30 32,30" fill="#ffd166" stroke="#ff8800" stroke-width="2"/>
<circle cx="40" cy="40" r="10" fill="#fff6c4"/>""")


def svg_plein(couleur):
    return svg(480, 360, '<rect width="480" height="360" fill="%s"/>' % couleur)


def svg_scene():
    return svg(480, 360, '<rect width="480" height="360" fill="#0b1021"/>')


def svg_rect(w, h, couleur, rayon=0, opacite=1.0, bord=None, epaisseur=0):
    """Rectangle plein (fond de panneau, bouton, barre)."""
    stroke = ' stroke="%s" stroke-width="%s"' % (bord, epaisseur) if bord else ""
    return svg(w, h, '<rect x="%s" y="%s" width="%s" height="%s" rx="%s" fill="%s" fill-opacity="%s"%s/>'
               % (epaisseur / 2, epaisseur / 2, w - epaisseur, h - epaisseur, rayon, couleur, opacite, stroke))


def svg_cercle(d, couleur, opacite=1.0, bord=None, epaisseur=0):
    stroke = ' stroke="%s" stroke-width="%s"' % (bord, epaisseur) if bord else ""
    return svg(d, d, '<circle cx="%s" cy="%s" r="%s" fill="%s" fill-opacity="%s"%s/>'
               % (d / 2, d / 2, d / 2 - epaisseur / 2, couleur, opacite, stroke))
