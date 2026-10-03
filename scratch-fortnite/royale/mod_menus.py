# -*- coding: utf-8 -*-
"""
MODULE MENUS — sprite « Menus » (calque CALQUES["Menus"]).

Tous les écrans hors jeu et les menus superposés :
  connexion, salon (7 onglets : accueil, passe, boutique, casier, quetes, carriere, parametres),
  matchmaking, chargement, pause (+ paramètres par-dessus), fin (victoire / défaite),
  touches « pause » et « carte ».

Principes de dessin
-------------------
- Fonds, panneaux et boutons : costumes SVG rectangulaires tamponnés (un costume par taille et couleur,
  fabriqués à la génération : `_boite(w, h, couleur, rayon)`), surlignés par l'effet luminosité au survol.
- Icônes : costumes normalisés dans une boîte carrée (`_icone`), issus de royale.svg_ui quand le module
  existe (import protégé + getattr), sinon d'un SVG de remplacement local. À la régénération, les vraies
  icônes sont prises automatiquement.
- Textes : moteur royale.texte (texte.installer sur ce sprite), FR/EN via contrat.tr.
- Barres de progression et séparateurs : stylo (lignes épaisses).
- Un menu plein écran n'est redessiné que si menu_sale = 1, si le survol change ou si sa « signature »
  de données change ; les superpositions sur le 3D (pause, fin) sont redessinées à chaque image.
- Boutons : pendant le dessin, chaque bouton est enregistré dans les listes locales menu_bx1/by1/bx2/by2/bid ;
  le survol est recalculé quand la souris bouge, le clic (front descendant de « souris pressée ») cherche le
  bouton sous la souris et appelle le bloc « action » avec son identifiant.

- Signalement (superposition = "signaler", panneau central x ∈ [−130, 130], y ∈ [−90, 90] dessiné par Social AVANT
  Menus dans l'image) : sur l'écran pause, Menus ne dessine qu'un voile sombre troué et aucun bouton (clics et
  touche pause ignorés) ; dans le salon, aucun bouton n'est trouvé sous la souris quand elle est sur le panneau.

Variables globales privées (préfixe menu_) : menu_survolId (identifiant du bouton survolé, pour Social).
Diffusions émises : evt changement ecran, sauvegarde charger, sauvegarde generer, createur definir,
boutique acheter, casier equiper, quete reclamer, quete partager, son clic, son survol.
"""
import re

from .dsl import *  # noqa: F401,F403
from . import contrat as C
from . import svg as S
from . import texte

ORDRE = 70       # après Systemes/Social : leurs listes globales (sys_*) sont connues
V = Var
A = Arg

# ===========================================================================
#  Accès protégé à royale.svg_ui + SVG de remplacement
# ===========================================================================
try:
    from . import svg_ui as _UI
except Exception:  # module écrit en parallèle : pas encore disponible
    _UI = None


def _svg_ok(s):
    return isinstance(s, str) and s.lstrip().startswith("<svg")


def _ui(nom, *args, **kw):
    """SVG de royale.svg_ui.<nom>(*args) si disponible, sinon un SVG de remplacement local."""
    if _UI is not None:
        f = getattr(_UI, nom, None)
        if callable(f):
            try:
                s = f(*args, **kw)
                if _svg_ok(s):
                    return s
            except Exception:
                pass
    return _secours(nom, *args, **kw)


_PAL = ["#f87171", "#fb923c", "#facc15", "#4ade80", "#22d3ee", "#60a5fa", "#a78bfa", "#f472b6", "#e5e7eb", "#fde68a"]


def _teinte(n):
    return _PAL[(int(n) - 1) % len(_PAL)]


