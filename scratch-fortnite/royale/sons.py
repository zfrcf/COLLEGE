# -*- coding: utf-8 -*-
"""
BANQUE DE SONS SYNTHÉTISÉE et sprite « Sons » du projet Royale 3D.

Scratch ne fournit aucun son ici : tous les effets et les musiques sont fabriqués
en Python pur (sans numpy) sous forme de WAV PCM 16 bits mono, puis attachés au
sprite « Sons ». La liste exacte des noms est `contrat.SONS` (28 sons) + SONS_SUPPLEMENTAIRES (5 sons
du spectacle, voir plus bas).

Synthèse
--------
- `wav(echantillons, rate)` : flottants [-1, 1] -> octets WAV.
- Primitives : bruit blanc déterministe (graine fixe => .sb3 reproductible),
  oscillateurs (sinus, additif), glissandos, enveloppes, filtres (passe-bas,
  passe-haut, passe-bande biquad), écrêtage doux, mixage, finition
  (fondu d'attaque/relâchement anti-clic + normalisation du pic).
- Un générateur par son (`GENERATEURS[nom](rate)` -> liste de flottants déjà
  normalisée, pic <= 0,8). Effets courts à 22050 Hz, nappes et musiques à 11025 Hz
  pour garder le .sb3 léger.

Sprite « Sons » (`installer(P)`)
-------------------------------
- Un script `quand je reçois "son <nom>"` par son. L'émetteur règle d'abord les
  globales `son_pan` (-100..100) et `son_volume` (0..100, relatif) puis diffuse.
  Volume joué = paramètre de catégorie x son_volume / 100 :
    musique_*                                            -> param_volumeMusique
    victoire, defaite, niveau, elimination, notification, compte -> param_volumeVoix
    le reste                                             -> param_volumeEffets
- Dans Scratch le volume et l'effet PAN appartiennent à la CIBLE et s'appliquent
  immédiatement à tous les sons en cours de cette cible. Les effets (courts) sont
  donc joués par le sprite original, tandis que la musique et les jingles « voix »
  (longs) sont joués par des CLONES éphémères qui ont leur propre volume : un coup
  de feu ne fait plus sauter le volume de la musique ni d'une fanfare.
  Attention : à sa création un clone repart à volume 100 mais HÉRITE de l'effet PAN
  de l'original (scratch-vm copie l'état sonore) ; les clones remettent donc leur
  PAN explicitement (comparé à `son_dernierPan`, lui aussi hérité) avant de jouer.
- Seul l'original réagit à « demarrer » : un clone qui le reçoit (relance du jeu)
  se supprime, sinon il remettrait ses locales à zéro et se prendrait pour l'original.
- Si le clone musique ne peut pas naître (limite de 300 clones atteinte par d'autres
  sprites), la globale privée `son_musiqueLecteur` reste à 0 et l'original réessaie
  toutes les 0,3 s ; un « son stop musique » volontaire la laisse à 1 (pas de reprise).
- Musique : `quand je reçois "demarrer"` -> boucle qui surveille `ecran` ; sur les
  écrans connexion/salon/matchmaking/chargement et si `son_musiqueActive` = 0, un
  clone « musique » est créé et joue `musique_salon` jusqu'au bout en boucle (volume
  suivi en temps réel sur param_volumeMusique) ; en quittant ces écrans, diffusion
  de "son stop musique" qui supprime le clone (ce qui arrête le son joué « jusqu'au
  bout » sans toucher aux effets). "son stop tout" arrête tout (effets compris) ;
  la musique reprend alors d'elle-même si l'on est toujours sur un écran musical.
- Musique DYNAMIQUE en jeu (bloc « musique jeu », chaque image hors des écrans de menu) :
  rien par défaut ; `musique_combat` (clone « combat ») quand un ennemi vivant est à moins de
  DISTANCE_COMBAT cases (listes E_x/E_y/E_actif/E_etat/E_equipe et px/py), maintenue
  HYSTERESIS_COMBAT s après le dernier contact ; `musique_tempete` (clone « tempete ») dès que
  horsZone = 1 (prioritaire). Globale privée `son_musiqueJeu` = 0 / 1 / 2 ; "son stop musique jeu"
  supprime le clone courant. Seulement sur l'écran « jeu » avec etat 1 ou 3.
- Sons supplémentaires du spectacle (SONS_SUPPLEMENTAIRES : explosion, serie, largage,
  musique_combat, musique_tempete) : même mécanisme que contrat.SONS ; à ajouter au contrat.

Ajout local au DSL : `volume_actuel()` (reporter `sound_volume`) pour éviter de
régler le volume (un rendu d'image perdu) quand il est déjà bon.
"""
import math
import random
import struct
import sys
from array import array

from . import contrat
from .dsl import (Cible, Node, Var, add, appel, attendre, changev, chrono, cloner_moi, diffuser, div, effet_son, eq,
                  et, gt, item, lt, mul, non, ou, ou3, quand_clone, quand_drapeau, quand_message, repeter, setv, si,
                  son, son_attendre, stop_sons, sub, supprimer_clone, toujours, volume)

TAU = 2.0 * math.pi
TAUX = 22050              # effets courts
TAUX_NAPPES = 11025       # nappes et musiques (taille divisée par deux)
NAPPES = ["tempete", "bus", "parachute", "musique_salon", "musique_fin", "musique_combat", "musique_tempete", "explosion"]
VOIX = ["victoire", "defaite", "niveau", "elimination", "notification", "compte", "serie"]
ECRANS_MUSIQUE = ["connexion", "salon", "matchmaking", "chargement"]
PARAMETRE_VOLUME = {"musique": "param_volumeMusique", "voix": "param_volumeVoix", "effets": "param_volumeEffets"}
# Sons SUPPLÉMENTAIRES du spectacle (module mod_spectacle) : le sprite Sons les possède et répond à « son <nom> »
# comme pour contrat.SONS ; à ajouter à contrat.SONS (ils disparaissent alors d'eux-mêmes de cette liste).
SONS_SUPPLEMENTAIRES = ["explosion", "serie", "largage", "musique_combat", "musique_tempete"]
TOUS_LES_SONS = list(contrat.SONS) + [n for n in SONS_SUPPLEMENTAIRES if n not in contrat.SONS]
# Musique dynamique en jeu (lecteur dans le sprite Sons) : globale privée son_musiqueJeu = 0 rien, 1 combat
# (un ennemi vivant à moins de DISTANCE_COMBAT cases, maintenu HYSTERESIS_COMBAT s), 2 tempête (horsZone = 1).
DISTANCE_COMBAT = 12
HYSTERESIS_COMBAT = 6
BPM_COMBAT = 128


def categorie(nom):
    """'musique' | 'voix' | 'effets' selon le nom du son."""
    if nom.startswith("musique_"):
        return "musique"
    if nom in VOIX:
        return "voix"
    return "effets"


def parametre_volume(nom):
    """Nom de la variable globale de volume (param_volume…) qui gouverne ce son."""
    return PARAMETRE_VOLUME[categorie(nom)]


def taux(nom):
    return TAUX_NAPPES if nom in NAPPES else TAUX


# ---------------------------------------------------------------------------
#  Fichier WAV
# ---------------------------------------------------------------------------
def wav(echantillons, rate=22050):
    """Octets d'un fichier WAV PCM 16 bits mono à partir de flottants dans [-1, 1]."""
    donnees = array("h")
    donnees.extend(int(round(32767.0 * (1.0 if v > 1.0 else (-1.0 if v < -1.0 else v)))) for v in echantillons)
    if sys.byteorder == "big":
        donnees.byteswap()
    octets = donnees.tobytes()
    entete = struct.pack("<4sI4s4sIHHIIHH4sI", b"RIFF", 36 + len(octets), b"WAVE", b"fmt ", 16, 1, 1,
                         rate, rate * 2, 2, 16, b"data", len(octets))
    return entete + octets


