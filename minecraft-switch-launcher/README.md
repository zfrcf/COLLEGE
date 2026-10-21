# MCSL – Launcher de serveur Minecraft local pour Nintendo Switch

Un petit launcher (Python, sans dépendance) qui monte **en un clic** un serveur
Minecraft **Java (Paper)** sur ton PC, avec le pont **Geyser + Floodgate** pour
que la **Switch (Bedrock)** puisse s'y connecter, et qui gère les plugins
(**WorldEdit**, etc.) depuis Modrinth.

```
PC : Minecraft Java ──TCP 25565──▶ Paper 26.x + WorldEdit + Geyser/Floodgate
Switch : Minecraft Bedrock ──UDP/TCP 19132 (+UDP 19133)──▶ Geyser ──▶ même monde
```

> Pourquoi Java et pas Bedrock ? Les « mods » type WorldEdit n'existent que
> côté Java. Geyser traduit le protocole Bedrock ↔ Java : la Switch rejoint
> donc un monde Java sans compte Java (Floodgate), et profite des plugins.

## Démarrage rapide (Ubuntu)

```bash
sudo apt install -y python3          # déjà présent sur Ubuntu en général
cd minecraft-switch-launcher
./lancer.sh                          # menu interactif
```

1. Menu → **1. Installer** : télécharge Java 25 (dans `runtime/`, sans toucher
   au système), Paper, Geyser, Floodgate, WorldEdit, fait un premier démarrage
   et configure tout.
2. Menu → **5. Ouvrir le pare-feu** : si `ufw` est actif, ajoute les règles
   (`sudo` demandé). S'il est inactif ou absent, rien à faire.
3. Menu → **2. Jouer** : démarre le serveur et ouvre Minecraft Java
   (détecte le `.deb` officiel, l'app Modrinth (`.deb`, Flatpak, AppImage),
   Flatpak `com.mojang.Minecraft`, Prism, MultiMC).
   Les instructions pour la Switch s'affichent dans la console.

Ligne de commande : `./lancer.sh installer | jouer | plugins | switch | parametres`

Windows : installer Python 3.10+ (cocher *Add python.exe to PATH*) puis
double-cliquer sur `lancer.bat` (en administrateur pour le pare-feu).
macOS : `./lancer.sh`.

## Se connecter depuis la Switch

La Switch et le PC doivent être sur le **même réseau** (même box). Deux méthodes :

| Méthode | Quand | Comment |
|---|---|---|
| **Amis → Jeux en réseau local** | le plus simple | Jouer › Amis : le serveur apparaît (port 19132). |
| **BedrockConnect** | si la liste reste vide | DNS manuel sur la Switch : `104.238.130.180` / `8.8.8.8`, puis Jouer › Serveurs › n'importe quel serveur en vedette › *Connect to a server* : IP du PC, port 19132. |

L'IP du PC et le détail sont affichés par le menu **4** (`python launcher.py switch`).
Pour retrouver les serveurs officiels, remettre le DNS en *Automatique*.

### NetherNet (Bedrock 26.60+, à partir du 27 octobre 2026)

Bedrock abandonne l'ancien protocole RakNet. Le launcher configure Geyser en
`transport: both` : **RakNet** (UDP 19132) pour la découverte LAN et les anciens
clients, **NetherNet** (signalisation TCP 19132 + jeu UDP 19133) pour les
clients à jour. À la première connexion par IP, Minecraft demande de faire
confiance au serveur : accepter.

## Plugins

Menu **3** ou `config.json` → `"plugins": ["worldedit"]`. Chaque entrée est le
*slug* d'un projet [Modrinth](https://modrinth.com/plugins) ; le launcher prend
la dernière version compatible avec ta version de Minecraft. Suggestions :

| Slug | Rôle |
|---|---|
| `worldedit` | édition de monde (`//wand`, `//set`, `//copy`…) |
| `fastasyncworldedit` | WorldEdit rapide (remplace `worldedit`) |
| `viaversion` | clients Java d'autres versions |
| `luckperms` | permissions |
| `essentialsx` | `/home`, `/tp`, kits… |
| `chunky` | pré-génération du monde |

