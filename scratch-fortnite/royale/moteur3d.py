# -*- coding: utf-8 -*-
"""
Moteur de rendu 3D (sprite Moteur3D) et panneaux 3D (Ennemi, Coffre, Marqueur, Balise,
CarteRedeploiement, Spray).

- Raycasting DDA sur la grille `Carte`, `colonnes` colonnes (40/80/120 selon param_qualite),
  ciel/sol, murs ombrés par distance et matériau, mur de tempête (intersection rayon/cercle),
  minicarte circulaire (en haut à droite) avec zone, prochaine zone, joueurs, coéquipiers, pings.
- Les panneaux se placent par projection caméra et sont masqués par les murs grâce à `Profondeur`.
- Ne rend que si `ecran` ∈ contrat.ECRANS_RENDU_3D ; les autres écrans sont dessinés par leurs
  propriétaires (Menus, Partie).
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
              "ex", "ey", "n"]:
        M.var(v, 0)

    # Couleurs selon daltonisme : teinte de la zone (0-100) — normal violet, proto/deutér. cyan, trit. orange
    M.proc("palette", [], [
        setv("teinteZone", 80),
        si(ou(eq(V("param_daltonisme"), 1), eq(V("param_daltonisme"), 2)), [setv("teinteZone", 52)]),
        si(eq(V("param_daltonisme"), 3), [setv("teinteZone", 12)]),
    ])

    M.proc("ciel et sol", [], [
        effacer(),
        # ciel : bleu, violet hors zone, doré en pré-partie (invulnérable)
        si(eq(V("horsZone"), 1), couleur_hsbt(V("teinteZone"), 55, 45), [
            si(eq(V("invulnerable"), 1), couleur_hsbt(12, 35, 95), couleur_hsbt(60, 45, 92)),
        ]),
        taille_stylo(sub(180, V("horizon"))),
        ligne(-250, div(add(180, V("horizon")), 2), 250, div(add(180, V("horizon")), 2)),
        # sol lointain puis proche (dégradé en 2 bandes ; 1 bande en mode performance)
        couleur_hsbt(30, 45, 38),
        taille_stylo(add(V("horizon"), 180)),
        ligne(-250, div(sub(V("horizon"), 180), 2), 250, div(sub(V("horizon"), 180), 2)),
        si(eq(V("param_performance"), 0), [
            couleur_hsbt(30, 50, 55),
            taille_stylo(div(add(V("horizon"), 180), 2)),
            ligne(-250, sub(V("horizon"), mul(add(V("horizon"), 180), 0.75)), 250,
                  sub(V("horizon"), mul(add(V("horizon"), 180), 0.75))),
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
        si(eq(V("hit"), 2), couleur_hsbt(8, 70, V("lum")), [
            si(eq(V("hit"), 3), couleur_hsbt(2, 60, V("lum")), [
                si(eq(V("hit"), 4), couleur_hsbt(58, 45, V("lum")), couleur_hsbt(0, 0, V("lum"))),
            ]),
        ]),
        setv("sx", add(-240, mul(add(V("i"), 0.5), V("largeurCol")))),
        si(lt(V("perp"), 59), [
            ligne(V("sx"), add(V("horizon"), div(V("h"), 2)), V("sx"), sub(V("horizon"), div(V("h"), 2))),
        ]),
        # mur de tempête (désactivé en mode performance)
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
                    couleur_hsbt(V("teinteZone"), 75, 85, 55),
                    ligne(V("sx"), add(V("horizon"), div(V("h"), 2)), V("sx"), sub(V("horizon"), div(V("h"), 2))),
                ]),
            ]),
        ]),
    ])

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
        # zone actuelle (teinte selon daltonisme) et prochaine zone (blanche)
        si(lt(V("zoneR"), C.TAILLE), cercle_mm(V("zoneX"), V("zoneY"), V("zoneR"), V("teinteZone"), 80, 95, 2)),
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
        # moi + direction
        point_mm(V("px"), V("py"), 0, 0, 100, 5),
        taille_stylo(2),
        ligne(mm_x(V("px")), mm_y(V("py")), add(mm_x(V("px")), mul(cos(V("dir")), 9)), add(mm_y(V("py")), mul(sin(V("dir")), 9))),
    ])

    M.proc("rendu", [], [
        appel("palette"),
        setv("largeurCol", div(480, V("colonnes"))),
        setv("cosD", cos(V("dir"))), setv("sinD", sin(V("dir"))),
        setv("planeX", mul(V("sinD"), V("plan"))), setv("planeY", mul(V("cosD"), mul(V("plan"), -1))),
        appel("ciel et sol"),
        taille_stylo(add(V("largeurCol"), 1)),
        setv("i", 0),
        repeter(V("colonnes"), [appel("colonne"), changev("i", 1)]),
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
        si(et(condition, est_ecran_rendu()), [
            setv("dx", sub(ex, V("px"))), setv("dy", sub(ey, V("py"))),
            setv("f", add(mul(V("dx"), cos(V("dir"))), mul(V("dy"), sin(V("dir"))))),
            setv("r", sub(mul(V("dx"), sin(V("dir"))), mul(V("dy"), cos(V("dir"))))),
            si(gt(V("f"), 0.25), [
                setv("sx", mul(div(div(V("r"), V("f")), V("plan")), 240)),
                setv("col", add(floor(div(add(V("sx"), 240), div(480, V("colonnes")))), 1)),
                si(lt(V("col"), 1), [setv("col", 1)]), si(gt(V("col"), V("colonnes")), [setv("col", V("colonnes"))]),
                si(et(lt(absv(V("sx")), 300), gt(item("Profondeur", V("col")), sub(V("f"), 0.15))), [
                    taille(div(taille_num, V("f"))),
                    aller(V("sx"), sub(V("horizon"), div(decal_y, V("f")))),
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
    a_skins = any(c["name"].startswith("skin") for c in E.costumes)
    installer_billboard(
        E, item("E_x", V("monIndex")), item("E_y", V("monIndex")), 224, 48,
        et3(non(eq(V("monIndex"), V("monSlot"))), eq(item("E_actif", V("monIndex")), 1),
            ou(eq(item("E_etat", V("monIndex")), 1), eq(item("E_etat", V("monIndex")), 3))),
        avant=[
            # pose : à terre / émote / debout
            setv("pose", "debout"),
            si(eq(item("E_etat", V("monIndex")), 3), [setv("pose", "aterre")]),
            si(et(eq(item("E_etat", V("monIndex")), 1), gt(item("E_emoteFin", V("monIndex")), chrono())), [setv("pose", "emote")]),
            (costume(join(join("skin", item("E_skin", V("monIndex"))), join("_", V("pose")))) if a_skins else costume(V("pose"))),
            si(eq(V("pose"), "aterre"), [taille(div(160, V("f"))), aller(V("sx"), sub(V("horizon"), div(110, V("f"))))]),
            # étiquette : nom ♥pv (★ pour un coéquipier) ; rien en mode performance
            si(eq(V("param_performance"), 0), [
                setv("etiquette", join(item("E_nom", V("monIndex")), join(" ♥", item("E_pv", V("monIndex"))))),
                si(et(gt(V("monEquipe"), 0), eq(item("E_equipe", V("monIndex")), V("monEquipe"))),
                   [setv("etiquette", join("★ ", V("etiquette")))]),
                si(eq(item("E_etat", V("monIndex")), 3), [setv("etiquette", join(V("etiquette"), " (à terre)"))]),
                dire(V("etiquette")),
            ], [dire("")]),
        ],
        apres_cache=[dire("")])
    E.script(quand_drapeau(), [cacher()])
    E.script(quand_message("demarrer"), [
        cacher(), setv("monIndex", 0),
        repeter(C.NB_JOUEURS, [changev("monIndex", 1), cloner_moi()]),
    ])
    E.script(quand_clone(), ([] if a_skins else [effet("COLOR", mul(V("monIndex"), 35))]) + [
        toujours([arriere_plan(), appel("afficher")]),
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
        cacher(), setv("monIndex", 0),
        repeter(10, [changev("monIndex", 1), cloner_moi()]),
    ])
    Sp.script(quand_clone(), [toujours([arriere_plan(), appel("lire spray"), appel("afficher")])])
