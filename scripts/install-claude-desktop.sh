#!/usr/bin/env bash
# =============================================================================
#  Claude Desktop (interface graphique : Chat + Claude Code) sur Ubuntu
#  — installation SANS sudo / SANS droits root —
# -----------------------------------------------------------------------------
#  Usage :
#     bash install-claude-desktop.sh              # installe / met à jour + icône sur le bureau
#     bash install-claude-desktop.sh --bureau     # (re)crée seulement l'icône sur le bureau
#     bash install-claude-desktop.sh --sans-bureau  # installe sans icône sur le bureau
#     bash install-claude-desktop.sh --uninstall  # désinstalle proprement
#     bash install-claude-desktop.sh --help
#
#  Le paquet .deb officiel d'Anthropic est téléchargé puis simplement extrait
#  dans ~/.local/opt/claude-desktop (pas d'apt, pas de dpkg -i, donc pas de root).
#  Un lanceur est créé dans ~/.local/bin et une entrée de menu dans
#  ~/.local/share/applications : l'appli apparaît dans votre menu Ubuntu.
#
#  Prérequis : Ubuntu 22.04+ (ou Debian 12+), x86_64 ou arm64, session graphique.
# =============================================================================
set -euo pipefail

VERT='\033[0;32m'; JAUNE='\033[1;33m'; ROUGE='\033[0;31m'; BLEU='\033[0;34m'; FIN='\033[0m'
info()  { echo -e "${BLEU}[INFO]${FIN}  $*"; }
ok()    { echo -e "${VERT}[OK]${FIN}    $*"; }
warn()  { echo -e "${JAUNE}[ATTN]${FIN}  $*"; }
err()   { echo -e "${ROUGE}[ERREUR]${FIN} $*" >&2; }

REPO_URL="https://downloads.claude.ai/claude-desktop/apt/stable"
PREFIX="$HOME/.local"
APP_DIR="$PREFIX/opt/claude-desktop"
BIN_DIR="$PREFIX/bin"
LAUNCHER="$BIN_DIR/claude-desktop"
DESKTOP_DIR="$PREFIX/share/applications"
DESKTOP_FILE="$DESKTOP_DIR/claude-desktop.desktop"
ICON_DIR="$PREFIX/share/icons/hicolor"

ACTION="install"
BUREAU=1
for arg in "$@"; do
  case "$arg" in
    --uninstall)   ACTION="uninstall" ;;
    --bureau)      ACTION="bureau" ;;
    --sans-bureau) BUREAU=0 ;;
    -h|--help) sed -n '2,19p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) err "Option inconnue : $arg (voir --help)"; exit 1 ;;
  esac
done

# -----------------------------------------------------------------------------
# Raccourci sur le bureau (GNOME / KDE / XFCE…)
# -----------------------------------------------------------------------------
dossier_bureau() {
  local d=""
  command -v xdg-user-dir >/dev/null 2>&1 && d="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  if [ -z "$d" ] || [ "$d" = "$HOME" ]; then
    for c in "$HOME/Bureau" "$HOME/Desktop"; do [ -d "$c" ] && { d="$c"; break; }; done
  fi
  [ -z "$d" ] && d="$HOME/Bureau"
  echo "$d"
}

creer_raccourci_bureau() {
  if [ ! -f "$DESKTOP_FILE" ]; then
    err "Claude Desktop n'est pas installé : lancez d'abord  bash $0"
    return 1
  fi
  local bureau raccourci
  bureau="$(dossier_bureau)"
  mkdir -p "$bureau"
  raccourci="$bureau/claude-desktop.desktop"
  cp "$DESKTOP_FILE" "$raccourci"
  # Chemin absolu de l'icône : fiable même si le thème d'icônes n'est pas rechargé
  sed -i "s|^Icon=.*|Icon=$ICON_DIR/256x256/apps/claude-desktop.png|" "$raccourci"
  chmod +x "$raccourci"
  # GNOME (Ubuntu) exige que le lanceur soit marqué « de confiance », sinon
  # l'icône reste barrée et demande « Autoriser le lancement » au clic droit.
  if command -v gio >/dev/null 2>&1; then
    gio set "$raccourci" metadata::trusted true 2>/dev/null || true
  fi
  if command -v dbus-launch >/dev/null 2>&1 && [ -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]; then
    dbus-launch gio set "$raccourci" metadata::trusted true 2>/dev/null || true
  fi
  ok "Icône « Claude » ajoutée sur le bureau : $raccourci"
  info "Si l'icône apparaît barrée : clic droit → « Autoriser le lancement »."
}

