"""Chargement / sauvegarde de la configuration du launcher (config.json)."""

from __future__ import annotations

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
FICHIER_CONFIG = RACINE / "config.json"

# Valeurs par défaut : tout est modifiable dans config.json ou via le menu.
CONFIG_DEFAUT: dict = {
    # "latest" = dernière version stable de Paper, sinon ex. "26.3" ou "1.21.11"
    "version_minecraft": "latest",
    # Dossier où vit le serveur (relatif à la racine du launcher)
    "dossier_serveur": "serveur",
    # Mémoire allouée au serveur (Mo)
    "ram_mo": 3072,
    # Port Java (TCP), port Bedrock / Geyser (UDP RakNet + TCP signalisation NetherNet)
    # et port NetherNet / WebRTC (UDP) pour les clients Bedrock 26.40+.
    "port_java": 25565,
    "port_bedrock": 19132,
    "port_nethernet": 19133,
    "motd": "Serveur local Switch",
    # Mode de jeu par défaut et difficulté
    "mode_jeu": "survival",
    "difficulte": "normal",
    # Plugins Modrinth (slug du projet). Geyser et Floodgate sont toujours installés.
    "plugins": ["worldedit"],
    # Chemin vers java (vide = détection automatique / installation locale)
    "java": "",
    # Chemin vers le launcher Minecraft Java (vide = détection automatique)
    "launcher_minecraft": "",
    # Lancer Minecraft Java en même temps que le serveur avec l'option "Jouer"
    "lancer_minecraft_avec_serveur": True,
}


def charger() -> dict:
    """Retourne la configuration, complétée par les valeurs par défaut manquantes."""
    config = dict(CONFIG_DEFAUT)
    if FICHIER_CONFIG.exists():
        try:
            config.update(json.loads(FICHIER_CONFIG.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"[config] config.json illisible ({exc}), valeurs par défaut utilisées.")
    else:
        sauvegarder(config)
    return config


def sauvegarder(config: dict) -> None:
    FICHIER_CONFIG.write_text(
        json.dumps(config, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def dossier_serveur(config: dict) -> Path:
    chemin = Path(config["dossier_serveur"])
    if not chemin.is_absolute():
        chemin = RACINE / chemin
    return chemin
