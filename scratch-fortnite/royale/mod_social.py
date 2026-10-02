# -*- coding: utf-8 -*-
"""
MODULE SOCIAL — sprite « Social » (calque CALQUES["Social"]) : tout le social et le spectateur.

1. Barre latérale sociale / liste d'amis dans le salon (x ∈ [150, 235], y ∈ [−150, 120]), dessinée
   quand `menu_rafraichi` = 1 ; `menu_sale` = 1 dès que les joueurs actifs, un survol ou un
   état interne (menu « … », mode info) changent.
2. Chat textuel rapide : superposition "chat" (touche `chat`), zone des derniers messages en jeu.
3. Roue d'émotes (superposition "emotes", touche `emotes`) et roue de sprays ("sprays", touche `sprays`).
4. Ping / marquage : touche `ping` en jeu, clic sur la carte plein écran (ecran = "carte").
5. Spectateur après la mort / mode spectateur (ecran = "spectateur", `spectSlot`).
6. Replay / mode cinéma = caméra libre (ecran = "cinema", `cineVitesse`).
7. Signaler un joueur (superposition "signaler", `soc_cible`, liste `Muets`).

Variables globales privées : soc_cible (joueur à signaler), soc_etape (étape du signalement :
1 choix du joueur, 2 raison, 3 confirmation), soc_mortT (chronomètre à la mort), soc_menuK
(emplacement dont le menu « … » est ouvert, 0 fermé).

Protocole « salon » : Menus efface et dessine le fond quand menu_sale = 1 puis met
menu_rafraichi = 1 pendant une image ; Social dessine alors sa barre (et le panneau de
signalement s'il est ouvert). Sur les écrans 3D, le rendu est effacé à chaque image : les
superpositions en jeu sont redessinées à chaque image.

Spectateur automatique : armé au passage de `etat` à 2 (ou 4) et déclenché UNE seule fois
(3 s après la mort, sur l'écran « jeu » ou « pause ») ; désarmé dès que l'écran est déjà
« spectateur » / « cinema », pour que la pause ouverte depuis le spectateur reste affichée.

Signalement depuis la pause : Menus (calque 88) redessine son menu de pause après Social à
chaque image et recouvrirait le panneau ; Social revient donc sur l'écran 3D sous-jacent
(`ecranPrecedent`) le temps du signalement et retourne à la pause quand on ferme.
Mes superpositions (chat, roues, signalement) sont refermées par un changement d'écran vers un
écran où elles n'ont pas de sens (salon, bus, fin, …).

Caméra libre : `horizon` est recalculé chaque image par Joueur (horizon = −hauteur) AVANT le
rendu ; Social règle donc `hauteur` (négative : la gravité de Joueur ne la touche pas) pour
obtenir un horizon de 0 à 40 px (vue plongeante) et la remet à 0 en quittant l'écran "cinema".
`velY` étant locale à Joueur, une hauteur positive (horizon négatif) ne peut pas être tenue.
"""
import math

from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as SV
from . import texte

try:
    from . import svg_ui as UI
except Exception:  # module des icônes pas encore disponible
    UI = None

V = Var
A = Arg
ORDRE = 60

# ---------------------------------------------------------------------------
#  Géométrie (partagée avec outils/scenarios/60_social.js et captures_scripts/social.js)
# ---------------------------------------------------------------------------
SB_X1, SB_X2, SB_Y1, SB_Y2 = 150, 235, -150, 120     # barre sociale
RANG_TOP, RANG_H, RANGS_MAX = 96, 40, 5              # lignes d'amis (haut de la 1re ligne, hauteur, nombre max)
BTN_INV_Y, BTN_PSEUDO_Y, BTN_H = -117, -139, 20       # boutons du bas (centres)
CHAT_X1, CHAT_X2, CHAT_Y1, CHAT_Y2 = -150, 150, -75, 85   # panneau de chat
CELL_W, CELL_H, CELL_PAS = 140, 20, 24
ROUE_CX, ROUE_CY, ROUE_R, ROUE_EP = 0, 10, 62, 44     # roues (émotes / sprays)
SIG_X1, SIG_X2, SIG_Y1, SIG_Y2 = -130, 130, -90, 90   # panneau de signalement
SIG_LIGNE_Y2, SIG_LIGNE_PAS, SIG_LIGNE_H = 52, 24, 20
ZC_X1, ZC_X2, ZC_Y1, ZC_Y2 = -235, -60, -115, -60     # zone des messages en jeu
RAISONS = [("Triche", "Cheating"), ("Comportement", "Behaviour"),
           ("Pseudo inapproprié", "Inappropriate name"), ("Autre", "Other")]


def tr(fr, en=None):
    return C.tr(fr, en)


def _dyn(x):
    """Vrai si x est une expression Scratch (et non un nombre Python)."""
    return isinstance(x, (Node, Var, Arg))


# ---------------------------------------------------------------------------
#  Icônes : svg_ui si disponible, sinon SVG simples de remplacement
# ---------------------------------------------------------------------------
def _ui(nom, *args):
    f = getattr(UI, nom, None) if UI else None
    if f is None:
        return None
    try:
        return f(*args)
    except Exception:
        return None


def _svg_emote(n):
    s = _ui("emote", n)
    if s:
        return s
    face = '<circle cx="24" cy="24" r="20" fill="#fcd34d" stroke="#92400e" stroke-width="2.5"/>'
    yeux = '<circle cx="17" cy="19" r="3" fill="#1f2937"/><circle cx="31" cy="19" r="3" fill="#1f2937"/>'
    sourire = '<path d="M14 28 Q24 38 34 28" fill="none" stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>'
    if n == 1:      # Salut : visage + main qui salue
        corps = face + yeux + sourire + ('<rect x="33" y="2" width="13" height="18" rx="5" fill="#fcd34d" stroke="#92400e" stroke-width="2"/>'
                                         '<path d="M35 6 V2 M39 5 V0.5 M43 6 V2" stroke="#92400e" stroke-width="2" stroke-linecap="round"/>')
    elif n == 2:    # Danse : visage + note de musique
        corps = face + yeux + sourire + ('<circle cx="39" cy="11" r="5" fill="#1d4ed8"/><rect x="42" y="0" width="3" height="11" fill="#1d4ed8"/>'
                                         '<path d="M45 0 Q50 2 48 7" fill="none" stroke="#1d4ed8" stroke-width="3"/>')
    elif n == 3:    # Rire : grande bouche ouverte
        corps = face + yeux + ('<path d="M12 26 Q24 42 36 26 Z" fill="#7f1d1d"/><path d="M17 31 Q24 37 31 31 Z" fill="#f87171"/>')
    elif n == 4:    # Pouce : main pouce levé
        corps = ('<rect x="8" y="22" width="9" height="20" rx="3" fill="#fcd34d" stroke="#92400e" stroke-width="2"/>'
                 '<path d="M17 24 h16 a4 4 0 0 1 0 8 h-1 a4 4 0 0 1 0 8 h-2 a3 3 0 0 1 -1 5 h-12 z" fill="#fcd34d" stroke="#92400e" stroke-width="2"/>'
                 '<path d="M19 24 V14 a4 4 0 0 1 8 0 v10" fill="#fcd34d" stroke="#92400e" stroke-width="2"/>')
    elif n == 5:    # Applaudir : deux mains
        corps = ('<rect x="6" y="14" width="14" height="22" rx="5" fill="#fcd34d" stroke="#92400e" stroke-width="2" transform="rotate(-15 13 25)"/>'
                 '<rect x="28" y="14" width="14" height="22" rx="5" fill="#fcd34d" stroke="#92400e" stroke-width="2" transform="rotate(15 35 25)"/>'
                 '<path d="M22 6 L24 12 M18 4 L21 10 M28 4 L26 10" stroke="#f97316" stroke-width="2.5" stroke-linecap="round"/>')
    else:           # Boude : moue + sourcils
        corps = face + yeux + ('<path d="M15 34 Q24 26 33 34" fill="none" stroke="#1f2937" stroke-width="3" stroke-linecap="round"/>'
                               '<path d="M12 13 L21 16 M36 13 L27 16" stroke="#1f2937" stroke-width="2.5" stroke-linecap="round"/>')
    return SV.svg(48, 48, corps)