# ---------------------------------------------------------------------------
#  Primitives de synthèse (listes de flottants)
# ---------------------------------------------------------------------------
def _n(duree, rate):
    return int(round(duree * rate))


def _bruit(n, graine=1):
    """Bruit blanc déterministe dans [-1, 1]."""
    u = random.Random(graine).uniform
    return [u(-1.0, 1.0) for _ in range(n)]


def _sinus(n, rate, freq, phase=0.0):
    """Sinusoïde ; `freq` est un nombre (Hz) ou une liste de n fréquences (glissando)."""
    s = math.sin
    if isinstance(freq, (int, float)):
        inc = TAU * freq / rate
        return [s(phase + inc * i) for i in range(n)]
    out = [0.0] * n
    ph = phase
    k = TAU / rate
    for i in range(n):
        out[i] = s(ph)
        ph += k * freq[i]
    return out


def _glisse(n, rate, f0, f1, duree=None):
    """Fréquence glissant exponentiellement de f0 à f1 en `duree` s (puis constante)."""
    m = n if duree is None else min(n, _n(duree, rate))
    if m <= 1:
        return [f1] * n
    r = math.log(f1 / f0) / (m - 1)
    e = math.exp
    out = [f0 * e(r * i) for i in range(m)]
    out += [f1] * (n - m)
    return out


def _additif(n, rate, freq, partiels, phase=0.0):
    """Somme de partiels (multiple, amplitude). Les partiels au-delà de 0,45·rate sont ignorés (anti-repliement)."""
    out = [0.0] * n
    fmax = 0.45 * rate
    constante = isinstance(freq, (int, float))
    f_ref = freq if constante else max(freq)
    for mult, amp in partiels:
        if f_ref * mult >= fmax:
            continue
        if constante:
            v = _sinus(n, rate, freq * mult, phase * mult)
        else:
            v = _sinus(n, rate, [f * mult for f in freq], phase * mult)
        out = [o + amp * x for o, x in zip(out, v)]
    return out


def _env_perc(n, rate, attaque, tau):
    """Attaque linéaire (s) puis décroissance exponentielle de constante de temps tau (s)."""
    na = max(1, _n(attaque, rate))
    k = 1.0 / (tau * rate)
    e = math.exp
    return [min(1.0, i / na) * e(-max(0, i - na) * k) for i in range(n)]


def _env_adsr(n, rate, a, d, s, r):
    """Attaque a, déclin d vers le niveau s, maintien, relâchement linéaire sur les r dernières secondes."""
    na, nd, nr = _n(a, rate), _n(d, rate), max(1, _n(r, rate))
    out = [0.0] * n
    for i in range(n):
        if i < na:
            v = i / max(1, na)
        elif i < na + nd:
            v = 1.0 - (1.0 - s) * (i - na) / max(1, nd)
        else:
            v = s
        reste = n - i
        if reste < nr:
            v *= reste / nr
        out[i] = v
    return out


def _mult(x, env):
    return [a * b for a, b in zip(x, env)]


def _ajouter(dest, src, debut=0, gain=1.0):
    """Mixe `src` dans `dest` (en place) à partir de l'échantillon `debut` ; tronque à la fin de `dest`."""
    fin = min(len(dest), debut + len(src))
    if fin <= debut:
        return dest
    dest[debut:fin] = [d + gain * s for d, s in zip(dest[debut:fin], src[:fin - debut])]
    return dest


def _passe_bas(x, fc, rate):
    """Passe-bas un pôle ; fc nombre ou liste (Hz)."""
    out = [0.0] * len(x)
    y = 0.0
    if isinstance(fc, (int, float)):
        a = 1.0 - math.exp(-TAU * fc / rate)
        for i, v in enumerate(x):
            y += a * (v - y)
            out[i] = y
    else:
        e = math.exp
        k = -TAU / rate
        for i, v in enumerate(x):
            y += (1.0 - e(k * fc[i])) * (v - y)
            out[i] = y
    return out


def _passe_haut(x, fc, rate):
    bas = _passe_bas(x, fc, rate)
    return [a - b for a, b in zip(x, bas)]


def _passe_bande(x, fc, q, rate):
    """Biquad passe-bande (gain 0 dB au pic) ; fc nombre ou liste (coefficients recalculés tous les 16 échantillons)."""
    out = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    constante = isinstance(fc, (int, float))

    def coef(f):
        w0 = TAU * min(f, 0.45 * rate) / rate
        al = math.sin(w0) / (2.0 * q)
        a0 = 1.0 + al
        return al / a0, -2.0 * math.cos(w0) / a0, (1.0 - al) / a0

    b0, a1, a2 = coef(fc if constante else fc[0])
    for i, v in enumerate(x):
        if not constante and (i & 15) == 0:
            b0, a1, a2 = coef(fc[i])
        y = b0 * (v - x2) - a1 * y1 - a2 * y2
        x2 = x1
        x1 = v
        y2 = y1
        y1 = y
        out[i] = y
    return out


def _doux(x, k=1.5):
    """Écrêtage doux (tanh) : du punch sans saturation dure."""
    t = math.tanh
    g = 1.0 / t(k)
    return [t(k * v) * g for v in x]


_SINC_POINTS = 24          # points de l'interpolateur (i-11 … i+12)
_SINC_SUR = 8              # positions estimées entre deux échantillons (1/8 … 7/8)


def _coeffs_sinc():
    """Coefficients d'interpolation sinc fenêtrée (24 points, fenêtre de Hann) aux positions k/8 entre deux
    échantillons : sert à estimer le signal reconstruit par le rééchantillonneur du navigateur."""
    out = []
    demi = _SINC_POINTS // 2
    for k in range(1, _SINC_SUR):
        frac = k / _SINC_SUR
        c = []
        for p in range(-demi + 1, demi + 1):         # échantillons i-11 … i+12 autour de la position i+frac
            d = p - frac
            s = math.sin(math.pi * d) / (math.pi * d)
            c.append(s * 0.5 * (1.0 + math.cos(math.pi * d / (demi + 0.5))))
        somme = sum(c)
        out.append([v / somme for v in c])           # gain unité en continu
    return out


_SINC = _coeffs_sinc()


def _pic_inter(x, seuil):
    """Pic INTER-échantillons estimé (interpolation sinc à 8×) autour des échantillons dont |x| > seuil.
    Chromium rééchantillonne les WAV à 44,1 kHz : un bruit riche près de Nyquist dont les échantillons
    plafonnent à 0,8 peut alors dépasser 1,0 entre deux échantillons (mesuré : tir_pistolet à 1,01)."""
    n = len(x)
    pic = 0.0
    a = abs
    demi = _SINC_POINTS // 2
    for i in range(n - 1):
        if a(x[i]) > seuil or a(x[i + 1]) > seuil:
            debut = i - demi + 1
            if debut >= 0 and i + demi < n:
                fen = x[debut:i + demi + 1]
                for c in _SINC:
                    v = sum(w * s for w, s in zip(c, fen))
                    if a(v) > pic:
                        pic = a(v)
            else:                                    # bord : les échantillons manquants valent 0
                for c in _SINC:
                    v = 0.0
                    for k, w in enumerate(c):
                        j = debut + k
                        if 0 <= j < n:
                            v += w * x[j]
                    if a(v) > pic:
                        pic = a(v)
    return pic


def _finir(x, rate, pic=0.8, attaque=0.002, relache=0.01):
    """Fondu d'attaque et de relâchement (anti-clic) puis normalisation du pic — pic des échantillons ET
    pic inter-échantillons estimé, pour que le son rééchantillonné par le navigateur reste sous `pic`."""
    n = len(x)
    na = max(1, _n(attaque, rate))
    nr = max(1, _n(relache, rate))
    for i in range(min(na, n)):
        x[i] *= i / na
    for i in range(min(nr, n)):
        x[n - 1 - i] *= i / nr
    m = max(abs(v) for v in x) or 1.0
    inter = _pic_inter(x, 0.5 * m)
    if inter > m:
        m = 1.03 * inter        # marge : l'estimateur sous-évalue de ~2 % le contenu collé à Nyquist (mesuré dans Chromium)
    g = pic / m
    return [g * v for v in x]


