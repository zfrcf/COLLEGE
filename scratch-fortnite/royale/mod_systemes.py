# -*- coding: utf-8 -*-
"""
Sprite « Systemes » : PROGRESSION ET MÉTA façon Fortnite (calque CALQUES["Systemes"]).

Aucun dessin d'écran (Menus affiche) : ce sprite calcule, remplit les listes du contrat et
diffuse des événements. Il possède : xp, niveau, xpNiveau, xpSuivant, jetons, hype, division,
passeNiveau, etoiles, saison, chapitre, joursSaison, bonusXP, xpGagne, skin, pioche, planeur,
spray, banniere, styleSkin, codeSauvegarde, codeCreateur, et les listes QueteTitres,
QuetesActives, Succes, PasseRecompenses, Possedes, Boutique, EmotesEquipees, RecapLignes.

DIFFUSIONS ÉCOUTÉES
  evt elimination (+50 XP), evt knock (+25), evt reanimation (+40), evt coffre (+10), evt mur (+2),
  evt recolte (+1 ; murs + récolte plafonnés à 100 XP par manche), evt lieu (+5, première visite
  du lieu dans la manche, seulement en écran « jeu » et vivant ou à terre), evt fin manche (evt_valeur = rang : placement 300/150/50 + survie/10,
  Arène : hype, record proposé, fin du bonus de session), evt victoire (+200), evt nouvelle manche,
  boutique acheter (evt_valeur = index 1-6), casier equiper (evt_texte = type, evt_valeur = id,
  evt_cible = case 1-6 pour les émotes), quete reclamer / quete partager (evt_valeur = position
  dans QuetesActives), sauvegarde generer, sauvegarde charger (lit reponse()), createur definir
  (evt_texte).
  Le multiplicateur bonusXP (+50 %) s'applique pendant la première manche de la session.

DIFFUSIONS ÉMISES (différées d'une image et relayées par les diffusions privées « sys relais » puis
« sys relais emettre », une par image, evt_valeur réglée juste avant : la valeur est ainsi écrite APRÈS
les gestionnaires des diffusions émises dans la même image par les autres sprites — voir la boucle)
  evt niveau (niveau), evt quete (index de la quête), evt succes (index du succès),
  evt achat (index de la boutique), record proposer, son niveau / son coffre / son notification /
  son clic, et les notifications (listes Notifications/NotificationsFin).

LISTES GLOBALES PRIVÉES (lecture seule pour les autres modules)
  sys_SuccesTitres, sys_SuccesDescriptions : 21 titres/descriptions FR puis EN
      (index i + 21 × param_langue).
  sys_DivisionNoms : 7 noms FR puis 7 EN (index division + 7 × param_langue).
  sys_SkinNoms (10+10), sys_PiocheNoms (9+9), sys_PlaneurNoms (9+9), sys_BanniereNoms (10+10).
  sys_debug (variable) : 1 → le sprite efface l'écran et écrit ses données (débogage).

FORMATS
  QueteTitres      : 32 titres FR puis 32 EN (12 quotidiennes, 10 hebdomadaires, 10 d'histoire).
  QuetesActives    : "index|type|progression|objectif|etat|xp" — positions 1-3 quotidiennes
                     (graine = jour), 4-8 hebdomadaires (graine = semaine), 9-11 histoire.
  Succes           : 21 entrées "index|etat".
  PasseRecompenses : 100 entrées "type|id" (type : skin, pioche, planeur, spray, emote, banniere,
                     jetons, style).
  Possedes         : "type|id". Boutique : 6 entrées "type|id|prix".
  codeSauvegarde (76 chiffres) : version(2 = "01") xp(7) jetons(5) hype(5) victoires(4)
      elims(6) parties(5) coffres(5) succes(7 : masque binaire des 21 succès, bit i-1 = succès i)
      possedes(20 : chaque chiffre code 3 cosmétiques du CATALOGUE dans l'ordre, valeur
      b1 + 2·b2 + 4·b3) skin(2) pioche(1) planeur(1) spray(1) banniere(2) style(1)
      controle(2 = somme des 74 chiffres précédents mod 97).
"""
import datetime

from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as SV
from . import texte

V = Var
A = Arg
ORDRE = 40

# ---------------------------------------------------------------------------
#  Données statiques
# ---------------------------------------------------------------------------
SAISON_DEBUT = (datetime.date(2026, 1, 1) - datetime.date(2000, 1, 1)).days   # 9497
DUREE_SAISON = 70
NIVEAU_MAX = 200
XP_PAR_NIVEAU = 1000
LONGUEUR_CODE = 76

# Statistiques suivies (code → variable). 1-16 : statistiques de session ; 17+ : internes.
STATS = ["stat_elims", "stat_degats", "stat_coffres", "stat_murs", "stat_recoltes", "stat_distance",
         "stat_tempsSurvie", "stat_parties", "stat_top3", "stat_victoires", "stat_reanimations", "stat_soins",
         "stat_pings", "stat_emotes", "stat_materiaux", "stat_touches"]
STATS_INTERNES = {17: "totElims", 18: "totVictoires", 19: "totCoffres", 20: "totParties", 21: "niveau",
                  22: "lieuxTotal"}
CODE_STAT = {nom: i + 1 for i, nom in enumerate(STATS)}

# Quêtes : (titre FR, titre EN, statistique, objectif, XP, jetons)
QUOTIDIENNES = [
    ("Élimine 3 adversaires", "Eliminate 3 opponents", "stat_elims", 3, 300, 50),
    ("Inflige 500 points de dégâts", "Deal 500 damage", "stat_degats", 500, 300, 50),
    ("Ouvre 5 coffres", "Open 5 chests", "stat_coffres", 5, 250, 50),
    ("Construis 20 murs", "Build 20 walls", "stat_murs", 20, 250, 50),
    ("Récolte des matériaux 50 fois", "Harvest materials 50 times", "stat_recoltes", 50, 250, 50),
    ("Parcours 300 m", "Travel 300 m", "stat_distance", 300, 200, 50),
    ("Survis 5 minutes au total", "Survive 5 minutes in total", "stat_tempsSurvie", 300, 300, 50),
    ("Joue 3 parties", "Play 3 matches", "stat_parties", 3, 300, 50),
    ("Termine dans le top 3", "Finish in the top 3", "stat_top3", 1, 400, 100),
    ("Réanime un coéquipier", "Revive a teammate", "stat_reanimations", 1, 300, 50),
    ("Utilise 3 objets de soin", "Use 3 healing items", "stat_soins", 3, 200, 50),
    ("Pose 5 marqueurs", "Place 5 markers", "stat_pings", 5, 200, 50),
]
HEBDOMADAIRES = [
    ("Élimine 15 adversaires", "Eliminate 15 opponents", "stat_elims", 15, 1000, 200),
    ("Inflige 3000 points de dégâts", "Deal 3000 damage", "stat_degats", 3000, 1000, 200),
    ("Ouvre 20 coffres", "Open 20 chests", "stat_coffres", 20, 800, 150),
    ("Construis 100 murs", "Build 100 walls", "stat_murs", 100, 800, 150),
    ("Récolte 1000 matériaux", "Harvest 1000 materials", "stat_materiaux", 1000, 800, 150),
    ("Parcours 2000 m", "Travel 2000 m", "stat_distance", 2000, 800, 150),
    ("Survis 30 minutes au total", "Survive 30 minutes in total", "stat_tempsSurvie", 1800, 1000, 200),
    ("Joue 15 parties", "Play 15 matches", "stat_parties", 15, 1000, 200),
    ("Remporte une partie", "Win a match", "stat_victoires", 1, 1500, 300),
    ("Touche 100 tirs", "Land 100 shots", "stat_touches", 100, 800, 150),
]
HISTOIRE = [
    ("Atterris et ouvre ton premier coffre", "Land and open your first chest", "stat_coffres", 1, 500, 100),
    ("Récolte 100 matériaux", "Harvest 100 materials", "stat_materiaux", 100, 500, 100),
    ("Construis 10 murs", "Build 10 walls", "stat_murs", 10, 500, 100),
    ("Inflige 200 points de dégâts", "Deal 200 damage", "stat_degats", 200, 500, 100),
    ("Élimine ton premier adversaire", "Eliminate your first opponent", "stat_elims", 1, 800, 150),
    ("Utilise une émote", "Use an emote", "stat_emotes", 1, 300, 100),
    ("Pose un marqueur pour ton équipe", "Place a marker for your team", "stat_pings", 1, 300, 100),
    ("Survis 3 minutes au total", "Survive 3 minutes in total", "stat_tempsSurvie", 180, 800, 150),
    ("Termine dans le top 3", "Finish in the top 3", "stat_top3", 1, 1000, 200),
    ("Remporte une Victoire Royale", "Claim a Victory Royale", "stat_victoires", 1, 2000, 500),
]
QUETES = [(q, 1) for q in QUOTIDIENNES] + [(q, 2) for q in HEBDOMADAIRES] + [(q, 3) for q in HISTOIRE]
NB_QUETES = len(QUETES)                     # 32
PREMIERE_HISTOIRE = len(QUOTIDIENNES) + len(HEBDOMADAIRES) + 1   # 23
NB_QUOT, NB_HEBDO, NB_HIST = len(QUOTIDIENNES), len(HEBDOMADAIRES), len(HISTOIRE)
PAS_JOUR = [1, 5, 7, 11]                    # premiers avec 12 → 3 quotidiennes distinctes
PAS_SEMAINE = [1, 3, 7, 9]                  # premiers avec 10 → 5 hebdomadaires distinctes

