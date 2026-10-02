# -*- coding: utf-8 -*-
"""
MOTEUR DE TEXTE du projet Royale 3D.

Scratch n'a pas de bloc « écrire » : on tamponne au stylo des costumes-glyphes
(un costume SVG par caractère) en les colorant par les effets graphiques.

Usage (Python, côté générateur) :

    from royale import texte
    texte.installer(S)                       # S : une Cible (sprite), police "Sans Serif" par défaut
    S.script(quand_drapeau(), [
        appel("ecrire", "Victoire Royale !", 0, 100, 32, "or", 1),      # texte, x, y(ligne de base), taille, couleur, alignement
        appel("largeur texte", "Jouer", 20),                            # → txt_largeur (px)
        appel("ecrire tronque", "Un très long titre", -200, 0, 16, "blanc", 0, 120),
        appel("ecrire nombre", 12345.678, 0, -40, 24, "jaune", 1),
    ])

Blocs personnalisés ajoutés au sprite (tous en « warp », sans rafraîchissement) :
    ecrire %s %n %n %n %s %n            (texte, x, y, taille, couleur, alignement)
    largeur texte %s %n                 (texte, taille)  → variable locale txt_largeur
    ecrire tronque %s %n %n %n %s %n %n (texte, x, y, taille, couleur, alignement, largeurMax)
    ecrire nombre %n %n %n %n %s %n     (nombre, x, y, taille, couleur, alignement)
    (internes) txt_passe %n %n %n, txt_dessiner %n %n %n %s %n

Conventions :
  - (x, y) : début de la ligne de base (alignement 0), centre (1) ou fin (2).
  - taille : hauteur de la boîte de glyphe en px (10 à 60). Une majuscule mesure 0.7 × taille.
  - couleur : "blanc" "noir" "gris" "rouge" "orange" "jaune" "or" "vert" "cyan" "bleu" "violet" "rose"
    (voir COULEURS ; nom inconnu → blanc).
  - txt_ombre (variable locale, 1 par défaut) : ombre noire décalée de (+1, −1) × taille/20.
  - txt_espacement (variable locale, 0 par défaut) : interlettrage en px à la taille 40.
  - Caractère inconnu → ignoré. L'espace avance de 0.3 × taille.
  - Coût : 1 tampon par glyphe et par passe (2 passes avec ombre) ; mesuré dans
    Chromium : 80 caractères ombrés = 128 tampons (64 non-espaces × 2), ~9 ms par
    image en OpenGL logiciel.
  - Les effets graphiques du sprite sont remis à zéro après chaque écriture ; son
    costume et sa taille sont modifiés (le sprite est censé rester caché).
  - txt_largeur est écrasée par toute écriture : lire sa valeur juste après
    « largeur texte » (ou l'évaluer dans l'argument de l'écriture suivante).

Limites connues :
  - Les images SVG des costumes se chargent de façon asynchrone après le chargement
    du projet : un tampon fait dans la toute première image après le drapeau peut
    être vide (attendre ~0.5 s ou redessiner l'écran).
  - La clôture de scène de Scratch empêche un glyphe de sortir de la scène de plus
    de ~15 px : un texte qui dépasse le bord voit ses derniers glyphes s'empiler sur
    le bord (utiliser « ecrire tronque »).
  - `lettre de` travaille en unités UTF-16 : les émojis hors BMP sont reconnus par
    paire de substitution (👍 seulement dans le jeu de glyphes).
  - Les blocs personnalisés ne sont appelables que depuis leur sprite : chaque
    sprite qui écrit du texte doit appeler installer() (163 costumes, SVG partagés
    dans le .sb3).
  - Polices : seule « Sans Serif » couvre tout le jeu de caractères ; « Scratch »
    n'a pas d'accents, « Pixel »/« Marker »/« Handwriting » ignorent ² (et –, ×).

Remarque DSL : `Cible.proc` écrit tous les arguments non booléens « %s » dans le
proccode Scratch (pas de %n) ; l'appel se fait par le nom seul, ce qui n'a
aucune incidence. Un sprite doit avoir `layer >= 1` (layerOrder) pour que le .sb3
soit valide.
"""
import math
from xml.sax.saxutils import escape

from .dsl import (Arg, Var, add, sub, mul, div, rnd, eq, gt, lt, non, ou, join, lettre, longueur,
                  item, num_item, long_liste, ajouter_liste, supprimer, vider,
                  setv, changev, si, repeter, repeter_jusqua, costume, costume_numero, taille,
                  aller, tampon, effet, effacer_effets, appel)

# ---------------------------------------------------------------------------
#  Jeu de caractères
# ---------------------------------------------------------------------------
CAP_REFERENCE = 28          # hauteur d'une majuscule (px) pour la boîte de référence de 40 px
BOITE = 40                  # hauteur de référence : « taille » = hauteur de boîte en px
LARGEUR_ESPACE = 12         # avance de l'espace à la taille 40 (0.3 × taille)

# Caractères dessinés avec la police (balise <text>)
CARACTERES_POLICE = (
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"
    "éèêëàâäçùûüôöîïÿœæÉÈÊËÀÂÄÇÙÛÜÔÖÎÏŒÆ"
    ".,:;!?'\"-_/()[]{}+*=%#&<>@°²|\\~^`$€…«»’‘“”–—×"
)
# Symboles dessinés en vectoriel (identiques quelle que soit la police)
SYMBOLES = "★☆♥❤●○✔✘→←↑↓▶◀▲▼■□👍"

# ---------------------------------------------------------------------------
#  Couleurs : nom -> (effet couleur, effet luminosité, effet fantôme)
#  Les glyphes sont rouge pur #ff0000 : l'effet couleur tourne la teinte
#  (200 unités = 360°), la luminosité ajoute v/100 aux canaux RVB (+100 → blanc,
#  −100 → noir), le fantôme rend transparent (gris = blanc + fantôme 45).
# ---------------------------------------------------------------------------
COULEURS = {
    "blanc": (0, 100, 0),
    "noir": (0, -100, 0),
    "gris": (0, 100, 45),
    "rouge": (0, 12, 0),
    "orange": (18, 5, 0),
    "jaune": (33, 10, 0),
    "or": (24, 0, 0),
    "vert": (70, 15, 0),
    "cyan": (100, 10, 0),
    "bleu": (133, 35, 0),
    "violet": (150, 25, 0),
    "rose": (183, 30, 0),
}


