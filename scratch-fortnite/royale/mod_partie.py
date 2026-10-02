# -*- coding: utf-8 -*-
"""
Sprite « Partie » : DÉROULÉ D'UNE MANCHE façon Fortnite (module royale/mod_partie.py).

Responsabilités
---------------
- ☁ Partie = "1" + debut(5) + mode(1) + ltm(1) + graine(2) (contrat.PARTIE_POS) : lue à chaque image ;
  réécrite par ce sprite quand elle est vide, périmée (tempsManche > DUREE_MANCHE·f + DUREE_RESULTATS),
  dans le futur (tempsManche < −5) ou DUREE_RESULTATS (+ 2 s × (monSlot − 1)) après une fin de manche
  détectée localement. Chaque écriture remet ☁ Construction et ☁ Construction2 à 1.
  Quand `debut` change : mode/ltm/graine/zones/bus/équipe recalculés puis "evt nouvelle manche".
- Machine à états : phase 0 île d'attente, 1 bus, 2..6 tempête (contrat.PHASES_TEMPETE), 8 fin.
  Durées × 0,5 quand ltm = 3 (Tempête éclair). Variables écrites : tempsManche, tempsPhase, tempsPartie,
  phase, zoneX/Y/R/Degats, prochaineZoneX/Y/R, tempsAvantZone, zoneEnMouvement, ⏱ Zone, busX/Y/DirX/DirY/
  busProgression, aSaute, altitude, invulnerable, monEquipe, vivants, equipesVivantes, participants, rang,
  victoire, finManche, mode, ltm, graine, debut.
- Transitions d'état/écran du joueur local quand enPartie = 1 : placement sur l'île (etat 8), bus (6),
  saut/parachute (7), atterrissage (1), arrivée en retard (parachute dans la zone, ou spectateur en
  dernière phase / fin), reconnexion, écran "fin" (etat 9). Les écrans d'attente de Menus sont respectés :
  rien n'est fait tant que ecran = "matchmaking", ni pendant les 2,5 s de la barre de "chargement" ; pendant
  les résultats (phase 8) un joueur resté en "chargement" attend la manche suivante.
  Quand enPartie = 0, Partie ne touche pas à `etat` (Menus remet 5 au retour au salon), sauf l'état « fin » 9 qui
  n'appartient qu'à elle (remis à 5) : elle nettoie invulnerable/altitude/aSaute si etat = 5, et ne suit la manche
  (phase, zone, compteurs) que pour le salon (5), le spectateur (4) et la fin (9) ; un état forcé par un test ou un
  autre module (1..3, 6..8) est laissé tel quel.
- Dessin plein écran des écrans "bus", "parachute" et "carte" : carte complète tamponnée (costume SVG
  généré ici, noms des lieux FR/EN inclus), zone et prochaine zone, trajectoire et icône du bus, moi,
  coéquipiers, joueurs en l'air, pings, balises, coffres, légendes (texte.installer).

Événements diffusés : "evt nouvelle manche", "evt phase" (evt_valeur = phase), "evt atterrissage",
"evt fin manche" (evt_valeur = rang), "evt victoire", "evt changement ecran" ; sons : compte, bus,
parachute, tempete, victoire, defaite.

Variables locales clés : t (secondes depuis debut, flottant), f (facteur de durée), kk (n° de phase de
tempête 1..5, 0 avant le combat), listes zx/zy/zr (zones : index 1 = cercle initial, k+1 = zone k),
pS/pA/pFin/pD (horaires non mis à l'échelle), bx0/by0/bx1/by1/bdx/bdy/busAngle (trajectoire du bus).
"""
from xml.sax.saxutils import escape

from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S
from . import texte

try:
    from . import svg_ui as UI
except Exception:  # module de la phase A pas (encore) disponible
    UI = None

V = Var
A = Arg
ORDRE = 40

# ---------------------------------------------------------------------------
#  Constantes dérivées du contrat
# ---------------------------------------------------------------------------
PX_CASE = 10                                   # pixels par case sur la carte plein écran
DEMI = C.TAILLE * PX_CASE / 2                  # 160
P0 = C.DUREE_PREPARTIE                         # fin de l'île d'attente
P1 = P0 + C.DUREE_BUS                          # fin du bus = début des phases de tempête
RAYONS = [C.RAYON_INITIAL] + [p[2] for p in C.PHASES_TEMPETE]     # [30, 14, 9, 5, 2.5, 1.5]
DEBUTS, FINS, ATTENTES, DEGATS = [], [], [], []
_t = P1
for _a, _r, _rayon, _d in C.PHASES_TEMPETE:
    DEBUTS.append(_t)
    ATTENTES.append(_a)
    FINS.append(_t + _a + _r)
    DEGATS.append(_d)
    _t += _a + _r
NB_PHASES = len(C.PHASES_TEMPETE)              # 5 → phases 2..6
CENTRE = C.TAILLE / 2                          # 16
# décalages (dx, dy) triés par distance pour trouver la case libre la plus proche
OFFSETS = sorted([(dx, dy) for dx in range(-3, 4) for dy in range(-3, 4) if (dx, dy) != (0, 0)],
                 key=lambda o: (o[0] ** 2 + o[1] ** 2, o))
MARGE = 1.2                                    # position minimale à l'intérieur de la carte (murs de bordure)
FIN_STABLE = 8                                 # images consécutives où la condition d'élimination doit tenir
COL_D = 185                                    # abscisse de la colonne de légendes de droite : entre la carte (x ≤ 160) et l'altimètre du HUD (x > 210)
ECRANS_CARTE = ["bus", "parachute", "carte"]


# ---------------------------------------------------------------------------
#  Costumes SVG (remplacements locaux : svg_ui.py n'est pas disponible)
# ---------------------------------------------------------------------------
def _svg_carte(langue):
    """Carte complète 320 × 320 px (10 px/case, y vers le haut), murs colorés par matériau, noms des lieux."""
    px, w = PX_CASE, C.TAILLE * PX_CASE
    couleurs = {1: ("#b3ada5", "#5f5a53"), 2: ("#b4651f", "#5c330d"), 3: ("#c2410c", "#6b2410"), 4: ("#7f8ea3", "#3e4a5c")}
    s = ['<rect width="%d" height="%d" fill="#3d7538"/>' % (w, w)]
    # léger quadrillage toutes les 4 cases et zones « terre » autour des lieux
    chemins = []
    for i in range(0, C.TAILLE + 1, 4):
        chemins.append("M%d 0V%d" % (i * px, w))
        chemins.append("M0 %dH%d" % (i * px, w))
    s.append('<path d="%s" stroke="#ffffff" stroke-opacity="0.07" stroke-width="1"/>' % "".join(chemins))
    for fr, en, lx, ly, lr in C.LIEUX:
        s.append('<circle cx="%.1f" cy="%.1f" r="%.1f" fill="#8a7a4a" fill-opacity="0.22"/>'
                 % (lx * px, (C.TAILLE - ly) * px, lr * px))
    # murs
    for mat in (1, 2, 3, 4):
        rects = []
        for y in range(C.TAILLE):
            for x in range(C.TAILLE):
                if C.cellule_base(x, y) == mat:
                    rects.append('<rect x="%d" y="%d" width="%d" height="%d"/>' % (x * px, (C.TAILLE - 1 - y) * px, px, px))
        if rects:
            fond, bord = couleurs[mat]
            s.append('<g fill="%s" stroke="%s" stroke-width="1">%s</g>' % (fond, bord, "".join(rects)))
    s.append('<rect x="0.5" y="0.5" width="%d" height="%d" fill="none" stroke="#111827" stroke-width="1"/>' % (w - 1, w - 1))
    # noms des lieux (contour sombre puis texte clair)
    for fr, en, lx, ly, lr in C.LIEUX:
        nom = escape(en if langue else fr)
        tx, ty = lx * px, (C.TAILLE - ly) * px + 4
        base = ('<text x="%.1f" y="%.1f" text-anchor="middle" font-family="Sans Serif" font-weight="bold" '
                'font-size="11" %%s>%s</text>' % (tx, ty, nom))
        s.append(base % 'fill="#0f172a" stroke="#0f172a" stroke-width="3" stroke-linejoin="round"')
        s.append(base % 'fill="#f8fafc"')
    return S.svg(w, w, "".join(s))


