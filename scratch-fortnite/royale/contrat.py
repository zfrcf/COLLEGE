# -*- coding: utf-8 -*-
"""
CONTRAT PARTAGÉ du projet Royale 3D.

Ce fichier est la seule source de vérité pour tout ce qui est partagé entre
modules : noms d'écrans, variables et listes globales, format des paquets
réseau, variables cloud, touches, événements (diffusions), textes FR/EN,
carte et lieux. Chaque module (menus.py, hud.py, social.py, systemes.py,
partie.py, joueur.py, moteur3d.py…) ne possède que SES sprites et ne touche aux
autres que via les variables/listes/événements déclarés ici.

RÈGLES
------
1. Une variable globale est déclarée ici (dans GLOBALES / LISTES). Un module peut
   déclarer des globales privées supplémentaires, préfixées par son nom
   (`menu_`, `hud_`, `soc_`, `sys_`, `par_`, `jou_`, `m3d_`, `txt_`, `son_`).
2. Les sprites communiquent par variables globales et par diffusions
   (`diffuser("evt ...")`). Pas d'appel de bloc personnalisé entre sprites.
3. Les comparaisons de longues chaînes de chiffres se font avec `eq_txt`.
4. Ordre d'exécution par image = ordre décroissant de `layer` (le sprite au
   calque le plus élevé s'exécute en premier). Voir CALQUES.
5. Le calque stylo est sous tous les sprites : les menus plein écran sont
   dessinés au stylo (fond + texte tamponné) pendant que les sprites 3D sont
   cachés ; le HUD en jeu est dessiné au stylo après le rendu 3D.
"""
import json
import os

from .dsl import Var, item, add, mul, sub, mod

# ---------------------------------------------------------------------------
#  Dimensions et constantes de jeu
# ---------------------------------------------------------------------------
NB_JOUEURS = 6                 # emplacements réseau (☁ J1..☁ J6)
TAILLE = 32                    # carte TAILLE x TAILLE cases
COLONNES_MAX = 120             # taille de la liste Profondeur (qualité épique)
COLONNES_PAR_QUALITE = {1: 40, 2: 80, 3: 120}
NB_COFFRES = 12
NB_BALISES = 2                 # balises de redéploiement
LARGEUR, HAUTEUR = 480, 360

# Durées (secondes) d'une manche — voir partie.py pour la machine à états
DUREE_PREPARTIE = 25           # île d'attente
DUREE_BUS = 20                 # traversée du bus
DUREE_MANCHE = 300             # fin de partie forcée
DUREE_RESULTATS = 20           # écran de fin avant nouvelle manche
# Phases de tempête : (attente, rétrécissement, rayon final, dégâts/s)
PHASES_TEMPETE = [
    (30, 30, 14.0, 1),
    (20, 25, 9.0, 2),
    (15, 20, 5.0, 5),
    (10, 15, 2.5, 8),
    (0, 40, 1.5, 10),          # dernière zone : le centre se déplace pendant le rétrécissement
]
RAYON_INITIAL = 30.0

# ---------------------------------------------------------------------------
#  Écrans (variable globale `ecran`) et onglets du salon (`onglet`)
# ---------------------------------------------------------------------------
ECRANS = ["connexion", "salon", "matchmaking", "chargement", "prepartie", "bus", "parachute",
          "jeu", "pause", "carte", "spectateur", "cinema", "fin"]
ECRANS_RENDU_3D = ["prepartie", "jeu", "pause", "spectateur", "cinema", "fin"]
ECRANS_JOUABLES = ["prepartie", "jeu"]            # entrées de déplacement/tir actives
ONGLETS = ["accueil", "passe", "boutique", "casier", "quetes", "carriere", "parametres"]

# Superpositions en jeu (`superposition`) : "" | "emotes" | "sprays" | "chat" | "inventaire" | "signaler"

# États du joueur (variable `etat`, aussi dans le paquet)
ETAT = {"vivant": 1, "mort": 2, "aterre": 3, "spectateur": 4, "salon": 5, "bus": 6,
        "parachute": 7, "prepartie": 8, "fin": 9}
ETATS_VISIBLES_3D = [1, 3, 8]   # états rendus comme panneau 3D (8 = île d'attente, invulnérable, pas une cible)
# Protocoles (voir joueur.py) :
# - Réanimation : le soigneur publie reanime = emplacement du coéquipier à terre tant qu'il tient « interagir »
#   à moins de 1,5 case ; le joueur à terre accumule le temps où un coéquipier publie son numéro et se relève à 4,5 s.
# - Redéploiement : un coéquipier ramasse la carte (passer à 1 case de mortX/mortY d'un mort de son équipe),
#   puis tient « interagir » 10 s à une balise ; le mort voit E_reanime pendant ≥ 8 s → etat 7 (parachute), redeploiement = 1.
# - Mort en mode à réapparition (Rumble) : etat 2 puis après 5 s etat 7 (parachute) au-dessus de la zone.
# - Mort sans réapparition : etat 2, position figée (mortX/mortY) ; Social passe en écran « spectateur » après 3 s.

