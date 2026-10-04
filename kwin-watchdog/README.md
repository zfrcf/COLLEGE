# kwin-watchdog — relance automatique de KWin (Ubuntu / Kubuntu)

Petit outil qui surveille KWin, le gestionnaire de fenêtres de KDE Plasma, et le
relance **immédiatement** s'il s'arrête (crash, `kill`, plantage d'un effet…).
Plus besoin de taper `kwin_x11 --replace` à la main quand les fenêtres perdent
leurs bordures.

## Installation (sans sudo)

```bash
cd kwin-watchdog
chmod +x install.sh
./install.sh
```

Le script :

1. copie `kwin-watchdog.sh` dans `~/.local/bin/` ;
2. installe le service utilisateur `kwin-watchdog.service` dans `~/.config/systemd/user/` ;
3. si Plasma gère déjà KWin via systemd (`plasma-kwin_x11.service`, Plasma ≥ 5.25),
   ajoute un override `Restart=always` pour que systemd relance KWin en moins d'une seconde ;
4. ajoute un fichier `~/.config/autostart/kwin-watchdog.desktop` : déclencheur de secours
   qui démarre le service même si la session Plasma ne passe pas par systemd ;
5. active et démarre le tout. Le service se relance automatiquement à chaque ouverture de session.

Aperçu sans rien modifier : `./install.sh --dry-run`

## Vérifier que ça marche

```bash
# État du service
systemctl --user status kwin-watchdog

# Journal en direct
journalctl --user -u kwin-watchdog -f

# Test : tuer KWin, il doit revenir en 1 à 3 secondes
pkill -x kwin_x11
```

## Réglages

Deux variables dans `~/.config/systemd/user/kwin-watchdog.service` :

| Variable | Rôle | Défaut |
|---|---|---|
| `KWIN_WATCHDOG_INTERVAL` | délai entre deux vérifications | 2 s |
| `KWIN_WATCHDOG_COOLDOWN` | pause après un relancement | 5 s |

Après modification : `systemctl --user daemon-reload && systemctl --user restart kwin-watchdog`

## Désinstallation

```bash
./uninstall.sh
```

## Limites à connaître

- **Session Wayland** : sous Wayland, KWin *est* le serveur d'affichage. S'il
  plante, toute la session tombe avec lui et aucun watchdog utilisateur ne peut
  la rattraper. L'override `Restart=always` est quand même posé sur
  `plasma-kwin_wayland.service` pour couvrir les cas où la session survit. Pour une
  vraie résilience, utilisez une session **Plasma (X11)** à l'écran de connexion.
- **Pas de systemd ?** Le service ne s'installera pas ; vous pouvez tout de même
  lancer `kwin-watchdog.sh &` depuis le démarrage automatique de Plasma
  (Configuration du système → Démarrage et arrêt → Démarrage automatique).
- Si KWin plante **en boucle** (pilote graphique, effet défectueux), le watchdog le
  relancera indéfiniment ; regardez `journalctl --user -u plasma-kwin_x11` pour la cause
  réelle, ou désactivez le compositing (`Alt+Maj+F12`).
