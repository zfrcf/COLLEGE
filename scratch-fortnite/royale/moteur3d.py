# -*- coding: utf-8 -*-
"""
Moteur de rendu 3D (sprite Moteur3D) et panneaux 3D (Ennemi, Coffre, Marqueur, Balise,
CarteRedeploiement, Spray).

- Raycasting DDA sur la grille `Carte`, `colonnes` colonnes (40/80/120 selon param_qualite),
  ciel/sol, murs ombrés par distance et matériau, mur de tempête (intersection rayon/cercle),
  minicarte circulaire (en haut à droite) avec zone, prochaine zone, joueurs, coéquipiers, pings.
- Les panneaux se placent par projection caméra et sont masqués par les murs grâce à `Profondeur`.
- Ne rend que si `ecran` ∈ contrat.ECRANS_RENDU_3D ; les autres écrans sont dessinés par leurs
  propriétaires (Menus, Partie). Les panneaux (sprites, donc au-dessus du stylo) se cachent dès qu'une
  `superposition` est ouverte et sur les écrans « pause » / « fin », où Menus dessine ses panneaux au stylo.
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S

try:
    from . import svg_ui as UI
except Exception:  # module de la phase A pas encore disponible
    UI = None

V = Var
A = Arg

# Minicarte : cercle de rayon 54 px centré en (190, 125)
MM_CX, MM_CY, MM_R = 190, 125, 54
MM_ECH = (2 * MM_R) / C.TAILLE
MM_OX, MM_OY = MM_CX - MM_R, MM_CY - MM_R


def mm_x(x): return add(MM_OX, mul(x, MM_ECH))
def mm_y(y): return add(MM_OY, mul(y, MM_ECH))


def est_ecran_rendu():
    cond = eq(V("ecran"), C.ECRANS_RENDU_3D[0])
    for e in C.ECRANS_RENDU_3D[1:]:
        cond = ou(cond, eq(V("ecran"), e))
    return cond


def _costume_personnage(skin, pose):
    if UI and hasattr(UI, "personnage"):
        try:
            return UI.personnage(skin, pose)
        except Exception:
            pass
    return S.svg_personnage()


def construire(P):
    construire_moteur(P)
    construire_panneaux(P)


# ---------------------------------------------------------------------------
#  Sprite Moteur3D
# ---------------------------------------------------------------------------
def construire_moteur(P):
    M = Cible(P, "Moteur3D")
    M.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    M.visible = False
    M.layer = C.CALQUES["Moteur3D"]
    for v in ["i", "camX", "rayX", "rayY", "mapX", "mapY", "deltaX", "deltaY", "stepX", "stepY", "sideX", "sideY",
              "hit", "side", "perp", "h", "sx", "pas", "a", "b", "c", "disc", "t", "s", "cosD", "sinD",
              "planeX", "planeY", "lum", "ang", "bx", "by", "k", "largeurCol", "teinteZone", "teinteCiel",
              "ex", "ey", "n",
              # rendu « spectaculaire » : horizon secoué, heure de la manche, lumière, couleurs des 3 bandes du ciel,
              # texture des murs, soleil / nuages, tempête
              "hz", "u", "t2", "lumG", "nuit", "cH1", "cS1", "cB1", "cH2", "cS2", "cB2", "cH3", "cS3", "cB3",
              "wallX", "tex", "j", "rel", "amp", "secX", "secY", "solX", "solAlt", "hc", "hx", "hy", "y1", "y2"]:
        M.var(v, 0)
    # Globales privées lues par les panneaux 3D et les superpositions (overlays.py)
    for g, val in [("m3d_secX", 0), ("m3d_secY", 0),          # décalage de secousse d'écran (px) de l'image courante
                   ("m3d_lumiere", 1), ("m3d_heure", 0), ("m3d_nuit", 0),   # facteur de lumière (0,4..1,3), heure (0..1), nuit (0..1)
                   ("m3d_flashFin", 0), ("m3d_eclairFin", 0), ("m3d_prochainEclair", 0), ("m3d_eclairX", 0)]:
        P.stage.var(g, val)

    # Couleurs selon daltonisme : teinte de la zone (0-100) — normal violet, proto/deutér. cyan, trit. orange
    M.proc("palette", [], [
        setv("teinteZone", 80),
        si(ou(eq(V("param_daltonisme"), 1), eq(V("param_daltonisme"), 2)), [setv("teinteZone", 52)]),
        si(eq(V("param_daltonisme"), 3), [setv("teinteZone", 12)]),
    ])

    # ---- cycle jour / nuit sur la manche ---------------------------------------------------------
    # u = tempsManche / DUREE_MANCHE (0..1) : aube → jour → crépuscule orangé → nuit bleutée (dernière zone).
    # Chaque étape fixe les 3 bandes du ciel (teinte, saturation, luminosité) et le facteur de lumière lumG.
    # Les teintes sont écrites hors 0..100 quand il faut passer par le violet (le stylo replie modulo 100).
    AUBE = dict(H1=64, S1=55, B1=60, H2=92, S2=35, B2=85, H3=10, S3=55, B3=98, L=0.8)
    JOUR_A = dict(H1=62, S1=65, B1=85, H2=58, S2=50, B2=95, H3=-45, S3=25, B3=100, L=1.0)   # H3 = 55 (via le violet)
    JOUR = dict(JOUR_A, H3=55)
    CREP = dict(H1=70, S1=60, B1=55, H2=95, S2=55, B2=85, H3=108, S3=85, B3=98, L=0.72)       # H3 = 8 (orange)
    CREP_D = dict(CREP, H3=8)
    NUIT = dict(H1=66, S1=70, B1=14, H2=64, S2=65, B2=24, H3=-38, S3=50, B3=38, L=0.4)       # H3 = 62

    def lerp(a, b, t):
        return a if a == b else add(a, mul(b - a, t))

    def segment(u0, u1, debut, fin):
        corps = [setv("t2", div(sub(V("u"), u0), u1 - u0))]
        for cle in ["H1", "S1", "B1", "H2", "S2", "B2", "H3", "S3", "B3"]:
            corps.append(setv("c" + cle, lerp(debut[cle], fin[cle], V("t2"))))
        corps.append(setv("lumG", lerp(debut["L"], fin["L"], V("t2"))))
        return corps

    M.proc("lumiere", [], [
        setv("u", div(V("tempsManche"), C.DUREE_MANCHE)),
        si(lt(V("u"), 0), [setv("u", 0)]), si(gt(V("u"), 1), [setv("u", 1)]),
        si(et(ge(V("phase"), 6), lt(V("phase"), 8)), [setv("u", 1)]),          # dernière zone : nuit
        si(lt(V("u"), 0.2), segment(0, 0.2, AUBE, JOUR_A), [
            si(lt(V("u"), 0.6), segment(0.2, 0.6, JOUR, JOUR), [
                si(lt(V("u"), 0.8), segment(0.6, 0.8, JOUR, CREP), segment(0.8, 1, CREP_D, NUIT)),
            ]),
        ]),
        setv("nuit", 0), si(gt(V("u"), 0.8), [setv("nuit", div(sub(V("u"), 0.8), 0.2))]),
        # hors zone : ciel violet sombre, lumière réduite
        si(eq(V("horsZone"), 1), [
            setv("cH1", V("teinteZone")), setv("cS1", 65), setv("cB1", 26),
            setv("cH2", V("teinteZone")), setv("cS2", 55), setv("cB2", 38),
            setv("cH3", V("teinteZone")), setv("cS3", 40), setv("cB3", 52),
            setv("lumG", mul(V("lumG"), 0.7)),
        ]),
        # éclair : une image de ciel blanc, murs sur-éclairés
        si(gt(V("m3d_flashFin"), chrono()), [
            setv("cS1", 5), setv("cS2", 5), setv("cS3", 5), setv("cB1", 100), setv("cB2", 100), setv("cB3", 100),
            setv("lumG", 1.3),
        ]),
        setv("m3d_lumiere", V("lumG")), setv("m3d_heure", V("u")), setv("m3d_nuit", V("nuit")),
    ])

    # ---- secousse d'écran : bruit aléatoire d'amplitude secousseForce × (secousse − chrono) / 0,3 ---------------
    M.proc("secousse", [], [
        setv("secX", 0), setv("secY", 0),
        si(gt(V("secousse"), chrono()), [
            setv("amp", mul(V("secousseForce"), div(sub(V("secousse"), chrono()), 0.3))),
            si(gt(V("amp"), V("secousseForce")), [setv("amp", V("secousseForce"))]),
            setv("secX", hasard(mul(V("amp"), -1), V("amp"))), setv("secY", hasard(mul(V("amp"), -1), V("amp"))),
        ]),
        setv("m3d_secX", V("secX")), setv("m3d_secY", V("secY")),
        setv("hz", add(V("horizon"), V("secY"))),
    ])

    # ---- éclairs de tempête (phase ≥ 4) : toutes les 4 à 9 s, un flash blanc (1 image) puis un éclair 0,35 s ------
    M.proc("eclairs", [], [
        si(et3(ge(V("phase"), 4), lt(V("phase"), 8), eq(V("param_performance"), 0)), [
            si(gt(chrono(), V("m3d_prochainEclair")), [
                setv("m3d_prochainEclair", add(chrono(), hasard(4, 9))),
                setv("m3d_flashFin", add(chrono(), 0.05)), setv("m3d_eclairFin", add(chrono(), 0.35)),
                setv("m3d_eclairX", hasard(-200, 200)),
            ]),
        ]),
    ])

    def point(x, y):
        return ligne(x, y, x, y)

    def bande_h(y, epaisseur):
        return [taille_stylo(epaisseur), ligne(-250, y, 250, y)]

    # soleil / lune (position selon dir et l'heure) et 3 nuages qui défilent (parallaxe : vitesses différentes)
    M.proc("soleil et nuages", [], [
        setv("rel", sub(mod(add(sub(add(20, mul(V("u"), 140)), V("dir")), 540), 360), 180)),
        si(lt(absv(V("rel")), 70), [
            setv("solX", add(mul(-240, div(mathop("tan", V("rel")), V("plan"))), V("secX"))),
            si(lt(V("nuit"), 0.5), [
                setv("solAlt", add(V("hz"), add(10, mul(160, mul(sin(mul(V("u"), 180)), sin(mul(V("u"), 180))))))),
                setv("t2", add(5, mul(10, sin(mul(V("u"), 180))))),
                couleur_hsbt(V("t2"), 85, 100, 84), taille_stylo(120), point(V("solX"), V("solAlt")),
                couleur_hsbt(V("t2"), 70, 100, 55), taille_stylo(62), point(V("solX"), V("solAlt")),
                couleur_hsbt(V("t2"), 40, 100, 0), taille_stylo(34), point(V("solX"), V("solAlt")),
            ], [
                setv("solAlt", add(V("hz"), 110)),
                couleur_hsbt(60, 20, 95, 72), taille_stylo(48), point(V("solX"), V("solAlt")),
                couleur_hsbt(60, 8, 98, 0), taille_stylo(24), point(V("solX"), V("solAlt")),
            ]),
        ]),
    ] + sum([[
        setv("rel", sub(mod(add(sub(add(k * 115, mul(chrono(), 1.0 + 0.6 * k)), V("dir")), 540), 360), 180)),
        si(lt(absv(V("rel")), 65), [
            setv("solX", add(mul(-240, div(mathop("tan", V("rel")), V("plan"))), V("secX"))),
            setv("solAlt", add(V("hz"), 40 + 26 * k)),
            couleur_hsbt(60, 12, mul(100, V("lumG")), 42), taille_stylo(22 + 4 * k),
            ligne(sub(V("solX"), 20 + 4 * k), V("solAlt"), add(V("solX"), 20 + 4 * k), V("solAlt")),
            taille_stylo(15 + 3 * k),
            ligne(sub(V("solX"), 2), add(V("solAlt"), 9), add(V("solX"), 30 + 3 * k), add(V("solAlt"), 9)),
        ]),
    ] for k in (1, 2, 3)], []))

    M.proc("ciel et sol", [], [
        effacer(),
        # ciel : 3 bandes (haute 45 %, moyenne 30 %, basse 25 %) aux couleurs de l'heure
        setv("hc", sub(180, V("hz"))),
        couleur_hsbt(V("cH1"), V("cS1"), V("cB1")), bande_h(sub(180, mul(V("hc"), 0.225)), add(mul(V("hc"), 0.45), 2)),
        couleur_hsbt(V("cH2"), V("cS2"), V("cB2")), bande_h(sub(180, mul(V("hc"), 0.6)), add(mul(V("hc"), 0.30), 2)),
        couleur_hsbt(V("cH3"), V("cS3"), V("cB3")), bande_h(add(V("hz"), mul(V("hc"), 0.125)), add(mul(V("hc"), 0.25), 2)),
        si(eq(V("param_performance"), 0), [appel("soleil et nuages")]),
        # éclair : ligne brisée blanche du haut de l'écran vers l'horizon (nouveau tracé à chaque image → scintille)
        si(gt(V("m3d_eclairFin"), chrono()), [
            setv("bx", V("m3d_eclairX")), setv("by", 180), setv("t", div(sub(170, V("hz")), 6)),
            couleur_hsbt(62, 30, 100, 55), taille_stylo(16), stylo_haut(), aller(V("bx"), V("by")), stylo_bas(),
            repeter(3, [changev("bx", hasard(-22, 22)), changev("by", mul(V("t"), -2)), aller(V("bx"), V("by"))]),
            stylo_haut(), setv("bx", V("m3d_eclairX")), setv("by", 180),
            couleur_hsbt(62, 5, 100, 0), taille_stylo(3.5), aller(V("bx"), V("by")), stylo_bas(),
            repeter(6, [changev("bx", hasard(-16, 16)), changev("by", mul(V("t"), -1)), aller(V("bx"), V("by"))]),
            stylo_haut(),
            # petite branche latérale
            ligne(V("bx"), add(V("by"), mul(V("t"), 2.5)), add(V("bx"), hasard(-40, 40)), add(V("by"), mul(V("t"), 1.2))),
        ]),
        # sol : 3 bandes (lointain sombre → proche clair) éclairées par lumG
        setv("hc", add(V("hz"), 180)),
        couleur_hsbt(31, 42, mul(34, V("lumG"))), bande_h(sub(V("hz"), mul(V("hc"), 0.1)), add(mul(V("hc"), 0.2), 2)),
        couleur_hsbt(31, 48, mul(46, V("lumG"))), bande_h(sub(V("hz"), mul(V("hc"), 0.375)), add(mul(V("hc"), 0.35), 2)),
        couleur_hsbt(31, 52, mul(58, V("lumG"))), bande_h(sub(V("hz"), mul(V("hc"), 0.775)), add(mul(V("hc"), 0.45), 2)),
        si(eq(V("param_performance"), 0), [
            # brume à l'horizon : bande très claire semi-transparente
            couleur_hsbt(V("cH3"), 20, 96, 55), bande_h(sub(V("hz"), 3), 12),
            # qualité épique : fines lignes de gazon en perspective
            si(eq(V("param_qualite"), 3), [couleur_hsbt(33, 45, mul(28, V("lumG")), 35), taille_stylo(1.5)] + sum(
                [ligne(-250, sub(V("hz"), mul(V("hc"), f)), 250, sub(V("hz"), mul(V("hc"), f))) for f in (0.07, 0.12, 0.19, 0.29, 0.43, 0.63)], [])),
        ]),
    ])

    M.proc("colonne", [], [
        setv("camX", add(div(mul(V("i"), 2), V("colonnes")), add(-1, div(1, V("colonnes"))))),
        setv("rayX", add(V("cosD"), mul(V("planeX"), V("camX")))),
        setv("rayY", add(V("sinD"), mul(V("planeY"), V("camX")))),
        setv("mapX", floor(V("px"))), setv("mapY", floor(V("py"))),
        setv("deltaX", absv(div(1, V("rayX")))), setv("deltaY", absv(div(1, V("rayY")))),
        si(lt(V("rayX"), 0), [setv("stepX", -1), setv("sideX", mul(sub(V("px"), V("mapX")), V("deltaX")))],
           [setv("stepX", 1), setv("sideX", mul(sub(add(V("mapX"), 1), V("px")), V("deltaX")))]),
        si(lt(V("rayY"), 0), [setv("stepY", -1), setv("sideY", mul(sub(V("py"), V("mapY")), V("deltaY")))],
           [setv("stepY", 1), setv("sideY", mul(sub(add(V("mapY"), 1), V("py")), V("deltaY")))]),
        setv("hit", 0), setv("pas", 0),
        repeter_jusqua(ou(gt(V("hit"), 0), gt(V("pas"), 64)), [
            si(lt(V("sideX"), V("sideY")), [
                changev("sideX", V("deltaX")), changev("mapX", V("stepX")), setv("side", 0),
            ], [
                changev("sideY", V("deltaY")), changev("mapY", V("stepY")), setv("side", 1),
            ]),
            setv("hit", item("Carte", add(mul(V("mapY"), C.TAILLE), add(V("mapX"), 1)))),
            changev("pas", 1),
        ]),
        si(eq(V("side"), 0), [setv("perp", sub(V("sideX"), V("deltaX")))], [setv("perp", sub(V("sideY"), V("deltaY")))]),
        si(lt(V("perp"), 0.05), [setv("perp", 0.05)]),
        si(gt(V("pas"), 64), [setv("perp", 60)]),
        remplacer("Profondeur", add(V("i"), 1), V("perp")),
        setv("h", div(320, V("perp"))),
        si(gt(V("h"), 900), [setv("h", 900)]),
        setv("lum", sub(100, mul(V("perp"), 2.6))),
        si(lt(V("lum"), 28), [setv("lum", 28)]),
        si(eq(V("side"), 1), [setv("lum", mul(V("lum"), 0.72))]),
        setv("lum", mul(V("lum"), V("lumG"))),
        setv("sx", add(add(-240, mul(add(V("i"), 0.5), V("largeurCol"))), V("secX"))),
        si(lt(V("perp"), 59), [
            # texture : de près seulement, en qualité ≥ 2 et hors mode performance (sinon une seule ligne)
            setv("tex", 0),
            si(et4(lt(V("perp"), 14), gt(V("h"), 16), gt(V("param_qualite"), 1), eq(V("param_performance"), 0)), [setv("tex", 1)]),
            setv("y1", add(V("hz"), div(V("h"), 2))), setv("y2", sub(V("hz"), div(V("h"), 2))),
            si(eq(V("tex"), 1), [
                # coordonnée de texture : fraction de la position d'impact le long du mur
                si(eq(V("side"), 0), [setv("wallX", add(V("py"), mul(V("perp"), V("rayY"))))],
                   [setv("wallX", add(V("px"), mul(V("perp"), V("rayX"))))]),
                setv("wallX", sub(V("wallX"), floor(V("wallX")))),
            ]),
            si(eq(V("hit"), 2), [appel("mur bois")], [
                si(eq(V("hit"), 3), [appel("mur brique")], [
                    si(eq(V("hit"), 4), [appel("mur metal")], [appel("mur beton")]),
                ]),
            ]),
        ]),
        # mur de tempête (désactivé en mode performance) : transparence qui pulse, stries verticales qui défilent
        si(eq(V("param_performance"), 0), [
            setv("bx", sub(V("px"), V("zoneX"))), setv("by", sub(V("py"), V("zoneY"))),
            setv("a", add(mul(V("rayX"), V("rayX")), mul(V("rayY"), V("rayY")))),
            setv("b", mul(2, add(mul(V("rayX"), V("bx")), mul(V("rayY"), V("by"))))),
            setv("c", sub(add(mul(V("bx"), V("bx")), mul(V("by"), V("by"))), mul(V("zoneR"), V("zoneR")))),
            setv("disc", sub(mul(V("b"), V("b")), mul(4, mul(V("a"), V("c"))))),
            si(gt(V("disc"), 0), [
                setv("s", sqrt(V("disc"))),
                setv("t", div(sub(mul(V("b"), -1), V("s")), mul(2, V("a")))),
                si(le(V("t"), 0.1), [setv("t", div(add(mul(V("b"), -1), V("s")), mul(2, V("a"))))]),
                si(et(gt(V("t"), 0.1), lt(V("t"), V("perp"))), [
                    setv("h", div(320, V("t"))), si(gt(V("h"), 900), [setv("h", 900)]),
                    setv("hx", add(add(V("px"), mul(V("t"), V("rayX"))), add(V("py"), mul(V("t"), V("rayY"))))),
                    setv("j", add(mul(V("hx"), 1.5), mul(chrono(), 0.7))), setv("j", sub(V("j"), floor(V("j")))),
                    setv("b", 68), si(lt(V("j"), 0.5), [setv("b", 90)]),
                    couleur_hsbt(V("teinteZone"), 75, V("b"), add(48, mul(12, sin(add(mul(chrono(), 200), mul(V("i"), 11)))))),
                    ligne(V("sx"), add(V("hz"), div(V("h"), 2)), V("sx"), sub(V("hz"), div(V("h"), 2))),
                ]),
            ]),
        ]),
    ])

    # ---- murs texturés (≤ 3 lignes par colonne ; 1 seule si tex = 0) ----------------------------------------
    # béton : joints horizontaux sombres tous les quarts de hauteur (traits fins)
    M.proc("mur beton", [], [
        couleur_hsbt(0, 0, V("lum")), ligne(V("sx"), V("y1"), V("sx"), V("y2")),
        si(eq(V("tex"), 1), [
            couleur_hsbt(0, 0, mul(V("lum"), 0.7)), taille_stylo(2),
            ligne(sub(V("sx"), div(V("largeurCol"), 2)), add(V("hz"), div(V("h"), 4)), add(V("sx"), div(V("largeurCol"), 2)), add(V("hz"), div(V("h"), 4))),
            ligne(sub(V("sx"), div(V("largeurCol"), 2)), sub(V("hz"), div(V("h"), 4)), add(V("sx"), div(V("largeurCol"), 2)), sub(V("hz"), div(V("h"), 4))),
            taille_stylo(add(V("largeurCol"), 1)),
        ]),
    ])
    # bois : planches verticales (teinte alternée selon wallX, rainure sombre entre deux planches)
    M.proc("mur bois", [], [
        si(eq(V("tex"), 1), [
            setv("j", mul(V("wallX"), 5)),
            si(eq(mod(floor(V("j")), 2), 0), [setv("lum", mul(V("lum"), 0.84))]),
            si(lt(sub(V("j"), floor(V("j"))), 0.1), [setv("lum", mul(V("lum"), 0.62))]),
        ]),
        couleur_hsbt(8, 70, V("lum")), ligne(V("sx"), V("y1"), V("sx"), V("y2")),
    ])
    # brique : 4 rangées ; joints verticaux clairs décalés d'une demi-brique une rangée sur deux
    M.proc("mur brique", [], [
        couleur_hsbt(2, 60, V("lum")), ligne(V("sx"), V("y1"), V("sx"), V("y2")),
        si(eq(V("tex"), 1), [
            setv("j", mul(V("wallX"), 4)), setv("j", sub(V("j"), floor(V("j")))),
            si(lt(V("j"), 0.13), [
                couleur_hsbt(4, 12, add(V("lum"), 12)),
                ligne(V("sx"), V("y1"), V("sx"), sub(V("y1"), div(V("h"), 4))),
                ligne(V("sx"), V("hz"), V("sx"), sub(V("hz"), div(V("h"), 4))),
            ], [
                si(et(gt(V("j"), 0.5), lt(V("j"), 0.63)), couleur_hsbt(4, 12, add(V("lum"), 12)), couleur_hsbt(2, 65, mul(V("lum"), 0.86))),
                ligne(V("sx"), sub(V("y1"), div(V("h"), 4)), V("sx"), V("hz")),
                ligne(V("sx"), sub(V("hz"), div(V("h"), 4)), V("sx"), V("y2")),
            ]),
        ]),
    ])
    # métal : panneaux alternés et reflet clair en diagonale
    M.proc("mur metal", [], [
        si(et(eq(V("tex"), 1), eq(mod(floor(mul(V("wallX"), 2)), 2), 1)), [setv("lum", mul(V("lum"), 0.88))]),
        couleur_hsbt(58, 45, V("lum")), ligne(V("sx"), V("y1"), V("sx"), V("y2")),
        si(eq(V("tex"), 1), [
            setv("j", add(V("hz"), mul(V("h"), sub(0.3, mul(0.6, V("wallX")))))),
            couleur_hsbt(58, 20, add(V("lum"), 30), 35),
            ligne(V("sx"), add(V("j"), mul(V("h"), 0.07)), V("sx"), sub(V("j"), mul(V("h"), 0.07))),
        ]),
    ])

    # ---- traceur de tir : trait jaune-blanc du canon vers le point d'impact + étincelles ---------------------------
    M.proc("traceur", [], [
        couleur_hsbt(14, 35, 100, 65), taille_stylo(6),
        ligne(add(150, V("secX")), add(-120, V("secY")), add(V("traceX"), V("secX")), add(V("traceY"), V("secY"))),
        couleur_hsbt(14, 55, 100, 0), taille_stylo(1.8),
        ligne(add(150, V("secX")), add(-120, V("secY")), add(V("traceX"), V("secX")), add(V("traceY"), V("secY"))),
        couleur_hsbt(9, 85, 100, 0), taille_stylo(1.5),
        repeter(4, [ligne(add(V("traceX"), V("secX")), add(V("traceY"), V("secY")),
                          add(add(V("traceX"), V("secX")), hasard(-11, 11)), add(add(V("traceY"), V("secY")), hasard(-8, 11)))]),
    ])

    # ---- vignette hors zone : bords assombris (2 passes translucides) -------------------------------------------
    def cadre():
        return [ligne(-250, 180, 250, 180), ligne(-250, -180, 250, -180), ligne(-240, -200, -240, 200), ligne(240, -200, 240, 200)]

    M.proc("vignette", [], [
        couleur_hsbt(V("teinteZone"), 70, 8, 72), taille_stylo(110)] + cadre() + [
        couleur_hsbt(V("teinteZone"), 70, 8, 50), taille_stylo(44)] + cadre())

    def point_mm(x, y, teinte, sat, lum, taille_pt):
        return [couleur_hsbt(teinte, sat, lum, 0), taille_stylo(taille_pt), ligne(mm_x(x), mm_y(y), mm_x(x), mm_y(y))]

    def cercle_mm(cx, cy, r, teinte, sat, lum, epaisseur, transparence=0):
        return [
            couleur_hsbt(teinte, sat, lum, transparence), taille_stylo(epaisseur), setv("ang", 0), stylo_haut(),
            aller(mm_x(add(cx, r)), mm_y(cy)), stylo_bas(),
            repeter(24, [
                changev("ang", 15),
                aller(mm_x(add(cx, mul(r, cos(V("ang"))))), mm_y(add(cy, mul(r, sin(V("ang")))))),
            ]),
            stylo_haut(),
        ]

    M.proc("minicarte", [], [
        couleur_hsbt(60, 30, 10, 30), taille_stylo(2 * MM_R + 4),
        ligne(MM_CX, MM_CY, MM_CX, MM_CY),
        # murs principaux (points discrets, 1 point sur 2 pour le coût) — seulement si pas en mode performance
        # zone actuelle (teinte selon daltonisme) avec halo pulsant, et prochaine zone (blanche)
        si(lt(V("zoneR"), C.TAILLE), cercle_mm(V("zoneX"), V("zoneY"), V("zoneR"), V("teinteZone"), 70, 95, 7,
                                                add(62, mul(22, sin(mul(chrono(), 240)))))
           + cercle_mm(V("zoneX"), V("zoneY"), V("zoneR"), V("teinteZone"), 80, 95, 2)),
        si(et(lt(V("prochaineZoneR"), V("zoneR")), gt(V("tempsAvantZone"), 0)),
           cercle_mm(V("prochaineZoneX"), V("prochaineZoneY"), V("prochaineZoneR"), 0, 0, 100, 1.5, 20)),
        # balises de redéploiement (modes équipe)
        si(gt(V("monEquipe"), 0), [
            setv("k", 1),
            repeter(C.NB_BALISES, [
                point_mm(item("BalisesX", V("k")), item("BalisesY", V("k")), 55, 90, 100, 5),
                changev("k", 1),
            ]),
        ]),
        # autres joueurs : rouges ; coéquipiers : verts
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1),
                   ou(eq(item("E_etat", V("k")), 1), eq(item("E_etat", V("k")), 3))), [
                si(et(gt(V("monEquipe"), 0), eq(item("E_equipe", V("k")), V("monEquipe"))),
                   point_mm(item("E_x", V("k")), item("E_y", V("k")), 38, 90, 95, 5),
                   point_mm(item("E_x", V("k")), item("E_y", V("k")), 0, 90, 100, 5)),
            ]),
            changev("k", 1),
        ]),
        # pings (entrées de 15 caractères : k xxxx yyyy eeeeee)
        setv("k", 1),
        repeter(long_liste("Pings"), [
            si(gt(C.sous_chaine(item("Pings", V("k")), 10, 6), mul(chrono(), 10)), [
                point_mm(div(C.sous_chaine(item("Pings", V("k")), 2, 4), 100),
                         div(C.sous_chaine(item("Pings", V("k")), 6, 4), 100), 15, 95, 100, 6),
            ]),
            changev("k", 1),
        ]),
        # moi : cône de vision translucide (7 rayons sur ± 30°), point et direction
        couleur_hsbt(0, 0, 100, 68), taille_stylo(2.5), setv("ang", sub(V("dir"), 30)),
        repeter(7, [
            ligne(mm_x(V("px")), mm_y(V("py")), add(mm_x(V("px")), mul(cos(V("ang")), 15)), add(mm_y(V("py")), mul(sin(V("ang")), 15))),
            changev("ang", 10),
        ]),
        point_mm(V("px"), V("py"), 0, 0, 100, 5),
        taille_stylo(2),
        ligne(mm_x(V("px")), mm_y(V("py")), add(mm_x(V("px")), mul(cos(V("dir")), 9)), add(mm_y(V("py")), mul(sin(V("dir")), 9))),
    ])

    M.proc("rendu", [], [
        appel("palette"), appel("eclairs"), appel("lumiere"), appel("secousse"),
        setv("largeurCol", div(480, V("colonnes"))),
        setv("cosD", cos(V("dir"))), setv("sinD", sin(V("dir"))),
        setv("planeX", mul(V("sinD"), V("plan"))), setv("planeY", mul(V("cosD"), mul(V("plan"), -1))),
        appel("ciel et sol"),
        taille_stylo(add(V("largeurCol"), 1)),
        setv("i", 0),
        repeter(V("colonnes"), [appel("colonne"), changev("i", 1)]),
        si(gt(V("traceFin"), chrono()), [appel("traceur")]),
        si(et(eq(V("horsZone"), 1), eq(V("param_performance"), 0)), [appel("vignette")]),
        si(eq(V("param_performance"), 0), [appel("minicarte")], [
            # minicarte réduite : moi + zone uniquement
            couleur_hsbt(60, 30, 10, 30), taille_stylo(2 * MM_R + 4), ligne(MM_CX, MM_CY, MM_CX, MM_CY),
            si(lt(V("zoneR"), C.TAILLE), cercle_mm(V("zoneX"), V("zoneY"), V("zoneR"), V("teinteZone"), 80, 95, 2)),
            point_mm(V("px"), V("py"), 0, 0, 100, 5),
        ]),
    ])
    M.proc("regler colonnes", [], [
        setv("colonnes", 80),
        si(eq(V("param_qualite"), 1), [setv("colonnes", 40)]),
        si(eq(V("param_qualite"), 3), [setv("colonnes", 120)]),
        si(eq(V("param_performance"), 1), [setv("colonnes", 40)]),
    ])
    M.script(quand_drapeau(), [
        cacher(), aller(0, 0),
        toujours([
            appel("regler colonnes"),
            si(est_ecran_rendu(), [appel("rendu")]),
        ]),
    ])


# ---------------------------------------------------------------------------
#  Panneaux 3D (billboards)
# ---------------------------------------------------------------------------
def installer_billboard(cible, ex, ey, taille_num, decal_y, condition, avant=None, apres_cache=None):
    """Proc « afficher » : place le sprite comme panneau 3D à la position monde (ex, ey).

    taille_num : taille% = taille_num / distance ; decal_y : décalage vertical = decal_y / distance.
    Un costume de 100 px de haut à 224/f % mesure 0,7 mur ; son centre est à horizon − 48/f.
    """
    for v in ["dx", "dy", "f", "r", "sx", "col"]:
        cible.var(v, 0)
    cible.proc("afficher", [], [
        # masqué dès qu'une superposition au stylo (chat, roues, signalement) est ouverte, et sur les écrans « pause » /
        # « fin » où Menus dessine ses panneaux au stylo : les sprites passent au-dessus du stylo
        si(et4(condition, est_ecran_rendu(), eq(V("superposition"), ""), non(ou(eq(V("ecran"), "pause"), eq(V("ecran"), "fin")))), [
            setv("dx", sub(ex, V("px"))), setv("dy", sub(ey, V("py"))),
            setv("f", add(mul(V("dx"), cos(V("dir"))), mul(V("dy"), sin(V("dir"))))),
            setv("r", sub(mul(V("dx"), sin(V("dir"))), mul(V("dy"), cos(V("dir"))))),
            si(gt(V("f"), 0.25), [
                setv("sx", mul(div(div(V("r"), V("f")), V("plan")), 240)),
                setv("col", add(floor(div(add(V("sx"), 240), div(480, V("colonnes")))), 1)),
                si(lt(V("col"), 1), [setv("col", 1)]), si(gt(V("col"), V("colonnes")), [setv("col", V("colonnes"))]),
                si(et(lt(absv(V("sx")), 300), gt(item("Profondeur", V("col")), sub(V("f"), 0.15))), [
                    taille(div(taille_num, V("f"))),
                    # la secousse d'écran du moteur (m3d_secX/Y) s'applique aussi aux panneaux
                    aller(add(V("sx"), V("m3d_secX")), add(sub(V("horizon"), div(decal_y, V("f"))), V("m3d_secY"))),
                    montrer(),
                ] + (avant or []), [cacher()] + (apres_cache or [])),
            ], [cacher()] + (apres_cache or [])),
        ], [cacher()] + (apres_cache or [])),
    ])


def construire_panneaux(P):
    # ---- Ennemi : un clone par emplacement -----------------------------------
    E = Cible(P, "Ennemi")
    E.costumes = [P.costume("debout", _costume_personnage(1, "debout"), 30, 50),
                  P.costume("aterre", _costume_personnage(1, "aterre"), 50, 30),
                  P.costume("emote", _costume_personnage(1, "emote"), 30, 50)]
    # skins supplémentaires si disponibles (costumes "skinN_pose")
    if UI and hasattr(UI, "personnage"):
        for skin in range(1, 11):
            for pose, cx, cy in [("debout", 30, 50), ("aterre", 50, 30), ("emote", 30, 50)]:
                try:
                    E.costumes.append(P.costume("skin%d_%s" % (skin, pose), UI.personnage(skin, pose), cx, cy))
                except Exception:
                    pass
    E.visible = False
    E.layer = C.CALQUES["Ennemi"]
    E.var("monIndex", 0)
    E.var("pose", "debout")
    E.var("etiquette", "")
    for v in ["vu", "mortAnim", "dsx", "dsy", "dt", "k"]:     # effet de disparition à la mort (dernière position vue)
        E.var(v, 0)
    a_skins = any(c["name"].startswith("skin") for c in E.costumes)
    installer_billboard(
        E, item("E_x", V("monIndex")), item("E_y", V("monIndex")), 224, 48,
        et3(non(eq(V("monIndex"), V("monSlot"))), eq(item("E_actif", V("monIndex")), 1),
            ou3(eq(item("E_etat", V("monIndex")), 1), eq(item("E_etat", V("monIndex")), 3), eq(item("E_etat", V("monIndex")), 8))),
        avant=[
            # pose : à terre / émote / debout
            setv("pose", "debout"),
            si(eq(item("E_etat", V("monIndex")), 3), [setv("pose", "aterre")]),
            si(et(eq(item("E_etat", V("monIndex")), 1), gt(item("E_emoteFin", V("monIndex")), chrono())), [setv("pose", "emote")]),
            (costume(join(join("skin", item("E_skin", V("monIndex"))), join("_", V("pose")))) if a_skins else costume(V("pose"))),
            si(eq(V("pose"), "aterre"), [taille(div(160, V("f"))),
                                         aller(add(V("sx"), V("m3d_secX")), add(sub(V("horizon"), div(110, V("f"))), V("m3d_secY")))]),
            # touché par moi (cible = monIndex) : éclat blanc 0,15 s ; sinon luminosité selon l'heure (nuit : plus sombre)
            si(et(gt(V("toucheFin"), add(chrono(), 0.1)), eq(V("cible"), V("monIndex"))), [effet("BRIGHTNESS", 60)],
               [effet("BRIGHTNESS", mul(sub(V("m3d_lumiere"), 1), 60))]),
            # mémoire de la dernière position affichée (pour la disparition à la mort)
            setv("vu", 1), setv("dsx", sub(position_x(), V("m3d_secX"))), setv("dsy", sub(position_y(), V("m3d_secY"))),
            setv("dt", taille_actuelle()),
            # étiquette : nom ♥pv (★ pour un coéquipier) ; rien en mode performance
            si(eq(V("param_performance"), 0), [
                setv("etiquette", join(item("E_nom", V("monIndex")), join(" ♥", item("E_pv", V("monIndex"))))),
                si(et(gt(V("monEquipe"), 0), eq(item("E_equipe", V("monIndex")), V("monEquipe"))),
                   [setv("etiquette", join("★ ", V("etiquette")))]),
                si(eq(item("E_etat", V("monIndex")), 3), [setv("etiquette", join(V("etiquette"), " (à terre)"))]),
                dire(V("etiquette")),
            ], [dire("")]),
        ],
        apres_cache=[dire(""), setv("vu", 0)])
    E.script(quand_drapeau(), [cacher()])
    E.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(C.NB_JOUEURS, [changev("monIndex", 1), cloner_moi()]),
    ])
    E.script(quand_clone(), ([] if a_skins else [effet("COLOR", mul(V("monIndex"), 35))]) + [
        setv("vu", 0), setv("mortAnim", 0),
        toujours([
            arriere_plan(),
            # mort d'un adversaire visible à l'image précédente : disparition de 0,6 s (rétrécit, monte, s'efface)
            si(et(eq(V("vu"), 1), eq(item("E_etat", V("monIndex")), 2)), [setv("mortAnim", add(chrono(), 0.6)), setv("vu", 0)]),
            appel("afficher"),
            si(gt(V("mortAnim"), chrono()), [
                setv("k", div(sub(V("mortAnim"), chrono()), 0.6)),
                taille(mul(V("dt"), add(0.35, mul(0.65, V("k"))))),
                aller(add(V("dsx"), V("m3d_secX")), add(add(V("dsy"), mul(sub(1, V("k")), 50)), V("m3d_secY"))),
                effet("GHOST", mul(sub(1, V("k")), 90)), effet("BRIGHTNESS", 50), montrer(),
            ], [
                si(gt(V("mortAnim"), 0), [setv("mortAnim", 0), effet("GHOST", 0), effet("BRIGHTNESS", 0), cacher()]),
            ]),
        ]),
    ])

    # ---- Coffre ----------------------------------------------------------------
    Co = Cible(P, "Coffre")
    Co.costumes = [P.costume("ferme", S.svg_coffre(), 30, 25)]
    try:
        Co.costumes.append(P.costume("ouvert", UI.coffre_ouvert(), 30, 25))
    except Exception:
        Co.costumes.append(P.costume("ouvert", S.svg_coffre(), 30, 25))
    Co.visible = False
    Co.layer = C.CALQUES["Coffre"]
    Co.var("monIndex", 0)
    installer_billboard(Co, item("CoffresX", V("monIndex")), item("CoffresY", V("monIndex")), 300, 85, gt(V("monIndex"), 0),
                        avant=[si(contient("CoffresPris", V("monIndex")), [costume("ouvert")], [costume("ferme")])])
    Co.script(quand_drapeau(), [cacher()])
    Co.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(C.NB_COFFRES, [changev("monIndex", 1), cloner_moi()]),
    ])
    Co.script(quand_clone(), [toujours([arriere_plan(), appel("afficher")])])

    # ---- Balise de redéploiement ----------------------------------------------
    B = Cible(P, "Balise")
    try:
        B.costumes = [P.costume("balise", UI.balise(), 20, 30)]
    except Exception:
        B.costumes = [P.costume("balise", S.svg_rect(40, 60, "#38bdf8", 6, 1.0, "#0c4a6e", 3), 20, 30)]
    B.visible = False
    B.layer = C.CALQUES["Balise"]
    B.var("monIndex", 0)
    installer_billboard(B, item("BalisesX", V("monIndex")), item("BalisesY", V("monIndex")), 340, 60,
                        et(gt(V("monIndex"), 0), gt(V("monEquipe"), 0)))
    B.script(quand_drapeau(), [cacher()])
    B.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(C.NB_BALISES, [changev("monIndex", 1), cloner_moi()]),
    ])
    B.script(quand_clone(), [toujours([arriere_plan(), appel("afficher")])])

    # ---- Carte de redéploiement d'un coéquipier mort -----------------------------
    CR = Cible(P, "CarteRedeploiement")
    try:
        CR.costumes = [P.costume("carte", UI.carte_redeploiement(), 16, 20)]
    except Exception:
        CR.costumes = [P.costume("carte", S.svg_rect(32, 40, "#60a5fa", 4, 1.0, "#1e3a8a", 3), 16, 20)]
    CR.visible = False
    CR.layer = C.CALQUES["CarteRedeploiement"]
    CR.var("monIndex", 0)
    installer_billboard(CR, item("E_x", V("monIndex")), item("E_y", V("monIndex")), 200, 70,
                        et4(non(eq(V("monIndex"), V("monSlot"))), eq(item("E_actif", V("monIndex")), 1),
                            et3(eq(item("E_etat", V("monIndex")), 2), gt(V("monEquipe"), 0),
                                eq(item("E_equipe", V("monIndex")), V("monEquipe"))),
                            non(contient("CartesRamassees", V("monIndex")))))
    CR.script(quand_drapeau(), [cacher()])
    CR.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(C.NB_JOUEURS, [changev("monIndex", 1), cloner_moi()]),
    ])
    CR.script(quand_clone(), [toujours([arriere_plan(), appel("afficher")])])

    # ---- Marqueur (ping) : un clone par emplacement, lit la liste Pings -------------
    Mq = Cible(P, "Marqueur")
    try:
        Mq.costumes = [P.costume("marqueur", UI.marqueur("#facc15"), 12, 36)]
    except Exception:
        Mq.costumes = [P.costume("marqueur", S.svg_cercle(24, "#facc15", 1.0, "#713f12", 3), 12, 24)]
    Mq.visible = False
    Mq.layer = C.CALQUES["Marqueur"]
    for v in ["monIndex", "entree", "k", "mx", "my"]:
        Mq.var(v, 0)
    Mq.proc("chercher ping", [], [
        setv("entree", ""), setv("k", 1),
        repeter(long_liste("Pings"), [
            si(eq(lettre(1, item("Pings", V("k"))), V("monIndex")), [setv("entree", item("Pings", V("k")))]),
            changev("k", 1),
        ]),
        si(gt(longueur(V("entree")), 14), [
            si(lt(C.sous_chaine(V("entree"), 10, 6), mul(chrono(), 10)), [setv("entree", "")], [
                setv("mx", div(C.sous_chaine(V("entree"), 2, 4), 100)),
                setv("my", div(C.sous_chaine(V("entree"), 6, 4), 100)),
            ]),
        ], [setv("entree", "")]),
    ])
    installer_billboard(Mq, V("mx"), V("my"), 260, -40, gt(longueur(V("entree")), 14))
    Mq.script(quand_drapeau(), [cacher()])
    Mq.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(C.NB_JOUEURS, [changev("monIndex", 1), cloner_moi()]),
    ])
    Mq.script(quand_clone(), [toujours([arriere_plan(), appel("chercher ping"), appel("afficher")])])

    # ---- Spray : clones indexés sur la liste Sprays (xxxx yyyy t ddd) ----------------
    Sp = Cible(P, "Spray")
    Sp.costumes = []
    for n in range(1, len(C.SPRAYS) + 1):
        try:
            Sp.costumes.append(P.costume("spray%d" % n, UI.spray(n), 32, 32))
        except Exception:
            Sp.costumes.append(P.costume("spray%d" % n, S.svg_cercle(64, ["#f87171", "#facc15", "#f472b6", "#e5e7eb", "#fde047", "#fb923c"][n - 1], 0.9), 32, 32))
    Sp.visible = False
    Sp.layer = C.CALQUES["Spray"]
    for v in ["monIndex", "entree", "mx", "my"]:
        Sp.var(v, 0)
    Sp.proc("lire spray", [], [
        setv("entree", item("Sprays", V("monIndex"))),
        si(gt(longueur(V("entree")), 11), [
            setv("mx", div(C.sous_chaine(V("entree"), 1, 4), 100)),
            setv("my", div(C.sous_chaine(V("entree"), 5, 4), 100)),
            costume(join("spray", lettre(9, V("entree")))),
        ]),
    ])
    installer_billboard(Sp, V("mx"), V("my"), 200, 60, gt(longueur(V("entree")), 11))
    Sp.script(quand_drapeau(), [cacher()])
    Sp.script(quand_message("demarrer"), [
        si(gt(V("monIndex"), 0), [supprimer_clone()]),      # un clone existant disparaît, l'original recrée la série
        cacher(), setv("monIndex", 0),
        repeter(10, [changev("monIndex", 1), cloner_moi()]),
    ])
    Sp.script(quand_clone(), [toujours([arriere_plan(), appel("lire spray"), appel("afficher")])])
