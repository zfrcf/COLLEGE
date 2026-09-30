# Écran Sans Feu — mod Fabric pour Minecraft 26.2

Mod **client uniquement** qui retire les effets visuels qui bouchent la vue :

| Effet retiré | Option dans la config | Par défaut |
|---|---|---|
| Flammes en bas de l'écran quand on brûle | `masquerFeuEcran` | activé |
| Brouillard orange quand la tête est dans la lave (on voit dans la lave) | `voirDansLaLave` | activé |
| Brouillard bleuté dans la neige poudreuse | `voirDansLaPoudreuse` | activé |
| Givre bleu sur les bords de l'écran quand on gèle | `masquerGivreEcran` | activé |
| Overlay bleu sous l'eau | `masquerOverlayEau` | désactivé |
| Texture de bloc quand la tête est dans un bloc | `masquerOverlayBloc` | désactivé |

Le mod ne change rien côté serveur : vous brûlez et prenez des dégâts normalement, seul l'affichage est nettoyé.

## Installation

1. Installer [Fabric Loader](https://fabricmc.net/use/) pour Minecraft **26.2** (version 0.19.5 ou plus récente).
2. Placer dans le dossier `mods/` :
   - `ecransansfeu-1.0.0.jar` (ce mod),
   - [Fabric API](https://modrinth.com/mod/fabric-api) pour 26.2.
3. Lancer le jeu avec le profil Fabric.

## Touches (menu Options → Commandes → catégorie « Écran Sans Feu »)

- **F8** : activer / désactiver tout le mod.
- *Non assignée* : basculer uniquement le feu à l'écran.
- *Non assignée* : basculer uniquement la vision dans la lave.

Un message s'affiche au-dessus de la barre d'inventaire à chaque changement.

## Configuration

Le fichier `config/ecransansfeu.json` est créé au premier lancement :

```json
{
  "modActive": true,
  "masquerFeuEcran": true,
  "voirDansLaLave": true,
  "voirDansLaPoudreuse": true,
  "masquerGivreEcran": true,
  "masquerOverlayEau": false,
  "masquerOverlayBloc": false
}
```

Les changements faits avec les touches sont sauvegardés automatiquement.

## Compiler soi-même

Prérequis : JDK 25.

```bash
./gradlew build
```

Le jar se trouve ensuite dans `build/libs/ecransansfeu-1.0.0.jar`.

## Comment ça marche

Minecraft 26.2 n'est plus obfusqué, le mod utilise donc directement les noms officiels via des mixins :

- `ScreenEffectRenderer.submitFire` / `submitWater` / `submitBlockSprite` : annulés selon la config.
- `LavaFogEnvironment.setupFog` et `PowderedSnowFogEnvironment.setupFog` : le brouillard est repoussé à la distance de rendu (mêmes valeurs que le mode spectateur).
- `Hud.extractTextureOverlay` : annulé uniquement pour la texture de givre.
