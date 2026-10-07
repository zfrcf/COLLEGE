# Réparer le bureau Ubuntu (sans sudo)

Écran noir, plus de dock, touche Super morte, pas de terminal → 3 façons de lancer l'outil :

| Fichier | Comment le lancer |
|---|---|
| `Reparer-bureau.exe` | Double-clic avec **Wine**, ou Steam → *Ajouter un jeu non-Steam* (Proton) |
| `reparer-bureau.desktop` | Steam → *Ajouter un jeu non-Steam*, ou à copier dans `~/.local/share/applications/` |
| `bureau.sh` | Console texte : **Ctrl+Alt+F3**, se connecter, puis `bash bureau.sh` |

Une fois lancé : **Réparation rapide** → **Relancer le bureau**.
Ensuite l'outil s'installe et reste accessible par **Ctrl+Alt+R** et dans le menu des applications.

Rien n'est supprimé : les réglages modifiés sont sauvegardés dans
`~/.local/share/reparer-bureau/` et restaurables depuis le menu.

Reconstruire l'exe après modification de `bureau.sh` : `exe/construire.sh`.
