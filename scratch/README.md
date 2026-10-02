# Roblox Multiplayer (Tower Obby) — version française modifiée

Fichier : `Roblox_Multiplayer_FR.sb3` (à ouvrir dans Scratch 3 ou TurboWarp).

## Ce qui a été ajouté

### Au démarrage (drapeau vert)
Le jeu pose 4 questions avant de lancer la partie :

1. **Ton pseudo** — lettres, chiffres, `_ - .` (12 caractères max, mis en minuscules). Vide = `joueur` + numéro aléatoire.
2. **Clavier** — `1` = AZERTY (ZQSD), `2` = QWERTY (WASD). Les flèches marchent toujours.
3. **Couleur du perso** — nombre de 0 à 199 (Entrée = couleur normale). Les autres joueurs voient ta couleur.
4. **Code admin** — Entrée pour passer. Le bon code donne les pouvoirs admin et le badge `★` après ton pseudo (visible par tous).

### Code admin
Code par défaut : **`ANTOINE33`** (majuscules ou minuscules, peu importe).

Pour le changer : dans l'éditeur Scratch, scène (Stage) → variable `_ADMIN CODE` → clic droit → modifier la valeur, puis sauvegarder le projet.
Il existe aussi `_ADMIN SCRATCH` : si tu y mets ton nom de compte Scratch, tu es admin automatiquement quand tu joues connecté sur scratch.mit.edu.

### Touches pour tout le monde
| Touche | Action |
|---|---|
| Flèches / ZQSD / WASD | bouger |
| P | basculer AZERTY ↔ QWERTY en cours de jeu |
| R | réapparaître au checkpoint |
| R + X | recommencer la tour (avant : R + Q, déplacé car Q = gauche en AZERTY) |
| 1 2 3 | emotes |
| 4 à 9 | messages rapides vus par les autres joueurs (Salut, GG, Suis-moi, À l'aide, mdr, Bien joué) |
| T | infos serveur (pseudo, clavier, couleur, record, morts, joueurs actifs…) |
| L | classement |
| N | afficher / masquer les pseudos |
| V | couper / remettre la musique |
| C | aide à l'écran |

### Pouvoirs admin
| Touche | Pouvoir |
|---|---|
| F | voler (Espace = turbo) |
| G | animation « flotter » |
| I | invincible (les pièges ne tuent plus, R marche encore) |
| J | vitesse ×2 |
| H | super saut |
| U / Y | téléportation au checkpoint suivant / précédent (ne compte pas comme une mort) |
| B | mode disco (le fond change de couleur) |
| M | afficher / masquer le panneau admin |
| 0 | réinitialisation totale |

Dès qu'un pouvoir admin est utilisé, la variable `Triche` passe à 1 : le temps de la course n'est plus enregistré dans le classement (anti-triche).

### Autres ajouts
- Messages automatiques au-dessus du joueur : « Bienvenue ! », « ★ Admin connecté ★ », « Checkpoint ! », « Tour terminée ! 🏆 ».
- Les messages rapides et la couleur sont transmis via les variables cloud (encodage étendu, moins de 100 chiffres sur les 256 autorisés).
- Interface traduite : écran d'intro, connexion (Connexion… / Connecté ! / Complet / Déconnecté !), boutons Relancer / Temps, infos serveur et classement.
- Les touches ne réagissent plus pendant qu'on tape les réponses (plus de bascule accidentelle des pseudos ou du classement).

## Limites à connaître
- Le multijoueur n'existe que si le projet est **partagé sur scratch.mit.edu** avec un compte « Scratcher » (variables cloud). En local (Scratch Desktop, TurboWarp hors ligne) le jeu marche seul.
- Le code admin est visible par quiconque ouvre le projet dans l'éditeur : c'est une protection « cour de récré », pas une vraie sécurité.
- Les pseudos sont limités aux caractères de la table d'encodage (`a-z 0-9 + - . _ espace`) et passent en minuscules.

## Outils (`outils/`)
- `patch_scratch.py` : script qui a généré cette version à partir du `.sb3` d'origine (`python3 patch_scratch.py <dossier_sb3_dézippé> <dossier_sortie>`).
- `dump_scratch.py` : affiche les scripts d'un `project.json` en texte lisible.
- `test_vm_admin.js`, `test_vm_joueur.js` : tests automatiques (Node + `scratch-vm`) qui chargent le `.sb3`, répondent aux questions, pressent les touches et vérifient les variables, les bulles et l'encodage cloud. Les deux scénarios passent.
