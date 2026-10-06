#!/usr/bin/env bash
# =====================================================================
#  Réparateur de bureau Ubuntu
#  Pour : écran noir, pas de barre des tâches, touche Super inactive.
#
#  Lancement depuis une console texte (Ctrl+Alt+F3, puis se connecter) :
#      sudo bash bureau.sh
# =====================================================================

set -u

LOG=/var/log/reparer-bureau.log
DATE=$(date +%Y%m%d-%H%M%S)

R=$'\e[31m'; V=$'\e[32m'; J=$'\e[33m'; B=$'\e[36m'; G=$'\e[1m'; N=$'\e[0m'

info()  { echo "${B}➜${N} $*"; echo "[INFO] $*" >>"$LOG"; }
ok()    { echo "${V}✔${N} $*"; echo "[OK] $*" >>"$LOG"; }
alerte(){ echo "${J}⚠${N} $*"; echo "[ALERTE] $*" >>"$LOG"; }
err()   { echo "${R}✖${N} $*"; echo "[ERREUR] $*" >>"$LOG"; }
pause() { echo; read -rp "Appuie sur Entrée pour continuer…" _; }
oui()   { local r; read -rp "$1 [o/N] " r; [[ "$r" =~ ^[oOyY] ]]; }

# ---------------------------------------------------------------------
# Droits administrateur
# ---------------------------------------------------------------------
if [ "$(id -u)" -ne 0 ]; then
  echo "Ce programme a besoin des droits administrateur."
  exec sudo bash "$0" "$@"
fi
touch "$LOG" 2>/dev/null || LOG=/tmp/reparer-bureau.log

# ---------------------------------------------------------------------
# Utilisateur concerné
# ---------------------------------------------------------------------
UTIL="${SUDO_USER:-}"
if [ -z "$UTIL" ] || [ "$UTIL" = "root" ]; then
  echo "Utilisateurs du système :"
  awk -F: '$3>=1000 && $3<65000 {print "  - "$1}' /etc/passwd
  read -rp "Nom de ton utilisateur : " UTIL
fi
if ! id "$UTIL" >/dev/null 2>&1; then
  err "Utilisateur « $UTIL » introuvable."; exit 1
fi
MAISON=$(getent passwd "$UTIL" | cut -d: -f6)
GROUPE=$(id -gn "$UTIL")
SAUV="$MAISON/sauvegarde-bureau-$DATE"

# ---------------------------------------------------------------------
# Détection de l'environnement
# ---------------------------------------------------------------------
detecter_meta() {
  for p in ubuntu-desktop ubuntu-desktop-minimal kubuntu-desktop xubuntu-desktop \
           ubuntu-mate-desktop lubuntu-desktop ubuntu-budgie-desktop; do
    if dpkg -s "$p" >/dev/null 2>&1; then echo "$p"; return; fi
  done
  echo "ubuntu-desktop"
}
detecter_dm() {
  if [ -f /etc/X11/default-display-manager ]; then
    basename "$(cat /etc/X11/default-display-manager)"
  elif dpkg -s gdm3 >/dev/null 2>&1; then echo gdm3
  else echo lightdm; fi
}
META=$(detecter_meta)
DM=$(detecter_dm)