def _secours(nom, *args, **kw):
    """Icônes simples de remplacement (mêmes signatures que svg_ui)."""
    g = S.svg
    a = list(args) + [kw[k] for k in kw]
    n = int(a[0]) if a and isinstance(a[0], (int, float)) else 1
    if nom == "logo":
        return g(300, 90, '<rect x="4" y="10" width="292" height="70" rx="16" fill="#111827" stroke="#facc15" stroke-width="4"/>'
                 '<text x="150" y="60" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="40" fill="#facc15" '
                 'stroke="#78350f" stroke-width="2" paint-order="stroke">ROYALE 3D</text>')
    if nom == "fond_ecran":
        variante = a[0] if a else "salon"
        couleurs = {"connexion": ("#0f172a", "#1e3a8a"), "salon": ("#111827", "#1f2937"), "matchmaking": ("#0b1021", "#312e81"),
                    "chargement": ("#0b1021", "#111827"), "victoire": ("#78350f", "#b45309"), "fin": ("#111827", "#374151")}
        c1, c2 = couleurs.get(variante, ("#111827", "#1f2937"))
        return g(480, 360, '<defs><linearGradient id="f" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="%s"/>'
                 '<stop offset="1" stop-color="%s"/></linearGradient></defs><rect width="480" height="360" fill="url(#f)"/>'
                 '<circle cx="400" cy="60" r="140" fill="#ffffff" fill-opacity="0.04"/><circle cx="60" cy="320" r="120" fill="#ffffff" fill-opacity="0.04"/>'
                 % (c1, c2))
    if nom == "personnage":
        skin = int(a[0]) if a else 1
        return S.svg_personnage(_teinte(skin))
    if nom == "icone_onglet":
        o = a[0] if a else "accueil"
        formes = {
            "accueil": '<path d="M4 16 L16 5 L28 16 V28 H19 V20 H13 V28 H4 Z" fill="#fff"/>',
            "passe": '<polygon points="16,3 20,12 30,13 22,19 25,29 16,24 7,29 10,19 2,13 12,12" fill="#facc15"/>',
            "boutique": '<path d="M6 10 H26 L24 29 H8 Z" fill="#60a5fa"/><path d="M11 10 a5 5 0 0 1 10 0" fill="none" stroke="#fff" stroke-width="3"/>',
            "casier": '<rect x="7" y="4" width="18" height="24" rx="3" fill="#a78bfa"/><rect x="10" y="8" width="12" height="6" fill="#111"/><rect x="10" y="17" width="12" height="6" fill="#111"/>',
            "quetes": '<rect x="6" y="4" width="20" height="24" rx="3" fill="#fff"/><path d="M9 11 h14 M9 16 h14 M9 21 h9" stroke="#111" stroke-width="2.5"/>',
            "carriere": '<rect x="4" y="18" width="6" height="10" fill="#4ade80"/><rect x="13" y="10" width="6" height="18" fill="#4ade80"/><rect x="22" y="4" width="6" height="24" fill="#4ade80"/>',
            "parametres": '<circle cx="16" cy="16" r="9" fill="none" stroke="#e5e7eb" stroke-width="5" stroke-dasharray="5 3"/><circle cx="16" cy="16" r="3" fill="#e5e7eb"/>',
        }
        return g(32, 32, formes.get(o, formes["accueil"]))
    if nom == "jeton":
        return g(32, 32, '<circle cx="16" cy="16" r="14" fill="#facc15" stroke="#b45309" stroke-width="3"/><text x="16" y="22" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="16" fill="#78350f">J</text>')
    if nom == "etoile":
        return g(32, 32, '<polygon points="16,2 20,12 31,13 22,20 25,31 16,25 7,31 10,20 1,13 12,12" fill="#facc15" stroke="#b45309" stroke-width="2"/>')
    if nom == "cadenas":
        return g(32, 32, '<rect x="7" y="14" width="18" height="15" rx="3" fill="#9ca3af"/><path d="M11 14 V10 a5 5 0 0 1 10 0 V14" fill="none" stroke="#9ca3af" stroke-width="3"/><circle cx="16" cy="21" r="2.5" fill="#111"/>')
    if nom == "coche":
        return g(32, 32, '<circle cx="16" cy="16" r="14" fill="#16a34a"/><polyline points="8,16 14,22 24,10" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" stroke-linejoin="round"/>')
    if nom == "croix":
        return g(32, 32, '<circle cx="16" cy="16" r="14" fill="#dc2626"/><path d="M10 10 L22 22 M22 10 L10 22" stroke="#fff" stroke-width="4" stroke-linecap="round"/>')
    if nom == "fleche":
        d = a[0] if a else "droite"
        rot = {"droite": 0, "bas": 90, "gauche": 180, "haut": 270}.get(d, 0)
        return g(32, 32, '<polygon points="10,6 24,16 10,26" fill="#fff" transform="rotate(%d 16 16)"/>' % rot)
    if nom == "icone_quete":
        t = a[0] if a else 1
        c = {1: "#4ade80", 2: "#60a5fa", 3: "#f472b6"}.get(int(t) if str(t).isdigit() else 1, "#4ade80")
        return g(32, 32, '<rect x="5" y="3" width="22" height="26" rx="4" fill="%s"/><path d="M10 11 h12 M10 17 h12 M10 23 h7" stroke="#111" stroke-width="2.5"/>' % c)
    if nom == "icone_succes":
        return g(32, 32, '<circle cx="16" cy="13" r="10" fill="#facc15" stroke="#b45309" stroke-width="2"/><path d="M10 22 L8 31 L16 27 L24 31 L22 22" fill="#dc2626"/>')
    if nom == "medaille":
        r = a[0] if a else 1
        c = {1: "#facc15", 2: "#d1d5db", 3: "#d97706"}.get(int(r) if str(r).isdigit() else 1, "#d1d5db")
        return g(60, 80, '<path d="M18 2 L30 30 L42 2 Z" fill="#2563eb"/><path d="M30 2 L30 30 L42 2 Z" fill="#dc2626"/>'
                 '<circle cx="30" cy="52" r="24" fill="%s" stroke="#78350f" stroke-width="4"/>'
                 '<polygon points="30,36 35,47 47,48 38,56 41,68 30,62 19,68 22,56 13,48 25,47" fill="#fff" fill-opacity="0.7"/>' % c)
    if nom == "division":
        return g(40, 40, '<polygon points="20,2 38,12 32,36 8,36 2,12" fill="%s" stroke="#111" stroke-width="2"/>'
                 '<text x="20" y="27" text-anchor="middle" font-family="Sans Serif" font-weight="bold" font-size="16" fill="#111">%d</text>' % (_teinte(n), n))
    if nom == "pioche":
        return g(40, 40, '<rect x="18" y="8" width="5" height="30" rx="2" fill="#92400e" transform="rotate(30 20 20)"/>'
                 '<path d="M6 12 Q20 2 34 12 Q20 8 6 12 Z" fill="%s" stroke="#111" stroke-width="1.5" transform="rotate(30 20 20)"/>' % _teinte(n))
    if nom == "planeur":
        return g(40, 40, '<path d="M4 18 Q20 2 36 18 Z" fill="%s" stroke="#111" stroke-width="1.5"/><path d="M8 18 L20 34 L32 18" fill="none" stroke="#e5e7eb" stroke-width="2"/>' % _teinte(n))
    if nom == "spray":
        return g(40, 40, '<circle cx="20" cy="20" r="16" fill="%s"/><circle cx="14" cy="16" r="4" fill="#fff" fill-opacity="0.6"/><circle cx="24" cy="24" r="6" fill="#111" fill-opacity="0.25"/>' % _teinte(n))
    if nom == "emote":
        return g(40, 40, '<circle cx="20" cy="20" r="16" fill="%s" stroke="#111" stroke-width="1.5"/><circle cx="14" cy="16" r="2.5" fill="#111"/><circle cx="26" cy="16" r="2.5" fill="#111"/><path d="M12 24 Q20 32 28 24" fill="none" stroke="#111" stroke-width="2.5" stroke-linecap="round"/>' % _teinte(n))
    if nom == "banniere":
        return g(40, 40, '<path d="M8 2 H32 V38 L20 30 L8 38 Z" fill="%s" stroke="#111" stroke-width="1.5"/><circle cx="20" cy="15" r="5" fill="#fff" fill-opacity="0.8"/>' % _teinte(n))
    if nom == "icone_haut_parleur":
        niveau = n
        ondes = "".join('<path d="M%d 12 q6 8 0 16" fill="none" stroke="#fff" stroke-width="2.5"/>' % (18 + 5 * k) for k in range(min(3, max(0, (niveau + 33) // 34))))
        return g(40, 40, '<path d="M6 15 H12 L20 8 V32 L12 25 H6 Z" fill="#e5e7eb"/>' + ondes)
    if nom == "icone_signaler":
        return g(32, 32, '<rect x="7" y="3" width="4" height="26" fill="#e5e7eb"/><path d="M11 4 H27 L22 11 L27 18 H11 Z" fill="#dc2626"/>')
    if nom == "icone_oeil":
        return g(32, 32, '<path d="M2 16 Q16 2 30 16 Q16 30 2 16 Z" fill="#e5e7eb"/><circle cx="16" cy="16" r="5" fill="#111"/>')
    if nom == "carte_complete":
        e = float(a[0]) if a else 5
        taille_px = int(C.TAILLE * e)
        couleurs = {1: "#9ca3af", 2: "#b45309", 3: "#b91c1c", 4: "#64748b"}
        cases = []
        for y in range(C.TAILLE):
            for x in range(C.TAILLE):
                v = C.cellule_base(x, y)
                if v:
                    cases.append('<rect x="%g" y="%g" width="%g" height="%g" fill="%s"/>' % (x * e, (C.TAILLE - 1 - y) * e, e, e, couleurs[v]))
        return g(taille_px, taille_px, '<rect width="%d" height="%d" fill="#365314"/>' % (taille_px, taille_px) + "".join(cases))
    if nom == "icone_objet":
        return g(32, 32, '<rect x="4" y="8" width="24" height="16" rx="3" fill="%s" stroke="#111" stroke-width="1.5"/>' % _teinte(n))
    # défaut : pastille colorée
    return g(32, 32, '<circle cx="16" cy="16" r="13" fill="#6b7280"/>')


# ===========================================================================
#  Costumes : rectangles (fonds, boutons) et icônes normalisées
# ===========================================================================
_RE_ATTR = re.compile(r'\s(width|height)="([\d.]+)(px)?"')
_RE_VIEWBOX = re.compile(r'viewBox="\s*([-\d.]+)[ ,]+([-\d.]+)[ ,]+([\d.]+)[ ,]+([\d.]+)"')


def _dims(svg_src):
    """(x0, y0, largeur, hauteur) de la racine d'un SVG."""
    m = _RE_VIEWBOX.search(svg_src)
    if m:
        return float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4))
    d = {}
    racine = svg_src[:svg_src.index(">") + 1]
    for k, v, _ in _RE_ATTR.findall(racine):
        d[k] = float(v)
    return 0.0, 0.0, d.get("width", 32.0), d.get("height", 32.0)


def _normaliser(svg_src, boite):
    """Recadre un SVG dans une boîte carrée de `boite` px (proportions conservées, centré)."""
    x0, y0, w, h = _dims(svg_src)
    debut = svg_src.index(">", svg_src.index("<svg")) + 1
    fin = svg_src.rindex("</svg>")
    interieur = svg_src[debut:fin]
    s = boite / float(max(w, h, 1))
    tx = (boite - w * s) / 2.0 - x0 * s
    ty = (boite - h * s) / 2.0 - y0 * s
    return ('<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="%d" height="%d" viewBox="0 0 %d %d">'
            '<g transform="translate(%.2f %.2f) scale(%.4f)">%s</g></svg>' % (boite, boite, boite, boite, tx, ty, s, interieur))


class _Costumes:
    """Fabrique et mémorise les costumes du sprite Menus (noms préfixés « m_ »)."""

    def __init__(self, cible):
        self.cible = cible
        self.noms = set()

    def ajouter(self, nom, svg_src, cx, cy):
        if nom in self.noms:
            return nom
        self.noms.add(nom)
        self.cible.costume_svg(nom, svg_src, cx, cy)
        return nom

    def boite(self, w, h, couleur, rayon=6, bord=None, epaisseur=0, opacite=1.0):
        """Rectangle plein w×h (centre au milieu). Nom : m_r_<w>x<h>_<couleur>_<rayon>[_<bord>]."""
        w, h = int(round(w)), int(round(h))
        nom = "m_r_%dx%d_%s_%d%s%s" % (w, h, couleur.lstrip("#"), rayon, ("_" + bord.lstrip("#")) if bord else "",
                                       ("_o%d" % int(opacite * 100)) if opacite < 1 else "")
        return self.ajouter(nom, S.svg_rect(w, h, couleur, rayon, opacite, bord, epaisseur), w / 2.0, h / 2.0)

    def icone(self, nom, svg_src, boite):
        """Icône normalisée dans une boîte carrée de `boite` px (centre au milieu)."""
        return self.ajouter(nom, _normaliser(svg_src, boite), boite / 2.0, boite / 2.0)

    def plein_ecran(self, nom, svg_src):
        return self.ajouter(nom, svg_src, 240, 180)


# couleurs des fonds / boutons
FOND = "#0f172a"           # fond général
PANNEAU = "#1e293b"        # panneaux
PANNEAU_CLAIR = "#334155"  # cartes
BOUTON = "#2563eb"         # bouton principal (bleu)
BOUTON_SOMBRE = "#475569"  # bouton secondaire
JAUNE = "#facc15"          # JOUER
VERT = "#16a34a"
ROUGE = "#dc2626"
OR = "#f59e0b"
SOCIAL = "#0b1120"


# ===========================================================================
#  Aides Python (retournent des listes de blocs)
# ===========================================================================
def tr(fr, en=None):
    return C.tr(fr, en)


def lignes_fr_en(paires):
    """[(fr, en), ...] -> liste de reporters traduits."""
    return [tr(fr, en) for fr, en in paires]


ASTUCES = [
    ("Tiens « interagir » (E) près d'un coffre pour l'ouvrir.", "Hold “interact” (E) near a chest to open it."),
    ("La pioche (F) récolte bois, pierre et métal.", "The pickaxe (F) harvests wood, stone and metal."),
    ("Construis un mur (B) pour te mettre à couvert.", "Build a wall (B) to take cover."),
    ("Le surbouclier se recharge après 6 s sans dégâts.", "Overshield recharges after 6 s without damage."),
    ("La tempête ignore les boucliers : reste dans la zone !", "The storm ignores shields: stay in the zone!"),
    ("Un coéquipier à terre peut être réanimé en 5 s.", "A downed teammate can be revived in 5 s."),
    ("Les balises de redéploiement ramènent un allié mort.", "Reboot beacons bring back a dead ally."),
    ("Le fusil à pompe fait plus de dégâts de près.", "The shotgun deals more damage up close."),
    ("Vise (C) avec le sniper pour zoomer.", "Aim (C) with the sniper to zoom in."),
    ("Termine des quêtes pour gagner de l'XP et des étoiles.", "Complete quests to earn XP and stars."),
]
NB_ASTUCES = len(ASTUCES)

# Onglets du salon : (nom, FR, EN)
ONGLETS = [("accueil", "Découvrir", "Discover"), ("passe", "Passe", "Battle Pass"), ("boutique", "Boutique", "Shop"),
           ("casier", "Casier", "Locker"), ("quetes", "Quêtes", "Quests"), ("carriere", "Carrière", "Career"),
           ("parametres", "Paramètres", "Settings")]
# Types de cosmétiques : (code, FR, EN, nombre d'objets)
COSMETIQUES = [("skin", "Tenue", "Outfit", 10), ("pioche", "Pioche", "Pickaxe", 9), ("planeur", "Planeur", "Glider", 9),
               ("spray", "Spray", "Spray", 6), ("emote", "Émote", "Emote", 6), ("banniere", "Bannière", "Banner", 10)]
CATEGORIES_CASIER = [("skin", "Tenues", "Outfits"), ("pioche", "Pioches", "Pickaxes"), ("planeur", "Planeurs", "Gliders"),
                     ("spray", "Sprays", "Sprays"), ("emote", "Émotes", "Emotes"), ("banniere", "Bannières", "Banners")]
ACTIONS_TOUCHES = [("avancer", "Avancer", "Forward"), ("reculer", "Reculer", "Back"), ("gauche", "Gauche", "Left"),
                   ("droite", "Droite", "Right"), ("sauter", "Sauter", "Jump"), ("construire", "Construire", "Build"),
                   ("interagir", "Interagir", "Interact"), ("recharger", "Recharger", "Reload"), ("carte", "Carte", "Map"),
                   ("pause", "Pause", "Pause"), ("chat", "Chat", "Chat"), ("emotes", "Émotes", "Emotes"),
                   ("sprays", "Sprays", "Sprays"), ("ping", "Marqueur", "Ping"), ("pioche", "Pioche", "Pickaxe"),
                   ("materiau", "Matériau", "Material"), ("edition", "Édition", "Edit"), ("sprint", "Sprint", "Sprint"),
                   ("viser", "Viser", "Aim")]
assert [a for a, _, _ in ACTIONS_TOUCHES] == C.TOUCHES
TOUCHES_CANDIDATES = list("abcdefghijklmnopqrstuvwxyz0123456789") + ["space", "up arrow", "down arrow", "left arrow", "right arrow"]
REGIONS = [("Europe (Scratch Cloud)", "Europe (Scratch Cloud)"), ("Amérique", "America"), ("Asie", "Asia")]
DALTONISME = [("Aucun", "None"), ("Protanopie", "Protanopia"), ("Deutéranopie", "Deuteranopia"), ("Tritanopie", "Tritanopia")]
QUALITES = [("Basse", "Low"), ("Moyenne", "Medium"), ("Épique", "Epic")]
CONFIDENTIALITES = [("Public", "Public"), ("Amis", "Friends"), ("Privé", "Private")]
SECTIONS = [("jeu", "Jeu", "Game"), ("commandes", "Commandes", "Controls"), ("video", "Vidéo", "Video"),
            ("audio", "Audio", "Audio"), ("acces", "Accessibilité", "Accessibility"), ("compte", "Compte", "Account")]

# Zones de l'écran salon
ZT_Y1, ZT_Y2 = 146, 180                 # barre d'onglets
ZC_X1, ZC_X2, ZC_Y1, ZC_Y2 = -236, 144, -106, 142   # contenu central
ZS_X1, ZS_X2, ZS_Y1, ZS_Y2 = 150, 235, -150, 120    # barre sociale (module Social)
SIG_X1, SIG_X2, SIG_Y1, SIG_Y2 = -130, 130, -90, 90  # panneau central de signalement (dessiné par Social, superposition "signaler")


def centre_y(cy, taille_txt):
    """Ligne de base pour centrer verticalement des majuscules de `taille_txt` autour de cy."""
    return cy - 0.35 * taille_txt


class Menus:
    """Générateur du sprite Menus."""

    def __init__(self, P):
        self.P = P
        M = Cible(P, "Menus")
        self.M = M
        M.costumes = [P.costume("vide", S.svg_vide(), 2, 2)]
        M.visible = False
        M.layer = C.CALQUES["Menus"]
        self.K = _Costumes(M)
        texte.installer(M)
        for v in ["survolId", "clicId", "sourisAvant", "sx0", "sy0", "signature", "ox", "pauseAvant", "carteAvant",
                  "listeModes", "sousOnglet", "section", "pagePasse", "categorie", "caseEmote", "pauseParam",
                  "attenteTouche", "tCompte", "tChargement", "astuce", "tAstuce", "vueClassement", "k", "i", "j", "n",
                  "x", "y", "p", "champ", "txt", "txt2", "tmp", "cx", "cy", "tot", "nb", "trouve", "parFrame", "idx",
                  "survolN", "ancienId", "touchePressee", "styleDispo", "estSale", "ci", "cj", "cc", "nbDessins", "ecranAvant"]:
            M.var(v, 0)
        for l in ["menu_bx1", "menu_by1", "menu_bx2", "menu_by2", "menu_bid", "menu_ordre"]:
            M.liste(l, [])
        P.stage.var("menu_survolId", "")
        self.icones_prets = set()
        self._costumes_fixes()
        self._procs_base()

    # ----------------------------------------------------------------------
    #  Costumes
    # ----------------------------------------------------------------------
    def _costumes_fixes(self):
        K = self.K
        for variante in ["connexion", "salon", "matchmaking", "chargement", "victoire", "fin"]:
            K.plein_ecran("m_fond_" + variante, _ui("fond_ecran", variante))
        # logo normalisé dans une boîte 300×300 pour une taille prévisible
        K.icone("m_logo_b", _ui("logo"), 300)
        for nom in ["accueil", "passe", "boutique", "casier", "quetes", "carriere", "parametres"]:
            K.icone("m_ong_" + nom, _ui("icone_onglet", nom), 32)
        for nom in ["jeton", "etoile", "cadenas", "coche", "croix", "icone_succes", "icone_signaler", "icone_oeil"]:
            K.icone("m_" + nom, _ui(nom), 32)
        for d in ["gauche", "droite", "haut", "bas"]:
            K.icone("m_fleche_" + d, _ui("fleche", d), 32)
        for t in (1, 2, 3):
            K.icone("m_quete_%d" % t, _ui("icone_quete", t), 32)
            K.icone("m_medaille_%d" % t, _ui("medaille", t), 100)
        for n in range(0, 4):
            K.icone("m_hp_%d" % n, _ui("icone_haut_parleur", n * 34), 32)
        for n in range(1, 11):
            K.icone("m_division_%d" % n, _ui("division", n), 32)
        # icônes de cosmétiques : m_ic_<type>_<id>
        for code, _, _, nb in COSMETIQUES:
            for n in range(1, nb + 1):
                if code == "skin":
                    K.icone("m_ic_skin_%d" % n, _ui("personnage", n, "debout"), 32)
                else:
                    K.icone("m_ic_%s_%d" % (code, n), _ui(code, n), 32)
        K.icone("m_ic_jetons", _ui("jeton"), 32)
        K.icone("m_ic_style", _ui("etoile"), 32)
        K.icone("m_ic_inconnu", S.svg(32, 32, '<rect x="4" y="4" width="24" height="24" rx="5" fill="#64748b"/>'
                                                '<text x="16" y="23" text-anchor="middle" font-family="Sans Serif" font-size="18" fill="#fff">?</text>'), 32)
        # personnages grands (aperçu) : m_perso_<skin>_<style>
        for n in range(1, 11):
            K.icone("m_perso_%d_0" % n, _ui("personnage", n, "debout"), 120)
            K.icone("m_perso_%d_1" % n, _ui("personnage", n, "debout", 1), 120)
        K.icone("m_carte", _ui("carte_complete", 5), 160)
        K.icone("m_banniere_grande", _ui("banniere", 1), 48)
        # voile sombre plein écran troué à l'emplacement du panneau de signalement de Social (pause + "signaler") ;
        # le trou est rentré de 8 px : le bord du panneau (traits de stylo à bouts ronds) est recouvert, pas la zone utile
        r = 8
        K.plein_ecran("m_voile_signaler", S.svg(C.LARGEUR, C.HAUTEUR,
                      '<path fill-rule="evenodd" fill="#000000" fill-opacity="0.55" d="M0 0 H%d V%d H0 Z M%d %d H%d V%d H%d Z"/>'
                      % (C.LARGEUR, C.HAUTEUR, 240 + SIG_X1 + r, 180 - SIG_Y2 + r, 240 + SIG_X2 - r, 180 - SIG_Y1 - r, 240 + SIG_X1 + r)))

    # ----------------------------------------------------------------------
    #  Primitives de dessin (listes de blocs)
    # ----------------------------------------------------------------------
    def rect(self, x1, y1, x2, y2, couleur, rayon=6, bord=None, epaisseur=0, opacite=1.0, dx=0, dy=0):
        """Rectangle fixe (coordonnées Python) ; dx/dy : décalage (expression) optionnel."""
        nom = self.K.boite(x2 - x1, y2 - y1, couleur, rayon, bord, epaisseur, opacite)
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        return [costume(nom), taille(100), aller(add(cx, dx) if dx else cx, add(cy, dy) if dy else cy), tampon()]

    def rect_a(self, w, h, couleur, cx, cy, rayon=6, bord=None, epaisseur=0, opacite=1.0):
        """Rectangle de taille fixe à une position dynamique."""
        nom = self.K.boite(w, h, couleur, rayon, bord, epaisseur, opacite)
        return [costume(nom), taille(100), aller(cx, cy), tampon()]

    def icone(self, nom, cx, cy, pct=100):
        return [costume(nom), taille(pct), aller(cx, cy), tampon()]

    def icone_dyn(self, expr_nom, cx, cy, pct=100):
        """Icône dont le nom est calculé ; repli sur m_ic_inconnu si le costume n'existe pas."""
        return [costume("m_ic_inconnu"), costume(expr_nom), taille(pct), aller(cx, cy), tampon()]

    def txt(self, t, x, y, taille_px=13, couleur="blanc", al=0):
        return texte.ecrire(t, x, y, taille_px, couleur, al)

    def txt_tr(self, t, x, y, taille_px, couleur, al, lmax):
        return texte.ecrire_tronque(t, x, y, taille_px, couleur, al, lmax)

    def contour(self, fond, w, h, rayon):
        """Costume « <fond>_s » : contour blanc de la même taille (surlignage du survol)."""
        if fond and fond + "_s" not in self.K.noms:
            self.K.ajouter(fond + "_s", S.svg_rect(int(round(w)), int(round(h)), "#ffffff", rayon, 0.0, "#ffffff", 3), int(round(w)) / 2.0, int(round(h)) / 2.0)
        return fond

    def bouton(self, ident, x1, y1, x2, y2, libelle="", taille_px=13, couleur=BOUTON, couleur_txt="blanc", rayon=6, dx=0, dy=0):
        """Bouton rectangulaire : enregistré pour le survol/clic, surligné au survol."""
        fond = self.contour(self.K.boite(x2 - x1, y2 - y1, couleur, rayon), x2 - x1, y2 - y1, rayon) if couleur else ""
        return appel("bouton", ident, add(x1, dx) if dx else x1, add(y1, dy) if dy else y1,
                     add(x2, dx) if dx else x2, add(y2, dy) if dy else y2, fond, libelle, taille_px, couleur_txt)

    def bouton_a(self, ident, w, h, cx, cy, libelle="", taille_px=13, couleur=BOUTON, couleur_txt="blanc", rayon=6):
        """Bouton de taille fixe à une position dynamique (cx, cy)."""
        fond = self.contour(self.K.boite(w, h, couleur, rayon), w, h, rayon) if couleur else ""
        return appel("bouton", ident, sub(cx, w / 2.0), sub(cy, h / 2.0), add(cx, w / 2.0), add(cy, h / 2.0), fond, libelle, taille_px, couleur_txt)

    def barre(self, x, y, w, h, p, fond="#334155", plein="#22c55e"):
        return appel("barre", x, y, w, h, p, fond, plein)

    def interrupteur(self, ident, x2, cy, valeur):
        """Interrupteur ON/OFF (bord droit en x2) : vert si valeur = 1."""
        return [si(eq(valeur, 1),
                   [self.bouton(ident, x2 - 36, cy - 9, x2, cy + 9, tr("ON", "ON"), 11, VERT, "blanc", 9)],
                   [self.bouton(ident, x2 - 36, cy - 9, x2, cy + 9, tr("OFF", "OFF"), 11, BOUTON_SOMBRE, "gris", 9)])]

    # ----------------------------------------------------------------------
    #  Blocs personnalisés de base
    # ----------------------------------------------------------------------
    def _procs_base(self):
        M = self.M
        # bouton : enregistre la zone, tamponne le fond (surligné si survolé), écrit le libellé centré
        M.proc("bouton", [("id", "s"), ("x1", "n"), ("y1", "n"), ("x2", "n"), ("y2", "n"), ("fond", "s"), ("libelle", "s"),
                          ("taille", "n"), ("couleur", "s")], [
            ajouter_liste("menu_bx1", A("x1")), ajouter_liste("menu_by1", A("y1")),
            ajouter_liste("menu_bx2", A("x2")), ajouter_liste("menu_by2", A("y2")), ajouter_liste("menu_bid", A("id")),
            si(gt(longueur(A("fond")), 0), [
                costume(A("fond")), taille(100), aller(div(add(A("x1"), A("x2")), 2), div(add(A("y1"), A("y2")), 2)), tampon(),
                si(eq(V("survolId"), A("id")), [
                    effet("BRIGHTNESS", 100), effet("GHOST", 70), tampon(), effacer_effets(),     # voile clair
                    costume(join(A("fond"), "_s")), taille(100), tampon(),                        # contour blanc (costume « _s »)
                ]),
            ]),
            si(gt(longueur(A("libelle")), 0), [
                texte.ecrire_tronque(A("libelle"), div(add(A("x1"), A("x2")), 2), sub(div(add(A("y1"), A("y2")), 2), mul(A("taille"), 0.35)),
                                     A("taille"), A("couleur"), 1, sub(sub(A("x2"), A("x1")), 6)),
            ]),
        ])
        # barre de progression au stylo : (x, y) coin gauche/centre vertical, w × h, p dans [0, 1]
        M.proc("barre", [("x", "n"), ("y", "n"), ("w", "n"), ("h", "n"), ("p", "n"), ("fond", "s"), ("plein", "s")], [
            stylo_haut(), taille_stylo(A("h")), couleur_stylo(A("fond")),
            aller(add(A("x"), div(A("h"), 2)), A("y")), stylo_bas(), aller(sub(add(A("x"), A("w")), div(A("h"), 2)), A("y")), stylo_haut(),
            setv("p", A("p")), si(gt(V("p"), 1), [setv("p", 1)]), si(lt(V("p"), 0), [setv("p", 0)]),
            si(gt(V("p"), 0), [
                couleur_stylo(A("plein")), taille_stylo(sub(A("h"), 2)),
                aller(add(A("x"), div(A("h"), 2)), A("y")), stylo_bas(),
                aller(add(add(A("x"), div(A("h"), 2)), mul(sub(A("w"), A("h")), V("p"))), A("y")), stylo_haut(),
            ]),
        ])
        # champ n (1-indexé) d'une entrée « a|b|c » → variable champ
        M.proc("champ", [("entree", "s"), ("n", "n")], [
            setv("champ", ""), setv("ci", 1), setv("cj", 1),
            repeter_jusqua(gt(V("ci"), longueur(A("entree"))), [
                setv("cc", lettre(V("ci"), A("entree"))),
                si(eq(V("cc"), "|"), [changev("cj", 1)], [
                    si(eq(V("cj"), A("n")), [setv("champ", join(V("champ"), V("cc")))]),
                ]),
                changev("ci", 1),
            ]),
        ])
        # bouton sous la souris → clicId ("" si aucun) et survolN (index)
        M.proc("chercher bouton", [], [
            setv("clicId", ""), setv("survolN", 0), setv("k", long_liste("menu_bid")),
            # salon + panneau de signalement de Social ouvert : rien sous la souris si elle est sur le panneau central
            si(et(eq(V("superposition"), "signaler"), eq(V("ecran"), "salon")), [
                si(et4(ge(souris_x(), SIG_X1), le(souris_x(), SIG_X2), ge(souris_y(), SIG_Y1), le(souris_y(), SIG_Y2)), [setv("k", 0)]),
            ]),
            repeter_jusqua(ou(lt(V("k"), 1), gt(longueur(V("clicId")), 0)), [
                si(et4(ge(souris_x(), item("menu_bx1", V("k"))), le(souris_x(), item("menu_bx2", V("k"))),
                       ge(souris_y(), item("menu_by1", V("k"))), le(souris_y(), item("menu_by2", V("k")))), [
                    setv("clicId", item("menu_bid", V("k"))), setv("survolN", V("k")),
                ]),
                changev("k", -1),
            ]),
        ])
        M.proc("vider boutons", [], [
            vider("menu_bx1"), vider("menu_by1"), vider("menu_bx2"), vider("menu_by2"), vider("menu_bid"),
        ])
        # ligne de séparation
        M.proc("separateur", [("x1", "n"), ("y", "n"), ("x2", "n")], [
            stylo_haut(), taille_stylo(1), couleur_stylo("#475569"), aller(A("x1"), A("y")), stylo_bas(), aller(A("x2"), A("y")), stylo_haut(),
        ])
        # changer d'écran
        M.proc("aller ecran", [("e", "s")], [
            setv("ecran", A("e")), setv("menu_sale", 1), setv("listeModes", 0), setv("pauseParam", 0), setv("attenteTouche", 0),
            diffuser("evt changement ecran"),
        ])
        M.proc("son", [("nom", "s")], [
            setv("son_pan", 0), setv("son_volume", 100),
            si(eq(A("nom"), "clic"), [diffuser("son clic")], [diffuser("son survol")]),
        ])

    # ----------------------------------------------------------------------
    #  Tables de textes indexées à l'exécution (entrées contiguës de Textes)
    # ----------------------------------------------------------------------
    def table(self, paires):
        """Table de textes FR/EN indexée à l'exécution : liste locale menu_t<n> (FR puis EN). Renvoie son nom."""
        if not hasattr(self, "_tables"):
            self._tables = {}
        nom = "menu_t%d" % (len(self._tables) + 1)
        self.M.liste(nom, [fr for fr, _ in paires] + [en for _, en in paires])
        self._tables[nom] = len(paires)
        return nom

    def texte_table(self, nom, index0):
        """Reporter : texte n° index0 (à partir de 0) de la table `nom`, dans la langue courante."""
        return item(nom, add(add(index0, 1), mul(self._tables[nom], V("param_langue"))))

    # ----------------------------------------------------------------------
    #  Reporters utiles
    # ----------------------------------------------------------------------
    @staticmethod
    def nom_mode(mode):
        return item("ModeNoms", add(mode, mul(6, V("param_langue"))))

    @staticmethod
    def nom_ltm(ltm):
        return item("LTMNoms", add(add(ltm, 1), mul(6, V("param_langue"))))

    @staticmethod
    def mon_nom():
        return [si(eq(longueur(V("monNom")), 0), [setv("txt", tr("Joueur", "Player"))], [setv("txt", V("monNom"))])]

    @staticmethod
    def mmss(secondes):
        return join(floor(div(secondes, 60)), join(":", C.rembourrer(mod(secondes, 60), 2)))

    # ======================================================================
    #  ÉCRAN CONNEXION
    # ======================================================================
    def ecran_connexion(self):
        return [
            self.icone("m_fond_connexion", 0, 0),
            self.icone("m_logo_b", 0, 108, 100),
            self.mon_nom(),
            self.txt(join(tr("Connecté en tant que ", "Signed in as "), V("txt")), 0, 40, 16, "blanc", 1),
            self.txt(join(tr("Niveau de compte : ", "Account level: "), V("niveau")), 0, 18, 13, "gris", 1),
            si(eq(V("connecte"), 1), [
                self.txt(join(tr("Emplacement ", "Slot "), join(V("monSlot"), "/6")), 0, -6, 13, "vert", 1),
                self.bouton("continuer", -100, -60, 100, -28, tr("CONTINUER", "CONTINUE"), 18, BOUTON),
            ], [
                si(eq(V("message"), "plein"),
                   [self.txt(tr("Serveur plein (6/6) — nouvel essai dans 5 s", "Server full (6/6) — retrying in 5 s"), 0, -6, 13, "orange", 1)],
                   [self.txt(tr("Connexion au serveur…", "Connecting to server…"), 0, -6, 13, "cyan", 1)]),
                self.bouton("continuer", -100, -60, 100, -28, tr("CONTINUER", "CONTINUE"), 18, BOUTON_SOMBRE, "gris"),
            ]),
            self.bouton("charger sauvegarde", -222, -102, -78, -76, tr("Charger un code", "Load a save code"), 12, BOUTON_SOMBRE),
            si(eq(V("param_langue"), 0),
               [self.bouton("langue", -66, -102, 66, -76, "Langue : FR", 12, BOUTON_SOMBRE)],
               [self.bouton("langue", -66, -102, 66, -76, "Language: EN", 12, BOUTON_SOMBRE)]),
            self.bouton("code createur", 78, -102, 222, -76, tr("Code créateur", "Creator code"), 12, BOUTON_SOMBRE),
            self.txt_tr(join(tr("Astuce : ", "Tip: "), self.texte_table(self.k_astuces, V("astuce"))), 0, -150, 12, "gris", 1, 460),
            self.txt("v1.0 — Scratch Cloud", 236, -174, 11, "gris", 2),
        ]

    # ======================================================================
    #  ÉCRAN MATCHMAKING
    # ======================================================================
    def ecran_matchmaking(self):
        return [
            self.icone("m_fond_matchmaking", 0, 0),
            self.txt(tr("Recherche de joueurs…", "Searching for players…"), 0, 112, 22, "blanc", 1),
            self.txt(join(V("👥 Joueurs"), tr("/6 joueurs", "/6 players")), 0, 66, 30, "jaune", 1),
            self.txt(joins(tr("Mode : ", "Mode: "), self.nom_mode(V("modeChoisi")), tr(" — Événement : ", " — Event: "), self.nom_ltm(V("ltmChoisi"))),
                     0, 30, 14, "cyan", 1),
            # niveau moyen du salon
            setv("tot", V("niveau")), setv("nb", 1), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(et(eq(item("E_actif", V("k")), 1), non(eq(V("k"), V("monSlot")))), [changev("tot", item("E_niveau", V("k"))), changev("nb", 1)]),
                changev("k", 1),
            ]),
            self.txt(join(tr("Matchmaking équilibré — niveau moyen du salon : ", "Skill-based matchmaking — lobby average level: "), rnd(div(V("tot"), V("nb")))),
                     0, 4, 12, "gris", 1),
            self.txt(joins(tr("Région : ", "Region: "), self.texte_table(self.k_regions, V("param_region")), tr(" — Latence : ", " — Latency: "), rnd(V("latence")), " ms"),
                     0, -18, 12, "gris", 1),
            si(et(ge(V("phase"), 2), le(V("phase"), 5)),
               [self.txt(tr("Partie en cours — entrée en parachute", "Match in progress — joining by parachute"), 0, -58, 15, "orange", 1)], [
                si(ge(V("phase"), 6),
                   [self.txt(tr("Dernière zone — tu observeras jusqu'à la prochaine manche", "Final zone — you will spectate until the next round"), 0, -58, 14, "orange", 1)],
                   [self.txt(join(tr("Lancement dans ", "Starting in "), join(plafond(sub(V("tCompte"), chrono())), " s")), 0, -58, 16, "blanc", 1)]),
            ]),
            self.barre(-150, -82, 300, 10, div(sub(5, sub(V("tCompte"), chrono())), 5), "#334155", "#facc15"),
            self.bouton("annuler", -70, -134, 70, -104, tr("Annuler", "Cancel"), 14, BOUTON_SOMBRE),
        ]

    # ======================================================================
    #  ÉCRAN CHARGEMENT
    # ======================================================================
    def ecran_chargement(self):
        p = div(sub(chrono(), V("tChargement")), 2.5)
        return [
            self.icone("m_fond_chargement", 0, 0),
            self.rect(-204, -64, -36, 104, PANNEAU_CLAIR, 4),
            self.icone("m_carte", -120, 20, 100),
            self.txt(tr("Chargement…", "Loading…"), 110, 92, 22, "blanc", 1),
            self.txt(self.nom_mode(V("modeChoisi")), 110, 58, 18, "jaune", 1),
            si(gt(V("ltmChoisi"), 0), [self.txt(join(tr("Événement : ", "Event: "), self.nom_ltm(V("ltmChoisi"))), 110, 34, 13, "rose", 1)]),
            self.txt(tr("Île : Royale 3D — 6 joueurs max", "Island: Royale 3D — 6 players max"), 110, 8, 12, "gris", 1),
            self.txt(join(tr("Région : ", "Region: "), self.texte_table(self.k_regions, V("param_region"))), 110, -12, 12, "gris", 1),
            self.txt_tr(join(tr("Astuce : ", "Tip: "), self.texte_table(self.k_astuces, V("astuce"))), 0, -98, 12, "cyan", 1, 460),
            self.barre(-200, -130, 400, 14, p, "#334155", "#22c55e"),
            si(lt(p, 1), [self.txt(join(rnd(mul(p, 100)), " %"), 0, -158, 12, "blanc", 1)],
               [self.txt(tr("Prêt — en attente de la partie…", "Ready — waiting for the match…"), 0, -158, 12, "vert", 1)]),
        ]

    # ======================================================================
    #  MENU PAUSE (superposé au 3D, chaque image)
    # ======================================================================
    def ecran_pause(self):
        def b(ident, cy, libelle, couleur=BOUTON):
            return self.bouton(ident, -100, cy - 13, 100, cy + 13, libelle, 14, couleur)
        # signalement ouvert depuis la pause : Social (calque 89) a déjà dessiné son panneau central
        # (x ∈ [−130, 130], y ∈ [−90, 90]) AVANT moi dans l'image → je ne dessine qu'un voile sombre
        # tout autour (quatre rectangles) et aucun bouton : les clics sont ignorés.
        voile = [self.icone("m_voile_signaler", 0, 0)]      # un seul costume troué : pas de raccord visible entre rectangles
        return [si(eq(V("superposition"), "signaler"), voile, [
            si(eq(V("pauseParam"), 1), [
                self.rect(-200, -152, 200, 152, PANNEAU, 12, "#64748b", 2, 0.94),
                setv("ox", 46), self.panneau_parametres(),
                self.bouton("pause retour", -60, -148, 60, -122, tr("Retour", "Back"), 13, BOUTON_SOMBRE),
            ], [
                self.rect(-120, -132, 120, 132, PANNEAU, 12, "#64748b", 2, 0.9),
                self.txt(tr("PAUSE", "PAUSED"), 0, 100, 26, "blanc", 1),
                self.txt(tr("La partie continue !", "The match goes on!"), 0, 80, 11, "orange", 1),
                b("reprendre", 52, tr("Reprendre", "Resume")),
                b("pause parametres", 18, tr("Paramètres", "Settings"), BOUTON_SOMBRE),
                b("signaler", -16, tr("Signaler un joueur", "Report a player"), BOUTON_SOMBRE),
                si(ou(eq(V("etat"), 2), eq(V("etat"), 4)), [b("camera", -50, tr("Caméra libre", "Free camera"), BOUTON_SOMBRE)]),
                b("quitter", -90, tr("Quitter la partie", "Leave match"), ROUGE),
                self.txt(join(tr("Touche ", "Key "), join(C.touche_config("pause"), tr(" : reprendre", ": resume"))), 0, -122, 11, "gris", 1),
            ]),
        ])]

    # ======================================================================
    #  ÉCRAN FIN (superposé au 3D, chaque image) — textes sans ombre sauf le titre
    # ======================================================================
    def ecran_fin(self):
        def stat(y, libelle, valeur):
            return [self.txt(libelle, -198, y, 12, "gris", 0), self.txt(valeur, -24, y, 12, "blanc", 2)]
        return [
            si(eq(V("victoire"), 1), [
                effet("GHOST", 20), self.icone("m_fond_victoire", 0, 0), effacer_effets(),
                self.txt(tr("VICTOIRE ROYALE !", "VICTORY ROYALE!"), 0, 118, 30, "or", 1),
                self.icone("m_medaille_1", -196, 128, 80),
                self.icone("m_medaille_1", 196, 128, 80),
                setv("txt_ombre", 0),
                self.txt(join(tr("#1 sur ", "#1 of "), join(V("participants"), tr(" joueurs", " players"))), 0, 92, 14, "jaune", 1),
            ], [
                effet("GHOST", 25), self.icone("m_fond_fin", 0, 0), effacer_effets(),
                self.txt(tr("PARTIE TERMINÉE", "MATCH OVER"), 0, 118, 26, "blanc", 1),
                setv("txt_ombre", 0),
                self.txt(joins(tr("Classement : #", "Placement: #"), V("rang"), tr(" sur ", " of "), V("participants")), 0, 92, 15, "orange", 1),
            ]),
            self.rect(-212, -112, 212, 72, PANNEAU, 10, None, 0, 0.88),
            stat(48, tr("Éliminations", "Eliminations"), V("💀 Éliminations")),
            stat(28, tr("Dégâts infligés", "Damage dealt"), V("stat_degats")),
            stat(8, tr("Temps de survie", "Survival time"), self.mmss(V("stat_tempsSurvie"))),
            stat(-12, tr("Coffres ouverts", "Chests opened"), V("stat_coffres")),
            stat(-32, tr("Matériaux", "Materials"), V("stat_materiaux")),
            stat(-52, tr("Placement", "Placement"), join("#", V("rang"))),
            si(eq(V("mode"), 6), stat(-72, tr("Hype (arène)", "Hype (arena)"), V("hype"))),
            # colonne droite : XP (3 lignes de récapitulatif au plus)
            self.txt(join(tr("XP gagnée : +", "XP earned: +"), V("xpGagne")), 4, 48, 13, "jaune", 0),
            setv("k", 1), setv("y", 28),
            repeter_jusqua(ou(gt(V("k"), long_liste("RecapLignes")), gt(V("k"), 4)), [
                self.txt_tr(item("RecapLignes", V("k")), 4, V("y"), 11, "blanc", 0, 196),
                changev("y", -15), changev("k", 1),
            ]),
            self.txt(join(tr("Niveau ", "Level "), V("niveau")), 4, -44, 12, "blanc", 0),
            self.txt(join(V("xpNiveau"), join(" / ", V("xpSuivant"))), 200, -44, 11, "gris", 2),
            self.barre(4, -58, 196, 8, div(V("xpNiveau"), V("xpSuivant")), "#334155", "#3b82f6"),
            si(gt(V("bonusXP"), 0), [self.txt(join(tr("Bonus d'XP de session : +", "Session XP bonus: +"), join(V("bonusXP"), " %")), 4, -80, 11, "vert", 0)]),
            setv("txt_ombre", 1),
            self.bouton("rejouer", -150, -162, -10, -128, tr("REJOUER", "PLAY AGAIN"), 16, JAUNE, "noir"),
            self.bouton("salon", 10, -162, 150, -128, tr("Salon", "Lobby"), 16, BOUTON_SOMBRE),
            # compte à rebours de la prochaine manche (tempsPhase = DUREE_RESULTATS − temps écoulé, calculé par Partie)
            si(eq(V("finManche"), 1), [
                self.txt(join(tr("Prochaine manche dans ", "Next round in "), join(V("tempsPhase"), " s")), 0, -176, 11, "gris", 1),
            ]),
        ]

    # ======================================================================
    #  SALON : cadre (onglets, zone sociale, bas d'écran, sélecteur de mode)
    # ======================================================================
    def _tabs(self):
        """Positions des onglets : largeurs proportionnelles aux libellés (FR et EN)."""
        larg = [max(texte.largeur_px(fr, 11), texte.largeur_px(en, 11)) + 12 for _, fr, en in ONGLETS]
        total = 476.0
        k = total / sum(larg)
        tabs, x = [], -238.0
        for (nom, fr, en), w in zip(ONGLETS, larg):
            w2 = w * k
            tabs.append((nom, round(x), round(x + w2)))
            x += w2
        return tabs

    def ecran_salon(self):
        corps = [
            self.icone("m_fond_salon", 0, 0),
            self.rect(-240, ZT_Y1, 240, ZT_Y2, "#0b1120", 0),
        ]
        for (nom, fr, en), (nom2, x1, x2) in zip(ONGLETS, self._tabs()):
            cx = (x1 + x2) / 2.0
            corps.append(si(eq(V("onglet"), nom),
                            [self.bouton("onglet " + nom, x1 + 1, ZT_Y1 + 1, x2 - 1, ZT_Y2 - 1, "", 11, BOUTON, "blanc", 5)],
                            [self.bouton("onglet " + nom, x1 + 1, ZT_Y1 + 1, x2 - 1, ZT_Y2 - 1, "", 11, "#1e293b", "gris", 5)]))
            corps.append(self.icone("m_ong_" + nom, cx, 169, 55))
            corps.append(si(eq(V("onglet"), nom), [self.txt(tr(fr, en), cx, 150, 11, "blanc", 1)],
                            [self.txt(tr(fr, en), cx, 150, 11, "gris", 1)]))
        corps += [
            # zone sociale (Social y dessine la liste d'amis)
            self.rect(ZS_X1, ZS_Y1, ZS_X2, ZS_Y2, SOCIAL, 8, "#1e293b", 2),
            # jetons et niveau au-dessus de la zone sociale
            self.icone("m_jeton", 159, 139, 45),
            self.txt(V("jetons"), 168, 135, 12, "jaune", 0),
            self.txt(join(tr("Niveau ", "Level "), V("niveau")), 154, 122, 11, "gris", 0),
            # contenu de l'onglet
            si(eq(V("onglet"), "accueil"), self.onglet_accueil()),
            si(eq(V("onglet"), "passe"), self.onglet_passe()),
            si(eq(V("onglet"), "boutique"), self.onglet_boutique()),
            si(eq(V("onglet"), "casier"), self.onglet_casier()),
            si(eq(V("onglet"), "quetes"), self.onglet_quetes()),
            si(eq(V("onglet"), "carriere"), self.onglet_carriere()),
            si(eq(V("onglet"), "parametres"), [setv("ox", 0), self.panneau_parametres()]),
            self.salon_bas(),
        ]
        return corps

    def salon_bas(self):
        return [
            # JOUER + sélecteur de mode (x ∈ [-30, 140])
            self.bouton("jouer", -30, -176, 140, -146, tr("JOUER", "PLAY"), 20, JAUNE, "noir", 8),
            self.bouton("mode", -30, -142, 140, -112, "", 13, PANNEAU_CLAIR, "blanc", 6),
            self.txt(self.nom_mode(V("modeChoisi")), 50, -126, 13, "blanc", 1),
            self.txt_tr(join(tr("Événement : ", "Event: "), self.nom_ltm(V("ltmChoisi"))), 50, -139, 11, "gris", 1, 150),
            self.icone("m_fleche_haut", 130, -127, 40),
            # réglages rapides à gauche
            self.txt(tr("Remplissage auto", "Auto fill"), -236, -124, 12, "blanc", 0),
            self.interrupteur("remplissage", -40, -120, V("remplissage")),
            self.txt(tr("Confidentialité", "Privacy"), -236, -150, 12, "blanc", 0),
            si(gt(V("confidentialite"), 0), [self.txt(join("#", V("codeSalon")), -124, -150, 11, "gris", 2)]),
            self.bouton("confidentialite", -118, -156, -40, -136, self.texte_table(self.k_confid, V("confidentialite")), 11, BOUTON_SOMBRE),
            si(et(ge(V("phase"), 1), gt(V("debut"), 0)), [
                self.txt_tr(joins("● ", self.nom_mode(V("mode")), " — ", V("vivants"), tr(" en jeu", " playing")), -236, -174, 11, "orange", 0, 130),
                self.bouton("regarder", -100, -178, -40, -160, tr("Regarder", "Watch"), 11, BOUTON),
            ], [
                si(eq(V("param_afficherPing"), 1), [self.txt(join(tr("Ping : ", "Ping: "), join(rnd(V("latence")), " ms")), -236, -174, 11, "gris", 0)]),
            ]),
            # liste déroulante des modes
            si(eq(V("listeModes"), 1), self.liste_modes()),
        ]

    def liste_modes(self):
        corps = [self.rect(-30, -110, 140, 44, PANNEAU, 8, "#64748b", 2)]
        for m in range(1, 7):
            cy = 32 - 20 * (m - 1)
            corps.append(si(eq(V("modeChoisi"), m),
                            [self.bouton("mode %d" % m, -26, cy - 9, 136, cy + 9, self.nom_mode(m), 12, BOUTON)],
                            [self.bouton("mode %d" % m, -26, cy - 9, 136, cy + 9, self.nom_mode(m), 12, PANNEAU_CLAIR)]))
        corps += [
            appel("separateur", -26, -80, 136),
            self.bouton("ltm -", -26, -106, -6, -86, "", 11, BOUTON_SOMBRE), self.icone("m_fleche_gauche", -16, -96, 40),
            self.txt_tr(join(tr("Événement : ", "Event: "), self.nom_ltm(V("ltmChoisi"))), 55, -100, 11, "rose", 1, 118),
            self.bouton("ltm +", 116, -106, 136, -86, "", 11, BOUTON_SOMBRE), self.icone("m_fleche_droite", 126, -96, 40),
        ]
        return corps

    # ======================================================================
    #  ONGLET DÉCOUVRIR (accueil)
    # ======================================================================
    def carte_info(self, x1, y1, x2, y2, titre, lignes):
        corps = [self.rect(x1, y1, x2, y2, PANNEAU_CLAIR, 8), self.txt_tr(titre, x1 + 8, y2 - 18, 12, "jaune", 0, x2 - x1 - 12)]
        y = y2 - 36
        for l in lignes:
            corps.append(self.txt_tr(l, x1 + 8, y, 11, "blanc", 0, x2 - x1 - 12))
            y -= 15
        return corps

    def onglet_accueil(self):
        ltm_jour = add(mod(date_actuelle("DATE"), 5), 1)
        return [
            # personnage équipé
            self.rect(-236, -106, -140, 142, PANNEAU, 8),
            self.icone_dyn(joins("m_perso_", V("skin"), "_", V("styleSkin")), -188, 62, 96),
            self.mon_nom(),
            self.txt_tr(V("txt"), -188, -12, 13, "blanc", 1, 88),
            self.txt(join(tr("Niveau ", "Level "), V("niveau")), -188, -30, 11, "gris", 1),
            self.icone_dyn(join("m_ic_banniere_", V("banniere")), -220, -52, 60),
            self.txt(join(tr("Bannière ", "Banner "), V("banniere")), -208, -56, 11, "gris", 0),
            self.txt(join(tr("Tenue ", "Outfit "), V("skin")), -188, -76, 11, "gris", 1),
            si(gt(longueur(V("codeCreateur")), 0), [self.txt_tr(join("★ ", V("codeCreateur")), -188, -96, 11, "cyan", 1, 88)]),
            # fil d'actualités : 4 cartes
            self.carte_info(-132, 22, 2, 140, joins(tr("Chap. ", "Chap. "), V("chapitre"), tr(" — Saison ", " — Season "), V("saison")), [
                join(V("joursSaison"), tr(" jours restants", " days left")),
                tr("Nouveau passe !", "New Battle Pass!"),
                join(tr("Passe : niveau ", "Pass: level "), join(V("passeNiveau"), "/100")),
                join(tr("Jetons : ", "Tokens: "), V("jetons")),
            ]),
            self.carte_info(10, 22, 144, 140, tr("Événement du jour", "Event of the day"), [
                self.nom_ltm(ltm_jour),
                tr("Règles spéciales !", "Special rules!"),
                tr("À choisir dans le", "Pick it in the"),
                tr("sélecteur de mode.", "mode selector."),
            ]),
            self.carte_info(-132, -104, 2, 14, tr("Notes de version", "Patch notes"), [
                tr("v1.0 : carte 32×32,", "v1.0: 32×32 map,"),
                tr("6 joueurs en ligne,", "6 online players,"),
                tr("construction, tempête,", "building, storm,"),
                tr("équipes, passe, quêtes.", "teams, pass, quests."),
            ]),
            self.carte_info(10, -104, 144, 14, tr("Astuce", "Tip"), [
                self.texte_table(self.k_astuces_l1, V("astuce")),
                self.texte_table(self.k_astuces_l2, V("astuce")),
                self.texte_table(self.k_astuces_l3, V("astuce")),
                self.texte_table(self.k_astuces_l4, V("astuce")),
            ]),
        ]

    # ======================================================================
    #  ONGLET PASSE DE COMBAT
    # ======================================================================
    def nom_icone_recompense(self):
        """txt ← nom du costume d'icône pour (champ type dans txt2, id dans tmp)."""
        return [
            si(eq(V("txt2"), "jetons"), [setv("txt", "m_ic_jetons")], [
                si(eq(V("txt2"), "style"), [setv("txt", "m_ic_style")], [setv("txt", joins("m_ic_", V("txt2"), "_", V("tmp")))]),
            ]),
        ]

    def nom_cosmetique(self):
        """txt ← nom lisible de l'objet (type dans txt2, id dans tmp) : listes sys_*Noms si elles existent."""
        listes = {"skin": "sys_SkinNoms", "pioche": "sys_PiocheNoms", "planeur": "sys_PlaneurNoms", "banniere": "sys_BanniereNoms"}
        corps = [
            setv("n", num_item("menu_types", V("txt2"))),
            si(gt(V("n"), 0), [setv("txt", join(self.texte_table(self.k_types, sub(V("n"), 1)), join(" n°", V("tmp"))))], [
                si(eq(V("txt2"), "jetons"), [setv("txt", join(V("tmp"), tr(" jetons", " tokens")))],
                   [setv("txt", join(tr("Style de tenue ", "Outfit style "), V("tmp")))]),
            ]),
        ]
        for code, nom in listes.items():
            if nom in self.P.stage.lists:
                corps.append(si(eq(V("txt2"), code), [
                    si(gt(longueur(item(nom, add(V("tmp"), mul(floor(div(long_liste(nom), 2)), V("param_langue"))))), 0),
                       [setv("txt", item(nom, add(V("tmp"), mul(floor(div(long_liste(nom), 2)), V("param_langue")))))]),
                ]))
        return corps

    def onglet_passe(self):
        palier = add(mul(V("pagePasse"), 30), add(V("i"), 1))
        return [
            self.txt(join(tr("Passe de combat — Niveau ", "Battle Pass — Level "), join(V("passeNiveau"), "/100")), -236, 124, 15, "blanc", 0),
            self.icone("m_etoile", -228, 103, 50),
            self.txt(join(V("etoiles"), tr("/5 étoiles", "/5 stars")), -216, 99, 12, "jaune", 0),
            # pagination
            self.bouton("passe page -", 100, 118, 118, 138, "", 11, BOUTON_SOMBRE), self.icone("m_fleche_gauche", 109, 128, 40),
            self.bouton("passe page +", 126, 118, 144, 138, "", 11, BOUTON_SOMBRE), self.icone("m_fleche_droite", 135, 128, 40),
            self.txt(join(add(mul(V("pagePasse"), 30), 1), join("–", add(mul(V("pagePasse"), 30), 30))), 96, 124, 11, "gris", 2),
            # XP vers le niveau suivant
            self.txt(tr("XP", "XP"), -140, 99, 11, "gris", 0),
            self.barre(-124, 102, 116, 8, div(V("xpNiveau"), V("xpSuivant")), "#334155", "#3b82f6"),
            self.txt(join(V("xpNiveau"), join(" / ", V("xpSuivant"))), -2, 99, 11, "gris", 0),
            self.txt(tr("5 ★ = 1 niveau", "5 ★ = 1 level"), 144, 99, 11, "jaune", 2),
            # grille 10 × 3
            setv("i", 0),
            repeter(30, [
                setv("cx", add(-218, mul(36.2, mod(V("i"), 10)))),
                setv("cy", sub(66, mul(40, floor(div(V("i"), 10))))),
                appel("champ", item("PasseRecompenses", palier), 1), setv("txt2", V("champ")),
                appel("champ", item("PasseRecompenses", palier), 2), setv("tmp", V("champ")),
                self.nom_icone_recompense(),
                si(le(palier, V("passeNiveau")), [
                    si(eq(V("txt2"), "style"), self.rect_a(34, 36, "#3b3b1a", V("cx"), V("cy"), 5, OR, 2),
                       self.rect_a(34, 36, PANNEAU_CLAIR, V("cx"), V("cy"), 5)),
                    self.icone_dyn(V("txt"), V("cx"), add(V("cy"), 5), 62),
                    self.txt(palier, sub(V("cx"), 14), sub(V("cy"), 16), 11, "vert", 0),
                ], [
                    si(eq(V("txt2"), "style"), self.rect_a(34, 36, "#2a2a16", V("cx"), V("cy"), 5, "#92400e", 2),
                       self.rect_a(34, 36, PANNEAU, V("cx"), V("cy"), 5)),
                    effet("GHOST", 55), self.icone_dyn(V("txt"), V("cx"), add(V("cy"), 5), 62), effacer_effets(),
                    self.icone("m_cadenas", add(V("cx"), 9), sub(V("cy"), 10), 32),
                    self.txt(palier, sub(V("cx"), 14), sub(V("cy"), 16), 11, "gris", 0),
                ]),
                changev("i", 1),
            ]),
            # légende et prochaine récompense
            self.rect(-236, -106, 144, -46, PANNEAU, 8),
            self.txt(tr("Prochaine récompense", "Next reward"), -228, -62, 12, "cyan", 0),
            appel("champ", item("PasseRecompenses", add(V("passeNiveau"), 1)), 1), setv("txt2", V("champ")),
            appel("champ", item("PasseRecompenses", add(V("passeNiveau"), 1)), 2), setv("tmp", V("champ")),
            self.nom_icone_recompense(),
            self.icone_dyn(V("txt"), -214, -84, 80),
            si(gt(longueur(V("txt2")), 0), [
                self.nom_cosmetique(),
                self.txt_tr(joins(tr("Palier ", "Tier "), add(V("passeNiveau"), 1), " : ", V("txt")), -196, -88, 12, "blanc", 0, 200),
            ], [self.txt(tr("Passe terminé — bravo !", "Pass complete — well done!"), -196, -88, 12, "blanc", 0)]),
            self.icone("m_cadenas", 17, -74, 36),
            self.txt(tr("Verrouillé", "Locked"), 30, -78, 11, "gris", 0),
            self.rect(10, -99, 24, -85, OR, 3),
            self.txt(tr("Récompense de style", "Style reward"), 30, -95, 11, "gris", 0),
            self.txt(join(tr("Bonus d'XP de session : +", "Session XP bonus: +"), join(V("bonusXP"), " %")), 142, -62, 11, "vert", 2),
        ]

    # ======================================================================
    #  ONGLET BOUTIQUE
    # ======================================================================
    def onglet_boutique(self):
        return [
            self.txt(tr("Boutique d'objets", "Item Shop"), -236, 124, 15, "blanc", 0),
            self.txt(join(tr("Rotation dans ", "Rotation in "), join(sub(24, date_actuelle("HOUR")), " h")), -20, 124, 12, "gris", 1),
            appel("largeur texte", join(V("jetons"), tr(" jetons", " tokens")), 13),
            self.icone("m_jeton", sub(134, V("txt_largeur")), 128, 55),
            self.txt(join(V("jetons"), tr(" jetons", " tokens")), 144, 124, 13, "jaune", 2),
            si(lt(long_liste("Boutique"), 1), [
                self.txt(tr("La boutique ouvre bientôt…", "The shop opens soon…"), -46, 20, 14, "gris", 1),
            ]),
            setv("i", 0),
            repeter(6, [
                si(gt(longueur(item("Boutique", add(V("i"), 1))), 0), [
                    setv("cx", add(-176, mul(128, mod(V("i"), 3)))),
                    setv("cy", sub(64, mul(112, floor(div(V("i"), 3))))),
                    appel("champ", item("Boutique", add(V("i"), 1)), 1), setv("txt2", V("champ")),
                    appel("champ", item("Boutique", add(V("i"), 1)), 2), setv("tmp", V("champ")),
                    appel("champ", item("Boutique", add(V("i"), 1)), 3), setv("p", V("champ")),
                    self.rect_a(120, 108, PANNEAU_CLAIR, V("cx"), V("cy"), 8),
                    self.nom_icone_recompense(),
                    self.icone_dyn(V("txt"), V("cx"), add(V("cy"), 26), 140),
                    self.nom_cosmetique(),
                    self.txt_tr(V("txt"), V("cx"), sub(V("cy"), 12), 11, "blanc", 1, 114),
                    self.icone("m_jeton", sub(V("cx"), 20), sub(V("cy"), 24), 40),
                    self.txt(V("p"), sub(V("cx"), 10), sub(V("cy"), 28), 12, "jaune", 0),
                    si(contient("Possedes", join(V("txt2"), join("|", V("tmp")))), [
                        self.icone("m_coche", sub(V("cx"), 30), sub(V("cy"), 44), 45),
                        self.txt(tr("Possédé", "Owned"), sub(V("cx"), 18), sub(V("cy"), 48), 12, "vert", 0),
                    ], [
                        si(ge(V("jetons"), V("p")),
                           [self.bouton_a(join("acheter ", add(V("i"), 1)), 104, 20, V("cx"), sub(V("cy"), 44), tr("Acheter", "Buy"), 12, BOUTON)],
                           [self.bouton_a(join("acheter ", add(V("i"), 1)), 104, 20, V("cx"), sub(V("cy"), 44), tr("Acheter", "Buy"), 12, BOUTON_SOMBRE, "gris")]),
                    ]),
                ]),
                changev("i", 1),
            ]),
        ]

    # ======================================================================
    #  ONGLET CASIER
    # ======================================================================
    def equipe_cosmetique(self):
        """trouve ← 1 si l'objet (type txt2, id tmp) est équipé."""
        return [
            setv("trouve", 0),
            si(eq(V("txt2"), "skin"), [si(eq(V("skin"), V("tmp")), [setv("trouve", 1)])]),
            si(eq(V("txt2"), "pioche"), [si(eq(V("pioche"), V("tmp")), [setv("trouve", 1)])]),
            si(eq(V("txt2"), "planeur"), [si(eq(V("planeur"), V("tmp")), [setv("trouve", 1)])]),
            si(eq(V("txt2"), "spray"), [si(eq(V("spray"), V("tmp")), [setv("trouve", 1)])]),
            si(eq(V("txt2"), "banniere"), [si(eq(V("banniere"), V("tmp")), [setv("trouve", 1)])]),
            si(eq(V("txt2"), "emote"), [si(contient("EmotesEquipees", V("tmp")), [setv("trouve", 1)])]),
        ]

    def onglet_casier(self):
        corps = []
        positions = [(-236, -176), (-172, -112), (-108, -48), (-44, 16), (20, 80), (84, 144)]
        for n, ((code, fr, en), (x1, x2)) in enumerate(zip(CATEGORIES_CASIER, positions), start=1):
            corps.append(si(eq(V("categorie"), n),
                            [self.bouton("categorie %d" % n, x1, 118, x2, 140, tr(fr, en), 11, BOUTON)],
                            [self.bouton("categorie %d" % n, x1, 118, x2, 140, tr(fr, en), 11, PANNEAU_CLAIR, "gris")]))
        corps += [
            # aperçu du personnage
            self.rect(-236, -106, -130, 110, PANNEAU, 8),
            self.icone_dyn(joins("m_perso_", V("skin"), "_", V("styleSkin")), -183, 52, 92),
            self.mon_nom(),
            self.txt_tr(V("txt"), -183, -10, 13, "blanc", 1, 98),
            setv("txt2", "skin"), setv("tmp", V("skin")), self.nom_cosmetique(),
            self.txt_tr(V("txt"), -183, -26, 11, "gris", 1, 98),
            si(contient("Possedes", join("style|", V("skin"))),
               [self.bouton("style", -226, -52, -140, -34, join(tr("Style ", "Style "), join(add(V("styleSkin"), 1), "/2")), 11, BOUTON_SOMBRE)],
               [self.txt(tr("Style 1/1", "Style 1/1"), -183, -46, 11, "gris", 1)]),
            self.icone_dyn(join("m_ic_banniere_", V("banniere")), -220, -72, 60),
            self.txt(join(tr("Bannière ", "Banner "), V("banniere")), -206, -76, 11, "gris", 0),
            self.txt(join(tr("Niveau ", "Level "), V("niveau")), -183, -96, 11, "gris", 1),
            # grille des objets de la catégorie (6 par ligne, 40 px)
            setv("txt2", item("menu_types", V("categorie"))),
            setv("n", item("menu_nbCosmetiques", V("categorie"))),
            setv("i", 0),
            repeter(V("n"), [
                setv("tmp", add(V("i"), 1)),
                setv("cx", add(-100, mul(44, mod(V("i"), 6)))),
                setv("cy", sub(90, mul(46, floor(div(V("i"), 6))))),
                self.equipe_cosmetique(),
                si(eq(V("trouve"), 1), self.rect_a(40, 40, "#1d4ed8", V("cx"), V("cy"), 6, JAUNE, 2), [
                    si(ou(contient("Possedes", join(V("txt2"), join("|", V("tmp")))), eq(V("tmp"), 1)),
                       self.rect_a(40, 40, PANNEAU_CLAIR, V("cx"), V("cy"), 6),
                       self.rect_a(40, 40, PANNEAU, V("cx"), V("cy"), 6)),
                ]),
                si(ou3(eq(V("trouve"), 1), contient("Possedes", join(V("txt2"), join("|", V("tmp")))), eq(V("tmp"), 1)), [
                    self.icone_dyn(joins("m_ic_", V("txt2"), "_", V("tmp")), V("cx"), V("cy"), 90),
                ], [
                    effet("GHOST", 60), self.icone_dyn(joins("m_ic_", V("txt2"), "_", V("tmp")), V("cx"), V("cy"), 90), effacer_effets(),
                    self.icone("m_cadenas", add(V("cx"), 12), sub(V("cy"), 12), 36),
                ]),
                self.bouton_a(join("casier ", V("tmp")), 40, 40, V("cx"), V("cy"), "", 11, None),
                changev("i", 1),
            ]),
            # cases de la roue d'émotes
            si(eq(V("categorie"), 5), [
                self.txt(tr("Case de la roue :", "Wheel slot:"), -120, -26, 11, "blanc", 0),
            ] + [si(eq(V("caseEmote"), k), [self.bouton("case %d" % k, -30 + 20 * k, -32, -14 + 20 * k, -16, str(k), 11, BOUTON)],
                     [self.bouton("case %d" % k, -30 + 20 * k, -32, -14 + 20 * k, -16, str(k), 11, BOUTON_SOMBRE)]) for k in range(1, 7)]
            + [self.txt(tr("Clique une émote pour l'y placer", "Click an emote to put it there"), -120, -42, 11, "gris", 0)]),
            # code de sauvegarde (complet, sur deux lignes de 38 caractères comme dans Paramètres › Compte)
            self.rect(-120, -106, 144, -52, PANNEAU, 8),
            self.txt(tr("Code de sauvegarde", "Save code"), -112, -62, 11, "cyan", 0),
            self.bouton("regenerer", 70, -70, 140, -56, tr("Régénérer", "Regenerate"), 11, BOUTON_SOMBRE),
            si(gt(longueur(V("codeSauvegarde")), 0), [
                self.txt(C.sous_chaine(V("codeSauvegarde"), 1, 38), -112, -82, 11, "blanc", 0),
                self.txt(C.sous_chaine(V("codeSauvegarde"), 39, 38), -112, -94, 11, "blanc", 0),
            ], [self.txt(tr("(en attente du module Systèmes)", "(waiting for the Systems module)"), -112, -82, 11, "gris", 0)]),
            self.txt(tr("Copie ce code pour garder ta progression.", "Copy this code to keep your progress."), -112, -104, 10, "gris", 0),
        ]
        return corps

    # ======================================================================
    #  ONGLET QUÊTES
    # ======================================================================
    def onglet_quetes(self):
        sous = [(1, "Quotidiennes", "Daily"), (2, "Hebdomadaires", "Weekly"), (3, "Histoire", "Story")]
        corps = []
        for n, fr, en in sous:
            x1 = -236 + 124 * (n - 1)
            corps.append(si(eq(V("sousOnglet"), n),
                            [self.bouton("sous %d" % n, x1, 118, x1 + 116, 140, tr(fr, en), 12, BOUTON)],
                            [self.bouton("sous %d" % n, x1, 118, x1 + 116, 140, tr(fr, en), 12, PANNEAU_CLAIR, "gris")]))
        titre = item("QueteTitres", add(V("idx"), mul(floor(div(long_liste("QueteTitres"), 2)), V("param_langue"))))
        corps += [
            setv("j", 0), setv("k", 0),
            repeter(long_liste("QuetesActives"), [
                changev("k", 1),
                appel("champ", item("QuetesActives", V("k")), 2),
                si(et(eq(V("champ"), V("sousOnglet")), lt(V("j"), 6)), [
                    setv("cy", sub(96, mul(36, V("j")))),
                    appel("champ", item("QuetesActives", V("k")), 1), setv("idx", V("champ")),
                    appel("champ", item("QuetesActives", V("k")), 3), setv("x", V("champ")),
                    appel("champ", item("QuetesActives", V("k")), 4), setv("y", V("champ")),
                    appel("champ", item("QuetesActives", V("k")), 5), setv("n", V("champ")),
                    appel("champ", item("QuetesActives", V("k")), 6), setv("tmp", V("champ")),
                    self.rect_a(380, 32, PANNEAU_CLAIR, -46, V("cy"), 6),
                    self.icone_dyn(join("m_quete_", V("sousOnglet")), -222, V("cy"), 60),
                    si(gt(longueur(titre), 0), [setv("txt", titre)], [setv("txt", join(tr("Quête n°", "Quest #"), V("idx")))]),
                    self.txt_tr(V("txt"), -206, add(V("cy"), 3), 12, "blanc", 0, 170),
                    self.barre(-206, sub(V("cy"), 8), 120, 7, div(V("x"), V("y")), "#1e293b", "#22c55e"),
                    self.txt(join(V("x"), join("/", V("y"))), -80, sub(V("cy"), 11), 11, "gris", 0),
                    self.txt(join("+", join(V("tmp"), " XP")), -20, sub(V("cy"), 4), 12, "jaune", 0),
                    si(eq(V("n"), 1), [self.bouton_a(join("quete reclamer ", V("k")), 56, 22, 56, V("cy"), tr("Réclamer", "Claim"), 11, VERT)]),
                    si(eq(V("n"), 2), [self.icone("m_coche", 34, V("cy"), 50), self.txt(tr("Réclamée", "Claimed"), 60, sub(V("cy"), 4), 10, "vert", 1)]),
                    self.bouton_a(join("quete partager ", V("k")), 58, 22, 115, V("cy"), tr("Partager", "Share"), 11, BOUTON_SOMBRE),
                    changev("j", 1),
                ]),
            ]),
            si(eq(V("j"), 0), [self.txt(tr("Aucune quête pour le moment", "No quests right now"), -46, 20, 14, "gris", 1)]),
            self.txt(tr("Partager = l'envoyer à ton équipe dans le chat", "Share = send it to your team in chat"), -236, -102, 11, "gris", 0),
        ]
        return corps

    # ======================================================================
    #  ONGLET CARRIÈRE / STATISTIQUES
    # ======================================================================
    def onglet_carriere(self):
        stage = self.P.stage
        a_divisions = "sys_DivisionNoms" in stage.lists
        a_succes = "sys_SuccesTitres" in stage.lists

        def ligne(y, libelle, valeur, couleur="blanc"):
            return [self.txt(libelle, -228, y, 11, "gris", 0), self.txt(valeur, -68, y, 11, couleur, 2)]

        def elims_de(k):
            return [si(eq(k, V("monSlot")), [setv("tmp", V("💀 Éliminations"))], [setv("tmp", item("E_elims", k))])]

        nom_division = (item("sys_DivisionNoms", add(V("division"), mul(floor(div(long_liste("sys_DivisionNoms"), 2)), V("param_langue"))))
                        if a_divisions else join(tr("Division ", "Division "), V("division")))
        titre_succes = (item("sys_SuccesTitres", add(V("i"), mul(floor(div(long_liste("sys_SuccesTitres"), 2)), V("param_langue"))))
                        if a_succes else join(tr("Succès n°", "Achievement #"), V("i")))
        return [
            self.txt(joins(tr("Carrière — Chapitre ", "Career — Chapter "), V("chapitre"), tr(", Saison ", ", Season "), V("saison")), -236, 124, 14, "blanc", 0),
            si(eq(V("vueClassement"), 1),
               [self.bouton("classement", -6, 118, 144, 140, tr("Retour aux statistiques", "Back to stats"), 11, BOUTON)],
               [self.bouton("classement", -16, 118, 144, 140, tr("Classement de fin de saison", "End-of-season ranking"), 11, BOUTON_SOMBRE)]),
            # --- statistiques ---
            self.rect(-236, -44, -60, 112, PANNEAU, 8),
            self.txt(tr("Statistiques", "Statistics"), -228, 98, 12, "cyan", 0),
            ligne(82, tr("Victoires", "Wins"), V("stat_victoires"), "jaune"),
            ligne(68, tr("Parties", "Matches"), V("stat_parties")),
            ligne(54, tr("Éliminations", "Eliminations"), V("stat_elims")),
            ligne(40, tr("Top 3", "Top 3"), V("stat_top3")),
            si(gt(V("stat_meilleurRang"), 0), ligne(26, tr("Meilleur rang", "Best placement"), join("#", V("stat_meilleurRang"))),
               ligne(26, tr("Meilleur rang", "Best placement"), "—")),
            ligne(12, "K/D", div(rnd(mul(div(V("stat_elims"), maximum(V("stat_morts"), 1)), 100)), 100)),
            ligne(-2, tr("Dégâts (session)", "Damage (session)"), V("stat_degats")),
            ligne(-16, tr("Coffres (session)", "Chests (session)"), V("stat_coffres")),
            ligne(-30, tr("Survie (session)", "Survival (session)"), self.mmss(V("stat_tempsSurvie"))),
            # --- arène + classement ---
            self.rect(-52, -44, 144, 112, PANNEAU, 8),
            si(eq(V("vueClassement"), 1), [
                self.txt(join(tr("Classement S", "Ranking S"), V("saison")), -44, 98, 12, "cyan", 0),
                self.txt(join(tr("fin dans ", "ends in "), join(V("joursSaison"), tr(" j", " d"))), 136, 98, 11, "gris", 2),
            ], [
                self.txt(tr("Arène", "Arena"), -44, 98, 12, "cyan", 0),
                self.icone_dyn(join("m_division_", V("division")), 4, 101, 60),
                self.txt(join(V("hype"), tr(" hype", " hype")), 16, 98, 12, "jaune", 0),
                self.txt_tr(nom_division, 136, 98, 11, "blanc", 2, 70),
            ]),
            self.txt(tr("Meilleurs joueurs de tous les temps", "All-time best players"), -44, 80, 11, "orange", 0),
            setv("k", 1),
            repeter(3, [
                si(gt(longueur(item("Record_nom", V("k"))), 0), [
                    self.txt_tr(joins(V("k"), ". ", item("Record_nom", V("k")), " — ", item("Record_elims", V("k")), tr(" élim., ", " elims, "),
                                      item("Record_victoires", V("k")), tr(" vict.", " wins")), -44, sub(80, mul(13, V("k"))), 11, "blanc", 0, 186),
                ], [self.txt(join(V("k"), tr(". (libre)", ". (open)")), -44, sub(80, mul(13, V("k"))), 11, "gris", 0)]),
                changev("k", 1),
            ]),
            self.txt(tr("Connectés (par éliminations)", "Online players (by eliminations)"), -44, 24, 11, "orange", 0),
            # tri des emplacements actifs (dont moi) par éliminations décroissantes
            vider("menu_ordre"), setv("k", 1),
            repeter(C.NB_JOUEURS, [
                si(ou(eq(V("k"), V("monSlot")), eq(item("E_actif", V("k")), 1)), [
                    elims_de(V("k")), setv("x", V("tmp")), setv("p", 1), setv("trouve", 0),
                    repeter(long_liste("menu_ordre"), [
                        si(eq(V("trouve"), 0), [
                            elims_de(item("menu_ordre", V("p"))),
                            si(gt(V("x"), V("tmp")), [setv("trouve", 1)], [changev("p", 1)]),
                        ]),
                    ]),
                    inserer("menu_ordre", V("p"), V("k")),
                ]),
                changev("k", 1),
            ]),
            setv("k", 1),
            repeter_jusqua(ou(gt(V("k"), long_liste("menu_ordre")), gt(V("k"), 5)), [
                setv("n", item("menu_ordre", V("k"))), elims_de(V("n")),
                si(eq(V("n"), V("monSlot")), [self.mon_nom(), setv("txt2", V("niveau")), setv("p", "jaune")],
                   [setv("txt", item("E_nom", V("n"))), setv("txt2", item("E_niveau", V("n"))), setv("p", "blanc")]),
                self.txt_tr(joins(V("k"), ". ", V("txt"), tr(" — niv. ", " — lvl "), V("txt2"), " — ", V("tmp"), tr(" élim.", " elims")),
                            -44, sub(24, mul(13, V("k"))), 11, V("p"), 0, 186),
                changev("k", 1),
            ]),
            # --- succès ---
            self.rect(-236, -106, 144, -50, PANNEAU, 8),
            setv("nb", 0), setv("k", 1),
            repeter(long_liste("Succes"), [appel("champ", item("Succes", V("k")), 2), si(eq(V("champ"), 1), [changev("nb", 1)]), changev("k", 1)]),
            self.txt(join(tr("Succès ", "Achievements "), join(V("nb"), "/20")), -228, -66, 12, "cyan", 0),
            setv("i", 1),
            repeter(20, [
                setv("cx", add(-108, mul(22, mod(sub(V("i"), 1), 10)))),
                setv("cy", sub(-62, mul(24, floor(div(sub(V("i"), 1), 10))))),
                setv("trouve", 0),
                si(ge(long_liste("Succes"), V("i")), [appel("champ", item("Succes", V("i")), 2), si(eq(V("champ"), 1), [setv("trouve", 1)])]),
                self.rect_a(20, 20, "#0f172a", V("cx"), V("cy"), 10),
                si(eq(V("trouve"), 1), [self.icone("m_icone_succes", V("cx"), V("cy"), 60)],
                   [effet("GHOST", 55), self.icone("m_icone_succes", V("cx"), V("cy"), 60), effacer_effets()]),
                self.bouton_a(join("succes ", V("i")), 22, 22, V("cx"), V("cy"), "", 11, None),
                si(eq(V("survolId"), join("succes ", V("i"))), [setv("idx", V("i"))]),
                changev("i", 1),
            ]),
            si(gt(V("idx"), 0), [
                setv("i", V("idx")),
                self.txt_tr(join(join(V("i"), ". "), titre_succes), -228, -98, 11, "blanc", 0, 150),
            ], [self.txt(tr("Survole un badge", "Hover a badge"), -228, -98, 11, "gris", 0)]),
            setv("idx", 0),
        ]

    # ======================================================================
    #  PANNEAU PARAMÈTRES (décalé de ox : 0 dans le salon, 46 dans la pause)
    # ======================================================================
    # Réglages : (section, genre, variable, FR, EN, options)
    #   genre num  : options = (min, pas, max)
    #   genre bool : options = None
    #   genre enum : options = [(valeur, FR, EN), ...]
    REGLAGES = [
        ("jeu", "num", "param_sensibilite", "Sensibilité souris / manette", "Mouse / controller sensitivity", (0.25, 0.25, 3)),
        ("jeu", "bool", "param_viseeAssistee", "Visée assistée", "Aim assist", None),
        ("jeu", "bool", "param_constructionTurbo", "Construction turbo", "Turbo building", None),
        ("jeu", "bool", "param_editionRapide", "Édition rapide", "Quick edit", None),
        ("jeu", "bool", "modeConstruction", "Mode construction (clic = mur)", "Build mode (click = wall)", None),
        ("jeu", "enum", "param_tailleHUD", "Taille du HUD", "HUD size", [(80, "80 %", "80 %"), (100, "100 %", "100 %"), (120, "120 %", "120 %")]),
        ("jeu", "enum", "param_langue", "Langue", "Language", [(0, "Français", "French"), (1, "Anglais", "English")]),
        ("jeu", "enum", "param_region", "Région de serveur", "Server region", [(0, "Europe (Scratch)", "Europe (Scratch)"), (1, "Amérique", "America"), (2, "Asie", "Asia")]),
        ("jeu", "bool", "param_afficherPing", "Affichage du ping / latence", "Show ping / latency", None),
        ("jeu", "bool", "param_infosReseau", "Affichage des informations réseau", "Show network info", None),
        ("jeu", "bool", "param_bots", "Bots de remplissage", "Fill bots", None),
        ("jeu", "enum", "bots_difficulte", "Difficulté des bots", "Bot difficulty", [(1, "Facile", "Easy"), (2, "Normale", "Normal"), (3, "Difficile", "Hard")]),
        ("video", "enum", "param_qualite", "Qualité graphique", "Graphics quality", [(i + 1, fr, en) for i, (fr, en) in enumerate(QUALITES)]),
        ("video", "bool", "param_afficherFPS", "Afficher les FPS", "Show FPS", None),
        ("video", "bool", "param_performance", "Mode performance", "Performance mode", None),
        ("video", "bool", "param_effetsDegats", "Effets visuels des dégâts", "Damage visual effects", None),
        ("audio", "num", "param_volumeMusique", "Volume de la musique", "Music volume", (0, 10, 100)),
        ("audio", "num", "param_volumeEffets", "Volume des effets", "Effects volume", (0, 10, 100)),
        ("audio", "num", "param_volumeVoix", "Volume des voix / annonces", "Voice / announcer volume", (0, 10, 100)),
        ("audio", "bool", "param_sousTitres", "Sous-titres", "Subtitles", None),
        ("acces", "enum", "param_daltonisme", "Filtre daltonisme", "Colour-blind filter", [(i, fr, en) for i, (fr, en) in enumerate(DALTONISME)]),
        ("acces", "enum", "param_tailleHUD", "Taille du HUD", "HUD size", [(80, "80 %", "80 %"), (100, "100 %", "100 %"), (120, "120 %", "120 %")]),
        ("acces", "bool", "param_sousTitres", "Sous-titres", "Subtitles", None),
        ("acces", "bool", "param_effetsDegats", "Effets visuels des dégâts", "Damage visual effects", None),
        ("acces", "num", "param_sensibilite", "Sensibilité", "Sensitivity", (0.25, 0.25, 3)),
        ("compte", "enum", "confidentialite", "Confidentialité", "Match privacy", [(i, fr, en) for i, (fr, en) in enumerate(CONFIDENTIALITES)]),
    ]

    def ligne_reglage(self, y, genre, var, fr, en, options, ident):
        ox = V("ox")
        corps = [self.txt_tr(tr(fr, en), add(-126, ox), y - 4, 12, "blanc", 0, 116 if genre == "enum" else 196)]
        if genre == "bool":
            corps.append(si(eq(V(var), 1),
                            [self.bouton(ident + " !", 92, y - 9, 128, y + 9, "ON", 11, VERT, "blanc", 9, ox)],
                            [self.bouton(ident + " !", 92, y - 9, 128, y + 9, "OFF", 11, BOUTON_SOMBRE, "gris", 9, ox)]))
        elif genre == "num":
            corps += [
                self.txt(V(var), add(84, ox), y - 4, 12, "jaune", 2),
                self.bouton(ident + " -", 92, y - 8, 108, y + 8, "–", 13, BOUTON_SOMBRE, "blanc", 4, ox),   # « – » : le signe moins U+2212 n'a pas de glyphe
                self.bouton(ident + " +", 112, y - 8, 128, y + 8, "+", 13, BOUTON_SOMBRE, "blanc", 4, ox),
            ]
            if var.startswith("param_volume"):
                corps.append(self.icone_dyn(join("m_hp_", plafond(div(V(var), 34))), add(54, ox), y, 55))
        else:
            for val, lfr, len_ in options:
                corps.append(si(eq(V(var), val), [self.txt_tr(tr(lfr, len_), add(84, ox), y - 4, 11, "jaune", 2, 92)]))
            corps += [
                self.bouton(ident + " <", 92, y - 8, 108, y + 8, "", 11, BOUTON_SOMBRE, "blanc", 4, ox),
                self.icone("m_fleche_gauche", add(100, ox), y, 36),
                self.bouton(ident + " >", 112, y - 8, 128, y + 8, "", 11, BOUTON_SOMBRE, "blanc", 4, ox),
                self.icone("m_fleche_droite", add(120, ox), y, 36),
            ]
        return corps

    def panneau_parametres(self):
        ox = V("ox")
        corps = [
            self.rect(-236, -106, -140, 142, PANNEAU, 8, dx=ox),
            self.rect(-134, -106, 144, 142, PANNEAU, 8, dx=ox),
        ]
        for n, (code, fr, en) in enumerate(SECTIONS, start=1):
            cy = 126 - 28 * (n - 1)
            corps.append(si(eq(V("section"), n),
                            [self.bouton("section %d" % n, -232, cy - 11, -144, cy + 11, tr(fr, en), 11, BOUTON, "blanc", 6, ox)],
                            [self.bouton("section %d" % n, -232, cy - 11, -144, cy + 11, tr(fr, en), 11, PANNEAU_CLAIR, "gris", 6, ox)]))
        corps.append(self.txt(tr("Paramètres", "Settings"), add(-188, ox), -98, 11, "gris", 1))
        # sections tabulaires
        for n, (code, fr, en) in enumerate(SECTIONS, start=1):
            lignes = []
            y = 124
            for (sec, genre, var, lfr, len_, options) in self.REGLAGES:
                if sec != code:
                    continue
                ident = "s %s" % var
                lignes.append(self.ligne_reglage(y, genre, var, lfr, len_, options, ident))
                y -= 22
            if code == "jeu":
                lignes.append(self.txt_tr(tr("Un seul serveur cloud : région indicative.", "Single cloud server: region is indicative."),
                                          add(-126, ox), y - 2, 11, "gris", 0, 268))
            if code == "video":
                lignes += [
                    self.txt(join(tr("Colonnes de rendu : ", "Render columns: "), V("colonnes")), add(-126, ox), y - 4, 11, "gris", 0),
                    self.txt(join(tr("FPS mesurés : ", "Measured FPS: "), V("fps")), add(-126, ox), y - 20, 11, "gris", 0),
                    self.txt_tr(tr("Perf. : 40 colonnes, sans mur de tempête.", "Perf.: 40 columns, no storm wall."),
                                add(-126, ox), y - 36, 11, "gris", 0, 268),
                ]
            if code == "audio":
                lignes.append(self.txt_tr(tr("Les volumes s'appliquent immédiatement.", "Volumes apply immediately."), add(-126, ox), y - 2, 11, "gris", 0, 268))
            if code == "acces":
                lignes.append(self.txt_tr(tr("Daltonisme : couleurs de tempête et marqueurs.", "Colour-blind: storm and marker colours."),
                                          add(-126, ox), y - 2, 11, "gris", 0, 268))
            if code == "compte":
                lignes += [
                    self.mon_nom(),
                    self.txt(join(tr("Nom d'affichage : ", "Display name: "), V("txt")), add(-126, ox), y - 4, 12, "blanc", 0),
                    self.txt(join(tr("Niveau de compte : ", "Account level: "), V("niveau")), add(-126, ox), y - 28, 12, "blanc", 0),
                    self.txt(tr("Code de sauvegarde", "Save code"), add(-126, ox), y - 52, 12, "blanc", 0),
                    self.bouton("charger sauvegarde", 6, y - 60, 60, y - 42, tr("Charger", "Load"), 11, BOUTON, "blanc", 5, ox),
                    self.bouton("regenerer", 64, y - 60, 140, y - 42, tr("Régénérer", "Regenerate"), 11, BOUTON_SOMBRE, "blanc", 5, ox),
                    si(gt(longueur(V("codeSauvegarde")), 0), [
                        self.txt(C.sous_chaine(V("codeSauvegarde"), 1, 38), add(-126, ox), y - 68, 11, "cyan", 0),
                        self.txt(C.sous_chaine(V("codeSauvegarde"), 39, 38), add(-126, ox), y - 82, 11, "cyan", 0),
                    ], [self.txt(tr("(en attente du module Systèmes)", "(waiting for the Systems module)"), add(-126, ox), y - 68, 11, "gris", 0)]),
                    self.txt(tr("Code créateur", "Creator code"), add(-126, ox), y - 104, 12, "blanc", 0),
                    si(gt(longueur(V("codeCreateur")), 0), [self.txt_tr(V("codeCreateur"), add(-20, ox), y - 104, 12, "cyan", 0, 90)],
                       [self.txt(tr("aucun", "none"), add(-20, ox), y - 104, 12, "gris", 0)]),
                    self.bouton("code createur", 80, y - 112, 140, y - 94, tr("Modifier", "Change"), 11, BOUTON_SOMBRE, "blanc", 5, ox),
                    self.txt_tr(tr("Le code créateur est gardé dans ta sauvegarde.", "The creator code is kept in your save."),
                                add(-126, ox), y - 128, 11, "gris", 0, 268),
                ]
            if code == "commandes":
                lignes = self.section_commandes()
            corps.append(si(eq(V("section"), n), lignes))
        return corps

    def section_commandes(self):
        ox = V("ox")
        corps = [
            self.txt(tr("Clavier", "Keyboard"), add(-126, ox), 120, 12, "blanc", 0),
            si(eq(V("param_clavier"), 0),
               [self.bouton("clavier 0", -40, 114, 24, 132, "AZERTY", 11, BOUTON, "blanc", 5, ox),
                self.bouton("clavier 1", 30, 114, 94, 132, "QWERTY", 11, BOUTON_SOMBRE, "gris", 5, ox)],
               [self.bouton("clavier 0", -40, 114, 24, 132, "AZERTY", 11, BOUTON_SOMBRE, "gris", 5, ox),
                self.bouton("clavier 1", 30, 114, 94, 132, "QWERTY", 11, BOUTON, "blanc", 5, ox)]),
            si(gt(V("attenteTouche"), 0),
               [self.txt(tr("Appuie sur une touche…", "Press a key…"), add(6, ox), -104, 12, "jaune", 1)],
               [self.txt_tr(tr("Clique une action pour changer sa touche.", "Click an action to rebind its key."), add(-126, ox), -104, 11, "gris", 0, 268)]),
        ]
        for a, (code, fr, en) in enumerate(ACTIONS_TOUCHES):
            col, row = a // 10, a % 10
            x1 = -130 + 138 * col
            x2 = x1 + 132
            y = 96 - 20 * row
            ident = "touche %d" % (a + 1)
            corps.append(si(eq(V("attenteTouche"), a + 1),
                            [self.bouton(ident, x1, y - 9, x2, y + 9, "", 11, BOUTON, "blanc", 4, ox)],
                            [self.bouton(ident, x1, y - 9, x2, y + 9, "", 11, PANNEAU_CLAIR, "blanc", 4, ox)]))
            corps.append(self.txt(tr(fr, en), add(x1 + 6, ox), y - 4, 11, "blanc", 0))
            corps.append(si(eq(V("attenteTouche"), a + 1), [self.txt("…", add(x2 - 6, ox), y - 4, 11, "jaune", 2)], [
                appel("nom touche", item("Touches", a + 1)),
                self.txt(V("txt2"), add(x2 - 6, ox), y - 4, 11, "jaune", 2),
            ]))
        return corps

    # ======================================================================
    #  ACTIONS DES BOUTONS
    # ======================================================================
    def _actions(self):
        """Liste de (identifiant, blocs) ; identifiants dynamiques traités à part dans `action`."""
        act = []
        sale = [setv("menu_sale", 1)]

        def ecran(e):
            return [appel("aller ecran", e)]

        act.append(("continuer", [si(eq(V("connecte"), 1), ecran("salon"))]))
        act.append(("charger sauvegarde", [
            demander(tr("Colle ton code de sauvegarde :", "Paste your save code:")),
            si(gt(longueur(reponse()), 0), [diffuser("sauvegarde charger")]), sale]))
        act.append(("langue", [setv("param_langue", sub(1, V("param_langue"))), sale]))
        act.append(("code createur", [
            demander(tr("Code créateur (vide pour retirer) :", "Creator code (empty to remove):")),
            setv("evt_texte", reponse()), diffuser("createur definir"), sale]))
        for nom, _, _ in ONGLETS:
            act.append(("onglet " + nom, [setv("onglet", nom), setv("listeModes", 0), setv("vueClassement", 0), setv("attenteTouche", 0), sale]))
        act.append(("jouer", [setv("enPartie", 1), setv("tCompte", add(chrono(), 5)), ecran("matchmaking")]))
        act.append(("mode", [setv("listeModes", sub(1, V("listeModes"))), sale]))
        for m in range(1, 7):
            act.append(("mode %d" % m, [setv("modeChoisi", m), setv("listeModes", 0), sale]))
        act.append(("ltm -", [setv("ltmChoisi", mod(add(V("ltmChoisi"), 5), 6)), sale]))
        act.append(("ltm +", [setv("ltmChoisi", mod(add(V("ltmChoisi"), 1), 6)), sale]))
        act.append(("remplissage", [setv("remplissage", sub(1, V("remplissage"))), sale]))
        act.append(("confidentialite", [
            setv("confidentialite", mod(add(V("confidentialite"), 1), 3)),
            si(gt(V("confidentialite"), 0), [
                demander(tr("Code du salon (4 chiffres) :", "Lobby code (4 digits):")),
                setv("codeSalon", floor(absv(mul(reponse(), 1)))),
                si(ou(lt(V("codeSalon"), 1), gt(V("codeSalon"), 9999)), [setv("codeSalon", hasard(1000, 9999))]),
            ], [setv("codeSalon", 0)]),
            sale]))
        act.append(("regarder", [setv("etat", 4), setv("enPartie", 0), ecran("spectateur")]))
        act.append(("passe page -", [si(gt(V("pagePasse"), 0), [changev("pagePasse", -1)]), sale]))
        act.append(("passe page +", [si(lt(V("pagePasse"), 3), [changev("pagePasse", 1)]), sale]))
        for n in range(1, 7):
            act.append(("categorie %d" % n, [setv("categorie", n), sale]))
            act.append(("case %d" % n, [setv("caseEmote", n), sale]))
        act.append(("style", [setv("styleSkin", sub(1, V("styleSkin"))), setv("evt_texte", "style"), setv("evt_valeur", V("styleSkin")),
                              diffuser("casier equiper"), sale]))
        act.append(("regenerer", [diffuser("sauvegarde generer"), sale]))
        for n in range(1, 4):
            act.append(("sous %d" % n, [setv("sousOnglet", n), sale]))
        act.append(("classement", [setv("vueClassement", sub(1, V("vueClassement"))), sale]))
        for n in range(1, len(SECTIONS) + 1):
            act.append(("section %d" % n, [setv("section", n), setv("attenteTouche", 0), sale]))
        # réglages
        vus = set()
        for (sec, genre, var, fr, en, options) in self.REGLAGES:
            if var in vus:
                continue
            vus.add(var)
            ident = "s %s" % var
            if genre == "bool":
                act.append((ident + " !", [setv(var, sub(1, V(var))), sale]))
            elif genre == "num":
                mn, pas, mx = options
                act.append((ident + " -", [setv(var, maximum(mn, div(rnd(mul(sub(V(var), pas), 100)), 100))), sale]))
                act.append((ident + " +", [setv(var, minimum(mx, div(rnd(mul(add(V(var), pas), 100)), 100))), sale]))
            else:
                vals = [v for v, _, _ in options]
                suivant = [si(eq(V(var), vals[i]), [setv("tmp", vals[(i + 1) % len(vals)])]) for i in range(len(vals))]
                precedent = [si(eq(V(var), vals[i]), [setv("tmp", vals[(i - 1) % len(vals)])]) for i in range(len(vals))]
                act.append((ident + " >", [setv("tmp", vals[0])] + suivant + [setv(var, V("tmp")), sale]))
                act.append((ident + " <", [setv("tmp", vals[0])] + precedent + [setv(var, V("tmp")), sale]))
        for n, preset in ((0, C.PRESET_AZERTY), (1, C.PRESET_QWERTY)):
            act.append(("clavier %d" % n, [setv("param_clavier", n)] + [remplacer("Touches", i + 1, k) for i, k in enumerate(preset)] + sale))
        for a in range(len(C.TOUCHES)):
            act.append(("touche %d" % (a + 1), [setv("attenteTouche", a + 1), sale]))
        act.append(("annuler", [setv("enPartie", 0), ecran("salon")]))
        # pause
        act.append(("reprendre", ecran(V("ecranPrecedent"))))
        act.append(("pause parametres", [setv("pauseParam", 1), setv("section", 1)]))
        act.append(("pause retour", [setv("pauseParam", 0), setv("attenteTouche", 0)]))
        act.append(("signaler", [setv("superposition", "signaler")]))
        act.append(("camera", [setv("ecranPrecedent", "cinema"), ecran("cinema")]))
        act.append(("quitter", [setv("enPartie", 0), setv("etat", 5), setv("superposition", ""), setv("pauseParam", 0), ecran("salon")]))
        # fin
        act.append(("rejouer", [setv("enPartie", 1), setv("tCompte", add(chrono(), 5)), ecran("matchmaking")]))
        act.append(("salon", [setv("enPartie", 0), setv("etat", 5), ecran("salon")]))
        return act

    def _proc_action(self):
        M = self.M
        corps = []
        for ident, blocs in self._actions():
            corps.append(si(eq(A("id"), ident), blocs))
        # identifiants dynamiques : « acheter n », « casier n », « quete reclamer n », « quete partager n »
        corps += [
            appel("champ", A("id"), 1),     # premier mot (pas de « | » : champ = id entier) → on découpe sur l'espace
            setv("txt", ""), setv("txt2", ""), setv("i", 1), setv("j", 0),
            repeter(longueur(A("id")), [
                setv("tmp", lettre(V("i"), A("id"))),
                si(eq(V("tmp"), " "), [changev("j", 1)], [
                    si(eq(V("j"), 0), [setv("txt", join(V("txt"), V("tmp")))], [setv("txt2", join(V("txt2"), V("tmp")))]),
                ]),
                changev("i", 1),
            ]),
            # txt = premier mot, txt2 = reste (« reclamer 3 » ou un nombre)
            si(eq(V("txt"), "acheter"), [setv("evt_valeur", mul(V("txt2"), 1)), diffuser("boutique acheter"), setv("menu_sale", 1)]),
            si(eq(V("txt"), "casier"), [
                setv("evt_texte", item("menu_types", V("categorie"))), setv("evt_valeur", mul(V("txt2"), 1)), setv("evt_cible", V("caseEmote")),
                diffuser("casier equiper"), setv("menu_sale", 1),
            ]),
            si(eq(V("txt"), "quete"), [
                setv("n", longueur(V("txt2"))), setv("tmp", ""),
                repeter_jusqua(ou(lt(V("n"), 1), eq(lettre(V("n"), V("txt2")), " ")), [setv("tmp", join(lettre(V("n"), V("txt2")), V("tmp"))), changev("n", -1)]),
                setv("evt_valeur", mul(V("tmp"), 1)),
                si(eq(lettre(1, V("txt2")), "r"), [diffuser("quete reclamer")], [diffuser("quete partager")]),
                setv("menu_sale", 1),
            ]),
        ]
        M.proc("action", [("id", "s")], corps, warp=False)

    # ======================================================================
    #  BOUCLE PRINCIPALE
    # ======================================================================
    def _procs_boucle(self):
        M = self.M
        # nom lisible d'une touche → txt2
        M.proc("nom touche", [("k", "s")], [
            setv("txt2", A("k")),
            si(eq(A("k"), "space"), [setv("txt2", tr("Espace", "Space"))]),
            si(eq(A("k"), "up arrow"), [setv("txt2", "↑")]), si(eq(A("k"), "down arrow"), [setv("txt2", "↓")]),
            si(eq(A("k"), "left arrow"), [setv("txt2", "←")]), si(eq(A("k"), "right arrow"), [setv("txt2", "→")]),
        ])
        # signature des données affichées (redessin si elle change)
        M.proc("signature", [], [
            si(eq(V("ecran"), "connexion"), [
                setv("tmp", joins(V("connecte"), "|", V("message"), "|", V("monNom"), "|", V("niveau"), "|", V("astuce"), "|", V("param_langue"))),
            ], [
                si(eq(V("ecran"), "matchmaking"), [
                    setv("tmp", joins(V("👥 Joueurs"), "|", plafond(sub(V("tCompte"), chrono())), "|", rnd(div(V("latence"), 20)), "|", V("phase"), "|", V("param_langue"))),
                ], [
                    setv("tmp", joins(V("onglet"), "|", V("jetons"), "|", V("niveau"), "|", V("modeChoisi"), "|", V("ltmChoisi"), "|", V("remplissage"), "|",
                                      V("confidentialite"), "|", V("codeSalon"), "|", V("phase"), "|", V("vivants"), "|", V("passeNiveau"), "|", V("etoiles"), "|",
                                      V("xpNiveau"), "|", V("param_langue"), "|", V("skin"), "|", V("styleSkin"), "|", V("banniere"), "|", V("pioche"), "|",
                                      V("planeur"), "|", V("spray"), "|", V("codeSauvegarde"), "|", V("codeCreateur"), "|", long_liste("QuetesActives"), "|",
                                      long_liste("Boutique"), "|", long_liste("Possedes"), "|", V("hype"), "|", V("division"), "|", V("astuce"), "|",
                                      V("param_sensibilite"), V("param_viseeAssistee"), V("param_constructionTurbo"), V("param_editionRapide"),
                                      V("modeConstruction"), V("param_tailleHUD"), V("param_region"), V("param_afficherPing"), V("param_infosReseau"),
                                      V("param_qualite"), V("param_afficherFPS"), V("param_performance"), V("param_effetsDegats"), V("param_volumeMusique"),
                                      V("param_volumeEffets"), V("param_volumeVoix"), V("param_sousTitres"), V("param_daltonisme"), V("param_clavier"),
                                      "|", Lst("Touches"), "|", Lst("EmotesEquipees"))),
                ]),
            ]),
            si(non(eq_txt(V("tmp"), V("signature"))), [setv("signature", V("tmp")), setv("menu_sale", 1)]),
        ])
        # dessin complet de l'écran courant
        M.proc("dessiner", [], [
            setv("txt_ombre", 1),
            si(eq(V("ecran"), "connexion"), self.ecran_connexion()),
            si(eq(V("ecran"), "salon"), self.ecran_salon()),
            si(eq(V("ecran"), "matchmaking"), self.ecran_matchmaking()),
            si(eq(V("ecran"), "chargement"), self.ecran_chargement()),
            si(eq(V("ecran"), "pause"), [setv("txt_ombre", 0), self.ecran_pause()]),
            si(eq(V("ecran"), "fin"), self.ecran_fin()),
            setv("txt_ombre", 1),
        ])
        est_menu = ou3(eq(V("ecran"), "connexion"), eq(V("ecran"), "salon"), eq(V("ecran"), "matchmaking"))
        est_superpose = ou(eq(V("ecran"), "pause"), eq(V("ecran"), "fin"))
        detection = [setv("txt2", "")] + [si(et(eq(V("txt2"), ""), touche(k)), [setv("txt2", k)]) for k in TOUCHES_CANDIDATES]
        M.proc("image", [], [
            si(eq(V("menu_rafraichi"), 1), [setv("menu_rafraichi", 0)]),
            # entrée sur un écran décidée par un autre module : (re)lancer les minuteries
            si(non(eq(V("ecran"), V("ecranAvant"))), [
                setv("ecranAvant", V("ecran")), setv("menu_sale", 1),
                si(et(eq(V("ecran"), "matchmaking"), lt(V("tCompte"), chrono())), [setv("tCompte", add(chrono(), 5))]),
                si(et(eq(V("ecran"), "chargement"), lt(V("tChargement"), sub(chrono(), 2.5))), [setv("tChargement", chrono())]),
            ]),
            # --- touches pause / carte (front descendant) ---
            si(et(eq(V("superposition"), ""), eq(V("attenteTouche"), 0)), [
                si(touche(C.touche_config("pause")), [
                    si(eq(V("pauseAvant"), 0), [
                        setv("pauseAvant", 1),
                        si(ou3(eq(V("ecran"), "jeu"), eq(V("ecran"), "spectateur"), eq(V("ecran"), "cinema")), [
                            setv("ecranPrecedent", V("ecran")), appel("aller ecran", "pause"),
                        ], [
                            si(eq(V("ecran"), "pause"), [
                                si(eq(V("pauseParam"), 1), [setv("pauseParam", 0)], [appel("aller ecran", V("ecranPrecedent"))]),
                            ]),
                        ]),
                    ]),
                ], [setv("pauseAvant", 0)]),
                si(touche(C.touche_config("carte")), [
                    si(eq(V("carteAvant"), 0), [
                        setv("carteAvant", 1),
                        si(eq(V("ecran"), "jeu"), [appel("aller ecran", "carte")], [si(eq(V("ecran"), "carte"), [appel("aller ecran", "jeu")])]),
                    ]),
                ], [setv("carteAvant", 0)]),
            ]),
            # --- attente d'une touche à configurer ---
            si(gt(V("attenteTouche"), 0), detection + [
                si(gt(longueur(V("txt2")), 0), [
                    remplacer("Touches", V("attenteTouche"), V("txt2")), setv("attenteTouche", 0), setv("menu_sale", 1), appel("son", "clic"),
                ]),
            ]),
            # --- minuteries ---
            si(ou(eq(V("ecran"), "connexion"), eq(V("ecran"), "salon")), [
                si(gt(chrono(), V("tAstuce")), [setv("astuce", mod(add(V("astuce"), 1), NB_ASTUCES)), setv("tAstuce", add(chrono(), 6))]),
            ]),
            si(eq(V("ecran"), "matchmaking"), [
                si(gt(chrono(), V("tCompte")), [setv("tChargement", chrono()), setv("astuce", hasard(0, NB_ASTUCES - 1)), appel("aller ecran", "chargement")]),
            ]),
            # --- souris : survol et clic sur MES boutons ---
            si(gt(long_liste("menu_bid"), 0), [
                si(ou3(non(eq(souris_x(), V("sx0"))), non(eq(souris_y(), V("sy0"))), eq(V("menu_sale"), 1)), [
                    setv("sx0", souris_x()), setv("sy0", souris_y()),
                    appel("chercher bouton"),
                    si(non(eq(V("clicId"), V("survolId"))), [
                        setv("survolId", V("clicId")), setv("menu_survolId", V("clicId")), setv("survol", V("survolN")), setv("menu_sale", 1),
                        si(gt(longueur(V("clicId")), 0), [appel("son", "survol")]),
                    ]),
                ]),
                si(souris_bas(), [
                    si(eq(V("sourisAvant"), 0), [
                        setv("sourisAvant", 1),
                        appel("chercher bouton"),
                        si(gt(longueur(V("clicId")), 0), [appel("son", "clic"), appel("action", V("clicId"))]),
                    ]),
                ], [setv("sourisAvant", 0)]),
            ], [
                si(souris_bas(), [setv("sourisAvant", 1)], [setv("sourisAvant", 0)]),
                si(gt(longueur(V("survolId")), 0), [setv("survolId", ""), setv("menu_survolId", "")]),
            ]),
            # --- dessin ---
            si(est_menu, [
                appel("signature"),
                si(eq(V("menu_sale"), 1), [
                    appel("vider boutons"), effacer(), appel("dessiner"), setv("menu_sale", 0), setv("menu_rafraichi", 1), changev("nbDessins", 1),
                ]),
            ], [
                si(eq(V("ecran"), "chargement"), [appel("vider boutons"), effacer(), appel("dessiner"), setv("menu_sale", 0)], [
                    si(est_superpose, [appel("vider boutons"), appel("dessiner"), setv("menu_sale", 0)], [
                        si(gt(long_liste("menu_bid"), 0), [appel("vider boutons")]),
                    ]),
                ]),
            ]),
        ])

    def _scripts(self):
        M = self.M
        M.script(quand_drapeau(), [
            cacher(), aller(0, 0), setv("txt_ombre", 1),
            setv("ecran", "connexion"), setv("onglet", "accueil"), setv("menu_sale", 1), setv("menu_rafraichi", 0), setv("menu_survolId", ""),
            setv("survolId", ""), setv("clicId", ""), setv("sourisAvant", 1), setv("sx0", 9999), setv("sy0", 9999), setv("signature", ""),
            setv("ox", 0), setv("pauseAvant", 1), setv("carteAvant", 1), setv("listeModes", 0), setv("sousOnglet", 1), setv("section", 1),
            setv("pagePasse", 0), setv("categorie", 1), setv("caseEmote", 1), setv("pauseParam", 0), setv("attenteTouche", 0),
            setv("tCompte", 0), setv("tChargement", 0), setv("astuce", hasard(0, NB_ASTUCES - 1)), setv("tAstuce", add(chrono(), 6)),
            setv("vueClassement", 0), setv("idx", 0), setv("nbDessins", 0), setv("ecranAvant", ""),
            appel("vider boutons"),
            attendre(0.4),              # les costumes SVG se chargent de façon asynchrone
            setv("menu_sale", 1),
            toujours([appel("image")]),
        ])
        for evt in ["evt changement ecran", "evt record", "evt quete", "evt achat", "evt niveau", "evt succes"]:
            M.script(quand_message(evt), [setv("menu_sale", 1)])

    def construire(self):
        # tables de textes indexées
        self.k_astuces = self.table(ASTUCES)
        lignes = [_couper(fr, en) for fr, en in ASTUCES]
        self.k_astuces_l1 = self.table([(l[0][0], l[1][0]) for l in lignes])
        self.k_astuces_l2 = self.table([(l[0][1], l[1][1]) for l in lignes])
        self.k_astuces_l3 = self.table([(l[0][2], l[1][2]) for l in lignes])
        self.k_astuces_l4 = self.table([(l[0][3], l[1][3]) for l in lignes])
        self.k_regions = self.table(REGIONS)
        self.k_confid = self.table(CONFIDENTIALITES)
        self.k_types = self.table([(fr, en) for _, fr, en, _ in COSMETIQUES])
        self.M.liste("menu_types", [code for code, _, _, _ in COSMETIQUES])
        self.M.liste("menu_nbCosmetiques", [nb for _, _, _, nb in COSMETIQUES])
        self._proc_action()
        self._procs_boucle()
        self._scripts()


def _couper(fr, en, largeur=112, taille_px=11, nb=4):
    """Coupe une astuce en `nb` lignes de `largeur` px max (chaque langue)."""
    def lignes(t):
        mots, out, cour = t.split(" "), [], ""
        for m in mots:
            essai = (cour + " " + m).strip()
            if texte.largeur_px(essai, taille_px) <= largeur or not cour:
                cour = essai
            else:
                out.append(cour)
                cour = m
        if cour:
            out.append(cour)
        while len(out) < nb:
            out.append(" ")
        if len(out) > nb:
            out = out[:nb - 1] + [" ".join(out[nb - 1:])]
        return out
    return lignes(fr), lignes(en)


def construire(P):
    Menus(P).construire()