def _svg_spray(n):
    s = _ui("spray", n)
    if s:
        return s
    fond = '<circle cx="24" cy="24" r="23" fill="#111827" fill-opacity="0.55"/>'
    if n == 1:      # Lama
        corps = ('<ellipse cx="22" cy="30" rx="13" ry="8" fill="#f9a8d4" stroke="#831843" stroke-width="2"/>'
                 '<rect x="30" y="12" width="7" height="18" rx="3" fill="#f9a8d4" stroke="#831843" stroke-width="2"/>'
                 '<ellipse cx="35" cy="11" rx="6" ry="4.5" fill="#f9a8d4" stroke="#831843" stroke-width="2"/>'
                 '<path d="M31 8 L30 3 M37 8 L39 3" stroke="#831843" stroke-width="2" stroke-linecap="round"/>'
                 '<path d="M14 36 V43 M20 37 V43 M26 37 V43 M31 35 V43" stroke="#831843" stroke-width="2.5" stroke-linecap="round"/>')
    elif n == 2:    # Éclair
        corps = '<polygon points="27,3 11,27 22,27 18,45 37,19 26,19 31,3" fill="#fde047" stroke="#a16207" stroke-width="2"/>'
    elif n == 3:    # Cœur
        corps = '<path d="M24 42 L7 25 A9 9 0 0 1 24 13 A9 9 0 0 1 41 25 Z" fill="#ef4444" stroke="#7f1d1d" stroke-width="2"/>'
    elif n == 4:    # Crâne
        corps = ('<circle cx="24" cy="21" r="15" fill="#f3f4f6" stroke="#374151" stroke-width="2"/>'
                 '<rect x="16" y="30" width="16" height="10" rx="2" fill="#f3f4f6" stroke="#374151" stroke-width="2"/>'
                 '<circle cx="18" cy="21" r="4" fill="#111827"/><circle cx="30" cy="21" r="4" fill="#111827"/>'
                 '<path d="M20 32 V38 M24 32 V38 M28 32 V38" stroke="#374151" stroke-width="1.5"/>')
    elif n == 5:    # Étoile
        pts = []
        for i in range(10):
            r = 20 if i % 2 == 0 else 8.5
            a = -math.pi / 2 + i * math.pi / 5
            pts.append("%.1f,%.1f" % (24 + r * math.cos(a), 24 + r * math.sin(a)))
        corps = '<polygon points="%s" fill="#fbbf24" stroke="#92400e" stroke-width="2"/>' % " ".join(pts)
    else:           # Flamme
        corps = ('<path d="M24 4 Q34 16 30 22 Q36 20 36 30 Q36 44 24 44 Q12 44 12 30 Q12 22 18 16 Q18 24 22 24 Q20 12 24 4 Z" fill="#f97316" stroke="#7c2d12" stroke-width="2"/>'
                 '<path d="M24 24 Q30 32 28 36 Q26 42 24 42 Q18 42 18 34 Q18 30 24 24 Z" fill="#fde047"/>')
    return SV.svg(48, 48, fond + corps)


_AMI_COULEURS = {"salon": "#22c55e", "partie": "#f97316", "air": "#38bdf8", "spect": "#94a3b8"}
_AMI_UI = {"salon": "enligne", "partie": "enpartie", "air": "enpartie", "spect": "horsligne"}   # états de svg_ui.icone_ami


def _svg_ami(etat):
    s = _ui("icone_ami", _AMI_UI[etat])
    if s:
        return s
    c = _AMI_COULEURS[etat]
    return SV.svg(48, 48, ('<circle cx="24" cy="24" r="22" fill="%s" stroke="#0f172a" stroke-width="2"/>'
                           '<circle cx="24" cy="18" r="7" fill="#0f172a"/>'
                           '<path d="M11 40 Q24 24 37 40 Z" fill="#0f172a"/>') % c)


def _svg_signaler():
    s = _ui("icone_signaler")
    if s:
        return s
    return SV.svg(48, 48, '<path d="M10 44 V6 h26 l-6 9 6 9 H14" fill="#ef4444" stroke="#7f1d1d" stroke-width="2.5" stroke-linejoin="round"/>')


def _svg_oeil():
    s = _ui("icone_oeil")
    if s:
        return s
    return SV.svg(48, 48, ('<path d="M4 24 Q24 4 44 24 Q24 44 4 24 Z" fill="#e5e7eb" stroke="#111827" stroke-width="2.5"/>'
                           '<circle cx="24" cy="24" r="8" fill="#0ea5e9" stroke="#111827" stroke-width="2"/>'
                           '<circle cx="24" cy="24" r="3.5" fill="#111827"/>'))


