# Pack de ressources : Sans feu + Vision dans la lave + Netherite bleue

Pack de textures pour **Minecraft 26.2** (Java, compatible Fabric, aucun mod requis). Format de pack : 88.

## Installation
1. Télécharge `SansFeu-VisionLave-NetheriteBleue.zip`.
2. Dans Minecraft : **Options → Packs de ressources → Ouvrir le dossier des packs**.
3. Colle le fichier `.zip` dans ce dossier.
4. Active le pack dans la liste, puis **Terminé**.

## Ce que fait le pack
- **Plus de flammes à l'écran** quand tu brûles : la texture `fire_1` est rendue transparente
  (c'est celle que le jeu utilise pour l'overlay de feu). Les blocs de feu restent visibles
  car leurs modèles sont redirigés sur `fire_0`.
- **Vision dans la lave** : le shader de brouillard (`fog.glsl`) désactive le brouillard
  quand il détecte la couleur orange de la lave. Le reste du brouillard (eau, distance, cécité…) est intact.
- **Netherite bleue** : lingot, débris, bloc, épée, pioche, hache, pelle, houe, lance,
  casque, plastron, jambières, bottes, armure de cheval, armure de nautile, armures portées
  (joueur, bébé, cheval, nautile) et palettes de couleur des ornements en netherite.

## Remarque
Ce pack modifie un shader vanilla. Si tu utilises un mod de shaders (Iris, etc.), la
vision dans la lave peut ne pas fonctionner tant que le shader est actif.
