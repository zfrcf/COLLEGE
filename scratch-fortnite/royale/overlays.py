# -*- coding: utf-8 -*-
"""
Superpositions visibles en jeu : teinte de tempête, flash de dégâts, arme en vue subjective,
flash de bouche, viseur / lunette, bannières de message (sprite Message piloté par `message`,
costumes FR et EN selon `param_langue`, cachées sur les écrans « pause » et « fin »).
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
        # teinte violette qui pulse légèrement hors zone (le moteur assombrit aussi ciel et murs et ajoute une vignette)
        toujours([si(et(eq(V("horsZone"), 1), est_ecran_rendu()), [effet("GHOST", add(72, mul(5, sin(mul(chrono(), 160))))), montrer()], [cacher()])]),
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
    # armes : costumes 1..6 dans l'ordre des codes d'objets (sélection par numéro)
    W.costumes = [P.costume("pistolet", S.svg_arme("pistolet"), 140, 75),
                  P.costume("pompe", S.svg_arme("pompe"), 140, 75),
                  P.costume("sniper", S.svg_arme("sniper"), 140, 75),
                  P.costume("assaut", S.svg_arme("assaut"), 140, 75),
                  P.costume("pm", S.svg_arme("pm"), 140, 75),
                  P.costume("lance", S.svg_arme("lance"), 140, 75)]
    # consommables (7..10) et pioche (11) en vue subjective : icônes agrandies si disponibles
    for code, nom in [(7, "bandages"), (8, "medikit"), (9, "minipotion"), (10, "potion"), (11, "pioche")]:
        try:
            W.costumes.append(P.costume(nom, UI.icone_objet(code), 24, 24))
        except Exception:
            W.costumes.append(P.costume(nom, S.svg_rect(48, 48, "#94a3b8", 8, 1.0, "#1e293b", 3), 24, 24))
    W.visible = False
    W.layer = C.CALQUES["Arme"]
    W.var("objet", 0)
    for v in ["dist0", "bob", "ph", "ax", "ay", "p", "ta"]:    # balancement de marche, recul, rechargement
        W.var(v, 0)
    W.script(quand_drapeau(), [
        cacher(), taille(58), setv("dist0", 0), setv("bob", 0), setv("ph", 0),
        toujours([
            si(et4(ou(eq(V("etat"), 1), eq(V("etat"), 8)), gt(V("plan"), 0.5), et(en_jeu(), eq(V("superposition"), "")), lt(V("monEmoteFin"), chrono())), [
                setv("objet", item("Inventaire", V("slotActif"))),
                si(eq(V("armeNum"), C.PIOCHE), [setv("objet", C.PIOCHE)]),
                si(lt(V("objet"), C.CONSO_MIN), [
                    taille(58), costume(V("objet")),
                    # balancement de marche : la distance parcourue augmente → oscillation (amortie à l'arrêt)
                    si(gt(V("stat_distance"), add(V("dist0"), 0.005)), [setv("bob", minimum(add(V("bob"), 0.2), 1))], [setv("bob", mul(V("bob"), 0.8))]),
                    setv("dist0", V("stat_distance")),
                    setv("ph", mod(add(V("ph"), mul(V("bob"), 13)), 360)),
                    # recul visuel (tirAnim 4 → 0) et secousse d'écran du moteur
                    setv("ta", minimum(V("tirAnim"), 4)),
                    setv("ax", add(add(178, mul(sin(V("ph")), mul(8, V("bob")))), add(mul(V("ta"), 5), mul(V("m3d_secX"), 0.5)))),
                    setv("ay", add(add(-118, mul(absv(cos(V("ph"))), mul(-6, V("bob")))), add(mul(V("ta"), 7), mul(V("m3d_secY"), 0.5)))),
                    si(gt(V("rechargeFin"), 0), [
                        # rechargement : l'arme descend puis remonte (demi-sinus sur la durée), légèrement inclinée
                        setv("p", div(sub(chrono(), V("rechargeDebut")), maximum(sub(V("rechargeFin"), V("rechargeDebut")), 0.1))),
                        si(lt(V("p"), 0), [setv("p", 0)]), si(gt(V("p"), 1), [setv("p", 1)]),
                        changev("ay", mul(-80, sin(mul(V("p"), 180)))), pointer(add(90, mul(35, sin(mul(V("p"), 180))))),
                    ], [pointer(sub(90, mul(V("ta"), 4)))]),
                    aller(V("ax"), V("ay")),
                ], [
                    taille(220), pointer(90),
                    si(eq(V("objet"), 7), [costume("bandages")]), si(eq(V("objet"), 8), [costume("medikit")]),
                    si(eq(V("objet"), 9), [costume("minipotion")]), si(eq(V("objet"), 10), [costume("potion")]),
                    si(eq(V("objet"), C.PIOCHE), [costume("pioche")]),
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
        toujours([si(et4(gt(V("tirAnim"), 2), gt(V("plan"), 0.5), lt(V("armeNum"), C.CONSO_MIN), eq(V("superposition"), "")), [
            # flash de bouche plus grand pour le pompe, le sniper et le lance-grenades ; orientation aléatoire
            taille(120), si(eq(V("armeNum"), 2), [taille(200)]), si(eq(V("armeNum"), 3), [taille(165)]),
            si(eq(V("armeNum"), 6), [taille(180)]),
            pointer(hasard(45, 135)), aller(add(40, mul(V("m3d_secX"), 0.5)), add(-45, mul(V("m3d_secY"), 0.5))), montrer(),
        ], [cacher()])]),
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
                aller(mul(V("m3d_secX"), 0.3), mul(V("m3d_secY"), 0.3)),      # suit un peu la secousse d'écran
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
        "largage": ("LARGAGE EN COURS", "#60a5fa", "Butin légendaire dans la prochaine zone"),
    }
    textes_en = {
        "connexion": ("Connecting to the server…", None),
        "plein": ("SERVER FULL", "Try again in a moment (6 players max)"),
        "elimine": ("ELIMINATED!", "You can watch the other players"),
        "aterre": ("KNOCKED DOWN!", "A teammate can revive you"),
        "reanime": ("REVIVED!", "Stay under cover"),
        "elimination": ("ELIMINATION!", None),
        "knock": ("OPPONENT KNOCKED", "Finish them or let them bleed out"),
        "recharge": ("Reloading…", None),
        "victoire": ("VICTORY ROYALE!", "#1 of the match"),
        "defaite": ("MATCH OVER", "See the recap"),
        "zone": ("THE STORM IS CLOSING", "Get to the circle"),
        "zonebouge": ("MOVING STORM", "The circle is moving!"),
        "coffre": ("CHEST OPENED", None),
        "prepartie": ("WAITING ISLAND", "The bus takes off soon"),
        "bus": ("JUMP FROM THE BUS!", "Press space to jump"),
        "atterrissage": ("LANDED", "Find weapons and loot"),
        "redeploiement": ("REBOOTED", "A teammate brought you back"),
        "niveau": ("LEVEL UP!", "Reward unlocked"),
        "quete": ("QUEST COMPLETE", "+XP"),
        "ltm": ("LIMITED TIME EVENT", "Special rules active"),
        "largage": ("SUPPLY DROP INCOMING", "Legendary loot in the next zone"),
    }
    assert set(textes_en) == set(textes)
    Msg.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    for cle, val in textes.items():
        Msg.costumes.append(P.costume(cle, S.svg_texte(val[0], val[1], 34, "#111827", val[2]), 170, 50))
        en = textes_en[cle]
        Msg.costumes.append(P.costume(cle + "_en", S.svg_texte(en[0], val[1], 34, "#111827", en[1]), 170, 50))
    Msg.visible = False
    Msg.layer = C.CALQUES["Message"]
    Msg.var("dernier", "")
    Msg.var("fin", 0)
    # La bannière (sprite, donc au-dessus du stylo) n'est pas montrée sur les écrans « pause » et « fin », dont les
    # panneaux de Menus occupent le centre (l'écran de fin annonce déjà la victoire / la défaite) ; le message expire
    # normalement pendant ce temps. Costumes FR (<message>) et EN (<message>_en) selon param_langue.
    hors_menu = non(ou(eq(V("ecran"), "pause"), eq(V("ecran"), "fin")))
    Msg.script(quand_drapeau(), [
        aller(0, 60), cacher(), setv("dernier", ""), setv("fin", 0),
        toujours([
            si(non(eq(V("message"), V("dernier"))), [
                setv("dernier", V("message")),
                si(eq(V("message"), ""), [costume("vide"), cacher()], [
                    si(eq(V("param_langue"), 1), [costume(join(V("message"), "_en"))], [costume(V("message"))]),
                    setv("fin", add(chrono(), 3)), si(hors_menu, [montrer()]),
                ]),
                si(ou(eq(V("message"), "plein"), eq(V("message"), "connexion")), [setv("fin", add(chrono(), 9999))]),
            ]),
            si(gt(chrono(), V("fin")), [cacher(), setv("message", ""), setv("dernier", "")], [
                si(et(non(eq(V("message"), "")), non(hors_menu)), [cacher()]),
            ]),
        ]),
    ])
