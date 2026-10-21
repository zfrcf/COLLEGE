"""Gestion des plugins du serveur : Geyser, Floodgate (obligatoires) et plugins Modrinth."""

from __future__ import annotations

import json
from pathlib import Path

from . import telechargement
from .config import dossier_serveur

# Plugins toujours installés : c'est eux qui permettent à la Switch de se connecter.
PLUGINS_OBLIGATOIRES = ("geyser", "floodgate")

# Installés quand "accepter_toutes_versions_java" est activé : clients Java plus récents
# (ViaVersion) ou plus anciens (ViaBackwards) que le serveur.
PLUGINS_COMPATIBILITE = ("viaversion", "viabackwards")

# Quelques slugs Modrinth utiles, proposés dans le menu.
PLUGINS_SUGGERES = {
    "worldedit": "WorldEdit – édition de monde (//set, //copy, baguette…)",
    "fastasyncworldedit": "FastAsyncWorldEdit – WorldEdit plus rapide (remplace worldedit)",
    "viaversion": "ViaVersion – accepte des clients Java d'autres versions",
    "luckperms": "LuckPerms – gestion des permissions",
    "essentialsx": "EssentialsX – /home, /tp, /kit, économie…",
    "chunky": "Chunky – pré-génération du monde",
    "simple-voice-chat": "Simple Voice Chat – chat vocal (Java uniquement)",
}


def dossier_plugins(config: dict) -> Path:
    return dossier_serveur(config) / "plugins"


def fichier_etat(config: dict) -> Path:
    return dossier_plugins(config) / ".mcsl-plugins.json"


def lire_etat(config: dict) -> dict:
    chemin = fichier_etat(config)
    if chemin.exists():
        try:
            return json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def ecrire_etat(config: dict, etat: dict) -> None:
    fichier_etat(config).write_text(json.dumps(etat, indent=2, ensure_ascii=False), encoding="utf-8")


def _supprimer_ancien(config: dict, etat: dict, cle: str) -> None:
    ancien = etat.get(cle, {}).get("fichier")
    if ancien:
        (dossier_plugins(config) / ancien).unlink(missing_ok=True)


def installer_geyser_floodgate(config: dict) -> None:
    dossier = dossier_plugins(config)
    dossier.mkdir(parents=True, exist_ok=True)
    etat = lire_etat(config)
    for projet in PLUGINS_OBLIGATOIRES:
        info = telechargement.info_build_geyser(projet)
        nom_fichier = f"{projet.capitalize()}-Spigot.jar"
        identifiant = f"{info['version']}-{info['build']}"
        if etat.get(projet, {}).get("id") == identifiant and (dossier / nom_fichier).exists():
            print(f"  {projet.capitalize()} {identifiant} déjà à jour.")
            continue
        _supprimer_ancien(config, etat, projet)
        telechargement.telecharger(
            info["url"], dossier / nom_fichier, sha256=info["sha256"],
            label=f"{projet.capitalize()} {info['version']} build {info['build']}",
        )
        etat[projet] = {"id": identifiant, "fichier": nom_fichier}
        ecrire_etat(config, etat)


def installer_plugins_modrinth(config: dict, version_minecraft: str) -> None:
    dossier = dossier_plugins(config)
    dossier.mkdir(parents=True, exist_ok=True)
    etat = lire_etat(config)
    voulus = plugins_voulus(config)

    # Retire les plugins qui ne sont plus dans la config
    for cle in list(etat):
        if cle not in PLUGINS_OBLIGATOIRES and cle not in voulus:
            print(f"  Suppression de {cle} (retiré de la configuration).")
            _supprimer_ancien(config, etat, cle)
            del etat[cle]
    ecrire_etat(config, etat)

    for slug in voulus:
        try:
            info = telechargement.info_plugin_modrinth(slug, version_minecraft)
        except telechargement.ErreurTelechargement as exc:
            print(f"  ! {slug} : {exc}")
            continue
        if not info["compatible"]:
            print(
                f"  ! {slug} : aucune version annoncée pour Minecraft {version_minecraft}, "
                f"installation de {info['nom']} (cible {', '.join(info['versions_jeu'][-3:])}) — à tester."
            )
        if etat.get(slug, {}).get("id") == info["numero"] and (dossier / info["fichier"]).exists():
            print(f"  {slug} {info['numero']} déjà à jour.")
            continue
        _supprimer_ancien(config, etat, slug)
        telechargement.telecharger(info["url"], dossier / info["fichier"], label=f"{slug} {info['numero']}")
        etat[slug] = {"id": info["numero"], "fichier": info["fichier"]}
        ecrire_etat(config, etat)


def plugins_voulus(config: dict) -> list[str]:
    """Slugs Modrinth à installer : ceux de la config + la compatibilité de versions si activée."""
    voulus = [slug.strip().lower() for slug in config.get("plugins", []) if slug.strip()]
    if config.get("accepter_toutes_versions_java", True):
        voulus += [slug for slug in PLUGINS_COMPATIBILITE if slug not in voulus]
    return voulus


def lister_installes(config: dict) -> list[tuple[str, str]]:
    etat = lire_etat(config)
    return [(cle, valeur.get("id", "?")) for cle, valeur in sorted(etat.items())]
