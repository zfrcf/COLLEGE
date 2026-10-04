#!/usr/bin/env bash
# Installe le watchdog KWin pour l'utilisateur courant (aucun droit root requis).
#
#   ./install.sh            installation + activation immédiate
#   ./install.sh --dry-run  affiche les actions sans rien modifier

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
UNIT_DIR="$HOME/.config/systemd/user"
DOC_DIR="$HOME/.local/share/kwin-watchdog"
DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

run() {
    if [ "$DRY_RUN" -eq 1 ]; then
        printf '  [dry-run] %s\n' "$*"
    else
        "$@"
    fi
}

info() { printf '\033[1;32m➜\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m!\033[0m %s\n' "$*"; }

# --- Vérifications préalables -------------------------------------------------
if [ "$(id -u)" -eq 0 ]; then
    warn "Lancez ce script avec votre utilisateur normal, pas avec sudo."
    exit 1
fi
if ! command -v systemctl >/dev/null 2>&1; then
    warn "systemd introuvable : ce watchdog nécessite systemd (standard sur Ubuntu)."
    exit 1
fi
if ! command -v kwin_x11 >/dev/null 2>&1 && ! command -v kwin_wayland >/dev/null 2>&1; then
    warn "Aucun binaire kwin_x11 / kwin_wayland trouvé. Installez KDE Plasma (ex : sudo apt install kwin-x11)."
    exit 1
fi

# --- Copie des fichiers --------------------------------------------------------
info "Installation du script dans $BIN_DIR"
run mkdir -p "$BIN_DIR" "$UNIT_DIR" "$DOC_DIR"
run install -m 755 "$HERE/kwin-watchdog.sh" "$BIN_DIR/kwin-watchdog.sh"
run install -m 644 "$HERE/kwin-watchdog.service" "$UNIT_DIR/kwin-watchdog.service"
run install -m 644 "$HERE/README.md" "$DOC_DIR/README.md"

# --- Renforcement de l'unité Plasma native (si présente) -----------------------
# Plasma ≥ 5.25 lance KWin via plasma-kwin_x11.service / plasma-kwin_wayland.service.
# On force Restart=always sur ces unités : systemd relance alors KWin en moins d'une seconde,
# le watchdog ne servant que de filet de sécurité.
for unit in plasma-kwin_x11.service plasma-kwin_wayland.service; do
    if systemctl --user cat "$unit" >/dev/null 2>&1; then
        info "Unité $unit détectée → ajout d'un override Restart=always"
        override_dir="$UNIT_DIR/$unit.d"
        run mkdir -p "$override_dir"
        if [ "$DRY_RUN" -eq 1 ]; then
            printf '  [dry-run] écriture de %s/kwin-watchdog.conf\n' "$override_dir"
        else
            cat > "$override_dir/kwin-watchdog.conf" <<'CONF'
# Ajouté par kwin-watchdog : relance KWin quelle que soit la raison de l'arrêt.
[Unit]
StartLimitIntervalSec=0

[Service]
Restart=always
RestartSec=1
CONF
        fi
    fi
done

# --- Démarrage automatique KDE (ceinture de sécurité) -------------------------
# Si la session Plasma ne passe pas par systemd, ce fichier .desktop démarre
# quand même le service à l'ouverture de session.
AUTOSTART_DIR="$HOME/.config/autostart"
info "Ajout du déclencheur de secours dans $AUTOSTART_DIR"
run mkdir -p "$AUTOSTART_DIR"
if [ "$DRY_RUN" -eq 1 ]; then
    printf '  [dry-run] écriture de %s/kwin-watchdog.desktop\n' "$AUTOSTART_DIR"
else
    cat > "$AUTOSTART_DIR/kwin-watchdog.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=KWin Watchdog
Comment=Relance KWin automatiquement s'il s'arrête
Exec=systemctl --user start kwin-watchdog.service
X-KDE-autostart-phase=2
OnlyShowIn=KDE;
X-GNOME-Autostart-enabled=true
DESKTOP
fi

# --- Activation ---------------------------------------------------------------
info "Rechargement de systemd --user et activation du service"
run systemctl --user daemon-reload
run systemctl --user enable --now kwin-watchdog.service

if [ "$DRY_RUN" -eq 0 ]; then
    echo
    systemctl --user --no-pager status kwin-watchdog.service || true
    echo
    info "Terminé. Suivi en direct : journalctl --user -u kwin-watchdog -f"
    info "Test : pkill -x kwin_x11   (KWin doit revenir en quelques secondes)"
fi
