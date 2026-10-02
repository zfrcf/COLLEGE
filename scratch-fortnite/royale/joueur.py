# -*- coding: utf-8 -*-
"""
Sprites Reseau et Joueur.

Reseau : prend un emplacement cloud (☁ J1..☁ J6) avec reconnexion, encode mon paquet, décode
ceux des autres dans les listes E_*, détecte les événements (coups reçus → DegatsRecus, morts →
Journal/éliminations, émotes, pings, chat, bruits), synchronise la construction partagée
(☁ Construction + ☁ Construction2) et le ☁ Record.

Joueur : entrées (touches configurables, souris, sensibilité), déplacement avec collisions,
sprint/endurance, saut, inventaire 5 cases + pioche, armes (chargeur, réserve, rechargement),
consommables (barre d'utilisation), récolte de matériaux et destruction de murs, construction
(bois/pierre/métal, édition), interactions (coffre, réanimation, redéploiement), dégâts
(surbouclier, bouclier, PV, à terre, mort), tempête, lieux nommés, statistiques, événements.
"""
from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S

V = Var
A = Arg
ETAT = C.ETAT


def ecran_jouable():
    return ou(eq(V("ecran"), "jeu"), eq(V("ecran"), "prepartie"))


def meme_equipe(k):
    """Vrai si l'emplacement k est dans mon équipe (équipes > 0)."""
    return et(gt(V("monEquipe"), 0), eq(item("E_equipe", k), V("monEquipe")))


def est_vivant_ou_aterre(k):
    return ou(eq(item("E_etat", k), 1), eq(item("E_etat", k), 3))


def construire(P):
    construire_reseau(P)
    construire_joueur(P)