# Succès : (titre FR, titre EN, description FR, description EN, code de statistique, seuil)
SUCCES = [
    ("Première victime", "First blood", "Élimine ton premier adversaire", "Eliminate your first opponent", 17, 1),
    ("Chasseur", "Hunter", "Élimine 10 adversaires", "Eliminate 10 opponents", 17, 10),
    ("Prédateur", "Predator", "Élimine 50 adversaires", "Eliminate 50 opponents", 17, 50),
    ("Victoire Royale", "Victory Royale", "Remporte ta première partie", "Win your first match", 18, 1),
    ("Champion", "Champion", "Remporte 5 parties", "Win 5 matches", 18, 5),
    ("Pilleur", "Looter", "Ouvre 10 coffres", "Open 10 chests", 19, 10),
    ("Bâtisseur", "Builder", "Construis 100 murs", "Build 100 walls", CODE_STAT["stat_murs"], 100),
    ("Bûcheron", "Lumberjack", "Récolte 1000 matériaux", "Harvest 1000 materials", CODE_STAT["stat_materiaux"], 1000),
    ("Médecin", "Medic", "Réanime 5 coéquipiers", "Revive 5 teammates", CODE_STAT["stat_reanimations"], 5),
    ("Podium", "Podium", "Termine dans le top 3", "Finish in the top 3", CODE_STAT["stat_top3"], 1),
    ("Habitué", "Regular", "Joue 10 parties", "Play 10 matches", 20, 10),
    ("Marathonien", "Marathoner", "Parcours 500 m", "Travel 500 m", CODE_STAT["stat_distance"], 500),
    ("Éclaireur", "Scout", "Pose 10 marqueurs", "Place 10 markers", CODE_STAT["stat_pings"], 10),
    ("Danseur", "Dancer", "Utilise 10 émotes", "Use 10 emotes", CODE_STAT["stat_emotes"], 10),
    ("Infirmier", "Nurse", "Utilise 10 objets de soin", "Use 10 healing items", CODE_STAT["stat_soins"], 10),
    ("Niveau 10", "Level 10", "Atteins le niveau 10", "Reach level 10", 21, 10),
    ("Niveau 25", "Level 25", "Atteins le niveau 25", "Reach level 25", 21, 25),
    ("Niveau 50", "Level 50", "Atteins le niveau 50", "Reach level 50", 21, 50),
    ("Artilleur", "Gunner", "Inflige 5000 points de dégâts", "Deal 5000 damage", CODE_STAT["stat_degats"], 5000),
    ("Tireur d'élite", "Sharpshooter", "Touche 50 tirs", "Land 50 shots", CODE_STAT["stat_touches"], 50),
    ("Explorateur", "Explorer", "Découvre 20 lieux (toutes manches)", "Discover 20 places (all matches)", 22, 20),
]
NB_SUCCES = len(SUCCES)                     # 21 (masque < 2^21 = 2097152, 7 chiffres)

DIVISIONS = [("Bronze", "Bronze", 0), ("Argent", "Silver", 500), ("Or", "Gold", 1000), ("Platine", "Platinum", 1500),
             ("Diamant", "Diamond", 2000), ("Champion", "Champion", 2500), ("Irréel", "Unreal", 3000)]

# Cosmétiques : catalogue à ordre FIXE (60 entrées → 20 chiffres octaux du code de sauvegarde)
NB_SKINS, NB_PIOCHES, NB_PLANEURS, NB_SPRAYS, NB_EMOTES, NB_BANNIERES, NB_STYLES = 10, 9, 9, 6, 6, 10, 10
CATALOGUE = ([("skin", i) for i in range(1, NB_SKINS + 1)] + [("pioche", i) for i in range(1, NB_PIOCHES + 1)]
             + [("planeur", i) for i in range(1, NB_PLANEURS + 1)] + [("spray", i) for i in range(1, NB_SPRAYS + 1)]
             + [("emote", i) for i in range(1, NB_EMOTES + 1)] + [("banniere", i) for i in range(1, NB_BANNIERES + 1)]
             + [("style", i) for i in range(1, NB_STYLES + 1)])
assert len(CATALOGUE) == 60
POSSEDES_DEFAUT = [("skin", 1), ("pioche", 1), ("planeur", 1), ("spray", 1), ("banniere", 1)] + [("emote", i) for i in range(1, 7)]

NOMS_SKINS = [("Recrue", "Recruit"), ("Ranger", "Ranger"), ("Ombre", "Shadow"), ("Néon", "Neon"), ("Chevalier", "Knight"),
              ("Pirate", "Pirate"), ("Astronaute", "Astronaut"), ("Ninja", "Ninja"), ("Robot", "Robot"), ("Légende", "Legend")]
NOMS_PIOCHES = [("Pioche de base", "Basic pickaxe"), ("Hache", "Axe"), ("Marteau", "Hammer"), ("Faux", "Scythe"),
                ("Clé géante", "Giant wrench"), ("Katana", "Katana"), ("Guitare", "Guitar"), ("Pelle dorée", "Golden shovel"),
                ("Sceptre", "Scepter")]
NOMS_PLANEURS = [("Parapluie", "Umbrella"), ("Deltaplane", "Hang glider"), ("Dragon", "Dragon"), ("Fusée", "Rocket"),
                 ("Ballon", "Balloon"), ("Parachute militaire", "Military chute"), ("Aile de chauve-souris", "Bat wing"),
                 ("Tapis volant", "Flying carpet"), ("OVNI", "UFO")]
NOMS_BANNIERES = [("Étoile", "Star"), ("Lama", "Llama"), ("Éclair", "Lightning"), ("Crâne", "Skull"), ("Cœur", "Heart"),
                  ("Flamme", "Flame"), ("Couronne", "Crown"), ("Bouclier", "Shield"), ("Diamant", "Diamond"), ("Trophée", "Trophy")]


