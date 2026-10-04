#!/usr/bin/env bash
# kwin-watchdog : relance KWin automatiquement dès qu'il s'arrête.
#
# Fonctionnement :
#   - toutes les INTERVAL secondes, vérifie qu'un processus kwin_x11 (ou kwin_wayland) tourne ;
#   - s'il a disparu, le relance soit via l'unité systemd de Plasma (si elle existe),
#     soit directement avec « kwin_x11 --replace ».
#
# Variables d'environnement optionnelles :
#   KWIN_WATCHDOG_INTERVAL   délai entre deux vérifications (défaut : 2 s)
#   KWIN_WATCHDOG_COOLDOWN   pause après un redémarrage (défaut : 5 s)

set -u

INTERVAL="${KWIN_WATCHDOG_INTERVAL:-2}"
COOLDOWN="${KWIN_WATCHDOG_COOLDOWN:-5}"

log() {
    # Visible dans : journalctl --user -u kwin-watchdog -f
    printf '[kwin-watchdog] %s\n' "$*"
}

# Détermine le binaire KWin à surveiller selon le type de session.
detect_kwin() {
    case "${XDG_SESSION_TYPE:-}" in
        wayland) echo "kwin_wayland" ;;
        x11)     echo "kwin_x11" ;;
        *)
            if pgrep -x kwin_wayland >/dev/null 2>&1; then
                echo "kwin_wayland"
            else
                echo "kwin_x11"
            fi
            ;;
    esac
}

# Garantit un DISPLAY exploitable quand le service est lancé hors de l'environnement graphique.
ensure_display() {
    if [ -z "${DISPLAY:-}" ]; then
        export DISPLAY=":0"
    fi
    if [ -z "${XAUTHORITY:-}" ] && [ -f "$HOME/.Xauthority" ]; then
        export XAUTHORITY="$HOME/.Xauthority"
    fi
}

# Attend que la session graphique soit réellement disponible (évite une boucle au démarrage).
wait_for_session() {
    local tries=0
    until pgrep -x plasmashell >/dev/null 2>&1 || pgrep -x "$KWIN_BIN" >/dev/null 2>&1; do
        tries=$((tries + 1))
        if [ "$tries" -ge 60 ]; then
            log "Session Plasma introuvable après 60 s, poursuite quand même."
            break
        fi
        sleep 1
    done
}

restart_kwin() {
    local unit="plasma-${KWIN_BIN}.service"

    # 1) Plasma ≥ 5.25 gère KWin via systemd --user : on passe par là pour rester cohérent.
    if systemctl --user cat "$unit" >/dev/null 2>&1; then
        log "KWin absent → systemctl --user restart $unit"
        if systemctl --user restart "$unit"; then
            return 0
        fi
        log "Échec du redémarrage via systemd, tentative directe."
    fi

    # 2) Lancement direct, détaché du watchdog.
    if [ "$KWIN_BIN" = "kwin_wayland" ]; then
        # Sous Wayland, KWin EST le serveur d'affichage : si il meurt, la session
        # entière tombe. On tente néanmoins un relancement si une session survit.
        log "KWin absent → lancement direct de kwin_wayland"
        setsid kwin_wayland --xwayland --replace >/dev/null 2>&1 < /dev/null &
    else
        log "KWin absent → lancement direct de kwin_x11 --replace"
        setsid kwin_x11 --replace >/dev/null 2>&1 < /dev/null &
    fi
}

main() {
    KWIN_BIN="$(detect_kwin)"
    ensure_display
    log "Démarrage : surveillance de $KWIN_BIN toutes les ${INTERVAL}s (DISPLAY=${DISPLAY:-?})"
    wait_for_session

    while true; do
        if ! pgrep -x "$KWIN_BIN" >/dev/null 2>&1; then
            restart_kwin
            sleep "$COOLDOWN"
        fi
        sleep "$INTERVAL"
    done
}

main "$@"
