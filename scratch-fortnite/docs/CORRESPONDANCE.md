# Correspondance des fonctionnalités demandées

Légende : ✅ implémenté · 🟡 simulé / adapté aux limites de Scratch · ❌ impossible sur Scratch (expliqué).
Les numéros reprennent la liste d'origine.

## Écrans et navigation

| # | Élément | État | Où / comment |
|---|---|---|---|
| 0 | Écran de connexion | ✅ | `mod_menus` : pseudo Scratch détecté, emplacement réseau, code de sauvegarde, langue, code créateur |
| 1 | Salon (lobby) | ✅ | `mod_menus` : onglets, personnage, bouton Jouer, mode, remplissage, confidentialité, partie en cours |
| 2 | Écran d'accueil / Découvrir | ✅ | onglet « accueil » : fil d'actualités, saison, événement du jour |
| 3 | Onglet Passe de combat | ✅ | 100 paliers, étoiles, récompenses, styles (`mod_systemes` + `mod_menus`) |
| 4 | Boutique d'objets | ✅ | 6 objets du jour, jetons gagnés en jeu (aucun achat réel) |
| 5 | Casier (locker) | ✅ | tenues, pioches, planeurs, sprays, émotes, bannières, styles |
| 6 | Onglet Quêtes | ✅ | quotidiennes, hebdomadaires, histoire ; réclamer, partager |
| 7 | Onglet Carrière / Statistiques | ✅ | statistiques de session et de compte, succès, classements |
| 8 | Paramètres | ✅ | Jeu, Commandes, Vidéo, Audio, Accessibilité, Compte |
| 9 | Menu pause | ✅ | touche P ; la partie continue (comme Fortnite) |
| 10 | Liste d'amis | 🟡 | joueurs connectés au même projet (Scratch n'expose pas la liste d'amis d'un compte) |
| 11 | Barre latérale sociale | ✅ | `mod_social` dans le salon |
| 12 | Fil d'actualités | ✅ | cartes de l'onglet accueil |
| 13 | Sélecteur de mode de jeu | ✅ | Solo, Duo, Trio, Sections, Rumble, Arène + événement limité |
| 14 | Bouton Jouer | ✅ | |
| 15 | Compte à rebours de matchmaking | ✅ | écran « matchmaking » |
| 16 | Écran de chargement | ✅ | barre, astuce, miniature de carte |
| 17 | Écran de fin de partie | ✅ | récapitulatif, XP, boutons |
| 18 | Écran de victoire | ✅ | variante dorée « VICTOIRE ROYALE » |
| 19 | Récapitulatif de partie | ✅ | éliminations, dégâts, survie, placement, lignes d'XP |
| 20 | Bouton Rejouer | ✅ | renvoie en matchmaking pour la manche suivante |
| 21 | Signaler un joueur | 🟡 | signalement local : le joueur est masqué pour toi (pas de modération serveur sur Scratch) |

## Multijoueur et social

| # | Élément | État | Où / comment |
|---|---|---|---|
| 23-26 | Modes Solo / Duo / Trio / Sections | ✅ | équipes par emplacement, pas de réapparition, à terre / réanimation / redéploiement |
| 27 | Groupe / équipe | 🟡 | équipes automatiques ; « groupe » = joueurs partageant ton code de salon |
| 28 | Invitation d'amis | 🟡 | Scratch n'a pas de messagerie : on partage le lien du projet + le code de salon |
| 29 | Code créateur | 🟡 | cosmétique (« Tu soutiens X »), aucun paiement |
| 30 | Chat vocal | ❌ | pas de micro ni d'audio réseau dans Scratch |
| 31 | Chat textuel | 🟡 | messages prédéfinis (chat rapide) : les variables cloud ne transportent que des nombres et les règles Scratch interdisent le chat libre |
| 32 | Remplissage automatique (fill) | ✅ | interrupteur dans le salon |
| 33 | Crossplay | 🟡 | de fait : tout navigateur avec compte Scratch ; pas de consoles |
| 34 | Nom d'affichage Epic | 🟡 | = pseudo Scratch (8 lettres transmises) |
| 35 | Niveau de compte | ✅ | XP → niveau, affiché partout, transmis en réseau |
| 36 | Système de ping / marquage | ✅ | touche V, carte, visible en 3D, minicarte et boussole |
| 37 | Pouce en l'air / émotes rapides | ✅ | chat rapide 👍 + roue d'émotes |
| 38 | Spectateur après la mort | ✅ | modes sans réapparition |
| 39 | Mode spectateur | ✅ | « Regarder » depuis le salon |
| 40 | Replay / mode cinéma | 🟡 | caméra libre (pas d'enregistrement : Scratch n'a pas de stockage) |
| 41 | Partage de mission | ✅ | bouton Partager dans Quêtes → message rapide |
| 42 | Carte à points de rassemblement | ✅ | clic sur la carte plein écran |

## Interface en jeu (HUD) — `mod_hud`, `moteur3d`, `overlays`

