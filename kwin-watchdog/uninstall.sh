#!/usr/bin/env bash
# Retire complètement le watchdog KWin (service, script, overrides).
set -euo pipefail

UNIT_DIR="$HOME/.config/systemd/user"

echo "➜ Arrêt et désactivation du service"
systemctl --user disable --now kwin-watchdog.service 2>/dev/null || true

echo "➜ Suppression des fichiers"
rm -f "$UNIT_DIR/kwin-watchdog.service"
rm -f "$HOME/.local/bin/kwin-watchdog.sh"
rm -rf "$HOME/.local/share/kwin-watchdog"
rm -f "$HOME/.config/autostart/kwin-watchdog.desktop"
rm -f "$UNIT_DIR/plasma-kwin_x11.service.d/kwin-watchdog.conf"
rm -f "$UNIT_DIR/plasma-kwin_wayland.service.d/kwin-watchdog.conf"
rmdir "$UNIT_DIR/plasma-kwin_x11.service.d" "$UNIT_DIR/plasma-kwin_wayland.service.d" 2>/dev/null || true

systemctl --user daemon-reload
echo "✔ kwin-watchdog désinstallé."