def couleurs():
    """Dict nom → (effet couleur 0-200, effet luminosité −100..100, effet fantôme 0-100)."""
    return dict(COULEURS)


# ---------------------------------------------------------------------------
#  Mesures des polices Scratch (générées par outils/demos/texte/mesurer_polices.py)
#  fs : taille de police (px) pour une majuscule de 28 px ; montee / descente /
#  debord_gauche : dépassements maximaux des glyphes (px) autour de l'origine.
# ---------------------------------------------------------------------------
# Table générée par outils/demos/texte/mesurer_polices.py (fontTools) — ne pas éditer à la main.
POLICES = {
    'Sans Serif': {
        'fs': 39.22,
        'montee': 36.9,
        'descente': 9.4,
        'debord_gauche': 3.0,
        'largeurs': {
            '!': 10.75, '"': 16.75, '#': 25.33, '$': 22.43, '%': 33.41, '&': 28.9, "'": 9.29, '(': 12.24,
            ')': 12.24, '*': 21.53, '+': 22.43, ',': 10.71, '-': 12.63, '.': 10.71, '/': 15.06, '0': 22.43,
            '1': 22.43, '2': 22.43, '3': 22.43, '4': 22.43, '5': 22.43, '6': 22.43, '7': 22.43, '8': 22.43,
            '9': 22.43, ':': 10.71, ';': 10.71, '<': 22.43, '=': 22.43, '>': 22.43, '?': 17.53, '@': 35.22,
            'A': 25.65, 'B': 25.73, 'C': 24.82, 'D': 28.75, 'E': 21.84, 'F': 20.71, 'G': 28.51, 'H': 29.33,
            'I': 13.88, 'J': 11.37, 'K': 24.78, 'L': 21.02, 'M': 36.0, 'N': 30.43, 'O': 30.78, 'P': 24.0,
            'Q': 30.78, 'R': 24.82, 'S': 21.57, 'T': 22.08, 'U': 28.94, 'V': 24.12, 'W': 36.9, 'X': 23.92,
            'Y': 22.86, 'Z': 22.51, '[': 12.94, '\\': 15.06, ']': 12.94, '^': 22.43, '_': 17.02, '`': 11.96,
            'a': 22.51, 'b': 24.31, 'c': 19.22, 'd': 24.31, 'e': 22.43, 'f': 14.0, 'g': 24.31, 'h': 24.71,
            'i': 10.67, 'j': 10.67, 'k': 21.92, 'l': 10.67, 'm': 37.22, 'n': 24.71, 'o': 23.88, 'p': 24.31,
            'q': 24.31, 'r': 16.67, 's': 18.98, 't': 15.02, 'u': 24.71, 'v': 20.63, 'w': 31.65, 'x': 21.29,
            'y': 20.67, 'z': 18.63, '{': 15.06, '|': 21.61, '}': 15.06, '~': 22.43, '«': 21.18, '°': 16.78,
            '²': 14.08, '»': 21.18, 'À': 25.65, 'Â': 25.65, 'Ä': 25.65, 'Æ': 35.37, 'Ç': 24.82, 'È': 21.84,
            'É': 21.84, 'Ê': 21.84, 'Ë': 21.84, 'Î': 13.88, 'Ï': 13.88, 'Ô': 30.78, 'Ö': 30.78, '×': 22.43,
            'Ù': 28.94, 'Û': 28.94, 'Ü': 28.94, 'à': 22.51, 'â': 22.51, 'ä': 22.51, 'æ': 34.51, 'ç': 19.22,
            'è': 22.43, 'é': 22.43, 'ê': 22.43, 'ë': 22.43, 'î': 10.67, 'ï': 10.67, 'ô': 23.88, 'ö': 23.88,
            'ù': 24.71, 'û': 24.71, 'ü': 24.71, 'ÿ': 20.67, 'Œ': 36.9, 'œ': 37.45, '–': 19.61, '—': 39.22,
            '‘': 7.33, '’': 7.33, '“': 15.06, '”': 15.06, '…': 31.76, '€': 22.43,
        },
    },
    'Serif': {
        'fs': 41.85,
        'montee': 36.7,
        'descente': 10.5,
        'debord_gauche': 3.5,
        'largeurs': {
            '!': 12.1, '"': 14.86, '#': 22.01, '$': 20.93, '%': 36.04, '&': 30.13, "'": 7.66, '(': 14.19,
            ')': 14.19, '*': 18.37, '+': 22.22, ',': 12.56, '-': 13.06, '.': 12.56, '/': 13.81, '0': 20.93,
            '1': 20.93, '2': 20.93, '3': 20.93, '4': 20.93, '5': 20.93, '6': 20.93, '7': 20.93, '8': 20.93,
            '9': 20.93, ':': 12.56, ';': 12.56, '<': 22.22, '=': 22.22, '>': 22.22, '?': 17.41, '@': 34.95,
            'A': 27.79, 'B': 26.33, 'C': 26.41, 'D': 29.72, 'E': 25.24, 'F': 24.23, 'G': 28.54, 'H': 33.02,
            'I': 15.53, 'J': 15.65, 'K': 27.92, 'L': 24.94, 'M': 37.75, 'N': 30.76, 'O': 29.59, 'P': 24.65,
            'Q': 29.59, 'R': 27.25, 'S': 21.43, 'T': 25.28, 'U': 30.43, 'V': 28.21, 'W': 40.26, 'X': 27.12,
            'Y': 26.49, 'Z': 23.06, '[': 13.39, '\\': 13.81, ']': 13.39, '^': 22.22, '_': 21.43, '`': 16.74,
            'a': 21.3, 'b': 24.15, 'c': 20.42, 'd': 23.73, 'e': 21.35, 'f': 14.82, 'g': 21.68, 'h': 25.15,
            'i': 12.47, 'j': 11.59, 'k': 22.89, 'l': 12.47, 'm': 37.71, 'n': 25.36, 'o': 22.98, 'p': 24.4,
            'q': 23.31, 'r': 17.7, 's': 18.16, 't': 13.6, 'u': 24.4, 'v': 21.14, 'w': 31.98, 'x': 22.01,
            'y': 21.43, 'z': 19.09, '{': 14.4, '|': 10.51, '}': 14.4, '~': 22.22, '«': 20.38, '°': 13.73,
            '²': 15.49, '»': 20.38, 'À': 27.79, 'Â': 27.79, 'Ä': 27.79, 'Æ': 38.51, 'Ç': 26.41, 'È': 25.24,
            'É': 25.24, 'Ê': 25.24, 'Ë': 25.24, 'Î': 15.53, 'Ï': 15.53, 'Ô': 29.59, 'Ö': 29.59, '×': 22.22,
            'Ù': 30.43, 'Û': 30.43, 'Ü': 30.43, 'à': 21.3, 'â': 21.3, 'ä': 21.3, 'æ': 32.73, 'ç': 20.42,
            'è': 21.35, 'é': 21.35, 'ê': 21.35, 'ë': 21.35, 'î': 12.47, 'ï': 12.47, 'ô': 22.98, 'ö': 22.98,
            'ù': 24.4, 'û': 24.4, 'ü': 24.4, 'ÿ': 21.43, 'Œ': 39.26, 'œ': 36.33, '–': 21.43, '—': 33.99,
            '‘': 8.87, '’': 8.87, '“': 17.37, '”': 17.37, '…': 37.67, '€': 20.93,
        },
    },
    'Handwriting': {
        'fs': 39.55,
        'montee': 36.9,
        'descente': 10.1,
        'debord_gauche': 3.6,
        'largeurs': {
            '!': 9.21, '"': 12.81, '#': 23.53, '$': 21.32, '%': 29.07, '&': 13.37, "'": 7.36, '(': 10.84,
            ')': 9.41, '*': 17.48, '+': 17.95, ',': 7.24, '-': 21.55, '.': 8.94, '/': 19.42, '0': 25.47,
            '1': 13.37, '2': 22.46, '3': 20.72, '4': 21.51, '5': 22.86, '6': 22.98, '7': 19.22, '8': 23.73,
            '9': 19.93, ':': 9.69, ';': 9.65, '<': 18.71, '=': 23.81, '>': 18.71, '?': 17.4, '@': 20.72,
            'A': 27.45, 'B': 27.53, 'C': 29.19, 'D': 29.94, 'E': 24.92, 'F': 23.81, 'G': 30.1, 'H': 28.51,
            'I': 9.65, 'J': 18.86, 'K': 25.47, 'L': 21.16, 'M': 34.05, 'N': 30.89, 'O': 32.23, 'P': 26.54,
            'Q': 30.93, 'R': 27.41, 'S': 24.8, 'T': 25.51, 'U': 27.13, 'V': 26.58, 'W': 41.41, 'X': 25.43,
            'Y': 23.61, 'Z': 25.47, '[': 14.4, '\\': 19.02, ']': 14.04, '^': 17.56, '_': 28.67, '`': 14.08,
            'a': 17.76, 'b': 17.88, 'c': 17.64, 'd': 18.71, 'e': 18.71, 'f': 12.42, 'g': 18.43, 'h': 19.3,
            'i': 7.91, 'j': 7.95, 'k': 18.67, 'l': 9.41, 'm': 26.42, 'n': 18.82, 'o': 19.38, 'p': 18.63,
            'q': 18.31, 'r': 15.74, 's': 17.24, 't': 14.16, 'u': 18.11, 'v': 17.76, 'w': 26.58, 'x': 15.31,
            'y': 17.48, 'z': 17.4, '{': 13.09, '|': 7.95, '}': 11.55, '~': 22.07, '«': 26.34, '°': 13.96,
            '»': 26.22, 'À': 27.45, 'Â': 27.45, 'Ä': 27.45, 'Æ': 38.95, 'Ç': 29.11, 'È': 24.92, 'É': 24.92,
            'Ê': 24.92, 'Ë': 24.92, 'Î': 9.65, 'Ï': 9.65, 'Ô': 32.23, 'Ö': 32.23, 'Ù': 27.13, 'Û': 27.13,
            'Ü': 27.13, 'à': 17.76, 'â': 17.76, 'ä': 17.76, 'æ': 31.12, 'ç': 17.6, 'è': 18.71, 'é': 18.71,
            'ê': 18.71, 'ë': 18.71, 'î': 7.91, 'ï': 7.91, 'ô': 19.38, 'ö': 19.38, 'ù': 18.11, 'û': 18.11,
            'ü': 18.11, 'ÿ': 17.48, 'Œ': 47.58, 'œ': 31.8, '–': 26.06, '—': 30.65, '‘': 7.4, '’': 7.47,
            '“': 13.05, '”': 13.05, '…': 29.46, '€': 30.33,
        },
    },
    'Marker': {
        'fs': 35.62,
        'montee': 40.3,
        'descente': 13.2,
        'debord_gauche': 9.3,
        'largeurs': {
            '!': 13.54, '"': 16.67, '#': 30.03, '$': 21.41, '%': 35.12, '&': 25.72, "'": 9.26, '(': 9.94,
            ')': 15.57, '*': 20.23, '+': 18.06, ',': 10.62, '-': 21.3, '.': 8.73, '/': 20.55, '0': 24.19,
            '1': 14.61, '2': 19.77, '3': 21.62, '4': 22.23, '5': 21.84, '6': 21.09, '7': 19.88, '8': 23.8,
            '9': 21.84, ':': 12.43, ';': 12.43, '<': 20.66, '=': 20.55, '>': 26.9, '?': 20.66, '@': 29.39,
            'A': 20.45, 'B': 21.2, 'C': 20.77, 'D': 21.52, 'E': 19.02, 'F': 15.46, 'G': 23.12, 'H': 21.3,
            'I': 13.43, 'J': 20.34, 'K': 20.98, 'L': 16.99, 'M': 24.97, 'N': 22.8, 'O': 24.54, 'P': 21.94,
            'Q': 26.15, 'R': 21.09, 'S': 20.02, 'T': 18.24, 'U': 24.76, 'V': 18.7, 'W': 27.89, 'X': 21.73,
            'Y': 17.85, 'Z': 20.34, '[': 19.45, '\\': 20.55, ']': 19.77, '^': 19.56, '_': 30.03, '`': 10.4,
            'a': 19.45, 'b': 19.24, 'c': 16.21, 'd': 19.66, 'e': 17.53, 'f': 15.89, 'g': 19.66, 'h': 21.41,
            'i': 11.79, 'j': 13.11, 'k': 17.31, 'l': 10.83, 'm': 27.68, 'n': 23.58, 'o': 19.02, 'p': 21.3,
            'q': 20.88, 'r': 14.5, 's': 18.38, 't': 15.89, 'u': 21.94, 'v': 18.49, 'w': 25.61, 'x': 16.99,
            'y': 18.74, 'z': 18.81, '{': 18.38, '|': 15.35, '}': 21.09, '~': 16.89, '«': 26.47, '°': 16.89,
            '»': 27.79, 'À': 20.45, 'Â': 20.45, 'Ä': 20.45, 'Æ': 30.46, 'Ç': 20.77, 'È': 19.02, 'É': 19.02,
            'Ê': 19.02, 'Ë': 19.02, 'Î': 12.43, 'Ï': 12.43, 'Ô': 23.12, 'Ö': 23.12, '×': 22.69, 'Ù': 23.12,
            'Û': 23.12, 'Ü': 23.12, 'à': 19.45, 'â': 20.34, 'ä': 19.45, 'æ': 29.07, 'ç': 15.67, 'è': 16.67,
            'é': 16.67, 'ê': 16.67, 'ë': 16.67, 'î': 10.72, 'ï': 10.72, 'ô': 18.6, 'ö': 18.6, 'ù': 21.94,
            'û': 21.94, 'ü': 21.94, 'ÿ': 20.98, 'Œ': 34.59, 'œ': 29.82, '–': 22.48, '—': 26.79, '‘': 8.87,
            '’': 8.87, '“': 16.67, '”': 16.89, '…': 25.51, '€': 23.23,
        },
    },
    'Curly': {
        'fs': 38.75,
        'montee': 36.4,
        'descente': 15.1,
        'debord_gauche': 5.8,
        'largeurs': {
            '!': 6.92, '"': 10.06, '#': 20.32, '$': 15.06, '%': 23.61, '&': 20.77, "'": 4.65, '(': 8.17,
            ')': 8.97, '*': 19.64, '+': 17.71, ',': 6.28, '-': 16.31, '.': 5.37, '/': 10.22, '0': 23.19,
            '1': 12.49, '2': 21.04, '3': 20.58, '4': 20.96, '5': 21.53, '6': 22.59, '7': 21.42, '8': 22.25,
            '9': 22.32, ':': 5.45, ';': 6.28, '<': 12.6, '=': 16.57, '>': 12.6, '?': 18.09, '@': 30.04,
            'A': 28.42, 'B': 27.36, 'C': 23.8, 'D': 27.39, 'E': 25.05, 'F': 21.11, 'G': 29.06, 'H': 27.39,
            'I': 10.97, 'J': 19.41, 'K': 22.7, 'L': 22.48, 'M': 30.88, 'N': 28.0, 'O': 28.61, 'P': 23.61,
            'Q': 28.08, 'R': 23.46, 'S': 19.9, 'T': 19.98, 'U': 24.33, 'V': 20.66, 'W': 30.88, 'X': 23.23,
            'Y': 16.65, 'Z': 23.5, '[': 6.62, '\\': 9.46, ']': 6.24, '^': 14.04, '_': 20.92, '`': 14.45,
            'a': 17.82, 'b': 19.03, 'c': 18.12, 'd': 19.75, 'e': 17.59, 'f': 13.96, 'g': 19.41, 'h': 17.97,
            'i': 9.31, 'j': 8.55, 'k': 15.36, 'l': 8.25, 'm': 25.77, 'n': 19.94, 'o': 18.43, 'p': 19.18,
            'q': 19.64, 'r': 16.72, 's': 16.19, 't': 12.64, 'u': 19.64, 'v': 17.33, 'w': 23.5, 'x': 17.71,
            'y': 18.01, 'z': 17.82, '{': 8.44, '|': 7.42, '}': 8.63, '~': 14.79, '«': 14.0, '°': 8.74,
            '²': 12.68, '»': 14.0, 'À': 28.42, 'Â': 28.42, 'Ä': 28.42, 'Æ': 34.36, 'Ç': 23.8, 'È': 25.05,
            'É': 25.05, 'Ê': 25.05, 'Ë': 25.05, 'Î': 10.97, 'Ï': 10.97, 'Ô': 28.61, 'Ö': 28.61, '×': 17.33,
            'Ù': 24.33, 'Û': 24.33, 'Ü': 24.33, 'à': 17.82, 'â': 17.82, 'ä': 17.82, 'æ': 29.32, 'ç': 18.12,
            'è': 17.59, 'é': 17.59, 'ê': 17.59, 'ë': 17.59, 'î': 9.31, 'ï': 9.31, 'ô': 18.43, 'ö': 18.43,
            'ù': 19.64, 'û': 19.64, 'ü': 19.64, 'ÿ': 18.01, 'Œ': 39.46, 'œ': 30.91, '–': 16.31, '—': 21.68,
            '‘': 5.6, '’': 4.84, '“': 11.05, '”': 10.25, '…': 15.48, '€': 21.42,
        },
    },
    'Pixel': {
        'fs': 32.0,
        'montee': 40.0,
        'descente': 8.0,
        'debord_gauche': -0.0,
        'largeurs': {
            '!': 8.0, '"': 16.0, '#': 28.0, '$': 24.0, '%': 32.0, '&': 24.0, "'": 8.0, '(': 16.0, ')': 16.0,
            '*': 24.0, '+': 24.0, ',': 8.0, '-': 20.0, '.': 8.0, '/': 16.0, '0': 24.0, '1': 12.0, '2': 24.0,
            '3': 20.0, '4': 24.0, '5': 24.0, '6': 24.0, '7': 24.0, '8': 24.0, '9': 24.0, ':': 8.0, ';': 8.0,
            '<': 20.0, '=': 20.0, '>': 20.0, '?': 20.0, '@': 32.0, 'A': 24.0, 'B': 24.0, 'C': 20.0, 'D': 24.0,
            'E': 20.0, 'F': 20.0, 'G': 24.0, 'H': 24.0, 'I': 8.0, 'J': 24.0, 'K': 24.0, 'L': 24.0, 'M': 24.0,
            'N': 24.0, 'O': 24.0, 'P': 24.0, 'Q': 28.0, 'R': 24.0, 'S': 24.0, 'T': 24.0, 'U': 24.0, 'V': 24.0,
            'W': 24.0, 'X': 24.0, 'Y': 24.0, 'Z': 24.0, '[': 16.0, '\\': 16.0, ']': 16.0, '^': 24.0,
            '_': 16.0, '`': 12.0, 'a': 20.0, 'b': 20.0, 'c': 16.0, 'd': 20.0, 'e': 20.0, 'f': 20.0, 'g': 20.0,
            'h': 20.0, 'i': 8.0, 'j': 16.0, 'k': 20.0, 'l': 8.0, 'm': 24.0, 'n': 20.0, 'o': 20.0, 'p': 20.0,
            'q': 20.0, 'r': 20.0, 's': 20.0, 't': 20.0, 'u': 20.0, 'v': 24.0, 'w': 24.0, 'x': 24.0, 'y': 20.0,
            'z': 24.0, '{': 20.0, '|': 8.0, '}': 20.0, '~': 28.0, '«': 28.0, '°': 16.0, '»': 28.0, 'À': 24.0,
            'Â': 24.0, 'Ä': 24.0, 'Æ': 28.0, 'Ç': 20.0, 'È': 20.0, 'É': 20.0, 'Ê': 20.0, 'Ë': 20.0, 'Î': 12.0,
            'Ï': 12.0, 'Ô': 24.0, 'Ö': 24.0, '×': 24.0, 'Ù': 24.0, 'Û': 24.0, 'Ü': 24.0, 'à': 20.0, 'â': 20.0,
            'ä': 20.0, 'æ': 24.0, 'ç': 16.0, 'è': 20.0, 'é': 20.0, 'ê': 20.0, 'ë': 20.0, 'î': 12.0, 'ï': 12.0,
            'ô': 20.0, 'ö': 20.0, 'ù': 20.0, 'û': 20.0, 'ü': 20.0, 'ÿ': 20.0, 'Œ': 28.0, 'œ': 24.0, '—': 24.0,
            '‘': 8.0, '’': 8.0, '“': 16.0, '”': 16.0, '…': 24.0, '€': 24.0,
        },
    },
    'Scratch': {
        'fs': 40.52,
        'montee': 28.0,
        'descente': 8.0,
        'debord_gauche': 4.0,
        'largeurs': {
            '!': 6.12, '"': 9.0, '#': 15.32, '$': 10.82, '%': 12.12, '&': 21.03, "'": 4.38, '(': 10.37,
            ')': 10.41, '*': 14.22, '+': 15.28, ',': 8.63, '-': 13.74, '.': 7.33, '/': 11.18, '0': 17.55,
            '1': 13.13, '2': 16.61, '3': 20.18, '4': 18.4, '5': 17.67, '6': 17.18, '7': 18.64, '8': 17.95,
            '9': 16.74, ':': 6.0, ';': 6.4, '<': 10.25, '=': 14.02, '>': 12.16, '?': 12.97, '@': 16.65,
            'A': 23.06, 'B': 19.77, 'C': 15.28, 'D': 21.76, 'E': 21.4, 'F': 21.23, 'G': 19.21, 'H': 21.48,
            'I': 9.85, 'J': 17.34, 'K': 24.76, 'L': 20.06, 'M': 29.18, 'N': 23.66, 'O': 19.86, 'P': 18.76,
            'Q': 20.18, 'R': 22.04, 'S': 15.24, 'T': 20.95, 'U': 22.81, 'V': 22.29, 'W': 30.15, 'X': 26.18,
            'Y': 24.07, 'Z': 18.07, '[': 8.39, '\\': 10.25, ']': 9.08, 'a': 13.33, 'b': 16.13, 'c': 12.08,
            'd': 17.14, 'e': 13.66, 'f': 13.29, 'g': 18.92, 'h': 21.96, 'i': 11.18, 'j': 12.32, 'k': 20.38,
            'l': 9.64, 'm': 33.07, 'n': 19.69, 'o': 14.71, 'p': 17.14, 'q': 13.94, 'r': 16.17, 's': 15.6,
            't': 13.33, 'u': 20.26, 'v': 18.27, 'w': 26.3, 'x': 20.79, 'y': 19.0, 'z': 14.3,
        },
    },
}