# Modes de jeu (chiffre `mode` de ☁ Partie et variable `modeChoisi`)
MODES = {1: "Solo", 2: "Duo", 3: "Trio", 4: "Sections", 5: "Rumble", 6: "Arène"}
TAILLE_EQUIPE = {1: 1, 2: 2, 3: 3, 4: 3, 5: 1, 6: 1}
MODES_AVEC_REAPPARITION = [5]
MODES_EQUIPE = [2, 3, 4]
# Événements à durée limitée (chiffre `ltm` de ☁ Partie) : 0 aucun
LTM = {0: "Aucun", 1: "Pompes uniquement", 2: "Snipers uniquement", 3: "Tempête éclair",
       4: "Munitions infinies", 5: "Gravité faible"}

# ---------------------------------------------------------------------------
#  Calques (ordre d'exécution décroissant) — les sprites invisibles « logiques »
#  prennent les calques hauts pour s'exécuter d'abord.
# ---------------------------------------------------------------------------
CALQUES = {
    "Joueur": 99, "Reseau": 98, "Partie": 97, "Systemes": 96, "Moteur3D": 95,
    "HUD": 90, "Social": 89, "Menus": 88, "Sons": 87, "Texte": 86,
    # sprites visibles (du fond vers l'avant)
    "Spray": 2, "Balise": 3, "CarteRedeploiement": 4, "Marqueur": 5, "Coffre": 6, "Ennemi": 7,
    "Tempête": 10, "Dégâts": 11, "Arme": 12, "Flash": 13, "Viseur": 14, "Message": 15,
}

# ---------------------------------------------------------------------------
#  Paquet réseau d'un joueur (☁ Jn) : "1" puis les champs ci-dessous.
#  Toutes les valeurs sont des entiers ≥ 0 (x, y multipliés par 100).
# ---------------------------------------------------------------------------
CHAMPS = [
    ("x", 4), ("y", 4), ("dir", 3), ("pv", 3), ("bouclier", 3),
    ("battement", 5),            # secondes (maintenant) ; emplacement libre si |écart| > 15 s
    ("cible", 1), ("seq", 2), ("degats", 2),   # dernier tir : cible touchée, n° de tir, dégâts
    ("tueur", 1), ("morts", 1),  # qui m'a éliminé ; compteur de morts (mod 10)
    ("arme", 1),                 # code d'objet tenu (voir OBJETS)
    ("etat", 1),                 # voir ETAT
    ("nom", 16),                 # 8 lettres codées sur 2 chiffres (ALPHABET, 0 = rien)
    ("elims", 2),
    ("niveau", 3),               # niveau de compte
    ("equipe", 1),               # 0 = sans équipe
    ("emote", 1), ("emoteSeq", 1),
    ("pingX", 2), ("pingY", 2), ("pingSeq", 1),
    ("chat", 2), ("chatSeq", 1),
    ("salon", 4),                # code de salon privé (0 = public)
    ("altitude", 2),             # 0 au sol, sinon altitude (parachute/bus)
    ("reanime", 1),              # emplacement du coéquipier que je réanime / redéploie
    ("skin", 2), ("pioche", 1), ("planeur", 1),
    ("surbouclier", 2),
    ("modeChoisi", 1),
    ("degatsTotal", 4), ("victoires", 2), ("banniere", 2),
    ("knockPar", 1),             # qui m'a mis à terre
]
POS = {}
_p = 2
for _n, _l in CHAMPS:
    POS[_n] = (_p, _l)
    _p += _l
LONGUEUR_PAQUET = _p - 1       # 88
assert LONGUEUR_PAQUET <= 250

ALPHABET = list("abcdefghijklmnopqrstuvwxyz0123456789_-")

# ☁ Partie : "1" + debut(5) + mode(1) + ltm(1) + graine(2)
PARTIE_POS = {"debut": (2, 5), "mode": (7, 1), "ltm": (8, 1), "graine": (9, 2)}
# ☁ Construction (+ ☁ Construction2 en débordement) : "1" + entrées de 5 chiffres : matériau(1) xx yy ;
#   matériau 0 = suppression du mur (case remise à 0, sauf bordure). Appliquées dans l'ordre, les deux
#   variables mises bout à bout. Remises à "1" à chaque nouvelle manche.
# ☁ Record : "1" + 3 × [nom(16) elims(4) victoires(3)] (meilleurs joueurs de tous les temps)
RECORD_TAILLE = 23

