#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test de la banque d'icônes (royale/svg_ui.py) : chaque SVG est un XML valide (minidom), a la
taille annoncée, est déterministe (deux appels identiques), ne contient pas de valeur invalide
(nan/None) ni de <text> hors carte complète et logo ; l'ensemble se génère en moins de 2 s.

    python3 outils/demos/svg_ui/test_svg.py
"""
import os
import re
import sys
import time
from xml.dom import minidom

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..", "..")))
from royale import svg_ui as UI, contrat as C  # noqa: E402


def cas_de_test():
    """Liste de (libellé, fabrique sans argument, largeur, hauteur)."""
    cas = []
    for c in range(1, 9):
        cas.append(("icone_objet(%d)" % c, lambda c=c: UI.icone_objet(c), 48, 48))
    for t in ("legeres", "cartouches", "lourdes"):
        cas.append(("icone_munitions(%s)" % t, lambda t=t: UI.icone_munitions(t), 32, 32))
    for c in (1, 2, 3):
        cas.append(("icone_materiau(%d)" % c, lambda c=c: UI.icone_materiau(c), 32, 32))
    for s in range(1, 11):
        for p, (w, h) in UI.POSES.items():
            for st in (0, 1):
                cas.append(("personnage(%d,%s,%d)" % (s, p, st), lambda s=s, p=p, st=st: UI.personnage(s, p, st), w, h))
    assert len(UI.NOMS_PIOCHES) == 9 and len(UI.NOMS_PLANEURS) == 9 and len(UI.NOMS_BANNIERES) == 10 and len(UI.NOMS_SKINS) == 10
    for n in range(1, len(UI.NOMS_PIOCHES) + 1):
        cas.append(("pioche(%d)" % n, lambda n=n: UI.pioche(n), 48, 48))
    for n in range(1, len(UI.NOMS_PLANEURS) + 1):
        cas.append(("planeur(%d)" % n, lambda n=n: UI.planeur(n), 64, 48))
    for n in range(1, len(C.SPRAYS) + 1):
        cas.append(("spray(%d)" % n, lambda n=n: UI.spray(n), 64, 64))
    for n in range(1, len(C.EMOTES) + 1):
        cas.append(("emote(%d)" % n, lambda n=n: UI.emote(n), 48, 48))
    for n in range(1, len(UI.NOMS_BANNIERES) + 1):
        cas.append(("banniere(%d)" % n, lambda n=n: UI.banniere(n), 40, 40))
    for n in range(1, 8):
        cas.append(("division(%d)" % n, lambda n=n: UI.division(n), 48, 48))
    for n in range(1, 4):
        cas.append(("medaille(%d)" % n, lambda n=n: UI.medaille(n), 48, 48))
    cas += [("bus", UI.bus, 64, 40), ("parachute_icone", UI.parachute_icone, 32, 32), ("planeur_icone", UI.planeur_icone, 32, 32),
            ("marqueur", lambda: UI.marqueur("#facc15"), 24, 36), ("carte_redeploiement", UI.carte_redeploiement, 32, 40),
            ("balise", UI.balise, 40, 60), ("coffre_ouvert", UI.coffre_ouvert, 60, 50), ("boussole_curseur", UI.boussole_curseur, 16, 16),
            ("jeton", UI.jeton, 24, 24), ("etoile", UI.etoile, 24, 24), ("cadenas", UI.cadenas, 24, 24), ("coche", UI.coche, 24, 24),
            ("croix", UI.croix, 24, 24), ("marqueur(vide)", lambda: UI.marqueur(""), 24, 36),
            ("bus_carte", UI.bus_carte, 30, 18), ("parachute_carte", UI.parachute_carte, 14, 16), ("coffre_carte", UI.coffre_carte, 8, 8)]
    for d in ("haut", "bas", "gauche", "droite"):
        cas.append(("fleche(%s)" % d, lambda d=d: UI.fleche(d), 24, 24))
    for o in C.ONGLETS:
        cas.append(("icone_onglet(%s)" % o, lambda o=o: UI.icone_onglet(o), 32, 32))
    for q in ("quotidienne", "hebdomadaire", "histoire", 1, 2, 3):
        cas.append(("icone_quete(%s)" % q, lambda q=q: UI.icone_quete(q), 32, 32))
    cas.append(("icone_succes", UI.icone_succes, 32, 32))
    for e in ("enligne", "enpartie", "horsligne"):
        cas.append(("icone_ami(%s)" % e, lambda e=e: UI.icone_ami(e), 24, 24))
    for n in (0, 1, 2, 3, 34, 68, 102, -1, "x"):
        cas.append(("icone_haut_parleur(%s)" % n, lambda n=n: UI.icone_haut_parleur(n), 24, 24))
    cas += [("icone_oeil", UI.icone_oeil, 24, 24), ("icone_signaler", UI.icone_signaler, 24, 24), ("icone_zone", UI.icone_zone, 24, 24),
            ("icone_bruit", UI.icone_bruit, 24, 24), ("fleche_degats", UI.fleche_degats, 48, 48)]
    for p in (0, 1, 25, 50, 75, 99, 100, 150, -5):
        cas.append(("cercle_interaction(%d)" % p, lambda p=p: UI.cercle_interaction(p), 64, 64))
    for (w, h, p) in ((120, 14, 60), (200, 20, 0), (80, 10, 100), (150, 16, 120), (10, 10, 50), (60, 60, 50), (8, 6, 100)):
        cas.append(("barre(%d,%d,%d)" % (w, h, p), lambda w=w, h=h, p=p: UI.barre(w, h, "#22c55e", p), w, h))
    # tailles trop petites : bornées (jamais de dimension négative) ; pourcentage non numérique = 0
    cas += [("barre(0,0)", lambda: UI.barre(0, 0, "#22c55e", 50), 8, 6), ("barre(2,2)", lambda: UI.barre(2, 2, "#22c55e", 50), 8, 6),
            ("barre(abc)", lambda: UI.barre(120, 14, "#22c55e", "abc"), 120, 14), ("barre(None)", lambda: UI.barre(120, 14, "#22c55e", None), 120, 14),
            ("cercle_interaction(abc)", lambda: UI.cercle_interaction("abc"), 64, 64), ("cercle_interaction(None)", lambda: UI.cercle_interaction(None), 64, 64),
            ("bouton(0,0)", lambda: UI.bouton(0, 0), 8, 8), ("bouton(10,10)", lambda: UI.bouton(10, 10), 10, 10),
            ("panneau(2,2)", lambda: UI.panneau(2, 2), 8, 8), ("panneau(10,10)", lambda: UI.panneau(10, 10), 10, 10),
            ("carte_complete(0)", lambda: UI.carte_complete(0), 32, 32), ("carte_complete(1)", lambda: UI.carte_complete(1), 32, 32)]
    for (w, h, sv) in ((120, 36, False), (120, 36, True), (200, 48, True)):
        cas.append(("bouton(%d,%d,%s)" % (w, h, sv), lambda w=w, h=h, sv=sv: UI.bouton(w, h, sv), w, h))
    cas += [("panneau", lambda: UI.panneau(200, 100), 200, 100), ("onglet_fond(actif)", lambda: UI.onglet_fond(True), 120, 40),
            ("onglet_fond(inactif)", lambda: UI.onglet_fond(False), 120, 40),
            ("carte_complete", UI.carte_complete, 320, 320), ("carte_complete(5)", lambda: UI.carte_complete(5), 160, 160),
            ("carte_complete(7)", lambda: UI.carte_complete(7), 224, 224),
            ("carte_minimap", UI.carte_minimap, 109, 109), ("logo", UI.logo, 300, 80)]
    for v in ("connexion", "salon", "matchmaking", "chargement", "victoire", "defaite", "fin", "tempete", "ciel"):
        cas.append(("fond_ecran(%s)" % v, lambda v=v: UI.fond_ecran(v), 480, 360))
    return cas


def main():
    cas = cas_de_test()
    erreurs = []
    t0 = time.time()
    rendus = [(nom, f(), w, h) for nom, f, w, h in cas]
    duree = time.time() - t0
    for (nom, s, w, h), (_, f, _, _) in zip(rendus, cas):
        try:
            racine = minidom.parseString(s.encode("utf-8")).documentElement
        except Exception as e:  # noqa: BLE001
            erreurs.append("%s : XML invalide (%s)" % (nom, e))
            continue
        if racine.tagName != "svg" or racine.getAttribute("xmlns") != "http://www.w3.org/2000/svg":
            erreurs.append("%s : racine <svg> sans espace de noms" % nom)
        if racine.getAttribute("width") != str(w) or racine.getAttribute("height") != str(h):
            erreurs.append("%s : taille %s×%s au lieu de %d×%d" % (nom, racine.getAttribute("width"), racine.getAttribute("height"), w, h))
        if racine.getAttribute("viewBox") != "0 0 %d %d" % (w, h):
            erreurs.append("%s : viewBox %r" % (nom, racine.getAttribute("viewBox")))
        if re.search(r"\bnan\b|\binf\b", s, re.I) or "None" in s:
            erreurs.append("%s : valeur invalide (nan/None/inf)" % nom)
        if "<text" in s and not (nom.startswith("carte_complete") or nom == "logo"):
            erreurs.append("%s : contient du texte" % nom)
        if f() != s:
            erreurs.append("%s : non déterministe" % nom)
        for m in re.finditer(r'url\(#([^)]+)\)', s):
            if ('id="%s"' % m.group(1)) not in s:
                erreurs.append("%s : référence #%s sans définition" % (nom, m.group(1)))
        neg = re.findall(r'\b(?:width|height|r|rx|ry|stroke-width|font-size)="-[0-9.]+"', s)
        if neg:
            erreurs.append("%s : dimension négative %s" % (nom, neg[:3]))
    # erreurs attendues sur arguments invalides (toujours KeyError, même pour une valeur non numérique)
    for libelle, appel in (("icone_objet(9)", lambda: UI.icone_objet(9)), ("icone_objet(x)", lambda: UI.icone_objet("x")),
                           ("icone_objet(None)", lambda: UI.icone_objet(None)), ("personnage(11)", lambda: UI.personnage(11, "debout")),
                           ("personnage(0)", lambda: UI.personnage(0, "debout")), ("personnage pose", lambda: UI.personnage(1, "assis")),
                           ("fleche(x)", lambda: UI.fleche("x")), ("fleche(1)", lambda: UI.fleche(1)),
                           ("fond_ecran(x)", lambda: UI.fond_ecran("x")), ("icone_onglet(x)", lambda: UI.icone_onglet("x")),
                           ("icone_munitions(1)", lambda: UI.icone_munitions(1)), ("icone_materiau(0)", lambda: UI.icone_materiau(0)),
                           ("pioche(10)", lambda: UI.pioche(10)), ("planeur(10)", lambda: UI.planeur(10)), ("banniere(11)", lambda: UI.banniere(11)),
                           ("spray(0)", lambda: UI.spray(0)), ("emote(7)", lambda: UI.emote(7)), ("division(8)", lambda: UI.division(8)),
                           ("medaille(4)", lambda: UI.medaille(4)), ("icone_quete(4)", lambda: UI.icone_quete(4)),
                           ("icone_ami(x)", lambda: UI.icone_ami("x")), ("barre(x,x)", lambda: UI.barre("x", "x", "#fff", 1))):
        try:
            appel()
            erreurs.append("%s : aurait dû lever KeyError" % libelle)
        except KeyError:
            pass
        except Exception as e:  # noqa: BLE001
            erreurs.append("%s : %s au lieu de KeyError" % (libelle, type(e).__name__))
    # utilitaires de couleur tolérants
    if UI.eclaircir("#fff") != "#ffffff" or UI.eclaircir("red") != "red" or UI.assombrir("#000000", 0.5) != "#000000":
        erreurs.append("eclaircir/assombrir : couleurs courtes ou nommées mal gérées")
    # alias numériques : même rendu que la chaîne
    if UI.icone_quete(2) != UI.icone_quete("hebdomadaire") or UI.icone_haut_parleur(34) != UI.icone_haut_parleur(1) \
            or UI.icone_haut_parleur(68) != UI.icone_haut_parleur(2) or UI.icone_haut_parleur(102) != UI.icone_haut_parleur(3) \
            or UI.icone_haut_parleur(0) != UI.icone_haut_parleur("x"):
        erreurs.append("alias numériques (icone_quete, icone_haut_parleur) incohérents")
    # les noms du catalogue de mod_systemes doivent correspondre (casier, boutique, passe)
    try:
        from royale import mod_systemes as MS
        for a, b, quoi in ((UI.NOMS_SKINS, MS.NOMS_SKINS, "skins"), (UI.NOMS_PIOCHES, MS.NOMS_PIOCHES, "pioches"),
                           (UI.NOMS_PLANEURS, MS.NOMS_PLANEURS, "planeurs"), (UI.NOMS_BANNIERES, MS.NOMS_BANNIERES, "bannières")):
            if list(a) != [fr for fr, _ in b]:
                erreurs.append("noms de %s différents de mod_systemes : %s / %s" % (quoi, a, [fr for fr, _ in b]))
    except ImportError:
        pass
    taille = sum(len(s) for _, s, _, _ in rendus)
    print("%d SVG générés en %.2f s (%d Ko), %d erreur(s)" % (len(rendus), duree, taille // 1024, len(erreurs)))
    for e in erreurs:
        print("  ✘ " + e)
    if duree > 2.0:
        print("  ✘ trop lent (%.2f s > 2 s)" % duree)
        erreurs.append("lent")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