def _construire_passe():
    """100 paliers « type|id » déterministes : skins 2-10 aux paliers 1, 8, 16, 24, 32, 36, 48, 56, 64 ; styles aux
    paliers 10, 20, …, 100 ; pioches, planeurs, sprays, bannières, émotes répartis ; le reste en jetons."""
    passe = [None] * 101
    for k, palier in enumerate([1, 8, 16, 24, 32, 36, 48, 56, 64]):   # 36 au lieu de 40 (palier de style)
        passe[palier] = ("skin", k + 2)
    for k, skin in enumerate([2, 3, 4, 5, 6, 7, 8, 9, 10, 1]):
        passe[10 * (k + 1)] = ("style", skin)
    autres = [("pioche", 2), ("planeur", 2), ("spray", 2), ("banniere", 2), ("emote", 1),
              ("pioche", 3), ("planeur", 3), ("spray", 3), ("banniere", 3), ("emote", 2),
              ("pioche", 4), ("planeur", 4), ("spray", 4), ("banniere", 4), ("emote", 3),
              ("pioche", 5), ("planeur", 5), ("banniere", 5), ("emote", 4), ("banniere", 6), ("emote", 5), ("emote", 6)]
    libres = [p for p in range(1, 101) if passe[p] is None]
    positions = [libres[int((j + 0.5) * len(libres) / len(autres))] for j in range(len(autres))]
    assert len(set(positions)) == len(autres)
    for p, a in zip(positions, autres):
        passe[p] = a
    for p in range(1, 101):
        if passe[p] is None:
            passe[p] = ("jetons", 100)
    return passe[1:]


PASSE = _construire_passe()
assert len(PASSE) == 100
_DANS_PASSE = set(PASSE)
# Boutique : cosmétiques hors passe, hors défauts, hors styles/émotes
POOL_BOUTIQUE = [c for c in CATALOGUE if c not in _DANS_PASSE and c not in POSSEDES_DEFAUT and c[0] not in ("style", "emote")]
NB_POOL = len(POOL_BOUTIQUE)                # 14
assert NB_POOL == 14, POOL_BOUTIQUE
PAS_BOUTIQUE = [1, 3, 5, 9, 11, 13]         # premiers avec 14 → 6 objets distincts


def cle(type_, ident):
    return "%s|%d" % (type_, ident)