# ---------------------------------------------------------------------------
#  Construction du sprite
# ---------------------------------------------------------------------------
def construire(P):
    P.stage.var("soc_cible", 0)
    P.stage.var("soc_etape", 1)
    P.stage.var("soc_mortT", 0)
    P.stage.var("soc_menuK", 0)

    S = Cible(P, "Social")
    S.visible = False
    S.layer = C.CALQUES["Social"]
    S.costumes.append(P.costume("vide", SV.svg_vide(), 2, 2))
    for n in range(1, len(C.EMOTES) + 1):
        S.costumes.append(P.costume("emote%d" % n, _svg_emote(n), 24, 24))
    for n in range(1, len(C.SPRAYS) + 1):
        S.costumes.append(P.costume("spray%d" % n, _svg_spray(n), 24, 24))
    for etat in ["salon", "partie", "air", "spect"]:
        S.costumes.append(P.costume("ami_" + etat, _svg_ami(etat), 24, 24))
    S.costumes.append(P.costume("signaler", _svg_signaler(), 24, 24))
    S.costumes.append(P.costume("oeil", _svg_oeil(), 24, 24))
    texte.installer(S)

    for v in ["k", "i", "r", "n", "t", "d", "a", "mx", "my", "sx", "sy", "dx", "dy", "dist", "ang", "sourisAvant",
              "clicSoc", "survolSoc", "survolAvant", "rangSurvol", "resume", "dernierResume", "chatRel", "emoteRel",
              "sprayRel", "pingRel", "gaucheRel", "droiteRel", "menuR", "infoMode", "infoFin", "fermeture",
              "etatAvant", "ecranAvant", "superAvant", "nom", "libelle", "coul", "trouve", "cineH", "nbDessins",
              "nbLignes", "vitesseCam", "infoAvant", "notifsAvant", "specArme", "sigDepuisPause", "sigEcran"]:
        S.var(v, 0)

    # --- aides Python ---------------------------------------------------------
    def couleur(h, s, b, t=0):
        return couleur_hsbt(h, s, b, t)

    def bande(x1, x2, y, ep):
        return [taille_stylo(ep), stylo_haut(), aller(x1, y), stylo_bas(), aller(x2, y), stylo_haut()]

    def pilule(x1, x2, yc, h):
        """Bande horizontale aux bouts ronds couvrant exactement x1..x2, hauteur h, centrée en yc."""
        return bande(add(x1, h / 2.0) if _dyn(x1) else x1 + h / 2.0,
                     add(x2, -h / 2.0) if _dyn(x2) else x2 - h / 2.0, yc, h)

    def panneau(x1, y1, x2, y2, r=6):
        """Rectangle plein aux coins arrondis (bandes de hauteur 2r). x1, x2 numériques ; y1 peut être une expression."""
        h = y2 - y1 if not _dyn(y1) else None
        blocs = [taille_stylo(2 * r)]
        if h is None:
            raise ValueError("panneau : hauteur statique requise")
        n = max(1, int(math.ceil((h - 2 * r) / (2.0 * r - 1))) + 1)
        for j in range(n):
            y = y1 + r + (h - 2 * r) * j / float(n - 1) if n > 1 else y1 + r
            blocs += [stylo_haut(), aller(x1 + r, y), stylo_bas(), aller(x2 - r, y), stylo_haut()]
        return blocs

    def panneau_dyn(x1, y_top, x2, h, r=4):
        """Panneau dont le haut est une expression (y_top) : h et r statiques."""
        blocs = [taille_stylo(2 * r)]
        n = max(1, int(math.ceil((h - 2 * r) / (2.0 * r - 1))) + 1)
        for j in range(n):
            dy = -(r + (h - 2 * r) * j / float(n - 1)) if n > 1 else -r
            blocs += [stylo_haut(), aller(x1 + r, add(y_top, dy)), stylo_bas(), aller(x2 - r, add(y_top, dy)), stylo_haut()]
        return blocs

    def ecrire(t, x, y, taille_px, coul="blanc", al=0):
        return appel("ecrire", t, x, y, taille_px, coul, al)

    def ecrire_tronque(t, x, y, taille_px, coul, al, lmax):
        return appel("ecrire tronque", t, x, y, taille_px, coul, al, lmax)

    def icone(nom_costume, x, y, pct):
        return [costume(nom_costume), taille(pct), aller(x, y), tampon()]

    def dans_rect(x1, y1, x2, y2):
        return et(et(gt(souris_x(), x1), lt(souris_x(), x2)), et(gt(souris_y(), y1), lt(souris_y(), y2)))

    def jouer_son(nom_son, vol=100):
        return [setv("son_pan", 0), setv("son_volume", vol), diffuser("son " + nom_son)]

    def notification(t, duree=4):
        return [ajouter_liste("Notifications", t), ajouter_liste("NotificationsFin", add(chrono(), duree)),
                si(gt(long_liste("Notifications"), 4), [supprimer("Notifications", 1), supprimer("NotificationsFin", 1)])]

    def ecran_est(*noms):
        cond = eq(V("ecran"), noms[0])
        for e in noms[1:]:
            cond = ou(cond, eq(V("ecran"), e))
        return cond

    def super_est(*noms):
        cond = eq(V("superposition"), noms[0])
        for e in noms[1:]:
            cond = ou(cond, eq(V("superposition"), e))
        return cond

    def tc(nom_touche):
        return touche(C.touche_config(nom_touche))

    def actif_vivant(k):
        return et3(non(eq(k, V("monSlot"))), eq(item("E_actif", k), 1),
                   ou(eq(item("E_etat", k), 1), eq(item("E_etat", k), 3)))

    def changer_ecran(nom_ecran):
        return [setv("ecran", nom_ecran), setv("menu_sale", 1), diffuser("evt changement ecran")]

    def rangee_salon(corps):
        """Boucle sur les emplacements actifs (≠ monSlot) : r = n° de ligne (0..), sy = haut de la ligne."""
        return [setv("r", 0), setv("k", 1),
                repeter(C.NB_JOUEURS, [
                    si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), lt(V("r"), RANGS_MAX)), [
                        setv("sy", sub(RANG_TOP, mul(RANG_H, V("r")))),
                    ] + corps + [changev("r", 1)]),
                    changev("k", 1),
                ])]

    colonne_centrale = item("Profondeur", rnd(div(V("colonnes"), 2)))

    # =======================================================================
    #  1. BARRE SOCIALE (salon)
    # =======================================================================
    S.proc("resume joueurs", [], [
        setv("resume", joins(V("👥 Joueurs"), "/", V("codeSalon"), "/", V("niveau"))), setv("k", 1),
        repeter(C.NB_JOUEURS, [
            setv("resume", joins(V("resume"), "|", item("E_actif", V("k")), item("E_etat", V("k")), item("E_niveau", V("k")),
                                 "/", item("E_nom", V("k")))),
            si(contient("Muets", V("k")), [setv("resume", join(V("resume"), "m"))], [setv("resume", join(V("resume"), "-"))]),
            si(eq(item("E_salon", V("k")), V("codeSalon")), [setv("resume", join(V("resume"), "g"))]),
            changev("k", 1),
        ]),
    ])

    S.proc("survol salon", [], [
        setv("survolSoc", 0),
        si(eq(V("superposition"), "signaler"), [appel("survol signaler")], [
            si(gt(V("soc_menuK"), 0), [
                setv("sy", sub(RANG_TOP, mul(RANG_H, V("menuR")))),
                si(dans_rect(154, add(V("sy"), -35), 234, add(V("sy"), -21)), [setv("survolSoc", 31)]),
                si(dans_rect(154, add(V("sy"), -52), 234, add(V("sy"), -38)), [setv("survolSoc", 32)]),
            ], [
                si(eq(V("infoMode"), 0), rangee_salon([
                    si(dans_rect(218, add(V("sy"), -19), 235, add(V("sy"), -3)), [setv("survolSoc", add(10, V("k"))), setv("rangSurvol", V("r"))]),
                ])),
                si(dans_rect(153, BTN_INV_Y - BTN_H / 2, 232, BTN_INV_Y + BTN_H / 2), [setv("survolSoc", 1)]),
                si(dans_rect(153, BTN_PSEUDO_Y - BTN_H / 2, 232, BTN_PSEUDO_Y + BTN_H / 2), [setv("survolSoc", 2)]),
            ]),
        ]),
    ])

    S.proc("basculer muet", [("n", "n")], [
        si(contient("Muets", A("n")), [supprimer("Muets", num_item("Muets", A("n")))], [ajouter_liste("Muets", A("n"))]),
    ])

    S.proc("clic salon", [], [
        si(eq(V("superposition"), "signaler"), [appel("clic signaler")], [
            si(gt(V("soc_menuK"), 0), [
                si(eq(V("survolSoc"), 31), [appel("basculer muet", V("soc_menuK"))] + jouer_son("clic")),
                si(eq(V("survolSoc"), 32), [setv("soc_cible", V("soc_menuK")), setv("soc_etape", 2), setv("superposition", "signaler")] + jouer_son("clic")),
                setv("soc_menuK", 0), setv("menu_sale", 1),
            ], [
                si(et(gt(V("survolSoc"), 10), lt(V("survolSoc"), 20)), [
                    setv("soc_menuK", sub(V("survolSoc"), 10)), setv("menuR", V("rangSurvol")), setv("menu_sale", 1),
                ] + jouer_son("clic")),
                si(eq(V("survolSoc"), 1), [
                    setv("infoMode", 1), setv("infoFin", add(chrono(), 8)), setv("menu_sale", 1),
                ] + notification(tr("Partage le lien du projet Scratch :", "Share the Scratch project link:"), 6)
                  + notification(tr("tes amis rejoignent ton salon automatiquement", "your friends join your lobby automatically"), 6)
                  + [si(gt(V("codeSalon"), 0), notification(join(tr("Code de salon : ", "Lobby code: "), V("codeSalon")), 6))]
                  + jouer_son("clic")),
                si(eq(V("survolSoc"), 2), [
                    setv("infoMode", 2), setv("infoFin", add(chrono(), 8)), setv("menu_sale", 1),
                ] + notification(joins(tr("Nom d'affichage : ", "Display name: "), V("monNom"), tr(" (pseudo Scratch)", " (Scratch username)")), 6)
                  + notification(join(tr("Niveau de compte ", "Account level "), V("niveau")), 6)
                  + jouer_son("clic")),
                si(et(eq(V("survolSoc"), 0), gt(V("infoMode"), 0)), [setv("infoMode", 0), setv("menu_sale", 1)]),
            ]),
        ]),
    ])

    def bouton_salon(idx, libelle_txt, yc):
        return [si(eq(V("survolSoc"), idx), couleur(14, 75, 92), couleur(200, 55, 50)), pilule(153, 232, yc, BTN_H),
                ecrire(libelle_txt, 192.5, yc - 3.5, 10, "blanc", 1)]

    S.proc("dessiner info", [], [
        si(eq(V("infoMode"), 1), [
            ecrire(tr("Inviter des amis", "Invite friends"), 192.5, 84, 10, "jaune", 1),
            ecrire(tr("Partage le lien du", "Share the link of"), 155, 68, 8, "blanc", 0),
            ecrire(tr("projet Scratch :", "the Scratch project:"), 155, 56, 8, "blanc", 0),
            ecrire(tr("tes amis rejoignent", "your friends join"), 155, 44, 8, "blanc", 0),
            ecrire(tr("ton salon", "your lobby"), 155, 32, 8, "blanc", 0),
            ecrire(tr("automatiquement", "automatically"), 155, 20, 8, "blanc", 0),
            si(gt(V("codeSalon"), 0), [
                ecrire(tr("Code de salon :", "Lobby code:"), 155, 0, 8, "gris", 0),
                ecrire(V("codeSalon"), 192.5, -16, 13, "jaune", 1),
            ], [
                ecrire(tr("Salon public", "Public lobby"), 155, 0, 8, "gris", 0),
            ]),
        ], [
            ecrire(tr("Pseudo Epic", "Epic name"), 192.5, 84, 10, "jaune", 1),
            ecrire(tr("Nom d'affichage :", "Display name:"), 155, 68, 8, "gris", 0),
            ecrire_tronque(V("monNom"), 155, 54, 11, "blanc", 0, 76),
            ecrire(tr("(pseudo Scratch)", "(Scratch username)"), 155, 42, 8, "gris", 0),
            ecrire(tr("Niveau de compte", "Account level"), 155, 22, 8, "gris", 0),
            ecrire(V("niveau"), 155, 6, 13, "jaune", 0),
            ecrire(join(tr("Emplacement ", "Slot "), V("monSlot")), 155, -12, 8, "gris", 0),
        ]),
    ])

    S.proc("dessiner barre", [], [
        changev("nbDessins", 1),
        setv("txt_ombre", 1),
        couleur(62, 35, 16), panneau(SB_X1, SB_Y1, SB_X2, SB_Y2, 6),
        ecrire(joins(tr("Amis en ligne (", "Friends online ("), sub(V("👥 Joueurs"), 1), ")"), 153, 106, 10, "blanc", 0),
        couleur(62, 30, 40), bande(154, 231, 100, 1),
        si(gt(V("infoMode"), 0), [appel("dessiner info")], rangee_salon([
            # état
            si(ou(eq(item("E_etat", V("k")), 5), eq(item("E_etat", V("k")), 9)),
               [setv("nom", "ami_salon"), setv("libelle", tr("Au salon", "In lobby")), setv("coul", "vert")], [
                si(ou(eq(item("E_etat", V("k")), 6), eq(item("E_etat", V("k")), 7)),
                   [setv("nom", "ami_air"), setv("libelle", tr("En l'air", "Airborne")), setv("coul", "cyan")], [
                    si(eq(item("E_etat", V("k")), 4),
                       [setv("nom", "ami_spect"), setv("libelle", tr("Spectateur", "Spectating")), setv("coul", "gris")],
                       [setv("nom", "ami_partie"), setv("libelle", tr("En partie", "In match")), setv("coul", "orange")]),
                ]),
            ]),
            icone(V("nom"), 161, add(V("sy"), -11), 30),
            ecrire_tronque(item("E_nom", V("k")), 170, add(V("sy"), -15), 10, "blanc", 0, 46),
            # bouton « … »
            si(eq(V("survolSoc"), add(10, V("k"))), couleur(14, 70, 90), couleur(62, 25, 40)),
            pilule(219, 234, add(V("sy"), -11), 14),
            ecrire("…", 226.5, add(V("sy"), -12), 11, "blanc", 1),
            # ligne 2 : niveau et état
            ecrire(joins(tr("Niv ", "Lvl "), item("E_niveau", V("k")), " - ", V("libelle")), 157, add(V("sy"), -26), 8, V("coul"), 0),
            # ligne 3 : étiquettes
            si(contient("Muets", V("k")), [ecrire(tr("Masqué", "Muted"), 157, add(V("sy"), -36), 8, "gris", 0)], [
                si(et(gt(V("codeSalon"), 0), eq(item("E_salon", V("k")), V("codeSalon"))),
                   [ecrire(tr("Groupe", "Party"), 157, add(V("sy"), -36), 8, "vert", 0)]),
            ]),
            couleur(62, 30, 28), bande(154, 231, add(V("sy"), -RANG_H + 0.5), 1),
        ]) + [
            si(eq(V("r"), 0), [
                ecrire(tr("Personne en ligne", "Nobody online"), 192.5, 70, 9, "gris", 1),
                ecrire(tr("Invite tes amis !", "Invite your friends!"), 192.5, 56, 9, "gris", 1),
            ]),
        ]),
        bouton_salon(1, tr("Inviter des amis", "Invite friends"), BTN_INV_Y),
        bouton_salon(2, tr("Pseudo Epic", "Epic name"), BTN_PSEUDO_Y),
        # menu « … »
        si(gt(V("soc_menuK"), 0), [
            setv("sy", sub(RANG_TOP, mul(RANG_H, V("menuR")))),
            couleur(62, 30, 30), panneau_dyn(153, add(V("sy"), -16), 235, 40, 4),
            si(eq(V("survolSoc"), 31), couleur(14, 75, 92), couleur(62, 20, 45)), pilule(156, 232, add(V("sy"), -28), 14),
            si(contient("Muets", V("soc_menuK")), [ecrire(tr("Réactiver", "Unmute"), 194, add(V("sy"), -31), 9, "blanc", 1)],
               [ecrire(tr("Masquer", "Mute"), 194, add(V("sy"), -31), 9, "blanc", 1)]),
            si(eq(V("survolSoc"), 32), couleur(14, 75, 92), couleur(0, 60, 55)), pilule(156, 232, add(V("sy"), -45), 14),
            ecrire(tr("Signaler", "Report"), 194, add(V("sy"), -48), 9, "blanc", 1),
        ]),
        si(eq(V("superposition"), "signaler"), [appel("dessiner signaler")]),
    ])

    # =======================================================================
    #  2. CHAT RAPIDE
    # =======================================================================
    def cellule_x1(c):
        return CHAT_X1 + 8 + (CELL_W + 6) * c

    def cellule_y2(j):
        return 54 - CELL_PAS * j

    S.proc("survol chat", [], [
        setv("survolSoc", 0),
        si(dans_rect(100, 61, 141, 81), [setv("survolSoc", 9)]),
        setv("i", 0),
        repeter(2, [
            setv("n", 0),
            repeter(5, [
                si(dans_rect(add(cellule_x1(0), mul(V("i"), CELL_W + 6)), sub(sub(54, mul(V("n"), CELL_PAS)), CELL_H),
                             add(cellule_x1(0) + CELL_W, mul(V("i"), CELL_W + 6)), sub(54, mul(V("n"), CELL_PAS))),
                   [setv("survolSoc", add(add(V("n"), 1), mul(V("i"), 5)))]),
                changev("n", 1),
            ]),
            changev("i", 1),
        ]),
    ])

    S.proc("envoyer chat", [("n", "n")], [
        setv("chat", A("n")), setv("chatSeq", mod(add(V("chatSeq"), 1), 10)),
        ajouter_liste("Chat", join(tr("Toi : ", "You: "), item("ChatRapide", add(A("n"), mul(len(C.CHAT_RAPIDE), V("param_langue")))))),
        ajouter_liste("ChatFin", add(chrono(), 8)),
        si(gt(long_liste("Chat"), 5), [supprimer("Chat", 1), supprimer("ChatFin", 1)]),
    ] + jouer_son("clic", 70))

    S.proc("dessiner panneau chat", [], [
        setv("txt_ombre", 1),
        couleur(62, 40, 14), panneau(CHAT_X1, CHAT_Y1, CHAT_X2, CHAT_Y2, 8),
        couleur(200, 60, 45), bande(CHAT_X1 + 8, CHAT_X2 - 8, 58, 1),
        ecrire(tr("Chat rapide", "Quick chat"), CHAT_X1 + 10, 66, 12, "blanc", 0),
        ecrire(join(tr("Touche ", "Key "), join(C.touche_config("chat"), tr(" : fermer", ": close"))), 20, 67, 8, "gris", 0),
        si(eq(V("survolSoc"), 9), couleur(14, 75, 92), couleur(200, 55, 50)), pilule(100, 141, 71, 20),
        ecrire("👍", 120.5, 65, 13, "blanc", 1),
        setv("i", 0),
        repeter(2, [
            setv("n", 0),
            repeter(5, [
                setv("k", add(add(V("n"), 1), mul(V("i"), 5))),
                si(eq(V("survolSoc"), V("k")), couleur(14, 70, 85), couleur(62, 30, 26)),
                pilule(add(cellule_x1(0), mul(V("i"), CELL_W + 6)), add(cellule_x1(0) + CELL_W, mul(V("i"), CELL_W + 6)),
                       sub(54 - CELL_H / 2.0, mul(V("n"), CELL_PAS)), CELL_H),
                ecrire_tronque(joins(V("k"), ". ", item("ChatRapide", add(V("k"), mul(len(C.CHAT_RAPIDE), V("param_langue"))))),
                               add(cellule_x1(0) + 10, mul(V("i"), CELL_W + 6)), sub(54 - CELL_H + 6, mul(V("n"), CELL_PAS)), 10, "blanc", 0, CELL_W - 16),
                changev("n", 1),
            ]),
            changev("i", 1),
        ]),
    ])

    # zone des derniers messages (en jeu)
    S.proc("dessiner zone chat", [], [
        setv("nbLignes", 0), setv("k", long_liste("Chat")),
        repeter(long_liste("Chat"), [
            si(et(gt(item("ChatFin", V("k")), chrono()), lt(V("nbLignes"), 4)), [changev("nbLignes", 1)]),
            changev("k", -1),
        ]),
        si(gt(V("nbLignes"), 0), [
            couleur(62, 40, 10, 40),
            bande(ZC_X1 + 7, ZC_X2 - 7, add(ZC_Y1 + 3, mul(V("nbLignes"), 6.5)), add(mul(V("nbLignes"), 13), 6)),
            setv("txt_ombre", 0),
            setv("k", long_liste("Chat")), setv("n", 0),
            repeter(long_liste("Chat"), [
                si(et(gt(item("ChatFin", V("k")), chrono()), lt(V("n"), 4)), [
                    si(lt(item("ChatFin", V("k")), add(chrono(), 1.5)), [setv("coul", "gris")], [setv("coul", "blanc")]),
                    ecrire_tronque(item("Chat", V("k")), ZC_X1 + 6, add(ZC_Y1 + 7, mul(V("n"), 13)), 11, V("coul"), 0, ZC_X2 - ZC_X1 - 12),
                    changev("n", 1),
                ]),
                changev("k", -1),
            ]),
            setv("txt_ombre", 1),
        ]),
    ])

    # =======================================================================
    #  3. ROUES (émotes / sprays)
    # =======================================================================
    def angle_secteur(i):
        """Angle (degrés, repère mathématique) du centre du secteur i (1..6) : 1 en haut puis sens horaire."""
        return sub(90, mul(sub(i, 1), 60))

    S.proc("survol roue", [], [
        setv("survolSoc", 0),
        setv("dx", sub(souris_x(), ROUE_CX)), setv("dy", sub(souris_y(), ROUE_CY)),
        setv("dist", sqrt(add(mul(V("dx"), V("dx")), mul(V("dy"), V("dy"))))),
        si(et(gt(V("dist"), ROUE_R - ROUE_EP / 2.0 - 2), lt(V("dist"), ROUE_R + ROUE_EP / 2.0 + 4)), [
            si(lt(absv(V("dx")), 0.0001), [si(gt(V("dy"), 0), [setv("ang", 90)], [setv("ang", 270)])], [
                setv("ang", atan(div(V("dy"), V("dx")))), si(lt(V("dx"), 0), [changev("ang", 180)]),
            ]),
            setv("survolSoc", add(floor(div(mod(add(sub(90, V("ang")), 30), 360), 60)), 1)),
        ]),
    ])

    S.proc("dessiner roue", [("type", "n")], [     # type 1 émotes, 2 sprays
        setv("txt_ombre", 1),
        # voile + disque central
        couleur(62, 40, 12, 35), taille_stylo(2 * ROUE_R + ROUE_EP + 30), ligne(ROUE_CX, ROUE_CY, ROUE_CX, ROUE_CY),
        setv("i", 1),
        repeter(6, [
            setv("a", sub(angle_secteur(V("i")), 26)),
            si(eq(V("survolSoc"), V("i")), couleur(14, 80, 95), couleur(62, 35, 32)),
            taille_stylo(ROUE_EP), stylo_haut(),
            aller(add(ROUE_CX, mul(ROUE_R, cos(V("a")))), add(ROUE_CY, mul(ROUE_R, sin(V("a"))))), stylo_bas(),
            repeter(8, [changev("a", 6.5), aller(add(ROUE_CX, mul(ROUE_R, cos(V("a")))), add(ROUE_CY, mul(ROUE_R, sin(V("a")))))]),
            stylo_haut(),
            changev("i", 1),
        ]),
        # séparateurs
        couleur(62, 40, 10), taille_stylo(3), setv("i", 0),
        repeter(6, [
            setv("a", add(60, mul(V("i"), 60))),
            ligne(add(ROUE_CX, mul(ROUE_R - ROUE_EP / 2.0 - 2, cos(V("a")))), add(ROUE_CY, mul(ROUE_R - ROUE_EP / 2.0 - 2, sin(V("a")))),
                  add(ROUE_CX, mul(ROUE_R + ROUE_EP / 2.0 + 2, cos(V("a")))), add(ROUE_CY, mul(ROUE_R + ROUE_EP / 2.0 + 2, sin(V("a"))))),
            changev("i", 1),
        ]),
        couleur(62, 40, 16), taille_stylo(2 * (ROUE_R - ROUE_EP / 2.0) - 8), ligne(ROUE_CX, ROUE_CY, ROUE_CX, ROUE_CY),
        # icônes
        setv("i", 1),
        repeter(6, [
            setv("a", angle_secteur(V("i"))),
            si(eq(A("type"), 1), [setv("nom", join("emote", item("EmotesEquipees", V("i"))))], [setv("nom", join("spray", V("i")))]),
            icone(V("nom"), add(ROUE_CX, mul(ROUE_R, cos(V("a")))), add(ROUE_CY, mul(ROUE_R, sin(V("a")))), 58),
            changev("i", 1),
        ]),
        # au centre : le nom du secteur survolé, sinon le titre de la roue
        si(gt(V("survolSoc"), 0), [
            si(eq(A("type"), 1), [setv("nom", item("Emotes", add(item("EmotesEquipees", V("survolSoc")), mul(len(C.EMOTES), V("param_langue")))))],
               [setv("nom", item("SprayNoms", V("survolSoc")))]),
            ecrire_tronque(V("nom"), ROUE_CX, ROUE_CY - 4, 10, "blanc", 1, 2 * (ROUE_R - ROUE_EP / 2.0) - 12),
        ], [
            si(eq(A("type"), 1), [setv("libelle", tr("Émotes", "Emotes"))], [setv("libelle", tr("Sprays", "Sprays"))]),
            ecrire(V("libelle"), ROUE_CX, ROUE_CY - 4, 11, "jaune", 1),
        ]),
    ])

    S.proc("faire emote", [("n", "n")], [
        setv("emote", item("EmotesEquipees", A("n"))), setv("emoteSeq", mod(add(V("emoteSeq"), 1), 10)),
        setv("monEmoteFin", add(chrono(), 3)), changev("stat_emotes", 1),
    ] + jouer_son("emote", 90))

    S.proc("poser spray", [("n", "n")], [
        setv("d", sub(colonne_centrale, 0.3)),
        si(gt(V("d"), 2), [setv("d", 2)]), si(lt(V("d"), 0.3), [setv("d", 0.3)]),
        setv("sx", add(V("px"), mul(cos(V("dir")), V("d")))), setv("sy", add(V("py"), mul(sin(V("dir")), V("d")))),
        si(lt(V("sx"), 0.1), [setv("sx", 0.1)]), si(lt(V("sy"), 0.1), [setv("sy", 0.1)]),
        si(gt(V("sx"), C.TAILLE - 0.1), [setv("sx", C.TAILLE - 0.1)]), si(gt(V("sy"), C.TAILLE - 0.1), [setv("sy", C.TAILLE - 0.1)]),
        ajouter_liste("Sprays", joins(C.rembourrer(mul(V("sx"), 100), 4), C.rembourrer(mul(V("sy"), 100), 4), A("n"),
                                       C.rembourrer(mod(rnd(V("dir")), 360), 3))),
        si(gt(long_liste("Sprays"), 10), [supprimer("Sprays", 1)]),
    ] + notification(tr("Spray posé", "Spray placed")) + jouer_son("construction", 80))

    S.proc("dessiner emote en cours", [], [
        setv("txt_ombre", 1),
        setv("nom", item("Emotes", add(V("emote"), mul(len(C.EMOTES), V("param_langue"))))),
        couleur(62, 40, 12, 35), pilule(-90, 90, -126, 22),
        ecrire(join(tr("Tu fais : ", "You do: "), V("nom")), 0, -130, 12, "jaune", 1),
        icone(join("emote", V("emote")), 0, add(-98, mul(sin(mul(chrono(), 600)), 6)), 85),
    ])

    # =======================================================================
    #  4. PING
    # =======================================================================
    S.proc("poser ping", [("x", "n"), ("y", "n")], [
        setv("pingX", floor(A("x"))), setv("pingY", floor(A("y"))),
        si(lt(V("pingX"), 0), [setv("pingX", 0)]), si(lt(V("pingY"), 0), [setv("pingY", 0)]),
        si(gt(V("pingX"), C.TAILLE - 1), [setv("pingX", C.TAILLE - 1)]), si(gt(V("pingY"), C.TAILLE - 1), [setv("pingY", C.TAILLE - 1)]),
        setv("pingSeq", mod(add(V("pingSeq"), 1), 10)), changev("stat_pings", 1),
        # retirer mon ancien ping puis ajouter le nouveau (format k xxxx yyyy eeeeee)
        setv("i", 1), setv("n", long_liste("Pings")),
        repeter(V("n"), [
            si(eq(lettre(1, item("Pings", V("i"))), V("monSlot")), [supprimer("Pings", V("i"))], [changev("i", 1)]),
        ]),
        ajouter_liste("Pings", joins(V("monSlot"), C.rembourrer(mul(V("pingX"), 100), 4), C.rembourrer(mul(V("pingY"), 100), 4),
                                     C.rembourrer(mul(add(chrono(), 20), 10), 6))),
        setv("evt_cible", V("monSlot")), setv("evt_valeur", add(mul(V("pingX"), 100), V("pingY"))), diffuser("evt ping"),
    ] + jouer_son("notification", 70))

    S.proc("ping devant", [], [
        setv("d", sub(colonne_centrale, 0.2)),
        si(gt(V("d"), 8), [setv("d", 8)]), si(lt(V("d"), 0.5), [setv("d", 0.5)]),
        appel("poser ping", add(V("px"), mul(cos(V("dir")), V("d"))), add(V("py"), mul(sin(V("dir")), V("d")))),
    ])

    # =======================================================================
    #  5. SPECTATEUR
    # =======================================================================
    S.proc("choisir cible", [], [
        setv("trouve", 0), setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(et4(eq(V("trouve"), 0), actif_vivant(V("k")), gt(V("monEquipe"), 0), eq(item("E_equipe", V("k")), V("monEquipe"))),
               [setv("trouve", V("k"))]),
            changev("k", 1),
        ]),
        setv("k", 1),
        repeter(C.NB_JOUEURS, [
            si(et(eq(V("trouve"), 0), actif_vivant(V("k"))), [setv("trouve", V("k"))]),
            changev("k", 1),
        ]),
        setv("spectSlot", V("trouve")),
    ])
    S.proc("cible suivante", [("sens", "n")], [
        setv("trouve", 0), setv("k", V("spectSlot")),
        si(lt(V("k"), 1), [setv("k", 1)]),
        repeter(C.NB_JOUEURS, [
            setv("k", add(mod(add(sub(V("k"), 1), A("sens")), C.NB_JOUEURS), 1)),
            si(et(eq(V("trouve"), 0), actif_vivant(V("k"))), [setv("trouve", V("k"))]),
        ]),
        setv("spectSlot", V("trouve")),
    ])
    S.proc("entrer spectateur", [], [
        appel("choisir cible"),
        si(super_est("chat", "emotes", "sprays"), [setv("superposition", "")]),
        setv("hauteur", 0), setv("horizon", 0),
    ] + changer_ecran("spectateur"))

    S.proc("suivre cible", [], [
        si(gt(V("spectSlot"), 0), [si(non(actif_vivant(V("spectSlot"))), [appel("cible suivante", 1)])]),
        si(eq(V("spectSlot"), 0), [appel("choisir cible")]),
        si(gt(V("spectSlot"), 0), [
            changev("px", mul(sub(item("E_x", V("spectSlot")), V("px")), 0.3)),
            changev("py", mul(sub(item("E_y", V("spectSlot")), V("py")), 0.3)),
            setv("d", sub(mod(add(sub(item("E_dir", V("spectSlot")), V("dir")), 540), 360), 180)),
            setv("dir", mod(add(V("dir"), mul(V("d"), 0.3)), 360)),
        ]),
        setv("horizon", 0),
        # flèches : cible précédente / suivante (front descendant)
        si(touche("right arrow"), [si(eq(V("droiteRel"), 0), [setv("droiteRel", 1), appel("cible suivante", 1)] + jouer_son("clic", 50))], [setv("droiteRel", 0)]),
        si(touche("left arrow"), [si(eq(V("gaucheRel"), 0), [setv("gaucheRel", 1), appel("cible suivante", -1)] + jouer_son("clic", 50))], [setv("gaucheRel", 0)]),
        # (le bandeau « SPECTATEUR : nom — ← → changer de joueur » est dessiné par HUD)
    ])

    # =======================================================================
    #  6. CAMÉRA LIBRE (cinéma)
    # =======================================================================
    S.proc("camera libre", [], [
        setv("vitesseCam", V("cineVitesse")),
        si(ou(tc("avancer"), touche("up arrow")), [changev("px", mul(cos(V("dir")), V("vitesseCam"))), changev("py", mul(sin(V("dir")), V("vitesseCam")))]),
        si(ou(tc("reculer"), touche("down arrow")), [changev("px", mul(cos(V("dir")), mul(V("vitesseCam"), -1))), changev("py", mul(sin(V("dir")), mul(V("vitesseCam"), -1)))]),
        si(tc("droite"), [changev("px", mul(sin(V("dir")), V("vitesseCam"))), changev("py", mul(cos(V("dir")), mul(V("vitesseCam"), -1)))]),
        si(tc("gauche"), [changev("px", mul(sin(V("dir")), mul(V("vitesseCam"), -1))), changev("py", mul(cos(V("dir")), V("vitesseCam")))]),
        si(lt(V("px"), 0.5), [setv("px", 0.5)]), si(gt(V("px"), C.TAILLE - 0.5), [setv("px", C.TAILLE - 0.5)]),
        si(lt(V("py"), 0.5), [setv("py", 0.5)]), si(gt(V("py"), C.TAILLE - 0.5), [setv("py", C.TAILLE - 0.5)]),
        si(touche("o"), [setv("cineVitesse", mul(V("cineVitesse"), 1.04)), si(gt(V("cineVitesse"), 1.5), [setv("cineVitesse", 1.5)])]),
        si(touche("l"), [setv("cineVitesse", mul(V("cineVitesse"), 0.96)), si(lt(V("cineVitesse"), 0.02), [setv("cineVitesse", 0.02)])]),
        # montée (sauter) / descente (pioche) : horizon 0..40 px (vue plongeante) — voir l'en-tête
        si(tc("sauter"), [changev("cineH", 2), si(gt(V("cineH"), 40), [setv("cineH", 40)])]),
        si(tc("pioche"), [changev("cineH", -2), si(lt(V("cineH"), 0), [setv("cineH", 0)])]),
        # rotation : flèches et souris vers les bords (comme le joueur)
        si(touche("left arrow"), [changev("dir", mul(3, V("param_sensibilite")))]),
        si(touche("right arrow"), [changev("dir", mul(-3, V("param_sensibilite")))]),
        si(et(lt(absv(souris_x()), 241), lt(absv(souris_y()), 181)), [
            si(gt(souris_x(), 90), [changev("dir", mul(div(sub(90, souris_x()), 30), V("param_sensibilite")))]),
            si(lt(souris_x(), -90), [changev("dir", mul(div(sub(-90, souris_x()), 30), V("param_sensibilite")))]),
        ]),
        setv("dir", mod(V("dir"), 360)),
        # horizon voulu via hauteur (Joueur recalcule horizon = −hauteur avant le rendu ; une hauteur
        # négative n'est pas touchée par sa gravité, une hauteur positive retomberait)
        setv("hauteur", mul(V("cineH"), -1)),
        # texte d'aide
        setv("txt_ombre", 1),
        couleur(62, 40, 12, 35), pilule(-170, 170, -158, 20),
        ecrire(joins(tr("CAMÉRA LIBRE — ", "FREE CAMERA — "), C.touche_config("avancer"), C.touche_config("gauche"), C.touche_config("reculer"),
                     C.touche_config("droite"), tr(" déplacer, O/L vitesse, ", " move, O/L speed, "), C.touche_config("pause"), tr(" menu", " menu")),
               0, -162, 10, "blanc", 1),
        couleur(62, 40, 12, 35), pilule(166, 236, -142, 16),
        ecrire(join(tr("Vitesse ", "Speed "), rnd(mul(V("cineVitesse"), 100))), 201, -145, 9, "blanc", 1),
    ])

    # =======================================================================
    #  7. SIGNALER
    # =======================================================================
    def ligne_sig_y2(idx):   # haut de la ligne idx (expression ou entier, 0..) à l'étape 1
        return sub(SIG_LIGNE_Y2, mul(SIG_LIGNE_PAS, idx)) if _dyn(idx) else SIG_LIGNE_Y2 - SIG_LIGNE_PAS * idx

    def raison_y2(idx):      # haut de la raison idx à l'étape 2 (décalée de 16 px sous la ligne « Joueur : … »)
        return sub(SIG_LIGNE_Y2 - 16, mul(SIG_LIGNE_PAS, idx)) if _dyn(idx) else SIG_LIGNE_Y2 - 16 - SIG_LIGNE_PAS * idx

    S.proc("survol signaler", [], [
        setv("survolSoc", 0),
        si(dans_rect(-40, -85, 40, -65), [setv("survolSoc", 49)]),
        si(eq(V("soc_etape"), 1), [
            setv("r", 0), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), lt(V("r"), 5)), [
                    si(dans_rect(SIG_X1 + 12, sub(ligne_sig_y2(V("r")), SIG_LIGNE_H), SIG_X2 - 12, ligne_sig_y2(V("r"))),
                       [setv("survolSoc", add(40, V("k")))]),
                    changev("r", 1),
                ]),
                changev("k", 1),
            ]),
        ]),
        si(eq(V("soc_etape"), 2), [
            setv("r", 0),
            repeter(len(RAISONS), [
                si(dans_rect(SIG_X1 + 12, sub(raison_y2(V("r")), SIG_LIGNE_H), SIG_X2 - 12, raison_y2(V("r"))),
                   [setv("survolSoc", add(51, V("r")))]),
                changev("r", 1),
            ]),
        ]),
    ])

    S.proc("clic signaler", [], [
        si(eq(V("survolSoc"), 49), [
            setv("superposition", ""), setv("soc_cible", 0), setv("soc_etape", 1), setv("menu_sale", 1),
            # ouvert depuis le menu pause : on y retourne (Menus garde son ecranPrecedent)
            si(et(eq(V("sigDepuisPause"), 1), eq(V("ecran"), V("sigEcran"))), changer_ecran("pause")),
            setv("sigDepuisPause", 0),
        ] + jouer_son("clic")),
        si(et(gt(V("survolSoc"), 40), lt(V("survolSoc"), 47)), [
            setv("soc_cible", sub(V("survolSoc"), 40)), setv("soc_etape", 2), setv("menu_sale", 1),
        ] + jouer_son("clic")),
        si(et(gt(V("survolSoc"), 50), lt(V("survolSoc"), 51 + len(RAISONS))), [
            setv("soc_etape", 3), setv("menu_sale", 1),
            si(non(contient("Muets", V("soc_cible"))), [ajouter_liste("Muets", V("soc_cible"))]),
        ] + notification(join(item("E_nom", V("soc_cible")), tr(" a été signalé et masqué", " was reported and muted"))) + jouer_son("notification", 60)),
    ])

    def bouton_sig(idx_survol, libelle_txt, y2):
        yc = sub(y2, SIG_LIGNE_H / 2.0) if _dyn(y2) else y2 - SIG_LIGNE_H / 2.0
        yb = sub(y2, SIG_LIGNE_H - 6) if _dyn(y2) else y2 - SIG_LIGNE_H + 6
        return [si(eq(V("survolSoc"), idx_survol), couleur(14, 70, 85), couleur(62, 30, 28)),
                pilule(SIG_X1 + 12, SIG_X2 - 12, yc, SIG_LIGNE_H),
                ecrire_tronque(libelle_txt, SIG_X1 + 24, yb, 10, "blanc", 0, SIG_X2 - SIG_X1 - 48)]

    S.proc("dessiner signaler", [], [
        setv("txt_ombre", 1),
        couleur(62, 40, 14), panneau(SIG_X1, SIG_Y1, SIG_X2, SIG_Y2, 8),
        couleur(0, 65, 50), bande(SIG_X1 + 8, SIG_X2 - 8, 64, 1),
        icone("signaler", SIG_X1 + 18, 76, 34),
        ecrire(tr("Signaler un joueur", "Report a player"), SIG_X1 + 30, 71, 12, "blanc", 0),
        si(eq(V("soc_etape"), 1), [
            setv("r", 0), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et3(non(eq(V("k"), V("monSlot"))), eq(item("E_actif", V("k")), 1), lt(V("r"), 5)), [
                    bouton_sig(add(40, V("k")), joins(item("E_nom", V("k")), "  -  ", tr("Niv ", "Lvl "), item("E_niveau", V("k"))), ligne_sig_y2(V("r"))),
                    changev("r", 1),
                ]),
                changev("k", 1),
            ]),
            si(eq(V("r"), 0), [ecrire(tr("Aucun autre joueur connecté", "No other player connected"), 0, 20, 10, "gris", 1)]),
        ]),
        si(eq(V("soc_etape"), 2), [
            ecrire(join(join(tr("Joueur : ", "Player: "), item("E_nom", V("soc_cible"))), tr("  —  Raison :", "  —  Reason:")), SIG_X1 + 14, 44, 9, "gris", 0),
        ] + sum([bouton_sig(51 + j, tr(fr, en), raison_y2(j)) for j, (fr, en) in enumerate(RAISONS)], [])),
        si(eq(V("soc_etape"), 3), [
            ecrire(tr("Signalement enregistré.", "Report saved."), 0, 34, 13, "vert", 1),
            ecrire(tr("Les joueurs signalés sont masqués pour toi", "Reported players are muted for you"), 0, 10, 10, "blanc", 1),
            ecrire(tr("(sanction locale : Scratch n'a pas de modération serveur).", "(local sanction: Scratch has no server moderation)."), 0, -8, 8, "gris", 1),
            ecrire(join(tr("Masqué : ", "Muted: "), item("E_nom", V("soc_cible"))), 0, -30, 10, "orange", 1),
        ]),
        si(eq(V("survolSoc"), 49), couleur(14, 75, 92), couleur(200, 55, 50)), pilule(-40, 40, -75, 20),
        ecrire(tr("Fermer", "Close"), 0, -78.5, 10, "blanc", 1),
    ])

    # =======================================================================
    #  Boucle principale
    # =======================================================================
    def front(nom_touche, rel, action):
        return si(tc(nom_touche), [si(eq(V(rel), 0), [setv(rel, 1)] + action)], [setv(rel, 0)])

    def basculer_super(nom_super):
        return [si(eq(V("superposition"), nom_super), [setv("superposition", "")],
                   [si(super_est("", "chat", "emotes", "sprays"), [setv("superposition", nom_super), setv("fermeture", 0)])])]

    S.proc("entrees jeu", [], [
        # touches (front descendant)
        front("chat", "chatRel", basculer_super("chat") + jouer_son("clic", 50)),
        si(ecran_est("jeu", "prepartie"), [
            front("emotes", "emoteRel", basculer_super("emotes") + jouer_son("clic", 50)),
            front("sprays", "sprayRel", basculer_super("sprays") + jouer_son("clic", 50)),
            front("ping", "pingRel", [si(super_est(""), [appel("ping devant")])]),
        ], [
            setv("emoteRel", 0), setv("sprayRel", 0), setv("pingRel", 0),
            si(super_est("emotes", "sprays"), [setv("superposition", "")]),
        ]),
        # superposition ouverte : survol, dessin, clic
        si(eq(V("fermeture"), 1), [
            si(non(souris_bas()), [setv("fermeture", 0), si(super_est("chat", "emotes", "sprays"), [setv("superposition", "")])]),
        ], [
            si(eq(V("superposition"), "chat"), [
                appel("survol chat"), appel("dessiner panneau chat"),
                si(eq(V("clicSoc"), 1), [
                    si(eq(V("survolSoc"), 9), [appel("envoyer chat", 9), setv("fermeture", 1)], [
                        si(gt(V("survolSoc"), 0), [appel("envoyer chat", V("survolSoc")), setv("fermeture", 1)], [
                            si(non(dans_rect(CHAT_X1, CHAT_Y1, CHAT_X2, CHAT_Y2)), [setv("fermeture", 1)]),
                        ]),
                    ]),
                ]),
            ]),
            si(eq(V("superposition"), "emotes"), [
                appel("survol roue"), appel("dessiner roue", 1),
                si(eq(V("clicSoc"), 1), [
                    si(gt(V("survolSoc"), 0), [appel("faire emote", V("survolSoc")), setv("fermeture", 1)], [
                        si(gt(V("dist"), ROUE_R + ROUE_EP / 2.0 + 4), [setv("fermeture", 1)]),
                    ]),
                ]),
            ]),
            si(eq(V("superposition"), "sprays"), [
                appel("survol roue"), appel("dessiner roue", 2),
                si(eq(V("clicSoc"), 1), [
                    si(gt(V("survolSoc"), 0), [appel("poser spray", V("survolSoc")), setv("fermeture", 1)], [
                        si(gt(V("dist"), ROUE_R + ROUE_EP / 2.0 + 4), [setv("fermeture", 1)]),
                    ]),
                ]),
            ]),
        ]),
    ])

    S.proc("initialiser social", [], [
        setv("sourisAvant", 1), setv("clicSoc", 0), setv("survolSoc", 0), setv("survolAvant", 0), setv("dernierResume", ""),
        setv("chatRel", 1), setv("emoteRel", 1), setv("sprayRel", 1), setv("pingRel", 1), setv("gaucheRel", 1), setv("droiteRel", 1),
        setv("soc_menuK", 0), setv("menuR", 0), setv("infoMode", 0), setv("infoFin", 0), setv("fermeture", 0),
        setv("etatAvant", V("etat")), setv("ecranAvant", V("ecran")), setv("superAvant", V("superposition")),
        setv("soc_cible", 0), setv("soc_etape", 1), setv("soc_mortT", 0), setv("spectSlot", 0), setv("cineH", 0),
        setv("nbDessins", 0), setv("infoAvant", 0), setv("txt_ombre", 1),
        setv("specArme", 0), setv("sigDepuisPause", 0), setv("sigEcran", "jeu"),
        vider("Muets"),
    ])

    S.script(quand_drapeau(), [
        cacher(), aller(0, 0), appel("initialiser social"),
        toujours([
            # --- front descendant de la souris ---
            si(et(souris_bas(), eq(V("sourisAvant"), 0)), [setv("clicSoc", 1)], [setv("clicSoc", 0)]),
            # --- transitions d'état / d'écran / de superposition ---
            si(non(eq(V("etat"), V("etatAvant"))), [
                # passage automatique en spectateur armé UNE fois par mort (etat 2) ou par mise en spectateur (etat 4)
                setv("specArme", 0),
                si(eq(V("etat"), 2), [setv("soc_mortT", chrono()), setv("specArme", 1)]),
                si(eq(V("etat"), 4), [setv("specArme", 1)]),
                setv("etatAvant", V("etat")),
            ]),
            si(non(eq(V("ecran"), V("ecranAvant"))), [
                si(eq(V("ecranAvant"), "cinema"), [setv("hauteur", 0)]),
                si(eq(V("ecran"), "cinema"), [setv("cineH", 0)]),
                si(eq(V("ecran"), "spectateur"), [si(eq(V("spectSlot"), 0), [appel("choisir cible")])]),
                # déjà spectateur / en caméra libre (par Partie, Menus ou moi) : ne plus forcer l'écran (sinon la
                # pause ouverte depuis le spectateur serait aussitôt refermée)
                si(ecran_est("spectateur", "cinema"), [setv("specArme", 0)]),
                # superpositions périmées : mes panneaux ne survivent pas à un changement d'écran
                si(super_est("chat", "emotes", "sprays"), [
                    si(non(ecran_est("jeu", "prepartie", "spectateur")), [setv("superposition", "")]),
                ]),
                si(eq(V("superposition"), "signaler"), [
                    si(ecran_est("fin", "bus", "parachute", "salon", "matchmaking", "chargement", "connexion"),
                       [setv("superposition", ""), setv("soc_cible", 0), setv("soc_etape", 1)]),
                ]),
                setv("soc_menuK", 0), setv("infoMode", 0), setv("fermeture", 0),
                setv("ecranAvant", V("ecran")),
            ]),
            si(non(eq(V("superposition"), V("superAvant"))), [
                si(eq(V("superposition"), "signaler"), [
                    si(gt(V("soc_cible"), 0), [setv("soc_etape", 2)], [setv("soc_etape", 1)]),
                    setv("soc_menuK", 0), setv("menu_sale", 1),
                    # ouvert depuis le menu pause : Menus (calque 88) redessine la pause APRÈS moi à chaque image et
                    # recouvrirait le panneau → on revient sur l'écran 3D sous-jacent le temps du signalement,
                    # puis à la pause quand on ferme (voir « clic signaler »)
                    si(eq(V("ecran"), "pause"), [
                        setv("sigDepuisPause", 1), setv("sigEcran", "jeu"),
                        si(ou(eq(V("ecranPrecedent"), "spectateur"), eq(V("ecranPrecedent"), "cinema")),
                           [setv("sigEcran", V("ecranPrecedent"))]),
                    ] + changer_ecran(V("sigEcran"))),
                ]),
                si(eq(V("superAvant"), "signaler"), [setv("menu_sale", 1), setv("sigDepuisPause", 0)]),
                setv("superAvant", V("superposition")),
            ]),
            # --- spectateur automatique après la mort (une seule fois par mort) ---
            si(et(eq(V("specArme"), 1), ecran_est("jeu", "pause")), [
                si(ou(et3(eq(V("etat"), 2), non(eq(V("mode"), 5)), gt(chrono(), add(V("soc_mortT"), 3))), eq(V("etat"), 4)),
                   [setv("specArme", 0), appel("entrer spectateur")]),
            ]),
            # --- salon : barre sociale ---
            si(eq(V("ecran"), "salon"), [
                appel("resume joueurs"),
                si(non(eq_txt(V("resume"), V("dernierResume"))), [setv("dernierResume", V("resume")), setv("menu_sale", 1)]),
                si(et(gt(V("infoMode"), 0), gt(chrono(), V("infoFin"))), [setv("infoMode", 0), setv("menu_sale", 1)]),
                appel("survol salon"),
                si(non(eq(V("survolSoc"), V("survolAvant"))), [
                    setv("survolAvant", V("survolSoc")), setv("menu_sale", 1),
                    si(gt(V("survolSoc"), 0), jouer_son("survol", 40)),
                ]),
                si(eq(V("menu_rafraichi"), 1), [appel("dessiner barre")]),
                si(et(eq(V("clicSoc"), 1), ou(dans_rect(SB_X1, SB_Y1, SB_X2, SB_Y2), ou(gt(V("soc_menuK"), 0), eq(V("superposition"), "signaler")))),
                   [appel("clic salon")]),
            ], [
                # --- écrans de jeu ---
                si(ecran_est("jeu", "prepartie", "spectateur"), [
                    appel("dessiner zone chat"),
                    si(et(ecran_est("jeu", "prepartie"), gt(V("monEmoteFin"), chrono())), [appel("dessiner emote en cours")]),
                    si(non(eq(V("superposition"), "signaler")), [appel("entrees jeu")]),
                ], [
                    setv("chatRel", 0), setv("emoteRel", 0), setv("sprayRel", 0), setv("pingRel", 0),
                ]),
                si(eq(V("ecran"), "spectateur"), [appel("suivre cible")]),
                si(eq(V("ecran"), "cinema"), [si(non(eq(V("superposition"), "signaler")), [appel("camera libre")])]),
                # carte plein écran : clic → point de rassemblement
                si(et(eq(V("ecran"), "carte"), eq(V("clicSoc"), 1)), [
                    si(dans_rect(-160, -160, 160, 160), [
                        appel("poser ping", div(add(souris_x(), 160), 10), div(add(souris_y(), 160), 10)),
                    ] + notification(tr("Point de rassemblement posé", "Rally point placed"))),
                ]),
                # signalement sur un écran 3D (ouvert par Menus depuis la pause) : redessiné à chaque image
                si(et(eq(V("superposition"), "signaler"), ecran_est("jeu", "prepartie", "pause", "spectateur", "cinema", "fin")), [
                    appel("survol signaler"), appel("dessiner signaler"),
                    si(eq(V("clicSoc"), 1), [appel("clic signaler")]),
                ]),
            ]),
            si(souris_bas(), [setv("sourisAvant", 1)], [setv("sourisAvant", 0)]),
        ]),
    ])

    S.script(quand_message("evt nouvelle manche"), [
        setv("soc_menuK", 0), setv("fermeture", 0), setv("spectSlot", 0), setv("soc_mortT", 0),
        setv("specArme", 0), setv("sigDepuisPause", 0),
        si(super_est("chat", "emotes", "sprays"), [setv("superposition", "")]),
    ])
