# Optimisation Fabric 26.2 — pack + gestionnaire de mods

Pack d'optimisation complet pour **Minecraft 26.2 / Fabric Loader 0.19.5** (Java 25),
avec un **gestionnaire en français** pour installer, activer, désactiver et mettre à jour
les mods sans jamais casser une dépendance.

Contenu du dossier :

| Fichier | Rôle |
|---|---|
| **`Optimisation-26.2-tout-en-un.jar`** | **Le mod unique** : un seul fichier à mettre dans `mods/`, qui contient les 38 mods et l'écran d'activation dans le jeu. |
| `Optimisation-26.2-tout-en-un-essentiel.jar` | Même mod, sans les 5 optionnels (Litematica, MaLiLib, Spark, C2ME, Placeholder API) : 26 Mo au lieu de 38. Généré par `python assembler.py --sans-optionnels`, non versionné. |
| `mod-unique/` | Code source Java du mod unique (Gradle + Fabric Loom). |
| `assembler.py` | Fabrique le jar tout-en-un à partir du mod compilé, du catalogue et des jars des mods. |
| `Optimisation-Fabric-26.2.mrpack` | Le pack prêt à importer dans **Modrinth App** ou **Prism Launcher** (le plus simple). |
| `Lancer-Gestionnaire.bat` / `lancer-gestionnaire.sh` | Lance le gestionnaire (Windows / macOS-Linux). |
| `gestionnaire.py` | Le gestionnaire lui-même (Python 3, aucune dépendance). |
| `catalogue.json` | La liste des mods du pack, leurs catégories, descriptions et fichiers associés. |
| `verrou.json` | Versions exactes vérifiées (URL Modrinth + empreintes SHA-512). |
| `mods-perso/` | Les 7 mods fournis dans ton zip, intégrés tels quels. |

## 0. Le mod unique (le plus simple)

