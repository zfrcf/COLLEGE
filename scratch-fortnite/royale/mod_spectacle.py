# -*- coding: utf-8 -*-
"""
MODULE SPECTACLE — sprite « Spectacle » (calque 85 : s'exécute APRÈS HUD (90), Social (89), Menus (88) et
dessine donc par-dessus leurs panneaux au stylo ; un sprite visible à ce calque passe au-dessus de tous les
sprites visibles du jeu, Message compris).

Effets
------
- Écran « fin » (Moteur3D efface chaque image, Menus dessine son panneau, puis moi) :
  victoire = 1 → feux d'artifice au stylo (NB_FUSEES fusées en permanence : montée 0,8 s puis explosion de
  NB_RAYONS traits colorés qui s'éloignent, retombent et s'estompent sur 1,5 s, puis nouvelle fusée) + confettis
  qui tombent en tournoyant ; « son explosion » discret et spatialisé à chaque explosion (au plus un par 0,4 s).
  Défaite → pluie lente de petites particules grises.
- En jeu (écrans jeu / prepartie / spectateur, superposition vide) :
  · bannière centrale animée (texte qui grossit, se stabilise 1,3 s puis se rétracte ; 2 s au total, file
    d'attente) sur « evt elimination » : DOUBLE / TRIPLE ÉLIMINATION !, QUADRUPLE !, MONSTRUEUX ! (serie ≥ 2),
    RAMPAGE / LÉGENDE (💀 Éliminations = 5 / 10), TÊTE DE SÉRIE (premier aux éliminations avec ≥ 3, une fois par
    manche) ; « son serie » à chaque bannière ;
  · annonces (bandeau sombre pleine largeur, texte qui glisse depuis le bord gauche, se tient, repart à droite ;
    2,6 s, file d'attente) : LA TEMPÊTE AVANCE (evt phase 3..5), DERNIÈRE ZONE (evt phase 6), IL RESTE 3 / 2
    JOUEURS (vivants qui descend à 3 ou 2 en partie), NIVEAU N (evt niveau) accompagné de NB_ETOILES étoiles
    qui tombent. (« LARGAGE REPÉRÉ » attendrait une globale largage_actif qui n'existe pas : non branché.)
    Les files sont vidées à « evt nouvelle manche » / « evt fin manche » ; une entrée qui attend depuis plus de
    DELAI_FILE s (écran non compatible : pause, carte…) est abandonnée.
- Salon : CLONES visibles (aucun stylo, donc rien à redessiner : Menus ne redessine le salon que sur menu_sale) :
  NB_BORDURE éclats qui défilent le long du bord de l'écran (jamais au centre), NB_ECLATS éclats qui montent
  autour du personnage (onglet accueil), halo pulsant autour du personnage, halo jaune pulsant autour du
  bouton JOUER (zone x ∈ [-30, 140], y ∈ [-176, -146] de mod_menus.salon_bas). Les clones vivent toute la
  session, cachés hors du salon ; ils ne réagissent à aucun événement.

Coût : ≤ 150 opérations stylo/tampons par image (victoire : 5 × 14 traits + 24 confettis ≈ 94 ; bannière :
une pilule + les glyphes). Dessin une seule fois par valeur du chronomètre (comme le HUD).

Variables globales privées : spc_particules (opérations stylo de la dernière image, 0 hors de l'écran fin),
spc_banniere (texte de la bannière en cours, "" sinon). Textes via contrat.tr (FR/EN).
Sons utilisés : explosion, serie (sons supplémentaires fournis par royale/sons.py).
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S
from . import texte

ORDRE = 80
V = Var
A = Arg

CALQUE = 85
NB_FUSEES, NB_RAYONS = 5, 14
NB_CONFETTIS, NB_PLUIE, NB_ETOILES = 24, 30, 16
NB_BORDURE, NB_ECLATS = 12, 6
DERNIERE_PHASE = len(C.PHASES_TEMPETE) + 1          # phase de la dernière zone (6)
# bord de l'écran parcouru par les éclats du salon
BX, BY = 238, 178
PERIM = 2 * (2 * BX + 2 * BY)
# positions (mod_menus) : bouton JOUER et personnage de l'onglet accueil
JOUER_X, JOUER_Y = 55, -161
PERSO_X, PERSO_Y = -188, 60
Y_BANNIERE = -66          # ligne de base de la bannière de série
Y_ANNONCE = -24           # centre du bandeau d'annonce
DELAI_FILE = 5            # une bannière / annonce en attente depuis plus de 5 s (hors écran de jeu) est abandonnée


def tr(fr, en):
    return C.tr(fr, en)


# ---------------------------------------------------------------------------
#  Costumes
# ---------------------------------------------------------------------------
def _svg_etoile():
    """Éclat à quatre pointes (32 × 32), blanc à cœur doré."""
    return S.svg(32, 32, '<path d="M16 1 Q18 13 31 16 Q18 19 16 31 Q14 19 1 16 Q14 13 16 1 Z" fill="#ffffff"/>'
                         '<path d="M16 7 Q17 15 25 16 Q17 17 16 25 Q15 17 7 16 Q15 15 16 7 Z" fill="#fde68a"/>'
                         '<circle cx="16" cy="16" r="2.2" fill="#fbbf24"/>')


def _svg_halo_jouer():
    """Anneau jaune diffus (200 × 60) : intérieur transparent, le bouton reste lisible."""
    return S.svg(200, 60, '<rect x="7" y="7" width="186" height="46" rx="16" fill="none" stroke="#facc15" stroke-width="10" stroke-opacity="0.22"/>'
                          '<rect x="7" y="7" width="186" height="46" rx="16" fill="none" stroke="#fde047" stroke-width="5" stroke-opacity="0.5"/>'
                          '<rect x="7" y="7" width="186" height="46" rx="16" fill="none" stroke="#fef9c3" stroke-width="1.5" stroke-opacity="0.95"/>')


def _svg_halo_perso():
    """Halo radial violet (160 × 160) : centre transparent, lueur en anneau qui s'évanouit vers l'extérieur."""
    return S.svg(160, 160, '<defs><radialGradient id="h" cx="0.5" cy="0.5" r="0.5">'
                           '<stop offset="0" stop-color="#a78bfa" stop-opacity="0"/><stop offset="0.44" stop-color="#a78bfa" stop-opacity="0"/>'
                           '<stop offset="0.6" stop-color="#c4b5fd" stop-opacity="0.5"/><stop offset="0.78" stop-color="#a78bfa" stop-opacity="0.18"/>'
                           '<stop offset="1" stop-color="#a78bfa" stop-opacity="0"/></radialGradient></defs>'
                           '<circle cx="80" cy="80" r="80" fill="url(#h)"/>')


# ---------------------------------------------------------------------------
#  Construction
# ---------------------------------------------------------------------------
def construire(P):
    Sp = Cible(P, "Spectacle")
    Sp.visible = False
    Sp.layer = CALQUE
    Sp.costumes = [P.costume("vide", S.svg_vide(), 2, 2),
                   P.costume("spc_etoile", _svg_etoile(), 16, 16),
                   P.costume("spc_halo_jouer", _svg_halo_jouer(), 100, 30),
                   P.costume("spc_halo_perso", _svg_halo_perso(), 80, 80)]
    texte.installer(Sp)
    for v in ["estClone", "role", "k", "clonesFaits", "dernierDessin", "i", "a", "p", "r", "t", "x", "y", "qx", "qy",
              "w", "h", "ang", "s", "n", "teteSerie", "vivantsAvant", "ecranAvant", "tFin0", "dernierBoum",
              "banTexte", "banCouleur", "banDebut", "annTexte", "annCouleur", "annDebut", "annEtoiles", "etoDebut", "elims"]:
        Sp.var(v, 0)
    for l in ["fx", "fy", "ft", "fh", "fo", "cx", "cp", "ch", "cv", "file", "fileC", "fileT", "fileA", "fileAC", "fileAE", "fileAT"]:
        Sp.liste(l, [])
    P.stage.var("spc_particules", 0)
    P.stage.var("spc_banniere", "")

    chr_ = chrono()
    i = V("i")
    en_jeu = ou3(eq(V("ecran"), "jeu"), eq(V("ecran"), "prepartie"), eq(V("ecran"), "spectateur"))
    original = eq(V("estClone"), 0)

    # ------------------------------------------------------------------
    #  Listes de particules
    # ------------------------------------------------------------------
    Sp.proc("fusee nouvelle", [("i", "n"), ("delai", "n")], [
        remplacer("fx", A("i"), hasard(-175, 175)), remplacer("fy", A("i"), hasard(82, 128)),
        remplacer("ft", A("i"), add(chr_, A("delai"))), remplacer("fh", A("i"), hasard(0, 100)),
        remplacer("fo", A("i"), hasard(0, 25)),
    ])
    Sp.proc("init listes", [], [
        vider("fx"), vider("fy"), vider("ft"), vider("fh"), vider("fo"),
        repeter(NB_FUSEES, [ajouter_liste("fx", 0), ajouter_liste("fy", 100), ajouter_liste("ft", 0), ajouter_liste("fh", 0), ajouter_liste("fo", 0)]),
        vider("cx"), vider("cp"), vider("ch"), vider("cv"),
        repeter(max(NB_CONFETTIS, NB_PLUIE, NB_ETOILES), [
            ajouter_liste("cx", hasard(-232, 232)), ajouter_liste("cp", hasard(0, 359)),
            ajouter_liste("ch", hasard(0, 100)), ajouter_liste("cv", hasard(45, 85)),
        ]),
    ])
    Sp.proc("entrer fin", [], [
        setv("tFin0", chr_), setv("dernierBoum", 0), setv("i", 1),
        repeter(NB_FUSEES, [appel("fusee nouvelle", i, mul(sub(i, 1), 0.4)), changev("i", 1)]),
    ])

    # ------------------------------------------------------------------
    #  Feux d'artifice (victoire) et pluie grise (défaite)
    # ------------------------------------------------------------------
    rayons = [
        ligne(add(V("x"), mul(sin(V("ang")), mul(V("r"), 0.55))), sub(add(V("y"), mul(cos(V("ang")), mul(V("r"), 0.55))), mul(V("t"), 0.6)),
              add(V("x"), mul(sin(V("ang")), V("r"))), sub(add(V("y"), mul(cos(V("ang")), V("r"))), V("t"))),
        changev("ang", 720.0 / NB_RAYONS),
    ]
    Sp.proc("feux", [], [
        setv("i", 1),
        repeter(NB_FUSEES, [
            setv("a", sub(chr_, item("ft", i))),
            si(gt(V("a"), 0), [
                setv("x", item("fx", i)), setv("h", item("fh", i)),
                si(lt(V("a"), 0.8), [
                    # montée : trait clair qui ralentit (sortie quadratique)
                    setv("p", sub(1, div(V("a"), 0.8))),
                    setv("y", add(-180, mul(add(item("fy", i), 180), sub(1, mul(V("p"), V("p")))))),
                    couleur_hsbt(V("h"), 35, 100, 10), taille_stylo(3),
                    ligne(V("x"), sub(V("y"), 14), V("x"), V("y")),
                    changev("spc_particules", 1),
                ], [
                    si(lt(V("a"), 2.3), [
                        # explosion : rayons qui s'éloignent (sortie quadratique), retombent (t) et s'estompent
                        setv("p", div(sub(V("a"), 0.8), 1.5)),
                        setv("r", mul(52, sub(1, mul(sub(1, V("p")), sub(1, V("p")))))),
                        setv("t", mul(34, mul(V("p"), V("p")))),
                        setv("y", item("fy", i)),
                        si(et(lt(V("a"), 0.9), gt(chr_, V("dernierBoum"))), [
                            setv("dernierBoum", add(chr_, 0.4)),
                            setv("son_pan", div(V("x"), 2.4)), setv("son_volume", 30), diffuser("son explosion"),
                        ]),
                        taille_stylo(add(1, mul(2.5, sub(1, V("p"))))),
                        setv("ang", item("fo", i)),
                        couleur_hsbt(V("h"), 90, 100, mul(V("p"), 100)),
                        repeter(NB_RAYONS // 2, rayons),
                        setv("ang", add(item("fo", i), 360.0 / NB_RAYONS)),
                        couleur_hsbt(add(V("h"), 22), 80, 100, mul(V("p"), 100)),
                        repeter(NB_RAYONS // 2, rayons),
                        changev("spc_particules", NB_RAYONS),
                    ], [
                        appel("fusee nouvelle", i, div(hasard(0, 9), 10)),
                    ]),
                ]),
            ]),
            changev("i", 1),
        ]),
    ])
    Sp.proc("confettis", [], [
        setv("t", sub(chr_, V("tFin0"))), setv("i", 1), taille_stylo(3),
        repeter(NB_CONFETTIS, [
            setv("y", sub(185, mod(add(mul(item("cv", i), V("t")), mul(item("cp", i), 1.05)), 370))),
            setv("x", add(item("cx", i), mul(10, sin(add(mul(V("t"), 90), item("cp", i)))))),
            setv("ang", add(mul(V("t"), 240), mul(item("cp", i), 3))),
            couleur_hsbt(item("ch", i), 85, 100, 0),
            ligne(V("x"), V("y"), add(V("x"), mul(5, sin(V("ang")))), add(V("y"), mul(3, cos(V("ang"))))),
            changev("i", 1),
        ]),
        changev("spc_particules", NB_CONFETTIS),
    ])
    Sp.proc("pluie", [], [
        setv("t", sub(chr_, V("tFin0"))), setv("i", 1), taille_stylo(2), couleur_hsbt(0, 0, 70, 45),
        repeter(NB_PLUIE, [
            setv("y", sub(185, mod(add(mul(mul(item("cv", i), 0.45), V("t")), mul(item("cp", i), 1.05)), 370))),
            setv("x", add(item("cx", i), mul(4, sin(add(mul(V("t"), 40), item("cp", i)))))),
            ligne(V("x"), add(V("y"), 4), V("x"), V("y")),
            changev("i", 1),
        ]),
        changev("spc_particules", NB_PLUIE),
    ])

    # ------------------------------------------------------------------
    #  Bannière de série (centre, texte qui grossit puis se rétracte)
    # ------------------------------------------------------------------
    Sp.proc("banniere suivante", [], [
        # entrées en attente depuis plus de DELAI_FILE s (écran non compatible) : jetées
        repeter_jusqua(ou(lt(long_liste("file"), 1), gt(item("fileT", 1), sub(chr_, DELAI_FILE))), [
            supprimer("file", 1), supprimer("fileC", 1), supprimer("fileT", 1),
        ]),
        si(et(eq(V("banTexte"), ""), gt(long_liste("file"), 0)), [
            setv("banTexte", item("file", 1)), setv("banCouleur", item("fileC", 1)),
            supprimer("file", 1), supprimer("fileC", 1), supprimer("fileT", 1),
            setv("banDebut", chr_), setv("spc_banniere", V("banTexte")),
            setv("son_pan", 0), setv("son_volume", 100), diffuser("son serie"),
        ]),
    ])
    Sp.proc("banniere", [], [
        appel("banniere suivante"),
        si(non(eq(V("banTexte"), "")), [
            setv("a", sub(chr_, V("banDebut"))),
            si(lt(V("a"), 0.25), [setv("p", add(0.4, mul(3.2, V("a"))))], [
                si(lt(V("a"), 0.4), [setv("p", sub(1.2, div(sub(V("a"), 0.25), 0.75)))], [
                    si(lt(V("a"), 1.7), [setv("p", 1)], [
                        si(lt(V("a"), 2), [setv("p", div(sub(2, V("a")), 0.3))], [setv("p", 0), setv("banTexte", ""), setv("spc_banniere", "")]),
                    ]),
                ]),
            ]),
            setv("t", mul(30, V("p"))),
            si(gt(V("t"), 6), [
                appel("largeur texte", V("banTexte"), V("t")),
                setv("w", V("txt_largeur")),
                couleur_hsbt(0, 0, 6, 35), taille_stylo(mul(V("t"), 1.25)),
                ligne(sub(mul(V("w"), -0.5), mul(V("t"), 0.4)), add(Y_BANNIERE, mul(V("t"), 0.33)), add(mul(V("w"), 0.5), mul(V("t"), 0.4)), add(Y_BANNIERE, mul(V("t"), 0.33))),
                setv("txt_ombre", 1),
                appel("txt_dessiner", 0, Y_BANNIERE, V("t"), V("banCouleur"), 1),
            ]),
        ]),
    ])

    # ------------------------------------------------------------------
    #  Annonces (bandeau qui glisse) + étoiles du niveau
    # ------------------------------------------------------------------
    Sp.proc("annonce suivante", [], [
        repeter_jusqua(ou(lt(long_liste("fileA"), 1), gt(item("fileAT", 1), sub(chr_, DELAI_FILE))), [
            supprimer("fileA", 1), supprimer("fileAC", 1), supprimer("fileAE", 1), supprimer("fileAT", 1),
        ]),
        si(et(eq(V("annTexte"), ""), gt(long_liste("fileA"), 0)), [
            setv("annTexte", item("fileA", 1)), setv("annCouleur", item("fileAC", 1)), setv("annEtoiles", item("fileAE", 1)),
            supprimer("fileA", 1), supprimer("fileAC", 1), supprimer("fileAE", 1), supprimer("fileAT", 1),
            setv("annDebut", chr_),
            si(eq(V("annEtoiles"), 1), [setv("etoDebut", chr_)]),
        ]),
    ])
    Sp.proc("annonce", [], [
        appel("annonce suivante"),
        si(non(eq(V("annTexte"), "")), [
            setv("a", sub(chr_, V("annDebut"))),
            appel("largeur texte", V("annTexte"), 18),
            setv("w", V("txt_largeur")),
            # glissement : depuis le bord gauche (texte entier visible) vers le centre, puis vers le bord droit
            si(lt(V("a"), 0.35), [
                setv("p", sub(1, div(V("a"), 0.35))), setv("p", mul(V("p"), V("p"))),
                setv("x", mul(sub(add(-240, mul(V("w"), 0.5)), -6), V("p"))),
            ], [
                si(lt(V("a"), 2.25), [setv("p", 0), setv("x", 0)], [
                    si(lt(V("a"), 2.6), [
                        setv("p", div(sub(V("a"), 2.25), 0.35)), setv("p", mul(V("p"), V("p"))),
                        setv("x", mul(sub(sub(240, mul(V("w"), 0.5)), 6), V("p"))),
                    ], [setv("p", 1), setv("annTexte", "")]),
                ]),
            ]),
            si(non(eq(V("annTexte"), "")), [
                couleur_hsbt(0, 0, 8, add(30, mul(60, V("p")))), taille_stylo(32),
                ligne(-240, Y_ANNONCE, 240, Y_ANNONCE),
                couleur_hsbt(0, 0, 100, add(45, mul(55, V("p")))), taille_stylo(2),
                ligne(-240, Y_ANNONCE + 16, 240, Y_ANNONCE + 16), ligne(-240, Y_ANNONCE - 16, 240, Y_ANNONCE - 16),
                setv("txt_ombre", 1),
                appel("txt_dessiner", V("x"), Y_ANNONCE - 6, 18, V("annCouleur"), 1),
                changev("spc_particules", 3),
            ]),
        ]),
    ])
    Sp.proc("etoiles", [], [
        setv("a", sub(chr_, V("etoDebut"))),
        si(et(gt(V("a"), 0), lt(V("a"), 2.5)), [
            setv("p", div(V("a"), 2.5)), setv("i", 1), costume("spc_etoile"),
            repeter(NB_ETOILES, [
                setv("y", sub(add(118, mul(item("cp", i), 0.15)), add(mul(150, mul(V("p"), V("p"))), mul(60, V("p"))))),
                setv("x", add(mul(item("cx", i), 0.9), mul(12, sin(add(mul(V("a"), 150), item("cp", i)))))),
                taille(add(45, mul(25, sin(add(mul(V("a"), 400), item("cp", i)))))),
                effet("GHOST", mul(V("p"), 100)),
                aller(V("x"), V("y")), tampon(),
                changev("i", 1),
            ]),
            effacer_effets(),
            changev("spc_particules", NB_ETOILES),
        ]),
    ])

    # ------------------------------------------------------------------
    #  Files d'attente (appelées par les événements)
    # ------------------------------------------------------------------
    Sp.proc("ajouter banniere", [("texte", "s"), ("couleur", "s")], [
        ajouter_liste("file", A("texte")), ajouter_liste("fileC", A("couleur")), ajouter_liste("fileT", chr_),
        si(gt(long_liste("file"), 4), [supprimer("file", 1), supprimer("fileC", 1), supprimer("fileT", 1)]),
    ])
    Sp.proc("ajouter annonce", [("texte", "s"), ("couleur", "s"), ("etoiles", "n")], [
        ajouter_liste("fileA", A("texte")), ajouter_liste("fileAC", A("couleur")), ajouter_liste("fileAE", A("etoiles")), ajouter_liste("fileAT", chr_),
        si(gt(long_liste("fileA"), 4), [supprimer("fileA", 1), supprimer("fileAC", 1), supprimer("fileAE", 1), supprimer("fileAT", 1)]),
    ])
    Sp.proc("vider files", [], [
        vider("file"), vider("fileC"), vider("fileT"), vider("fileA"), vider("fileAC"), vider("fileAE"), vider("fileAT"),
        setv("banTexte", ""), setv("annTexte", ""), setv("spc_banniere", ""), setv("etoDebut", -10),
    ])

    # ------------------------------------------------------------------
    #  Clones du salon
    # ------------------------------------------------------------------
    def cloner(role, nb):
        return [setv("role", role), setv("k", 0), repeter(nb, [cloner_moi(), changev("k", 1)])]
    Sp.proc("creer clones salon", [], [
        setv("estClone", 1),
        cloner("bordure", NB_BORDURE), cloner("eclat", NB_ECLATS), cloner("haloJouer", 1), cloner("haloPerso", 1),
        setv("estClone", 0), setv("role", ""), setv("clonesFaits", 1),
    ])
    pulse = add(0.5, mul(0.5, sin(mul(chr_, 180))))                 # 0..1, période 2 s
    accueil = eq(V("onglet"), "accueil")
    Sp.script(quand_clone(), [
        effacer_effets(), cacher(),
        toujours([
            si(eq(V("ecran"), "salon"), [
                si(eq(V("role"), "bordure"), [
                    costume("spc_etoile"),
                    setv("s", mod(add(mul(chr_, 45), mul(V("k"), PERIM / float(NB_BORDURE))), PERIM)),
                    si(lt(V("s"), 2 * BX), [setv("x", add(-BX, V("s"))), setv("y", BY)], [
                        si(lt(V("s"), 2 * BX + 2 * BY), [setv("x", BX), setv("y", sub(BY, sub(V("s"), 2 * BX)))], [
                            si(lt(V("s"), 4 * BX + 2 * BY), [setv("x", sub(BX, sub(V("s"), 2 * BX + 2 * BY))), setv("y", -BY)],
                               [setv("x", -BX), setv("y", add(-BY, sub(V("s"), 4 * BX + 2 * BY)))]),
                        ]),
                    ]),
                    aller(V("x"), V("y")),
                    setv("p", sin(add(mul(chr_, 250), mul(V("k"), 50)))),
                    taille(add(55, mul(15, V("p")))), effet("GHOST", add(45, mul(25, V("p")))), montrer(),
                ]),
                si(eq(V("role"), "eclat"), [
                    si(accueil, [
                        costume("spc_etoile"),
                        setv("p", div(mod(add(mul(chr_, 22), mul(V("k"), 26)), 156), 156)),       # 0 en bas → 1 en haut
                        setv("y", add(-24, mul(V("p"), 156))),
                        setv("x", add(PERSO_X, mul(32, sin(add(mul(chr_, 60), mul(V("k"), 61)))))),
                        aller(V("x"), V("y")),
                        taille(add(32, mul(14, sin(add(mul(chr_, 300), mul(V("k"), 70)))))),
                        effet("GHOST", add(25, mul(60, V("p")))), montrer(),
                    ], [cacher()]),
                ]),
                si(eq(V("role"), "haloJouer"), [
                    costume("spc_halo_jouer"), aller(JOUER_X, JOUER_Y),
                    taille(add(97, mul(8, pulse))), effet("GHOST", sub(70, mul(35, pulse))), montrer(),
                ]),
                si(eq(V("role"), "haloPerso"), [
                    si(accueil, [
                        costume("spc_halo_perso"), aller(PERSO_X, PERSO_Y),
                        taille(add(94, mul(10, pulse))), effet("GHOST", sub(80, mul(30, pulse))), montrer(),
                    ], [cacher()]),
                ]),
            ], [cacher()]),
        ]),
    ])

    # ------------------------------------------------------------------
    #  Boucle principale (original)
    # ------------------------------------------------------------------
    Sp.proc("image", [], [
        si(non(eq(V("ecran"), V("ecranAvant"))), [
            setv("ecranAvant", V("ecran")),
            si(eq(V("ecran"), "fin"), [appel("entrer fin")]),
        ]),
        si(et(eq(V("ecran"), "salon"), eq(V("clonesFaits"), 0)), [appel("creer clones salon")]),
        # « il reste N joueurs » (en partie : écran de jeu, manche en cours)
        si(et(lt(V("vivants"), V("vivantsAvant")), et3(en_jeu, eq(V("finManche"), 0), ge(V("phase"), 2))), [
            si(eq(V("vivants"), 3), [appel("ajouter annonce", tr("IL RESTE 3 JOUEURS", "3 PLAYERS LEFT"), "orange", 0)]),
            si(eq(V("vivants"), 2), [appel("ajouter annonce", tr("IL RESTE 2 JOUEURS", "2 PLAYERS LEFT"), "rouge", 0)]),
        ]),
        setv("vivantsAvant", V("vivants")),
        # dessin (une fois par image)
        si(non(eq(chr_, V("dernierDessin"))), [
            setv("dernierDessin", chr_), setv("spc_particules", 0),
            si(eq(V("ecran"), "fin"), [
                si(eq(V("victoire"), 1), [appel("feux"), appel("confettis")], [appel("pluie")]),
            ], [
                si(et(en_jeu, eq(V("superposition"), "")), [
                    setv("txt_ombre", 1),
                    appel("annonce"), appel("etoiles"), appel("banniere"),
                ]),
            ]),
        ]),
    ])

    Sp.script(quand_drapeau(), [
        cacher(), aller(0, 0), effacer_effets(), setv("estClone", 0), setv("role", ""), setv("clonesFaits", 0),
        setv("dernierDessin", -1), setv("ecranAvant", ""), setv("teteSerie", 0), setv("vivantsAvant", 0),
        setv("tFin0", 0), setv("dernierBoum", 0), setv("banCouleur", "or"), setv("annCouleur", "blanc"),
        setv("spc_particules", 0), appel("vider files"), appel("init listes"),
        toujours([si(original, [appel("image")])]),
    ])
    # relance sans drapeau vert : les clones se suppriment, l'original les recréera au prochain passage au salon
    Sp.script(quand_message("demarrer"), [si(eq(V("estClone"), 1), [supprimer_clone()], [setv("clonesFaits", 0)])])

    # ------------------------------------------------------------------
    #  Événements (original seulement)
    # ------------------------------------------------------------------
    k = V("k")
    # (blocs « warp » : un gestionnaire d'événement qui boucle céderait la main à chaque tour)
    Sp.proc("elimination", [], [
        setv("elims", V("💀 Éliminations")),
        si(ge(V("serie"), 2), [
            si(eq(V("serie"), 2), [appel("ajouter banniere", tr("DOUBLE ÉLIMINATION !", "DOUBLE ELIMINATION!"), "or")]),
            si(eq(V("serie"), 3), [appel("ajouter banniere", tr("TRIPLE ÉLIMINATION !", "TRIPLE ELIMINATION!"), "or")]),
            si(eq(V("serie"), 4), [appel("ajouter banniere", tr("QUADRUPLE !", "QUADRUPLE!"), "orange")]),
            si(ge(V("serie"), 5), [appel("ajouter banniere", tr("MONSTRUEUX !", "MONSTROUS!"), "rouge")]),
        ]),
        si(eq(V("elims"), 5), [appel("ajouter banniere", tr("RAMPAGE", "RAMPAGE"), "orange")]),
        si(eq(V("elims"), 10), [appel("ajouter banniere", tr("LÉGENDE", "LEGEND"), "jaune")]),
        si(et(ge(V("elims"), 3), eq(V("teteSerie"), 0)), [
            setv("n", 0), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et3(non(eq(k, V("monSlot"))), eq(item("E_actif", k), 1), ge(item("E_elims", k), V("elims"))), [setv("n", 1)]),
                changev("k", 1),
            ]),
            si(eq(V("n"), 0), [setv("teteSerie", 1), appel("ajouter banniere", tr("TÊTE DE SÉRIE", "TOP FRAGGER"), "cyan")]),
        ]),
    ])
    Sp.script(quand_message("evt elimination"), [si(original, [appel("elimination")])])
    Sp.script(quand_message("evt phase"), [si(et(original, en_jeu), [
        si(et(ge(V("evt_valeur"), 3), lt(V("evt_valeur"), DERNIERE_PHASE)),
           [appel("ajouter annonce", tr("LA TEMPÊTE AVANCE", "THE STORM ADVANCES"), "violet", 0)]),
        si(eq(V("evt_valeur"), DERNIERE_PHASE), [appel("ajouter annonce", tr("DERNIÈRE ZONE", "FINAL ZONE"), "rose", 0)]),
    ])])
    Sp.script(quand_message("evt niveau"), [si(original, [
        appel("ajouter annonce", join(tr("NIVEAU ", "LEVEL "), V("niveau")), "jaune", 1),
    ])])
    Sp.script(quand_message("evt nouvelle manche"), [si(original, [setv("teteSerie", 0), appel("vider files")])])
    Sp.script(quand_message("evt fin manche"), [si(original, [appel("vider files")])])
    return Sp