def _svg_bus():
    """Bus de combat vu de dessus, pointant vers +x (direction Scratch 90)."""
    return S.svg(30, 18, (
        '<ellipse cx="13" cy="9" rx="12" ry="8" fill="#7c3aed" fill-opacity="0.35"/>'
        '<rect x="2" y="4" width="22" height="10" rx="3" fill="#3b82f6" stroke="#1e3a8a" stroke-width="1.5"/>'
        '<rect x="5" y="6" width="4" height="3" fill="#dbeafe"/><rect x="11" y="6" width="4" height="3" fill="#dbeafe"/>'
        '<rect x="17" y="6" width="4" height="3" fill="#dbeafe"/>'
        '<polygon points="24,4 29,9 24,14" fill="#fbbf24" stroke="#78350f" stroke-width="1"/>'))


def _svg_parachute_mini():
    return S.svg(14, 16, (
        '<path d="M1 7 A6 6 0 0 1 13 7 L7 8 Z" fill="#f97316" stroke="#7c2d12" stroke-width="1"/>'
        '<path d="M2 7 L7 14 L12 7" fill="none" stroke="#fde68a" stroke-width="1"/>'
        '<circle cx="7" cy="14" r="1.6" fill="#f8fafc" stroke="#111827" stroke-width="0.8"/>'))


def _svg_coffre_mini():
    return S.svg(8, 8, '<rect x="1" y="1" width="6" height="6" rx="1" fill="#facc15" stroke="#713f12" stroke-width="1.2"/>'
                       '<rect x="3" y="1" width="2" height="6" fill="#a16207"/>')


def _costume_icone(P, nom, fonction_ui, fallback, cx, cy):
    """Costume depuis svg_ui si la fonction existe, sinon le SVG de remplacement local."""
    if UI and hasattr(UI, fonction_ui):
        try:
            return P.costume(nom, getattr(UI, fonction_ui)(), cx, cy)
        except Exception:
            pass
    return P.costume(nom, fallback(), cx, cy)


# ---------------------------------------------------------------------------
#  Aides d'expressions
# ---------------------------------------------------------------------------
def mx(x):
    """Case x → abscisse écran de la carte plein écran."""
    return add(-DEMI, mul(x, PX_CASE))


def my(y):
    return add(-DEMI, mul(y, PX_CASE))


def etat_in(*vals):
    cond = eq(V("etat"), vals[0])
    for v in vals[1:]:
        cond = ou(cond, eq(V("etat"), v))
    return cond


def mode_equipe():
    cond = eq(V("mode"), C.MODES_EQUIPE[0])
    for m in C.MODES_EQUIPE[1:]:
        cond = ou(cond, eq(V("mode"), m))
    return cond


def alea(k, sel):
    """Pseudo-aléatoire déterministe dans [0, 1[ à partir de graine, k et sel (identique pour tous les joueurs)."""
    return div(mod(mul(add(mul(V("graine"), 131), add(mul(k, 71), sel * 17)), 7919), 1000), 1000)


def son_(nom):
    return [setv("son_pan", 0), setv("son_volume", 100), diffuser("son " + nom)]


def son_si_en_partie(nom):
    return [si(eq(V("enPartie"), 1), son_(nom))]


def point(x, y, taille_pt):
    """Point au stylo (couleur courante) à la case (x, y) de la carte plein écran."""
    return [taille_stylo(taille_pt), stylo_haut(), aller(mx(x), my(y)), stylo_bas(), stylo_haut()]


def tc(nom):
    return touche(C.touche_config(nom))


def ecrire(txt, x, y, taille_px, couleur, alignement):
    return appel("ecrire", txt, x, y, taille_px, couleur, alignement)


def dist2(ax, ay, bx, by):
    return add(mul(sub(ax, bx), sub(ax, bx)), mul(sub(ay, by), sub(ay, by)))