Pour utiliser WorldEdit depuis la Switch, donne-toi l'OP dans la console du
serveur : `op TonPseudo` (joueur Java) ou `op .TonPseudoSwitch` (joueur
Bedrock : Floodgate préfixe les pseudos d'un point). Les commandes `//…` se
tapent dans le chat.

## Configuration (`config.json`)

| Clé | Défaut | Rôle |
|---|---|---|
| `version_minecraft` | `latest` | version Paper (`latest`, `26.3`, `1.21.11`…) |
| `ram_mo` | `3072` | RAM du serveur |
| `port_java` / `port_bedrock` / `port_nethernet` | `25565` / `19132` / `19133` | ports |
| `motd` | `Serveur local Switch` | nom affiché |
| `mode_jeu` / `difficulte` | `survival` / `normal` | réglages du monde |
| `plugins` | `["worldedit"]` | plugins Modrinth |
| `accepter_toutes_versions_java` | `true` | ViaVersion + ViaBackwards (clients Java d'autres versions) |
| `java` | *(auto)* | chemin vers un `java` précis |
| `launcher_minecraft` | *(auto)* | chemin du launcher Minecraft Java |
| `lancer_minecraft_avec_serveur` | `true` | ouvre Minecraft Java avec « Jouer » |

Java : Minecraft 26.x exige **Java 25**, 1.21.x **Java 21**. Si le PC n'a pas la
bonne version, un JRE Temurin est téléchargé dans `runtime/` (rien n'est
installé dans Windows).

## Arborescence

```
minecraft-switch-launcher/
├── launcher.py        point d'entrée
├── lancer.bat / .sh   double-clic Windows / script Linux-macOS
├── mcsl/
│   ├── config.py          config.json
│   ├── telechargement.py  API Paper, Geyser, Modrinth, Adoptium
│   ├── java.py            détection / installation de Java
│   ├── plugins.py         Geyser, Floodgate, plugins Modrinth
│   ├── serveur.py         eula, server.properties, config Geyser, démarrage/arrêt
│   ├── reseau.py          IP locale, ports, instructions Switch, pare-feu
│   └── menu.py            menu en français
├── serveur/           (généré) le serveur et le monde
└── runtime/           (généré) Java local si nécessaire
```

## Dépannage

- **La Switch ne voit rien** : même réseau ? pare-feu ouvert (menu 5) ?
  serveur démarré (`Done (…s)!` dans la console) ? Essayer BedrockConnect.
- **« You are not whitelisted »** : relancer le launcher (il remet
  `white-list=false` dans `server.properties`), ou taper `whitelist off`
  dans la console du serveur.
- **« disconnectionScreen.resourcePack »** : la Switch a refusé le pack de
  ressources Geyser → se reconnecter et l'accepter.
- **« Port déjà utilisé »** : un Minecraft Bedrock ouvert sur le PC occupe
  déjà 19132 → le fermer, ou changer `port_bedrock` (la Switch devra alors
  passer par BedrockConnect avec ce port).
- **Minecraft Java refuse de se connecter (« Outdated client / server »)** :
  par défaut le launcher installe ViaVersion + ViaBackwards
  (`accepter_toutes_versions_java`), donc un profil Modrinth en 1.21.x peut
  rejoindre un serveur 26.3 (relancer l'installation, menu 1, si le serveur
  a été installé avant cette option). Sinon, créer un profil dans la version
  du serveur (affichée dans l'en-tête du menu).
- **« Failed to verify username » / « Invalid session »** : le compte du
  launcher n'est pas authentifié chez Microsoft (compte hors-ligne). Se
  reconnecter avec un compte Microsoft possédant Minecraft Java.
- **Erreur au démarrage** : lire `serveur/logs/latest.log`.
- **Changer de version** : modifier `version_minecraft` puis relancer
  l'installation (menu 1). Sauvegarder `serveur/world*` avant.
