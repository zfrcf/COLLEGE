# Porte géante 67 × 67 à machines volantes (Minecraft Java 1.21.1)

## Ce qui a été vérifié
La porte a été testée tick par tick sur un vrai serveur 1.21.1, en taille réelle :
- ouverture 67 × 67 libre sur toute la profondeur une fois ouverte ;
- 3 cycles ouverture/fermeture consécutifs, sans aucun bloc déplacé de travers.

| Fichier | Méthode | Statut |
|---|---|---|
| `porte_67x67_datapack.zip` | Datapack vanilla (aucun mod) | ✅ testé, fonctionne |
| `porte_67x67.schem` | WorldEdit, **avec effets de bord coupés** (voir plus bas) | ✅ testé, fonctionne |
| `porte_67x67.schem` | WorldEdit, réglages par défaut | ❌ testé, casse la porte |
| `porte_67x67.litematic` | Litematica | ⚠️ non testable ici (mod client) |
| `.nbt` (bloc de structure / `/place`) | Vanilla | ❌ testé, casse la porte : fichier retiré |

**Pourquoi certains collages cassent la porte.** Un collage qui envoie des mises à jour de voisinage déclenche les 1 744 observateurs en même temps, et les moteurs partent n'importe comment. Il faut donc :
- soit poser les blocs dans le bon ordre (c'est ce que fait le datapack) ;
- soit coller sans aucune mise à jour.

## Installation

### Option A : datapack (recommandé, vanilla)
1. Copier `porte_67x67_datapack.zip` dans `saves/<monde>/datapacks/`, puis taper `/reload`.
2. Se placer **au coin bas-gauche de l'ouverture, côté façade**, les pieds au niveau du sol.
3. Taper `/function porte:construire`. La porte se construit, puis se finalise 15 s plus tard (message vert).
4. Les chunks doivent être chargés : rester sur place pendant la construction.

### Option B : WorldEdit
1. Copier `porte_67x67.schem` dans `config/worldedit/schematics/`.
2. Taper `//schem load porte_67x67`.
3. Couper les effets de bord : `//perf neighbors off` puis `//perf update off`. **Cette étape est indispensable.**
4. Se placer au coin bas-gauche de l'ouverture (côté façade), puis taper `//paste`.
5. Remettre les effets de bord : `//perf neighbors on` et `//perf update on`.

## Orientation et encombrement
- La porte est générée face au **nord** : la façade est côté −Z et l'ouverture s'étend vers l'est (+X).
  - Avec WorldEdit, `//rotate` permet de la tourner avant de coller (rotation non testée).
- Encombrement total : 78 de large × 153 de haut × 22 de profondeur.
  - Le volume comprend 6 blocs sous le sol (mécanisme) et un logement de 80 blocs au-dessus de l'ouverture : la porte monte comme une herse.
- Commandes : deux leviers devant la façade, à droite de l'ouverture vue de face.
  - Levier le plus proche de l'ouverture = **ouvrir** ; l'autre = **fermer**.
  - Durée d'un mouvement complet : environ 50 s à 1 min (mesuré : ouverture en 49 s).

## Limite importante : porte opaque, mais pas étanche
Les colonnes sont réparties sur 3 nappes en profondeur, en peigne. Vue de face, la porte est entièrement bouchée. En revanche, un joueur peut se faufiler en diagonale entre les nappes. C'est donc une herse visuelle, pas un mur infranchissable. Une version étanche est toujours à l'étude (voir `../NOTES.md`).

## Matériaux (survie)
| Bloc | Quantité |
|---|---|
| Briques de pierre (coque) | 23 645 |
| Blocs de slime | 6 432 |
| Blocs de miel | 6 432 |
| Obsidienne | 5 969 |
| Observateurs | 1 744 |
| Pistons collants | 1 608 |
| Lampes redstone | 1 608 |
| Blocs de redstone | 1 608 |
| Poudre de redstone | 436 |
| Répéteurs | 310 |
| Leviers | 2 |

En survie, avec Litematica en pose manuelle : poser **les observateurs en dernier**, puis les répéteurs d'alimentation (délai 4, au pied de la ligne d'alimentation). Sinon, la porte se déclenche pendant la construction.