internet() { wget -q --spider --timeout=6 http://archive.ubuntu.com 2>/dev/null; }

verifier_internet() {
  if internet; then ok "Connexion internet : OK"; return 0; fi
  err "Pas de connexion internet."
  echo "  Pour te connecter au Wi-Fi, choisis l'option 9 du menu (Wi-Fi),"
  echo "  ou branche un câble réseau, puis recommence."
  return 1
}

sauvegarder() { # copie ~/<chemin relatif> dans la sauvegarde, même arborescence
  local rel="$1"
  [ -e "$MAISON/$rel" ] || return 0
  mkdir -p "$SAUV/$(dirname "$rel")"
  cp -a "$MAISON/$rel" "$SAUV/$rel" 2>/dev/null && info "Sauvegardé : ~/$rel"
  chown -R "$UTIL:$GROUPE" "$SAUV"
}

# ---------------------------------------------------------------------
# 1. Diagnostic
# ---------------------------------------------------------------------
diagnostic() {
  echo; echo "${G}=== DIAGNOSTIC ===${N}"
  echo "Utilisateur : $UTIL ($MAISON)"
  echo "Système     : $(. /etc/os-release; echo "$PRETTY_NAME")"
  echo "Bureau      : $META   |   Écran de connexion : $DM"
  echo

  # Espace disque — cause n°1 des écrans noirs
  local pct
  pct=$(df --output=pcent / | tail -1 | tr -dc '0-9')
  if [ "$pct" -ge 97 ]; then
    err "Disque presque plein ($pct %) — c'est très probablement la cause ! → option 2"
  else
    ok "Espace disque : $pct % utilisé"
  fi

  # Paquets cassés
  if dpkg --audit 2>/dev/null | grep -q .; then
    err "Des paquets sont à moitié installés (mise à jour interrompue ?) → option 2"
  else
    ok "Paquets : cohérents"
  fi

  # Bureau installé
  if command -v gnome-shell >/dev/null || command -v plasmashell >/dev/null \
     || command -v xfce4-session >/dev/null; then
    ok "Environnement de bureau : présent"
  else
    err "Aucun environnement de bureau trouvé → option 2"
  fi

  # Fichiers appartenant à root dans le dossier perso
  local mauvais
  mauvais=$(find "$MAISON" -maxdepth 2 -user root 2>/dev/null | grep -v "sauvegarde-bureau" | head -5)
  if [ -n "$mauvais" ]; then
    alerte "Fichiers appartenant à root dans ton dossier (bloquent la session) → option 2"
    echo "$mauvais" | sed 's/^/     /'
  else
    ok "Droits du dossier personnel : OK"
  fi

  # Extensions GNOME
  if [ -d "$MAISON/.local/share/gnome-shell/extensions" ] && \
     [ -n "$(ls -A "$MAISON/.local/share/gnome-shell/extensions" 2>/dev/null)" ]; then
    alerte "Extensions GNOME installées (une extension cassée peut tout bloquer) → option 3"
  fi

  # Carte graphique NVIDIA
  if lspci 2>/dev/null | grep -qi nvidia; then
    if lsmod | grep -q '^nvidia'; then ok "Pilote NVIDIA chargé"
    else alerte "Carte NVIDIA sans pilote NVIDIA chargé → options 5 et 6"; fi
  fi

  # Session graphique
  if systemctl is-active --quiet "$DM"; then ok "Écran de connexion ($DM) : actif"
  else alerte "Écran de connexion ($DM) : arrêté"; fi

  internet && ok "Internet : OK" || alerte "Internet : non connecté (option 9)"
  pause
}

# ---------------------------------------------------------------------
# 2. Réparation complète (garde fichiers ET réglages)
# ---------------------------------------------------------------------
reparer() {
  echo; echo "${G}=== RÉPARATION (tes fichiers et réglages sont conservés) ===${N}"

  info "Libération d'espace disque…"
  apt-get clean
  journalctl --vacuum-size=100M >/dev/null 2>&1
  rm -rf "$MAISON/.cache/thumbnails" 2>/dev/null
  ok "Espace disque : $(df -h --output=avail / | tail -1 | tr -d ' ') libres"

  info "Correction des droits du dossier personnel…"
  rm -f "$MAISON/.Xauthority" "$MAISON/.ICEauthority"
  find "$MAISON" -xdev -user root -not -path "$SAUV*" -exec chown -h "$UTIL:$GROUPE" {} + 2>/dev/null
  chown "$UTIL:$GROUPE" "$MAISON"
  chmod 1777 /tmp
  ok "Droits corrigés"

  info "Réparation des paquets interrompus…"
  dpkg --configure -a 2>&1 | tee -a "$LOG" | tail -3

  if verifier_internet; then
    info "Mise à jour de la liste des paquets…"
    apt-get update 2>&1 | tail -2
    apt-get -y -f install 2>&1 | tail -2
    info "Réinstallation du bureau ($META) — peut prendre 5 à 20 min…"
    DEBIAN_FRONTEND=noninteractive apt-get -y install --reinstall "$META" "$DM" 2>&1 | tail -3
    if [ "$META" = "ubuntu-desktop" ] || [ "$META" = "ubuntu-desktop-minimal" ]; then
      DEBIAN_FRONTEND=noninteractive apt-get -y install --reinstall \
        gnome-shell gnome-session gnome-terminal gnome-shell-extension-ubuntu-dock 2>&1 | tail -3
    fi
    DEBIAN_FRONTEND=noninteractive apt-get -y upgrade 2>&1 | tail -3
    ok "Bureau réinstallé"
  else
    alerte "Sans internet : seules les réparations locales ont été faites."
  fi

  # Écran mal configuré = écran noir fréquent
  if [ -f "$MAISON/.config/monitors.xml" ]; then
    sauvegarder .config/monitors.xml
    rm -f "$MAISON/.config/monitors.xml"
    ok "Configuration d'écran réinitialisée"
  fi

  ok "Réparation terminée. Utilise l'option 8 pour relancer l'interface."
  pause
}

# ---------------------------------------------------------------------
# 3. Désactiver les extensions GNOME
# ---------------------------------------------------------------------
desactiver_extensions() {
  echo; echo "${G}=== DÉSACTIVATION DES EXTENSIONS ===${N}"
  local ext="$MAISON/.local/share/gnome-shell/extensions"
  if [ -d "$ext" ]; then
    mkdir -p "$SAUV/.local/share/gnome-shell"
    mv "$ext" "$SAUV/.local/share/gnome-shell/extensions" && ok "Extensions mises de côté dans $SAUV"
    chown -R "$UTIL:$GROUPE" "$SAUV"
  else
    info "Aucune extension personnelle."
  fi
  sudo -u "$UTIL" dbus-run-session dconf write \
    /org/gnome/shell/disable-user-extensions true 2>/dev/null \
    && ok "Extensions désactivées dans GNOME"
  pause
}

# ---------------------------------------------------------------------
# 4. Réinitialiser l'apparence du bureau (fichiers conservés)
# ---------------------------------------------------------------------
reinit_bureau() {
  echo; echo "${G}=== BUREAU NEUF (tes fichiers restent intacts) ===${N}"
  echo "Remet le bureau comme au premier jour : thème, dock, raccourcis, fond d'écran."
  echo "Tes documents, photos, téléchargements, etc. ne sont PAS touchés."
  echo "Les anciens réglages sont sauvegardés et restaurables (option 7)."
  oui "Continuer ?" || return
  for f in .config/dconf .config/monitors.xml .local/share/gnome-shell \
           .config/autostart .config/gnome-session .cache/gnome-shell \
           .config/plasma-org.kde.plasma.desktop-appletsrc .config/xfce4; do
    if [ -e "$MAISON/$f" ]; then
      mkdir -p "$SAUV/$(dirname "$f")"
      mv "$MAISON/$f" "$SAUV/$f" && info "Mis de côté : ~/$f"
    fi
  done
  chown -R "$UTIL:$GROUPE" "$SAUV" 2>/dev/null
  ok "Bureau réinitialisé. Sauvegarde : $SAUV"
  echo "   Utilise l'option 8 pour relancer l'interface."
  pause
}

# ---------------------------------------------------------------------
# 5. Basculer Wayland / Xorg
# ---------------------------------------------------------------------
basculer_xorg() {
  echo; echo "${G}=== MODE D'AFFICHAGE ===${N}"
  local conf=/etc/gdm3/custom.conf
  if [ ! -f "$conf" ]; then info "Non concerné (pas de GDM)."; pause; return; fi
  cp -a "$conf" "$conf.bak-$DATE"
  if grep -q '^WaylandEnable=false' "$conf"; then
    sed -i 's/^WaylandEnable=false/#WaylandEnable=false/' "$conf"
    ok "Wayland RÉACTIVÉ (mode moderne)."
  else
    if grep -q '^#\s*WaylandEnable=false' "$conf"; then
      sed -i 's/^#\s*WaylandEnable=false/WaylandEnable=false/' "$conf"
    else
      sed -i '/^\[daemon\]/a WaylandEnable=false' "$conf"
    fi
    ok "Mode Xorg activé (plus compatible, conseillé avec une carte NVIDIA)."
  fi
  pause
}

# ---------------------------------------------------------------------
# 6. Pilotes graphiques
# ---------------------------------------------------------------------
pilotes() {
  echo; echo "${G}=== PILOTES GRAPHIQUES ===${N}"
  verifier_internet || { pause; return; }
  command -v ubuntu-drivers >/dev/null || apt-get -y install ubuntu-drivers-common
  ubuntu-drivers devices 2>/dev/null
  echo
  echo "  a) Installer automatiquement le pilote recommandé"
  echo "  b) Revenir au pilote libre (si le pilote NVIDIA a tout cassé)"
  echo "  autre) Retour"
  read -rp "Choix : " c
  case "$c" in
    a) ubuntu-drivers install 2>&1 | tail -5; ok "Pilote installé. Redémarrage nécessaire (option 8)." ;;
    b) apt-get -y purge '^nvidia-.*' 2>&1 | tail -3
       DEBIAN_FRONTEND=noninteractive apt-get -y install --reinstall xserver-xorg-video-nouveau 2>&1 | tail -2
       ok "Pilote NVIDIA retiré. Redémarrage nécessaire (option 8)." ;;
  esac
  pause
}