# ---------------------------------------------------------------------------
#  Objets d'inventaire (codes), armes, consommables, matériaux
# ---------------------------------------------------------------------------
OBJETS = {
    0: "Vide", 1: "Pistolet", 2: "Fusil à pompe", 3: "Sniper", 4: "Bandages", 5: "Médikit",
    6: "Mini-potion", 7: "Potion de bouclier", 8: "Pioche",
}
ARMES = {  # code: (dégâts, cadence s, portée, tolérance, chargeur, type de munitions, temps de recharge)
    1: (20, 0.25, 14, 0.45, 12, "legeres", 1.5),
    2: (70, 0.9, 5, 0.9, 5, "cartouches", 2.0),
    3: (95, 1.4, 40, 0.35, 3, "lourdes", 2.5),
}
CONSOMMABLES = {  # code: (durée d'utilisation s, pv, bouclier, max empilable)
    4: (3, 15, 0, 15), 5: (8, 100, 0, 3), 6: (2, 0, 25, 6), 7: (5, 0, 50, 3),
}
MATERIAUX = {1: "Bois", 2: "Pierre", 3: "Métal"}
# valeur de case de la carte -> (nom, matériau récolté, coups de pioche pour détruire un mur construit)
CASES = {1: ("Béton", 2, 5), 2: ("Bois", 1, 3), 3: ("Brique", 2, 5), 4: ("Métal", 3, 7)}
MUR_PAR_MATERIAU = {1: 2, 2: 1, 3: 4}     # matériau de construction -> valeur de case
COUT_MUR = 10

# ---------------------------------------------------------------------------
#  Touches configurables : liste globale `Touches` (index 1..n)
# ---------------------------------------------------------------------------
TOUCHES = ["avancer", "reculer", "gauche", "droite", "sauter", "construire", "interagir", "recharger",
           "carte", "pause", "chat", "emotes", "sprays", "ping", "pioche", "materiau", "edition", "sprint", "viser"]
PRESET_AZERTY = ["z", "s", "q", "d", "space", "b", "e", "r", "m", "p", "t", "y", "h", "v", "f", "n", "g", "x", "c"]
PRESET_QWERTY = ["w", "s", "a", "d", "space", "b", "e", "r", "m", "p", "t", "y", "h", "v", "f", "n", "g", "x", "c"]
TOUCHE = {nom: i + 1 for i, nom in enumerate(TOUCHES)}


def touche_config(nom):
    """Reporter : nom de touche configuré (à passer à `touche(...)`)."""
    return item("Touches", TOUCHE[nom])


# ---------------------------------------------------------------------------
#  Événements (diffusions). Les détails voyagent dans les variables evt_*.
# ---------------------------------------------------------------------------
EVENEMENTS = [
    "demarrer",                 # drapeau vert : initialisation des sprites
    "evt tir",                  # j'ai tiré (evt_valeur = code d'arme)
    "evt touche",               # j'ai touché quelqu'un (evt_cible, evt_valeur = dégâts)
    "evt degats",               # j'ai pris des dégâts (evt_valeur, evt_source = emplacement ou 0 tempête, evt_angle)
    "evt mort",                 # je suis mort (evt_source)
    "evt aterre",               # je suis à terre
    "evt elimination",          # j'ai éliminé quelqu'un (evt_cible)
    "evt coffre",               # coffre ouvert (evt_valeur = n°)
    "evt mur",                  # mur construit (evt_valeur = matériau)
    "evt recolte",              # matériaux récoltés (evt_valeur = matériau)
    "evt soin",                 # consommable utilisé (evt_valeur = code objet)
    "evt reanimation",          # j'ai réanimé/redéployé (evt_cible)
    "evt nouvelle manche",      # début d'une manche (Partie)
    "evt phase",                # changement de phase de partie (evt_valeur = phase)
    "evt atterrissage",         # j'ai touché le sol après le parachute
    "evt fin manche",           # fin de la manche (evt_valeur = rang)
    "evt victoire",             # j'ai gagné
    "evt niveau",               # niveau de compte gagné (evt_valeur)
    "evt quete",                # quête terminée (evt_valeur = index)
    "evt succes",               # succès débloqué (evt_valeur = index)
    "evt achat",                # achat en boutique (evt_valeur = index)
    "evt lieu",                 # entrée dans un lieu nommé (evt_valeur = index de Lieux)
    "evt ping",                 # ping posé (evt_cible = emplacement, evt_valeur = x*100+y)
    "evt chat",                 # message rapide reçu (evt_cible, evt_valeur = index)
    "evt emote",                # émote reçue (evt_cible, evt_valeur)
    "evt notification",         # texte à afficher (evt_texte)
    "evt changement ecran",     # `ecran` vient de changer
    "sauvegarde charger",       # Menus a demandé un code de sauvegarde (reponse()) → Systemes le décode
    "sauvegarde generer",       # Systemes doit régénérer codeSauvegarde
    "evt knock",                # j'ai mis quelqu'un à terre (evt_cible)
    "evt record",               # ☁ Record vient d'être relu (listes Record_*)
    "record proposer",          # demande à Reseau d'inscrire rec_elims / rec_victoires au ☁ Record
]
# Sons : `diffuser("son <nom>")` après avoir réglé `son_pan` (-100..100) et `son_volume` (0..100, relatif).
SONS = ["tir_pistolet", "tir_pompe", "tir_sniper", "touche", "elimination", "degats", "coffre",
        "construction", "pioche", "rechargement", "clic", "survol", "victoire", "defaite", "tempete",
        "saut", "bus", "parachute", "emote", "notification", "compte", "niveau", "soin", "bouclier",
        "aterre", "reanimation", "musique_salon", "musique_fin"]