# --- timbres ----------------------------------------------------------------
_NOTES = {"C": 0, "C#": 1, "D": 2, "D#": 3, "E": 4, "F": 5, "F#": 6, "G": 7, "G#": 8, "A": 9, "A#": 10, "B": 11}


def _hz(nom):
    """'A4' -> 440.0 ; 'C#5' -> 554.37."""
    octave = int(nom[-1])
    demi = _NOTES[nom[:-1]]
    return 440.0 * 2.0 ** ((octave - 4) + (demi - 9) / 12.0)


def _cloche(n, rate, f, tau=0.3, brillance=1.0):
    """Cloche / carillon : partiels inharmoniques, les aigus s'éteignent plus vite."""
    out = [0.0] * n
    e = math.exp
    for mult, amp, vitesse in ((1.0, 1.0, 1.0), (2.0, 0.55 * brillance, 1.6), (3.0, 0.3 * brillance, 2.2),
                               (4.16, 0.15 * brillance, 3.0), (5.43, 0.08 * brillance, 4.0)):
        if f * mult >= 0.45 * rate:
            continue
        k = vitesse / (tau * rate)
        v = _sinus(n, rate, f * mult)
        out = [o + amp * s * e(-i * k) for i, (o, s) in enumerate(zip(out, v))]
    na = max(1, _n(0.002, rate))
    for i in range(min(na, n)):
        out[i] *= i / na
    return out


def _pince(n, rate, f, tau=0.15):
    """Corde pincée (arpèges)."""
    v = _additif(n, rate, f, ((1, 1.0), (2, 0.45), (3, 0.2), (4, 0.08)))
    return _mult(v, _env_perc(n, rate, 0.002, tau))


def _nappe(n, rate, f, attaque=0.06, relache=0.12, desaccord=0.004):
    """Nappe chaude : deux voix légèrement désaccordées, filtrées."""
    partiels = ((1, 1.0), (2, 0.5), (3, 0.25), (4, 0.12), (5, 0.06))
    a = _additif(n, rate, f * (1 + desaccord), partiels)
    b = _additif(n, rate, f * (1 - desaccord), partiels, phase=1.3)
    v = _passe_bas([p + q for p, q in zip(a, b)], 1400, rate)
    return _mult(v, _env_adsr(n, rate, attaque, 0.0, 1.0, relache))


def _cuivre(n, rate, f, attaque=0.02, relache=0.06, vibrato=0.004):
    """Cuivre de fanfare : riche en harmoniques, filtre qui s'ouvre, léger vibrato."""
    freqs = [f * (1 + vibrato * math.sin(TAU * 5.5 * i / rate)) for i in range(n)]
    v = _additif(n, rate, freqs, ((1, 1.0), (2, 0.75), (3, 0.55), (4, 0.4), (5, 0.3), (6, 0.22), (7, 0.16), (8, 0.12)))
    fc = [900 + 2600 * min(1.0, i / (0.08 * rate)) for i in range(n)]
    v = _passe_bas(v, fc, rate)
    return _mult(v, _env_adsr(n, rate, attaque, 0.08, 0.8, relache))


def _basse(n, rate, f, tau=0.4):
    v = _additif(n, rate, f, ((1, 1.0), (2, 0.35), (3, 0.12)))
    return _mult(v, _env_perc(n, rate, 0.006, tau))


# ---------------------------------------------------------------------------
#  Générateurs (un par son de contrat.SONS) : renvoient une liste normalisée
# ---------------------------------------------------------------------------
def _tir_pistolet(rate):
    """Pistolet : claquement sec et court."""
    n = _n(0.16, rate)
    b = _passe_haut(_bruit(n, 11), 250, rate)
    b = _passe_bas(b, _glisse(n, rate, 7000, 900, 0.12), rate)
    b = _mult(b, _env_perc(n, rate, 0.0005, 0.02))
    corps = _mult(_sinus(n, rate, _glisse(n, rate, 230, 60, 0.08)), _env_perc(n, rate, 0.001, 0.035))
    out = _doux([x + 0.8 * y for x, y in zip(b, corps)], 1.6)
    return _finir(out, rate, 0.8, 0.0007, 0.01)


def _tir_pompe(rate):
    """Fusil à pompe : détonation grave et large."""
    n = _n(0.45, rate)
    b = _passe_bas(_bruit(n, 12), _glisse(n, rate, 3500, 350, 0.3), rate)
    b = _mult(b, _env_perc(n, rate, 0.001, 0.07))
    sub = _mult(_sinus(n, rate, _glisse(n, rate, 120, 38, 0.2)), _env_perc(n, rate, 0.002, 0.13))
    out = _doux([x + 1.1 * y for x, y in zip(b, sub)], 2.0)
    return _finir(out, rate, 0.8, 0.0007, 0.03)


def _tir_sniper(rate):
    """Sniper : claquement très bref, détonation longue, échos en queue."""
    n = _n(1.0, rate)
    nc = _n(0.06, rate)
    clac = _mult(_passe_haut(_bruit(nc, 13), 1500, rate), _env_perc(nc, rate, 0.0003, 0.008))
    boum = _mult(_passe_bas(_bruit(n, 14), _glisse(n, rate, 1500, 200, 0.5), rate), _env_perc(n, rate, 0.002, 0.2))
    sub = _mult(_sinus(n, rate, _glisse(n, rate, 85, 28, 0.35)), _env_perc(n, rate, 0.003, 0.28))
    out = [0.0] * n
    _ajouter(out, clac, 0, 1.0)
    _ajouter(out, boum, 0, 0.9)
    _ajouter(out, sub, 0, 0.9)
    sec = _passe_bas(out[:_n(0.3, rate)], 900, rate)
    for retard, g in ((0.13, 0.35), (0.31, 0.18), (0.55, 0.09)):
        _ajouter(out, sec, _n(retard, rate), g)
    return _finir(_doux(out, 1.8), rate, 0.8, 0.0006, 0.05)


def _touche(rate):
    """Touche : tic métallique aigu."""
    n = _n(0.08, rate)
    out = [0.0] * n
    for f, g, tau in ((3150, 1.0, 0.014), (4700, 0.6, 0.010), (6300, 0.35, 0.007)):
        if f < 0.45 * rate:
            _ajouter(out, _mult(_sinus(n, rate, f), _env_perc(n, rate, 0.0005, tau)), 0, g)
    nc = _n(0.004, rate)
    _ajouter(out, _mult(_bruit(nc, 15), _env_perc(nc, rate, 0.0002, 0.001)), 0, 0.5)
    return _finir(out, rate, 0.75, 0.0006, 0.008)


def _elimination(rate):
    """Élimination : jingle de trois notes montantes (la majeur)."""
    n = _n(0.6, rate)
    out = [0.0] * n
    for t, nom, d in ((0.0, "A5", 0.2), (0.11, "C#6", 0.2), (0.22, "E6", 0.38)):
        _ajouter(out, _cloche(_n(d, rate), rate, _hz(nom), 0.12 if d < 0.3 else 0.16, 0.8), _n(t, rate), 0.7)
    return _finir(out, rate, 0.8, 0.001, 0.02)


def _degats(rate):
    """Dégâts reçus : coup grave et sourd."""
    n = _n(0.3, rate)
    thud = _mult(_sinus(n, rate, _glisse(n, rate, 130, 45, 0.15)), _env_perc(n, rate, 0.002, 0.08))
    souffle = _mult(_passe_bas(_bruit(n, 16), 450, rate), _env_perc(n, rate, 0.001, 0.05))
    out = _doux([x + 0.7 * y for x, y in zip(thud, souffle)], 1.4)
    return _finir(out, rate, 0.8, 0.001, 0.03)


