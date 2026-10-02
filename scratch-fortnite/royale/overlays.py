# -*- coding: utf-8 -*-
"""
Superpositions visibles en jeu : teinte de tempête, flash de dégâts, arme en vue subjective,
flash de bouche, viseur / lunette, bannières de message (sprite Message piloté par `message`).
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S

try:
    from . import svg_ui as UI
except Exception:
    UI = None

V = Var


def en_jeu():
    return ou(eq(V("ecran"), "jeu"), eq(V("ecran"), "prepartie"))


def construire(P):
    from .moteur3d import est_ecran_rendu

    T = Cible(P, "Tempête")
    T.costumes = [P.costume("violet", S.svg_plein("#7c3aed"), 240, 180)]
    T.visible = False
    T.layer = C.CALQUES["Tempête"]
    T.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([si(et(eq(V("horsZone"), 1), est_ecran_rendu()), [effet("GHOST", 72), montrer()], [cacher()])]),
    ])

    D = Cible(P, "Dégâts")
    D.costumes = [P.costume("rouge", S.svg_plein("#ef4444"), 240, 180)]
    D.visible = False
    D.layer = C.CALQUES["Dégâts"]
    D.var("g", 0)
    D.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([
            si(et3(eq(V("param_effetsDegats"), 1), gt(V("flash"), chrono()), est_ecran_rendu()), [
                setv("g", sub(100, mul(sub(V("flash"), chrono()), 180))),
                si(lt(V("g"), 45), [setv("g", 45)]),
                effet("GHOST", V("g")), montrer(),
            ], [
                si(et3(lt(V("❤ PV"), 30), eq(V("etat"), 1), en_jeu()), [effet("GHOST", 85), montrer()], [cacher()]),
            ]),
        ]),
    ])

    W = Cible(P, "Arme")
    W.costumes = [P.costume("pistolet", S.svg_arme("pistolet"), 140, 75),
                  P.costume("pompe", S.svg_arme("pompe"), 140, 75),
                  P.costume("sniper", S.svg_arme("sniper"), 140, 75)]
    # consommables et pioche en vue subjective : icônes agrandies si disponibles
    for code, nom in [(4, "bandages"), (5, "medikit"), (6, "minipotion"), (7, "potion"), (8, "pioche")]:
        try:
            W.costumes.append(P.costume(nom, UI.icone_objet(code), 24, 24))
        except Exception:
            W.costumes.append(P.costume(nom, S.svg_rect(48, 48, "#94a3b8", 8, 1.0, "#1e293b", 3), 24, 24))
    W.visible = False
    W.layer = C.CALQUES["Arme"]
    W.var("objet", 0)
    W.script(quand_drapeau(), [
        cacher(), taille(70),
        toujours([
            si(et4(ou(eq(V("etat"), 1), eq(V("etat"), 8)), gt(V("plan"), 0.5), et(en_jeu(), eq(V("superposition"), "")), lt(V("monEmoteFin"), chrono())), [
                setv("objet", item("Inventaire", V("slotActif"))),
                si(eq(V("armeNum"), 8), [setv("objet", 8)]),
                si(lt(V("objet"), 4), [
                    taille(70), costume(V("objet")),
                    aller(add(150, mul(V("tirAnim"), 4)), add(-110, mul(V("tirAnim"), 6))),
                    si(gt(V("rechargeFin"), 0), [mettre_y(-175)]),
                ], [
                    taille(220),
                    si(eq(V("objet"), 4), [costume("bandages")]), si(eq(V("objet"), 5), [costume("medikit")]),
                    si(eq(V("objet"), 6), [costume("minipotion")]), si(eq(V("objet"), 7), [costume("potion")]),
                    si(eq(V("objet"), 8), [costume("pioche")]),
                    aller(add(160, mul(V("tirAnim"), -8)), add(-120, mul(V("tirAnim"), 10))),
                    si(gt(V("utilisationFin"), chrono()), [aller(60, add(-120, mul(sin(mul(chrono(), 600)), 10)))]),
                ]),
                montrer(),
            ], [cacher()]),
        ]),
    ])

    F = Cible(P, "Flash")
    F.costumes = [P.costume("flash", S.svg_flash(), 40, 40)]
    F.visible = False
    F.layer = C.CALQUES["Flash"]
    F.script(quand_drapeau(), [
        cacher(), aller(40, -45), taille(120),
        toujours([si(et4(gt(V("tirAnim"), 2), gt(V("plan"), 0.5), lt(V("armeNum"), 4), eq(V("superposition"), "")), [montrer()], [cacher()])]),
    ])

    H = Cible(P, "Viseur")
    H.costumes = [P.costume("viseur", S.svg_viseur(False), 30, 30),
                  P.costume("touche", S.svg_viseur(True), 30, 30),
                  P.costume("lunette", S.svg_lunette(), 240, 180)]
    H.visible = False
    H.layer = C.CALQUES["Viseur"]
    H.script(quand_drapeau(), [
        aller(0, 0), cacher(),
        toujours([
            si(et3(ou(eq(V("etat"), 1), eq(V("etat"), 8)), en_jeu(), eq(V("superposition"), "")), [
                si(lt(V("plan"), 0.5), [costume("lunette"), taille(100)], [
                    taille(V("param_tailleHUD")),
                    si(gt(V("toucheFin"), chrono()), [costume("touche")], [costume("viseur")]),
                ]),
                montrer(),
            ], [cacher()]),
        ]),
    ])

    Msg = Cible(P, "Message")
    textes = {
        "connexion": ("Connexion au serveur…", "#ffffff", None),
        "plein": ("SERVEUR PLEIN", "#f87171", "Réessaie dans un instant (6 joueurs max)"),
        "elimine": ("ÉLIMINÉ !", "#f87171", "Tu peux observer les autres joueurs"),
        "aterre": ("À TERRE !", "#fb923c", "Un coéquipier peut te réanimer"),
        "reanime": ("RÉANIMÉ !", "#4ade80", "Reste à couvert"),
        "elimination": ("ÉLIMINATION !", "#fbbf24", None),
        "knock": ("ADVERSAIRE À TERRE", "#fbbf24", "Achève-le ou laisse-le saigner"),
        "recharge": ("Rechargement…", "#e5e7eb", None),
        "victoire": ("VICTOIRE ROYALE !", "#fbbf24", "n°1 de la partie"),
        "defaite": ("PARTIE TERMINÉE", "#e5e7eb", "Voir le récapitulatif"),
        "zone": ("LA ZONE SE REFERME", "#a78bfa", "Rejoins le cercle"),
        "zonebouge": ("ZONE EN MOUVEMENT", "#a78bfa", "Le cercle se déplace !"),
        "coffre": ("COFFRE OUVERT", "#fbbf24", None),
        "prepartie": ("ÎLE D'ATTENTE", "#67e8f9", "Le bus décolle bientôt"),
        "bus": ("SAUTE DU BUS !", "#67e8f9", "Espace pour sauter"),
        "atterrissage": ("ATTERRISSAGE", "#4ade80", "Trouve des armes et du butin"),
        "redeploiement": ("REDÉPLOIEMENT", "#67e8f9", "Un coéquipier t'a ramené"),
        "niveau": ("NIVEAU SUPÉRIEUR !", "#fbbf24", "Récompense débloquée"),
        "quete": ("QUÊTE TERMINÉE", "#4ade80", "+XP"),
        "ltm": ("ÉVÉNEMENT LIMITÉ", "#f472b6", "Règles spéciales actives"),
    }
    Msg.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    for cle, val in textes.items():
        Msg.costumes.append(P.costume(cle, S.svg_texte(val[0], val[1], 34, "#111827", val[2]), 170, 50))
    Msg.visible = False
    Msg.layer = C.CALQUES["Message"]
    Msg.var("dernier", "")
    Msg.var("fin", 0)
    Msg.script(quand_drapeau(), [
        aller(0, 60), cacher(), setv("dernier", ""), setv("fin", 0),
        toujours([
            si(non(eq(V("message"), V("dernier"))), [
                setv("dernier", V("message")),
                si(eq(V("message"), ""), [costume("vide"), cacher()], [
                    costume(V("message")), setv("fin", add(chrono(), 3)), montrer(),
                ]),
                si(ou(eq(V("message"), "plein"), eq(V("message"), "connexion")), [setv("fin", add(chrono(), 9999))]),
            ]),
            si(gt(chrono(), V("fin")), [cacher(), setv("message", ""), setv("dernier", "")]),
        ]),
    ])
