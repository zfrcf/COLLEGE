# Guide des modules — Royale 3D

Le projet Scratch est **généré** par Python : `python3 generer_projet.py` écrit `Royale 3D.sb3`.
Chaque fonctionnalité vit dans un module Python du package `royale/` qui crée ses sprites et
leurs scripts avec le DSL (`royale/dsl.py`). Le **contrat** (`royale/contrat.py`) fixe tout ce
qui est partagé. Ce guide explique comment écrire, brancher et tester un module.

## 1. Brancher un module

- Fichier `royale/mod_<nom>.py` exposant `construire(P)` (et optionnellement `ORDRE = 50`).
  `generer_projet.py` découvre automatiquement tous les `mod_*.py`.
- Dans `construire(P)` : créer un ou plusieurs sprites `Cible(P, "Nom")`, leur donner un costume
  (`P.costume(...)`), un calque (`contrat.CALQUES`), des variables **locales** (`cible.var`) et des
  scripts (`cible.script(hat, corps)`) / blocs personnalisés (`cible.proc(nom, args, corps)`).
- Variables globales privées supplémentaires : `P.stage.var("menu_xxx", 0)` avec le préfixe de
  votre module. Jamais de locale portant le nom d'une globale (le DSL refuse).
- Texte à l'écran : `from royale import texte ; texte.installer(cible)` puis
  `appel("ecrire", texte, x, y, taille, couleur, alignement)` — voir l'en-tête de `royale/texte.py`.
  Les textes visibles passent par `contrat.tr("Français", "English")` (reporter selon `param_langue`).
- Icônes : `royale/svg_ui.py` (voir ses docstrings) et `royale/svg.py`.
- Sons : `setv("son_pan", p), setv("son_volume", v), diffuser("son <nom>")` (noms dans `contrat.SONS`).

## 2. Règles d'exécution Scratch à connaître

- Ordre d'exécution par image = calques décroissants (`CALQUES`). Le stylo est **sous** tous les sprites.
- Un bloc personnalisé n'est appelable que depuis son sprite : on communique entre sprites par
  variables globales et diffusions (`diffuser("evt ...")`, détails dans `evt_valeur`, `evt_cible`, …).
- Deux diffusions identiques dans la même image se confondent : utiliser une liste-file pour les
  événements à ne pas perdre (ex. `DegatsRecus`).
- `=` compare numériquement les chaînes de chiffres : utiliser `eq_txt` pour les paquets/codes.
- Pas de `Shift`/`Échap` ; touches configurables via `contrat.touche_config("nom")`.
- Max 300 clones. Tamponner (`tampon()`) marche même caché.
- `ecran` décide qui dessine le fond : écrans 3D → Moteur3D ; connexion/salon/matchmaking/chargement →
  Menus ; bus/parachute/carte → Partie ; pause/fin → Moteur3D rend le 3D puis Menus dessine par-dessus.
  Le sprite propriétaire du fond fait `effacer()` en début d'image, les autres ne l'appellent jamais.
- Quand `superposition` ≠ "" (chat, roues, signalement…), les sprites 3D (Ennemi, Coffre, Spray…), l'arme et
  le viseur se cachent pour ne pas passer au-dessus des panneaux au stylo ; Joueur ignore alors les clics.
- En écran « cinema », Joueur n'applique pas la gravité : `hauteur` peut être réglée librement (horizon = −hauteur).
- Ne redessiner un menu que quand quelque chose change (survol, onglet, données) : un tampon par glyphe.

## 3. Tester

```bash
python3 generer_projet.py                          # construit le .sb3 (+ outils/contrat.json)
cd outils && node test_vm.js                       # tous les scénarios outils/scenarios/*.js
node test_vm.js ../"Royale 3D.sb3" scenarios/10_joueur_reseau.js   # un seul scénario
node capture.js captures_scripts/jeu_base.js       # rendu réel Chromium → outils/captures/*.png
```

Un scénario exporte `async (T, verifier) => { ... }` ; `T` est décrit dans `outils/vm_lib.js`
(`drapeau`, `pas`, `touche`, `appui`, `souris`, `clic`, `pseudo`, `diffuser`, `g`, `set`, `L`, `l`,
`visible`, `costume`, `clones`). `chargeurPaquets()` fabrique des paquets réseau d'adversaires simulés.
Un script de capture exporte `async (A) => { ... }` avec `A.evaluer((vm, V, L, arg) => ...)`,
`A.touche`, `A.souris`, `A.clic`, `A.attendre`, `A.capture("nom")`.

Dans scratch-vm sans rendu, une « image » (`T.pas(1)`) exécute plusieurs tours de boucle ; les
durées réelles (chrono) restent fiables, pas le nombre d'itérations.

**Un écran non capturé et non regardé n'est pas livré.** Chaque module doit fournir au moins un
scénario `outils/scenarios/NN_<module>.js` et un script `outils/captures_scripts/<module>.js`.

## 4. Conventions

- Tout en français (code, commentaires, textes, noms de sprites/variables). Textes joueur via `tr()`.
- Variables locales courtes autorisées (`k`, `i`, `x`…) ; globales privées préfixées.
- Pas de modification de `dsl.py`, `contrat.py`, ni des modules des autres : signaler le besoin.