def _coffre(rate):
    """Coffre : arpège doré montant + scintillement."""
    n = _n(0.8, rate)
    out = [0.0] * n
    for k, nom in enumerate(("C5", "E5", "G5", "C6", "E6")):
        _ajouter(out, _cloche(_n(0.45, rate), rate, _hz(nom), 0.22, 0.9), _n(0.1 * k, rate), 0.45 + 0.05 * k)
    ns = _n(0.6, rate)
    sc = _mult(_passe_haut(_bruit(ns, 17), 5500, rate), _env_adsr(ns, rate, 0.15, 0.0, 1.0, 0.3))
    _ajouter(out, sc, _n(0.2, rate), 0.06)
    return _finir(out, rate, 0.8, 0.001, 0.03)


def _construction(rate):
    """Construction : toc de bois (résonateurs)."""
    n = _n(0.16, rate)
    imp = _mult(_bruit(n, 18), _env_perc(n, rate, 0.0003, 0.004))
    bois = [0.0] * n
    for f, q, g in ((380, 9.0, 1.0), (820, 12.0, 0.5), (1350, 14.0, 0.25)):
        _ajouter(bois, _passe_bande(imp, f, q, rate), 0, g)
    thunk = _mult(_sinus(n, rate, _glisse(n, rate, 200, 120, 0.05)), _env_perc(n, rate, 0.001, 0.04))
    out = [4.0 * x + 0.6 * y for x, y in zip(bois, thunk)]
    return _finir(out, rate, 0.8, 0.0007, 0.02)


def _pioche(rate):
    """Pioche : coup sec + petit grésillement d'étincelles."""
    n = _n(0.22, rate)
    out = [0.0] * n
    nc = _n(0.03, rate)
    _ajouter(out, _mult(_passe_haut(_bruit(nc, 19), 1800, rate), _env_perc(nc, rate, 0.0003, 0.005)), 0, 1.0)
    _ajouter(out, _mult(_sinus(nc * 2, rate, 2600), _env_perc(nc * 2, rate, 0.0005, 0.02)), 0, 0.4)
    r = random.Random(20)
    gres = [0.0] * n
    for i in range(_n(0.01, rate), n):
        if r.random() < 0.02 * (1.0 - i / n):
            gres[i] = r.uniform(-1.0, 1.0)
    _ajouter(out, _passe_bas(gres, 3500, rate), 0, 1.2)
    return _finir(out, rate, 0.8, 0.0006, 0.02)


def _rechargement(rate):
    """Rechargement : deux clics mécaniques (clic-clac)."""
    n = _n(0.4, rate)
    out = [0.0] * n
    for t, fb, fp, g, graine in ((0.0, 1800, 2400, 1.0, 21), (0.21, 1300, 1900, 0.9, 22)):
        nc = _n(0.08, rate)
        b = _mult(_bruit(nc, graine), _env_perc(nc, rate, 0.0003, 0.006))
        cl = _passe_bande(b, fb, 3.0, rate)
        ping = _mult(_sinus(nc, rate, fp), _env_perc(nc, rate, 0.0005, 0.02))
        _ajouter(out, [3.0 * x + 0.5 * y for x, y in zip(cl, ping)], _n(t, rate), g)
    return _finir(out, rate, 0.75, 0.0006, 0.02)


def _clic(rate):
    """Clic d'interface : court."""
    n = _n(0.06, rate)
    out = _mult(_sinus(n, rate, 1500), _env_perc(n, rate, 0.001, 0.012))
    nc = _n(0.005, rate)
    _ajouter(out, _mult(_bruit(nc, 23), _env_perc(nc, rate, 0.0002, 0.0015)), 0, 0.5)
    return _finir(out, rate, 0.55, 0.0007, 0.01)


def _survol(rate):
    """Survol d'interface : très court et doux (55 ms : les effets durent au moins 50 ms)."""
    n = _n(0.055, rate)
    out = _mult(_sinus(n, rate, 2200), _env_perc(n, rate, 0.002, 0.009))
    return _finir(out, rate, 0.4, 0.001, 0.008)


def _victoire(rate):
    """Victoire : fanfare de six notes (do do do mi sol DO) + accord final."""
    n = _n(2.0, rate)
    out = [0.0] * n
    for t, d, nom in ((0.0, 0.14, "C5"), (0.17, 0.14, "C5"), (0.34, 0.14, "C5"), (0.51, 0.28, "E5"),
                      (0.82, 0.28, "G5"), (1.13, 0.82, "C6")):
        _ajouter(out, _cuivre(_n(d, rate), rate, _hz(nom), 0.012, 0.05), _n(t, rate), 0.55)
    for nom in ("C4", "E4", "G4"):
        _ajouter(out, _cuivre(_n(0.85, rate), rate, _hz(nom), 0.03, 0.25, 0.003), _n(1.13, rate), 0.22)
    ncy = _n(0.7, rate)
    cymbale = _mult(_passe_haut(_bruit(ncy, 42), 4000, rate), _env_perc(ncy, rate, 0.005, 0.18))
    _ajouter(out, cymbale, _n(1.13, rate), 0.12)
    return _finir(out, rate, 0.8, 0.002, 0.03)


def _defaite(rate):
    """Défaite : deux notes descendantes (sol -> mi bémol), timbre mou qui s'affaisse."""
    n = _n(1.0, rate)
    out = [0.0] * n
    for t, d, nom in ((0.0, 0.42, "G4"), (0.42, 0.58, "D#4")):
        nn = _n(d, rate)
        f = _hz(nom)
        v = _additif(nn, rate, _glisse(nn, rate, f, f * 0.985, d), ((1, 1.0), (2, 0.3), (3, 0.35), (5, 0.12)))
        v = _passe_bas(v, 1800, rate)
        v = _mult(v, _env_adsr(nn, rate, 0.02, 0.1, 0.8, 0.12 if t == 0 else 0.3))
        _ajouter(out, v, _n(t, rate), 0.8)
    return _finir(out, rate, 0.75, 0.002, 0.03)


def _tempete(rate):
    """Tempête : nappe de bruit filtré qui ondule, avec grondement."""
    n = _n(2.0, rate)
    fc = [550 + 350 * math.sin(TAU * 0.7 * i / rate) for i in range(n)]
    vent = _passe_bas(_bruit(n, 24), fc, rate)
    grond = _passe_bas(_bruit(n, 25), 70, rate)
    out = [x + 4.0 * y for x, y in zip(vent, grond)]
    out = _mult(out, _env_adsr(n, rate, 0.3, 0.0, 1.0, 0.4))
    return _finir(out, rate, 0.7, 0.01, 0.02)


def _saut(rate):
    """Saut : whoosh bref (bruit passe-bande montant)."""
    n = _n(0.25, rate)
    v = _passe_bande(_bruit(n, 26), _glisse(n, rate, 350, 2200, 0.2), 1.5, rate)
    v = _mult(v, _env_adsr(n, rate, 0.06, 0.0, 1.0, 0.12))
    return _finir(v, rate, 0.7, 0.005, 0.02)


def _bus(rate):
    """Bus de combat : moteur grave qui tousse."""
    n = _n(1.5, rate)
    f0 = [46 + 2.5 * math.sin(TAU * 0.8 * i / rate) for i in range(n)]
    moteur = _additif(n, rate, f0, ((1, 1.0), (2, 0.6), (3, 0.45), (4, 0.35), (5, 0.25), (6, 0.2), (8, 0.12)))
    am = [0.65 + 0.35 * math.sin(TAU * 23 * i / rate) for i in range(n)]
    moteur = _passe_bas(_mult(moteur, am), 500, rate)
    fumee = _mult(_passe_bas(_bruit(n, 27), 700, rate), am)
    out = [x + 0.35 * y for x, y in zip(moteur, fumee)]
    out = _mult(out, _env_adsr(n, rate, 0.12, 0.0, 1.0, 0.25))
    return _finir(_doux(out, 1.3), rate, 0.75, 0.01, 0.02)