# ---------------------------------------------------------------------------
#  Construction du sprite
# ---------------------------------------------------------------------------
def construire(P):
    S = Cible(P, "Systemes")
    S.costumes = [P.costume("vide", SV.svg_vide(), 2, 2)]
    S.visible = False
    S.layer = C.CALQUES["Systemes"]
    texte.installer(S)

    tr = C.tr

    # --- globales privées (lues par Menus) ------------------------------------------------
    P.stage.var("sys_debug", 0)
    P.stage.liste("sys_SuccesTitres", [s[0] for s in SUCCES] + [s[1] for s in SUCCES])
    P.stage.liste("sys_SuccesDescriptions", [s[2] for s in SUCCES] + [s[3] for s in SUCCES])
    P.stage.liste("sys_DivisionNoms", [d[0] for d in DIVISIONS] + [d[1] for d in DIVISIONS])
    P.stage.liste("sys_SkinNoms", [n[0] for n in NOMS_SKINS] + [n[1] for n in NOMS_SKINS])
    P.stage.liste("sys_PiocheNoms", [n[0] for n in NOMS_PIOCHES] + [n[1] for n in NOMS_PIOCHES])
    P.stage.liste("sys_PlaneurNoms", [n[0] for n in NOMS_PLANEURS] + [n[1] for n in NOMS_PLANEURS])
    P.stage.liste("sys_BanniereNoms", [n[0] for n in NOMS_BANNIERES] + [n[1] for n in NOMS_BANNIERES])

    # --- variables et listes locales ----------------------------------------------------------
    for v in ["i", "j", "k", "n", "c", "d", "pos", "idx", "pas", "prix", "entree", "code", "somme", "masque", "p2",
              "montant", "nomT", "nomC", "valStat", "ok", "palier", "champ1", "champ2", "champ3", "champ4", "champ5",
              "champ6", "nbChamps", "rangFin", "jour", "saisonGlobale", "jourCourant", "semaineCourante", "histProchaine",
              "passeDernier", "codeSale", "prochainTick", "prochainDebug", "mancheElims", "xpMursRecolte", "lieuxTotal",
              "victoireComptee", "survieDebut", "totElims", "totVictoires", "totCoffres", "totParties", "nbDebloques", "posR", "idxR",
              "prochainCode", "gainJetons"]:
        S.var(v, 0)
    S.var("messageAttente", "")
    S.liste("catalogue", [cle(t, i) for t, i in CATALOGUE])
    S.liste("boutiquePool", [cle(t, i) for t, i in POOL_BOUTIQUE])
    S.liste("boutiquePas", PAS_BOUTIQUE)
    S.liste("pasJour", PAS_JOUR)
    S.liste("pasSemaine", PAS_SEMAINE)
    S.liste("qType", [t for _, t in QUETES])
    S.liste("qStat", [CODE_STAT[q[2]] for q, _ in QUETES])
    S.liste("qObjectif", [q[3] for q, _ in QUETES])
    S.liste("qXp", [q[4] for q, _ in QUETES])
    S.liste("qJetons", [q[5] for q, _ in QUETES])
    S.liste("sStat", [s[4] for s in SUCCES])
    S.liste("sSeuil", [s[5] for s in SUCCES])
    for l in ["qaIndex", "qaDebut", "qaProg", "qaEtat", "sEtat", "recapTypes", "recapNb", "recapXp", "lieuxVisites",
              "evtCode", "evtVal"]:
        S.liste(l, [])

    # --- aides Python ---------------------------------------------------------------------------
    def notif(txt):
        return [ajouter_liste("Notifications", txt), ajouter_liste("NotificationsFin", add(chrono(), 4)),
                si(gt(long_liste("Notifications"), 4), [supprimer("Notifications", 1), supprimer("NotificationsFin", 1)])]

    def jouer_son(nom, vol=100):
        return [setv("son_pan", 0), setv("son_volume", vol), diffuser("son " + nom)]

    def emettre(code_evt, valeur):
        """Événement différé (émis par la boucle principale, un par image)."""
        return [ajouter_liste("evtCode", code_evt), ajouter_liste("evtVal", valeur)]

    def champ(valeur, chiffres):
        """Entier borné à [0, 10^chiffres − 1] sur `chiffres` positions."""
        return C.rembourrer(rnd(minimum(maximum(valeur, 0), 10 ** chiffres - 1)), chiffres)

    def titre_quete(idx):
        return item("QueteTitres", add(idx, mul(NB_QUETES, V("param_langue"))))

    def nom_division(div_):
        return item("sys_DivisionNoms", add(div_, mul(len(DIVISIONS), V("param_langue"))))

    def sale():
        return [setv("codeSale", 1), setv("menu_sale", 1)]

    # --- découpage « a|b|c » → champ1..champ6 ------------------------------------------------------
    S.proc("decouper", [("texte", "s")], [
        setv("champ1", ""), setv("champ2", ""), setv("champ3", ""), setv("champ4", ""), setv("champ5", ""), setv("champ6", ""),
        setv("nbChamps", 1), setv("i", 1),
        repeter(longueur(A("texte")), [
            setv("c", lettre(V("i"), A("texte"))),
            si(eq(V("c"), "|"), [changev("nbChamps", 1)], [
                si(eq(V("nbChamps"), 1), [setv("champ1", join(V("champ1"), V("c")))]),
                si(eq(V("nbChamps"), 2), [setv("champ2", join(V("champ2"), V("c")))]),
                si(eq(V("nbChamps"), 3), [setv("champ3", join(V("champ3"), V("c")))]),
                si(eq(V("nbChamps"), 4), [setv("champ4", join(V("champ4"), V("c")))]),
                si(eq(V("nbChamps"), 5), [setv("champ5", join(V("champ5"), V("c")))]),
                si(eq(V("nbChamps"), 6), [setv("champ6", join(V("champ6"), V("c")))]),
            ]),
            changev("i", 1),
        ]),
    ])

    # --- lecture d'une statistique par code --------------------------------------------------------
    S.proc("lire stat", [("code", "n")],
           [si(eq(A("code"), i + 1), [setv("valStat", V(nom))]) for i, nom in enumerate(STATS)]
           + [si(eq(A("code"), k), [setv("valStat", V(nom))]) for k, nom in STATS_INTERNES.items()])

    # --- noms traduits ------------------------------------------------------------------------------
    NOMS_TYPES = [("Éliminations", "Eliminations"), ("Adversaires à terre", "Knockdowns"), ("Réanimations", "Revives"),
                  ("Coffres", "Chests"), ("Constructions", "Builds"), ("Récolte", "Harvesting"),
                  ("Lieux découverts", "Places discovered"), ("Placement", "Placement"), ("Survie", "Survival"),
                  ("Victoire Royale", "Victory Royale"), ("Quêtes", "Quests")]
    S.proc("nom type", [("type", "n")],
           [si(eq(A("type"), i + 1), [setv("nomT", tr(fr, en))]) for i, (fr, en) in enumerate(NOMS_TYPES)])
    S.proc("nom cosmetique", [("type", "s"), ("id", "n")], [
        setv("nomC", join(A("type"), join(" ", A("id")))),
        si(eq(A("type"), "skin"), [setv("nomC", item("sys_SkinNoms", add(A("id"), mul(NB_SKINS, V("param_langue")))))]),
        si(eq(A("type"), "pioche"), [setv("nomC", item("sys_PiocheNoms", add(A("id"), mul(NB_PIOCHES, V("param_langue")))))]),
        si(eq(A("type"), "planeur"), [setv("nomC", item("sys_PlaneurNoms", add(A("id"), mul(NB_PLANEURS, V("param_langue")))))]),
        si(eq(A("type"), "banniere"), [setv("nomC", item("sys_BanniereNoms", add(A("id"), mul(NB_BANNIERES, V("param_langue")))))]),
        si(eq(A("type"), "spray"), [setv("nomC", join("Spray ", item("SprayNoms", A("id"))))]),
        si(eq(A("type"), "emote"), [setv("nomC", join(tr("Émote ", "Emote "), item("Emotes", add(A("id"), mul(len(C.EMOTES), V("param_langue"))))))]),
        si(eq(A("type"), "style"), [setv("nomC", join(tr("Style : ", "Style: "), item("sys_SkinNoms", add(A("id"), mul(NB_SKINS, V("param_langue"))))))]),
        si(eq(A("type"), "jetons"), [setv("nomC", join(A("id"), tr(" jetons", " coins")))]),
    ])

    # --- récapitulatif de fin de partie (regroupé par type) ------------------------------------------
    S.proc("recap", [("type", "n"), ("montant", "n")], [
        setv("pos", num_item("recapTypes", A("type"))),
        si(eq(V("pos"), 0), [
            ajouter_liste("recapTypes", A("type")), ajouter_liste("recapNb", 1), ajouter_liste("recapXp", A("montant")),
            ajouter_liste("RecapLignes", ""), setv("pos", long_liste("recapTypes")),
        ], [
            remplacer("recapNb", V("pos"), add(item("recapNb", V("pos")), 1)),
            remplacer("recapXp", V("pos"), add(item("recapXp", V("pos")), A("montant"))),
        ]),
        appel("nom type", A("type")),
        si(ou(lt(A("type"), 8), eq(A("type"), 11)), [
            remplacer("RecapLignes", V("pos"), joins(V("nomT"), " ×", item("recapNb", V("pos")), " : +", item("recapXp", V("pos")), " XP")),
        ], [
            remplacer("RecapLignes", V("pos"), joins(V("nomT"), " : +", item("recapXp", V("pos")), " XP")),
        ]),
    ])

    # --- passe de combat : déblocage des paliers passeDernier+1 .. passeNiveau --------------------------
    S.proc("debloquer passe", [("silencieux", "n")], [
        si(gt(V("passeNiveau"), V("passeDernier")), [
            setv("palier", V("passeDernier")),
            repeter(sub(V("passeNiveau"), V("passeDernier")), [
                changev("palier", 1),
                appel("decouper", item("PasseRecompenses", V("palier"))),
                si(eq(V("champ1"), "jetons"), [
                    si(eq(A("silencieux"), 0), [changev("jetons", V("champ2"))]),
                ], [
                    setv("entree", join(V("champ1"), join("|", V("champ2")))),
                    si(non(contient("Possedes", V("entree"))), [ajouter_liste("Possedes", V("entree"))]),
                ]),
                si(eq(A("silencieux"), 0), [
                    appel("nom cosmetique", V("champ1"), V("champ2")),
                    notif(joins(tr("Passe de combat — palier ", "Battle pass — tier "), V("palier"), " : ", V("nomC"))),
                ]),
            ]),
        ]),
        setv("passeDernier", V("passeNiveau")),
    ])

    # --- niveau à partir de l'XP ------------------------------------------------------------------------
    S.proc("recalculer niveau", [("silencieux", "n")], [
        si(lt(V("xp"), 0), [setv("xp", 0)]),
        setv("n", add(1, floor(div(V("xp"), XP_PAR_NIVEAU)))),
        si(gt(V("n"), NIVEAU_MAX), [setv("n", NIVEAU_MAX)]),
        setv("xpNiveau", mod(V("xp"), XP_PAR_NIVEAU)), setv("xpSuivant", XP_PAR_NIVEAU),
        si(et(gt(V("n"), V("niveau")), eq(A("silencieux"), 0)), [
            setv("gainJetons", mul(100, sub(V("n"), V("niveau")))),
            changev("jetons", V("gainJetons")),
            setv("niveau", V("n")),
            emettre(1, V("niveau")),
            setv("messageAttente", "niveau"), jouer_son("niveau"),
            notif(joins(tr("Niveau ", "Level "), V("niveau"), tr(" atteint ! +", " reached! +"), V("gainJetons"), tr(" jetons", " coins"))),
            appel("verifier succes"),
        ]),
        setv("niveau", V("n")),
        setv("passeNiveau", minimum(100, V("niveau"))),
        setv("etoiles", floor(div(V("xpNiveau"), 200))),
        appel("debloquer passe", A("silencieux")),
    ])

    # --- gain d'XP (avec bonus de session) ---------------------------------------------------------------
    S.proc("gagner xp", [("quantite", "n"), ("type", "n")], [
        setv("montant", rnd(A("quantite"))),
        si(eq(V("bonusXP"), 1), [setv("montant", rnd(mul(A("quantite"), 1.5)))]),
        si(gt(V("montant"), 0), [
            changev("xp", V("montant")),
            si(gt(V("xp"), 9999999), [setv("xp", 9999999)]),
            changev("xpGagne", V("montant")),
            appel("recap", A("type"), V("montant")),
            appel("recalculer niveau", 0),
            sale(),
        ]),
    ])

    # --- quêtes ---------------------------------------------------------------------------------------------
    S.proc("ecrire quete", [("pos", "n")], [
        setv("idx", item("qaIndex", A("pos"))),
        remplacer("QuetesActives", A("pos"), joins(V("idx"), "|", item("qType", V("idx")), "|", item("qaProg", A("pos")), "|",
                                                  item("qObjectif", V("idx")), "|", item("qaEtat", A("pos")), "|", item("qXp", V("idx")))),
    ])
    S.proc("placer quete", [("pos", "n"), ("index", "n")], [
        repeter_jusqua(ge(long_liste("qaIndex"), A("pos")), [
            ajouter_liste("qaIndex", 0), ajouter_liste("qaDebut", 0), ajouter_liste("qaProg", 0), ajouter_liste("qaEtat", 0),
            ajouter_liste("QuetesActives", ""),
        ]),
        remplacer("qaIndex", A("pos"), A("index")),
        appel("lire stat", item("qStat", A("index"))),
        remplacer("qaDebut", A("pos"), V("valStat")),
        remplacer("qaProg", A("pos"), 0), remplacer("qaEtat", A("pos"), 0),
        appel("ecrire quete", A("pos")),
    ])
    S.proc("activer quotidiennes", [], [
        setv("pas", item("pasJour", add(mod(V("jourCourant"), len(PAS_JOUR)), 1))), setv("i", 0),
        repeter(3, [
            appel("placer quete", add(V("i"), 1), add(mod(add(V("jourCourant"), mul(V("i"), V("pas"))), NB_QUOT), 1)),
            changev("i", 1),
        ]),
    ])
    S.proc("activer hebdomadaires", [], [
        setv("pas", item("pasSemaine", add(mod(V("semaineCourante"), len(PAS_SEMAINE)), 1))), setv("i", 0),
        repeter(5, [
            appel("placer quete", add(V("i"), 4), add(NB_QUOT, add(mod(add(V("semaineCourante"), mul(V("i"), V("pas"))), NB_HEBDO), 1))),
            changev("i", 1),
        ]),
    ])
    S.proc("activer histoire", [], [
        setv("i", 0),
        repeter(3, [
            si(le(V("histProchaine"), NB_QUETES), [appel("placer quete", add(V("i"), 9), V("histProchaine")), changev("histProchaine", 1)]),
            changev("i", 1),
        ]),
    ])
    S.proc("mettre a jour quetes", [], [
        setv("pos", 0),
        repeter(long_liste("qaIndex"), [
            changev("pos", 1),
            si(eq(item("qaEtat", V("pos")), 0), [
                setv("idx", item("qaIndex", V("pos"))),
                appel("lire stat", item("qStat", V("idx"))),
                setv("n", sub(V("valStat"), item("qaDebut", V("pos")))),
                si(lt(V("n"), 0), [setv("n", 0)]),
                si(gt(V("n"), item("qObjectif", V("idx"))), [setv("n", item("qObjectif", V("idx")))]),
                setv("n", floor(V("n"))),
                si(non(eq(V("n"), item("qaProg", V("pos")))), [
                    remplacer("qaProg", V("pos"), V("n")),
                    si(ge(V("n"), item("qObjectif", V("idx"))), [
                        remplacer("qaEtat", V("pos"), 1),
                        emettre(2, V("idx")),
                        setv("messageAttente", "quete"), jouer_son("notification"),
                        notif(join(tr("Quête terminée : ", "Quest complete: "), titre_quete(V("idx")))),
                    ]),
                    appel("ecrire quete", V("pos")), setv("menu_sale", 1),
                ]),
            ]),
        ]),
    ])

    # --- succès ----------------------------------------------------------------------------------------------
    S.proc("ecrire succes", [], [
        vider("Succes"), setv("i", 1),
        repeter(NB_SUCCES, [ajouter_liste("Succes", join(V("i"), join("|", item("sEtat", V("i"))))), changev("i", 1)]),
    ])
    S.proc("debloquer succes", [("i", "n")], [
        remplacer("sEtat", A("i"), 1), remplacer("Succes", A("i"), join(A("i"), "|1")),
        changev("jetons", 50),
        emettre(3, A("i")),
        notif(join(tr("Succès débloqué : ", "Achievement unlocked: "),
                   item("sys_SuccesTitres", add(A("i"), mul(NB_SUCCES, V("param_langue")))))),
        jouer_son("notification"), sale(),
    ])
    S.proc("verifier succes", [], [
        setv("j", 0),
        repeter(NB_SUCCES, [
            changev("j", 1),
            si(eq(item("sEtat", V("j")), 0), [
                appel("lire stat", item("sStat", V("j"))),
                si(ge(V("valStat"), item("sSeuil", V("j"))), [appel("debloquer succes", V("j"))]),
            ]),
        ]),
    ])
    S.proc("masque succes", [], [
        setv("masque", 0), setv("p2", 1), setv("i", 1),
        repeter(NB_SUCCES, [si(eq(item("sEtat", V("i")), 1), [changev("masque", V("p2"))]), setv("p2", mul(V("p2"), 2)), changev("i", 1)]),
    ])

    # --- boutique du jour ---------------------------------------------------------------------------------------
    S.proc("construire boutique", [], [
        vider("Boutique"),
        setv("pas", item("boutiquePas", add(mod(V("jourCourant"), len(PAS_BOUTIQUE)), 1))), setv("i", 0),
        repeter(6, [
            setv("k", add(mod(add(V("jourCourant"), mul(V("i"), V("pas"))), NB_POOL), 1)),
            setv("prix", add(200, mul(mod(add(mul(V("jourCourant"), 31), mul(V("k"), 97)), 14), 100))),
            ajouter_liste("Boutique", joins(item("boutiquePool", V("k")), "|", V("prix"))),
            changev("i", 1),
        ]),
    ])

    # --- possessions par défaut et équipement valide --------------------------------------------------------------
    S.proc("assurer possedes", [], [
        si(non(contient("Possedes", cle(t, i))), [ajouter_liste("Possedes", cle(t, i))]) for t, i in POSSEDES_DEFAUT
    ])
    S.proc("valider equipement", [], [
        si(non(contient("Possedes", join("skin|", V("skin")))), [setv("skin", 1)]),
        si(non(contient("Possedes", join("pioche|", V("pioche")))), [setv("pioche", 1)]),
        si(non(contient("Possedes", join("planeur|", V("planeur")))), [setv("planeur", 1)]),
        si(non(contient("Possedes", join("spray|", V("spray")))), [setv("spray", 1)]),
        si(non(contient("Possedes", join("banniere|", V("banniere")))), [setv("banniere", 1)]),
        si(non(contient("Possedes", join("style|", V("skin")))), [setv("styleSkin", 0)]),
        si(non(eq(V("styleSkin"), 1)), [setv("styleSkin", 0)]),
        repeter_jusqua(ge(long_liste("EmotesEquipees"), 6), [ajouter_liste("EmotesEquipees", 1)]),
    ])

    # --- casier --------------------------------------------------------------------------------------------------
    S.proc("equiper", [("type", "s"), ("id", "n"), ("case", "n")], [
        setv("ok", 0),
        si(eq(A("type"), "style"), [
            si(eq(A("id"), 0), [setv("styleSkin", 0), setv("ok", 1)], [
                # Menus peut avoir basculé styleSkin avant de demander : on tranche ici
                si(contient("Possedes", join("style|", V("skin"))), [setv("styleSkin", 1), setv("ok", 1)], [setv("styleSkin", 0)]),
            ]),
        ], [
            si(contient("Possedes", join(A("type"), join("|", A("id")))), [
                setv("ok", 1),
                si(eq(A("type"), "skin"), [si(non(eq(V("skin"), A("id"))), [setv("styleSkin", 0)]), setv("skin", A("id"))]),
                si(eq(A("type"), "pioche"), [setv("pioche", A("id"))]),
                si(eq(A("type"), "planeur"), [setv("planeur", A("id"))]),
                si(eq(A("type"), "spray"), [setv("spray", A("id"))]),
                si(eq(A("type"), "banniere"), [setv("banniere", A("id"))]),
                si(eq(A("type"), "emote"), [
                    si(et(ge(A("case"), 1), le(A("case"), 6)), [remplacer("EmotesEquipees", A("case"), A("id"))], [setv("ok", 0)]),
                ]),
            ]),
        ]),
        si(eq(V("ok"), 1), [notif(tr("Équipé !", "Equipped!")), jouer_son("clic"), sale()],
           [notif(tr("Non possédé", "Not owned"))]),
    ])

    # --- division (Arène) --------------------------------------------------------------------------------------------
    S.proc("mettre a jour division", [("silencieux", "n")], [
        setv("n", 1),
    ] + [si(ge(V("hype"), seuil), [setv("n", k + 1)]) for k, (_, _, seuil) in enumerate(DIVISIONS) if seuil > 0] + [
        si(non(eq(V("n"), V("division"))), [
            setv("division", V("n")),
            si(eq(A("silencieux"), 0), [notif(join(tr("Division : ", "Division: "), nom_division(V("division")))), jouer_son("niveau")]),
        ]),
    ])

    # --- saisons et changement de jour --------------------------------------------------------------------------------
    S.proc("mettre a jour saison", [], [
        setv("jour", floor(jours2000())),
        setv("n", sub(V("jour"), SAISON_DEBUT)),
        si(lt(V("n"), 0), [setv("n", 0)]),
        setv("saisonGlobale", add(1, floor(div(V("n"), DUREE_SAISON)))),
        setv("chapitre", add(1, floor(div(sub(V("saisonGlobale"), 1), 4)))),
        setv("saison", add(1, mod(sub(V("saisonGlobale"), 1), 4))),
        setv("joursSaison", sub(DUREE_SAISON, mod(V("n"), DUREE_SAISON))),
        si(non(eq(V("jour"), V("jourCourant"))), [
            setv("jourCourant", V("jour")), appel("construire boutique"), appel("activer quotidiennes"),
            si(non(eq(floor(div(V("jour"), 7)), V("semaineCourante"))), [
                setv("semaineCourante", floor(div(V("jour"), 7))), appel("activer hebdomadaires"),
            ]),
            setv("menu_sale", 1),
        ]),
    ])

    # --- code de sauvegarde -----------------------------------------------------------------------------------------------
    S.proc("generer code", [], [
        appel("masque succes"),
        setv("code", "01"),
        setv("code", join(V("code"), champ(V("xp"), 7))),
        setv("code", join(V("code"), champ(V("jetons"), 5))),
        setv("code", join(V("code"), champ(V("hype"), 5))),
        setv("code", join(V("code"), champ(V("totVictoires"), 4))),
        setv("code", join(V("code"), champ(V("totElims"), 6))),
        setv("code", join(V("code"), champ(V("totParties"), 5))),
        setv("code", join(V("code"), champ(V("totCoffres"), 5))),
        setv("code", join(V("code"), champ(V("masque"), 7))),
        setv("i", 0),
        repeter(20, [
            setv("d", 0),
            si(contient("Possedes", item("catalogue", add(mul(V("i"), 3), 1))), [changev("d", 1)]),
            si(contient("Possedes", item("catalogue", add(mul(V("i"), 3), 2))), [changev("d", 2)]),
            si(contient("Possedes", item("catalogue", add(mul(V("i"), 3), 3))), [changev("d", 4)]),
            setv("code", join(V("code"), V("d"))),
            changev("i", 1),
        ]),
        setv("code", join(V("code"), champ(V("skin"), 2))),
        setv("code", join(V("code"), champ(V("pioche"), 1))),
        setv("code", join(V("code"), champ(V("planeur"), 1))),
        setv("code", join(V("code"), champ(V("spray"), 1))),
        setv("code", join(V("code"), champ(V("banniere"), 2))),
        setv("code", join(V("code"), champ(V("styleSkin"), 1))),
        setv("somme", 0), setv("i", 1),
        repeter(longueur(V("code")), [changev("somme", lettre(V("i"), V("code"))), changev("i", 1)]),
        setv("code", join(V("code"), champ(mod(V("somme"), 97), 2))),
        setv("codeSauvegarde", V("code")),
    ])
    S.proc("charger code", [("brut", "s")], [
        # ne garder que les chiffres (espaces, tirets… ignorés)
        setv("code", ""), setv("i", 1),
        repeter(longueur(A("brut")), [
            setv("c", lettre(V("i"), A("brut"))),
            si(contient_texte("0123456789", V("c")), [setv("code", join(V("code"), V("c")))]),
            changev("i", 1),
        ]),
        setv("ok", 0),
        si(eq(longueur(V("code")), LONGUEUR_CODE), [
            setv("somme", 0), setv("i", 1),
            repeter(LONGUEUR_CODE - 2, [changev("somme", lettre(V("i"), V("code"))), changev("i", 1)]),
            si(et(eq(mod(V("somme"), 97), mul(C.sous_chaine(V("code"), 75, 2), 1)),
                  eq(mul(C.sous_chaine(V("code"), 1, 2), 1), 1)), [setv("ok", 1)]),
        ]),
        si(eq(V("ok"), 1), [
            setv("xp", mul(C.sous_chaine(V("code"), 3, 7), 1)),
            setv("jetons", mul(C.sous_chaine(V("code"), 10, 5), 1)),
            setv("hype", mul(C.sous_chaine(V("code"), 15, 5), 1)),
            setv("totVictoires", mul(C.sous_chaine(V("code"), 20, 4), 1)),
            setv("totElims", mul(C.sous_chaine(V("code"), 24, 6), 1)),
            setv("totParties", mul(C.sous_chaine(V("code"), 30, 5), 1)),
            setv("totCoffres", mul(C.sous_chaine(V("code"), 35, 5), 1)),
            setv("masque", mul(C.sous_chaine(V("code"), 40, 7), 1)),
            setv("i", 1),
            repeter(NB_SUCCES, [
                si(eq(mod(V("masque"), 2), 1), [remplacer("sEtat", V("i"), 1)], [remplacer("sEtat", V("i"), 0)]),
                setv("masque", floor(div(V("masque"), 2))),
                changev("i", 1),
            ]),
            appel("ecrire succes"),
            vider("Possedes"), setv("i", 0),
            repeter(20, [
                setv("d", mul(lettre(add(47, V("i")), V("code")), 1)),
                si(eq(mod(V("d"), 2), 1), [ajouter_liste("Possedes", item("catalogue", add(mul(V("i"), 3), 1)))]),
                si(eq(mod(floor(div(V("d"), 2)), 2), 1), [ajouter_liste("Possedes", item("catalogue", add(mul(V("i"), 3), 2)))]),
                si(ge(V("d"), 4), [ajouter_liste("Possedes", item("catalogue", add(mul(V("i"), 3), 3)))]),
                changev("i", 1),
            ]),
            appel("assurer possedes"),
            setv("skin", mul(C.sous_chaine(V("code"), 67, 2), 1)),
            setv("pioche", mul(lettre(69, V("code")), 1)),
            setv("planeur", mul(lettre(70, V("code")), 1)),
            setv("spray", mul(lettre(71, V("code")), 1)),
            setv("banniere", mul(C.sous_chaine(V("code"), 72, 2), 1)),
            setv("styleSkin", mul(lettre(74, V("code")), 1)),
            appel("valider equipement"),
            setv("passeDernier", 0),
            appel("recalculer niveau", 1),
            appel("mettre a jour division", 1),
            appel("generer code"), setv("codeSale", 0), setv("menu_sale", 1),
            notif(tr("Sauvegarde chargée", "Save loaded")), jouer_son("notification"),
        ], [notif(tr("Code invalide", "Invalid code"))]),
    ])

    # --- victoire / fin de manche --------------------------------------------------------------------------------------------
    S.proc("victoire", [], [
        setv("victoireComptee", 1), changev("totVictoires", 1),
        appel("gagner xp", 200, 10),
    ])
    S.proc("fin manche", [("rang", "n")], [
        changev("totParties", 1),
        si(eq(A("rang"), 1), [setv("n", 300)], [si(et(gt(A("rang"), 0), le(A("rang"), 3)), [setv("n", 150)], [setv("n", 50)])]),
        appel("gagner xp", V("n"), 8),
        setv("n", rnd(div(sub(V("stat_tempsSurvie"), V("survieDebut")), 10))),
        si(gt(V("n"), 0), [appel("gagner xp", V("n"), 9)]),
        si(et(eq(A("rang"), 1), eq(V("victoireComptee"), 0)), [appel("victoire")]),
        si(eq(V("mode"), 6), [
            setv("n", 10),
            si(eq(A("rang"), 3), [setv("n", 40)]), si(eq(A("rang"), 2), [setv("n", 60)]), si(eq(A("rang"), 1), [setv("n", 100)]),
            changev("hype", add(V("n"), mul(20, V("mancheElims")))),
            si(gt(V("hype"), 99999), [setv("hype", 99999)]),
            appel("mettre a jour division", 0),
        ]),
        setv("rec_elims", V("totElims")), setv("rec_victoires", V("totVictoires")), diffuser("record proposer"),
        setv("bonusXP", 0),
        appel("mettre a jour quetes"), appel("verifier succes"),
        sale(),
    ])

    # --- affichage de débogage (sys_debug = 1) --------------------------------------------------------------------------------
    def ecrire(txt, x, y, taille_px, couleur, align=0):
        return appel("ecrire", txt, x, y, taille_px, couleur, align)

    S.proc("afficher debug", [], [
        effacer(),
        ecrire(tr("SYSTÈMES — débogage", "SYSTEMS — debug"), -232, 158, 14, "jaune"),
        ecrire(joins(tr("Niveau ", "Level "), V("niveau"), "   XP ", V("xp"), " (", V("xpNiveau"), "/", V("xpSuivant"), ")   ",
                     tr("Jetons ", "Coins "), V("jetons")), -232, 139, 12, "blanc"),
        ecrire(joins("Hype ", V("hype"), "   ", tr("Division ", "Division "), nom_division(V("division")), "   ",
                     tr("Passe ", "Pass "), V("passeNiveau"), " ★", V("etoiles")), -232, 123, 12, "blanc"),
        ecrire(joins(tr("Saison ", "Season "), V("saison"), tr(" Chapitre ", " Chapter "), V("chapitre"), " (", V("joursSaison"),
                     tr(" j restants)   Bonus XP ", " d left)   XP bonus "), V("bonusXP"), tr("   XP manche ", "   Match XP "), V("xpGagne")),
               -232, 107, 12, "blanc"),
        setv("nbDebloques", 0), setv("i", 1),
        repeter(NB_SUCCES, [si(eq(item("sEtat", V("i")), 1), [changev("nbDebloques", 1)]), changev("i", 1)]),
        ecrire(joins(tr("Possédés ", "Owned "), long_liste("Possedes"), "/60   ", tr("Succès ", "Achievements "), V("nbDebloques"), "/", NB_SUCCES,
                     "   ", tr("Boutique : ", "Shop: "), item("Boutique", 1), "  ", item("Boutique", 2)), -232, 91, 11, "gris"),
        ecrire(tr("Quêtes actives (index|type|prog|obj|état|xp)", "Active quests (index|type|prog|obj|state|xp)"), -232, 74, 11, "cyan"),
        setv("pos", 0),
        repeter(long_liste("qaIndex"), [
            changev("pos", 1),
            setv("idx", item("qaIndex", V("pos"))),
            appel("ecrire tronque", joins(V("pos"), ". ", titre_quete(V("idx")), "  ", item("QuetesActives", V("pos"))),
                  -232, sub(60, mul(V("pos"), 13)), 10, "blanc", 0, 318),
        ]),
        ecrire(tr("Récap :", "Recap:"), 92, 74, 11, "cyan"),
        setv("i", 0),
        repeter(long_liste("RecapLignes"), [
            changev("i", 1),
            appel("ecrire tronque", item("RecapLignes", V("i")), 92, sub(60, mul(V("i"), 13)), 10, "or", 0, 146),
        ]),
        ecrire(joins("Skin ", V("skin"), " style ", V("styleSkin"), "  ", tr("Pioche ", "Pickaxe "), V("pioche"), "  ", tr("Planeur ", "Glider "), V("planeur"),
                     "  Spray ", V("spray"), "  ", tr("Bannière ", "Banner "), V("banniere"), "  ", tr("Créateur : ", "Creator: "), V("codeCreateur")),
               -232, -118, 10, "gris"),
        ecrire(C.sous_chaine(V("codeSauvegarde"), 1, 38), -232, -140, 11, "vert"),
        ecrire(C.sous_chaine(V("codeSauvegarde"), 39, 38), -232, -156, 11, "vert"),
        ecrire(join(tr("Notification : ", "Notification: "), item("Notifications", long_liste("Notifications"))), -232, -172, 10, "orange"),
    ])

    # --- initialisation (drapeau vert) --------------------------------------------------------------------------------------------
    S.proc("initialiser systemes", [], [
        setv("bonusXP", 1), setv("xpGagne", 0), vider("RecapLignes"), vider("recapTypes"), vider("recapNb"), vider("recapXp"),
        setv("mancheElims", 0), setv("xpMursRecolte", 0), vider("lieuxVisites"), setv("lieuxTotal", 0), setv("victoireComptee", 0),
        setv("survieDebut", V("stat_tempsSurvie")), setv("prochainTick", 0), setv("prochainDebug", 0), setv("prochainCode", 0),
        setv("messageAttente", ""), vider("evtCode"), vider("evtVal"),
        # listes statiques du contrat
        vider("QueteTitres"),
    ] + [ajouter_liste("QueteTitres", q[0]) for q, _ in QUETES] + [ajouter_liste("QueteTitres", q[1]) for q, _ in QUETES] + [
        vider("PasseRecompenses"),
    ] + [ajouter_liste("PasseRecompenses", cle(t, i)) for t, i in PASSE] + [
        # succès (états locaux conservés d'un drapeau à l'autre dans la même session)
        si(non(eq(long_liste("sEtat"), NB_SUCCES)), [vider("sEtat"), repeter(NB_SUCCES, [ajouter_liste("sEtat", 0)])]),
        appel("ecrire succes"),
        appel("assurer possedes"),
        setv("passeDernier", 0),
        appel("recalculer niveau", 1),
        appel("valider equipement"),
        appel("mettre a jour division", 1),
        # jour / semaine, boutique, quêtes
        setv("jourCourant", floor(jours2000())), setv("semaineCourante", floor(div(V("jourCourant"), 7))),
        appel("construire boutique"),
        vider("qaIndex"), vider("qaDebut"), vider("qaProg"), vider("qaEtat"), vider("QuetesActives"), setv("histProchaine", PREMIERE_HISTOIRE),
        appel("activer quotidiennes"), appel("activer hebdomadaires"), appel("activer histoire"),
        appel("mettre a jour saison"),
        appel("generer code"), setv("codeSale", 0), setv("menu_sale", 1),
    ])

    S.script(quand_drapeau(), [
        cacher(), aller(0, 0),
        appel("initialiser systemes"),
        toujours([
            # événements différés : un par image, relayés par « sys relais » (voir plus bas) pour que
            # evt_valeur soit écrite APRÈS les gestionnaires lancés dans la même image par les autres sprites
            si(gt(long_liste("evtCode"), 0), [diffuser("sys relais")]),
            # bannière différée tant qu'une autre (victoire, défaite, élimination…) est affichée
            si(et(non(eq(V("messageAttente"), "")), eq(V("message"), "")), [setv("message", V("messageAttente")), setv("messageAttente", "")]),
            # code de sauvegarde régénéré au plus toutes les 0,5 s (les gains d'XP peuvent être fréquents)
            si(et(eq(V("codeSale"), 1), gt(chrono(), V("prochainCode"))), [appel("generer code"), setv("codeSale", 0), setv("prochainCode", add(chrono(), 0.5))]),
            si(gt(chrono(), V("prochainTick")), [
                setv("prochainTick", add(chrono(), 1)),
                appel("mettre a jour quetes"),
                appel("verifier succes"),
                appel("mettre a jour saison"),
            ]),
            si(eq(V("sys_debug"), 1), [
                si(gt(chrono(), V("prochainDebug")), [setv("prochainDebug", add(chrono(), 0.5)), appel("afficher debug")]),
            ]),
        ]),
    ])

    # --- relais des événements différés ------------------------------------------------------------------------------------------------
    # Dans une image, Scratch exécute d'abord toutes les boucles « toujours » (calques décroissants), puis les
    # gestionnaires des diffusions qu'elles ont émises, dans l'ordre d'émission. Écrire evt_valeur depuis la boucle de
    # Systemes écraserait donc la valeur lue par les gestionnaires de « evt lieu », « evt coffre », « evt phase »,
    # « evt fin manche »… émis juste avant par Joueur, Reseau ou Partie (y compris nos propres gestionnaires).
    # « sys relais » (émis par la boucle) s'exécute après ces gestionnaires-là ; « sys relais emettre » (émis par
    # « sys relais ») s'exécute après tous les gestionnaires lancés par les boucles de l'image. C'est là qu'on émet.
    S.script(quand_message("sys relais"), [diffuser("sys relais emettre")])
    S.script(quand_message("sys relais emettre"), [
        si(gt(long_liste("evtCode"), 0), [
            setv("evt_valeur", item("evtVal", 1)),
            si(eq(item("evtCode", 1), 1), [diffuser("evt niveau")]),
            si(eq(item("evtCode", 1), 2), [diffuser("evt quete")]),
            si(eq(item("evtCode", 1), 3), [diffuser("evt succes")]),
            si(eq(item("evtCode", 1), 4), [diffuser("evt achat")]),
            supprimer("evtCode", 1), supprimer("evtVal", 1),
        ]),
    ])

    # --- réactions aux diffusions ----------------------------------------------------------------------------------------------------
    S.script(quand_message("evt nouvelle manche"), [
        setv("xpGagne", 0), vider("RecapLignes"), vider("recapTypes"), vider("recapNb"), vider("recapXp"),
        setv("mancheElims", 0), setv("xpMursRecolte", 0), vider("lieuxVisites"), setv("victoireComptee", 0),
        setv("survieDebut", V("stat_tempsSurvie")),
    ])
    S.script(quand_message("evt elimination"), [
        changev("totElims", 1), changev("mancheElims", 1),
        appel("gagner xp", 50, 1),
        appel("mettre a jour quetes"), appel("verifier succes"),
    ])
    S.script(quand_message("evt knock"), [appel("gagner xp", 25, 2), appel("mettre a jour quetes")])
    S.script(quand_message("evt reanimation"), [appel("gagner xp", 40, 3), appel("mettre a jour quetes"), appel("verifier succes")])
    S.script(quand_message("evt coffre"), [
        changev("totCoffres", 1), appel("gagner xp", 10, 4),
        appel("mettre a jour quetes"), appel("verifier succes"),
    ])
    S.script(quand_message("evt mur"), [
        si(lt(V("xpMursRecolte"), 100), [changev("xpMursRecolte", 2), appel("gagner xp", 2, 5)]),
    ])
    S.script(quand_message("evt recolte"), [
        si(lt(V("xpMursRecolte"), 100), [changev("xpMursRecolte", 1), appel("gagner xp", 1, 6)]),
    ])
    # lieu : seulement en manche, vivant (1) ou à terre (3) — le salon, l'île d'attente (etat 8) et le spectateur
    # passent aussi par des lieux nommés
    S.script(quand_message("evt lieu"), [
        si(et4(eq(V("ecran"), "jeu"), ou(eq(V("etat"), 1), eq(V("etat"), 3)), gt(V("evt_valeur"), 0),
               non(contient("lieuxVisites", V("evt_valeur")))), [
            ajouter_liste("lieuxVisites", V("evt_valeur")), changev("lieuxTotal", 1),
            appel("gagner xp", 5, 7), appel("verifier succes"),
        ]),
    ])
    S.script(quand_message("evt victoire"), [
        si(eq(V("victoireComptee"), 0), [appel("victoire"), appel("verifier succes"), sale()]),
    ])
    S.script(quand_message("evt fin manche"), [setv("rangFin", V("evt_valeur")), appel("fin manche", V("rangFin"))])

    S.script(quand_message("boutique acheter"), [
        si(et(ge(V("evt_valeur"), 1), le(V("evt_valeur"), long_liste("Boutique"))), [
            appel("decouper", item("Boutique", V("evt_valeur"))),
            setv("entree", join(V("champ1"), join("|", V("champ2")))),
            si(contient("Possedes", V("entree")), [notif(tr("Déjà possédé", "Already owned"))], [
                si(lt(V("jetons"), V("champ3")), [notif(tr("Pas assez de jetons", "Not enough coins"))], [
                    changev("jetons", mul(-1, V("champ3"))), ajouter_liste("Possedes", V("entree")),
                    emettre(4, V("evt_valeur")), jouer_son("coffre"),
                    appel("nom cosmetique", V("champ1"), V("champ2")),
                    notif(join(tr("Achat : ", "Purchased: "), V("nomC"))),
                    sale(),
                ]),
            ]),
        ]),
    ])
    S.script(quand_message("casier equiper"), [appel("equiper", V("evt_texte"), V("evt_valeur"), V("evt_cible"))])

    # (posR / idxR : « gagner xp » et « recap » utilisent pos / idx)
    S.script(quand_message("quete reclamer"), [
        setv("posR", V("evt_valeur")),
        si(et(ge(V("posR"), 1), le(V("posR"), long_liste("qaIndex"))), [
            si(eq(item("qaEtat", V("posR")), 1), [
                remplacer("qaEtat", V("posR"), 2),
                setv("idxR", item("qaIndex", V("posR"))),
                changev("jetons", item("qJetons", V("idxR"))),
                appel("ecrire quete", V("posR")),
                appel("gagner xp", item("qXp", V("idxR")), 11),     # « montant » = XP réellement créditée (bonus compris)
                notif(joins(tr("Récompense : +", "Reward: +"), V("montant"), " XP, +", item("qJetons", V("idxR")), tr(" jetons", " coins"))),
                jouer_son("coffre"),
                # quête d'histoire réclamée : la suivante prend sa place
                si(et(eq(item("qType", V("idxR")), 3), le(V("histProchaine"), NB_QUETES)), [
                    appel("placer quete", V("posR"), V("histProchaine")), changev("histProchaine", 1),
                ]),
                sale(),
            ]),
        ]),
    ])
    S.script(quand_message("quete partager"), [
        setv("posR", V("evt_valeur")),
        si(et(ge(V("posR"), 1), le(V("posR"), long_liste("qaIndex"))), [
            setv("chat", add(20, item("qaIndex", V("posR")))), setv("chatSeq", mod(add(V("chatSeq"), 1), 10)),
            notif(join(tr("Quête partagée : ", "Quest shared: "), titre_quete(item("qaIndex", V("posR"))))),
        ]),
    ])

    S.script(quand_message("sauvegarde generer"), [appel("generer code"), setv("codeSale", 0), setv("menu_sale", 1)])
    S.script(quand_message("sauvegarde charger"), [appel("charger code", reponse())])
    S.script(quand_message("createur definir"), [
        setv("codeCreateur", V("evt_texte")),
        si(gt(longueur(V("codeCreateur")), 0),
           [notif(join(tr("Tu soutiens ", "You support "), V("codeCreateur")))],
           [notif(tr("Code créateur retiré", "Creator code removed"))]),
        setv("menu_sale", 1),
    ])