# ---------------------------------------------------------------------------
#  Fabrique de SVG
# ---------------------------------------------------------------------------
def _svg(w, h, contenu):
    return ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
            % (w, h, w, h, contenu))


def _geometrie(pol):
    """Marge gauche, ligne de base et hauteur de boîte (px) communes à tous les glyphes."""
    mx = int(math.ceil(pol["debord_gauche"])) + 2
    base = int(math.ceil(pol["montee"])) + 2
    h = base + int(math.ceil(pol["descente"])) + 2
    return mx, base, h


def svg_glyphe(caractere, police="Sans Serif"):
    """SVG d'un caractère de la police : rouge pur, origine (marge, ligne de base)."""
    pol = POLICES[police]
    mx, base, h = _geometrie(pol)
    fs = pol["fs"]
    w = int(math.ceil(pol["largeurs"][caractere])) + mx + 6
    # Origine du texte = début de la ligne de base (SVG standard ; les corrections
    # « Scratch 2 » de scratch-svg-renderer ne s'appliquent qu'aux projets .sb2).
    contenu = ('<text x="%d" y="%d" font-family="%s" font-size="%s" fill="#ff0000">%s</text>'
               % (mx, base, police, fs, escape(caractere)))
    return _svg(w, h, contenu), mx, base


def svg_sentinelle(police="Sans Serif"):
    """Costume « g_ » : vide et large (sert de repère « caractère inconnu » et fixe
    la taille minimale autorisée par Scratch avant « mettre la taille à »)."""
    mx, base, h = _geometrie(POLICES[police])
    return _svg(200, h, '<rect width="200" height="%d" fill="none"/>' % h), 0, base