# ---------------------------------------------------------------------------
#  Variables globales : nom -> valeur initiale. (Module propriétaire en commentaire.)
# ---------------------------------------------------------------------------
GLOBALES = {
    # --- navigation (menus) ---
    "ecran": "connexion", "onglet": "accueil", "superposition": "", "ecranPrecedent": "",
    "survol": 0,                     # index du bouton survolé (pour le son/affichage)
    "menu_sale": 1,                  # 1 = un écran de menu doit être redessiné (n'importe quel module peut le demander)
    "menu_rafraichi": 0,             # 1 pendant l'image où Menus vient de redessiner le fond (Social dessine alors sa barre)
    "enPartie": 0,                   # 1 dès que le joueur a appuyé sur Jouer (Partie le place alors dans la manche)
    "ltmChoisi": 0,                  # événement limité choisi dans le sélecteur de mode (0 = aucun)
    # --- identité et réseau (Reseau/joueur) ---
    "monSlot": 0, "nomCode": "", "monNom": "", "maintenant": 0, "paquet": "", "_ext": "", "_pad": "", "_i": 0,
    "connecte": 0,                   # 1 quand un emplacement est pris
    "reconnexion": 0,                # 1 si la partie a été reprise après déconnexion
    "latence": 0,                    # latence estimée (ms)
    "paquetsEnvoyes": 0, "paquetsRecus": 0,
    # --- position / caméra (joueur ; spectateur/cinéma écrivent aussi) ---
    "px": 16.5, "py": 16.5, "dir": 0, "hauteur": 0, "horizon": 0, "plan": 0.66,
    # --- état du joueur ---
    "etat": 5, "❤ PV": 100, "🛡 Bouclier": 0, "surbouclier": 0, "endurance": 100,
    "invulnerable": 0, "altitude": 0, "aterreDepuis": 0, "pvAterre": 0, "respawnT": 0, "monEmoteFin": 0,
    "monEquipe": 0, "modeChoisi": 5, "mode": 5, "ltm": 0, "remplissage": 1,
    "codeSalon": 0, "confidentialite": 0,
    # --- inventaire / munitions / matériaux ---
    "slotActif": 1, "armeNum": 1, "🔫 Munitions": 0, "🎯 Arme": "Pistolet",
    "munitions_legeres": 36, "munitions_cartouches": 10, "munitions_lourdes": 6,
    "mat_bois": 0, "mat_pierre": 0, "mat_metal": 0, "materiauActif": 1, "🧱 Matériaux": 0,
    "rechargeFin": 0, "utilisationFin": 0, "utilisationDebut": 0, "utilisationObjet": 0,
    "interactionDebut": 0, "interactionType": 0, "interactionCible": 0,   # 1 coffre, 2 réanimation, 3 redéploiement
    "modeConstruction": 0, "tirAnim": 0, "toucheFin": 0, "flash": 0, "message": "",
    "rechargeDebut": 0, "interactionDuree": 1, "murCoups": 0, "murCible": 0, "reanimationProgres": 0,
    # --- champs du paquet écrits par les modules (Joueur : cible/seq/degats/tueur/morts/knockPar/reanime ;
    #     Social : emote/emoteSeq/pingX/pingY/pingSeq/chat/chatSeq ; Systemes : skin/pioche/planeur/banniere/niveau) ---
    "cible": 0, "seq": 0, "degats": 0, "tueur": 0, "morts": 0, "knockPar": 0, "reanime": 0,
    "emote": 0, "emoteSeq": 0, "pingX": 0, "pingY": 0, "pingSeq": 0, "chat": 0, "chatSeq": 0,
    "mortX": 0, "mortY": 0,          # position figée à la mort (carte de redéploiement, encodée à la place de px/py)
    "redeploiement": 0,              # 1 = un coéquipier vient de me redéployer (Partie me renvoie en parachute)
    "rec_elims": 0, "rec_victoires": 0,   # proposition de record (diffusion "record proposer")
    # --- partie / zone (Partie) ---
    "debut": 0, "tempsManche": 0, "phase": 0,        # phase : 0 prépartie,1 bus,2 parachute/combat,3..7 tempête,8 fin
    "zoneX": 16.5, "zoneY": 16.5, "zoneR": 30, "zoneDegats": 1, "horsZone": 0,
    "prochaineZoneX": 16.5, "prochaineZoneY": 16.5, "prochaineZoneR": 14, "tempsAvantZone": 0, "zoneEnMouvement": 0,
    "tempsPhase": 0,                 # secondes restantes dans la phase courante (pré-partie, bus, attente/rétrécissement)
    "⏱ Zone": 0, "👥 Joueurs": 1, "💀 Éliminations": 0, "vivants": 1, "equipesVivantes": 1,
    "rang": 0, "victoire": 0, "finManche": 0, "tempsPartie": 0, "graine": 0,
    "busX": 0, "busY": 0, "busDirX": 1, "busDirY": 0, "busProgression": 0, "aSaute": 0,
    "participants": 1,
    # --- spectateur / cinéma (Social) ---
    "spectSlot": 0, "cineVitesse": 0.2,
    # --- événements (détails) ---
    "evt_valeur": 0, "evt_cible": 0, "evt_source": 0, "evt_angle": 0, "evt_texte": "",
    "son_pan": 0, "son_volume": 100,
    # --- statistiques de session (incrémentées par qui observe) ---
    "stat_elims": 0, "stat_degats": 0, "stat_degatsRecus": 0, "stat_coffres": 0, "stat_murs": 0,
    "stat_tirs": 0, "stat_touches": 0, "stat_distance": 0, "stat_tempsSurvie": 0, "stat_victoires": 0,
    "stat_parties": 0, "stat_top3": 0, "stat_reanimations": 0, "stat_materiaux": 0, "stat_pings": 0,
    "stat_emotes": 0, "stat_soins": 0, "stat_recoltes": 0, "stat_morts": 0, "stat_meilleurRang": 0,
    "lieuActuel": 0,                 # index du lieu nommé où je me trouve (0 = aucun)
    # --- progression (Systemes) ---
    "xp": 0, "niveau": 1, "xpNiveau": 0, "xpSuivant": 1000, "jetons": 500, "hype": 0, "division": 1,
    "passeNiveau": 1, "etoiles": 0, "saison": 1, "chapitre": 1, "joursSaison": 0, "bonusXP": 0,
    "xpGagne": 0,                    # XP gagnée pendant la manche (récap)
    "skin": 1, "pioche": 1, "planeur": 1, "spray": 1, "banniere": 1, "styleSkin": 0,
    "codeSauvegarde": "", "codeCreateur": "",
    # --- paramètres (Menus) ---
    "param_sensibilite": 1, "param_viseeAssistee": 1, "param_constructionTurbo": 0, "param_editionRapide": 1,
    "param_qualite": 2, "param_afficherFPS": 0, "param_performance": 0, "param_effetsDegats": 1,
    "param_volumeMusique": 50, "param_volumeEffets": 80, "param_volumeVoix": 80, "param_sousTitres": 0,
    "param_daltonisme": 0, "param_tailleHUD": 100, "param_langue": 0, "param_region": 0,
    "param_afficherPing": 0, "param_infosReseau": 0, "param_clavier": 0,    # 0 AZERTY, 1 QWERTY
    "fps": 30, "colonnes": 80,
}