# ===========================================================================
#  Construction du sprite
# ===========================================================================
def construire(P):
    Pa = Cible(P, "Partie")
    Pa.costumes = [P.costume("carte_fr", _svg_carte(0), DEMI, DEMI), P.costume("carte_en", _svg_carte(1), DEMI, DEMI),
                   _costume_icone(P, "bus", "bus_carte", _svg_bus, 15, 9),
                   _costume_icone(P, "para_mini", "parachute_carte", _svg_parachute_mini, 7, 8),
                   _costume_icone(P, "coffre_mini", "coffre_carte", _svg_coffre_mini, 4, 4)]
    Pa.visible = False
    Pa.layer = C.CALQUES["Partie"]
    texte.installer(Pa)

    for v in ["t", "tf", "f", "s", "k", "kk", "n", "m", "p", "d", "r", "q", "ang", "angD", "tA", "tF", "nx", "ny", "cx", "cy",
              "dx", "dy", "dist", "lo", "hi", "ok", "i", "dt", "tPrec", "debutLu", "phasePrec", "etapePrec", "etape",
              "dernierCompte", "rangMort", "aJoue", "relache", "premier", "tFin", "bx0", "by0", "bx1", "by1", "bdx", "bdy",
              "busAngle", "nbCoeq", "nbFin", "nbAir", "finCompte", "teinte", "v", "attente", "tPret"]:
        Pa.var(v, 0)
    Pa.var("dernierePartie", "")
    Pa.var("ecranPrec", "")
    Pa.var("nomT", "")
    Pa.var("legendeT", "")
    Pa.liste("zx", [CENTRE] * (NB_PHASES + 1))
    Pa.liste("zy", [CENTRE] * (NB_PHASES + 1))
    Pa.liste("zr", RAYONS)
    Pa.liste("pS", DEBUTS)
    Pa.liste("pA", ATTENTES)
    Pa.liste("pFin", FINS)
    Pa.liste("pD", DEGATS)
    Pa.liste("ox", [o[0] for o in OFFSETS])
    Pa.liste("oy", [o[1] for o in OFFSETS])
    Pa.liste("equipes", [])

    tr = C.tr

    # -----------------------------------------------------------------------
    #  Écran
    # -----------------------------------------------------------------------
    Pa.proc("changer ecran", [("e", "s")], [
        si(non(eq(V("ecran"), A("e"))), [
            setv("ecran", A("e")), setv("menu_sale", 1), diffuser("evt changement ecran"),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  ☁ Partie : écriture, lecture, nouvelle manche
    # -----------------------------------------------------------------------
    Pa.proc("ecrire partie", [], [
        setv("m", rnd(V("modeChoisi"))),
        si(ou(lt(V("m"), 1), gt(V("m"), 6)), [setv("m", 5)]),
        setv("n", rnd(V("ltmChoisi"))),
        si(ou(lt(V("n"), 0), gt(V("n"), 5)), [setv("n", 0)]),
        setv("k", hasard(0, 99)),
        setv("☁ Partie", joins("1", C.rembourrer(V("maintenant"), 5), V("m"), V("n"), C.rembourrer(V("k"), 2))),
        setv("☁ Construction", 1), setv("☁ Construction2", 1),
    ])

    Pa.proc("lire partie", [], [
        setv("tf", mod(mul(jours2000(), 86400), 100000)),
        setv("s", V("☁ Partie")),
        setv("ok", 0),
        si(lt(longueur(V("s")), 10), [setv("ok", 1)], [
            setv("debutLu", mul(C.sous_chaine(V("s"), 2, 5), 1)),
            setv("t", C.ecart(V("tf"), V("debutLu"))),
            setv("f", 1), si(eq(lettre(8, V("s")), 3), [setv("f", 0.5)]),
            si(ou(gt(V("t"), add(mul(C.DUREE_MANCHE, V("f")), C.DUREE_RESULTATS)), lt(V("t"), -5)), [setv("ok", 1)]),
            # manche terminée localement : relance après les résultats (décalée selon l'emplacement pour
            # limiter les écritures simultanées ; si quelqu'un a déjà relancé, debut a changé entre-temps)
            si(et3(eq(V("finManche"), 1), eq(V("debutLu"), V("debut")),
                   gt(V("t"), add(V("tFin"), add(C.DUREE_RESULTATS, mul(sub(V("monSlot"), 1), 2))))), [setv("ok", 1)]),
        ]),
        si(eq(V("ok"), 1), [appel("ecrire partie"), setv("s", V("☁ Partie"))]),
        setv("debutLu", mul(C.sous_chaine(V("s"), 2, 5), 1)),
        setv("t", C.ecart(V("tf"), V("debutLu"))),
        # nouvelle manche dès que la chaîne complète change (debut, mais aussi mode/ltm/graine réécrits dans la même seconde)
        si(ou(eq(V("premier"), 1), non(eq_txt(V("s"), V("dernierePartie")))), [appel("nouvelle manche")]),
        setv("tempsManche", floor(V("t"))),
    ])

    Pa.proc("calculer equipe", [], [
        si(et(mode_equipe(), eq(V("remplissage"), 1)), [
            si(eq(V("mode"), 2), [setv("monEquipe", plafond(div(V("monSlot"), 2)))], [setv("monEquipe", plafond(div(V("monSlot"), 3)))]),
        ], [setv("monEquipe", 0)]),
    ])

    # zones : centre k (k = 1..5) déterministe dans le cercle précédent, à peu près dans la carte
    Pa.proc("calculer zones", [], [
        remplacer("zx", 1, CENTRE), remplacer("zy", 1, CENTRE),
        setv("k", 1),
        repeter(NB_PHASES, [
            setv("ang", mul(alea(V("k"), 1), 360)),
            setv("d", mul(alea(V("k"), 2), sub(item("zr", V("k")), item("zr", add(V("k"), 1))))),
            setv("cx", add(item("zx", V("k")), mul(V("d"), cos(V("ang"))))),
            setv("cy", add(item("zy", V("k")), mul(V("d"), sin(V("ang"))))),
            setv("lo", add(1, mul(item("zr", add(V("k"), 1)), 0.5))), setv("hi", sub(C.TAILLE - 1, mul(item("zr", add(V("k"), 1)), 0.5))),
            si(lt(V("cx"), V("lo")), [setv("cx", V("lo"))]), si(gt(V("cx"), V("hi")), [setv("cx", V("hi"))]),
            si(lt(V("cy"), V("lo")), [setv("cy", V("lo"))]), si(gt(V("cy"), V("hi")), [setv("cy", V("hi"))]),
            # inclusion stricte dans le cercle précédent
            setv("dx", sub(V("cx"), item("zx", V("k")))), setv("dy", sub(V("cy"), item("zy", V("k")))),
            setv("dist", sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
            setv("r", sub(item("zr", V("k")), item("zr", add(V("k"), 1)))),
            si(gt(V("dist"), V("r")), [
                setv("cx", add(item("zx", V("k")), mul(V("dx"), div(V("r"), V("dist"))))),
                setv("cy", add(item("zy", V("k")), mul(V("dy"), div(V("r"), V("dist"))))),
            ]),
            remplacer("zx", add(V("k"), 1), V("cx")), remplacer("zy", add(V("k"), 1), V("cy")),
            changev("k", 1),
        ]),
        setv("angD", mul(alea(NB_PHASES + 1, 3), 360)),       # direction de dérive de la dernière zone
    ])

    # bus : d'un bord à l'autre (toujours ≥ 60 % de la carte), déterministe
    Pa.proc("calculer bus", [], [
        setv("q", mod(V("graine"), 4)),
        setv("p", add(4, mul(alea(NB_PHASES + 2, 1), C.TAILLE - 8))),
        setv("d", add(4, mul(alea(NB_PHASES + 2, 2), C.TAILLE - 8))),
        si(eq(V("q"), 0), [setv("bx0", 0.5), setv("by0", V("p")), setv("bx1", C.TAILLE - 0.5), setv("by1", V("d"))]),
        si(eq(V("q"), 1), [setv("bx0", V("p")), setv("by0", 0.5), setv("bx1", V("d")), setv("by1", C.TAILLE - 0.5)]),
        si(eq(V("q"), 2), [setv("bx0", C.TAILLE - 0.5), setv("by0", V("p")), setv("bx1", 0.5), setv("by1", V("d"))]),
        si(eq(V("q"), 3), [setv("bx0", V("p")), setv("by0", C.TAILLE - 0.5), setv("bx1", V("d")), setv("by1", 0.5)]),
        setv("bdx", sub(V("bx1"), V("bx0"))), setv("bdy", sub(V("by1"), V("by0"))),
        setv("dist", sqrt(add(mul(V("bdx"), V("bdx")), mul(V("bdy"), V("bdy"))))),
        setv("busDirX", div(V("bdx"), V("dist"))), setv("busDirY", div(V("bdy"), V("dist"))),
        si(lt(absv(V("bdx")), 0.0001), [
            si(gt(V("bdy"), 0), [setv("busAngle", 90)], [setv("busAngle", 270)]),
        ], [
            setv("busAngle", atan(div(V("bdy"), V("bdx")))),
            si(lt(V("bdx"), 0), [changev("busAngle", 180)]),
        ]),
        setv("busAngle", mod(V("busAngle"), 360)),
        setv("busX", V("bx0")), setv("busY", V("by0")), setv("busProgression", 0),
    ])

    Pa.proc("nouvelle manche", [], [
        setv("dernierePartie", V("s")), setv("debut", V("debutLu")),
        setv("mode", mul(lettre(7, V("s")), 1)), setv("ltm", mul(lettre(8, V("s")), 1)),
        setv("graine", mul(C.sous_chaine(V("s"), 9, 2), 1)),
        si(ou(lt(V("mode"), 1), gt(V("mode"), 6)), [setv("mode", 5)]),
        setv("f", 1), si(eq(V("ltm"), 3), [setv("f", 0.5)]),
        appel("calculer equipe"), appel("calculer zones"), appel("calculer bus"),
        setv("finManche", 0), setv("victoire", 0), setv("rang", 0), setv("participants", 0), setv("vivants", 0),
        setv("equipesVivantes", 0), setv("rangMort", 0), setv("aJoue", 0), setv("phasePrec", -1), setv("etapePrec", -1),
        setv("dernierCompte", 0), setv("aSaute", 0), setv("zoneEnMouvement", 0), setv("tempsPartie", 0), setv("tFin", 0),
        setv("finCompte", 0),
        setv("zoneX", CENTRE), setv("zoneY", CENTRE), setv("zoneR", C.RAYON_INITIAL), setv("zoneDegats", 0),
        setv("prochaineZoneX", item("zx", 2)), setv("prochaineZoneY", item("zy", 2)), setv("prochaineZoneR", item("zr", 2)),
        # reprise après reconnexion : on garde l'état et la position du joueur (pas de remise à zéro)
        setv("ok", 0),
        si(et4(eq(V("premier"), 1), eq(V("reconnexion"), 1), etat_in(1, 3), ge(V("t"), mul(P1, V("f")))), [
            setv("ok", 1), setv("enPartie", 1), setv("aJoue", 1), setv("invulnerable", 0), setv("altitude", 0),
            appel("changer ecran", "jeu"),
        ]),
        setv("premier", 0),
        si(eq(V("ok"), 0), [
            # seul un joueur en partie est remis au salon (un spectateur venu du salon, enPartie = 0, est conservé)
            si(et(eq(V("enPartie"), 1), non(eq(V("etat"), 5))), [
                setv("etat", 5), setv("invulnerable", 0), setv("altitude", 0), setv("aSaute", 0),
            ]),
            diffuser("evt nouvelle manche"),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Phase courante, zone, bus, annonces
    # -----------------------------------------------------------------------
    def lerp_zone(liste):
        return add(item(liste, V("kk")), mul(sub(item(liste, add(V("kk"), 1)), item(liste, V("kk"))), V("p")))

    Pa.proc("calculer phase", [], [
        setv("f", 1), si(eq(V("ltm"), 3), [setv("f", 0.5)]),
        si(eq(V("finManche"), 1), [
            setv("phase", 8),
            setv("tempsPhase", plafond(sub(add(V("tFin"), C.DUREE_RESULTATS), V("t")))),
            si(lt(V("tempsPhase"), 0), [setv("tempsPhase", 0)]),
            setv("⏱ Zone", 0), setv("tempsAvantZone", 0), setv("zoneEnMouvement", 0),
            # « evt phase » (8) à l'image qui suit « terminer manche » : jamais dans la même image que « evt fin
            # manche », dont les gestionnaires lisent evt_valeur = rang
            si(non(eq(V("phasePrec"), 8)), [setv("phasePrec", 8), setv("evt_valeur", 8), diffuser("evt phase")]),
        ], [
            setv("kk", 0),
            si(ge(V("t"), mul(P1, V("f"))), [
                setv("k", 1),
                repeter(NB_PHASES, [si(ge(V("t"), mul(item("pS", V("k")), V("f"))), [setv("kk", V("k"))]), changev("k", 1)]),
            ]),
            si(eq(V("kk"), 0), [
                # île d'attente et bus : cercle initial, prochaine zone = zone 1
                setv("zoneX", item("zx", 1)), setv("zoneY", item("zy", 1)), setv("zoneR", item("zr", 1)), setv("zoneDegats", 0),
                setv("prochaineZoneX", item("zx", 2)), setv("prochaineZoneY", item("zy", 2)), setv("prochaineZoneR", item("zr", 2)),
                setv("tempsAvantZone", plafond(sub(mul(DEBUTS[0] + ATTENTES[0], V("f")), V("t")))),
                setv("zoneEnMouvement", 0), setv("etape", 0), setv("etapePrec", 0), setv("tempsPartie", 0),
                si(lt(V("t"), mul(P0, V("f"))), [
                    setv("phase", 0),
                    setv("tempsPhase", plafond(sub(mul(P0, V("f")), V("t")))),
                    setv("busProgression", 0),
                    # compte à rebours sonore des 5 dernières secondes
                    si(et(lt(V("tempsPhase"), 6), non(eq(V("tempsPhase"), V("dernierCompte")))), [
                        setv("dernierCompte", V("tempsPhase")),
                        si(gt(V("tempsPhase"), 0), son_si_en_partie("compte")),
                    ]),
                ], [
                    setv("phase", 1),
                    setv("tempsPhase", plafond(sub(mul(P1, V("f")), V("t")))),
                    setv("busProgression", div(sub(V("t"), mul(P0, V("f"))), mul(C.DUREE_BUS, V("f")))),
                ]),
                setv("busX", add(V("bx0"), mul(V("bdx"), V("busProgression")))),
                setv("busY", add(V("by0"), mul(V("bdy"), V("busProgression")))),
                setv("⏱ Zone", V("tempsPhase")),
            ], [
                setv("phase", add(V("kk"), 1)),
                setv("busProgression", 1), setv("busX", V("bx1")), setv("busY", V("by1")),
                setv("tA", mul(add(item("pS", V("kk")), item("pA", V("kk"))), V("f"))),
                setv("tF", mul(item("pFin", V("kk")), V("f"))),
                setv("prochaineZoneX", item("zx", add(V("kk"), 1))), setv("prochaineZoneY", item("zy", add(V("kk"), 1))),
                setv("prochaineZoneR", item("zr", add(V("kk"), 1))),
                si(lt(V("t"), V("tA")), [
                    # attente : zone fixe = cercle précédent
                    setv("zoneX", item("zx", V("kk"))), setv("zoneY", item("zy", V("kk"))), setv("zoneR", item("zr", V("kk"))),
                    setv("tempsAvantZone", plafond(sub(V("tA"), V("t")))),
                    setv("⏱ Zone", V("tempsAvantZone")),
                    setv("zoneDegats", item("pD", maximum(sub(V("kk"), 1), 1))),
                    setv("etape", mul(V("kk"), 2)),
                ], [
                    # rétrécissement : interpolation linéaire centre + rayon
                    setv("p", div(sub(V("t"), V("tA")), sub(V("tF"), V("tA")))),
                    si(gt(V("p"), 1), [setv("p", 1)]),
                    setv("zoneX", lerp_zone("zx")), setv("zoneY", lerp_zone("zy")), setv("zoneR", lerp_zone("zr")),
                    setv("tempsAvantZone", 0),
                    setv("⏱ Zone", plafond(sub(V("tF"), V("t")))),
                    si(lt(V("⏱ Zone"), 0), [setv("⏱ Zone", 0)]),
                    setv("zoneDegats", item("pD", V("kk"))),
                    setv("etape", add(mul(V("kk"), 2), 1)),
                ]),
                setv("tempsPhase", V("⏱ Zone")),
                setv("tempsPartie", floor(sub(V("t"), mul(P1, V("f"))))),
                # dernière zone : le centre dérive en continu (0,04 case/s), borné à la carte
                si(eq(V("kk"), NB_PHASES), [
                    setv("zoneEnMouvement", 1),
                    setv("d", mul(sub(V("t"), mul(item("pS", NB_PHASES), V("f"))), 0.04)),
                    changev("zoneX", mul(V("d"), cos(V("angD")))), changev("zoneY", mul(V("d"), sin(V("angD")))),
                    si(lt(V("zoneX"), 2.5), [setv("zoneX", 2.5)]), si(gt(V("zoneX"), C.TAILLE - 2.5), [setv("zoneX", C.TAILLE - 2.5)]),
                    si(lt(V("zoneY"), 2.5), [setv("zoneY", 2.5)]), si(gt(V("zoneY"), C.TAILLE - 2.5), [setv("zoneY", C.TAILLE - 2.5)]),
                ], [setv("zoneEnMouvement", 0)]),
                # annonces à chaque début de rétrécissement
                si(non(eq(V("etape"), V("etapePrec"))), [
                    si(et3(non(eq(V("etapePrec"), -1)), eq(mod(V("etape"), 2), 1), eq(V("enPartie"), 1)), [
                        si(eq(V("kk"), NB_PHASES), [setv("message", "zonebouge")], [setv("message", "zone")]),
                        son_("tempete"),
                    ]),
                    setv("etapePrec", V("etape")),
                ]),
            ]),
            # changement de phase → "evt phase" (evt_valeur = phase), son du bus
            si(non(eq(V("phase"), V("phasePrec"))), [
                si(et(eq(V("phase"), 1), non(eq(V("phasePrec"), -1))), son_si_en_partie("bus")),
                setv("phasePrec", V("phase")),
                setv("evt_valeur", V("phase")), diffuser("evt phase"),
            ]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Compteurs
    # -----------------------------------------------------------------------
    k = V("k")
    Pa.proc("compter", [], [
        setv("n", 0), setv("m", 0), setv("nbCoeq", 0), setv("nbFin", 0), setv("nbAir", 0), vider("equipes"),
        si(etat_in(1, 3), [
            setv("n", 1),
            si(gt(V("monEquipe"), 0), [ajouter_liste("equipes", V("monEquipe"))], [ajouter_liste("equipes", "moi")]),
        ]),
        si(eq(V("etat"), 2), [setv("m", 1)]),                  # morts seulement : un spectateur (4) n'est pas un participant
        si(et(eq(V("enPartie"), 1), etat_in(6, 7)), [setv("nbAir", 1)]),
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(et(non(eq(k, V("monSlot"))), eq(item("E_actif", k), 1)), [
                si(ou(eq(item("E_etat", k), 1), eq(item("E_etat", k), 3)), [
                    changev("n", 1),
                    si(gt(item("E_equipe", k), 0), [
                        si(non(contient("equipes", item("E_equipe", k))), [ajouter_liste("equipes", item("E_equipe", k))]),
                        si(eq(item("E_equipe", k), V("monEquipe")), [changev("nbCoeq", 1)]),
                    ], [ajouter_liste("equipes", join("s", k))]),
                ]),
                si(eq(item("E_etat", k), 2), [changev("m", 1)]),
                si(ou(eq(item("E_etat", k), 6), eq(item("E_etat", k), 7)), [changev("nbAir", 1)]),
                si(eq(item("E_etat", k), 9), [changev("nbFin", 1)]),
            ]),
            changev("k", 1),
        ]),
        si(eq(V("monEquipe"), 0), [setv("nbCoeq", 0)]),
        setv("vivants", V("n")),
        si(mode_equipe(), [setv("equipesVivantes", long_liste("equipes"))], [setv("equipesVivantes", V("n"))]),
        si(gt(add(V("n"), V("m")), V("participants")), [setv("participants", add(V("n"), V("m")))]),
    ])

    # -----------------------------------------------------------------------
    #  Placement
    # -----------------------------------------------------------------------
    Pa.proc("borner position", [], [
        si(lt(V("px"), MARGE), [setv("px", MARGE)]), si(gt(V("px"), C.TAILLE - MARGE), [setv("px", C.TAILLE - MARGE)]),
        si(lt(V("py"), MARGE), [setv("py", MARGE)]), si(gt(V("py"), C.TAILLE - MARGE), [setv("py", C.TAILLE - MARGE)]),
    ])
    Pa.proc("case libre aleatoire", [], [
        setv("ok", 0),
        repeter(60, [
            si(eq(V("ok"), 0), [
                setv("nx", add(hasard(1, C.TAILLE - 2), 0.5)), setv("ny", add(hasard(1, C.TAILLE - 2), 0.5)),
                si(eq(C.cellule(V("nx"), V("ny")), 0), [setv("ok", 1)]),
            ]),
        ]),
        si(eq(V("ok"), 0), [setv("nx", CENTRE + 0.5), setv("ny", CENTRE + 0.5)]),
    ])
    # case libre la plus proche de (nx, ny) (anneaux de rayon 1 à 3)
    Pa.proc("case libre proche", [], [
        setv("ok", 0), setv("i", 1), setv("cx", floor(V("nx"))), setv("cy", floor(V("ny"))),
        si(eq(C.cellule(V("nx"), V("ny")), 0), [setv("ok", 1)]),
        repeter_jusqua(ou(eq(V("ok"), 1), gt(V("i"), len(OFFSETS))), [
            setv("dx", add(V("cx"), item("ox", V("i")))), setv("dy", add(V("cy"), item("oy", V("i")))),
            si(et4(gt(V("dx"), 0), lt(V("dx"), C.TAILLE - 1), gt(V("dy"), 0), lt(V("dy"), C.TAILLE - 1)), [
                si(eq(C.cellule(V("dx"), V("dy")), 0), [setv("nx", add(V("dx"), 0.5)), setv("ny", add(V("dy"), 0.5)), setv("ok", 1)]),
            ]),
            changev("i", 1),
        ]),
        si(eq(V("ok"), 0), [setv("nx", CENTRE + 0.5), setv("ny", CENTRE + 0.5)]),
    ])
    Pa.proc("case libre dans zone", [], [
        setv("r", sub(V("zoneR"), 1)), si(lt(V("r"), 1), [setv("r", 1)]),
        setv("ok", 0),
        repeter(60, [
            si(eq(V("ok"), 0), [
                setv("nx", add(floor(add(V("zoneX"), hasard(mul(V("r"), -1), V("r")))), 0.5)),
                setv("ny", add(floor(add(V("zoneY"), hasard(mul(V("r"), -1), V("r")))), 0.5)),
                si(et4(gt(V("nx"), 1), lt(V("nx"), C.TAILLE - 1), gt(V("ny"), 1), lt(V("ny"), C.TAILLE - 1)), [
                    si(et(eq(C.cellule(V("nx"), V("ny")), 0),
                          lt(dist2(V("nx"), V("ny"), V("zoneX"), V("zoneY")), mul(V("r"), V("r")))), [setv("ok", 1)]),
                ]),
            ]),
        ]),
        si(eq(V("ok"), 0), [
            setv("nx", V("zoneX")), setv("ny", V("zoneY")),
            si(lt(V("nx"), MARGE), [setv("nx", MARGE)]), si(gt(V("nx"), C.TAILLE - MARGE), [setv("nx", C.TAILLE - MARGE)]),
            si(lt(V("ny"), MARGE), [setv("ny", MARGE)]), si(gt(V("ny"), C.TAILLE - MARGE), [setv("ny", C.TAILLE - MARGE)]),
            appel("case libre proche"),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Bus, saut, parachute, atterrissage
    # -----------------------------------------------------------------------
    Pa.proc("sauter", [], [
        setv("etat", 7), setv("aSaute", 1), setv("altitude", 99), setv("invulnerable", 1), setv("hauteur", 0),
        appel("changer ecran", "parachute"),
    ] + son_si_en_partie("parachute"))

    Pa.proc("atterrir", [], [
        setv("nx", V("px")), setv("ny", V("py")),
        si(non(eq(C.cellule(V("nx"), V("ny")), 0)), [appel("case libre proche")]),
        setv("px", V("nx")), setv("py", V("ny")),
        setv("etat", 1), setv("altitude", 0), setv("invulnerable", 0), setv("hauteur", 0), setv("redeploiement", 0), setv("aJoue", 1),
        appel("changer ecran", "jeu"),
        diffuser("evt atterrissage"), setv("message", "atterrissage"),
    ])

    def avance(signe):
        return [changev("px", mul(cos(V("dir")), mul(V("v"), signe))), changev("py", mul(sin(V("dir")), mul(V("v"), signe)))]

    def lateral(signe):   # vecteur droite = (sin, -cos), comme Joueur
        return [changev("px", mul(sin(V("dir")), mul(V("v"), signe))), changev("py", mul(cos(V("dir")), mul(V("v"), -signe)))]

    Pa.proc("parachute", [], [
        setv("invulnerable", 1),
        # chute : 8/s, puis 4/s sous 30 (le planeur s'ouvre)
        si(gt(V("altitude"), 30), [changev("altitude", mul(V("dt"), -8))], [changev("altitude", mul(V("dt"), -4))]),
        setv("v", 0.12),
        si(ou(tc("avancer"), touche("up arrow")), avance(1)),
        si(ou(tc("reculer"), touche("down arrow")), avance(-1)),
        si(tc("droite"), lateral(1)),
        si(tc("gauche"), lateral(-1)),
        si(touche("left arrow"), [changev("dir", mul(3, V("param_sensibilite")))]),
        si(touche("right arrow"), [changev("dir", mul(-3, V("param_sensibilite")))]),
        setv("dir", mod(V("dir"), 360)),
        appel("borner position"),
        si(le(V("altitude"), 0), [appel("atterrir")]),
    ])

    # -----------------------------------------------------------------------
    #  État du joueur local selon la phase
    # -----------------------------------------------------------------------
    souris_dans_scene = et3(souris_bas(), lt(absv(souris_x()), 241), lt(absv(souris_y()), 181))
    pas_en_attente = eq(V("attente"), 0)
    Pa.proc("joueur", [], [
        # écrans d'attente de Menus : on ne prend pas le joueur pendant le compte à rebours de matchmaking, ni pendant
        # les 2,5 s de la barre de chargement (Menus affiche ensuite « Prêt — en attente de la partie… »)
        setv("attente", 0),
        si(eq(V("ecran"), "matchmaking"), [setv("attente", 1)]),
        si(eq(V("ecran"), "chargement"), [
            si(non(eq(V("ecranPrec"), "chargement")), [setv("tPret", add(chrono(), 2.5))]),
            si(lt(chrono(), V("tPret")), [setv("attente", 1)]),
        ]),
        setv("ecranPrec", V("ecran")),
        si(eq(V("enPartie"), 0), [
            # retour au salon : Menus remet etat = 5 ; on ne nettoie que nos variables. Un état forcé par un test ou un
            # autre module (1..3, 6..8) n'est jamais touché ici. L'état « fin » (9) n'appartient qu'à Partie : « Rejouer »
            # puis « Annuler » le laisserait au salon, où il serait publié et ferait finir la manche suivante des autres.
            si(eq(V("etat"), 9), [setv("etat", 5)]),
            si(et(eq(V("etat"), 5), ou3(eq(V("invulnerable"), 1), gt(V("altitude"), 0), eq(V("aSaute"), 1))),
               [setv("invulnerable", 0), setv("altitude", 0), setv("aSaute", 0)]),
        ], [
            si(eq(V("phase"), 8), [
                # arrivée pendant les résultats : spectateur jusqu'à la manche suivante, sauf si Menus affiche encore
                # l'attente (matchmaking / chargement : le joueur y reste jusqu'à la nouvelle manche)
                si(et3(eq(V("etat"), 5), pas_en_attente, non(eq(V("ecran"), "chargement"))),
                   [setv("etat", 4), appel("changer ecran", "spectateur")]),
            ]),
            si(et(eq(V("phase"), 0), pas_en_attente), [
                si(non(etat_in(4, 8)), [
                    appel("case libre aleatoire"),
                    setv("px", V("nx")), setv("py", V("ny")), setv("dir", hasard(0, 359)), setv("hauteur", 0),
                    setv("etat", 8), setv("invulnerable", 1), setv("altitude", 0), setv("aSaute", 0),
                    appel("changer ecran", "jeu"), setv("message", "prepartie"),
                ]),
            ]),
            si(eq(V("phase"), 1), [
                # embarquement des joueurs qui ne sont pas encore partis (salon, île, fin) ; un joueur qui a déjà
                # sauté ou atterri pendant la phase (etat 7, 1) garde son état
                si(et(etat_in(5, 8, 9), pas_en_attente), [
                    setv("etat", 6), setv("aSaute", 0), setv("invulnerable", 1), setv("altitude", 99), setv("relache", 0),
                    setv("hauteur", 0), appel("changer ecran", "bus"), setv("message", "bus"),
                ]),
                si(eq(V("etat"), 6), [
                    setv("px", V("busX")), setv("py", V("busY")), appel("borner position"),
                    setv("dir", V("busAngle")), setv("altitude", 99),
                    si(ou(tc("sauter"), souris_dans_scene), [si(eq(V("relache"), 1), [appel("sauter")])], [setv("relache", 1)]),
                ]),
            ]),
            si(et(ge(V("phase"), 2), lt(V("phase"), 8)), [
                si(eq(V("etat"), 6), [appel("sauter")]),                   # fin du bus : saut automatique
                si(et(etat_in(5, 8, 9), pas_en_attente), [                   # arrivée en retard
                    si(lt(V("phase"), 6), [
                        appel("case libre dans zone"),
                        setv("px", V("nx")), setv("py", V("ny")), setv("dir", hasard(0, 359)), setv("hauteur", 0),
                        setv("etat", 7), setv("altitude", 99), setv("invulnerable", 1), setv("aSaute", 1),
                        appel("changer ecran", "parachute"),
                    ], [
                        setv("etat", 4), setv("invulnerable", 0), setv("altitude", 0), appel("changer ecran", "spectateur"),
                    ]),
                ]),
            ]),
            si(eq(V("etat"), 7), [appel("parachute")]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Fin de manche et rang
    # -----------------------------------------------------------------------
    mes_elims = V("💀 Éliminations")
    actif_autre = et(non(eq(k, V("monSlot"))), eq(item("E_actif", k), 1))
    autre_vivant = ou(eq(item("E_etat", k), 1), eq(item("E_etat", k), 3))
    autre_ennemi = ou(eq(V("monEquipe"), 0), non(eq(item("E_equipe", k), V("monEquipe"))))

    Pa.proc("calculer rang", [], [
        setv("n", 0), setv("k", 1),
        si(eq(V("mode"), 5), [
            # Rumble : classement aux éliminations parmi les joueurs actifs
            repeter(C.NB_JOUEURS, [si(et(actif_autre, gt(item("E_elims", k), mes_elims)), [changev("n", 1)]), changev("k", 1)]),
            setv("rang", add(V("n"), 1)),
        ], [
            setv("ok", 0),
            si(etat_in(1, 3), [setv("ok", 1)]),
            si(et(mode_equipe(), gt(V("nbCoeq"), 0)), [setv("ok", 1)]),      # mon équipe est encore en vie
            si(eq(V("ok"), 1), [
                si(mode_equipe(), [
                    si(le(V("equipesVivantes"), 1), [setv("rang", 1)], [
                        repeter(C.NB_JOUEURS, [si(et4(actif_autre, autre_vivant, autre_ennemi, gt(item("E_elims", k), mes_elims)),
                                                  [changev("n", 1)]), changev("k", 1)]),
                        setv("rang", add(V("n"), 1)),
                        si(gt(V("rang"), V("equipesVivantes")), [setv("rang", V("equipesVivantes"))]),
                    ]),
                ], [
                    si(le(V("vivants"), 1), [setv("rang", 1)], [
                        repeter(C.NB_JOUEURS, [si(et3(actif_autre, autre_vivant, gt(item("E_elims", k), mes_elims)),
                                                  [changev("n", 1)]), changev("k", 1)]),
                        setv("rang", add(V("n"), 1)),
                    ]),
                ]),
            ], [
                si(gt(V("rangMort"), 0), [setv("rang", V("rangMort"))], [
                    si(mode_equipe(), [setv("rang", maximum(2, add(V("equipesVivantes"), 1)))],
                       [setv("rang", maximum(2, add(V("vivants"), 1)))]),
                ]),
            ]),
        ]),
    ])

    Pa.proc("terminer manche", [], [
        setv("finManche", 1), setv("phase", 8), setv("tFin", V("t")), setv("tempsAvantZone", 0), setv("⏱ Zone", 0),
        setv("zoneEnMouvement", 0),
        si(eq(V("enPartie"), 1), [
            appel("calculer rang"),
            setv("victoire", 0),
            si(eq(V("rang"), 1), [
                setv("victoire", 1), setv("message", "victoire"), diffuser("evt victoire"), changev("stat_victoires", 1),
            ] + son_("victoire"), [setv("message", "defaite")] + son_("defaite")),
            changev("stat_parties", 1),
            si(le(V("rang"), 3), [changev("stat_top3", 1)]),
            si(ou(eq(V("stat_meilleurRang"), 0), lt(V("rang"), V("stat_meilleurRang"))), [setv("stat_meilleurRang", V("rang"))]),
            setv("evt_valeur", V("rang")), diffuser("evt fin manche"),
            setv("etat", 9), setv("invulnerable", 0), setv("altitude", 0),
            appel("changer ecran", "fin"),
        ]),
    ])

    Pa.proc("fin de manche", [], [
        si(et3(eq(V("finManche"), 0), ge(V("phase"), 2), lt(V("phase"), 8)), [
            # rang mémorisé à ma mort (ou à l'élimination de mon équipe)
            si(et4(eq(V("enPartie"), 1), eq(V("rangMort"), 0), eq(V("aJoue"), 1), etat_in(2, 4)), [
                si(mode_equipe(), [
                    si(eq(V("nbCoeq"), 0), [setv("rangMort", maximum(2, add(V("equipesVivantes"), 1))), setv("rang", V("rangMort"))]),
                ], [
                    si(non(eq(V("mode"), 5)), [setv("rangMort", maximum(2, add(V("vivants"), 1))), setv("rang", V("rangMort"))]),
                ]),
            ]),
            setv("ok", 0),
            si(ge(V("t"), mul(C.DUREE_MANCHE, V("f"))), [setv("ok", 1)]),
            si(gt(V("nbFin"), 0), [setv("ok", 1)]),                           # un autre joueur a déjà vu la fin
            # fin par élimination : au moins 2 participants, personne encore en l'air (bus/parachute), et la
            # condition doit tenir FIN_STABLE images de suite (Reseau décode un emplacement par image : les
            # listes E_* peuvent être transitoirement incohérentes pendant un balayage)
            setv("q", 0),
            si(et(ge(V("participants"), 2), eq(V("nbAir"), 0)), [
                si(mode_equipe(), [si(le(V("equipesVivantes"), 1), [setv("q", 1)])], [
                    si(non(eq(V("mode"), 5)), [si(le(V("vivants"), 1), [setv("q", 1)])]),
                ]),
            ]),
            si(eq(V("q"), 1), [changev("finCompte", 1), si(ge(V("finCompte"), FIN_STABLE), [setv("ok", 1)])], [setv("finCompte", 0)]),
            si(eq(V("ok"), 1), [appel("terminer manche")]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Dessin plein écran : bus, parachute, carte
    # -----------------------------------------------------------------------
    Pa.proc("cercle carte", [("cx", "n"), ("cy", "n"), ("r", "n")], [
        stylo_haut(), aller(mx(add(A("cx"), A("r"))), my(A("cy"))), stylo_bas(), setv("ang", 0),
        repeter(36, [
            changev("ang", 10),
            aller(mx(add(A("cx"), mul(A("r"), cos(V("ang"))))), my(add(A("cy"), mul(A("r"), sin(V("ang")))))),
        ]),
        stylo_haut(),
    ])
    Pa.proc("tamponner", [("c", "s"), ("x", "n"), ("y", "n"), ("d", "n")], [
        costume(A("c")), taille(100), pointer(A("d")), aller(mx(A("x")), my(A("y"))), tampon(), pointer(90),
    ])

    def touche_nom(nom):
        return C.touche_config(nom)

    # nom lisible d'une touche configurée → nomT (« space » → Espace, flèches → ← → ↑ ↓)
    Pa.proc("nom touche", [("k", "s")], [
        setv("nomT", A("k")),
        si(eq(A("k"), "space"), [setv("nomT", tr("Espace", "Space"))]),
        si(eq(A("k"), "up arrow"), [setv("nomT", "↑")]), si(eq(A("k"), "down arrow"), [setv("nomT", "↓")]),
        si(eq(A("k"), "left arrow"), [setv("nomT", "←")]), si(eq(A("k"), "right arrow"), [setv("nomT", "→")]),
    ])

    def ajouter_touche(nom):
        return [appel("nom touche", touche_nom(nom)), setv("legendeT", join(V("legendeT"), V("nomT")))]

    Pa.proc("legendes", [], [
        # bandeaux haut et bas
        couleur_hsbt(60, 40, 8, 35), taille_stylo(30), ligne(-240, 150, 240, 150), ligne(-240, -150, 240, -150),
        si(eq(V("ecran"), "bus"), [
            ecrire(joins(tr("BUS DE COMBAT", "BATTLE BUS"), " | ", tr("saut automatique dans ", "auto-jump in "), V("tempsPhase"), " s"),
                   0, 144, 15, "cyan", 1),
            appel("nom touche", touche_nom("sauter")),
            ecrire(join(V("nomT"), tr(" / clic : sauter du bus", " / click: jump from the bus")), 0, -156, 14, "blanc", 1),
        ]),
        si(eq(V("ecran"), "parachute"), [
            si(gt(V("altitude"), 30), [ecrire(tr("CHUTE LIBRE", "FREE FALL"), 0, 144, 15, "cyan", 1)],
               [ecrire(tr("PLANEUR", "GLIDER"), 0, 144, 15, "cyan", 1)]),
            ecrire(tr("ALTITUDE", "ALTITUDE"), -200, 40, 12, "gris", 1),
            appel("ecrire nombre", V("altitude"), -200, 6, 30, "blanc", 1),
            setv("legendeT", ""),
        ] + ajouter_touche("avancer") + ajouter_touche("gauche") + ajouter_touche("reculer") + ajouter_touche("droite") + [
            ecrire(join(V("legendeT"), tr(" : diriger | ← → : tourner", ": steer | ← →: turn")), 0, -156, 13, "blanc", 1),
        ]),
        si(eq(V("ecran"), "carte"), [
            ecrire(tr("CARTE", "MAP"), 0, 144, 15, "cyan", 1),
            appel("nom touche", touche_nom("carte")),
            ecrire(join(V("nomT"), tr(" : fermer", ": close")), 0, -156, 14, "blanc", 1),
        ]),
        # colonne droite, entre le bord de la carte (x = 160) et l'altimètre du HUD (x > 210) : libellés en taille 10
        # (« Zone dans » mesure 49 px), nombres en 24
        si(gt(V("tempsAvantZone"), 0), [
            ecrire(tr("Zone dans", "Zone in"), COL_D, 60, 10, "gris", 1),
            appel("ecrire nombre", V("tempsAvantZone"), COL_D, 30, 24, "violet", 1),
        ], [
            ecrire(tr("Zone", "Zone"), COL_D, 60, 10, "gris", 1),
            appel("ecrire nombre", V("⏱ Zone"), COL_D, 30, 24, "violet", 1),
        ]),
        # joueurs connectés avant le combat (île, bus), joueurs en vie ensuite
        si(lt(V("phase"), 2), [
            ecrire(tr("Joueurs", "Players"), COL_D, -30, 10, "gris", 1),
            appel("ecrire nombre", V("👥 Joueurs"), COL_D, -60, 24, "blanc", 1),
        ], [
            ecrire(tr("En vie", "Alive"), COL_D, -30, 10, "gris", 1),
            appel("ecrire nombre", V("vivants"), COL_D, -60, 24, "blanc", 1),
        ]),
        # colonne gauche : mode et événement limité
        si(non(eq(V("ecran"), "parachute")), [
            ecrire(item("ModeNoms", add(V("mode"), mul(len(C.MODES), V("param_langue")))), -200, 40, 13, "or", 1),
            si(gt(V("ltm"), 0), [appel("ecrire tronque", item("LTMNoms", add(add(V("ltm"), 1), mul(len(C.LTM), V("param_langue")))),
                                       -200, 18, 11, "rose", 1, 78)]),
        ]),
    ])

    Pa.proc("dessiner carte", [], [
        effacer(),
        si(eq(V("param_langue"), 1), [costume("carte_en")], [costume("carte_fr")]),
        taille(100), pointer(90), aller(0, 0), tampon(),
        # teinte de la zone selon le daltonisme (comme Moteur3D)
        setv("teinte", 80),
        si(ou(eq(V("param_daltonisme"), 1), eq(V("param_daltonisme"), 2)), [setv("teinte", 52)]),
        si(eq(V("param_daltonisme"), 3), [setv("teinte", 12)]),
        # halo de tempête puis cercle de zone
        si(lt(V("zoneR"), C.TAILLE + 4), [
            couleur_hsbt(V("teinte"), 80, 70, 60), taille_stylo(10),
            appel("cercle carte", V("zoneX"), V("zoneY"), add(V("zoneR"), 0.5)),
            couleur_hsbt(V("teinte"), 85, 95, 0), taille_stylo(3),
            appel("cercle carte", V("zoneX"), V("zoneY"), V("zoneR")),
        ]),
        si(et(gt(V("tempsAvantZone"), 0), lt(V("prochaineZoneR"), V("zoneR"))), [
            couleur_hsbt(0, 0, 100, 10), taille_stylo(2),
            appel("cercle carte", V("prochaineZoneX"), V("prochaineZoneY"), V("prochaineZoneR")),
        ]),
        # trajectoire du bus (pointillés) et icône du bus pendant l'île d'attente et le bus
        si(lt(V("phase"), 2), [
            couleur_hsbt(0, 0, 100, 25), taille_stylo(2), setv("i", 0),
            repeter(20, [
                setv("p", div(V("i"), 20)),
                ligne(mx(add(V("bx0"), mul(V("bdx"), V("p")))), my(add(V("by0"), mul(V("bdy"), V("p")))),
                      mx(add(V("bx0"), mul(V("bdx"), add(V("p"), 0.025)))), my(add(V("by0"), mul(V("bdy"), add(V("p"), 0.025))))),
                changev("i", 1),
            ]),
            appel("tamponner", "bus", V("busX"), V("busY"), sub(90, V("busAngle"))),
        ]),
        # balises de redéploiement (modes équipe)
        si(gt(V("monEquipe"), 0), [
            couleur_hsbt(55, 90, 100, 0), setv("k", 1),
            repeter(C.NB_BALISES, [point(item("BalisesX", k), item("BalisesY", k), 7), changev("k", 1)]),
        ]),
        # coffres non ouverts
        setv("k", 1),
        repeter(C.NB_COFFRES, [
            si(non(contient("CoffresPris", k)), [appel("tamponner", "coffre_mini", item("CoffresX", k), item("CoffresY", k), 90)]),
            changev("k", 1),
        ]),
        # pings (k xxxx yyyy eeeeee)
        couleur_hsbt(15, 95, 100, 0), setv("k", 1),
        repeter(long_liste("Pings"), [
            si(gt(C.sous_chaine(item("Pings", k), 10, 6), mul(chrono(), 10)), [
                point(div(C.sous_chaine(item("Pings", k), 2, 4), 100), div(C.sous_chaine(item("Pings", k), 6, 4), 100), 8),
            ]),
            changev("k", 1),
        ]),
        # autres joueurs : coéquipiers (verts) et joueurs en l'air (coéquipiers, ou tout le monde en Rumble)
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(actif_autre, [
                si(et(gt(V("monEquipe"), 0), eq(item("E_equipe", k), V("monEquipe"))), [
                    si(gt(item("E_altitude", k), 0), [appel("tamponner", "para_mini", item("E_x", k), item("E_y", k), 90)], [
                        si(autre_vivant, [couleur_hsbt(38, 90, 95, 0)] + point(item("E_x", k), item("E_y", k), 7)),
                    ]),
                ], [
                    si(et(eq(V("mode"), 5), gt(item("E_altitude", k), 0)), [appel("tamponner", "para_mini", item("E_x", k), item("E_y", k), 90)]),
                ]),
            ]),
            changev("k", 1),
        ]),
        # moi : point blanc + direction, parachute si en l'air
        couleur_hsbt(0, 0, 100, 0), point(V("px"), V("py"), 7),
        taille_stylo(2),
        ligne(mx(V("px")), my(V("py")), add(mx(V("px")), mul(cos(V("dir")), 12)), add(my(V("py")), mul(sin(V("dir")), 12))),
        si(gt(V("altitude"), 0), [appel("tamponner", "para_mini", V("px"), V("py"), 90)]),
        appel("legendes"),
    ])

    # -----------------------------------------------------------------------
    #  Boucle principale
    # -----------------------------------------------------------------------
    ecran_carte = eq(V("ecran"), ECRANS_CARTE[0])
    for e in ECRANS_CARTE[1:]:
        ecran_carte = ou(ecran_carte, eq(V("ecran"), e))

    Pa.script(quand_drapeau(), [
        cacher(), aller(0, 0), pointer(90), taille(100), costume("carte_fr"),
        setv("txt_ombre", 0),
        setv("premier", 1), setv("debutLu", -1), setv("tPrec", chrono()), setv("phasePrec", -1), setv("etapePrec", -1),
        setv("rangMort", 0), setv("aJoue", 0), setv("tFin", 0), setv("relache", 0), setv("dernierCompte", 0),
        setv("finManche", 0), setv("victoire", 0), setv("rang", 0), setv("participants", 0), setv("vivants", 1),
        setv("equipesVivantes", 1), setv("aSaute", 0), setv("busProgression", 0), setv("zoneEnMouvement", 0), setv("tempsPartie", 0),
        setv("tempsManche", 0), setv("tempsPhase", 0), setv("tempsAvantZone", 0), setv("⏱ Zone", 0),
        setv("bx0", 0.5), setv("by0", CENTRE), setv("bx1", C.TAILLE - 0.5), setv("by1", CENTRE), setv("bdx", C.TAILLE - 1), setv("bdy", 0),
        setv("busAngle", 0), setv("busX", 0.5), setv("busY", CENTRE), setv("busDirX", 1), setv("busDirY", 0),
        toujours([
            setv("dt", sub(chrono(), V("tPrec"))), setv("tPrec", chrono()),
            si(gt(V("dt"), 0.1), [setv("dt", 0.1)]), si(lt(V("dt"), 0), [setv("dt", 0)]),
            si(eq(V("connecte"), 1), [
                appel("lire partie"),
                appel("calculer equipe"),
                # hors partie (enPartie = 0), seuls le salon (etat 5), le spectateur (4) et l'état « fin » (9, remis à 5)
                # suivent la manche ; un état forcé par un test ou un autre module (1..3, 6..8) garde sa zone, sa phase
                # et son état
                si(ou(eq(V("enPartie"), 1), etat_in(4, 5, 9)), [
                    appel("calculer phase"),
                    appel("joueur"),          # transitions d'état (placement, bus, saut, parachute, retardataire)
                    appel("compter"),         # compteurs à jour APRÈS les transitions (nbAir, vivants…)
                    appel("fin de manche"),
                ]),
            ]),
            si(ecran_carte, [appel("dessiner carte")]),
        ]),
    ])
    return Pa
