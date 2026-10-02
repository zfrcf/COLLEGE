# -*- coding: utf-8 -*-
"""
Exporte les 28 WAV de la banque dans ce dossier (outils/demos/sons/*.wav) pour inspection
et les contrôle : relecture par le module `wave`, durées, pic <= 0,8, absence de clic aux
bords (premiers / derniers échantillons), continuité de la boucle du salon, taille totale.

    python3 outils/demos/sons/ecoute.py
"""
import math
import os
import struct
import sys
import wave

ICI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(ICI, "..", "..", "..")))
from royale import contrat, sons  # noqa: E402

DUREES_ATTENDUES = {"musique_salon": (8.6, 8.9), "musique_fin": (3.9, 4.1)}


def rms(x):
    return math.sqrt(sum(v * v for v in x) / max(1, len(x)))


def main():
    banque = sons.fabriquer_sons()
    erreurs = []
    total = 0
    duree_totale = 0.0
    print("%-14s %-8s %5s %6s %6s %6s %7s %7s %7s %8s   %s" % ("son", "cat.", "Hz", "durée", "pic", "RMS", "x[0,1]", "fin 1ms", "saut", "octets",
                                                               "[3 premiers … 3 derniers échantillons]"))
    for nom in contrat.SONS:
        octets, rate, n = banque[nom]
        chemin = os.path.join(ICI, nom + ".wav")
        with open(chemin, "wb") as f:
            f.write(octets)
        with wave.open(chemin, "rb") as w:
            ok = (w.getnchannels() == 1 and w.getsampwidth() == 2 and w.getframerate() == rate and w.getnframes() == n)
            if not ok:
                erreurs.append("%s : en-tête WAV incohérent (%d canaux, %d octets, %d Hz, %d trames)"
                               % (nom, w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()))
            trames = w.readframes(n)
        x = [v / 32768.0 for v in struct.unpack("<%dh" % n, trames)]
        duree = n / rate
        pic = max(abs(v) for v in x)
        bord = max(2, int(rate * 0.001))                 # dernière milliseconde
        # un clic = une marche au bord : le premier échantillon doit être nul et le 2e déjà petit
        # (rampe d'attaque), la dernière milliseconde doit être quasi silencieuse (relâchement).
        debut = max(abs(x[0]), abs(x[1]))
        fin = max(abs(v) for v in x[-bord:])
        saut = max(abs(x[i] - x[i - 1]) for i in range(1, n))
        total += len(octets)
        duree_totale += duree
        cat = sons.categorie(nom)
        print("%-14s %-8s %5d %5.2fs %6.3f %6.3f %7.4f %7.4f %7.3f %8d   [%s … %s]"
              % (nom, cat, rate, duree, pic, rms(x), debut, fin, saut, len(octets),
                 " ".join("%.3f" % v for v in x[:3]), " ".join("%.3f" % v for v in x[-3:])))
        if pic > 0.8 + 1e-3:
            erreurs.append("%s : pic %.3f > 0,8" % (nom, pic))
        # le navigateur rééchantillonne à 44,1 kHz : le pic entre deux échantillons compte aussi
        pic_inter = sons._pic_inter(x, 0.5 * pic)
        if pic_inter > 0.8 + 0.01:
            erreurs.append("%s : pic inter-échantillons %.3f > 0,8 (écrêtage après rééchantillonnage)" % (nom, pic_inter))
        if abs(x[0]) > 0.01 or abs(x[-1]) > 0.01:
            erreurs.append("%s : premier/dernier échantillon non nul (%.3f / %.3f) → clic" % (nom, x[0], x[-1]))
        if debut > 0.1:
            erreurs.append("%s : pas de rampe d'attaque (2e échantillon %.3f) → clic" % (nom, debut))
        if fin > 0.05:
            erreurs.append("%s : pas de relâchement (dernière ms %.3f) → clic" % (nom, fin))
        lo, hi = DUREES_ATTENDUES.get(nom, (0.05, 2.0))     # énoncé : effets de 0,05 à 2 s
        if not (lo - 1e-9 <= duree <= hi + 1e-9):
            erreurs.append("%s : durée %.2f s hors de [%.2f, %.2f]" % (nom, duree, lo, hi))
        if nom == "musique_salon":
            # la queue est repliée au début : les 20 premières et dernières ms doivent se ressembler en niveau
            m = int(rate * 0.02)
            r_debut, r_fin = rms(x[m:2 * m]), rms(x[-2 * m:-m])
            print("   boucle du salon : RMS 20 ms après le début %.3f / avant la fin %.3f ; x[0]=%.4f x[-1]=%.4f ; "
                  "attendu %.3f s à %d BPM" % (r_debut, r_fin, x[0], x[-1], sons.duree_musique_salon(), sons.BPM_SALON))
            if abs(duree - sons.duree_musique_salon()) > 0.001:
                erreurs.append("musique_salon : durée %.4f ≠ %.4f" % (duree, sons.duree_musique_salon()))
    print("\n%d sons, %.1f s d'audio, %.0f Ko de WAV (limite visée : < 1,5 Mo pour le .sb3)" % (len(banque), duree_totale, total / 1024))
    if total > 1_500_000:
        erreurs.append("taille totale %d o > 1,5 Mo" % total)
    if erreurs:
        print("\nERREURS :")
        for e in erreurs:
            print(" -", e)
        return 1
    print("Tous les contrôles passent.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