# ---------------------------------------------------------------------
# 7. Restaurer une sauvegarde de réglages
# ---------------------------------------------------------------------
restaurer() {
  echo; echo "${G}=== RESTAURER D'ANCIENS RÉGLAGES ===${N}"
  mapfile -t liste < <(ls -d "$MAISON"/sauvegarde-bureau-* 2>/dev/null)
  if [ ${#liste[@]} -eq 0 ]; then info "Aucune sauvegarde."; pause; return; fi
  local i=1
  for s in "${liste[@]}"; do echo "  $i) $(basename "$s")"; i=$((i+1)); done
  read -rp "Numéro : " n
  local src="${liste[$((n-1))]:-}"
  [ -d "$src" ] || return
  cp -a "$src"/. "$MAISON"/ && chown -R "$UTIL:$GROUPE" "$MAISON/.config" "$MAISON/.local" 2>/dev/null
  ok "Réglages restaurés depuis $(basename "$src")"
  pause
}

# ---------------------------------------------------------------------
# 10. Nouveau compte utilisateur tout neuf
# ---------------------------------------------------------------------
nouveau_compte() {
  echo; echo "${G}=== CRÉER UN NOUVEAU COMPTE (bureau 100 % neuf) ===${N}"
  echo "Utile si ton compte actuel reste bloqué. L'ancien compte n'est pas supprimé."
  read -rp "Nom du nouveau compte (minuscules, sans espace) : " nv
  [[ "$nv" =~ ^[a-z][a-z0-9_-]*$ ]] || { err "Nom invalide."; pause; return; }
  if id "$nv" >/dev/null 2>&1; then err "Ce compte existe déjà."; pause; return; fi
  adduser --gecos "" "$nv" || { pause; return; }
  usermod -aG sudo "$nv" && ok "Compte « $nv » créé avec droits administrateur."
  if oui "Copier tes fichiers (Documents, Images, Bureau, Musique, Vidéos, Téléchargements) dans ce compte ?"; then
    local dest
    dest=$(getent passwd "$nv" | cut -d: -f6)
    for d in Documents Images Pictures Bureau Desktop Musique Music Vidéos Videos Téléchargements Downloads; do
      [ -d "$MAISON/$d" ] && cp -a "$MAISON/$d" "$dest/" && info "Copié : $d"
    done
    chown -R "$nv:$(id -gn "$nv")" "$dest"
    ok "Fichiers copiés."
  fi
  echo "   Utilise l'option 8, puis connecte-toi avec « $nv »."
  pause
}

# ---------------------------------------------------------------------
# 11. Sauvegarder ses fichiers sur clé USB / disque externe
# ---------------------------------------------------------------------
sauvegarde_usb() {
  echo; echo "${G}=== SAUVEGARDE SUR CLÉ USB / DISQUE EXTERNE ===${N}"
  echo "Branche ta clé ou ton disque maintenant, puis appuie sur Entrée."; read -r _
  lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT | grep -v loop
  echo
  read -rp "Nom de la partition (ex : sdb1) : " part
  [ -b "/dev/$part" ] || { err "Partition introuvable."; pause; return; }
  mkdir -p /mnt/sauvegarde
  mount "/dev/$part" /mnt/sauvegarde || { err "Montage impossible."; pause; return; }
  local cible="/mnt/sauvegarde/sauvegarde-$UTIL-$DATE"
  info "Copie de $MAISON vers la clé (hors caches)…"
  mkdir -p "$cible"
  if command -v rsync >/dev/null; then
    rsync -rlt --info=progress2 --exclude='.cache' --exclude='snap/*/common/.cache' \
      "$MAISON"/ "$cible"/
  else
    cp -r "$MAISON"/. "$cible"/
  fi
  sync; umount /mnt/sauvegarde
  ok "Sauvegarde terminée, tu peux retirer la clé."
  pause
}

# ---------------------------------------------------------------------
# 9. Wi-Fi
# ---------------------------------------------------------------------
wifi() {
  if command -v nmtui >/dev/null; then nmtui
  else nmcli dev wifi list; read -rp "Nom du réseau : " s; nmcli --ask dev wifi connect "$s"; fi
  verifier_internet; pause
}

# ---------------------------------------------------------------------
# 8. Relancer
# ---------------------------------------------------------------------
relancer() {
  echo
  echo "  a) Relancer seulement l'interface graphique (rapide)"
  echo "  b) Redémarrer l'ordinateur (conseillé après une réparation)"
  read -rp "Choix : " c
  case "$c" in
    a) systemctl restart "$DM"; echo "Retour à l'interface : Ctrl+Alt+F1 ou Ctrl+Alt+F2." ;;
    b) reboot ;;
  esac
}