def _etoile(cx, cy, r1, r2, pleine):
    pts = []
    for k in range(10):
        r = r1 if k % 2 == 0 else r2
        a = math.radians(-90 + 36 * k)
        pts.append("%.1f,%.1f" % (cx + r * math.cos(a), cy + r * math.sin(a)))
    if pleine:
        return '<polygon points="%s" fill="#ff0000"/>' % " ".join(pts)
    return '<polygon points="%s" fill="none" stroke="#ff0000" stroke-width="3" stroke-linejoin="round"/>' % " ".join(pts)


def _fleche(mx, cy, direction):
    # flèche de 28 px de long, pointe pleine ; direction : droite, gauche, haut, bas
    if direction in ("droite", "gauche"):
        x0, x1 = mx + 2, mx + 28
        tete = 10
        if direction == "droite":
            return ('<rect x="%d" y="%d" width="%d" height="5" fill="#ff0000"/>'
                    '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>'
                    % (x0, cy - 2.5, x1 - x0 - tete + 2, x1 - tete, cy - 10, x1, cy, x1 - tete, cy + 10)), 32
        return ('<rect x="%d" y="%d" width="%d" height="5" fill="#ff0000"/>'
                '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>'
                % (x0 + tete - 2, cy - 2.5, x1 - x0 - tete + 2, x0 + tete, cy - 10, x0, cy, x0 + tete, cy + 10)), 32
    y_haut, y_bas = cy - 15, cy + 13
    tete = 10
    x = mx + 11
    if direction == "haut":
        return ('<rect x="%d" y="%d" width="5" height="%d" fill="#ff0000"/>'
                '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>'
                % (x - 2.5, y_haut + tete - 2, y_bas - y_haut - tete + 2, x - 10, y_haut + tete, x, y_haut, x + 10, y_haut + tete)), 24
    return ('<rect x="%d" y="%d" width="5" height="%d" fill="#ff0000"/>'
            '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>'
            % (x - 2.5, y_haut, y_bas - y_haut - tete + 2, x - 10, y_bas - tete, x, y_bas, x + 10, y_bas - tete)), 24