def _parachute(rate):
    """Parachute : vent qui siffle doucement."""
    n = _n(1.5, rate)
    fc = [800 + 300 * math.sin(TAU * 0.55 * i / rate) for i in range(n)]
    v = _passe_bande(_bruit(n, 28), fc, 1.1, rate)
    v = _mult(v, [0.8 + 0.2 * math.sin(TAU * 6.5 * i / rate) for i in range(n)])
    v = _mult(v, _env_adsr(n, rate, 0.2, 0.0, 1.0, 0.3))
    return _finir(v, rate, 0.7, 0.01, 0.02)


def _emote(rate):
    """Émote : ding joyeux (petite note d'ornement puis note claire)."""
    n = _n(0.4, rate)
    out = [0.0] * n
    _ajouter(out, _cloche(_n(0.12, rate), rate, _hz("C6"), 0.06, 0.8), 0, 0.5)
    _ajouter(out, _cloche(_n(0.33, rate), rate, _hz("E6"), 0.14, 0.9), _n(0.07, rate), 0.8)
    return _finir(out, rate, 0.75, 0.001, 0.02)


def _notification(rate):
    """Notification : double ding."""
    n = _n(0.5, rate)
    out = [0.0] * n
    for t in (0.0, 0.17):
        _ajouter(out, _cloche(_n(0.3, rate), rate, _hz("A5"), 0.12, 0.9), _n(t, rate), 0.75)
    return _finir(out, rate, 0.75, 0.001, 0.02)


def _compte(rate):
    """Compte à rebours : bip."""
    n = _n(0.15, rate)
    v = _additif(n, rate, 880.0, ((1, 1.0), (2, 0.25), (3, 0.1)))
    v = _mult(v, _env_adsr(n, rate, 0.005, 0.0, 1.0, 0.04))
    return _finir(v, rate, 0.7, 0.003, 0.02)


def _niveau(rate):
    """Niveau gagné : arpège de quatre notes (ré majeur) + octave scintillante."""
    n = _n(0.8, rate)
    out = [0.0] * n
    for k, nom in enumerate(("D5", "F#5", "A5", "D6")):
        d, tau = (0.35, 0.2) if k < 3 else (0.5, 0.3)
        _ajouter(out, _cloche(_n(d, rate), rate, _hz(nom), tau, 1.0), _n(0.13 * k, rate), 0.5 + 0.08 * k)
    _ajouter(out, _cloche(_n(0.4, rate), rate, _hz("A6"), 0.25, 0.5), _n(0.52, rate), 0.2)
    return _finir(out, rate, 0.8, 0.001, 0.03)


def _soin(rate):
    """Soin : deux bulles douces."""
    n = _n(0.5, rate)
    out = [0.0] * n
    for t, f0, f1 in ((0.0, 330, 720), (0.2, 420, 920)):
        nb = _n(0.22, rate)
        v = _sinus(nb, rate, _glisse(nb, rate, f0, f1, 0.07))
        v = _passe_bas(_mult(v, _env_perc(nb, rate, 0.004, 0.06)), 2000, rate)
        _ajouter(out, v, _n(t, rate), 0.8)
    return _finir(out, rate, 0.7, 0.002, 0.03)


def _bouclier(rate):
    """Bouclier : shimmer cristallin (accord aigu en trémolo qui monte)."""
    n = _n(0.6, rate)
    out = [0.0] * n
    trem = [0.75 + 0.25 * math.sin(TAU * 13 * i / rate) for i in range(n)]
    for f, g in ((1760, 1.0), (2217, 0.7), (2637, 0.5), (3520, 0.3)):
        if f * 1.03 >= 0.45 * rate:
            continue
        _ajouter(out, _mult(_sinus(n, rate, _glisse(n, rate, f, f * 1.03, 0.5)), trem), 0, g)
    out = _mult(out, _env_adsr(n, rate, 0.05, 0.15, 0.6, 0.25))
    sc = _mult(_passe_haut(_bruit(n, 29), 4500, rate), _env_adsr(n, rate, 0.1, 0.0, 1.0, 0.3))
    _ajouter(out, sc, 0, 0.15)
    return _finir(out, rate, 0.7, 0.005, 0.03)


def _aterre(rate):
    """À terre : chute sourde en deux temps."""
    n = _n(0.4, rate)
    out = [0.0] * n
    for t, f0, f1, g, graine in ((0.0, 95, 32, 1.0, 30), (0.15, 70, 28, 0.6, 31)):
        nt = _n(0.25, rate)
        thud = _mult(_sinus(nt, rate, _glisse(nt, rate, f0, f1, 0.12)), _env_perc(nt, rate, 0.002, 0.09))
        souffle = _mult(_passe_bas(_bruit(nt, graine), 380, rate), _env_perc(nt, rate, 0.001, 0.045))
        _ajouter(out, [x + 0.9 * y for x, y in zip(thud, souffle)], _n(t, rate), g)
    return _finir(_doux(out, 1.5), rate, 0.8, 0.001, 0.03)


def _reanimation(rate):
    """Réanimation : montée qui s'éclaircit, conclue par un petit ding."""
    n = _n(0.8, rate)
    out = [0.0] * n
    nm = _n(0.62, rate)
    v = _additif(nm, rate, _glisse(nm, rate, 300, 900, 0.6), ((1, 1.0), (2, 0.4), (3, 0.15)))
    v = _mult(v, [0.25 + 0.75 * i / nm for i in range(nm)])
    v = _mult(v, _env_adsr(nm, rate, 0.02, 0.0, 1.0, 0.05))
    _ajouter(out, v, 0, 0.6)
    _ajouter(out, _cloche(_n(0.22, rate), rate, 1200.0, 0.12, 0.8), _n(0.58, rate), 0.7)
    return _finir(out, rate, 0.75, 0.003, 0.03)


BPM_SALON = 110
MESURES_SALON = 4


def duree_musique_salon():
    """Durée exacte de la boucle du salon : 4 mesures à 4 temps à 110 BPM (8,73 s)."""
    return MESURES_SALON * 4 * 60.0 / BPM_SALON


def _musique_salon(rate):
    """Boucle du salon : basse + nappes d'accords + arpège + shaker, do - sol - la m - fa.
    La queue des notes qui dépasse la fin est repliée au début : la boucle est continue."""
    temps = 60.0 / BPM_SALON
    mesure = 4 * temps
    N = _n(MESURES_SALON * mesure, rate)
    queue = _n(0.6, rate)
    buf = [0.0] * (N + queue)
    accords = [("C3", ("C4", "E4", "G4"), ("C5", "E5", "G5", "C6")),
               ("G2", ("B3", "D4", "G4"), ("G4", "B4", "D5", "G5")),
               ("A2", ("A3", "C4", "E4"), ("A4", "C5", "E5", "A5")),
               ("F2", ("A3", "C4", "F4"), ("F4", "A4", "C5", "F5"))]
    motif = (0, 1, 2, 3, 2, 1, 0, 1)
    nn = _n(mesure, rate)
    for m, (basse, nappe, arpege) in enumerate(accords):
        t0 = m * mesure
        for nom in nappe:
            _ajouter(buf, _nappe(nn, rate, _hz(nom)), _n(t0, rate), 0.16)
        for temps_k, g in ((0, 1.0), (2, 0.8)):
            _ajouter(buf, _basse(_n(temps * 1.6, rate), rate, _hz(basse)), _n(t0 + temps_k * temps, rate), 0.5 * g)
        _ajouter(buf, _basse(_n(temps * 0.5, rate), rate, _hz(basse) * 2), _n(t0 + 3.5 * temps, rate), 0.22)
        for k, idx in enumerate(motif):
            _ajouter(buf, _pince(_n(0.5, rate), rate, _hz(arpege[idx]), 0.14), _n(t0 + k * temps / 2, rate),
                     0.26 if k % 2 == 0 else 0.21)
            if k % 2 == 1:
                nh = _n(0.05, rate)
                shaker = _mult(_passe_bande(_bruit(nh, 7 + k + m * 8), 3800, 1.2, rate), _env_perc(nh, rate, 0.001, 0.012))
                _ajouter(buf, shaker, _n(t0 + k * temps / 2, rate), 0.16)
    for i in range(queue):
        buf[i] += buf[N + i]
    return _finir(buf[:N], rate, 0.7, 0.002, 0.002)