# ===========================================================================
#  RESEAU
# ===========================================================================
def construire_reseau(P):
    R = Cible(P, "Reseau")
    R.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    R.visible = False
    R.layer = C.CALQUES["Reseau"]
    for v in ["k", "age", "premiere", "dernierEnvoye", "dernierEnvoiT", "nx", "ny", "c", "base", "n2", "code",
              "_angle", "adx", "ady", "dist", "prochainRecord", "i", "j", "score", "place", "texte", "libre",
              "trouve", "dernierConstruction", "longueurAvant", "tDernierPaquet"]:
        R.var(v, 0)
    R.liste("rec_codes", ["", "", ""])
    R.liste("rec_e", [0, 0, 0])
    R.liste("rec_v", [0, 0, 0])

    # --- accès aux emplacements cloud -------------------------------------------
    R.proc("lire paquet", [("n", "n")],
           [si(eq(A("n"), k), [setv("paquet", V("☁ J%d" % k))]) for k in range(1, C.NB_JOUEURS + 1)])
    R.proc("ecrire paquet", [("n", "n"), ("valeur", "s")],
           [si(eq(A("n"), k), [setv("☁ J%d" % k, A("valeur"))]) for k in range(1, C.NB_JOUEURS + 1)])
    R.proc("extraire", [("debut", "n"), ("longueur", "n")], [
        setv("_ext", ""), setv("_i", A("debut")),
        repeter(A("longueur"), [setv("_ext", join(V("_ext"), lettre(V("_i"), V("paquet")))), changev("_i", 1)]),
    ])
    R.proc("ajouter", [("valeur", "n"), ("chiffres", "n")], [
        setv("_pad", rnd(A("valeur"))),
        si(lt(V("_pad"), 0), [setv("_pad", 0)]),
        repeter_jusqua(ge(longueur(V("_pad")), A("chiffres")), [setv("_pad", join("0", V("_pad")))]),
        setv("paquet", join(V("paquet"), V("_pad"))),
    ])
    R.proc("maintenant", [], [setv("maintenant", mod(floor(mul(jours2000(), 86400)), 100000))])
    R.proc("coder nom", [], [
        setv("nomCode", ""), setv("_i", 1), setv("monNom", pseudo()),
        repeter(8, [
            setv("_pad", num_item("Alphabet", lettre(V("_i"), pseudo()))),
            si(lt(V("_pad"), 10), [setv("_pad", join("0", V("_pad")))]),
            setv("nomCode", join(V("nomCode"), V("_pad"))),
            changev("_i", 1),
        ]),
        si(eq(longueur(pseudo()), 0), [setv("monNom", "Joueur")]),
    ])

    # --- encodage ----------------------------------------------------------------
    def clamp_pos(v):
        return v   # px, py restent dans ]0, TAILLE[ grâce aux murs de bordure

    expressions = {
        "x": rnd(mul(V("nx"), 100)), "y": rnd(mul(V("ny"), 100)),
        "dir": mod(rnd(V("dir")), 360), "pv": V("❤ PV"), "bouclier": V("🛡 Bouclier"),
        "battement": V("maintenant"), "cible": V("cible"), "seq": V("seq"), "degats": V("degats"),
        "tueur": V("tueur"), "morts": V("morts"), "arme": V("armeNum"), "etat": V("etat"),
        "elims": mod(V("💀 Éliminations"), 100), "niveau": V("niveau"), "equipe": V("monEquipe"),
        "emote": V("emote"), "emoteSeq": V("emoteSeq"), "pingX": V("pingX"), "pingY": V("pingY"),
        "pingSeq": V("pingSeq"), "chat": V("chat"), "chatSeq": V("chatSeq"), "salon": V("codeSalon"),
        "altitude": V("altitude"), "reanime": V("reanime"), "skin": V("skin"), "pioche": V("pioche"),
        "planeur": V("planeur"), "surbouclier": V("surbouclier"), "modeChoisi": V("modeChoisi"),
        "degatsTotal": mod(V("stat_degats"), 10000), "victoires": mod(V("stat_victoires"), 100),
        "banniere": V("banniere"), "knockPar": V("knockPar"),
    }
    corps = [
        setv("paquet", "1"),
        setv("nx", V("px")), setv("ny", V("py")),
        si(eq(V("etat"), ETAT["mort"]), [setv("nx", V("mortX")), setv("ny", V("mortY"))]),
    ]
    for nom, longueur_champ in C.CHAMPS:
        if nom == "nom":
            corps.append(setv("paquet", join(V("paquet"), V("nomCode"))))
        else:
            corps.append(appel("ajouter", expressions[nom], longueur_champ))
    R.proc("encoder", [], corps)
    R.proc("envoyer", [("force", "n")], [
        appel("encoder"),
        si(et(non(eq_txt(V("paquet"), V("dernierEnvoye"))),
              ou(eq(A("force"), 1), gt(sub(chrono(), V("dernierEnvoiT")), 0.1))), [
            appel("ecrire paquet", V("monSlot"), V("paquet")),
            setv("dernierEnvoye", V("paquet")),
            setv("dernierEnvoiT", chrono()),
            changev("paquetsEnvoyes", 1),
        ]),
    ])

    # --- angle monde → angle relatif à la vue (0 devant, 90 à droite) ------------------
    R.proc("angle vers", [("x", "n"), ("y", "n")], [
        setv("adx", sub(A("x"), V("px"))), setv("ady", sub(A("y"), V("py"))),
        si(lt(absv(V("adx")), 0.0001), [
            si(gt(V("ady"), 0), [setv("_angle", 90)], [setv("_angle", 270)]),
        ], [
            setv("_angle", atan(div(V("ady"), V("adx")))),
            si(lt(V("adx"), 0), [changev("_angle", 180)]),
        ]),
        setv("_angle", mod(sub(V("dir"), V("_angle")), 360)),
        setv("dist", sqrt(add(mul(V("adx"), V("adx")), mul(V("ady"), V("ady"))))),
    ])

    # --- décodage d'un emplacement ------------------------------------------------
    def ext(nom):
        p, l = C.POS[nom]
        return appel("extraire", p, l)

    decodage = []
    for nom, _ in C.CHAMPS:
        if nom == "nom":
            decodage += [
                setv("_pad", ""), setv("_i", C.POS["nom"][0]),
                repeter(8, [
                    setv("nx", join(lettre(V("_i"), V("paquet")), lettre(add(V("_i"), 1), V("paquet")))),
                    si(gt(V("nx"), 0), [setv("_pad", join(V("_pad"), item("Alphabet", V("nx"))))]),
                    changev("_i", 2),
                ]),
                si(eq(longueur(V("_pad")), 0), [setv("_pad", join("J", A("n")))]),
                remplacer("E_nom", A("n"), V("_pad")),
            ]
        elif nom in ("x", "y"):
            decodage += [ext(nom), remplacer("E_" + nom, A("n"), div(V("_ext"), 100))]
        else:
            decodage += [ext(nom), remplacer("E_" + nom, A("n"), mul(V("_ext"), 1))]

    def nom_de(k):
        return item("E_nom", k)

    def journal(texte):
        return [ajouter_liste("Journal", texte), ajouter_liste("JournalFin", add(chrono(), 8)),
                si(gt(long_liste("Journal"), 6), [supprimer("Journal", 1), supprimer("JournalFin", 1)])]

    def notification(texte):
        return [ajouter_liste("Notifications", texte), ajouter_liste("NotificationsFin", add(chrono(), 4)),
                si(gt(long_liste("Notifications"), 4), [supprimer("Notifications", 1), supprimer("NotificationsFin", 1)])]

    def son_spatial(nom_son, portee):
        return [si(lt(V("dist"), portee), [
            setv("son_pan", rnd(mul(sin(V("_angle")), 100))),
            setv("son_volume", rnd(sub(100, mul(div(V("dist"), portee), 80)))),
            diffuser("son " + nom_son),
        ])]

    n = A("n")
    evenements = [
        # ----- tir sur moi -----
        si(et(eq(item("E_cible", n), V("monSlot")), non(eq(item("E_seq", n), item("E_dernierSeq", n)))), [
            remplacer("E_dernierSeq", n, item("E_seq", n)),
            si(ou3(eq(V("etat"), 1), eq(V("etat"), 3), eq(V("etat"), 8)), [
                ajouter_liste("DegatsRecus", join(n, join(C.rembourrer(item("E_degats", n), 3), item("E_arme", n)))),
            ]),
        ]),
        # ----- coup de feu entendu (n° de tir changé) -----
        si(non(eq(item("E_seq", n), item("E_vuA", n))), [
            remplacer("E_vuA", n, item("E_seq", n)),
            appel("angle vers", item("E_x", n), item("E_y", n)),
            si(lt(V("dist"), 24), [
                ajouter_liste("Bruits", join(C.rembourrer(V("_angle"), 3), join(C.rembourrer(mul(add(chrono(), 1.2), 10), 6), 1))),
                si(gt(long_liste("Bruits"), 8), [supprimer("Bruits", 1)]),
                si(eq(item("E_arme", n), 1), son_spatial("tir_pistolet", 24)),
                si(eq(item("E_arme", n), 2), son_spatial("tir_pompe", 24)),
                si(eq(item("E_arme", n), 3), son_spatial("tir_sniper", 30)),
            ]),
        ]),
        # ----- mort observée -----
        si(non(eq(item("E_morts", n), item("E_dernierMorts", n))), [
            remplacer("E_dernierMorts", n, item("E_morts", n)),
            si(eq(item("E_tueur", n), 0), journal(join(nom_de(n), tr_txt(" est tombé dans la tempête", " fell to the storm"))), [
                si(eq(item("E_tueur", n), V("monSlot")), [
                    journal(join(tr_txt("Tu as éliminé ", "You eliminated "), nom_de(n))),
                    changev("💀 Éliminations", 1), changev("stat_elims", 1),
                    setv("evt_cible", n), diffuser("evt elimination"),
                    setv("message", "elimination"), setv("son_pan", 0), setv("son_volume", 100), diffuser("son elimination"),
                ], [
                    journal(joins(nom_de(item("E_tueur", n)), tr_txt(" a éliminé ", " eliminated "), nom_de(n),
                                  " (", item("ObjetNoms", item("E_arme", item("E_tueur", n))), ")")),
                ]),
            ]),
        ]),
        # ----- mis à terre observé -----
        si(et(eq(item("E_etat", n), 3), non(eq(item("E_dernierEtat", n), 3))), [
            si(eq(item("E_knockPar", n), V("monSlot")), [
                journal(join(tr_txt("Tu as mis à terre ", "You knocked "), nom_de(n))),
                setv("evt_cible", n), diffuser("evt knock"), setv("message", "knock"),
            ], [
                si(gt(item("E_knockPar", n), 0), [
                    journal(joins(nom_de(item("E_knockPar", n)), tr_txt(" a mis à terre ", " knocked "), nom_de(n))),
                ]),
            ]),
        ]),
        remplacer("E_dernierEtat", n, item("E_etat", n)),
        # ----- émote -----
        si(non(eq(item("E_emoteSeq", n), item("E_dernierEmoteSeq", n))), [
            remplacer("E_dernierEmoteSeq", n, item("E_emoteSeq", n)),
            si(non(contient("Muets", n)), [
                remplacer("E_emoteFin", n, add(chrono(), 3)),
                setv("evt_cible", n), setv("evt_valeur", item("E_emote", n)), diffuser("evt emote"),
                appel("angle vers", item("E_x", n), item("E_y", n)), son_spatial("emote", 20),
            ]),
        ]),
        # ----- ping (coéquipiers, ou tout le monde en Rumble) -----
        si(non(eq(item("E_pingSeq", n), item("E_dernierPingSeq", n))), [
            remplacer("E_dernierPingSeq", n, item("E_pingSeq", n)),
            si(et(non(contient("Muets", n)), ou(meme_equipe(n), eq(V("mode"), 5))), [
                # retirer l'ancien ping de cet emplacement
                setv("i", 1), setv("j", long_liste("Pings")),
                repeter(V("j"), [
                    si(eq(lettre(1, item("Pings", V("i"))), n), [supprimer("Pings", V("i"))], [changev("i", 1)]),
                ]),
                ajouter_liste("Pings", joins(n, C.rembourrer(mul(item("E_pingX", n), 100), 4),
                                             C.rembourrer(mul(item("E_pingY", n), 100), 4),
                                             C.rembourrer(mul(add(chrono(), 20), 10), 6))),
                setv("evt_cible", n), setv("evt_valeur", add(mul(item("E_pingX", n), 100), item("E_pingY", n))),
                diffuser("evt ping"),
                notification(join(nom_de(n), tr_txt(" a posé un marqueur", " placed a marker"))),
                setv("son_pan", 0), setv("son_volume", 70), diffuser("son notification"),
            ]),
        ]),
        # ----- message rapide -----
        si(non(eq(item("E_chatSeq", n), item("E_dernierChatSeq", n))), [
            remplacer("E_dernierChatSeq", n, item("E_chatSeq", n)),
            si(et(non(contient("Muets", n)), ou3(meme_equipe(n), eq(V("monEquipe"), 0), eq(V("mode"), 5))), [
                si(gt(item("E_chat", n), 0), [
                    si(lt(item("E_chat", n), 20), [
                        ajouter_liste("Chat", join(nom_de(n), join(" : ", item("ChatRapide", add(item("E_chat", n), mul(len(C.CHAT_RAPIDE), V("param_langue"))))))),
                    ], [
                        ajouter_liste("Chat", joins(nom_de(n), tr_txt(" partage la quête : ", " shares the quest: "),
                                                    item("QueteTitres", add(sub(item("E_chat", n), 20), mul(div(long_liste("QueteTitres"), 2), V("param_langue")))))),
                    ]),
                    ajouter_liste("ChatFin", add(chrono(), 8)),
                    si(gt(long_liste("Chat"), 5), [supprimer("Chat", 1), supprimer("ChatFin", 1)]),
                    setv("evt_cible", n), setv("evt_valeur", item("E_chat", n)), diffuser("evt chat"),
                    setv("son_pan", 0), setv("son_volume", 60), diffuser("son notification"),
                ]),
            ]),
        ]),
        # ----- bruit de pas (déplacement proche) -----
        si(et(lt(V("dist"), 7), gt(add(absv(sub(item("E_x", n), V("nx"))), absv(sub(item("E_y", n), V("ny")))), 0.05)), [
            si(gt(chrono(), item("E_dernierBattement", n)), [
                appel("angle vers", item("E_x", n), item("E_y", n)),
                ajouter_liste("Bruits", join(C.rembourrer(V("_angle"), 3), join(C.rembourrer(mul(add(chrono(), 0.6), 10), 6), 2))),
                si(gt(long_liste("Bruits"), 8), [supprimer("Bruits", 1)]),
                remplacer("E_dernierBattement", n, add(chrono(), 0.5)),
            ]),
        ]),
    ]

    R.proc("decoder", [("n", "n")], [
        appel("lire paquet", n),
        si(non(eq_txt(V("paquet"), item("E_paquet", n))), [
            changev("paquetsRecus", 1),
            setv("latence", rnd(add(mul(V("latence"), 0.8), mul(sub(chrono(), V("tDernierPaquet")), 200)))),
            setv("tDernierPaquet", chrono()),
            si(lt(longueur(V("paquet")), C.LONGUEUR_PAQUET), [
                remplacer("E_paquet", n, V("paquet")),
                remplacer("E_battement", n, -100000), remplacer("E_vu", n, 0),
            ], [
                setv("premiere", 0),
                si(eq(item("E_vu", n), 0), [setv("premiere", 1)]),
                # positions précédentes (bruit de pas) et distance
                setv("nx", item("E_x", n)), setv("ny", item("E_y", n)),
                appel("angle vers", item("E_x", n), item("E_y", n)),
            ] + decodage + [
                remplacer("E_vu", n, 1),
                si(eq(V("premiere"), 1), [
                    remplacer("E_dernierSeq", n, item("E_seq", n)), remplacer("E_dernierMorts", n, item("E_morts", n)),
                    remplacer("E_dernierEmoteSeq", n, item("E_emoteSeq", n)), remplacer("E_dernierPingSeq", n, item("E_pingSeq", n)),
                    remplacer("E_dernierChatSeq", n, item("E_chatSeq", n)), remplacer("E_dernierEtat", n, item("E_etat", n)),
                    remplacer("E_vuA", n, item("E_seq", n)), remplacer("E_dernierBattement", n, 0),
                ], evenements),
                remplacer("E_paquet", n, V("paquet")),
            ]),
        ]),
        # activité : battement récent, paquet complet, même code de salon
        setv("age", absv(C.ecart(V("maintenant"), item("E_battement", n)))),
        si(et3(lt(V("age"), 15), eq(item("E_vu", n), 1), eq(item("E_salon", n), V("codeSalon"))),
           [remplacer("E_actif", n, 1)], [remplacer("E_actif", n, 0)]),
    ])

    # --- rejoindre : reconnexion puis premier emplacement libre ------------------------
    R.proc("rejoindre", [], [
        appel("maintenant"), setv("monSlot", 0), setv("k", 1), setv("reconnexion", 0),
        # 1) reconnexion : un emplacement à mon nom, actif il y a moins de 90 s
        si(gt(V("nomCode"), 0), [
            repeter(C.NB_JOUEURS, [
                si(eq(V("monSlot"), 0), [
                    appel("lire paquet", V("k")),
                    si(ge(longueur(V("paquet")), C.LONGUEUR_PAQUET), [
                        appel("extraire", C.POS["nom"][0], C.POS["nom"][1]),
                        si(eq_txt(V("_ext"), V("nomCode")), [
                            appel("extraire", C.POS["battement"][0], C.POS["battement"][1]),
                            si(lt(absv(C.ecart(V("maintenant"), V("_ext"))), 90), [
                                setv("monSlot", V("k")), setv("reconnexion", 1),
                                appel("decoder", V("k")),     # restaure E_* pour relire mon état
                                setv("❤ PV", item("E_pv", V("k"))), setv("🛡 Bouclier", item("E_bouclier", V("k"))),
                                setv("💀 Éliminations", item("E_elims", V("k"))), setv("stat_elims", item("E_elims", V("k"))),
                                setv("px", item("E_x", V("k"))), setv("py", item("E_y", V("k"))),
                                setv("morts", item("E_morts", V("k"))), setv("seq", item("E_seq", V("k"))),
                                setv("etat", item("E_etat", V("k"))),
                                si(non(ou(eq(V("etat"), 1), eq(V("etat"), 3))), [setv("etat", 5)]),
                            ]),
                        ]),
                    ]),
                ]),
                changev("k", 1),
            ]),
        ]),
        # 2) premier emplacement libre (vide ou battement périmé)
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(eq(V("monSlot"), 0), [
                appel("lire paquet", V("k")),
                si(lt(longueur(V("paquet")), C.LONGUEUR_PAQUET), [setv("monSlot", V("k"))], [
                    appel("extraire", C.POS["battement"][0], C.POS["battement"][1]),
                    si(gt(absv(C.ecart(V("maintenant"), V("_ext"))), 15), [setv("monSlot", V("k"))]),
                ]),
            ]),
            changev("k", 1),
        ]),
        si(gt(V("monSlot"), 0), [
            setv("connecte", 1), appel("envoyer", 1),
            si(eq(V("reconnexion"), 1), [notification(tr_txt("Reconnexion à la partie en cours", "Reconnected to the match in progress"))]),
        ], [setv("connecte", 0), setv("message", "plein")]),
    ])

    # --- construction partagée ------------------------------------------------------
    R.proc("copier carte", [], [
        setv("_i", 1),
        repeter(C.TAILLE * C.TAILLE, [remplacer("Carte", V("_i"), item("CarteBase", V("_i"))), changev("_i", 1)]),
    ])
    R.proc("appliquer entrees", [("texte", "s")], [
        setv("_i", 2),
        repeter(floor(div(sub(longueur(A("texte")), 1), 5)), [
            setv("code", lettre(V("_i"), A("texte"))),
            setv("nx", join(lettre(add(V("_i"), 1), A("texte")), lettre(add(V("_i"), 2), A("texte")))),
            setv("ny", join(lettre(add(V("_i"), 3), A("texte")), lettre(add(V("_i"), 4), A("texte")))),
            si(et4(gt(V("nx"), 0), gt(V("ny"), 0), lt(V("nx"), C.TAILLE - 1), lt(V("ny"), C.TAILLE - 1)), [
                si(eq(V("code"), 0), [remplacer("Carte", C.index_cellule(V("nx"), V("ny")), 0)], [
                    si(eq(V("code"), 1), [remplacer("Carte", C.index_cellule(V("nx"), V("ny")), C.MUR_PAR_MATERIAU[1])]),
                    si(eq(V("code"), 2), [remplacer("Carte", C.index_cellule(V("nx"), V("ny")), C.MUR_PAR_MATERIAU[2])]),
                    si(eq(V("code"), 3), [remplacer("Carte", C.index_cellule(V("nx"), V("ny")), C.MUR_PAR_MATERIAU[3])]),
                ]),
            ]),
            changev("_i", 5),
        ]),
    ])
    R.proc("synchroniser construction", [], [
        setv("base", join(V("☁ Construction"), join("|", V("☁ Construction2")))),
        si(non(eq_txt(V("base"), V("dernierConstruction"))), [
            si(lt(longueur(V("base")), V("longueurAvant")), [appel("copier carte")]),
            appel("copier carte"),
            appel("appliquer entrees", V("☁ Construction")),
            appel("appliquer entrees", V("☁ Construction2")),
            setv("dernierConstruction", V("base")), setv("longueurAvant", longueur(V("base"))),
        ]),
    ])

    # --- ☁ Record : "1" + 3 × [nom16 elims4 victoires3] ---------------------------------
    R.proc("lire record", [], [
        setv("texte", V("☁ Record")), setv("i", 0),
        repeter(3, [
            setv("j", add(2, mul(V("i"), C.RECORD_TAILLE))),
            si(ge(longueur(V("texte")), add(V("j"), C.RECORD_TAILLE - 1)), [
                setv("_pad", ""), setv("code", ""), setv("k", 0),
                repeter(8, [
                    setv("nx", join(lettre(add(V("j"), mul(V("k"), 2)), V("texte")), lettre(add(add(V("j"), mul(V("k"), 2)), 1), V("texte")))),
                    setv("code", join(V("code"), V("nx"))),
                    si(gt(V("nx"), 0), [setv("_pad", join(V("_pad"), item("Alphabet", V("nx"))))]),
                    changev("k", 1),
                ]),
                remplacer("rec_codes", add(V("i"), 1), V("code")),
                remplacer("Record_nom", add(V("i"), 1), V("_pad")),
                remplacer("rec_e", add(V("i"), 1), mul(C.sous_chaine(V("texte"), add(V("j"), 16), 4), 1)),
                remplacer("Record_elims", add(V("i"), 1), item("rec_e", add(V("i"), 1))),
                remplacer("rec_v", add(V("i"), 1), mul(C.sous_chaine(V("texte"), add(V("j"), 20), 3), 1)),
                remplacer("Record_victoires", add(V("i"), 1), item("rec_v", add(V("i"), 1))),
            ], [
                remplacer("rec_codes", add(V("i"), 1), ""), remplacer("Record_nom", add(V("i"), 1), ""),
                remplacer("rec_e", add(V("i"), 1), 0), remplacer("Record_elims", add(V("i"), 1), 0),
                remplacer("rec_v", add(V("i"), 1), 0), remplacer("Record_victoires", add(V("i"), 1), 0),
            ]),
            changev("i", 1),
        ]),
        diffuser("evt record"),
    ])
    R.proc("ecrire record", [], [
        setv("texte", "1"), setv("i", 1),
        repeter(3, [
            si(gt(longueur(item("rec_codes", V("i"))), 0), [
                setv("texte", joins(V("texte"), item("rec_codes", V("i")), C.rembourrer(item("rec_e", V("i")), 4),
                                    C.rembourrer(item("rec_v", V("i")), 3))),
            ]),
            changev("i", 1),
        ]),
        setv("☁ Record", V("texte")),
    ])
    R.script(quand_message("record proposer"), [
        si(et(gt(V("nomCode"), 0), gt(add(V("rec_elims"), V("rec_victoires")), 0)), [
            appel("lire record"),
            # retirer mon ancienne entrée
            setv("i", 1),
            repeter(3, [
                si(eq_txt(item("rec_codes", V("i")), V("nomCode")), [
                    remplacer("rec_codes", V("i"), ""), remplacer("rec_e", V("i"), 0), remplacer("rec_v", V("i"), 0),
                ]),
                changev("i", 1),
            ]),
            # trouver la place (score = victoires × 10000 + élims)
            setv("score", add(mul(V("rec_victoires"), 10000), V("rec_elims"))), setv("place", 0), setv("i", 3),
            repeter(3, [
                si(ou(eq(longueur(item("rec_codes", V("i"))), 0),
                      gt(V("score"), add(mul(item("rec_v", V("i")), 10000), item("rec_e", V("i"))))), [setv("place", V("i"))]),
                changev("i", -1),
            ]),
            si(gt(V("place"), 0), [
                inserer("rec_codes", V("place"), V("nomCode")), inserer("rec_e", V("place"), V("rec_elims")),
                inserer("rec_v", V("place"), V("rec_victoires")),
                supprimer("rec_codes", 4), supprimer("rec_e", 4), supprimer("rec_v", 4),
                appel("ecrire record"), appel("lire record"),
            ]),
        ]),
    ])

    # --- boucle principale -----------------------------------------------------------------
    R.script(quand_drapeau(), [
        cacher(), setv("connecte", 0), setv("monSlot", 0), setv("paquetsEnvoyes", 0), setv("paquetsRecus", 0),
        setv("latence", 0), setv("dernierEnvoye", ""), setv("dernierEnvoiT", 0), setv("dernierConstruction", ""),
        setv("longueurAvant", 0), setv("prochainRecord", 0),
        setv("_i", 1), repeter(C.NB_JOUEURS, [
            remplacer("E_paquet", V("_i"), 0), remplacer("E_actif", V("_i"), 0), remplacer("E_vu", V("_i"), 0),
            remplacer("E_battement", V("_i"), -100000), remplacer("E_nom", V("_i"), join("J", V("_i"))),
            remplacer("E_emoteFin", V("_i"), 0), remplacer("E_dernierBattement", V("_i"), 0),
            changev("_i", 1)]),
        appel("maintenant"), appel("coder nom"), appel("copier carte"),
        repeter_jusqua(eq(V("connecte"), 1), [appel("rejoindre"), si(eq(V("connecte"), 0), [attendre(5)])]),
        setv("message", ""),
        appel("lire record"),
        toujours([
            appel("maintenant"),
            setv("n2", 1), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(non(eq(V("k"), V("monSlot"))), [
                    appel("decoder", V("k")),
                    si(eq(item("E_actif", V("k")), 1), [changev("n2", 1)]),
                ]),
                changev("k", 1),
            ]),
            setv("👥 Joueurs", V("n2")),
            appel("envoyer", 0),
            appel("synchroniser construction"),
            si(gt(chrono(), V("prochainRecord")), [setv("prochainRecord", add(chrono(), 10)), appel("lire record")]),
        ]),
    ])