# Listes globales : nom -> valeurs initiales
def _carte():
    return [cellule_base(x, y) for y in range(TAILLE) for x in range(TAILLE)]


CARTE_ASCII = [
    # 32 colonnes ; ligne du haut = y = 31. 1 béton, 2 bois, 3 brique, 4 métal, '.' vide
    "11111111111111111111111111111111",
    "1..............................1",
    "1.3333.........44444...........1",
    "1.3..3.........4...4......111..1",
    "1.3..3.........4...4......1....1",
    "1.3333.........44.44......1....1",
    "1..............................1",
    "1........1.....................1",
    "1........1.........2222........1",
    "1........1.........2..2........1",
    "1..................2..2....3...1",
    "1....1111..........2222....3...1",
    "1....1..1..................3...1",
    "1....1..1......................1",
    "1..............33333...........1",
    "1..............3...3...........1",
    "1......11......3...3......44...1",
    "1......11......33.33......4....1",
    "1..............................1",
    "1..4444........................1",
    "1..4..4.........11111..........1",
    "1..4..4.........1...1..........1",
    "1..44.4.........1...1....2222..1",
    "1...............11.11....2..2..1",
    "1........................2..2..1",
    "1..........3.............2222..1",
    "1..........3...................1",
    "1..........3.....1111..........1",
    "1....22..........1..1..........1",
    "1....22..........1..1..........1",
    "1..............................1",
    "11111111111111111111111111111111",
]
assert len(CARTE_ASCII) == TAILLE and all(len(l) == TAILLE for l in CARTE_ASCII)