def _musique_fin(rate):
    """Fin de partie : cadence fa - sol - DO (résolution majeure), 4 s."""
    N = _n(4.0, rate)
    buf = [0.0] * N
    for t, d, basse, nappe, melodie, g in ((0.0, 0.9, "F2", ("F3", "A3", "C4"), "A4", 0.9),
                                            (0.9, 0.9, "G2", ("G3", "B3", "D4"), "B4", 0.9),
                                            (1.8, 2.2, "C2", ("E3", "G3", "C4", "E4"), "C5", 1.0)):
        nn = _n(d, rate)
        for nom in nappe:
            _ajouter(buf, _nappe(nn, rate, _hz(nom), 0.05, 0.15 if t < 1.8 else 1.0), _n(t, rate), 0.17 * g)
        _ajouter(buf, _basse(nn, rate, _hz(basse), 0.6 if t < 1.8 else 1.2), _n(t, rate), 0.5 * g)
        _ajouter(buf, _cuivre(nn, rate, _hz(melodie), 0.03, 0.12 if t < 1.8 else 1.2, 0.003), _n(t, rate), 0.28 * g)
    for k, nom in enumerate(("C6", "E6", "G6")):
        _ajouter(buf, _cloche(_n(1.2, rate), rate, _hz(nom), 0.4, 0.7), _n(1.8 + 0.12 * k, rate), 0.14)
    return _finir(buf, rate, 0.7, 0.002, 0.05)


def _explosion(rate):
    """Explosion (feu d'artifice) : détonation grave et ronde, 0,8 s, avec un léger crépitement."""
    n = _n(0.8, rate)
    boum = _mult(_passe_bas(_bruit(n, 51), _glisse(n, rate, 900, 120, 0.5), rate), _env_perc(n, rate, 0.003, 0.16))
    sub = _mult(_sinus(n, rate, _glisse(n, rate, 95, 30, 0.4)), _env_perc(n, rate, 0.004, 0.22))
    r = random.Random(52)
    crep = [0.0] * n
    for i in range(_n(0.08, rate), n):
        if r.random() < 0.012 * (1.0 - i / n):
            crep[i] = r.uniform(-1.0, 1.0)
    out = [x + 1.2 * y for x, y in zip(boum, sub)]
    _ajouter(out, _passe_bas(crep, 2500, rate), 0, 0.5)
    return _finir(_doux(out, 1.6), rate, 0.8, 0.002, 0.04)


def _serie(rate):
    """Série d'éliminations : jingle montant de quatre notes brillantes (mi majeur) + éclat final, 0,6 s."""
    n = _n(0.6, rate)
    out = [0.0] * n
    for t, nom, d in ((0.0, "E5", 0.14), (0.09, "G#5", 0.14), (0.18, "B5", 0.16), (0.27, "E6", 0.33)):
        _ajouter(out, _cloche(_n(d, rate), rate, _hz(nom), 0.11 if d < 0.3 else 0.15, 0.9), _n(t, rate), 0.65)
    ns = _n(0.3, rate)
    sc = _mult(_passe_haut(_bruit(ns, 53), 5000, rate), _env_perc(ns, rate, 0.01, 0.08))
    _ajouter(out, sc, _n(0.27, rate), 0.08)
    return _finir(out, rate, 0.8, 0.001, 0.02)


def _largage(rate):
    """Largage repéré : sifflement descendant (bruit passe-bande qui chute) sur 1,2 s."""
    n = _n(1.2, rate)
    v = _passe_bande(_bruit(n, 54), _glisse(n, rate, 2600, 380, 1.1), 2.5, rate)
    v = _mult(v, [0.85 + 0.15 * math.sin(TAU * 9 * i / rate) for i in range(n)])
    v = _mult(v, _env_adsr(n, rate, 0.08, 0.0, 1.0, 0.3))
    sif = _mult(_sinus(n, rate, _glisse(n, rate, 2400, 420, 1.1)), _env_adsr(n, rate, 0.1, 0.0, 1.0, 0.3))
    out = [3.0 * x + 0.25 * y for x, y in zip(v, sif)]
    return _finir(out, rate, 0.7, 0.005, 0.03)


def _kick(n, rate):
    """Grosse caisse synthétique : sinus qui chute + clic."""
    v = _mult(_sinus(n, rate, _glisse(n, rate, 150, 42, 0.09)), _env_perc(n, rate, 0.001, 0.09))
    nc = _n(0.006, rate)
    _ajouter(v, _mult(_bruit(nc, 61), _env_perc(nc, rate, 0.0003, 0.002)), 0, 0.5)
    return _doux(v, 1.4)


def _caisse(n, rate, graine=62):
    """Caisse claire : bruit filtré + corps bref."""
    b = _mult(_passe_bande(_bruit(n, graine), 1800, 0.8, rate), _env_perc(n, rate, 0.001, 0.05))
    c = _mult(_sinus(n, rate, _glisse(n, rate, 240, 170, 0.04)), _env_perc(n, rate, 0.001, 0.03))
    return [2.5 * x + 0.6 * y for x, y in zip(b, c)]


def _charley(n, rate, graine=63):
    return _mult(_passe_haut(_bruit(n, graine), 6000, rate), _env_perc(n, rate, 0.0005, 0.012))


def duree_musique_combat():
    """Durée exacte de la boucle de combat : 4 mesures à 4 temps à 128 BPM (7,5 s)."""
    return 4 * 4 * 60.0 / BPM_COMBAT


def _musique_combat(rate):
    """Boucle de combat (tendue, 128 BPM, 4 mesures) : grosse caisse à chaque temps, caisse claire sur 2 et 4,
    charley en croches, basse en doubles-croches sur mi mineur (mi - mi - do - ré), nappe tendue (quinte + 2de mineure).
    La queue des notes qui dépasse la fin est repliée au début : la boucle est continue."""
    temps = 60.0 / BPM_COMBAT
    mesure = 4 * temps
    N = _n(4 * mesure, rate)
    queue = _n(0.5, rate)
    buf = [0.0] * (N + queue)
    basses = ("E2", "E2", "C2", "D2")
    nappes = (("E3", "B3", "F4"), ("E3", "B3", "F4"), ("C3", "G3", "C#4"), ("D3", "A3", "D#4"))
    nk, ns, nh = _n(0.25, rate), _n(0.18, rate), _n(0.06, rate)
    kick, caisse, charley = _kick(nk, rate), _caisse(ns, rate), _charley(nh, rate)
    charley2 = _charley(nh, rate, 64)
    nb = _n(temps * 0.22, rate)
    for m in range(4):
        t0 = m * mesure
        for nom in nappes[m]:
            _ajouter(buf, _nappe(_n(mesure, rate), rate, _hz(nom), 0.04, 0.1, 0.006), _n(t0, rate), 0.09)
        f = _hz(basses[m])
        for k in range(16):
            t = t0 + k * temps / 4
            # motif de basse : fondamentale, octave sur les contretemps 3 et 7, silences sur 11 et 15
            if k in (3, 7):
                _ajouter(buf, _basse(nb, rate, f * 2, 0.08), _n(t, rate), 0.3)
            elif k not in (11, 15):
                _ajouter(buf, _basse(nb, rate, f, 0.1), _n(t, rate), 0.42)
            if k % 2 == 0:
                _ajouter(buf, charley if k % 4 == 0 else charley2, _n(t, rate), 0.16 if k % 4 == 0 else 0.1)
        for k in range(4):
            t = t0 + k * temps
            _ajouter(buf, kick, _n(t, rate), 0.8)
            if k in (1, 3):
                _ajouter(buf, caisse, _n(t, rate), 0.45)
        # roulement de caisse claire à la fin de la 4e mesure
        if m == 3:
            for k in range(4):
                _ajouter(buf, caisse, _n(t0 + 3 * temps + k * temps / 4, rate), 0.25 + 0.08 * k)
    for i in range(queue):
        buf[i] += buf[N + i]
    return _finir(_doux(buf[:N], 1.2), rate, 0.7, 0.002, 0.002)