def _pouce(mx, base):
    """Pouce levé (silhouette 👍, environ 28 px) : manchette, poing à trois doigts, pouce dressé."""
    x = mx
    y = base - 27
    return ('<rect x="%d" y="%d" width="6" height="15" rx="1.5" fill="#ff0000"/>'                  # manchette
            '<rect x="%d" y="%d" width="9" height="15" rx="2" fill="#ff0000"/>'                    # paume
            '<rect x="%d" y="%d" width="20" height="4.4" rx="2.2" fill="#ff0000"/>'                # doigt 1
            '<rect x="%d" y="%.1f" width="19" height="4.4" rx="2.2" fill="#ff0000"/>'              # doigt 2
            '<rect x="%d" y="%.1f" width="17" height="4.4" rx="2.2" fill="#ff0000"/>'              # doigt 3
            '<path d="M%d %d C%d %d %d %d %d %d C%d %d %d %d %d %d L%d %d Z" fill="#ff0000"/>'     # pouce
            % (x, y + 12,
               x + 7, y + 12,
               x + 7, y + 12,
               x + 7, y + 17.4,
               x + 7, y + 22.8,
               x + 8, y + 12, x + 7, y + 7, x + 10, y + 1, x + 13, y, x + 16, y - 1, x + 18, y + 3, x + 17, y + 6,
               x + 15, y + 12)), 28