1. Installe Fabric Loader 0.19.5 pour Minecraft 26.2 ([fabricmc.net/use](https://fabricmc.net/use/installer/)).
2. Copie **`Optimisation-26.2-tout-en-un.jar`** dans ton dossier `.minecraft/mods/`. Rien d'autre : Fabric API,
   Sodium, Iris, Lithium, tes 7 mods… tout est à l'intérieur (mécanisme officiel Fabric « jar-in-jar »).
3. Lance le jeu. Dans Mod Menu, le pack apparaît comme **« Optimisation 26.2 »** avec tous les mods en dessous.
4. Pour activer / désactiver un mod : Mod Menu → Optimisation 26.2 → **Configurer**.
   - un onglet par famille (Rendu et FPS, Moteur, Réseau, Mods personnels, Outils optionnels…) ;
   - chaque mod a un interrupteur Activé / Désactivé et une infobulle (rôle, dépendances, qui en a besoin,
     fichiers associés) ;
   - **désactiver une bibliothèque** (ex. Sodium) désactive automatiquement ce qui en dépend (Iris, Sodium Extra…)
     après confirmation ; **activer un mod** réactive ses bibliothèques tout seul ;
   - les contraintes de version déclarées par les mods sont vérifiées par Fabric Loader lui-même ;
   - option **« Mettre de côté les fichiers des mods désactivés »** : schematics, shaderpacks, resourcepacks et
     `config/...` d'un mod désactivé sont déplacés dans `config/optimisation_pack/mis-de-cote/<mod>/`, puis remis
     en place automatiquement à la réactivation. Un dossier partagé par un mod encore actif n'est jamais touché.
   - Mod Menu, Cloth Config et Fabric API restent toujours actifs (ils font fonctionner l'écran).
5. Clique **Enregistrer** : les changements sont appliqués **à la fermeture du jeu** (le jar ne peut pas être
   modifié tant que Minecraft l'utilise), puis pris en compte au lancement suivant.

Comment ça marche : le jar contient les 38 mods dans `META-INF/jars/`. Sa liste `jars` (dans `fabric.mod.json`)
indique ceux que Fabric doit charger. Quand tu enregistres, le mod écrit `config/optimisation_pack/en-attente.txt`
et, à la fermeture du jeu, lance un petit programme Java (inclus dans le jar) qui attend la fin de Minecraft,
réécrit la liste `jars` du fichier, et déplace/restaure les fichiers associés. Journal :
`config/optimisation_pack/applicateur.log`. Les mods optionnels (Litematica, MaLiLib, Spark, C2ME) sont déjà dans
le jar : il suffit de les cocher.

Reconstruire le jar après modification : `cd mod-unique && gradle build` (JDK 25, Internet) puis
`python assembler.py` à la racine.

## 1. Installation rapide (via launcher ou gestionnaire Python)

**Option A — via un launcher qui gère les packs**

1. Installe [Modrinth App](https://modrinth.com/app) ou [Prism Launcher](https://prismlauncher.org/).
2. « Ajouter une instance » → « Importer depuis un fichier » → choisis `Optimisation-Fabric-26.2.mrpack`.
3. Lance l'instance : Fabric 0.19.5, Minecraft 26.2 et les 33 mods s'installent tout seuls.

**Option B — dans ton `.minecraft` habituel (launcher Mojang)**

1. Installe Fabric Loader pour 26.2 depuis [fabricmc.net/use](https://fabricmc.net/use/installer/).
2. Double-clique `Lancer-Gestionnaire.bat` (Windows) ou `lancer-gestionnaire.sh` (Mac/Linux).
   Il faut Python 3 ([python.org](https://www.python.org/downloads/), coche « Add to PATH »).
3. Vérifie le dossier Minecraft affiché en haut (détecté automatiquement, modifiable avec « Parcourir… »).
4. Clique **« Installer / mettre à jour le pack »** → « Non » pour les versions vérifiées du pack.
5. Lance Minecraft avec le profil Fabric.

## 2. Le gestionnaire

Interface graphique (fenêtre) :

- **Liste** de tous les mods : état (Actif / Désactivé / Non installé), version, catégorie,
  de quoi ils dépendent, qui a besoin d'eux, et leurs fichiers associés.
  Filtre par catégorie, recherche, affichage ou non des bibliothèques. Les mods dont une
  dépendance manque apparaissent sur fond rouge.
- **Activer / Désactiver** (ou double-clic) :
  - désactiver une bibliothèque (ex. Fabric API) propose de désactiver aussi tous les mods
    qui en ont besoin, en cascade ;
  - activer un mod réactive automatiquement ses bibliothèques, ou les télécharge si elles
    ne sont pas installées ;
  - les contraintes de version déclarées par les mods (`>=`, `<`, `~`…) sont respectées,
    y compris les incompatibilités (`breaks`).
- **Fichiers associés** (schematics, shaderpacks, resourcepacks, `config/...`) :
  - listés pour chaque mod (depuis le catalogue + détection automatique dans `config/`) ;
  - case **« Mettre de côté les fichiers associés »** : à la désactivation, ils sont déplacés
    dans `gestionnaire-mods/mis-de-cote/<mod>/` et **restaurés automatiquement** à la réactivation.
    Un fichier partagé par un autre mod actif (ex. `shaderpacks` utilisé par Iris *et* Resourcify)
    n'est jamais déplacé. Sans la case, rien n'est touché : tes schematics restent en place.
- **Installer la sélection** : installe les mods « Non installé » choisis (Litematica, Spark, C2ME…)
  avec leurs dépendances.
- **Vérifier** : dépendances manquantes, versions trop anciennes, incompatibilités, doublons.
- **Profils** : sauvegarde/charge un jeu de mods actifs (ex. « Survie », « Construction »,
  « Shaders off »), tout activer / tout désactiver.
- **Exporter .mrpack** : régénère le pack pour le partager.

Ligne de commande (même moteur, utile si pas de tkinter) :

```text
python gestionnaire.py liste [--tout]
python gestionnaire.py installer [--mise-a-jour] [--avec-optionnels] [id...]
python gestionnaire.py activer <id...> [--oui]
python gestionnaire.py desactiver <id...> [--oui] [--mettre-de-cote]
python gestionnaire.py fichiers <id>
python gestionnaire.py verifier
python gestionnaire.py profil liste|sauver|charger <nom>
python gestionnaire.py dossier [chemin]      # choisir le dossier .minecraft / instance
python gestionnaire.py mrpack [sortie]
python gestionnaire.py -m <dossier> ...      # dossier Minecraft ponctuel
```

Mécanisme : un mod désactivé est renommé `*.jar.disabled` (Fabric l'ignore). Rien n'est supprimé.
Un journal des actions est écrit dans `<minecraft>/gestionnaire-mods/journal.log`.

## 3. Mods du pack

### Bibliothèques (requises par d'autres mods)

| Mod | Version | Rôle |
|---|---|---|
| Fabric API | 0.161.0+26.2 | Bibliothèque centrale de Fabric, requise par la majorité des mods. |
| Fabric Language Kotlin | 1.14.1+kotlin.2.4.20 | Support Kotlin, requis par Resourcify et Particle Core. |
| Cloth Config | 26.2.155 | Écrans de configuration, requis par RenderScale, More Culling et FastQuit. |
| Fzzy Config | 0.7.7+26.2 | Bibliothèque de configuration requise par Particle Core. |

### Rendu et FPS

| Mod | Version | Rôle |
|---|---|---|
| Sodium | 0.9.2+mc26.2 | Moteur de rendu moderne : le plus gros gain de FPS du pack. |
| Iris Shaders | 1.11.4+mc26.2 | Shaders compatibles Sodium (dossier shaderpacks). |
| Sodium Extra | 0.9.4+mc26.2 | Options supplémentaires pour Sodium (particules, animations, brouillard...). |
| Reese's Sodium Options | 2.2.4+mc26.2 | Menu d'options Sodium plus lisible. |
| Entity Culling | 1.11.2 | Ne rend plus les entités cachées derrière les murs. |
| More Culling | 1.8.1 | Culling supplémentaire des feuilles, blocs et objets invisibles. |
| ImmediatelyFast | 1.16.5+26.2 | Accélère le rendu immédiat (interface, texte, entités). |
| BadOptimizations | 2.4.1 | Optimisations diverses du rendu et des calculs d'éclairage. |
| Particle Core | 0.3.3+26.2 | Optimise le rendu et le culling des particules. |
| Entity View Distance | 1.9.0+26.2 | Limite la distance d'affichage des entités côté client. |
| Dynamic FPS | 3.11.9 | Réduit la charge quand la fenêtre n'est pas au premier plan. |

### Moteur de jeu et chargement

| Mod | Version | Rôle |
|---|---|---|
| Lithium | 0.25.3+mc26.2 | Optimise la logique du jeu (IA, physique, redstone, ticks) sans changer le comportement. |
| FerriteCore | 9.0.0 | Réduit fortement la consommation de mémoire. |
| ScalableLux | 0.2.1+fabric.2b08348 | Moteur d'éclairage plus rapide (successeur de Starlight). |
| Alternate Current | 1.9.0 | Redstone jusqu'à 20x plus rapide à calculer. |
| Ksyxis | 1.4.5 | Accélère le chargement des mondes (pas de pré-chargement du spawn). |
| FastQuit | 3.1.5+mc26.2 | Retour au menu immédiat, la sauvegarde se termine en arrière-plan. |
| Debugify | 26.2.0.1 | Corrige des centaines de bugs vanilla référencés. |
| Clumps | 26.2.1 | Regroupe les orbes d'expérience pour éviter le lag. |
| C2ME (expérimental) *(optionnel, non installé par défaut)* | 0.4.2-alpha.0.56+26.2 | Génération et chargement de chunks multithread. Version alpha : à activer si stable chez toi. |

### Réseau et multijoueur

| Mod | Version | Rôle |
|---|---|---|
| Krypton | 0.3.1 | Optimise la pile réseau de Minecraft. |
| Fast IP Ping | 1.0.12 | Ping des serveurs beaucoup plus rapide dans la liste multijoueur. |

### Confort et interface

| Mod | Version | Rôle |
|---|---|---|
| Language Reload | 1.7.7+26.2 | Changement de langue instantané et chargement des ressources plus rapide. |

### Mods personnels (zip)

| Mod | Version | Rôle |
|---|---|---|
| Mod Menu | 20.0.3 | Liste des mods et accès à leurs configurations dans le jeu. |
| Mouse Tweaks | 2.31 | Gestion des stacks à la souris dans les inventaires. |
| RenderScale | 1.4.0-alpha.4 | Rend le jeu à une résolution différente de la fenêtre (gain de FPS ou netteté). |
| Resourceful Lib | 5.0.4 | Bibliothèque fournie dans ton zip (requise par les mods Team Resourceful). |
| Resourcify | 1.8.7 | Navigateur de packs de ressources et shaders dans le jeu. |
| Smooth Swapping | 0.9.10 | Animations fluides des objets dans l'inventaire. |
| YK FPS |  | Mod FPS fourni dans ton zip (non publié sur Modrinth). |

### Outils (optionnels)

| Mod | Version | Rôle |
|---|---|---|
| MaLiLib *(optionnel, non installé par défaut)* | 0.29.6 | Bibliothèque requise par Litematica. |
| Litematica *(optionnel, non installé par défaut)* | 0.28.8 | Schématiques (dossier schematics). Optionnel : à installer depuis le gestionnaire. |
| Spark *(optionnel, non installé par défaut)* | 1.10.187 | Profileur de performances pour trouver ce qui ralentit le jeu. Optionnel. |

Les 7 mods de ton zip sont installés tels quels depuis `mods-perso/` (même en mode .mrpack).

## 4. Mise à jour du pack

- Bouton « Installer / mettre à jour » → **Oui** : cherche les dernières versions Fabric 26.2 sur
  Modrinth, remplace les anciens jars (l'état actif/désactivé est conservé) et met `verrou.json` à jour.
- Pour les mods perso, remplace le jar dans `mods-perso/` et mets le nom dans `catalogue.json`.
- Pour ajouter un mod : une ligne dans `catalogue.json` (`id` = identifiant Fabric du mod,
  `modrinth` = son slug), puis « Installer la sélection ».
- Mainteneur : `python gestionnaire.py verrou` régénère `verrou.json` complet.

## 5. Points d'attention

- **Java 25** est requis par Minecraft 26.2 (le launcher officiel l'embarque).
- **C2ME** est en alpha pour 26.2 : non installé par défaut, à tester si tu veux du multithread chunks.
- **RenderScale** (ton zip) est une alpha ; il est marqué incompatible avec Resolution Control.
- **Alternate Current / Ksyxis / Clumps / Lithium** agissent côté serveur intégré (solo) ;
  sur un serveur distant ils n'ont d'effet que s'il les a aussi.
- Pas de ModernFix / MemoryLeakFix / Starlight : pas de version 26.2 (Starlight est intégré à ScalableLux).