def _musique_tempete(rate):
    """Nappe de tempête (8 s, bouclable) : bourdon grave désaccordé, triton lent, souffle filtré qui ondule et
    battements sourds irréguliers — inquiétant."""
    N = _n(8.0, rate)
    queue = _n(0.8, rate)
    buf = [0.0] * (N + queue)
    for nom, g, des in (("A1", 0.5, 0.006), ("E2", 0.3, 0.004), ("D#3", 0.16, 0.009)):
        f = _hz(nom)
        a = _additif(N, rate, f * (1 + des), ((1, 1.0), (2, 0.5), (3, 0.3), (4, 0.15)))
        b = _additif(N, rate, f * (1 - des), ((1, 1.0), (2, 0.4), (3, 0.25)), phase=0.7)
        v = _passe_bas([p + q for p, q in zip(a, b)], 600, rate)
        lent = [0.7 + 0.3 * math.sin(TAU * 0.11 * i / rate + des * 100) for i in range(N)]
        _ajouter(buf, _mult(v, lent), 0, g)
    fc = [320 + 220 * math.sin(TAU * 0.17 * i / rate) for i in range(N)]
    vent = _passe_bas(_bruit(N, 71), fc, rate)
    _ajouter(buf, vent, 0, 0.5)
    nb = _n(0.5, rate)
    for t, g in ((0.6, 1.0), (2.9, 0.7), (3.4, 0.5), (5.8, 0.9), (7.3, 0.6)):
        thud = _mult(_sinus(nb, rate, _glisse(nb, rate, 70, 32, 0.3)), _env_perc(nb, rate, 0.01, 0.14))
        _ajouter(buf, thud, _n(t, rate), 0.7 * g)
    for i in range(queue):
        buf[i] += buf[N + i]
    return _finir(buf[:N], rate, 0.7, 0.002, 0.002)


GENERATEURS = {
    "tir_pistolet": _tir_pistolet, "tir_pompe": _tir_pompe, "tir_sniper": _tir_sniper, "touche": _touche,
    "elimination": _elimination, "degats": _degats, "coffre": _coffre, "construction": _construction,
    "pioche": _pioche, "rechargement": _rechargement, "clic": _clic, "survol": _survol, "victoire": _victoire,
    "defaite": _defaite, "tempete": _tempete, "saut": _saut, "bus": _bus, "parachute": _parachute, "emote": _emote,
    "notification": _notification, "compte": _compte, "niveau": _niveau, "soin": _soin, "bouclier": _bouclier,
    "aterre": _aterre, "reanimation": _reanimation, "musique_salon": _musique_salon, "musique_fin": _musique_fin,
    "explosion": _explosion, "serie": _serie, "largage": _largage,
    "musique_combat": _musique_combat, "musique_tempete": _musique_tempete,
}
assert set(GENERATEURS) == set(TOUS_LES_SONS), "GENERATEURS et contrat.SONS (+ SONS_SUPPLEMENTAIRES) divergent : %s" % (
    set(GENERATEURS) ^ set(TOUS_LES_SONS))

_CACHE = {}


def generer(nom, rate=None):
    """Échantillons (liste de flottants, pic <= 0,8) et taux d'un son. Mémorisé."""
    rate = rate or taux(nom)
    cle = (nom, rate)
    if cle not in _CACHE:
        _CACHE[cle] = GENERATEURS[nom](rate)
    return _CACHE[cle], rate


def fabriquer_sons():
    """{nom: (octets_wav, rate, nombre_d_echantillons)} pour tous les sons (TOUS_LES_SONS)."""
    banque = {}
    for nom in TOUS_LES_SONS:
        ech, rate = generer(nom)
        banque[nom] = (wav(ech, rate), rate, len(ech))
    return banque


def infos(banque=None):
    """{nom: {'duree', 'pic', 'pic_inter', 'rate', 'octets', 'categorie', 'debut', 'fin'}} — pour inspection
    (pic_inter : pic inter-échantillons estimé, voir _pic_inter)."""
    banque = banque or fabriquer_sons()
    out = {}
    for nom in TOUS_LES_SONS:
        ech, rate = generer(nom, banque[nom][1])
        bord = max(1, int(rate * 0.001))
        pic = max(abs(v) for v in ech)
        out[nom] = {"duree": len(ech) / rate, "pic": pic, "pic_inter": max(pic, _pic_inter(ech, 0.5 * pic)), "rate": rate,
                    "octets": len(banque[nom][0]), "categorie": categorie(nom),
                    "debut": max(abs(v) for v in ech[:bord]), "fin": max(abs(v) for v in ech[-bord:])}
    return out


# ---------------------------------------------------------------------------
#  Sprite « Sons »
# ---------------------------------------------------------------------------
def volume_actuel():
    """Reporter `volume` du sprite (opcode sound_volume) — ajout local au DSL."""
    return Node("sound_volume")


def _sur_ecran_musique():
    e = Var("ecran")
    return ou(ou(eq(e, ECRANS_MUSIQUE[0]), eq(e, ECRANS_MUSIQUE[1])), ou(eq(e, ECRANS_MUSIQUE[2]), eq(e, ECRANS_MUSIQUE[3])))


def _cloner_avec_role(role):
    """Crée un clone qui naît avec son_estClone = 1 et son_role = role (les locales sont copiées à la création)."""
    return [setv("son_role", role), setv("son_estClone", 1), cloner_moi(), setv("son_estClone", 0), setv("son_role", "")]