| # | Élément | État | # | Élément | État |
|---|---|---|---|---|---|
| 43 | Barre de vie | ✅ | 61 | Chiffres de dégâts | ✅ |
| 44 | Barre de bouclier | ✅ | 62 | Journal d'éliminations | ✅ |
| 45 | Barre de bouclier supérieur | ✅ (surbouclier régénérant) | 63 | Notifications de butin | ✅ |
| 46 | Barre d'endurance | ✅ (sprint X) | 64 | Bouton de construction rapide | ✅ (B / mode construction) |
| 47 | Mini-carte | ✅ | 65 | Roue d'émotes | ✅ |
| 48 | Carte plein écran | ✅ (M) | 66 | Roue des pioches / sprays | ✅ |
| 49 | Boussole | ✅ | 67 | Icône de bus de combat | ✅ |
| 50 | Compteur de joueurs restants | ✅ | 68 | Indicateur de chute / planeur | ✅ |
| 51 | Compteur d'éliminations | ✅ | 69 | Indicateur d'altitude | ✅ |
| 52 | Compteur de munitions | ✅ | 70 | Barre d'ouverture de coffre | ✅ |
| 53 | Barre d'inventaire (5 emplacements) | ✅ | 71 | Barre de réanimation | ✅ |
| 54 | Compteur de matériaux | ✅ | 72 | Barre de soin / consommable | ✅ |
| 55 | Compteur bois / pierre / métal | ✅ | 73 | Barre de carte de redéploiement | ✅ |
| 56 | Minuteur de tempête | ✅ | 74 | Icônes des coéquipiers | ✅ |
| 57 | Indicateur de zone de tempête | ✅ | 75 | Barre de vie des coéquipiers | ✅ |
| 58 | Flèche de dégâts | ✅ | 76 | État « à terre » | ✅ |
| 59 | Indicateur de bruit | ✅ (tirs, pas) | 77 | Chronomètre de redéploiement | ✅ |
| 60 | Réticule / viseur | ✅ | 78 | Compteur de temps de partie | ✅ |

## Systèmes de jeu — `mod_systemes`, `mod_partie`

| # | Élément | État | Remarque |
|---|---|---|---|
| 79 | Matchmaking basé sur le niveau | 🟡 | un seul serveur cloud : affichage du niveau moyen du salon, pas de tri réel |
| 81-82 | Points d'arène (hype), classement / divisions | ✅ | mode Arène, 7 divisions |
| 83-86 | Niveaux du passe, étoiles, XP, bonus d'XP de session | ✅ | |
| 87-89 | Quêtes quotidiennes / hebdomadaires / histoire | ✅ | graines par jour / semaine |
| 90-91 | Récompenses de palier et de style | ✅ | |
| 92 | Événements limités (LTM) | ✅ | Pompes, Snipers, Tempête éclair, Munitions infinies, Gravité faible |
| 93 | Saisons et chapitres | ✅ | calculés à partir de la date |
| 96 | Succès / badges | ✅ | 20 succès |
| 97 | Classement de fin de saison | 🟡 | record de tous les temps (☁ Record, 3 entrées) + classement des connectés ; pas de base de données |
| 98 | Reconnexion en cours de partie | ✅ | emplacement retrouvé par le pseudo, état restauré |
| 99 | Signalement / sanctions | 🟡 | masquage local |
| — | Persistance du compte | 🟡 | code de sauvegarde à copier (Scratch n'a pas de stockage par joueur) |

## Paramètres — `mod_menus`

| # | Élément | État | Remarque |
|---|---|---|---|
| 103 | Sensibilité souris / manette | 🟡 | souris oui ; pas de manette dans Scratch |
| 104 | Mode construction / combat | ✅ | |
| 105 | Visée assistée | ✅ | tolérance élargie |
| 106 | Construction turbo | ✅ | |
| 107 | Édition rapide | ✅ | retrait instantané ou maintenu |
| 108 | Configuration des touches | ✅ | 19 actions, presets AZERTY/QWERTY |
| 109 | Qualité graphique | ✅ | 40 / 80 / 120 colonnes |
| 110 | FPS | ✅ | affichage ; le plafond reste 30 images/s (Scratch) |
| 111 | Mode performance | ✅ | |
| 112 | Effets visuels des dégâts | ✅ | |
| 113 | Volume musique / effets / voix | ✅ | sons synthétisés ; « voix » = annonces |
| 114 | Sous-titres | ✅ | |
| 115 | Daltonisme | ✅ | 3 filtres |
| 116 | Taille du HUD | ✅ | |
| 117 | Confidentialité de la partie | ✅ | code de salon ; même serveur cloud |
| 118 | Langue | ✅ | FR / EN |
| 119 | Région de serveur | ❌ | un seul serveur cloud Scratch : liste indicative seulement |
| 120 | Affichage du ping / latence | 🟡 | latence estimée d'après l'arrivée des paquets |
| 121 | Informations réseau | ✅ | |

## Éléments d'une partie — `mod_partie`

| # | Élément | État |
|---|---|---|
| 122 | Phase de pré-partie (île d'attente) | ✅ |
| 123 | Bus de combat et trajectoire | ✅ |
| 124 | Parachutage | ✅ |
| 125 | Zone de sécurité / cercle | ✅ |
| 126 | Phases de tempête (dégâts croissants) | ✅ (5 phases) |
| 127 | Fin de partie (endgame) | ✅ |
| 128 | Dernière zone en mouvement | ✅ |