# ---------------------------------------------------------------------
# Menu principal
# ---------------------------------------------------------------------
while true; do
  clear
  echo "${G}╔══════════════════════════════════════════════════╗"
  echo "║         RÉPARATEUR DE BUREAU UBUNTU              ║"
  echo "╚══════════════════════════════════════════════════╝${N}"
  echo "  Utilisateur : $UTIL"
  echo
  echo "  ${G}RETROUVER MON BUREAU${N}"
  echo "   1) Diagnostic (trouver la panne)"
  echo "   2) Réparation complète          ${V}← à essayer en premier${N}"
  echo "   3) Désactiver les extensions GNOME"
  echo "   5) Basculer Wayland ↔ Xorg      (écran noir + NVIDIA)"
  echo "   6) Pilotes graphiques"
  echo
  echo "  ${G}REPARTIR DE ZÉRO${N}"
  echo "   4) Bureau neuf (réglages remis à zéro, fichiers gardés)"
  echo "  10) Nouveau compte utilisateur tout neuf"
  echo "   7) Restaurer d'anciens réglages"
  echo
  echo "  ${G}OUTILS${N}"
  echo "   9) Connexion Wi-Fi"
  echo "  11) Sauvegarder mes fichiers sur clé USB"
  echo "   8) Relancer l'interface / redémarrer"
  echo "   0) Quitter"
  echo
  read -rp "Ton choix : " choix
  case "$choix" in
    1) diagnostic ;;
    2) reparer ;;
    3) desactiver_extensions ;;
    4) reinit_bureau ;;
    5) basculer_xorg ;;
    6) pilotes ;;
    7) restaurer ;;
    8) relancer ;;
    9) wifi ;;
    10) nouveau_compte ;;
    11) sauvegarde_usb ;;
    0) exit 0 ;;
  esac
done