def installer(P, banque=None):
    """Crée le sprite « Sons » (invisible, calque CALQUES['Sons']) avec les 28 sons du contrat + les 5 sons du
    spectacle et ses scripts. Renvoie la Cible."""
    from .svg import svg_vide
    S = Cible(P, "Sons")
    S.visible = False
    S.layer = contrat.CALQUES["Sons"]
    S.costumes = [P.costume("vide", svg_vide(), 2, 2)]
    banque = banque if banque is not None else fabriquer_sons()
    for nom in TOUS_LES_SONS:
        octets, rate, n = banque[nom]
        S.son_wav(nom, octets, rate, n)
    for nom, val in (("son_estClone", 0), ("son_musiqueActive", 0), ("son_role", ""),
                     ("son_niveauClone", 100), ("son_panClone", 0), ("son_dernierPan", 0),
                     ("son_combatFin", 0), ("son_voulu", 0), ("son_k", 0), ("son_dx", 0), ("son_dy", 0)):
        S.var(nom, val)
    P.stage.var("son_musiqueLecteur", 0)      # globale privée : le clone musique y écrit 1 à sa naissance
    P.stage.var("son_musiqueJeu", 0)          # globale privée : musique dynamique en cours (0 rien, 1 combat, 2 tempête)
    V = Var
    init = [setv("son_estClone", 0), setv("son_musiqueActive", 0), setv("son_role", ""), setv("son_dernierPan", 0),
            setv("son_combatFin", 0), setv("son_voulu", 0), setv("son_musiqueJeu", 0)]
    # --- musique dynamique en jeu : combat quand un ennemi vivant est proche (hystérésis), tempête hors zone -----
    # Appelé chaque image hors des écrans de menu. son_voulu = 0/1/2 ; au changement, le clone courant est supprimé
    # (« son stop musique jeu ») et un clone « combat » / « tempete » joue sa boucle au volume param_volumeMusique.
    ennemi = et(et(non(eq(V("son_k"), V("monSlot"))), eq(item("E_actif", V("son_k")), 1)),
                et(ou(eq(item("E_etat", V("son_k")), 1), eq(item("E_etat", V("son_k")), 3)),
                   ou(eq(V("monEquipe"), 0), non(eq(item("E_equipe", V("son_k")), V("monEquipe"))))))
    S.proc("musique jeu", [], [
        setv("son_voulu", 0),
        si(et(eq(V("ecran"), "jeu"), ou(eq(V("etat"), 1), eq(V("etat"), 3))), [
            si(eq(V("horsZone"), 1), [setv("son_voulu", 2)], [
                setv("son_k", 1),
                repeter(contrat.NB_JOUEURS, [
                    si(ennemi, [
                        setv("son_dx", sub(item("E_x", V("son_k")), V("px"))), setv("son_dy", sub(item("E_y", V("son_k")), V("py"))),
                        si(lt(add(mul(V("son_dx"), V("son_dx")), mul(V("son_dy"), V("son_dy"))), DISTANCE_COMBAT ** 2),
                           [setv("son_combatFin", add(chrono(), HYSTERESIS_COMBAT))]),
                    ]),
                    changev("son_k", 1),
                ]),
                si(gt(V("son_combatFin"), chrono()), [setv("son_voulu", 1)]),
            ]),
        ], [setv("son_combatFin", 0)]),
        si(non(eq(V("son_voulu"), V("son_musiqueJeu"))), [
            si(gt(V("son_musiqueJeu"), 0), [diffuser("son stop musique jeu")]),
            setv("son_musiqueJeu", V("son_voulu")),
            si(eq(V("son_voulu"), 1), _cloner_avec_role("combat")),
            si(eq(V("son_voulu"), 2), _cloner_avec_role("tempete")),
        ]),
    ])

    # --- initialisation et surveillance de l'écran pour la musique ---------------
    S.script(quand_drapeau(), list(init))
    # Les clones reçoivent aussi « demarrer » (relance sans drapeau vert) : ils se suppriment, et seul
    # l'original remet ses locales à zéro puis surveille l'écran (la musique repart proprement).
    # Si « créer un clone » échoue (limite de 300 clones atteinte), le clone musique ne naît jamais : la globale
    # son_musiqueLecteur (mise à 0 avant le clonage, à 1 par le clone à sa naissance) reste à 0 et l'original
    # réessaie toutes les 0,3 s. Un « son stop musique » volontaire laisse son_musiqueLecteur à 1 : pas de reprise.
    S.script(quand_message("demarrer"), [si(eq(V("son_estClone"), 1), [supprimer_clone()], init + [
        volume(100), effet_son("PAN", 0),
        toujours([
            si(_sur_ecran_musique(),
               [si(gt(V("son_musiqueJeu"), 0), [setv("son_musiqueJeu", 0), setv("son_combatFin", 0), diffuser("son stop musique jeu")]),
                si(eq(V("son_musiqueActive"), 0),
                   [setv("son_musiqueActive", 1), setv("son_musiqueLecteur", 0)] + _cloner_avec_role("musique"),
                   [si(eq(V("son_musiqueLecteur"), 0),
                       [attendre(0.3), si(eq(V("son_musiqueLecteur"), 0), [setv("son_musiqueActive", 0)])])])],
               [si(eq(V("son_musiqueActive"), 1), [setv("son_musiqueActive", 0), diffuser("son stop musique")]),
                appel("musique jeu")]),
        ])])])

    # --- un script par son ---------------------------------------------------------
    for nom in TOUS_LES_SONS:
        niveau = div(mul(V(parametre_volume(nom)), V("son_volume")), 100)
        if categorie(nom) == "effets":
            corps = [
                si(non(eq(volume_actuel(), niveau)), [volume(niveau)]),
                si(non(eq(V("son_pan"), V("son_dernierPan"))),
                   [setv("son_dernierPan", V("son_pan")), effet_son("PAN", V("son_pan"))]),
                son(nom),
            ]
        else:   # musique et voix : un clone éphémère au volume indépendant
            corps = [setv("son_niveauClone", niveau), setv("son_panClone", V("son_pan"))] + _cloner_avec_role(nom)
            if nom == "musique_salon":
                # la boucle du salon est automatique : un lecteur par son et par sprite, un second départ
                # ne ferait que la relancer au début ; ignoré tant que la boucle est active
                corps = [si(eq(V("son_musiqueActive"), 0), corps)]
        S.script(quand_message("son " + nom), [si(eq(V("son_estClone"), 0), corps)])

    # --- clones : musique en boucle ou jingle joué jusqu'au bout ---------------------
    # Un clone naît à volume 100 mais avec le PAN de l'original (état sonore copié) ; son_dernierPan,
    # copié lui aussi, dit quel PAN il a hérité : on ne règle (une image perdue) que ce qui change.
    jingles = [si(eq(V("son_role"), nom), [son_attendre(nom)]) for nom in TOUS_LES_SONS if categorie(nom) != "effets"]
    boucles = {"musique": "musique_salon", "combat": "musique_combat", "tempete": "musique_tempete"}
    est_boucle = ou3(eq(V("son_role"), "musique"), eq(V("son_role"), "combat"), eq(V("son_role"), "tempete"))
    S.script(quand_clone(), [
        si(est_boucle,
           [si(eq(V("son_role"), "musique"), [setv("son_musiqueLecteur", 1)]),   # « je suis né » (voir « demarrer »)
            si(non(eq(V("son_dernierPan"), 0)), [effet_son("PAN", 0)]),           # musique toujours au centre
            volume(V("param_volumeMusique"))]
           + [si(eq(V("son_role"), role), [toujours([son_attendre(piste)])]) for role, piste in boucles.items()],
           [si(non(eq(volume_actuel(), V("son_niveauClone"))), [volume(V("son_niveauClone"))]),
            si(non(eq(V("son_panClone"), V("son_dernierPan"))), [effet_son("PAN", V("son_panClone"))])]
           + jingles + [supprimer_clone()])])
    # volume de la musique suivi en temps réel (le réglage s'applique au son en cours)
    S.script(quand_clone(), [si(est_boucle, [toujours([volume(V("param_volumeMusique")), attendre(0.1)])])])

    # --- arrêts ----------------------------------------------------------------------
    S.script(quand_message("son stop musique"),
             [si(et(eq(V("son_estClone"), 1), eq(V("son_role"), "musique")), [supprimer_clone()])])
    S.script(quand_message("son stop musique jeu"),
             [si(et(eq(V("son_estClone"), 1), ou(eq(V("son_role"), "combat"), eq(V("son_role"), "tempete"))), [supprimer_clone()])])
    S.script(quand_message("son stop tout"),
             [si(eq(V("son_estClone"), 1), [supprimer_clone()],
                [stop_sons(), setv("son_musiqueActive", 0), setv("son_musiqueJeu", 0), setv("son_combatFin", 0)])])
    return S


if __name__ == "__main__":
    import time
    t = time.time()
    b = fabriquer_sons()
    total = sum(len(o) for o, _, _ in b.values())
    print("%d sons, %.0f Ko, %.1f s de synthèse" % (len(b), total / 1024, time.time() - t))
    for nom, i in infos(b).items():
        print("%-14s %5d Hz %5.2f s pic %.2f (inter %.2f) %7d o  %s"
              % (nom, i["rate"], i["duree"], i["pic"], i["pic_inter"], i["octets"], i["categorie"]))