if [ "$ACTION" = "bureau" ]; then
  creer_raccourci_bureau
  exit $?
fi

# -----------------------------------------------------------------------------
# Désinstallation
# -----------------------------------------------------------------------------
if [ "$ACTION" = "uninstall" ]; then
  rm -rf "$APP_DIR"
  rm -f "$LAUNCHER" "$DESKTOP_FILE" "$(dossier_bureau)/claude-desktop.desktop"
  find "$ICON_DIR" -name 'claude-desktop.png' -delete 2>/dev/null || true
  command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
  ok "Claude Desktop désinstallé (vos données dans ~/.config/Claude sont conservées)."
  exit 0
fi

# -----------------------------------------------------------------------------
# 0. Vérifications
# -----------------------------------------------------------------------------
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64)        DEB_ARCH="amd64" ;;
  aarch64|arm64) DEB_ARCH="arm64" ;;
  *) err "Architecture non supportée : $ARCH (amd64 ou arm64 uniquement)"; exit 1 ;;
esac

if command -v curl >/dev/null 2>&1; then
  dl() { curl -fsSL "$1" -o "$2"; }
  dl_stdout() { curl -fsSL "$1"; }
elif command -v wget >/dev/null 2>&1; then
  dl() { wget -qO "$2" "$1"; }
  dl_stdout() { wget -qO- "$1"; }
else
  err "Ni curl ni wget disponible. Demandez à un administrateur : sudo apt install curl"
  exit 1
fi

if command -v dpkg-deb >/dev/null 2>&1; then
  EXTRACT="dpkg"
elif command -v ar >/dev/null 2>&1 && command -v tar >/dev/null 2>&1; then
  EXTRACT="ar"
else
  err "Impossible d'extraire un .deb : ni dpkg-deb ni ar/tar ne sont présents."
  exit 1
fi

# -----------------------------------------------------------------------------
# 1. Trouver et télécharger la dernière version
# -----------------------------------------------------------------------------
info "Recherche de la dernière version de Claude Desktop ($DEB_ARCH)…"
DEB_PATH="$(dl_stdout "$REPO_URL/dists/stable/main/binary-$DEB_ARCH/Packages" \
  | grep '^Filename: pool/main/c/claude-desktop/claude-desktop_' | sort -V | tail -n1 | cut -d' ' -f2 || true)"
if [ -z "$DEB_PATH" ]; then
  err "Aucun paquet trouvé. Vérifiez que downloads.claude.ai est joignable."
  exit 1
fi
VERSION="$(basename "$DEB_PATH" | sed -E 's/^claude-desktop_([^_]+)_.*/\1/')"

if [ -f "$APP_DIR/VERSION" ] && [ "$(cat "$APP_DIR/VERSION")" = "$VERSION" ]; then
  ok "Claude Desktop $VERSION est déjà installé dans $APP_DIR."
  [ "$BUREAU" -eq 1 ] && creer_raccourci_bureau
  info "Relancez avec --uninstall puis réinstallez si vous voulez forcer."
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
info "Téléchargement de claude-desktop $VERSION (~170 Mo)…"
dl "$REPO_URL/$DEB_PATH" "$TMP/claude-desktop.deb"

# -----------------------------------------------------------------------------
# 2. Extraction dans ~/.local/opt (aucun droit root nécessaire)
# -----------------------------------------------------------------------------
info "Extraction du paquet…"
mkdir -p "$TMP/root"
if [ "$EXTRACT" = "dpkg" ]; then
  dpkg-deb -x "$TMP/claude-desktop.deb" "$TMP/root"
else
  (cd "$TMP" && ar x claude-desktop.deb && tar -xf data.tar.* -C root)
fi

rm -rf "$APP_DIR"
mkdir -p "$(dirname "$APP_DIR")" "$BIN_DIR" "$DESKTOP_DIR"
mv "$TMP/root/usr/lib/claude-desktop" "$APP_DIR"
echo "$VERSION" > "$APP_DIR/VERSION"

