#!/usr/bin/env bash
# =============================================================================
#  Installation de Claude Code sur Ubuntu — SANS sudo / SANS droits root
# -----------------------------------------------------------------------------
#  Usage :
#     bash install-claude-code.sh            # installation standard
#     bash install-claude-code.sh --npm      # forcer la méthode Node/npm (nvm)
#     bash install-claude-code.sh --help
#
#  Méthode 1 (par défaut) : installateur natif officiel -> ~/.local/bin/claude
#  Méthode 2 (secours)    : Node.js via nvm (dans ~/.nvm) + npm install -g
#  Tout est installé dans le dossier personnel : aucun droit administrateur.
# =============================================================================
set -euo pipefail

VERT='\033[0;32m'; JAUNE='\033[1;33m'; ROUGE='\033[0;31m'; BLEU='\033[0;34m'; FIN='\033[0m'
info()  { echo -e "${BLEU}[INFO]${FIN}  $*"; }
ok()    { echo -e "${VERT}[OK]${FIN}    $*"; }
warn()  { echo -e "${JAUNE}[ATTN]${FIN}  $*"; }
err()   { echo -e "${ROUGE}[ERREUR]${FIN} $*" >&2; }

FORCE_NPM=0
for arg in "$@"; do
  case "$arg" in
    --npm)  FORCE_NPM=1 ;;
    -h|--help)
      sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    *) err "Option inconnue : $arg (voir --help)"; exit 1 ;;
  esac
done

# -----------------------------------------------------------------------------
# 0. Vérifications préalables
# -----------------------------------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
  warn "Vous êtes root : ce script est prévu pour un utilisateur normal, mais on continue."
fi

if ! command -v curl >/dev/null 2>&1 && ! command -v wget >/dev/null 2>&1; then
  err "Ni 'curl' ni 'wget' n'est disponible. Sur Ubuntu, curl est normalement préinstallé."
  err "Sans sudo, demandez à un administrateur : sudo apt install curl"
  exit 1
fi

telecharger() {
  # telecharger <url>  -> écrit sur stdout
  if command -v curl >/dev/null 2>&1; then
    curl -fsSL "$1"
  else
    wget -qO- "$1"
  fi
}

# -----------------------------------------------------------------------------
# 1. S'assurer que ~/.local/bin est dans le PATH (maintenant + à l'avenir)
# -----------------------------------------------------------------------------
BIN_DIR="$HOME/.local/bin"
mkdir -p "$BIN_DIR"

ajouter_path() {
  local ligne='export PATH="$HOME/.local/bin:$PATH"'
  local rc
  for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
    if [ -f "$rc" ] && ! grep -Fq '.local/bin' "$rc"; then
      {
        echo ''
        echo '# Ajouté par install-claude-code.sh'
        echo "$ligne"
      } >> "$rc"
      info "PATH mis à jour dans $rc"
    fi
  done
  [ -f "$HOME/.bashrc" ] || { echo "$ligne" >> "$HOME/.bashrc"; info "PATH ajouté dans ~/.bashrc"; }
}
ajouter_path
case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) export PATH="$BIN_DIR:$PATH" ;;
esac

# -----------------------------------------------------------------------------
# 2. Méthode 1 : installateur natif (aucune dépendance Node, aucun sudo)
# -----------------------------------------------------------------------------
installer_natif() {
  info "Méthode 1 : installateur natif officiel (claude.ai/install.sh)…"
  if telecharger https://claude.ai/install.sh | bash; then
    return 0
  fi
  return 1
}

# -----------------------------------------------------------------------------
# 3. Méthode 2 : Node.js via nvm (dans le HOME) puis npm install -g
# -----------------------------------------------------------------------------
installer_npm() {
  info "Méthode 2 : Node.js via nvm + npm (tout dans votre dossier personnel)…"
  export NVM_DIR="$HOME/.nvm"

  if [ ! -s "$NVM_DIR/nvm.sh" ]; then
    info "Installation de nvm dans $NVM_DIR…"
    telecharger https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh | bash
  fi
  # shellcheck disable=SC1091
  . "$NVM_DIR/nvm.sh"

  if ! command -v node >/dev/null 2>&1 || [ "$(node -p 'process.versions.node.split(".")[0]')" -lt 18 ]; then
    info "Installation de Node.js LTS (Claude Code requiert Node 18+)…"
    nvm install --lts
  fi
  nvm use --lts >/dev/null

  info "npm install -g @anthropic-ai/claude-code (préfixe npm dans ~/.nvm, donc sans sudo)…"
  npm install -g @anthropic-ai/claude-code

  # Lien pratique dans ~/.local/bin pour que 'claude' soit dispo même hors nvm
  local cible
  cible="$(command -v claude || true)"
  if [ -n "$cible" ] && [ ! -e "$BIN_DIR/claude" ]; then
    ln -s "$cible" "$BIN_DIR/claude"
  fi
}

# -----------------------------------------------------------------------------
# 4. Exécution
# -----------------------------------------------------------------------------
if command -v claude >/dev/null 2>&1 && [ "$FORCE_NPM" -eq 0 ]; then
  warn "Claude Code semble déjà installé : $(command -v claude)"
  info "Pour mettre à jour : claude update"
else
  if [ "$FORCE_NPM" -eq 1 ]; then
    installer_npm
  elif ! installer_natif; then
    warn "L'installateur natif a échoué, bascule sur la méthode Node/npm…"
    installer_npm
  fi
fi

# -----------------------------------------------------------------------------
# 5. Vérification
# -----------------------------------------------------------------------------
hash -r 2>/dev/null || true
if command -v claude >/dev/null 2>&1; then
  ok "Claude Code installé : $(command -v claude)"
  ok "Version : $(claude --version 2>/dev/null || echo 'inconnue')"
  echo
  echo -e "${VERT}Prochaines étapes :${FIN}"
  echo "  1. Ouvrez un nouveau terminal (ou lancez :  source ~/.bashrc )"
  echo "  2. Placez-vous dans votre projet :  cd mon-projet"
  echo "  3. Lancez :  claude   puis connectez-vous (compte Claude ou clé API)"
  echo
  echo "  Diagnostic :  claude doctor      Mise à jour :  claude update"
else
  err "Installation terminée mais 'claude' est introuvable dans le PATH."
  err "Essayez :  source ~/.bashrc   puis   claude --version"
  err "Ou relancez avec :  bash $0 --npm"
  exit 1
fi