def svg_symbole(symbole, police="Sans Serif"):
    """SVG vectoriel d'un symbole (rouge pur) et sa largeur d'avance."""
    mx, base, h = _geometrie(POLICES[police])
    cy = base - 13          # axe des symboles (milieu des majuscules ≈ base − 14)
    s = ""
    adv = 30
    if symbole == "★":
        s = _etoile(mx + 15, cy, 14, 5.8, True)
    elif symbole == "☆":
        s = _etoile(mx + 15, cy, 12.5, 5.2, False)
    elif symbole in "♥❤":
        cx = mx + 14
        s = ('<path d="M%d %d c-3 -9 -16 -10 -16 1 c0 8 10 14 16 20 c6 -6 16 -12 16 -20 c0 -11 -13 -10 -16 -1 z" fill="#ff0000"/>'
             % (cx, cy - 10))
        adv = 30
    elif symbole == "●":
        s = '<circle cx="%d" cy="%d" r="11" fill="#ff0000"/>' % (mx + 13, cy)
        adv = 26
    elif symbole == "○":
        s = '<circle cx="%d" cy="%d" r="9.5" fill="none" stroke="#ff0000" stroke-width="3"/>' % (mx + 13, cy)
        adv = 26
    elif symbole == "✔":
        s = ('<polyline points="%d,%d %d,%d %d,%d" fill="none" stroke="#ff0000" stroke-width="5" '
             'stroke-linecap="round" stroke-linejoin="round"/>' % (mx + 3, cy + 1, mx + 11, cy + 10, mx + 27, cy - 11))
    elif symbole == "✘":
        s = ('<path d="M%d %d L%d %d M%d %d L%d %d" stroke="#ff0000" stroke-width="5" stroke-linecap="round"/>'
             % (mx + 4, cy - 11, mx + 24, cy + 11, mx + 24, cy - 11, mx + 4, cy + 11))
        adv = 28
    elif symbole == "→":
        s, adv = _fleche(mx, cy, "droite")
    elif symbole == "←":
        s, adv = _fleche(mx, cy, "gauche")
    elif symbole == "↑":
        s, adv = _fleche(mx, cy, "haut")
    elif symbole == "↓":
        s, adv = _fleche(mx, cy, "bas")
    elif symbole == "▶":
        s = '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>' % (mx + 3, cy - 12, mx + 25, cy, mx + 3, cy + 12)
        adv = 28
    elif symbole == "◀":
        s = '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>' % (mx + 25, cy - 12, mx + 3, cy, mx + 25, cy + 12)
        adv = 28
    elif symbole == "▲":
        s = '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>' % (mx + 2, cy + 11, mx + 14, cy - 11, mx + 26, cy + 11)
        adv = 28
    elif symbole == "▼":
        s = '<polygon points="%d,%d %d,%d %d,%d" fill="#ff0000"/>' % (mx + 2, cy - 11, mx + 14, cy + 11, mx + 26, cy - 11)
        adv = 28
    elif symbole == "■":
        s = '<rect x="%d" y="%d" width="20" height="20" fill="#ff0000"/>' % (mx + 3, cy - 10)
        adv = 26
    elif symbole == "□":
        s = '<rect x="%d" y="%d" width="17" height="17" fill="none" stroke="#ff0000" stroke-width="3"/>' % (mx + 4.5, cy - 8.5)
        adv = 26
    elif symbole == "👍":
        s, adv = _pouce(mx, base)
    else:
        raise KeyError("symbole inconnu : %r" % symbole)
    return _svg(adv + mx + 6, h, s), mx, base, adv