def cellule_base(x, y):
    c = CARTE_ASCII[TAILLE - 1 - y][x]
    return 0 if c == "." else int(c)


# Lieux nommés (nom FR, nom EN, x, y, rayon) — affichés sur la carte, notification à l'arrivée
LIEUX = [
    ("Fort Béton", "Concrete Fort", 3.5, 27.5, 4),
    ("Hangar Métal", "Metal Hangar", 17.5, 27.5, 4),
    ("Tour Nord", "North Tower", 27.5, 27.5, 3),
    ("Cabane Bois", "Wood Cabin", 20.5, 21.5, 3),
    ("Place Brique", "Brick Plaza", 17.5, 15.5, 4),
    ("Bunker Ouest", "West Bunker", 4.5, 10.5, 4),
    ("Marché", "Market", 18.5, 9.5, 4),
    ("Chalet Est", "East Lodge", 26.5, 7.5, 4),
    ("Ruines Sud", "South Ruins", 18.5, 2.5, 3),
]
COFFRES = [(3.5, 28.5), (17.5, 28.5), (27.5, 26.5), (20.5, 21.5), (16.5, 15.5), (5.5, 9.5), (17.5, 9.5), (26.5, 7.5),
           (18.5, 2.5), (7.5, 19.5), (12.5, 5.5), (28.5, 18.5)]
BALISES = [(10.5, 25.5), (24.5, 12.5)]       # balises de redéploiement
for _cx, _cy in COFFRES + BALISES:
    assert cellule_base(int(_cx), int(_cy)) == 0, (_cx, _cy)

# Phrases du chat rapide (FR, EN) — index 1..n ; 20+ = partage de quête
CHAT_RAPIDE = [("Salut !", "Hi!"), ("Bien joué !", "Nice one!"), ("Merci", "Thanks"), ("Par ici", "Over here"),
               ("Ennemi repéré", "Enemy spotted"), ("Besoin de soins", "Need healing"), ("Allons-y", "Let's go"),
               ("Attention !", "Watch out!"), ("👍", "👍"), ("Désolé", "Sorry")]
EMOTES = [("Salut", "Wave"), ("Danse", "Dance"), ("Rire", "Laugh"), ("Pouce", "Thumbs up"), ("Applaudir", "Clap"),
          ("Boude", "Sulk")]
SPRAYS = ["Lama", "Éclair", "Cœur", "Crâne", "Étoile", "Flamme"]

