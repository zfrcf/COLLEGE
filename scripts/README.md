# Installer Claude Code sur Ubuntu sans sudo

Script : `scripts/install-claude-code.sh`

Tout est installé dans votre dossier personnel (`~/.local/bin`, et `~/.nvm` en secours).
Aucun droit administrateur n'est nécessaire.

## Utilisation rapide

```bash
bash scripts/install-claude-code.sh
source ~/.bashrc
claude --version
```

Ou en une ligne, directement depuis GitHub :

```bash
curl -fsSL https://raw.githubusercontent.com/zfrcf/college/main/scripts/install-claude-code.sh | bash
```

## Options

| Commande | Effet |
|---|---|
| `bash install-claude-code.sh` | Installateur natif officiel, puis repli automatique sur Node/npm en cas d'échec |
| `bash install-claude-code.sh --npm` | Force la méthode Node.js via nvm + `npm install -g @anthropic-ai/claude-code` |
| `bash install-claude-code.sh --help` | Affiche l'aide |

## Ce que fait le script

1. Vérifie que `curl` ou `wget` est présent.
2. Ajoute `~/.local/bin` au PATH dans `~/.bashrc`, `~/.zshrc` et `~/.profile` si besoin.
3. Lance l'installateur natif de Claude Code (binaire autonome, sans Node.js).
4. En cas d'échec, installe nvm puis Node.js LTS dans `~/.nvm` et Claude Code via npm, toujours sans sudo.
5. Vérifie que `claude` répond et affiche les prochaines étapes.

## Après l'installation

```bash
cd mon-projet
claude          # première connexion : compte Claude ou clé API
claude doctor   # diagnostic
claude update   # mise à jour
```
