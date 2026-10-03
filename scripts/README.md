# Installer Claude sur Ubuntu sans sudo

Deux scripts, tout est installé dans votre dossier personnel. Aucun droit administrateur.

| Vous voulez… | Script |
|---|---|
| **Une interface graphique** (fenêtre : Chat + Claude Code, diff visuel, terminal intégré) | `scripts/install-claude-desktop.sh` |
| Claude Code en ligne de commande dans le terminal | `scripts/install-claude-code.sh` |

---

## 1. Claude Desktop : l'interface graphique

```bash
bash scripts/install-claude-desktop.sh
```

Puis double-cliquez sur l'icône **« Claude »** posée sur votre bureau, ouvrez-la depuis le menu des applications, ou tapez `claude-desktop` dans un terminal.
Connexion avec votre compte claude.ai (Pro, Max, Team) ou le SSO de votre organisation.

### Ce que fait le script

1. Détecte l'architecture (amd64 / arm64) et télécharge le dernier paquet `.deb` officiel d'Anthropic.
2. L'extrait dans `~/.local/opt/claude-desktop` au lieu de l'installer avec apt (donc sans root).
3. Crée le lanceur `~/.local/bin/claude-desktop`, l'entrée de menu et les icônes dans `~/.local/share`.
4. Pose une icône « Claude » sur le bureau (dossier `~/Bureau` ou `~/Desktop`) et la marque comme fiable pour GNOME.
5. Enregistre le gestionnaire des liens `claude://`.
6. Vérifie les bibliothèques système et liste celles qui manqueraient.

### Options

| Commande | Effet |
|---|---|
| `bash install-claude-desktop.sh` | Installe, ou met à jour si une nouvelle version existe, et pose l'icône sur le bureau |
| `bash install-claude-desktop.sh --bureau` | Recrée seulement l'icône sur le bureau |
| `bash install-claude-desktop.sh --sans-bureau` | Installe sans toucher au bureau |
| `bash install-claude-desktop.sh --uninstall` | Supprime l'application (vos données dans `~/.config/Claude` sont gardées) |
| `bash install-claude-desktop.sh --help` | Aide |

### Bon à savoir

- **Prérequis** : Ubuntu 22.04+ ou Debian 12+, session graphique, environ 600 Mo d'espace disque.
- **Ubuntu 24.04 et plus** : sans root, le bac à sable Chromium ne peut pas s'activer. Le lanceur ajoute automatiquement `--no-sandbox` dans ce cas. C'est le même compromis que pour toute application Electron lancée depuis un dossier utilisateur.
- **Icône barrée sur le bureau** : clic droit → « Autoriser le lancement ». Cela arrive si GNOME n'a pas pu marquer le fichier comme fiable.
- **Mises à jour** : pas automatiques. Relancez le script de temps en temps.
- **Cowork** (agents en machine virtuelle) nécessite KVM et le groupe `kvm`, donc un administrateur. Le Chat et Claude Code fonctionnent sans.
- **Bibliothèques manquantes** : sur un Ubuntu Desktop standard, tout est déjà présent. Sinon le script affiche la commande `apt` à transmettre à un administrateur.

### Alternative sans rien installer

[claude.ai/code](https://claude.ai/code) dans le navigateur, pour les projets hébergés sur GitHub.

---

## 2. Claude Code en ligne de commande

```bash
bash scripts/install-claude-code.sh
source ~/.bashrc
claude --version
```

| Commande | Effet |
|---|---|
| `bash install-claude-code.sh` | Installateur natif officiel vers `~/.local/bin`, repli automatique sur Node/npm |
| `bash install-claude-code.sh --npm` | Force la méthode Node.js via nvm + `npm install -g @anthropic-ai/claude-code` |
| `bash install-claude-code.sh --help` | Aide |

Ensuite : `cd mon-projet` puis `claude`. Diagnostic avec `claude doctor`, mise à jour avec `claude update`.

---

## Télécharger les scripts directement

```bash
B=https://raw.githubusercontent.com/zfrcf/COLLEGE/claude/focused-lovelace-7xclxg/scripts
curl -fsSLO $B/install-claude-desktop.sh && bash install-claude-desktop.sh
```