LISTES = {
    "Carte": _carte(), "CarteBase": _carte(),
    "Profondeur": [30] * COLONNES_MAX,
    "Alphabet": ALPHABET,
    "Touches": PRESET_AZERTY,
    "Inventaire": [1, 2, 3, 4, 6],            # codes d'objets par emplacement (1..5)
    "Quantites": [12, 5, 3, 5, 3],            # munitions dans le chargeur / nombre de consommables
    # lieux nommés : LieuxNom contient les noms FR puis les noms EN (index i + len(LIEUX) * param_langue)
    "LieuxNom": [l[0] for l in LIEUX] + [l[1] for l in LIEUX],
    "LieuxX": [l[2] for l in LIEUX], "LieuxY": [l[3] for l in LIEUX], "LieuxR": [l[4] for l in LIEUX],
    "ObjetNoms": [OBJETS[i] for i in range(1, 9)],
    "ArmeDegats": [ARMES[i][0] for i in (1, 2, 3)], "ArmeCadence": [ARMES[i][1] for i in (1, 2, 3)],
    "ArmePortee": [ARMES[i][2] for i in (1, 2, 3)], "ArmeTolerance": [ARMES[i][3] for i in (1, 2, 3)],
    "ArmeChargeur": [ARMES[i][4] for i in (1, 2, 3)], "ArmeRecharge": [ARMES[i][6] for i in (1, 2, 3)],
    "ConsoDuree": [CONSOMMABLES[i][0] for i in (4, 5, 6, 7)], "MaxConsommable": [CONSOMMABLES[i][3] for i in (4, 5, 6, 7)],
    # LTMNoms : FR (index ltm+1) puis EN (index ltm+1+6)
    "LTMNoms": [LTM[i] for i in range(6)] + ["None", "Shotguns only", "Snipers only", "Flash storm", "Infinite ammo", "Low gravity"],
    "ModeNoms": [MODES[i] for i in range(1, 7)] + ["Solo", "Duos", "Trios", "Squads", "Rumble", "Arena"],
    "MateriauNoms": [MATERIAUX[i] for i in range(1, 4)],
    "CoffresX": [c[0] for c in COFFRES], "CoffresY": [c[1] for c in COFFRES], "CoffresPris": [],
    "BalisesX": [b[0] for b in BALISES], "BalisesY": [b[1] for b in BALISES],
    "CartesRamassees": [],                    # emplacements dont j'ai la carte de redéploiement
    "Journal": [], "Notifications": [], "DegatsAffiches": [], "Bruits": [], "Chat": [], "Pings": [], "Muets": [],
    "DegatsRecus": [],                        # entrées fixes "s ddd a" (source 1, dégâts 3, arme 1) : décodées par Reseau, appliquées par Joueur
    "NotificationsFin": [], "ChatFin": [], "JournalFin": [],   # expirations (valeur du chronomètre) parallèles
    "Record_nom": ["", "", ""], "Record_elims": [0, 0, 0], "Record_victoires": [0, 0, 0],   # ☁ Record décodé
    "Sprays": [],                             # xxxx yyyy t ddd : sprays posés localement (max 10)
    # --- progression (remplies par Systemes ; lues par Menus/Social) ---
    "QueteTitres": [],                        # titres FR puis EN (index i + NB_QUETES * param_langue), remplis par Systemes
    "QuetesActives": [],                      # "index|type|progression|objectif|etat|xp" (type 1 quotidienne 2 hebdo 3 histoire ; etat 0 en cours, 1 terminée, 2 réclamée)
    "Succes": [],                             # "index|etat" (0 verrouillé, 1 débloqué)
    "PasseRecompenses": [],                   # 100 entrées "type|id" (type : skin, pioche, planeur, spray, emote, banniere, jetons, style)
    "Possedes": [],                           # cosmétiques possédés "type|id"
    "Boutique": [],                           # 6 entrées du jour "type|id|prix"
    "EmotesEquipees": [1, 2, 3, 4, 5, 6],     # roue d'émotes (6 cases)
    "RecapLignes": [],                        # lignes du récapitulatif de fin de partie ("Éliminations ×3 : +150 XP")
    "Textes": [],                             # rempli par tr() : index 2k+1 = FR, 2k+2 = EN
    "ChatRapide": [f for f, _ in CHAT_RAPIDE] + [e for _, e in CHAT_RAPIDE],
    "Emotes": [f for f, _ in EMOTES] + [e for _, e in EMOTES],
    "SprayNoms": SPRAYS,
}
for _nom in ["E_x", "E_y", "E_dir", "E_pv", "E_bouclier", "E_battement", "E_cible", "E_seq", "E_degats", "E_tueur",
             "E_morts", "E_arme", "E_etat", "E_nom", "E_elims", "E_niveau", "E_equipe", "E_emote", "E_emoteSeq",
             "E_pingX", "E_pingY", "E_pingSeq", "E_chat", "E_chatSeq", "E_salon", "E_altitude", "E_reanime",
             "E_skin", "E_pioche", "E_planeur", "E_surbouclier", "E_modeChoisi", "E_degatsTotal", "E_victoires",
             "E_banniere", "E_knockPar",
             "E_actif", "E_paquet", "E_dernierSeq", "E_dernierMorts", "E_dernierEmoteSeq", "E_dernierPingSeq",
             "E_dernierChatSeq", "E_vu", "E_emoteFin", "E_dernierEtat", "E_dernierBattement", "E_vuA"]:
    LISTES[_nom] = [0] * NB_JOUEURS

CLOUD = ["☁ J%d" % k for k in range(1, NB_JOUEURS + 1)] + ["☁ Construction", "☁ Construction2", "☁ Partie", "☁ Record"]

# ---------------------------------------------------------------------------
#  Textes traduits : tr("Jouer", "Play") -> reporter Scratch du texte dans la langue courante
# ---------------------------------------------------------------------------
_TEXTES = []       # [(fr, en)]
_INDEX = {}


def tr(fr, en=None):
    """Enregistre un couple FR/EN et renvoie l'expression `item(2k + langue + 1, Textes)`."""
    en = fr if en is None else en
    cle = (fr, en)
    if cle not in _INDEX:
        _INDEX[cle] = len(_TEXTES)
        _TEXTES.append(cle)
    k = _INDEX[cle]
    return item("Textes", add(2 * k + 1, Var("param_langue")))


