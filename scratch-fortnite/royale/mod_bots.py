# -*- coding: utf-8 -*-
"""
Sprite « Bots » : BOTS DE REMPLISSAGE façon Fortnite (module royale/mod_bots.py, calque 94, invisible).

Principe
--------
Un bot occupe un emplacement réseau libre (☁ Jk vide ou périmé, k ≠ monSlot) : BotsActifs[k] = 1 et
BotsPaquets[k] = un paquet complet au format contrat.CHAMPS (même codage que Reseau.encoder). Le bloc
« lire paquet » de Reseau substitue ce paquet local à la variable cloud : le bot est ensuite décodé, affiché,
compté, visé et entendu exactement comme un vrai joueur (listes E_*, Ennemi, HUD, Partie…). Les bots sont
LOCAUX : chaque joueur voit ses propres bots ; un vrai joueur qui prend l'emplacement (battement frais)
désactive le bot immédiatement (≤ 6 images : un emplacement est surveillé par image).

Arrivée (comme un salon qui se remplit) : les bots rejoignent un par un, échelonnés en temps réel
(1,5 s + 0,6 s par emplacement + hasard), pendant la pré-partie seulement — enPartie = 1, phase ≤ 1 et moi
sur l'île (etat 8) ou dans le bus (etat 6). Personne ne rejoint une manche déjà en combat, ce qui laisse
les scénarios « adversaires simulés » (emplacements vides en combat) inchangés. 0 bot si param_bots = 0,
si enPartie = 0 ou si connecte = 0. nbBots = nombre de bots actifs (≤ 6 − vrais joueurs par construction).

Comportement par bot et par image (machine à états sur `be`, coût léger ; paquet ré-encodé toutes les
3 images par bot, comme la cadence d'envoi de Reseau) :
- phase 0 : errance sur l'île, etat 8 (invulnérable, pas une cible) ; émotes et chat rapide de temps en temps.
- phase 1 : dans le bus (etat 6, altitude 99, position du bus), saut à une progression aléatoire → parachute
  (etat 7, altitude décroissante 8/s puis 4/s) vers une case libre de la zone, atterrissage → etat 1.
- combat (etat 1) : errance vers une cible aléatoire (case libre dans la zone, 0,05 case/image, évitement des
  murs : si la case devant est un mur, tourner ±90° et garder le cap quelques images) ; retour dans la zone
  si hors zone (la tempête inflige zoneDegats/s, sans bouclier) ; poursuite du joueur s'il est à portée
  (≤ portée + 1) ET en ligne de vue (test par pas de 0,5 case sur Carte, 4 fois par seconde), arrêt à
  2,5 cases ; tir toutes les 0,6–1,2 s × cadence : précision p % → seq = (seq + 1) mod 100, cible = monSlot,
  degats aléatoires ; un tir raté ne change pas seq. Faute de joueur visible, le bot tire sur le bot ennemi
  visible le plus proche (dégâts appliqués localement : le journal de Reseau raconte « nina a éliminé max_7 »,
  et la manche peut se terminer même après ma mort). Un coéquipier bot vient me réanimer (reanime = monSlot
  à moins de 1,5 case) quand je suis à terre.
- mes tirs : lecture des globales cible/seq/degats (mon dernier tir) : si cible = k et seq différent du dernier
  vu → bouclier puis PV ; PV ≤ 0 → etat 2 (tueur = monSlot, morts + 1) ou, en modes à terre (2-4), etat 3
  pendant 20 s puis mort. Le bot touché se retourne et poursuit son agresseur.
- mort : Rumble (mode 5) → réapparition en parachute (altitude 40) après 5 s ; sinon etat 2 figé jusqu'à
  « evt nouvelle manche » (tout l'état de manche est réinitialisé, les bots gardent leur identité).

Difficulté : variable globale privée `bots_difficulte` (1 facile, 2 normal, 3 difficile ; défaut 2) :
précision 35/55/75 %, portée 7/9/11 cases, cadence ×1,4/×1,05/×0,7, dégâts 6-12 / 8-17 / 10-22.

Identité : pseudo plausible distinct (liste bNoms, codé sur 16 chiffres avec Alphabet), niveau 1-40, skin 1-10,
pioche/planeur 1-9, victoires 0-15, bannière 1-10, arme 1-3 (LTM respecté), équipe = plafond(k / taille) en
modes équipe. Chaque bot a son propre code de salon = codeSalon (sinon Reseau l'ignore).
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S

V = Var
A = Arg
ORDRE = 45
CALQUE = 94
NB = C.NB_JOUEURS
CENTRE = C.TAILLE / 2 + 0.5

# pseudos plausibles (≤ 8 caractères de contrat.ALPHABET)
NOMS = ["bot_lama", "nina", "max_7", "kylian", "zoe_", "raptor", "lea-22", "tomtom", "sacha", "pixel", "ninja_x",
        "lucas", "emma", "noah77", "jade", "gabriel", "chloe", "arthur", "lina", "hugo_fps", "manon", "louis",
        "ines", "rayan", "camille", "nael", "mila", "ethan", "sofia", "tiago", "maya_", "adam", "yanis", "eva_"]
for _n in NOMS:
    assert 1 <= len(_n) <= 8 and all(c in C.ALPHABET for c in _n), _n

# listes locales indexées par emplacement (1..6)
LISTES_BOT = ["bx", "by", "bd", "be", "bpv", "bbou", "bcible", "bseq", "bdeg", "btueur", "bmorts", "barme", "bnom",
              "belims", "bniv", "bequipe", "bemote", "bemoteSeq", "bchat", "bchatSeq", "balt", "bfixe2", "bfixe3",
              "bknock", "breanime", "bcx", "bcy", "bdetour", "bProchainTir", "bProchainVue", "bVoit", "bDistJ",
              "bDernierSeq", "bTempsEtat", "bProchainZone", "bProchainSocial", "bSaut", "bArrivee", "bEnnemi",
              "bPatience", "bNomIdx"]


def construire(P):
    P.stage.var("bots_difficulte", 2)

    B = Cible(P, "Bots")
    B.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    B.visible = False
    B.layer = CALQUE
    for v in ["k", "j", "i", "n", "x", "y", "d", "e", "dx", "dy", "dist", "ang", "ok", "nx", "ny", "vu", "dt", "tPrec",
              "tAttente", "tour", "nb", "q", "prec", "portee", "cad", "dmin", "dmax", "poursuite", "a", "b", "t", "v",
              "meilleur", "meilleurD"]:
        B.var(v, 0)
    B.var("s", "")
    B.var("texte", "")
    B.var("pad", "")
    for nom in LISTES_BOT:
        B.liste(nom, [0] * NB)
    B.liste("bNoms", NOMS)
    B.liste("bNomPris", [])

    k = V("k")

    def L(nom):                       # item du bot courant (k)
        return item(nom, k)

    def R(nom, val):
        return remplacer(nom, k, val)

    def Ln(nom):                      # item du bot désigné par l'argument n
        return item(nom, A("n"))

    def Rn(nom, val):
        return remplacer(nom, A("n"), val)

    def pad(val, n):
        return C.rembourrer(val, n)

    def dist2(ax, ay, bx, by):
        return add(mul(sub(ax, bx), sub(ax, bx)), mul(sub(ay, by), sub(ay, by)))

    def mode_equipe():
        return ou3(eq(V("mode"), 2), eq(V("mode"), 3), eq(V("mode"), 4))

    def meme_equipe_que_moi(expr_equipe):
        return et(gt(V("monEquipe"), 0), eq(expr_equipe, V("monEquipe")))

    # -----------------------------------------------------------------------
    #  Accès aux emplacements cloud et au nom
    # -----------------------------------------------------------------------
    B.proc("lire cloud", [("n", "n")],
           [si(eq(A("n"), i), [setv("s", V("☁ J%d" % i))]) for i in range(1, NB + 1)])

    # ok = 1 si l'emplacement n est libre pour un bot (vide, incomplet ou battement périmé)
    B.proc("emplacement libre", [("n", "n")], [
        appel("lire cloud", A("n")),
        setv("ok", 1),
        si(ge(longueur(V("s")), C.LONGUEUR_PAQUET), [
            setv("t", mul(C.sous_chaine(V("s"), C.POS["battement"][0], C.POS["battement"][1]), 1)),
            si(le(absv(C.ecart(V("maintenant"), V("t"))), 15), [setv("ok", 0)]),
        ]),
    ])

    B.proc("coder nom", [("mot", "s")], [
        setv("texte", ""), setv("i", 1),
        repeter(8, [
            setv("pad", num_item("Alphabet", lettre(V("i"), A("mot")))),
            si(lt(V("pad"), 10), [setv("pad", join("0", V("pad")))]),
            setv("texte", join(V("texte"), V("pad"))),
            changev("i", 1),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Géométrie : angle, ligne de vue, case libre
    # -----------------------------------------------------------------------
    B.proc("angle vers", [("dx", "n"), ("dy", "n")], [
        si(lt(absv(A("dx")), 0.0001), [
            si(gt(A("dy"), 0), [setv("ang", 90)], [setv("ang", 270)]),
        ], [
            setv("ang", atan(div(A("dy"), A("dx")))),
            si(lt(A("dx"), 0), [changev("ang", 180)]),
        ]),
        setv("ang", mod(V("ang"), 360)),
    ])

    # vu = 1 si aucun mur entre (x1, y1) et (x2, y2) — pas de 0,5 case sur Carte
    B.proc("ligne de vue", [("x1", "n"), ("y1", "n"), ("x2", "n"), ("y2", "n")], [
        setv("vu", 1),
        setv("dx", sub(A("x2"), A("x1"))), setv("dy", sub(A("y2"), A("y1"))),
        setv("n", floor(div(sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy")))), 0.5))),
        si(gt(V("n"), 0), [
            setv("dx", div(V("dx"), V("n"))), setv("dy", div(V("dy"), V("n"))),
            setv("nx", A("x1")), setv("ny", A("y1")), setv("i", 1),
            repeter_jusqua(ou(eq(V("vu"), 0), gt(V("i"), V("n"))), [
                changev("nx", V("dx")), changev("ny", V("dy")), changev("i", 1),
                si(non(eq(C.cellule(V("nx"), V("ny")), 0)), [setv("vu", 0)]),
            ]),
        ]),
    ])

    # nx, ny = centre d'une case libre à moins de r de (cx, cy), dans la carte et dans la zone
    B.proc("case libre autour", [("cx", "n"), ("cy", "n"), ("r", "n")], [
        setv("ok", 0), setv("i", 0),
        repeter_jusqua(ou(eq(V("ok"), 1), gt(V("i"), 24)), [
            changev("i", 1),
            setv("nx", add(floor(add(A("cx"), hasard(mul(A("r"), -1), A("r")))), 0.5)),
            setv("ny", add(floor(add(A("cy"), hasard(mul(A("r"), -1), A("r")))), 0.5)),
            si(et4(gt(V("nx"), 1), lt(V("nx"), C.TAILLE - 1), gt(V("ny"), 1), lt(V("ny"), C.TAILLE - 1)), [
                si(et(eq(C.cellule(V("nx"), V("ny")), 0),
                      lt(dist2(V("nx"), V("ny"), V("zoneX"), V("zoneY")), mul(sub(V("zoneR"), 1), sub(V("zoneR"), 1)))),
                   [setv("ok", 1)]),
            ]),
        ]),
        si(eq(V("ok"), 0), [setv("nx", CENTRE), setv("ny", CENTRE)]),
    ])

    # -----------------------------------------------------------------------
    #  Cycle de vie : équipe, placement selon la phase, activation, désactivation
    # -----------------------------------------------------------------------
    B.proc("equipe bot", [], [
        si(mode_equipe(), [
            si(eq(V("mode"), 2), [R("bequipe", plafond(div(k, 2)))], [R("bequipe", plafond(div(k, 3)))]),
        ], [R("bequipe", 0)]),
    ])

    B.proc("placer bot", [], [
        R("bpv", 100), R("bbou", 0), R("bcible", 0), R("bdeg", 0), R("btueur", 0), R("bknock", 0), R("breanime", 0),
        R("balt", 0), R("bdetour", 0), R("bPatience", 0), R("bVoit", 0), R("bEnnemi", 0), R("bDistJ", 99),
        R("bProchainTir", add(chrono(), hasard(1.0, 3.0))), R("bProchainVue", chrono()), R("bProchainZone", add(chrono(), 1)),
        R("bTempsEtat", chrono()), R("bProchainSocial", add(chrono(), hasard(5, 20))),
        si(lt(V("phase"), 1), [
            appel("case libre autour", C.TAILLE / 2, C.TAILLE / 2, C.TAILLE / 2 - 1),
            R("bx", V("nx")), R("by", V("ny")), R("be", 8),
        ], [
            si(eq(V("phase"), 1), [
                R("bx", V("busX")), R("by", V("busY")), R("be", 6), R("balt", 99), R("bSaut", hasard(0.15, 0.85)),
            ], [
                appel("case libre autour", V("zoneX"), V("zoneY"), sub(V("zoneR"), 1)),
                R("bx", V("nx")), R("by", V("ny")), R("be", 1),
            ]),
        ]),
        R("bd", hasard(0, 359)), R("bcx", L("bx")), R("bcy", L("by")),
        appel("equipe bot"),
    ])

    B.proc("activer bot", [], [
        remplacer("BotsActifs", k, 1),
        # pseudo distinct des autres bots
        setv("ok", 0), setv("i", 0),
        repeter_jusqua(ou(eq(V("ok"), 1), gt(V("i"), 12)), [
            changev("i", 1), setv("n", hasard(1, len(NOMS))),
            si(non(contient("bNomPris", V("n"))), [setv("ok", 1)]),
        ]),
        ajouter_liste("bNomPris", V("n")), R("bNomIdx", V("n")),
        appel("coder nom", item("bNoms", V("n"))), R("bnom", V("texte")),
        # (un hasard passé à rembourrer serait tiré une fois par chiffre : on le fixe d'abord dans une variable)
        setv("a", hasard(1, 40)), R("bniv", pad(V("a"), 3)),
        setv("a", hasard(1, 10)), R("bfixe2", joins(pad(V("a"), 2), hasard(1, 9), hasard(1, 9))),
        setv("a", hasard(0, 15)), setv("b", hasard(1, 10)), R("bfixe3", join(pad(V("a"), 2), pad(V("b"), 2))),
        R("barme", hasard(1, 3)),
        si(eq(V("ltm"), 1), [R("barme", 2)]), si(eq(V("ltm"), 2), [R("barme", 3)]),
        R("bseq", 0), R("belims", 0), R("bmorts", 0), R("bemote", 0), R("bemoteSeq", 0), R("bchat", 0), R("bchatSeq", 0),
        R("bDernierSeq", V("seq")),
        appel("placer bot"),
        appel("encoder bot"),
    ])

    B.proc("desactiver bot", [], [
        remplacer("BotsActifs", k, 0), remplacer("BotsPaquets", k, 0), R("be", 0),
        setv("n", num_item("bNomPris", L("bNomIdx"))),
        si(gt(V("n"), 0), [supprimer("bNomPris", V("n"))]),
        R("bNomIdx", 0),
    ])

    B.proc("desactiver tous", [], [
        setv("k", 1),
        repeter(NB, [si(eq(item("BotsActifs", k), 1), [appel("desactiver bot")]), changev("k", 1)]),
        setv("nbBots", 0),
    ])

    # surveille l'emplacement k : un vrai joueur frais désactive le bot ; un emplacement libre reçoit un bot
    # pendant l'attente pré-partie (île ou bus), à son heure d'arrivée
    B.proc("surveiller emplacement", [], [
        si(eq(k, V("monSlot")), [
            si(eq(item("BotsActifs", k), 1), [appel("desactiver bot")]),
        ], [
            appel("emplacement libre", k),
            si(eq(item("BotsActifs", k), 1), [
                si(eq(V("ok"), 0), [appel("desactiver bot")]),
            ], [
                si(et4(eq(V("ok"), 1), le(V("phase"), 1), ou(eq(V("etat"), 8), eq(V("etat"), 6)),
                       ge(V("tAttente"), L("bArrivee"))), [appel("activer bot")]),
            ]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Encodage du paquet (format contrat.CHAMPS, même codage que Reseau.encoder)
    # -----------------------------------------------------------------------
    champs = {
        "x": pad(mul(L("bx"), 100), 4), "y": pad(mul(L("by"), 100), 4), "dir": pad(mod(rnd(L("bd")), 360), 3),
        "pv": pad(L("bpv"), 3), "bouclier": pad(L("bbou"), 3), "battement": pad(V("maintenant"), 5),
        "cible": L("bcible"), "seq": pad(L("bseq"), 2), "degats": pad(L("bdeg"), 2), "tueur": L("btueur"),
        "morts": L("bmorts"), "arme": L("barme"), "etat": L("be"), "nom": L("bnom"),
        "elims": pad(mod(L("belims"), 100), 2), "niveau": L("bniv"), "equipe": L("bequipe"),
        "emote": L("bemote"), "emoteSeq": L("bemoteSeq"), "chat": pad(L("bchat"), 2), "chatSeq": L("bchatSeq"),
        "salon": pad(V("codeSalon"), 4), "altitude": pad(L("balt"), 2), "reanime": L("breanime"),
        "skin": L("bfixe2"), "pioche": None, "planeur": None,              # bfixe2 = skin(2) pioche(1) planeur(1)
        "modeChoisi": V("mode"), "victoires": L("bfixe3"), "banniere": None,   # bfixe3 = victoires(2) banniere(2)
        "knockPar": L("bknock"),
    }
    morceaux = ["1"]
    for nom, longueur_champ in C.CHAMPS:
        if nom in champs:
            if champs[nom] is not None:
                morceaux.append(champs[nom])
        elif isinstance(morceaux[-1], str):
            morceaux[-1] += "0" * longueur_champ      # champ inconnu ou sans objet : zéros
        else:
            morceaux.append("0" * longueur_champ)
    B.proc("encoder bot", [], [remplacer("BotsPaquets", k, joins(*morceaux))])

    # -----------------------------------------------------------------------
    #  Dégâts, à terre, mort, tir
    # -----------------------------------------------------------------------
    def mourir(source):
        return [Rn("be", 2), Rn("bpv", 0), Rn("btueur", source), Rn("bmorts", mod(add(Ln("bmorts"), 1), 10)),
                Rn("bTempsEtat", chrono()), Rn("balt", 0), Rn("breanime", 0),
                si(et(gt(source, 0), non(eq(source, V("monSlot")))),
                   [remplacer("belims", source, add(item("belims", source), 1))])]

    # dégâts q sur le bot n (source : emplacement du tireur, 0 = tempête qui ignore le bouclier)
    B.proc("degats bot", [("n", "n"), ("q", "n"), ("source", "n")], [
        setv("b", A("q")),
        si(gt(A("source"), 0), [
            setv("a", minimum(Ln("bbou"), V("b"))), Rn("bbou", sub(Ln("bbou"), V("a"))), changev("b", mul(V("a"), -1)),
            # le bot touché se retourne vers son agresseur et le poursuit
            si(eq(A("source"), V("monSlot")), [Rn("bcx", V("px")), Rn("bcy", V("py"))],
               [Rn("bcx", item("bx", A("source"))), Rn("bcy", item("by", A("source")))]),
            Rn("bPatience", add(chrono(), 6)), Rn("bdetour", 0),
        ]),
        Rn("bpv", sub(Ln("bpv"), V("b"))),
        si(le(Ln("bpv"), 0), [
            Rn("bpv", 0),
            si(eq(Ln("be"), 3), mourir(A("source")), [
                si(et(mode_equipe(), gt(A("source"), 0)), [
                    Rn("be", 3), Rn("bknock", A("source")), Rn("bpv", 40), Rn("bTempsEtat", chrono()), Rn("breanime", 0),
                ], mourir(A("source"))),
            ]),
        ]),
    ])

    # tir du bot k sur la cible c (monSlot ou un autre bot) ; précision prec %, un tir raté ne change pas seq
    B.proc("tirer bot", [("c", "n")], [
        R("bProchainTir", add(chrono(), mul(hasard(0.6, 1.2), V("cad")))),
        si(le(hasard(1, 100), V("prec")), [
            R("bseq", mod(add(L("bseq"), 1), 100)), R("bcible", A("c")), R("bdeg", hasard(V("dmin"), V("dmax"))),
            si(non(eq(A("c"), V("monSlot"))), [appel("degats bot", A("c"), L("bdeg"), k)]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Perception (4 Hz) : joueur visible ? bot ennemi visible ? coéquipier à réanimer ?
    # -----------------------------------------------------------------------
    B.proc("percevoir", [], [
        R("bProchainVue", add(chrono(), 0.25)), R("bVoit", 0), R("bEnnemi", 0), R("breanime", 0),
        setv("x", L("bx")), setv("y", L("by")),
        si(meme_equipe_que_moi(L("bequipe")), [
            # coéquipier : venir me réanimer si je suis à terre
            si(eq(V("etat"), 3), [
                R("bcx", V("px")), R("bcy", V("py")), R("bPatience", add(chrono(), 5)),
                si(lt(dist2(V("x"), V("y"), V("px"), V("py")), 2.25), [R("breanime", V("monSlot"))]),
            ]),
        ], [
            si(et3(ou(eq(V("etat"), 1), eq(V("etat"), 3)), eq(V("invulnerable"), 0), gt(V("monSlot"), 0)), [
                setv("dist", sqrt(dist2(V("x"), V("y"), V("px"), V("py")))),
                si(lt(V("dist"), V("poursuite")), [
                    appel("ligne de vue", V("x"), V("y"), V("px"), V("py")),
                    si(eq(V("vu"), 1), [R("bVoit", 1), R("bDistJ", V("dist"))]),
                ]),
            ]),
        ]),
        # bot ennemi le plus proche à portée et en vue (seulement si le joueur n'est pas visible)
        si(eq(L("bVoit"), 0), [
            setv("meilleur", 0), setv("meilleurD", mul(V("portee"), V("portee"))), setv("j", 1),
            repeter(NB, [
                si(et4(non(eq(V("j"), k)), eq(item("BotsActifs", V("j")), 1),
                       ou(eq(item("be", V("j")), 1), eq(item("be", V("j")), 3)),
                       non(et(gt(L("bequipe"), 0), eq(L("bequipe"), item("bequipe", V("j")))))), [
                    setv("dist", dist2(V("x"), V("y"), item("bx", V("j")), item("by", V("j")))),
                    si(lt(V("dist"), V("meilleurD")), [setv("meilleur", V("j")), setv("meilleurD", V("dist"))]),
                ]),
                changev("j", 1),
            ]),
            si(gt(V("meilleur"), 0), [
                appel("ligne de vue", V("x"), V("y"), item("bx", V("meilleur")), item("by", V("meilleur"))),
                si(eq(V("vu"), 1), [R("bEnnemi", V("meilleur"))]),
            ]),
        ]),
    ])

    # -----------------------------------------------------------------------
    #  Déplacement au sol (île et combat) : errance, poursuite, évitement des murs
    # -----------------------------------------------------------------------
    B.proc("deplacer bot", [], [
        setv("x", L("bx")), setv("y", L("by")), setv("d", L("bd")), setv("v", 0.05),
        # cible atteinte, patience épuisée ou cible hors zone → nouvelle cible dans la zone
        si(ou3(lt(add(absv(sub(L("bcx"), V("x"))), absv(sub(L("bcy"), V("y")))), 0.4), gt(chrono(), L("bPatience")),
               gt(dist2(L("bcx"), L("bcy"), V("zoneX"), V("zoneY")), mul(V("zoneR"), V("zoneR")))), [
            appel("case libre autour", V("x"), V("y"), 8),
            R("bcx", V("nx")), R("bcy", V("ny")), R("bPatience", add(chrono(), hasard(8, 15))),
        ]),
        setv("dx", sub(L("bcx"), V("x"))), setv("dy", sub(L("bcy"), V("y"))),
        # poursuite du joueur visible (arrêt à 2,5 cases, toujours face à lui)
        si(et(eq(L("bVoit"), 1), eq(L("be"), 1)), [
            setv("dx", sub(V("px"), V("x"))), setv("dy", sub(V("py"), V("y"))), setv("v", 0.06),
            si(lt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))), 6.25), [setv("v", 0)]),
        ]),
        si(gt(L("bdetour"), 0), [R("bdetour", sub(L("bdetour"), 1))], [appel("angle vers", V("dx"), V("dy")), setv("d", V("ang"))]),
        si(gt(V("v"), 0), [
            si(non(eq(C.cellule(add(V("x"), mul(cos(V("d")), 0.5)), add(V("y"), mul(sin(V("d")), 0.5))), 0)), [
                # mur devant : tourner et garder le cap quelques images
                si(lt(hasard(0, 1), 0.5), [changev("d", 90)], [changev("d", -90)]),
                R("bdetour", hasard(8, 20)),
            ], [
                setv("nx", add(V("x"), mul(cos(V("d")), V("v")))), setv("ny", add(V("y"), mul(sin(V("d")), V("v")))),
                si(eq(C.cellule(V("nx"), V("ny")), 0), [setv("x", V("nx")), setv("y", V("ny"))], [changev("d", 180), R("bdetour", 6)]),
            ]),
        ]),
        R("bx", V("x")), R("by", V("y")), R("bd", mod(V("d"), 360)),
    ])

    # -----------------------------------------------------------------------
    #  Une image d'un bot (k)
    # -----------------------------------------------------------------------
    B.proc("bot", [], [
        # ---- mon dernier tir (globales cible / seq / degats) ----
        si(et(eq(V("cible"), k), non(eq(V("seq"), L("bDernierSeq")))), [
            R("bDernierSeq", V("seq")),
            si(et3(ou(eq(L("be"), 1), eq(L("be"), 3)), non(meme_equipe_que_moi(L("bequipe"))), gt(V("monSlot"), 0)),
               [appel("degats bot", k, V("degats"), V("monSlot"))]),
        ]),
        # ---- transitions de phase ----
        si(lt(V("phase"), 1), [si(non(eq(L("be"), 8)), [appel("placer bot")])]),
        si(eq(V("phase"), 1), [si(eq(L("be"), 8), [appel("placer bot")])]),
        si(ge(V("phase"), 2), [
            si(eq(L("be"), 8), [appel("placer bot")]),
            si(eq(L("be"), 6), [                       # fin du bus : saut automatique
                appel("case libre autour", V("busX"), V("busY"), 10), R("bcx", V("nx")), R("bcy", V("ny")), R("be", 7),
            ]),
        ]),
        setv("e", L("be")),
        # ---- bus ----
        si(eq(V("e"), 6), [
            R("bx", V("busX")), R("by", V("busY")), R("balt", 99),
            si(ge(V("busProgression"), L("bSaut")), [
                appel("case libre autour", V("busX"), V("busY"), 10), R("bcx", V("nx")), R("bcy", V("ny")), R("be", 7),
            ]),
        ]),
        # ---- parachute : descente réelle, dérive vers la case visée, atterrissage ----
        si(eq(V("e"), 7), [
            si(gt(L("balt"), 30), [R("balt", sub(L("balt"), mul(V("dt"), 8)))], [R("balt", sub(L("balt"), mul(V("dt"), 4)))]),
            setv("dx", sub(L("bcx"), L("bx"))), setv("dy", sub(L("bcy"), L("by"))),
            setv("dist", sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
            si(gt(V("dist"), 0.12), [
                R("bx", add(L("bx"), mul(div(V("dx"), V("dist")), 0.12))), R("by", add(L("by"), mul(div(V("dy"), V("dist")), 0.12))),
                appel("angle vers", V("dx"), V("dy")), R("bd", V("ang")),
            ]),
            si(le(L("balt"), 0), [
                R("balt", 0), R("bx", L("bcx")), R("by", L("bcy")), R("be", 1), R("bTempsEtat", chrono()),
                R("bPatience", 0), R("bProchainTir", add(chrono(), hasard(0.5, 1.5))),
            ]),
        ]),
        # ---- île et combat : déplacement ----
        si(ou(eq(V("e"), 8), eq(V("e"), 1)), [appel("deplacer bot")]),
        # ---- combat ----
        si(eq(V("e"), 1), [
            si(gt(chrono(), L("bProchainVue")), [appel("percevoir")]),
            si(gt(chrono(), L("bProchainTir")), [
                si(et(eq(L("bVoit"), 1), lt(L("bDistJ"), V("portee"))), [appel("tirer bot", V("monSlot"))], [
                    si(gt(L("bEnnemi"), 0), [appel("tirer bot", L("bEnnemi"))]),
                ]),
            ]),
        ]),
        # ---- tempête (vivant ou à terre) : zoneDegats par seconde hors zone ----
        si(ou(eq(V("e"), 1), eq(V("e"), 3)), [
            si(gt(chrono(), L("bProchainZone")), [
                R("bProchainZone", add(chrono(), 1)),
                si(et(gt(V("zoneDegats"), 0), gt(dist2(L("bx"), L("by"), V("zoneX"), V("zoneY")), mul(V("zoneR"), V("zoneR")))),
                   [appel("degats bot", k, V("zoneDegats"), 0)]),
            ]),
        ]),
        # ---- à terre : 20 s puis mort ----
        si(eq(V("e"), 3), [
            si(gt(sub(chrono(), L("bTempsEtat")), 20), [appel("degats bot", k, 999, L("bknock"))]),
        ]),
        # ---- mort : réapparition en Rumble après 5 s (parachute depuis l'altitude 40) ----
        si(eq(V("e"), 2), [
            si(et3(eq(V("mode"), 5), lt(V("phase"), 8), gt(sub(chrono(), L("bTempsEtat")), 5)), [
                appel("case libre autour", V("zoneX"), V("zoneY"), sub(V("zoneR"), 1)),
                R("bcx", V("nx")), R("bcy", V("ny")), R("bx", V("nx")), R("by", V("ny")),
                R("bpv", 100), R("bbou", 0), R("be", 7), R("balt", 40), R("btueur", 0), R("bknock", 0),
            ]),
        ]),
        # ---- vie sociale : chat rapide, émote (île), petit bouclier trouvé (combat) ----
        si(et(ou(eq(V("e"), 8), eq(V("e"), 1)), gt(chrono(), L("bProchainSocial"))), [
            R("bProchainSocial", add(chrono(), hasard(20, 60))),
            setv("a", hasard(1, 10)),
            si(le(V("a"), 3), [R("bchat", hasard(1, len(C.CHAT_RAPIDE))), R("bchatSeq", mod(add(L("bchatSeq"), 1), 10))]),
            si(et(eq(V("a"), 4), eq(V("e"), 8)), [R("bemote", hasard(1, len(C.EMOTES))), R("bemoteSeq", mod(add(L("bemoteSeq"), 1), 10))]),
            si(et3(ge(V("a"), 8), eq(V("e"), 1), lt(L("bbou"), 50)), [R("bbou", add(L("bbou"), 25))]),
        ]),
        # ---- paquet : une fois toutes les 3 images par bot ----
        si(eq(mod(add(k, V("tour")), 3), 0), [appel("encoder bot")]),
    ])

    # -----------------------------------------------------------------------
    #  Réglages de difficulté (recalculés chaque image : bots_difficulte peut changer en jeu)
    # -----------------------------------------------------------------------
    B.proc("regler difficulte", [], [
        setv("q", rnd(V("bots_difficulte"))),
        si(ou(lt(V("q"), 1), gt(V("q"), 3)), [setv("q", 2), setv("bots_difficulte", 2)]),
        setv("prec", add(15, mul(20, V("q")))),            # 35 / 55 / 75 %
        setv("portee", add(5, mul(2, V("q")))),            # 7 / 9 / 11 cases
        setv("poursuite", add(V("portee"), 1)),
        setv("cad", sub(1.75, mul(0.35, V("q")))),         # × 1,4 / 1,05 / 0,7
        setv("dmin", add(4, mul(2, V("q")))),              # 6 / 8 / 10
        setv("dmax", add(7, mul(5, V("q")))),              # 12 / 17 / 22
    ])

    B.proc("initialiser", [], [
        setv("k", 1),
        repeter(NB, [
            remplacer("BotsActifs", k, 0), remplacer("BotsPaquets", k, 0),
            R("be", 0), R("bNomIdx", 0), R("bnom", "0" * 16),
            # heure d'arrivée (s d'attente pré-partie) : échelonnée par emplacement
            R("bArrivee", add(1.5, add(mul(0.6, sub(k, 1)), hasard(0, 0.5)))),
            changev("k", 1),
        ]),
        vider("bNomPris"), setv("nbBots", 0), setv("tAttente", 0), setv("tour", 0), setv("tPrec", chrono()),
    ])

    # -----------------------------------------------------------------------
    #  Scripts
    # -----------------------------------------------------------------------
    # une image complète (bloc « sans rafraîchissement » : un `repeter` au niveau du script céderait la main à chaque
    # itération, ce qui étalerait le passage sur les 6 emplacements sur plusieurs images et partagerait `k` avec le
    # gestionnaire de « evt nouvelle manche »)
    B.proc("image", [], [
        appel("regler difficulte"),
        # temps d'attente pré-partie (île ou bus) : les bots arrivent un par un
        si(et(le(V("phase"), 1), ou(eq(V("etat"), 8), eq(V("etat"), 6))), [changev("tAttente", V("dt"))]),
        setv("tour", add(mod(V("tour"), NB), 1)),
        setv("k", V("tour")), appel("surveiller emplacement"),
        setv("nb", 0), setv("k", 1),
        repeter(NB, [
            si(eq(item("BotsActifs", k), 1), [changev("nb", 1), appel("bot")]),
            changev("k", 1),
        ]),
        setv("nbBots", V("nb")),
    ])

    # nouvelle manche : les bots gardent leur identité, tout l'état de manche est remis à zéro
    B.proc("nouvelle manche", [], [
        setv("tAttente", 0), setv("k", 1),
        repeter(NB, [
            R("bArrivee", add(1.5, add(mul(0.6, sub(k, 1)), hasard(0, 0.5)))),
            si(eq(item("BotsActifs", k), 1), [
                R("belims", 0), R("bmorts", 0), R("bseq", 0), R("bchat", 0), R("bemote", 0),
                appel("placer bot"), appel("encoder bot"),
            ]),
            changev("k", 1),
        ]),
    ])

    B.script(quand_drapeau(), [
        cacher(), appel("initialiser"),
        toujours([
            setv("dt", sub(chrono(), V("tPrec"))), setv("tPrec", chrono()),
            si(gt(V("dt"), 0.1), [setv("dt", 0.1)]), si(lt(V("dt"), 0), [setv("dt", 0)]),
            si(et4(eq(V("connecte"), 1), eq(V("param_bots"), 1), eq(V("enPartie"), 1), gt(V("monSlot"), 0)),
               [appel("image")],
               [si(gt(V("nbBots"), 0), [appel("desactiver tous")]), setv("tAttente", 0)]),
        ]),
    ])
    B.script(quand_message("evt nouvelle manche"), [appel("nouvelle manche")])
    return B
