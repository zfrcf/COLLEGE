# -*- coding: utf-8 -*-
"""
Largages de ravitaillement et lama à butin (module royale/mod_largages.py).

Sprites
-------
- « Largages » (logique, invisible, calque 94 : juste après Moteur3D pour dessiner sur sa minicarte) :
  * à chaque début de rétrécissement des phases de jeu contrat.PHASES_LARGAGE (2 et 4 : `phase` ∈ {2, 4} et
    `tempsAvantZone` = 0), un largage apparaît à un point déterministe (graine, n°) dans la prochaine zone
    (prochaineZoneX/Y/R), sur une case libre. Globales écrites : largage_num (n° croissant, 0 = aucun),
    largage_phase, largage_x/y, largage_debut (chrono, recalé sur le temps déjà écoulé du rétrécissement pour
    un joueur qui arrive en cours), largage_alt (DUREE_DESCENTE_LARGAGE → 0 en autant de secondes).
    Notification « Largage en cours », bannière `message` = "largage", son « notification ».
  * lama à butin : une position déterministe par manche (graine) sur une case libre → lama_x / lama_y,
    lama_coups remis à 0, LamasPris vidée (sur « evt nouvelle manche » et au démarrage).
  * minicarte : point bleu clignotant à la position du largage tant qu'il n'est pas ouvert (stylo, après le
    rendu de Moteur3D ; pas en mode performance).
- « Largage » (panneau 3D, costumes svg_ui.largage / largage_pose) : caisse sous ballon placée par installer_billboard
  à (largage_x, largage_y) ; sa hauteur à l'écran suit largage_alt (descente), caisse seule une fois posée, cachée une
  fois ouverte.
- « Lama » (panneau 3D, costume svg_ui.lama_3d) : visible tant que LamasPris ne contient pas 1 ; éclair de
  luminosité à chaque coup (lama_touche) et compteur de coups en bulle.

Ouverture (dans Joueur, royale/joueur.py — choix le plus simple : il possède déjà la machine « interagir
maintenu » et l'inventaire) :
- largage posé (largage_alt = 0) à moins de 1,5 case → interaction de type 4 (DUREE_OUVERTURE_LARGAGE = 2,5 s),
  « ouvrir largage » : arme légendaire (sniper / fusil d'assaut / lance-grenades selon n° + graine), potion de
  bouclier, 100 de chaque matériau, LargagesPris += n°, « evt coffre » (evt_valeur = 100 + n°).
- lama : COUPS_LAMA (5) coups de pioche (« coup de pioche », lama devant à ≤ 1,8 case) ou tirs (« tirer » :
  lama dans la ligne de mire, ou dans le rayon d'une grenade) → « ouvrir lama » : 200 de chaque matériau,
  3 potions de bouclier, munitions de chaque type, LamasPris += 1, « evt coffre » (evt_valeur = 200).

Limites : la descente est locale à chaque client (recalée à la seconde près sur tempsPhase) ; le largage et le
lama ne sont pas dessinés sur la carte plein écran de Partie.
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S
from .moteur3d import installer_billboard, est_ecran_rendu, mm_x, mm_y

try:
    from . import svg_ui as UI
except Exception:
    UI = None

V = Var
ORDRE = 45
ALT_MAX = C.DUREE_DESCENTE_LARGAGE          # altitude de départ (unités) : 1 unité par seconde de descente
PX_PAR_UNITE = 16                           # hauteur écran (px à distance 1) d'une unité d'altitude
OFFSETS = sorted([(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4) if (dx, dy) != (0, 0)],
                 key=lambda o: (o[0] ** 2 + o[1] ** 2, o))
RETRECISSEMENTS = [p[1] for p in C.PHASES_TEMPETE]      # durée du rétrécissement de chaque zone (index = phase − 1)


def alea(k, sel):
    """Pseudo-aléatoire déterministe dans [0, 1[ (graine, k, sel) — même formule que Partie."""
    return div(mod(mul(add(mul(V("graine"), 131), add(mul(k, 71), sel * 17)), 7919), 1000), 1000)


def _costume(P, nom, fonction, fallback, cx, cy):
    if UI and hasattr(UI, fonction):
        try:
            return P.costume(nom, getattr(UI, fonction)(), cx, cy)
        except Exception:
            pass
    return P.costume(nom, fallback, cx, cy)


def largage_actif():
    return et(gt(V("largage_num"), 0), non(contient("LargagesPris", V("largage_num"))))


def lama_actif():
    return et(gt(V("lama_x"), 0), non(contient("LamasPris", 1)))


def construire(P):
    construire_logique(P)
    construire_panneaux(P)


# ---------------------------------------------------------------------------
#  Sprite logique « Largages »
# ---------------------------------------------------------------------------
def construire_logique(P):
    L = Cible(P, "Largages")
    L.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    L.visible = False
    L.layer = C.CALQUES["Largages"]
    for v in ["nx", "ny", "cx", "cy", "dx", "dy", "i", "ok", "ang", "d", "f", "ecoule", "r"]:
        L.var(v, 0)
    L.liste("ox", [o[0] for o in OFFSETS])
    L.liste("oy", [o[1] for o in OFFSETS])
    L.liste("retrecissements", RETRECISSEMENTS)

    def notification(texte):
        return [ajouter_liste("Notifications", texte), ajouter_liste("NotificationsFin", add(chrono(), 4)),
                si(gt(long_liste("Notifications"), 4), [supprimer("Notifications", 1), supprimer("NotificationsFin", 1)])]

    # case libre la plus proche de (nx, ny), à l'intérieur des murs de bordure (anneaux de rayon 1 à 3)
    L.proc("case libre", [], [
        si(lt(V("nx"), 1.5), [setv("nx", 1.5)]), si(gt(V("nx"), C.TAILLE - 1.5), [setv("nx", C.TAILLE - 1.5)]),
        si(lt(V("ny"), 1.5), [setv("ny", 1.5)]), si(gt(V("ny"), C.TAILLE - 1.5), [setv("ny", C.TAILLE - 1.5)]),
        setv("nx", add(floor(V("nx")), 0.5)), setv("ny", add(floor(V("ny")), 0.5)),
        setv("ok", 0), setv("i", 1), setv("cx", floor(V("nx"))), setv("cy", floor(V("ny"))),
        si(eq(C.cellule(V("nx"), V("ny")), 0), [setv("ok", 1)]),
        repeter_jusqua(ou(eq(V("ok"), 1), gt(V("i"), len(OFFSETS))), [
            setv("dx", add(V("cx"), item("ox", V("i")))), setv("dy", add(V("cy"), item("oy", V("i")))),
            si(et4(gt(V("dx"), 0), lt(V("dx"), C.TAILLE - 1), gt(V("dy"), 0), lt(V("dy"), C.TAILLE - 1)), [
                si(eq(C.cellule(V("dx"), V("dy")), 0), [setv("nx", add(V("dx"), 0.5)), setv("ny", add(V("dy"), 0.5)), setv("ok", 1)]),
            ]),
            changev("i", 1),
        ]),
        si(eq(V("ok"), 0), [setv("nx", C.TAILLE / 2 + 0.5), setv("ny", C.TAILLE / 2 + 0.5)]),
    ])

    # lama de la manche : position déterministe (graine seule) sur une case libre
    L.proc("placer lama", [], [
        setv("nx", add(2, mul(alea(90, 1), C.TAILLE - 4))), setv("ny", add(2, mul(alea(90, 2), C.TAILLE - 4))),
        appel("case libre"),
        setv("lama_x", V("nx")), setv("lama_y", V("ny")), setv("lama_coups", 0), setv("lama_touche", 0),
        vider("LamasPris"),
    ])

    # nouveau largage : point déterministe (graine, n°) dans la prochaine zone, descente recalée sur le temps déjà
    # écoulé du rétrécissement (tempsPhase = secondes restantes, durées × 0,5 en Tempête éclair)
    L.proc("lancer largage", [], [
        changev("largage_num", 1), setv("largage_phase", V("phase")),
        setv("ang", mul(alea(add(60, V("largage_num")), 1), 360)),
        setv("d", mul(alea(add(60, V("largage_num")), 2), mul(V("prochaineZoneR"), 0.7))),
        setv("nx", add(V("prochaineZoneX"), mul(V("d"), cos(V("ang"))))),
        setv("ny", add(V("prochaineZoneY"), mul(V("d"), sin(V("ang"))))),
        appel("case libre"),
        setv("largage_x", V("nx")), setv("largage_y", V("ny")),
        setv("f", 1), si(eq(V("ltm"), 3), [setv("f", 0.5)]),
        setv("ecoule", sub(mul(item("retrecissements", sub(V("phase"), 1)), V("f")), V("tempsPhase"))),
        si(lt(V("ecoule"), 0), [setv("ecoule", 0)]), si(gt(V("ecoule"), ALT_MAX), [setv("ecoule", ALT_MAX)]),
        setv("largage_debut", sub(chrono(), V("ecoule"))), setv("largage_alt", sub(ALT_MAX, V("ecoule"))),
        notification(C.tr("Largage en cours", "Supply drop incoming")),
        si(eq(V("enPartie"), 1), [setv("message", "largage")]),
        setv("son_pan", 0), setv("son_volume", 80), diffuser("son notification"),
    ])

    phase_largage = eq(V("phase"), C.PHASES_LARGAGE[0])
    for p in C.PHASES_LARGAGE[1:]:
        phase_largage = ou(phase_largage, eq(V("phase"), p))

    L.proc("suivre", [], [
        # déclenchement : début de rétrécissement d'une phase de largage, une fois par phase
        si(et3(phase_largage, eq(V("tempsAvantZone"), 0), non(eq(V("largage_phase"), V("phase")))), [appel("lancer largage")]),
        # descente
        si(gt(V("largage_num"), 0), [
            setv("largage_alt", sub(ALT_MAX, sub(chrono(), V("largage_debut")))),
            si(lt(V("largage_alt"), 0), [setv("largage_alt", 0)]),
        ]),
    ])

    # minicarte (dessinée par Moteur3D juste avant) : point bleu clignotant sur le largage non ouvert
    L.proc("marqueur minicarte", [], [
        si(et4(largage_actif(), est_ecran_rendu(), eq(V("param_performance"), 0), eq(mod(floor(mul(chrono(), 3)), 2), 0)), [
            couleur_hsbt(62, 90, 100, 0), taille_stylo(7), stylo_haut(),
            aller(mm_x(V("largage_x")), mm_y(V("largage_y"))), stylo_bas(), stylo_haut(),
            couleur_hsbt(0, 0, 100, 0), taille_stylo(3),
            aller(mm_x(V("largage_x")), mm_y(V("largage_y"))), stylo_bas(), stylo_haut(),
        ]),
    ])

    L.script(quand_drapeau(), [
        cacher(), aller(0, 0),
        setv("largage_num", 0), setv("largage_phase", 0), setv("largage_alt", 0), setv("largage_debut", 0),
        setv("largage_x", 0), setv("largage_y", 0), vider("LargagesPris"),
        appel("placer lama"),
        toujours([
            si(eq(V("connecte"), 1), [appel("suivre"), appel("marqueur minicarte")]),
        ]),
    ])
    L.script(quand_message("evt nouvelle manche"), [
        setv("largage_num", 0), setv("largage_phase", 0), setv("largage_alt", 0), setv("largage_debut", 0),
        setv("largage_x", 0), setv("largage_y", 0), vider("LargagesPris"),
        appel("placer lama"),
    ])
    return L


# ---------------------------------------------------------------------------
#  Panneaux 3D « Largage » et « Lama »
# ---------------------------------------------------------------------------
def construire_panneaux(P):
    # ---- Largage : costume 60×90, centre de rotation au bas de la caisse ; décalage vertical = sol + altitude ----
    G = Cible(P, "Largage")
    G.costumes = [_costume(P, "largage", "largage", S.svg_rect(60, 90, "#2563eb", 6, 1.0, "#1e3a8a", 3), 30, 88),
                  _costume(P, "largage_pose", "largage_pose", S.svg_rect(60, 34, "#2563eb", 6, 1.0, "#1e3a8a", 3), 30, 32)]
    G.visible = False
    G.layer = C.CALQUES["Largage"]
    # taille 220 : posée, la caisse reste sous la barre d'interaction du HUD même à 2 cases ; en descente, ballon + caisse
    installer_billboard(G, V("largage_x"), V("largage_y"), 220, sub(160, mul(V("largage_alt"), PX_PAR_UNITE)), largage_actif(),
                        avant=[si(gt(V("largage_alt"), 0), [costume("largage")], [costume("largage_pose")])])
    G.script(quand_drapeau(), [cacher(), toujours([arriere_plan(), appel("afficher")])])

    # ---- Lama : costume 60×70 (pieds en bas) ; éclair à chaque coup, compteur de coups en bulle ----
    La = Cible(P, "Lama")
    La.costumes = [_costume(P, "lama", "lama_3d", S.svg_rect(60, 70, "#d946ef", 8, 1.0, "#6b21a8", 3), 30, 68)]
    La.visible = False
    La.layer = C.CALQUES["Lama"]
    installer_billboard(La, V("lama_x"), V("lama_y"), 300, 160, lama_actif(), avant=[
        si(lt(sub(chrono(), V("lama_touche")), 0.25), [effet("BRIGHTNESS", 45)], [effet("BRIGHTNESS", 0)]),
        si(gt(V("lama_coups"), 0), [dire(join(V("lama_coups"), "/%d" % C.COUPS_LAMA))], [dire("")]),
    ], apres_cache=[dire("")])
    La.script(quand_drapeau(), [cacher(), toujours([arriere_plan(), appel("afficher")])])
    return G, La