def textes_enregistres():
    out = []
    for fr, en in _TEXTES:
        out += [fr, en]
    return out


# ---------------------------------------------------------------------------
#  Formats des entrées de listes (largeur fixe → extraction par sous_chaine)
#  Pings           : k(1) xxxx(4 = x*100) yyyy(4) eeeeee(6 = chrono*10 à l'expiration)          15 car.
#  DegatsAffiches  : mmm(3) xxxx(4 = sx+2000) yyyy(4 = sy+2000) eeeeee(6) t(1 : 0 pv, 1 bouclier) 18 car.
#  Bruits          : aaa(3 = angle relatif 0..359, 0 devant, 90 à droite) eeeeee(6) t(1 : 1 tir, 2 pas, 3 coffre) 10 car.
#  Sprays          : xxxx(4) yyyy(4) t(1) ddd(3 = direction)                                       12 car.
#  Journal / Notifications / Chat : texte libre, expiration dans la liste *Fin parallèle.
# ---------------------------------------------------------------------------
def sous_chaine(expr, debut, longueur):
    """Reporter : les `longueur` caractères de `expr` à partir de `debut` (1-indexé ; entier ou expression), sans boucle."""
    from .dsl import lettre, join, Node
    if isinstance(debut, (int, float)):
        parties = [lettre(debut + i, expr) for i in range(longueur)]
    else:
        parties = [lettre(add(debut, i) if i else debut, expr) for i in range(longueur)]
    out = parties[-1]
    for p in reversed(parties[:-1]):
        out = join(p, out)
    return out


def rembourrer(valeur, chiffres):
    """Reporter : entier `valeur` (0 ≤ v < 10^chiffres) sur `chiffres` positions, sans boucle :
    on ajoute 10^chiffres puis on retire le premier caractère."""
    from .dsl import rnd, add, join, lettre
    # join de lettres 2..chiffres+1 de (valeur + 10^chiffres)
    base = rnd(add(valeur, 10 ** chiffres))
    return sous_chaine(base, 2, chiffres)


def ecart(a, b):
    """Différence signée a - b sur un cadran de 100000 s (horloges décalées entre joueurs)."""
    return sub(mod(add(sub(a, b), 50000), 100000), 50000)


def index_cellule(x, y):
    from .dsl import floor
    return add(mul(floor(y), TAILLE), add(floor(x), 1))


def cellule(x, y):
    """Reporter : valeur de la case (x, y) de `Carte`."""
    return item("Carte", index_cellule(x, y))


# ---------------------------------------------------------------------------
#  Déclaration sur la scène
# ---------------------------------------------------------------------------
def declarer_globales(stage):
    for nom in CLOUD:
        stage.var(nom, 0, cloud=True)
    for nom, val in GLOBALES.items():
        stage.var(nom, val)
    for nom, vals in LISTES.items():
        stage.liste(nom, vals)


def finaliser_textes(stage):
    """À appeler juste avant la sérialisation : remplit la liste Textes."""
    stage.lists["Textes"] = (stage.lists["Textes"][0], textes_enregistres())


def exporter_json(chemin=None):
    """Écrit outils/contrat.json pour les tests JavaScript."""
    chemin = chemin or os.path.join(os.path.dirname(__file__), "..", "outils", "contrat.json")
    data = {
        "champs": CHAMPS, "pos": POS, "longueurPaquet": LONGUEUR_PAQUET, "alphabet": ALPHABET,
        "etat": ETAT, "modes": MODES, "ltm": LTM, "ecrans": ECRANS, "onglets": ONGLETS, "taille": TAILLE,
        "coffres": COFFRES, "balises": BALISES, "lieux": LIEUX, "touches": TOUCHES, "presetAzerty": PRESET_AZERTY,
        "objets": OBJETS, "phasesTempete": PHASES_TEMPETE, "durees": {"prepartie": DUREE_PREPARTIE, "bus": DUREE_BUS,
                                                                     "manche": DUREE_MANCHE, "resultats": DUREE_RESULTATS},
        "partiePos": PARTIE_POS, "globales": list(GLOBALES.keys()), "listes": list(LISTES.keys()),
        "evenements": EVENEMENTS, "sons": SONS, "chatRapide": CHAT_RAPIDE, "emotes": EMOTES,
    }
    temporaire = chemin + ".tmp.%d" % os.getpid()
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    os.replace(temporaire, chemin)
    return chemin


if __name__ == "__main__":
    print("contrat exporté :", exporter_json(), "— paquet de", LONGUEUR_PAQUET, "chiffres")
