"""Détection de Java et, si besoin, installation locale d'un JRE Temurin.

La version de Java requise dépend de la version de Minecraft :
  - 26.1 et plus récent  → Java 25
  - 1.20.5 → 1.21.x      → Java 21
"""

from __future__ import annotations

import os
import platform
import re
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

from . import telechargement
from .config import RACINE

DOSSIER_RUNTIME = RACINE / "runtime"


def java_requis(version_minecraft: str) -> int:
    """Version majeure de Java nécessaire pour `version_minecraft` (ex. "26.3" → 25)."""
    correspondance = re.match(r"(\d+)\.(\d+)", version_minecraft)
    if not correspondance:
        return 25
    majeure, mineure = int(correspondance.group(1)), int(correspondance.group(2))
    if majeure >= 26:
        return 25
    if majeure == 1 and mineure < 17:
        return 17
    return 21


def version_java(executable: str | Path) -> int | None:
    """Retourne la version majeure de `executable` (ex. 21) ou None s'il ne répond pas."""
    try:
        resultat = subprocess.run(
            [str(executable), "-version"], capture_output=True, text=True, timeout=20
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    sortie = resultat.stderr + resultat.stdout
    correspondance = re.search(r'version "(\d+)(?:\.(\d+))?', sortie)
    if not correspondance:
        return None
    majeure = int(correspondance.group(1))
    # Les vieux JDK s'annoncent "1.8" → majeure = 8
    if majeure == 1 and correspondance.group(2):
        majeure = int(correspondance.group(2))
    return majeure


def _candidats_locaux() -> list[Path]:
    nom = "java.exe" if os.name == "nt" else "java"
    if not DOSSIER_RUNTIME.exists():
        return []
    return sorted(DOSSIER_RUNTIME.glob(f"**/bin/{nom}"), reverse=True)


def trouver_java(minimum: int, chemin_config: str = "") -> Path | None:
    """Cherche un Java >= `minimum` : config, runtime local, PATH, JAVA_HOME."""
    candidats: list[Path] = []
    if chemin_config:
        candidats.append(Path(chemin_config))
    candidats.extend(_candidats_locaux())
    java_home = os.environ.get("JAVA_HOME")
    if java_home:
        candidats.append(Path(java_home) / "bin" / ("java.exe" if os.name == "nt" else "java"))
    dans_path = shutil.which("java")
    if dans_path:
        candidats.append(Path(dans_path))

    for candidat in candidats:
        if candidat.exists():
            version = version_java(candidat)
            if version and version >= minimum:
                return candidat
    return None


def _cible_adoptium() -> tuple[str, str]:
    systeme = platform.system().lower()
    os_nom = {"windows": "windows", "linux": "linux", "darwin": "mac"}.get(systeme)
    if not os_nom:
        raise telechargement.ErreurTelechargement(f"Système non pris en charge : {systeme}")
    machine = platform.machine().lower()
    archi = "aarch64" if machine in ("arm64", "aarch64") else "x64"
    return os_nom, archi


def installer_java(majeure: int) -> Path:
    """Télécharge un JRE Temurin `majeure` dans runtime/ et retourne le chemin de java."""
    os_nom, archi = _cible_adoptium()
    print(f"[java] Aucun Java {majeure}+ trouvé : installation d'un JRE Temurin {majeure} ({os_nom}/{archi})…")
    info = telechargement.info_java_adoptium(majeure, os_nom, archi)
    DOSSIER_RUNTIME.mkdir(parents=True, exist_ok=True)
    archive = DOSSIER_RUNTIME / info["nom"]
    telechargement.telecharger(info["url"], archive, sha256=info["sha256"], label=f"JRE Temurin {majeure}")

    print("[java] Extraction…")
    if archive.suffix == ".zip":
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(DOSSIER_RUNTIME)
    else:
        with tarfile.open(archive) as tf:
            tf.extractall(DOSSIER_RUNTIME, filter="data")
    archive.unlink(missing_ok=True)

    for candidat in _candidats_locaux():
        if os.name != "nt":
            candidat.chmod(candidat.stat().st_mode | 0o111)
        version = version_java(candidat)
        if version and version >= majeure:
            print(f"[java] JRE installé : {candidat}")
            return candidat
    raise telechargement.ErreurTelechargement("Le JRE téléchargé ne contient pas d'exécutable java utilisable")


def obtenir_java(version_minecraft: str, chemin_config: str = "") -> Path:
    """Retourne un Java adapté à `version_minecraft`, en l'installant localement si nécessaire."""
    minimum = java_requis(version_minecraft)
    java = trouver_java(minimum, chemin_config)
    if java:
        return java
    return installer_java(minimum)