# ---------------------------------------------------------------------------
#  Installation dans un sprite
# ---------------------------------------------------------------------------
def installer(cible, police="Sans Serif"):
    """Ajoute à `cible` les costumes de glyphes, la liste txt_largeurs, les variables
    txt_* et les blocs « ecrire », « largeur texte », « ecrire tronque », « ecrire nombre ».
    Idempotent. Les costumes déjà présents gardent leurs numéros (entrées à 0 dans txt_largeurs)."""
    if getattr(cible, "_texte_installe", None):
        return
    if cible.is_stage:
        raise ValueError("texte.installer : la scène ne peut pas tamponner, choisir un sprite")
    if police not in POLICES:
        raise KeyError("police inconnue : %r (choix : %s)" % (police, ", ".join(POLICES)))
    cible._texte_installe = police
    pol = POLICES[police]

    # --- costumes ------------------------------------------------------------
    largeurs = [0] * len(cible.costumes)          # alignée sur les numéros ABSOLUS de costumes
    svg, cx, cy = svg_sentinelle(police)
    cible.costume_svg("g_", svg, cx, cy)
    sentinelle = len(cible.costumes)              # numéro (1-based) du costume « g_ »
    largeurs.append(0)
    numeros = {}
    for c in CARACTERES_POLICE:
        if c not in pol["largeurs"]:
            continue                              # glyphe absent de cette police : caractère ignoré
        svg, cx, cy = svg_glyphe(c, police)
        cible.costume_svg("g_" + c, svg, cx, cy)
        numeros[c] = len(cible.costumes)
        largeurs.append(pol["largeurs"][c])
    for c in SYMBOLES:
        svg, cx, cy, adv = svg_symbole(c, police)
        cible.costume_svg("g_" + c, svg, cx, cy)
        numeros[c] = len(cible.costumes)
        largeurs.append(adv)
    # points de suspension pour « ecrire tronque » : « … » ou trois points
    if "…" in numeros:
        suspension = [numeros["…"]]
    else:
        suspension = [numeros["."]] * 3
    largeur_suspension = sum(largeurs[n - 1] for n in suspension)

    # --- données locales -----------------------------------------------------
    cible.liste("txt_largeurs", largeurs)
    cible.liste("txt_glyphes", [])
    noms = list(COULEURS.keys())
    cible.liste("txt_couleurNoms", noms)
    valeurs = []
    for n in noms:
        valeurs += list(COULEURS[n])
    cible.liste("txt_couleurValeurs", valeurs)
    for nom, val in [("txt_largeur", 0), ("txt_i", 0), ("txt_j", 0), ("txt_c", 0), ("txt_x", 0), ("txt_x0", 0),
                     ("txt_k", 1), ("txt_n", 0), ("txt_lmax", 0), ("txt_ombre", 1), ("txt_espacement", 0)]:
        cible.var(nom, val)

    V = Var
    k = V("txt_k")
    esp = V("txt_espacement")

    def avance(num):
        """Avance (px) du glyphe de costume n° `num` à la taille courante."""
        return mul(add(item("txt_largeurs", num), esp), k)

    # --- largeur texte %s %n : remplit txt_glyphes (numéros de costume, 0 = espace)
    #     et txt_largeur (px). Un caractère inconnu laisse le costume sur « g_ ».
    cible.proc("largeur texte", [("texte", "s"), ("taille", "n")], [
        vider("txt_glyphes"),
        setv("txt_largeur", 0),
        setv("txt_k", div(Arg("taille"), BOITE)),
        setv("txt_i", 1),
        repeter_jusqua(gt(V("txt_i"), longueur(Arg("texte"))), [
            setv("txt_c", lettre(V("txt_i"), Arg("texte"))),
            si(eq(V("txt_c"), " "), [
                ajouter_liste("txt_glyphes", 0),
                changev("txt_largeur", mul(LARGEUR_ESPACE, k)),
            ], [
                # paire de substitution UTF-16 (émoji) : lettre(i) ≥ U+D800 → on prend 2 unités
                si(gt(V("txt_c"), "퟿"), [
                    setv("txt_c", join(V("txt_c"), lettre(add(V("txt_i"), 1), Arg("texte")))),
                    changev("txt_i", 1),
                ]),
                costume("g_"),
                costume(join("g_", V("txt_c"))),
                setv("txt_c", costume_numero()),
                si(non(eq(V("txt_c"), sentinelle)), [
                    ajouter_liste("txt_glyphes", V("txt_c")),
                    changev("txt_largeur", avance(V("txt_c"))),
                ]),
            ]),
            changev("txt_i", 1),
        ]),
    ])

    # --- txt_passe %n %n %n : tamponne txt_glyphes à partir de (x, y) avec les effets courants
    cible.proc("txt_passe", [("x", "n"), ("y", "n"), ("taille", "n")], [
        costume("g_"),                                   # costume large : taille minimale non bridée
        taille(mul(Arg("taille"), 100.0 / BOITE)),
        setv("txt_x", Arg("x")),
        setv("txt_j", 0),
        repeter(long_liste("txt_glyphes"), [
            changev("txt_j", 1),
            setv("txt_c", item("txt_glyphes", V("txt_j"))),
            si(eq(V("txt_c"), 0), [
                changev("txt_x", mul(LARGEUR_ESPACE, k)),
            ], [
                costume(V("txt_c")),
                aller(V("txt_x"), Arg("y")),
                tampon(),
                changev("txt_x", avance(V("txt_c"))),
            ]),
        ]),
    ])

    # --- txt_dessiner %n %n %n %s %n : alignement, ombre puis couleur
    cible.proc("txt_dessiner", [("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("alignement", "n")], [
        setv("txt_k", div(Arg("taille"), BOITE)),
        setv("txt_x0", sub(Arg("x"), div(mul(Arg("alignement"), V("txt_largeur")), 2))),
        si(eq(V("txt_ombre"), 1), [
            effet("COLOR", 0), effet("BRIGHTNESS", -100), effet("GHOST", 0),
            appel("txt_passe", add(V("txt_x0"), div(Arg("taille"), 20)), sub(Arg("y"), div(Arg("taille"), 20)), Arg("taille")),
        ]),
        setv("txt_n", num_item("txt_couleurNoms", Arg("couleur"))),
        si(eq(V("txt_n"), 0), [setv("txt_n", 1)]),                 # couleur inconnue → blanc
        setv("txt_n", mul(sub(V("txt_n"), 1), 3)),
        effet("COLOR", item("txt_couleurValeurs", add(V("txt_n"), 1))),
        effet("BRIGHTNESS", item("txt_couleurValeurs", add(V("txt_n"), 2))),
        effet("GHOST", item("txt_couleurValeurs", add(V("txt_n"), 3))),
        appel("txt_passe", V("txt_x0"), Arg("y"), Arg("taille")),
        effacer_effets(),
    ])

    # --- ecrire %s %n %n %n %s %n
    cible.proc("ecrire", [("texte", "s"), ("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("alignement", "n")], [
        appel("largeur texte", Arg("texte"), Arg("taille")),
        appel("txt_dessiner", Arg("x"), Arg("y"), Arg("taille"), Arg("couleur"), Arg("alignement")),
    ])

    # --- ecrire tronque %s %n %n %n %s %n %n : coupe avec « … » si plus large que largeurMax
    dernier = long_liste("txt_glyphes")
    cible.proc("ecrire tronque", [("texte", "s"), ("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"),
                                  ("alignement", "n"), ("largeurMax", "n")], [
        appel("largeur texte", Arg("texte"), Arg("taille")),
        si(gt(V("txt_largeur"), Arg("largeurMax")), [
            setv("txt_lmax", sub(Arg("largeurMax"), mul(largeur_suspension, k))),
            repeter_jusqua(ou(non(gt(V("txt_largeur"), V("txt_lmax"))), lt(dernier, 1)), [
                setv("txt_c", item("txt_glyphes", dernier)),
                si(eq(V("txt_c"), 0), [
                    changev("txt_largeur", mul(-LARGEUR_ESPACE, k)),
                ], [
                    changev("txt_largeur", mul(-1, avance(V("txt_c")))),
                ]),
                supprimer("txt_glyphes", dernier),
            ]),
            # pas d'espace juste avant les points de suspension
            repeter_jusqua(ou(lt(dernier, 1), non(eq(item("txt_glyphes", dernier), 0))), [
                changev("txt_largeur", mul(-LARGEUR_ESPACE, k)),
                supprimer("txt_glyphes", dernier),
            ]),
            [ajouter_liste("txt_glyphes", n) for n in suspension],
            changev("txt_largeur", mul(largeur_suspension, k)),
        ]),
        appel("txt_dessiner", Arg("x"), Arg("y"), Arg("taille"), Arg("couleur"), Arg("alignement")),
    ])

    # --- ecrire nombre %n %n %n %n %s %n : nombre arrondi à l'entier
    cible.proc("ecrire nombre", [("nombre", "n"), ("x", "n"), ("y", "n"), ("taille", "n"), ("couleur", "s"), ("alignement", "n")], [
        appel("ecrire", rnd(Arg("nombre")), Arg("x"), Arg("y"), Arg("taille"), Arg("couleur"), Arg("alignement")),
    ])


# ---------------------------------------------------------------------------
#  Raccourcis Python (renvoient le bloc d'appel ; à utiliser dans le sprite installé)
# ---------------------------------------------------------------------------
def ecrire(texte, x, y, taille_px, couleur="blanc", alignement=0):
    return appel("ecrire", texte, x, y, taille_px, couleur, alignement)


def largeur_texte(texte, taille_px):
    return appel("largeur texte", texte, taille_px)


def ecrire_tronque(texte, x, y, taille_px, couleur, alignement, largeur_max):
    return appel("ecrire tronque", texte, x, y, taille_px, couleur, alignement, largeur_max)


def ecrire_nombre(nombre, x, y, taille_px, couleur="blanc", alignement=0):
    return appel("ecrire nombre", nombre, x, y, taille_px, couleur, alignement)


def largeur_px(texte, taille_px, police="Sans Serif"):
    """Largeur approximative (px) calculée côté Python (mise en page statique des menus)."""
    pol = POLICES[police]
    k = taille_px / float(BOITE)
    total = 0.0
    for c in texte:
        if c == " ":
            total += LARGEUR_ESPACE * k
        elif c in pol["largeurs"]:
            total += pol["largeurs"][c] * k
        elif c in SYMBOLES:
            total += svg_symbole(c, police)[3] * k
    return total
