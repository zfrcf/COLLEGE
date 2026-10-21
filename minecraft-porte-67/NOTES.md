# Porte géante 67×67 en machines volantes : journal de recherche

Ce journal sert à reprendre le travail d'une session à l'autre. Le projet est en cours et aucun schématique final n'est livré.

## Objectif
Ouverture de 67 × 67 blocs, en redstone vanilla (Java 1.21.1) : pistons collants, slime, miel et observateurs, sans command blocks.

## Ce qui est validé sur un vrai serveur 1.21.1 (tick par tick)
- **Module de colonne** `modules/module_valide_P6.json` : moteur 2 sens dérivé du « slim engine » du wiki.
  - Un module porte un panneau de 1×6 et utilise 12 blocs par moitié, soit la limite de poussée.
  - Il occupe 2 plans en X (plan principal + plan latéral) et 3 de profondeur (z0..z2). Le plan z3 reste vide.
- **Colonne complète de 12 modules** (72 de haut) : elle monte de 72 puis redescend à l'identique, 0 bloc faux (`outils/t25.py`).
  - Chaînage en chenille : chaque module démarre quand son voisin bouge.
  - Arrêt exact par contact.
  - Retard intégré par **lampe redstone** : 4 ticks à l'extinction, alimentée par un bloc de redstone du voisin. Sans ce retard, le suiveur renvoie une impulsion au meneur et la colonne cale.

## Règles physiques apprises (pièges)
- Les observateurs se déclenchent quand on les pose ET quand un piston les déplace.
- Le miel ne conduit pas la redstone, le slime oui.
- **Quasi-connectivité** : un bloc de redstone voisin de la case AU-DESSUS d'un piston l'active. Ça a coûté un échec.
- Déclencher un meneur en ALLUMANT une lampe avec un bloc de redstone fixe est dangereux : quasi-connectivité, piston qui reste bloqué sorti.
  - Déclencher en RETIRANT le bloc (front descendant) fonctionne.
- Un bloc fixe mobile (piston rentré, bloc de redstone…) collé au trajet d'un slime est arraché.
  - Seuls l'obsidienne et les composants « destroy » (poudre, répéteur, torche) peuvent longer le trajet.

## Blocage actuel : l'étanchéité de la porte
Des colonnes de ce module ne peuvent pas se toucher : il faut un pas de 3 en X (principal, latéral, tampon). Couvrir toute la largeur demande donc 3 nappes en profondeur.
- `outils/leak.py` prouve qu'un joueur passerait par les tampons et les plans latéraux (FUITE).
- Recherches CP-SAT prouvées infaisables :
  - plan unique (P=5, 6, 7, fenêtre élargie) ;
  - colonnes de pas 1 ;
  - colonnes de pas 2 ;
  - colonnes de 3 de large à face pleine ;
  - 2 ou 3 types de modules jointifs ;
  - panneaux alternés en profondeur ;
  - lampes en face avant ou arrière.

## Pistes restantes
1. Pas vertical P=2 ou 3, avec panneaux de 3×2 portés par des modules entrelacés. Modèle plus gros, avec voisins j±4.
2. Moteur à 3 parties : budget de 36 blocs.
3. Accepter une herse en peigne non étanche : à valider avec l'utilisateur.

## Reprise
- Serveur : `outils/startsrv.sh` (attend `../srv/server.jar` 1.21.1, RCON 25575, mot de passe `test`, `tick freeze`).
- Solveurs : `pip install ortools`, puis `python3 solve2.py 6 5 600` (module isolé) ou les variantes 10 à 14.