def tr_txt(fr, en):
    """Texte traduit pour les journaux (reporter)."""
    return C.tr(fr, en)


# ===========================================================================
#  JOUEUR
# ===========================================================================
def construire_joueur(P):
    J = Cible(P, "Joueur")
    J.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
    J.visible = False
    J.layer = C.CALQUES["Joueur"]
    for v in ["k", "dx", "dy", "f", "r", "meilleur", "meilleurDist", "meilleurR", "nx", "ny", "ok", "d", "n", "cx", "cy",
              "idx", "velY", "prochainTir", "prochaineConstruction", "prochainDegatZone", "prochaineRecolte",
              "dernierDegatsT", "sprint", "v", "cod", "q", "entree", "source", "arme", "a", "construireRelache",
              "editionDebut", "dernierX", "dernierY", "dernierT", "prochainLieu", "redeploiementProgres",
              "materiauRelache", "tirRelache", "slotPrecedent", "tolerance", "mx", "my", "pioches", "t", "c"]:
        J.var(v, 0)

    def notification(texte):
        return [ajouter_liste("Notifications", texte), ajouter_liste("NotificationsFin", add(chrono(), 4)),
                si(gt(long_liste("Notifications"), 4), [supprimer("Notifications", 1), supprimer("NotificationsFin", 1)])]

    def journal(texte):
        return [ajouter_liste("Journal", texte), ajouter_liste("JournalFin", add(chrono(), 8)),
                si(gt(long_liste("Journal"), 6), [supprimer("Journal", 1), supprimer("JournalFin", 1)])]

    def jouer_son(nom, volume=100):
        return [setv("son_pan", 0), setv("son_volume", volume), diffuser("son " + nom)]

    def tc(nom):
        return touche(C.touche_config(nom))

    def mat_var():
        """Nom de la variable du matériau actif (expression de choix)."""
        return None

    # --- cellules / déplacement -------------------------------------------------------
    J.proc("deplacer", [("dx", "n"), ("dy", "n")], [
        setv("nx", add(V("px"), A("dx"))),
        si(et(eq(C.cellule(add(V("nx"), 0.25), V("py")), 0), eq(C.cellule(sub(V("nx"), 0.25), V("py")), 0)),
           [setv("px", V("nx"))]),
        setv("ny", add(V("py"), A("dy"))),
        si(et(eq(C.cellule(V("px"), add(V("ny"), 0.25)), 0), eq(C.cellule(V("px"), sub(V("ny"), 0.25)), 0)),
           [setv("py", V("ny"))]),
    ])
    # case visée devant moi à distance d (cx, cy, idx)
    J.proc("case devant", [("d", "n")], [
        setv("cx", floor(add(V("px"), mul(cos(V("dir")), A("d"))))),
        setv("cy", floor(add(V("py"), mul(sin(V("dir")), A("d"))))),
        setv("idx", C.index_cellule(V("cx"), V("cy"))),
    ])

    # --- équipement -------------------------------------------------------------------------
    J.proc("equipement de depart", [], [
        remplacer("Inventaire", 1, 1), remplacer("Quantites", 1, C.ARMES[1][4]),
        si(eq(V("ltm"), 1), [remplacer("Inventaire", 1, 2), remplacer("Quantites", 1, C.ARMES[2][4])]),
        si(eq(V("ltm"), 2), [remplacer("Inventaire", 1, 3), remplacer("Quantites", 1, C.ARMES[3][4])]),
        remplacer("Inventaire", 2, 0), remplacer("Inventaire", 3, 0), remplacer("Inventaire", 4, 0), remplacer("Inventaire", 5, 0),
        remplacer("Quantites", 2, 0), remplacer("Quantites", 3, 0), remplacer("Quantites", 4, 0), remplacer("Quantites", 5, 0),
        setv("munitions_legeres", 24), setv("munitions_cartouches", 10), setv("munitions_lourdes", 3),
        setv("mat_bois", 0), setv("mat_pierre", 0), setv("mat_metal", 0), setv("materiauActif", 1),
        setv("slotActif", 1), setv("armeNum", item("Inventaire", 1)), setv("rechargeFin", 0), setv("utilisationFin", 0),
        setv("interactionType", 0), setv("reanime", 0), setv("surbouclier", 0), setv("endurance", 100),
    ])
    J.proc("choisir slot", [("s", "n")], [
        si(non(eq(V("slotActif"), A("s"))), [
            setv("rechargeFin", 0), setv("utilisationFin", 0), setv("utilisationObjet", 0),
        ]),
        setv("slotActif", A("s")), setv("armeNum", item("Inventaire", A("s"))),
        setv("pioches", 0),
    ])
    J.proc("mettre a jour affichage", [], [
        si(eq(V("pioches"), 1), [setv("armeNum", 8)], [setv("armeNum", item("Inventaire", V("slotActif")))]),
        si(gt(V("armeNum"), 0), [setv("🎯 Arme", item("ObjetNoms", V("armeNum")))], [setv("🎯 Arme", tr_txt("Mains nues", "Unarmed"))]),
        setv("🔫 Munitions", item("Quantites", V("slotActif"))),
        setv("🧱 Matériaux", add(V("mat_bois"), add(V("mat_pierre"), V("mat_metal")))),
    ])
    # ramasser un objet (code, quantité) : arme → case vide ou réserve de munitions ; consommable → empile
    J.proc("ramasser", [("code", "n"), ("quantite", "n")], [
        setv("ok", 0),
        si(lt(A("code"), 4), [
            # déjà équipé → munitions en réserve
            setv("k", 1),
            repeter(5, [si(eq(item("Inventaire", V("k")), A("code")), [setv("ok", 1)]), changev("k", 1)]),
            si(eq(V("ok"), 1), [
                si(eq(A("code"), 1), [changev("munitions_legeres", 24)]),
                si(eq(A("code"), 2), [changev("munitions_cartouches", 10)]),
                si(eq(A("code"), 3), [changev("munitions_lourdes", 5)]),
                notification(join("+ ", tr_txt("munitions", "ammo"))),
            ], [
                setv("k", 1), setv("n", 0),
                repeter(5, [si(et(eq(V("n"), 0), eq(item("Inventaire", V("k")), 0)), [setv("n", V("k"))]), changev("k", 1)]),
                si(eq(V("n"), 0), [setv("n", V("slotActif"))]),
                remplacer("Inventaire", V("n"), A("code")), remplacer("Quantites", V("n"), A("quantite")),
                notification(join("+ ", item("ObjetNoms", A("code")))),
            ]),
        ], [
            setv("k", 1),
            repeter(5, [
                si(et(eq(V("ok"), 0), eq(item("Inventaire", V("k")), A("code"))), [
                    setv("ok", 1),
                    remplacer("Quantites", V("k"), minimum(add(item("Quantites", V("k")), A("quantite")),
                                                          item("MaxConsommable", sub(A("code"), 3)))),
                ]),
                changev("k", 1),
            ]),
            si(eq(V("ok"), 0), [
                setv("k", 1), setv("n", 0),
                repeter(5, [si(et(eq(V("n"), 0), eq(item("Inventaire", V("k")), 0)), [setv("n", V("k"))]), changev("k", 1)]),
                si(eq(V("n"), 0), [setv("n", V("slotActif"))]),
                remplacer("Inventaire", V("n"), A("code")), remplacer("Quantites", V("n"), A("quantite")),
            ]),
            notification(joins("+", A("quantite"), " ", item("ObjetNoms", A("code")))),
        ]),
        appel("mettre a jour affichage"),
    ])
    # coffre n : butin déterministe (n, graine) + matériaux
    J.proc("ouvrir coffre", [("n", "n")], [
        ajouter_liste("CoffresPris", A("n")),
        setv("k", mod(add(mul(A("n"), 7), mul(V("graine"), 3)), 6)),
        si(eq(V("k"), 0), [appel("ramasser", 2, 5), changev("munitions_cartouches", 10)]),
        si(eq(V("k"), 1), [appel("ramasser", 3, 3), changev("munitions_lourdes", 6)]),
        si(eq(V("k"), 2), [appel("ramasser", 5, 1), appel("ramasser", 4, 5)]),
        si(eq(V("k"), 3), [appel("ramasser", 7, 1), appel("ramasser", 6, 3)]),
        si(eq(V("k"), 4), [changev("munitions_legeres", 24), appel("ramasser", 2, 5)]),
        si(eq(V("k"), 5), [appel("ramasser", 3, 3), appel("ramasser", 7, 1)]),
        si(eq(V("ltm"), 1), [appel("ramasser", 2, 5), changev("munitions_cartouches", 10)]),
        si(eq(V("ltm"), 2), [appel("ramasser", 3, 3), changev("munitions_lourdes", 6)]),
        setv("k", mod(add(A("n"), V("graine")), 3)),
        si(eq(V("k"), 0), [changev("mat_bois", 30)]), si(eq(V("k"), 1), [changev("mat_pierre", 30)]),
        si(eq(V("k"), 2), [changev("mat_metal", 30)]),
        changev("🛡 Bouclier", 0),
        changev("stat_coffres", 1), setv("evt_valeur", A("n")), diffuser("evt coffre"),
        setv("message", "coffre"), jouer_son("coffre"),
        appel("mettre a jour affichage"),
    ])

    # --- tir ---------------------------------------------------------------------------------
    J.proc("tirer", [], [
        si(non(eq(V("ltm"), 4)), [remplacer("Quantites", V("slotActif"), sub(item("Quantites", V("slotActif")), 1))]),
        setv("prochainTir", add(chrono(), item("ArmeCadence", V("armeNum")))),
        setv("tirAnim", 4), changev("stat_tirs", 1),
        setv("evt_valeur", V("armeNum")), diffuser("evt tir"),
        si(eq(V("armeNum"), 1), jouer_son("tir_pistolet")), si(eq(V("armeNum"), 2), jouer_son("tir_pompe")),
        si(eq(V("armeNum"), 3), jouer_son("tir_sniper")),
        setv("tolerance", item("ArmeTolerance", V("armeNum"))),
        si(eq(V("param_viseeAssistee"), 1), [setv("tolerance", mul(V("tolerance"), 1.3))]),
        setv("meilleur", 0), setv("meilleurDist", item("ArmePortee", V("armeNum"))),
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(et4(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), est_vivant_ou_aterre(V("k")),
                   non(meme_equipe(V("k")))), [
                setv("dx", sub(item("E_x", V("k")), V("px"))), setv("dy", sub(item("E_y", V("k")), V("py"))),
                setv("f", add(mul(V("dx"), cos(V("dir"))), mul(V("dy"), sin(V("dir"))))),
                setv("r", sub(mul(V("dx"), sin(V("dir"))), mul(V("dy"), cos(V("dir"))))),
                si(et4(gt(V("f"), 0.3), lt(V("f"), V("meilleurDist")), lt(absv(V("r")), V("tolerance")),
                       gt(item("Profondeur", rnd(div(V("colonnes"), 2))), sub(V("f"), 0.3))), [
                    setv("meilleur", V("k")), setv("meilleurDist", V("f")), setv("meilleurR", V("r")),
                ]),
            ]),
            changev("k", 1),
        ]),
        si(gt(V("meilleur"), 0), [
            setv("cible", V("meilleur")), setv("seq", mod(add(V("seq"), 1), 100)),
            setv("degats", item("ArmeDegats", V("armeNum"))),
            si(eq(V("armeNum"), 2), [
                setv("degats", rnd(mul(V("degats"), sub(1, div(V("meilleurDist"), 6))))),
                si(lt(V("degats"), 10), [setv("degats", 10)]),
            ]),
            setv("toucheFin", add(chrono(), 0.25)),
            changev("stat_touches", 1), changev("stat_degats", V("degats")),
            setv("evt_cible", V("meilleur")), setv("evt_valeur", V("degats")), diffuser("evt touche"),
            jouer_son("touche"),
            # chiffres de dégâts à l'écran : mmm xxxx yyyy eeeeee t
            setv("mx", rnd(add(mul(div(div(V("meilleurR"), V("meilleurDist")), V("plan")), 240), 2000))),
            setv("my", rnd(add(add(V("horizon"), hasard(-10, 20)), 2000))),
            si(lt(V("mx"), 1700), [setv("mx", 1700)]), si(gt(V("mx"), 2300), [setv("mx", 2300)]),
            setv("t", 0), si(gt(item("E_bouclier", V("meilleur")), 0), [setv("t", 1)]),
            ajouter_liste("DegatsAffiches", joins(C.rembourrer(V("degats"), 3), C.rembourrer(V("mx"), 4), C.rembourrer(V("my"), 4),
                                                  C.rembourrer(mul(add(chrono(), 1), 10), 6), V("t"))),
            si(gt(long_liste("DegatsAffiches"), 8), [supprimer("DegatsAffiches", 1)]),
        ]),
    ])
    J.proc("recharger", [], [
        setv("k", item("ArmeChargeur", V("armeNum"))),
        setv("q", 0),
        si(eq(V("armeNum"), 1), [setv("q", V("munitions_legeres"))]), si(eq(V("armeNum"), 2), [setv("q", V("munitions_cartouches"))]),
        si(eq(V("armeNum"), 3), [setv("q", V("munitions_lourdes"))]),
        si(et3(eq(V("rechargeFin"), 0), lt(item("Quantites", V("slotActif")), V("k")),
               ou(eq(V("ltm"), 4), gt(V("q"), 0))), [
            setv("rechargeDebut", chrono()), setv("rechargeFin", add(chrono(), item("ArmeRecharge", V("armeNum")))),
            setv("message", "recharge"), jouer_son("rechargement"),
        ]),
    ])
    J.proc("finir recharge", [], [
        setv("k", sub(item("ArmeChargeur", V("armeNum")), item("Quantites", V("slotActif")))),
        si(non(eq(V("ltm"), 4)), [
            si(eq(V("armeNum"), 1), [setv("k", minimum(V("k"), V("munitions_legeres"))), changev("munitions_legeres", mul(V("k"), -1))]),
            si(eq(V("armeNum"), 2), [setv("k", minimum(V("k"), V("munitions_cartouches"))), changev("munitions_cartouches", mul(V("k"), -1))]),
            si(eq(V("armeNum"), 3), [setv("k", minimum(V("k"), V("munitions_lourdes"))), changev("munitions_lourdes", mul(V("k"), -1))]),
        ]),
        remplacer("Quantites", V("slotActif"), add(item("Quantites", V("slotActif")), V("k"))),
        setv("rechargeFin", 0),
    ])

    # --- consommables -------------------------------------------------------------------------
    J.proc("commencer utilisation", [], [
        setv("cod", V("armeNum")),
        setv("ok", 1),
        si(ou(eq(V("cod"), 4), eq(V("cod"), 5)), [si(ge(V("❤ PV"), 100), [setv("ok", 0)])]),
        si(eq(V("cod"), 4), [si(ge(V("❤ PV"), 75), [setv("ok", 0)])]),
        si(ou(eq(V("cod"), 6), eq(V("cod"), 7)), [si(ge(V("🛡 Bouclier"), 100), [setv("ok", 0)])]),
        si(eq(V("cod"), 6), [si(ge(V("🛡 Bouclier"), 50), [setv("ok", 0)])]),
        si(et(eq(V("ok"), 1), gt(item("Quantites", V("slotActif")), 0)), [
            setv("utilisationObjet", V("cod")), setv("utilisationDebut", chrono()),
            setv("utilisationFin", add(chrono(), item("ConsoDuree", sub(V("cod"), 3)))),
        ]),
    ])
    J.proc("finir utilisation", [], [
        setv("cod", V("utilisationObjet")),
        si(eq(V("cod"), 4), [changev("❤ PV", 15), si(gt(V("❤ PV"), 75), [setv("❤ PV", 75)])]),
        si(eq(V("cod"), 5), [setv("❤ PV", 100)]),
        si(eq(V("cod"), 6), [changev("🛡 Bouclier", 25), si(gt(V("🛡 Bouclier"), 50), [setv("🛡 Bouclier", 50)])]),
        si(eq(V("cod"), 7), [changev("🛡 Bouclier", 50), si(gt(V("🛡 Bouclier"), 100), [setv("🛡 Bouclier", 100)])]),
        remplacer("Quantites", V("slotActif"), sub(item("Quantites", V("slotActif")), 1)),
        si(le(item("Quantites", V("slotActif")), 0), [remplacer("Inventaire", V("slotActif"), 0), remplacer("Quantites", V("slotActif"), 0)]),
        changev("stat_soins", 1), setv("evt_valeur", V("cod")), diffuser("evt soin"),
        si(lt(V("cod"), 6), jouer_son("soin"), jouer_son("bouclier")),
        setv("utilisationFin", 0), setv("utilisationObjet", 0),
        appel("mettre a jour affichage"),
    ])

    # --- pioche : récolte et destruction ------------------------------------------------------
    J.proc("coup de pioche", [], [
        setv("prochaineRecolte", add(chrono(), 0.45)), setv("tirAnim", 4),
        appel("case devant", 1.2),
        setv("c", item("Carte", V("idx"))),
        si(et4(gt(V("c"), 0), gt(V("cx"), 0), gt(V("cy"), 0), et(lt(V("cx"), C.TAILLE - 1), lt(V("cy"), C.TAILLE - 1))), [
            jouer_son("pioche"),
            si(eq(V("c"), 2), [changev("mat_bois", 10), setv("evt_valeur", 1)]),
            si(ou(eq(V("c"), 1), eq(V("c"), 3)), [changev("mat_pierre", 8), setv("evt_valeur", 2)]),
            si(eq(V("c"), 4), [changev("mat_metal", 6), setv("evt_valeur", 3)]),
            si(gt(V("mat_bois"), 500), [setv("mat_bois", 500)]), si(gt(V("mat_pierre"), 500), [setv("mat_pierre", 500)]),
            si(gt(V("mat_metal"), 500), [setv("mat_metal", 500)]),
            changev("stat_recoltes", 1), changev("stat_materiaux", 8), diffuser("evt recolte"),
            si(eq(V("murCible"), V("idx")), [changev("murCoups", 1)], [setv("murCible", V("idx")), setv("murCoups", 1)]),
            setv("k", 5),
            si(eq(V("c"), 2), [setv("k", 3)]), si(eq(V("c"), 4), [setv("k", 7)]),
            si(ge(V("murCoups"), V("k")), [
                remplacer("Carte", V("idx"), 0), setv("murCoups", 0), setv("murCible", 0),
                appel("publier entree", 0, V("cx"), V("cy")),
                notification(tr_txt("Mur détruit", "Wall destroyed")),
            ]),
        ]),
        appel("mettre a jour affichage"),
    ])
    # entrée de construction partagée : matériau(1) xx yy, ☁ Construction puis ☁ Construction2
    J.proc("publier entree", [("m", "n"), ("x", "n"), ("y", "n")], [
        setv("entree", joins(A("m"), C.rembourrer(A("x"), 2), C.rembourrer(A("y"), 2))),
        setv("a", V("☁ Construction")),
        si(ou(lt(longueur(V("a")), 1), eq(V("a"), 0)), [setv("a", "1")]),
        si(lt(longueur(V("a")), 246), [setv("☁ Construction", join(V("a"), V("entree")))], [
            setv("a", V("☁ Construction2")),
            si(ou(lt(longueur(V("a")), 1), eq(V("a"), 0)), [setv("a", "1")]),
            si(lt(longueur(V("a")), 246), [setv("☁ Construction2", join(V("a"), V("entree")))],
               notification(tr_txt("Limite de construction atteinte", "Build limit reached"))),
        ]),
    ])
    J.proc("construire", [], [
        setv("ok", 0),
        si(eq(V("materiauActif"), 1), [si(ge(V("mat_bois"), C.COUT_MUR), [setv("ok", 1)])]),
        si(eq(V("materiauActif"), 2), [si(ge(V("mat_pierre"), C.COUT_MUR), [setv("ok", 1)])]),
        si(eq(V("materiauActif"), 3), [si(ge(V("mat_metal"), C.COUT_MUR), [setv("ok", 1)])]),
        si(eq(V("ok"), 0), [notification(tr_txt("Pas assez de matériaux", "Not enough materials"))], [
            appel("case devant", 1.6),
            si(et4(eq(item("Carte", V("idx")), 0), non(et(eq(V("cx"), floor(V("px"))), eq(V("cy"), floor(V("py"))))),
                   et(gt(V("cx"), 0), lt(V("cx"), C.TAILLE - 1)), et(gt(V("cy"), 0), lt(V("cy"), C.TAILLE - 1))), [
                si(eq(V("materiauActif"), 1), [remplacer("Carte", V("idx"), C.MUR_PAR_MATERIAU[1]), changev("mat_bois", -C.COUT_MUR)]),
                si(eq(V("materiauActif"), 2), [remplacer("Carte", V("idx"), C.MUR_PAR_MATERIAU[2]), changev("mat_pierre", -C.COUT_MUR)]),
                si(eq(V("materiauActif"), 3), [remplacer("Carte", V("idx"), C.MUR_PAR_MATERIAU[3]), changev("mat_metal", -C.COUT_MUR)]),
                appel("publier entree", V("materiauActif"), V("cx"), V("cy")),
                changev("stat_murs", 1), setv("evt_valeur", V("materiauActif")), diffuser("evt mur"), jouer_son("construction"),
            ]),
        ]),
        appel("mettre a jour affichage"),
    ])
    J.proc("editer", [], [
        appel("case devant", 1.6),
        si(et4(gt(item("Carte", V("idx")), 0), eq(item("CarteBase", V("idx")), 0),
               et(gt(V("cx"), 0), lt(V("cx"), C.TAILLE - 1)), et(gt(V("cy"), 0), lt(V("cy"), C.TAILLE - 1))), [
            remplacer("Carte", V("idx"), 0), appel("publier entree", 0, V("cx"), V("cy")),
            jouer_son("construction"), notification(tr_txt("Mur retiré", "Wall removed")),
        ]),
    ])

    # --- interactions (touche « interagir ») ---------------------------------------------------
    J.proc("chercher interaction", [], [
        setv("interactionCible", 0), setv("n", 0),
        # coéquipier à terre à moins de 1,5 case → réanimation (5 s)
        si(gt(V("monEquipe"), 0), [
            setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et4(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_etat", V("k")), 3), meme_equipe(V("k"))), [
                    si(lt(add(absv(sub(item("E_x", V("k")), V("px"))), absv(sub(item("E_y", V("k")), V("py")))), 1.5), [
                        setv("n", 2), setv("interactionCible", V("k")), setv("interactionDuree", 5),
                    ]),
                ]),
                changev("k", 1),
            ]),
            # carte de redéploiement d'un coéquipier mort → ramassage immédiat
            si(eq(V("n"), 0), [
                setv("k", 1),
                repeter(C.NB_JOUEURS, [
                    si(et4(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_etat", V("k")), 2), meme_equipe(V("k"))), [
                        si(et(non(contient("CartesRamassees", V("k"))),
                              lt(add(absv(sub(item("E_x", V("k")), V("px"))), absv(sub(item("E_y", V("k")), V("py")))), 1.2)), [
                            ajouter_liste("CartesRamassees", V("k")),
                            notification(join(tr_txt("Carte de redéploiement : ", "Reboot card: "), item("E_nom", V("k")))),
                            jouer_son("notification"),
                        ]),
                    ]),
                    changev("k", 1),
                ]),
            ]),
            # balise + carte en poche → redéploiement (10 s)
            si(et(eq(V("n"), 0), gt(long_liste("CartesRamassees"), 0)), [
                setv("k", 1),
                repeter(C.NB_BALISES, [
                    si(lt(add(absv(sub(item("BalisesX", V("k")), V("px"))), absv(sub(item("BalisesY", V("k")), V("py")))), 1.4), [
                        setv("n", 3), setv("interactionCible", item("CartesRamassees", 1)), setv("interactionDuree", 10),
                    ]),
                    changev("k", 1),
                ]),
            ]),
        ]),
        # coffre à moins de 1,2 case (1,2 s)
        si(eq(V("n"), 0), [
            setv("k", 1),
            repeter(C.NB_COFFRES, [
                si(et(non(contient("CoffresPris", V("k"))),
                      lt(add(absv(sub(item("CoffresX", V("k")), V("px"))), absv(sub(item("CoffresY", V("k")), V("py")))), 1.2)), [
                    setv("n", 1), setv("interactionCible", V("k")), setv("interactionDuree", 1.2),
                ]),
                changev("k", 1),
            ]),
        ]),
        si(non(eq(V("n"), V("interactionType"))), [setv("interactionType", V("n")), setv("interactionDebut", chrono())]),
        si(eq(V("n"), 0), [setv("reanime", 0)]),
        si(ou(eq(V("n"), 2), eq(V("n"), 3)), [setv("reanime", V("interactionCible"))]),
        si(gt(V("n"), 0), [
            si(gt(sub(chrono(), V("interactionDebut")), V("interactionDuree")), [
                si(eq(V("n"), 1), [appel("ouvrir coffre", V("interactionCible"))]),
                si(eq(V("n"), 2), [changev("stat_reanimations", 1), setv("evt_cible", V("interactionCible")), diffuser("evt reanimation"),
                                   notification(tr_txt("Coéquipier réanimé", "Teammate revived")), jouer_son("reanimation")]),
                si(eq(V("n"), 3), [
                    setv("k", num_item("CartesRamassees", V("interactionCible"))),
                    si(gt(V("k"), 0), [supprimer("CartesRamassees", V("k"))]),
                    changev("stat_reanimations", 1), setv("evt_cible", V("interactionCible")), diffuser("evt reanimation"),
                    notification(tr_txt("Coéquipier redéployé", "Teammate rebooted")), jouer_son("reanimation"),
                ]),
                setv("interactionType", 0), setv("interactionDebut", chrono()),
            ]),
        ]),
    ])

    # --- dégâts, à terre, mort, réapparition ----------------------------------------------------
    J.proc("tomber a terre", [("source", "n")], [
        setv("etat", 3), setv("knockPar", A("source")), setv("pvAterre", 100), setv("aterreDepuis", chrono()),
        setv("❤ PV", 0), setv("reanimationProgres", 0), setv("utilisationFin", 0), setv("rechargeFin", 0),
        setv("message", "aterre"), diffuser("evt aterre"), jouer_son("aterre"),
    ])
    J.proc("mourir", [("source", "n")], [
        setv("etat", 2), setv("❤ PV", 0), setv("tueur", A("source")), setv("morts", mod(add(V("morts"), 1), 10)),
        setv("mortX", V("px")), setv("mortY", V("py")), setv("respawnT", add(chrono(), 5)), setv("redeploiementProgres", 0),
        setv("flash", add(chrono(), 0.6)), setv("utilisationFin", 0), setv("rechargeFin", 0), setv("interactionType", 0), setv("reanime", 0),
        changev("stat_morts", 1), setv("message", "elimine"), setv("evt_source", A("source")), diffuser("evt mort"),
        si(eq(A("source"), 0), journal(tr_txt("Tu es tombé dans la tempête", "You fell to the storm")),
           journal(join(item("E_nom", A("source")), tr_txt(" t'a éliminé", " eliminated you")))),
        jouer_son("defaite"),
    ])
    J.proc("coequipier vivant", [], [
        setv("ok", 0),
        si(gt(V("monEquipe"), 0), [
            setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et4(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), eq(item("E_etat", V("k")), 1), meme_equipe(V("k"))), [setv("ok", 1)]),
                changev("k", 1),
            ]),
        ]),
    ])
    J.proc("prendre degats", [("source", "n"), ("quantite", "n"), ("arme", "n")], [
        si(et(ou(eq(V("etat"), 1), eq(V("etat"), 3)), eq(V("invulnerable"), 0)), [
            setv("ok", 1),
            si(et(gt(A("source"), 0), meme_equipe(A("source"))), [setv("ok", 0)]),
            si(eq(V("ok"), 1), [
                setv("n", A("quantite")),
                setv("flash", add(chrono(), 0.35)), changev("stat_degatsRecus", V("n")), setv("dernierDegatsT", chrono()),
                setv("evt_source", A("source")), setv("evt_valeur", V("n")),
                si(gt(A("source"), 0), [
                    setv("dx", sub(item("E_x", A("source")), V("px"))), setv("dy", sub(item("E_y", A("source")), V("py"))),
                    si(lt(absv(V("dx")), 0.0001), [si(gt(V("dy"), 0), [setv("a", 90)], [setv("a", 270)])], [
                        setv("a", atan(div(V("dy"), V("dx")))), si(lt(V("dx"), 0), [changev("a", 180)]),
                    ]),
                    setv("evt_angle", mod(sub(V("dir"), V("a")), 360)),
                ], [setv("evt_angle", -1)]),
                diffuser("evt degats"), jouer_son("degats", 80),
                si(eq(V("etat"), 3), [
                    changev("pvAterre", mul(V("n"), -1)),
                    si(le(V("pvAterre"), 0), [appel("mourir", A("source"))]),
                ], [
                    # surbouclier puis bouclier puis PV (la tempête — source 0 — ignore les boucliers)
                    si(gt(A("source"), 0), [
                        setv("a", minimum(V("surbouclier"), V("n"))), changev("surbouclier", mul(V("a"), -1)), changev("n", mul(V("a"), -1)),
                        setv("a", minimum(V("🛡 Bouclier"), V("n"))), changev("🛡 Bouclier", mul(V("a"), -1)), changev("n", mul(V("a"), -1)),
                    ]),
                    changev("❤ PV", mul(V("n"), -1)),
                    si(le(V("❤ PV"), 0), [
                        appel("coequipier vivant"),
                        si(et(eq(V("ok"), 1), ou3(eq(V("mode"), 2), eq(V("mode"), 3), eq(V("mode"), 4))),
                           [appel("tomber a terre", A("source"))], [appel("mourir", A("source"))]),
                    ]),
                ]),
            ]),
        ]),
    ])
    J.proc("appliquer degats recus", [], [
        repeter(long_liste("DegatsRecus"), [
            setv("entree", item("DegatsRecus", 1)), supprimer("DegatsRecus", 1),
            si(ge(longueur(V("entree")), 5), [
                appel("prendre degats", lettre(1, V("entree")), mul(C.sous_chaine(V("entree"), 2, 3), 1), lettre(5, V("entree"))),
            ]),
        ]),
    ])
    J.proc("reapparaitre", [], [
        # point aléatoire dans la zone, en parachute (Partie gère la descente)
        setv("ok", 0),
        repeter(60, [
            si(eq(V("ok"), 0), [
                setv("nx", add(hasard(1, C.TAILLE - 2), 0.5)), setv("ny", add(hasard(1, C.TAILLE - 2), 0.5)),
                si(et(eq(C.cellule(V("nx"), V("ny")), 0),
                      lt(sqrt(add(mul(sub(V("nx"), V("zoneX")), sub(V("nx"), V("zoneX"))), mul(sub(V("ny"), V("zoneY")), sub(V("ny"), V("zoneY"))))),
                         sub(V("zoneR"), 0.5))), [setv("ok", 1)]),
            ]),
        ]),
        si(eq(V("ok"), 0), [setv("nx", V("zoneX")), setv("ny", V("zoneY"))]),
        setv("px", V("nx")), setv("py", V("ny")), setv("dir", hasard(0, 359)),
        setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("surbouclier", 0), setv("hauteur", 0), setv("velY", 0),
        appel("equipement de depart"),
        setv("etat", 7), setv("altitude", 40), setv("ecran", "parachute"), diffuser("evt changement ecran"),
    ])

    # --- tempête ----------------------------------------------------------------------------
    J.proc("tempete", [], [
        setv("d", sqrt(add(mul(sub(V("px"), V("zoneX")), sub(V("px"), V("zoneX"))), mul(sub(V("py"), V("zoneY")), sub(V("py"), V("zoneY")))))),
        si(gt(V("d"), V("zoneR")), [setv("horsZone", 1)], [setv("horsZone", 0)]),
        si(et4(eq(V("horsZone"), 1), ou(eq(V("etat"), 1), eq(V("etat"), 3)), eq(V("invulnerable"), 0), gt(chrono(), V("prochainDegatZone"))), [
            setv("prochainDegatZone", add(chrono(), 1)),
            appel("prendre degats", 0, V("zoneDegats"), 0),
        ]),
    ])

    # --- lieux nommés -----------------------------------------------------------------------
    J.proc("lieux", [], [
        setv("prochainLieu", add(chrono(), 0.5)), setv("n", 0), setv("k", 1),
        repeter(len(C.LIEUX), [
            si(lt(add(absv(sub(item("LieuxX", V("k")), V("px"))), absv(sub(item("LieuxY", V("k")), V("py")))), item("LieuxR", V("k"))), [setv("n", V("k"))]),
            changev("k", 1),
        ]),
        si(non(eq(V("n"), V("lieuActuel"))), [
            setv("lieuActuel", V("n")),
            si(gt(V("n"), 0), [
                notification(join("📍 ", item("LieuxNom", add(V("n"), mul(len(C.LIEUX), V("param_langue")))))),
                setv("evt_valeur", V("n")), diffuser("evt lieu"),
            ]),
        ]),
    ])

    # --- entrées ------------------------------------------------------------------------------
    def avance(signe):
        return appel("deplacer", mul(cos(V("dir")), mul(V("v"), signe)), mul(sin(V("dir")), mul(V("v"), signe)))

    def lateral(signe):   # vecteur droite = (sin, -cos)
        return appel("deplacer", mul(sin(V("dir")), mul(V("v"), 0.85 * signe)), mul(cos(V("dir")), mul(V("v"), -0.85 * signe)))

    J.proc("entrees", [], [
        # vitesse : sprint avec endurance ; immobile pendant un soin ; lent à terre
        setv("v", 0.07), setv("sprint", 0),
        si(et3(tc("sprint"), gt(V("endurance"), 0), eq(V("etat"), 1)), [setv("v", 0.105), setv("sprint", 1)]),
        si(eq(V("etat"), 3), [setv("v", 0.025)]),
        si(gt(V("utilisationFin"), chrono()), [setv("v", 0)]),
        si(gt(V("interactionType"), 0), [setv("v", 0)]),
        setv("dernierX", V("px")), setv("dernierY", V("py")),
        si(ou(tc("avancer"), touche("up arrow")), [avance(1)]),
        si(ou(tc("reculer"), touche("down arrow")), [avance(-1)]),
        si(tc("gauche"), [lateral(-1)]),
        si(tc("droite"), [lateral(1)]),
        changev("stat_distance", add(absv(sub(V("px"), V("dernierX"))), absv(sub(V("py"), V("dernierY"))))),
        si(et(eq(V("sprint"), 1), gt(add(absv(sub(V("px"), V("dernierX"))), absv(sub(V("py"), V("dernierY")))), 0)),
           [changev("endurance", -0.8)], [changev("endurance", 0.6)]),
        si(lt(V("endurance"), 0), [setv("endurance", 0)]), si(gt(V("endurance"), 100), [setv("endurance", 100)]),
        # rotation : flèches, souris vers les bords (sensibilité)
        si(touche("left arrow"), [changev("dir", mul(3, V("param_sensibilite")))]),
        si(touche("right arrow"), [changev("dir", mul(-3, V("param_sensibilite")))]),
        si(et3(eq(V("superposition"), ""), lt(absv(souris_x()), 241), lt(absv(souris_y()), 181)), [
            si(gt(souris_x(), 90), [changev("dir", mul(div(sub(90, souris_x()), 30), V("param_sensibilite")))]),
            si(lt(souris_x(), -90), [changev("dir", mul(div(sub(-90, souris_x()), 30), V("param_sensibilite")))]),
        ]),
        setv("dir", mod(V("dir"), 360)),
        # saut (gravité faible en LTM 5)
        si(et3(tc("sauter"), eq(V("hauteur"), 0), eq(V("etat"), 1)), [
            si(eq(V("ltm"), 5), [setv("velY", 13)], [setv("velY", 9)]), jouer_son("saut", 50),
        ]),
        # emplacements 1-5, pioche, matériau, viser
        si(touche("1"), [appel("choisir slot", 1)]), si(touche("2"), [appel("choisir slot", 2)]),
        si(touche("3"), [appel("choisir slot", 3)]), si(touche("4"), [appel("choisir slot", 4)]),
        si(touche("5"), [appel("choisir slot", 5)]),
        si(tc("pioche"), [setv("pioches", 1), setv("rechargeFin", 0), setv("utilisationFin", 0)]),
        si(tc("materiau"), [
            si(eq(V("materiauRelache"), 0), [setv("materiauActif", add(mod(V("materiauActif"), 3), 1)), setv("materiauRelache", 1),
                                         notification(join(tr_txt("Matériau : ", "Material: "), item("MateriauNoms", V("materiauActif"))))]),
        ], [setv("materiauRelache", 0)]),
        appel("mettre a jour affichage"),
        si(et(tc("viser"), eq(V("armeNum"), 3)), [setv("plan", 0.22)], [setv("plan", 0.66)]),
        # rechargement
        si(et(tc("recharger"), lt(V("armeNum"), 4)), [si(gt(V("armeNum"), 0), [appel("recharger")])]),
        si(et(gt(V("rechargeFin"), 0), gt(chrono(), V("rechargeFin"))), [appel("finir recharge")]),
        si(et(gt(V("utilisationFin"), 0), lt(V("utilisationFin"), chrono())), [appel("finir utilisation")]),
        # clic : tir / consommable / pioche / construction (mode construction)
        si(et4(souris_bas(), eq(V("superposition"), ""), lt(absv(souris_x()), 241), lt(absv(souris_y()), 181)), [
            si(eq(V("modeConstruction"), 1), [
                si(et(eq(V("construireRelache"), 0), gt(chrono(), V("prochaineConstruction"))), [
                    appel("construire"), setv("prochaineConstruction", add(chrono(), 0.25)),
                    si(eq(V("param_constructionTurbo"), 0), [setv("construireRelache", 1)]),
                ]),
            ], [
                si(eq(V("armeNum"), 8), [si(gt(chrono(), V("prochaineRecolte")), [appel("coup de pioche")])]),
                si(et3(gt(V("armeNum"), 0), lt(V("armeNum"), 4), ou(eq(V("etat"), 1), eq(V("etat"), 8))), [
                    setv("ok", 1),
                    si(et(eq(V("ltm"), 1), non(eq(V("armeNum"), 2))), [setv("ok", 0)]),
                    si(et(eq(V("ltm"), 2), non(eq(V("armeNum"), 3))), [setv("ok", 0)]),
                    si(et4(eq(V("ok"), 1), gt(chrono(), V("prochainTir")), eq(V("rechargeFin"), 0), et(eq(V("interactionType"), 0), lt(V("monEmoteFin"), chrono()))), [
                        si(ou(gt(item("Quantites", V("slotActif")), 0), eq(V("ltm"), 4)), [appel("tirer")], [appel("recharger")]),
                    ]),
                    si(et(eq(V("ok"), 0), eq(V("tirRelache"), 0)), [
                        notification(join(item("LTMNoms", add(V("ltm"), 1)), " !")), setv("tirRelache", 1),
                    ]),
                ]),
                si(et4(gt(V("armeNum"), 3), lt(V("armeNum"), 8), eq(V("utilisationFin"), 0), eq(V("etat"), 1)), [appel("commencer utilisation")]),
            ]),
        ], [setv("construireRelache", 0), setv("tirRelache", 0)]),
        # construction directe / mode construction, matériau, édition
        si(tc("construire"), [
            si(eq(V("param_constructionTurbo"), 1), [
                si(gt(chrono(), V("prochaineConstruction")), [appel("construire"), setv("prochaineConstruction", add(chrono(), 0.25))]),
            ], [
                si(eq(V("construireRelache"), 0), [appel("construire"), setv("construireRelache", 1)]),
            ]),
        ]),
        si(tc("edition"), [
            si(eq(V("param_editionRapide"), 1), [
                si(eq(V("editionDebut"), 0), [appel("editer"), setv("editionDebut", 1)]),
            ], [
                si(eq(V("editionDebut"), 0), [setv("editionDebut", chrono())]),
                si(gt(sub(chrono(), V("editionDebut")), 0.8), [appel("editer"), setv("editionDebut", add(chrono(), 9999))]),
            ]),
        ], [setv("editionDebut", 0)]),
        # interaction
        si(tc("interagir"), [appel("chercher interaction")], [
            si(gt(V("interactionType"), 0), [setv("interactionType", 0)]), setv("reanime", 0),
        ]),
    ])

    # --- état par image (hors entrées) ------------------------------------------------------------
    J.proc("physique", [], [
        # gravité du saut (pas en caméra libre : Social règle hauteur librement, vers le haut ou le bas)
        si(et(ou(gt(V("hauteur"), 0), gt(V("velY"), 0)), non(eq(V("ecran"), "cinema"))), [
            changev("hauteur", V("velY")),
            si(eq(V("ltm"), 5), [changev("velY", -0.4)], [changev("velY", -0.8)]),
            si(lt(V("hauteur"), 0), [setv("hauteur", 0), setv("velY", 0)]),
        ]),
        setv("horizon", mul(V("hauteur"), -1)),
        si(gt(V("tirAnim"), 0), [changev("tirAnim", -1)]),
        # surbouclier : +5/s après 6 s sans dégâts, max 50 (en combat seulement)
        si(et3(eq(V("etat"), 1), gt(sub(chrono(), V("dernierDegatsT")), 6), lt(V("surbouclier"), 50)), [
            si(ge(V("phase"), 2), [changev("surbouclier", 0.17), si(gt(V("surbouclier"), 50), [setv("surbouclier", 50)])]),
        ]),
        # à terre : saignement 40 s, réanimation par un coéquipier (4,5 s cumulées)
        si(eq(V("etat"), 3), [
            changev("pvAterre", -0.0833),
            si(le(V("pvAterre"), 0), [appel("mourir", V("knockPar"))], [
                setv("ok", 0), setv("k", 1),
                repeter(C.NB_JOUEURS, [
                    si(et3(eq(item("E_actif", V("k")), 1), meme_equipe(V("k")), eq(item("E_reanime", V("k")), V("monSlot"))), [setv("ok", 1)]),
                    changev("k", 1),
                ]),
                si(eq(V("ok"), 1), [changev("reanimationProgres", 0.0333)], [
                    changev("reanimationProgres", -0.01), si(lt(V("reanimationProgres"), 0), [setv("reanimationProgres", 0)]),
                ]),
                si(ge(V("reanimationProgres"), 4.5), [
                    setv("etat", 1), setv("❤ PV", 30), setv("reanimationProgres", 0), setv("message", "reanime"),
                    jouer_son("reanimation"),
                ]),
            ]),
        ]),
        # mort : réapparition (Rumble) ou redéploiement par un coéquipier (8 s cumulées)
        si(eq(V("etat"), 2), [
            si(et(eq(V("mode"), 5), gt(chrono(), V("respawnT"))), [si(lt(V("phase"), 8), [appel("reapparaitre")])]),
            si(ou3(eq(V("mode"), 2), eq(V("mode"), 3), eq(V("mode"), 4)), [
                setv("ok", 0), setv("k", 1), setv("n", 0),
                repeter(C.NB_JOUEURS, [
                    si(et3(eq(item("E_actif", V("k")), 1), meme_equipe(V("k")), eq(item("E_reanime", V("k")), V("monSlot"))), [setv("ok", 1), setv("n", V("k"))]),
                    changev("k", 1),
                ]),
                si(eq(V("ok"), 1), [changev("redeploiementProgres", 0.0333)]),
                si(ge(V("redeploiementProgres"), 8), [
                    setv("redeploiementProgres", 0), setv("redeploiement", 1),
                    setv("px", item("E_x", V("n"))), setv("py", item("E_y", V("n"))),
                    setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("surbouclier", 0), appel("equipement de depart"),
                    setv("etat", 7), setv("altitude", 60), setv("ecran", "parachute"), diffuser("evt changement ecran"),
                    setv("message", "redeploiement"), jouer_son("reanimation"),
                ]),
            ]),
        ]),
        # temps de survie
        si(et3(eq(V("etat"), 1), ge(V("phase"), 2), gt(chrono(), V("dernierT"))), [setv("dernierT", add(chrono(), 1)), changev("stat_tempsSurvie", 1)]),
    ])

    J.proc("initialiser", [], [
        setv("etat", 5), setv("ecran", "connexion"), setv("onglet", "accueil"), setv("superposition", ""),
        setv("px", C.TAILLE / 2 + 0.5), setv("py", C.TAILLE / 2 + 0.5), setv("dir", 0), setv("hauteur", 0), setv("horizon", 0), setv("plan", 0.66),
        setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("surbouclier", 0), setv("endurance", 100), setv("invulnerable", 0), setv("altitude", 0),
        setv("monEquipe", 0), setv("mode", 5), setv("ltm", 0), setv("horsZone", 0), setv("zoneX", C.TAILLE / 2), setv("zoneY", C.TAILLE / 2),
        setv("zoneR", C.RAYON_INITIAL), setv("zoneDegats", 1), setv("phase", 0), setv("flash", 0), setv("tirAnim", 0), setv("toucheFin", 0),
        setv("message", ""), setv("cible", 0), setv("seq", 0), setv("degats", 0), setv("tueur", 0), setv("morts", 0), setv("knockPar", 0),
        setv("reanime", 0), setv("mortX", 0), setv("mortY", 0), setv("redeploiement", 0), setv("modeConstruction", 0),
        setv("💀 Éliminations", 0), setv("lieuActuel", 0), setv("rechargeFin", 0), setv("utilisationFin", 0), setv("interactionType", 0),
        setv("murCoups", 0), setv("murCible", 0), setv("reanimationProgres", 0),
        setv("velY", 0), setv("respawnT", 0), setv("prochainTir", 0), setv("prochaineConstruction", 0), setv("prochainDegatZone", 0),
        setv("prochaineRecolte", 0), setv("dernierDegatsT", 0), setv("construireRelache", 0), setv("editionDebut", 0), setv("dernierT", 0),
        setv("prochainLieu", 0), setv("redeploiementProgres", 0), setv("materiauRelache", 0), setv("tirRelache", 0), setv("pioches", 0),
        vider("CoffresPris"), vider("CartesRamassees"), vider("DegatsRecus"), vider("Journal"), vider("JournalFin"),
        vider("Notifications"), vider("NotificationsFin"), vider("DegatsAffiches"), vider("Bruits"), vider("Chat"), vider("ChatFin"),
        vider("Pings"), vider("Sprays"),
        appel("equipement de depart"), appel("mettre a jour affichage"),
    ])

    J.script(quand_drapeau(), [
        cacher(), appel("initialiser"),
        diffuser("demarrer"),
        toujours([
            si(eq(V("connecte"), 1), [
                si(et(ecran_jouable(), ou3(eq(V("etat"), 1), eq(V("etat"), 3), eq(V("etat"), 8))), [appel("entrees")], [
                    setv("interactionType", 0), setv("reanime", 0), setv("plan", 0.66),
                ]),
                appel("appliquer degats recus"),
                appel("physique"),
                appel("tempete"),
                si(gt(chrono(), V("prochainLieu")), [appel("lieux")]),
            ]),
        ]),
    ])
    # nouvelle manche : remise à zéro de l'état de partie (Partie place les joueurs)
    J.script(quand_message("evt nouvelle manche"), [
        setv("💀 Éliminations", 0), setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("surbouclier", 0), setv("endurance", 100),
        setv("hauteur", 0), setv("velY", 0), setv("knockPar", 0), setv("reanime", 0), setv("redeploiement", 0), setv("horsZone", 0),
        setv("murCoups", 0), setv("murCible", 0), setv("reanimationProgres", 0), setv("redeploiementProgres", 0), setv("lieuActuel", 0),
        vider("CoffresPris"), vider("CartesRamassees"), vider("DegatsRecus"), vider("DegatsAffiches"), vider("Bruits"), vider("Pings"), vider("Sprays"),
        appel("equipement de depart"), appel("mettre a jour affichage"),
    ])
    # décollage du bus : l'équipement de la pré-partie est remis à zéro
    J.script(quand_message("evt phase"), [
        si(eq(V("evt_valeur"), 1), [appel("equipement de depart"), setv("❤ PV", 100), setv("🛡 Bouclier", 0), setv("surbouclier", 0)]),
    ])