# Icônes dans le thème utilisateur
for png in "$TMP"/root/usr/share/icons/hicolor/*/apps/claude-desktop.png; do
  taille="$(basename "$(dirname "$(dirname "$png")")")"
  mkdir -p "$ICON_DIR/$taille/apps"
  cp "$png" "$ICON_DIR/$taille/apps/"
done

# -----------------------------------------------------------------------------
# 3. Lanceur : gère le bac à sable Chromium sans droits root
# -----------------------------------------------------------------------------
# Le paquet officiel installe (en root) un helper SUID et un profil AppArmor.
# Sans root, sur Ubuntu 24.04+ (userns restreint), Electron ne peut pas créer
# son bac à sable : on passe alors --no-sandbox. Sur 22.04 ce n'est pas requis.
cat > "$LAUNCHER" <<'LANCEUR'
#!/usr/bin/env bash
APP="$HOME/.local/opt/claude-desktop/claude-desktop"
FLAGS=()
restrict="$(cat /proc/sys/kernel/apparmor_restrict_unprivileged_userns 2>/dev/null || echo 0)"
if [ "$restrict" = "1" ] || [ "${CLAUDE_DESKTOP_NO_SANDBOX:-0}" = "1" ]; then
  FLAGS+=(--no-sandbox)
fi
exec "$APP" "${FLAGS[@]}" "$@"
LANCEUR
chmod +x "$LAUNCHER"

# -----------------------------------------------------------------------------
# 4. Entrée de menu (menu Ubuntu / GNOME / KDE) + liens claude://
# -----------------------------------------------------------------------------
cat > "$DESKTOP_FILE" <<EOF2
[Desktop Entry]
Name=Claude
Comment=Claude Desktop : Chat et Claude Code (interface graphique)
GenericName=Assistant IA
Keywords=AI;IA;Chat;Assistant;Claude;Code;LLM;
Exec=$LAUNCHER %U
Icon=claude-desktop
Type=Application
StartupNotify=true
StartupWMClass=com.anthropic.Claude
SingleMainWindow=true
Categories=Utility;Development;
MimeType=x-scheme-handler/claude;
Actions=NewChat;NewCode;

[Desktop Action NewChat]
Name=Nouvelle discussion
Exec=$LAUNCHER "claude://claude.ai/new?surface=chat&source=desktop_action"

[Desktop Action NewCode]
Name=Nouvelle session Claude Code
Exec=$LAUNCHER "claude://code/new?source=desktop_action"
EOF2

command -v update-desktop-database >/dev/null 2>&1 && update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
command -v gtk-update-icon-cache  >/dev/null 2>&1 && gtk-update-icon-cache -q -t "$ICON_DIR" 2>/dev/null || true
command -v xdg-mime >/dev/null 2>&1 && xdg-mime default claude-desktop.desktop x-scheme-handler/claude 2>/dev/null || true

[ "$BUREAU" -eq 1 ] && creer_raccourci_bureau

# -----------------------------------------------------------------------------
# 5. PATH + bibliothèques système
# -----------------------------------------------------------------------------
ligne='export PATH="$HOME/.local/bin:$PATH"'
for rc in "$HOME/.bashrc" "$HOME/.zshrc" "$HOME/.profile"; do
  if [ -f "$rc" ] && ! grep -Fq '.local/bin' "$rc"; then
    printf '\n# Ajouté par install-claude-desktop.sh\n%s\n' "$ligne" >> "$rc"
  fi
done

MANQUANTES="$(ldd "$APP_DIR/claude-desktop" 2>/dev/null | awk '/not found/{print $1}' | sort -u || true)"
if [ -n "$MANQUANTES" ]; then
  warn "Bibliothèques système manquantes (un administrateur doit les installer) :"
  echo "$MANQUANTES" | sed 's/^/      /'
  warn "Commande pour l'admin : sudo apt install libgtk-3-0 libnotify4 libnss3 libxss1 libasound2t64 libatspi2.0-0 libdrm2 libgbm1 libsecret-1-0 libxtst6 xdg-utils"
fi

# -----------------------------------------------------------------------------
# 6. Vérification
# -----------------------------------------------------------------------------
if V="$("$LAUNCHER" --version 2>/dev/null | tail -n1)"; then
  ok "Claude Desktop $V installé dans $APP_DIR"
else
  warn "Installé, mais le test de lancement a échoué (normal sans session graphique)."
fi
echo
echo -e "${VERT}Pour lancer l'interface :${FIN}"
echo "  • Double-clic sur l'icône « Claude » du bureau"
echo "  • Menu des applications  →  « Claude »  (déconnexion/reconnexion si absent)"
echo "  • ou dans un terminal :     claude-desktop"
echo
echo "  Mise à jour      : relancez ce script"
echo "  Icône du bureau  : bash $0 --bureau"
echo "  Désinstallation  : bash $0 --uninstall"
echo "  Connexion        : compte claude.ai (Pro/Max/Team) ou SSO — pas de clé API"
