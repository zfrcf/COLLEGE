# Optimisation 1.21.11 — tout-en-un essentiel

Conversion du pack « Optimisation 26.2 tout-en-un essentiel » vers Minecraft **1.21.11** (Fabric, Java 21).

- `dist/Optimisation-1.21.11-tout-en-un-essentiel.jar` : le jar final à déposer dans `mods/`.
- `projet/` : projet Gradle (Loom 1.17.21, mappings Mojang) avec le code du gestionnaire (`pack/`) et du mod personnel YK FPS (`ykfps/`), recompilés pour 1.21.11.
- `pack-manifest.json` : manifeste des 33 mods embarqués (versions 1.21.11).
- `outils/generer_manifeste.py` : régénère le manifeste depuis les fabric.mod.json des jars.
- `outils/assembler.py` : assemble le jar final (jar du pack + mods imbriqués + manifeste).

## Reconstruire

```bash
cd projet && ./gradlew build
python3 ../outils/generer_manifeste.py <manifeste 26.2> <dossier mods 1.21.11> ../pack-manifest.json
python3 ../outils/assembler.py pack/build/libs/optimisation-pack-1.0.0.jar <dossier mods 1.21.11> ../pack-manifest.json ../dist/Optimisation-1.21.11-tout-en-un-essentiel.jar
```

## Changements par rapport à la 26.2

- Prérequis : Fabric Loader ≥ 0.19.2, Java ≥ 21 (au lieu de Java 25).
- Sodium 0.8.14 (stable, imposé par Reese's Sodium Options qui exige exactement cette version).
- YK FPS porté : `Hud.extractRenderState` → `Gui.render`, `Minecraft.renderFrame` → `Minecraft.runTick`, présentation via `Window.updateDisplay`, limite via `RenderSystem.limitDisplayFPS`.
- ScalableLux : seule une version alpha (0.3.0-alpha.0.3) cible la 1.21.11. Smooth Swapping : seule une bêta (0.9.8) existe.
