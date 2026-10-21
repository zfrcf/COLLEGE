"""Téléchargements : Paper, Geyser, Floodgate, plugins Modrinth, Java (Adoptium)."""

from __future__ import annotations

import hashlib
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import __version__

USER_AGENT = f"mcsl/{__version__} (launcher Minecraft Switch local)"

API_PAPER = "https://fill.papermc.io/v3/projects/paper"
API_GEYSER = "https://download.geysermc.org/v2/projects"
API_MODRINTH = "https://api.modrinth.com/v2"
API_ADOPTIUM = "https://api.adoptium.net/v3/assets/latest/{majeure}/hotspot"


class ErreurTelechargement(Exception):
    pass


def _requete(url: str, timeout: int = 30) -> urllib.request.Request:
    return urllib.request.Request(url, headers={"User-Agent": USER_AGENT})


def json_depuis(url: str) -> object:
    try:
        with urllib.request.urlopen(_requete(url), timeout=30) as reponse:
            return json.loads(reponse.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise ErreurTelechargement(f"HTTP {exc.code} sur {url}") from exc
    except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
        raise ErreurTelechargement(f"Impossible de lire {url} : {exc}") from exc


def telecharger(url: str, destination: Path, sha256: str | None = None, label: str = "") -> Path:
    """Télécharge `url` vers `destination` avec une barre de progression simple."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporaire = destination.with_suffix(destination.suffix + ".part")
    label = label or destination.name
    empreinte = hashlib.sha256()
    try:
        with urllib.request.urlopen(_requete(url), timeout=60) as reponse, open(temporaire, "wb") as sortie:
            total = int(reponse.headers.get("Content-Length") or 0)
            lu = 0
            while True:
                bloc = reponse.read(1024 * 256)
                if not bloc:
                    break
                sortie.write(bloc)
                empreinte.update(bloc)
                lu += len(bloc)
                _afficher_progression(label, lu, total)
    except urllib.error.HTTPError as exc:
        temporaire.unlink(missing_ok=True)
        raise ErreurTelechargement(f"HTTP {exc.code} sur {url}") from exc
    except (urllib.error.URLError, OSError) as exc:
        temporaire.unlink(missing_ok=True)
        raise ErreurTelechargement(f"Téléchargement de {label} échoué : {exc}") from exc
    sys.stdout.write("\n")

    if sha256 and empreinte.hexdigest().lower() != sha256.lower():
        temporaire.unlink(missing_ok=True)
        raise ErreurTelechargement(f"Empreinte SHA-256 invalide pour {label}")
    temporaire.replace(destination)
    return destination


def _afficher_progression(label: str, lu: int, total: int) -> None:
    if total:
        pourcent = min(100, lu * 100 // total)
        barre = "#" * (pourcent // 4) + "-" * (25 - pourcent // 4)
        sys.stdout.write(f"\r  {label:<40} [{barre}] {pourcent:3d}% ({lu / 1_000_000:.1f} Mo)")
    else:
        sys.stdout.write(f"\r  {label:<40} {lu / 1_000_000:.1f} Mo")
    sys.stdout.flush()


# ---------------------------------------------------------------- Paper


def _est_version_stable(version: str) -> bool:
    return not any(mot in version for mot in ("-rc", "-pre", "snapshot"))


def resoudre_version_paper(version_demandee: str) -> str:
    """Retourne la version Paper à utiliser ("latest" → dernière stable)."""
    donnees = json_depuis(API_PAPER)
    familles: dict = donnees["versions"]
    toutes = [v for groupe in familles.values() for v in groupe]
    if version_demandee != "latest":
        if version_demandee not in toutes:
            raise ErreurTelechargement(
                f"La version {version_demandee} n'existe pas chez Paper. "
                f"Dernières disponibles : {', '.join(v for v in toutes[:6])}"
            )
        return version_demandee
    for version in toutes:  # l'API liste les versions de la plus récente à la plus ancienne
        if _est_version_stable(version):
            return version
    return toutes[0]


def info_build_paper(version: str) -> dict:
    """Retourne {version, build, url, sha256, nom} du dernier build Paper de `version`."""
    donnees = json_depuis(f"{API_PAPER}/versions/{version}/builds/latest")
    fichier = donnees["downloads"]["server:default"]
    return {
        "version": version,
        "build": donnees["id"],
        "canal": donnees.get("channel", ""),
        "nom": fichier["name"],
        "url": fichier["url"],
        "sha256": fichier.get("checksums", {}).get("sha256"),
    }


# ---------------------------------------------------------------- Geyser / Floodgate


def info_build_geyser(projet: str) -> dict:
    """`projet` = "geyser" ou "floodgate". Retourne l'URL du build spigot le plus récent."""
    url_builds = f"{API_GEYSER}/{projet}/versions/latest/builds/latest"
    donnees = json_depuis(url_builds)
    return {
        "projet": projet,
        "version": donnees.get("version", "?"),
        "build": donnees.get("build", "?"),
        "url": f"{url_builds}/downloads/spigot",
        "sha256": donnees.get("downloads", {}).get("spigot", {}).get("sha256"),
    }


# ---------------------------------------------------------------- Modrinth


def info_plugin_modrinth(slug: str, version_minecraft: str) -> dict:
    """Trouve le dernier fichier Paper du projet Modrinth `slug` compatible avec `version_minecraft`.

    Si aucune version ne cible exactement `version_minecraft`, on retombe sur la
    dernière version Paper disponible en le signalant.
    """
    base = f"{API_MODRINTH}/project/{urllib.parse.quote(slug)}/version"
    filtre_loaders = urllib.parse.quote('["paper","spigot","bukkit"]')
    filtre_versions = urllib.parse.quote(f'["{version_minecraft}"]')
    versions = json_depuis(f"{base}?loaders={filtre_loaders}&game_versions={filtre_versions}")
    compatible = True
    if not versions:
        versions = json_depuis(f"{base}?loaders={filtre_loaders}")
        compatible = False
    if not versions:
        raise ErreurTelechargement(f"Aucune version Paper/Spigot trouvée sur Modrinth pour '{slug}'")
    version = versions[0]
    fichiers = version["files"]
    fichier = next((f for f in fichiers if f.get("primary")), fichiers[0])
    return {
        "slug": slug,
        "nom": version["name"],
        "numero": version["version_number"],
        "fichier": fichier["filename"],
        "url": fichier["url"],
        "sha512": fichier.get("hashes", {}).get("sha512"),
        "compatible": compatible,
        "versions_jeu": version.get("game_versions", []),
    }


# ---------------------------------------------------------------- Java (Adoptium Temurin)


def info_java_adoptium(majeure: int, os_nom: str, archi: str) -> dict:
    url = f"{API_ADOPTIUM.format(majeure=majeure)}?os={os_nom}&architecture={archi}&image_type=jre"
    donnees = json_depuis(url)
    if not donnees:
        raise ErreurTelechargement(f"Aucun JRE Temurin {majeure} pour {os_nom}/{archi}")
    paquet = donnees[0]["binary"]["package"]
    return {
        "url": paquet["link"],
        "nom": paquet["name"],
        "sha256": paquet.get("checksum"),
        "version": donnees[0].get("release_name", str(majeure)),
    }
