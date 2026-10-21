"""Installation, configuration et exécution du serveur Paper + Geyser."""

from __future__ import annotations

import json
import os
import re
from collections import deque
import shlex
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

from . import java as java_mod
from . import plugins, telechargement
from .config import dossier_serveur

NOM_JAR = "paper.jar"
FICHIER_ETAT = ".mcsl-serveur.json"
MARQUEUR_DEMARRE = re.compile(r"Done \([\d.]+s\)!")

# Drapeaux JVM recommandés (Aikar) pour un petit serveur local.
DRAPEAUX_JVM = [
    "-XX:+UseG1GC", "-XX:+ParallelRefProcEnabled", "-XX:MaxGCPauseMillis=200",
    "-XX:+UnlockExperimentalVMOptions", "-XX:+DisableExplicitGC", "-XX:+AlwaysPreTouch",
    "-XX:G1NewSizePercent=30", "-XX:G1MaxNewSizePercent=40", "-XX:G1HeapRegionSize=8M",
    "-XX:G1ReservePercent=20", "-XX:G1HeapWastePercent=5", "-XX:G1MixedGCCountTarget=4",
    "-XX:InitiatingHeapOccupancyPercent=15", "-XX:G1MixedGCLiveThresholdPercent=90",
    "-XX:G1RSetUpdatingPauseTimePercent=5", "-XX:SurvivorRatio=32", "-XX:+PerfDisableSharedMem",
    "-XX:MaxTenuringThreshold=1", "-Dusing.aikars.flags=https://mcflags.emc.gs",
    "-Daikars.new.flags=true",
]


def lire_etat(config: dict) -> dict:
    chemin = dossier_serveur(config) / FICHIER_ETAT
    if chemin.exists():
        try:
            return json.loads(chemin.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def ecrire_etat(config: dict, etat: dict) -> None:
    (dossier_serveur(config) / FICHIER_ETAT).write_text(
        json.dumps(etat, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def est_installe(config: dict) -> bool:
    return (dossier_serveur(config) / NOM_JAR).exists()


# ---------------------------------------------------------------- Installation


def installer(config: dict) -> dict:
    """Installe ou met à jour Paper, Geyser, Floodgate et les plugins. Retourne l'état."""
    dossier = dossier_serveur(config)
    dossier.mkdir(parents=True, exist_ok=True)

    print("[1/4] Version du serveur…")
    version = telechargement.resoudre_version_paper(config["version_minecraft"])
    print(f"  Minecraft {version} → Java {java_mod.java_requis(version)} requis")
    java = java_mod.obtenir_java(version, config.get("java", ""))
    print(f"  Java utilisé : {java} (version {java_mod.version_java(java)})")

    print("[2/4] Serveur Paper…")
    info = telechargement.info_build_paper(version)
    etat = lire_etat(config)
    identifiant = f"{info['version']}-{info['build']}"
    if etat.get("paper") == identifiant and (dossier / NOM_JAR).exists():
        print(f"  Paper {identifiant} déjà à jour.")
    else:
        telechargement.telecharger(
            info["url"], dossier / NOM_JAR, sha256=info["sha256"],
            label=f"Paper {info['version']} build {info['build']}",
        )
        etat["paper"] = identifiant
        etat["premiere_initialisation_faite"] = False
    etat["version_minecraft"] = version
    ecrire_etat(config, etat)

    print("[3/4] Geyser + Floodgate (pont Bedrock ↔ Java)…")
    plugins.installer_geyser_floodgate(config)

    print("[4/4] Plugins…")
    plugins.installer_plugins_modrinth(config, version)

    ecrire_fichiers_de_base(config)
    if not etat.get("premiere_initialisation_faite"):
        print("\nPremier démarrage pour générer les fichiers de configuration (1 à 3 minutes)…")
        premiere_initialisation(config, java)
        etat["premiere_initialisation_faite"] = True
        ecrire_etat(config, etat)
    configurer_geyser(config)
    print("\nInstallation terminée.")
    return etat


# ---------------------------------------------------------------- Fichiers de configuration


def _lire_properties(chemin: Path) -> dict[str, str]:
    valeurs: dict[str, str] = {}
    if chemin.exists():
        for ligne in chemin.read_text(encoding="utf-8").splitlines():
            if "=" in ligne and not ligne.lstrip().startswith("#"):
                cle, _, valeur = ligne.partition("=")
                valeurs[cle.strip()] = valeur.strip()
    return valeurs


def ecrire_fichiers_de_base(config: dict) -> None:
    """eula.txt + server.properties (on conserve les réglages déjà présents)."""
    dossier = dossier_serveur(config)
    (dossier / "eula.txt").write_text(
        "# En lançant ce serveur, vous acceptez l'EULA Minecraft :\n"
        "# https://aka.ms/MinecraftEULA\neula=true\n", encoding="utf-8",
    )
    chemin = dossier / "server.properties"
    valeurs = _lire_properties(chemin)
    valeurs.update({
        "server-port": str(config["port_java"]),
        "motd": config["motd"],
        "gamemode": config["mode_jeu"],
        "difficulty": config["difficulte"],
        # online-mode reste activé : les joueurs Java sont authentifiés, les joueurs
        # Switch passent par Floodgate (pas besoin de compte Java).
        "online-mode": "true",
        # Évite les déconnexions "chat non signé" côté Bedrock.
        "enforce-secure-profile": "false",
        # Paper 26.x active la whitelist par défaut : sur un serveur local, tout le
        # monde doit pouvoir entrer (sinon "You are not whitelisted on this server!").
        "white-list": "false",
        "enforce-whitelist": "false",
        "max-players": valeurs.get("max-players", "8"),
        "view-distance": valeurs.get("view-distance", "10"),
        "spawn-protection": valeurs.get("spawn-protection", "0"),
    })
    lignes = ["# Généré par MCSL — modifiable, les clés ci-dessus sont réappliquées à chaque installation"]
    lignes += [f"{cle}={valeur}" for cle, valeur in sorted(valeurs.items())]
    chemin.write_text("\n".join(lignes) + "\n", encoding="utf-8")


def _remplacer_cle_yaml(texte: str, cle: str, valeur: str, indentation: str = "  ") -> str:
    """Remplace `cle: ...` (à l'indentation donnée) dans un YAML simple, sans dépendance externe."""
    motif = re.compile(rf"^({re.escape(indentation)}{re.escape(cle)}:)\s*.*$", re.MULTILINE)
    if motif.search(texte):
        return motif.sub(rf"\g<1> {valeur}", texte, count=1)
    return texte


def configurer_geyser(config: dict) -> bool:
    """Force ports Bedrock, transport NetherNet + RakNet, auth Floodgate et nom dans la config Geyser."""
    chemin = dossier_serveur(config) / "plugins" / "Geyser-Spigot" / "config.yml"
    if not chemin.exists():
        print("[geyser] config.yml absent (sera créé au premier démarrage).")
        return False
    texte = chemin.read_text(encoding="utf-8")
    original = texte
    nom = json.dumps(config["motd"], ensure_ascii=False)
    # Section "bedrock"
    texte = _remplacer_cle_yaml(texte, "port", str(config["port_bedrock"]))
    texte = _remplacer_cle_yaml(texte, "webrtc-port", str(config["port_nethernet"]))
    # "both" = NetherNet (obligatoire pour Bedrock 26.60+, dont la Switch) + RakNet (anciens clients,
    # découverte dans l'onglet Amis). Chacun a besoin de son propre port UDP.
    texte = _remplacer_cle_yaml(texte, "transport", "both")
    # Section "java"
    texte = _remplacer_cle_yaml(texte, "auth-type", "floodgate")
    # Sections "motd" et "gameplay"
    texte = _remplacer_cle_yaml(texte, "primary-motd", nom)
    texte = _remplacer_cle_yaml(texte, "server-name", nom)
    if texte != original:
        chemin.write_text(texte, encoding="utf-8")
        print(f"[geyser] Configuration appliquée : RakNet UDP {config['port_bedrock']}, "
              f"NetherNet TCP {config['port_bedrock']} + UDP {config['port_nethernet']}, auth floodgate.")
    return True


# ---------------------------------------------------------------- Exécution


def _commande(config: dict, java: Path) -> list[str]:
    ram = int(config["ram_mo"])
    return [str(java), f"-Xms{ram}M", f"-Xmx{ram}M", *DRAPEAUX_JVM, "-jar", NOM_JAR, "--nogui"]


def _lancer_processus(config: dict, java: Path, stdout) -> subprocess.Popen:
    return subprocess.Popen(
        _commande(config, java),
        cwd=dossier_serveur(config),
        stdin=subprocess.PIPE,
        stdout=stdout,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
    )


def envoyer_commande(processus: subprocess.Popen, commande: str) -> None:
    if processus.poll() is None and processus.stdin:
        try:
            processus.stdin.write(commande.rstrip("\n") + "\n")
            processus.stdin.flush()
        except (OSError, ValueError):
            pass


def arreter(processus: subprocess.Popen, delai: int = 60) -> None:
    """Arrêt propre (commande `stop`) puis forcé si le serveur ne répond plus."""
    if processus.poll() is not None:
        return
    print("\n[serveur] Arrêt en cours (sauvegarde du monde)…")
    envoyer_commande(processus, "stop")
    try:
        processus.wait(timeout=delai)
    except subprocess.TimeoutExpired:
        print("[serveur] Pas de réponse, arrêt forcé.")
        processus.kill()
        processus.wait()


def premiere_initialisation(config: dict, java: Path) -> None:
    """Démarre le serveur jusqu'à "Done" puis l'arrête : génère toutes les configs (dont Geyser)."""
    processus = _lancer_processus(config, java, subprocess.PIPE)
    demarre = False
    dernieres_lignes: deque[str] = deque(maxlen=15)
    try:
        assert processus.stdout is not None
        for ligne in processus.stdout:
            ligne = ligne.rstrip()
            dernieres_lignes.append(ligne)
            if any(mot in ligne for mot in ("Downloading", "Applying patches", "Starting minecraft server",
                                            "Preparing spawn area", "Done", "ERROR", "Geyser", "floodgate")):
                print("  " + ligne[-110:])
            if MARQUEUR_DEMARRE.search(ligne):
                demarre = True
                envoyer_commande(processus, "stop")
        processus.wait(timeout=120)
    except (KeyboardInterrupt, subprocess.TimeoutExpired):
        processus.kill()
        processus.wait()
        raise
    if not demarre:
        print("\n  Dernières lignes du serveur :")
        for ligne in dernieres_lignes:
            print("  | " + ligne[-150:])
        raise RuntimeError(
            "Le serveur ne s'est pas lancé correctement. Journal complet : "
            f"{dossier_serveur(config) / 'logs' / 'latest.log'}"
        )


def _relais_clavier(processus: subprocess.Popen) -> None:
    """Transmet ce que tape l'utilisateur à la console du serveur."""
    try:
        for ligne in sys.stdin:
            if processus.poll() is not None:
                break
            envoyer_commande(processus, ligne)
    except (OSError, ValueError):
        pass


def demarrer(config: dict, au_demarrage=None) -> int:
    """Lance le serveur en avant-plan (console interactive). Retourne le code de sortie."""
    if not est_installe(config):
        raise RuntimeError("Le serveur n'est pas installé : lancez d'abord l'installation.")
    version = lire_etat(config).get("version_minecraft", config["version_minecraft"])
    java = java_mod.obtenir_java(version, config.get("java", ""))
    ecrire_fichiers_de_base(config)
    configurer_geyser(config)

    print(f"[serveur] Démarrage ({config['ram_mo']} Mo de RAM). Tapez 'stop' pour arrêter.\n")
    processus = _lancer_processus(config, java, subprocess.PIPE)
    threading.Thread(target=_relais_clavier, args=(processus,), daemon=True).start()
    try:
        assert processus.stdout is not None
        for ligne in processus.stdout:
            sys.stdout.write(ligne)
            sys.stdout.flush()
            if au_demarrage and MARQUEUR_DEMARRE.search(ligne):
                au_demarrage()
                au_demarrage = None
        return processus.wait()
    except KeyboardInterrupt:
        arreter(processus)
        return processus.returncode or 0


# ---------------------------------------------------------------- Launcher Minecraft Java


def _flatpak_installe(identifiant: str) -> bool:
    if not shutil.which("flatpak"):
        return False
    try:
        resultat = subprocess.run(["flatpak", "info", identifiant], capture_output=True, timeout=15)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return resultat.returncode == 0


def _candidats_launcher_minecraft() -> list[list[str]]:
    """Commandes possibles pour ouvrir le launcher Minecraft Java, par ordre de préférence."""
    if os.name == "nt":
        local = Path(os.environ.get("LOCALAPPDATA", ""))
        programmes = Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"))
        chemins = [
            local / "Programs" / "Minecraft Launcher" / "MinecraftLauncher.exe",
            programmes / "Minecraft Launcher" / "MinecraftLauncher.exe",
            Path(r"C:\XboxGames\Minecraft Launcher\Content\Minecraft.exe"),
        ]
        return [[str(c)] for c in chemins if c.exists()]
    if sys.platform == "darwin":
        chemin = Path("/Applications/Minecraft.app/Contents/MacOS/launcher")
        return [[str(chemin)]] if chemin.exists() else []

    # Linux (Ubuntu…) : paquet .deb officiel, app Modrinth, Flatpak, Snap, launchers alternatifs.
    candidats: list[list[str]] = []
    for executable in ("minecraft-launcher", "modrinth-app", "ModrinthApp", "prismlauncher", "multimc", "hmcl"):
        chemin = shutil.which(executable)
        if chemin:
            candidats.append([chemin])
    for chemin in ("/opt/minecraft-launcher/minecraft-launcher", "/snap/bin/mc-installer"):
        if Path(chemin).exists():
            candidats.append([chemin])
    for identifiant in ("com.mojang.Minecraft", "com.modrinth.ModrinthApp", "org.prismlauncher.PrismLauncher"):
        if _flatpak_installe(identifiant):
            candidats.append(["flatpak", "run", identifiant])
    # AppImage (Modrinth, Prism…) rangée dans les dossiers habituels
    maison = Path.home()
    for dossier in (maison / "Applications", maison / "Apps", maison / ".local" / "bin", maison / "Downloads",
                    maison / "Téléchargements", maison / "Bureau", maison / "Desktop"):
        for appimage in sorted(dossier.glob("*[Mm]odrinth*.AppImage")) + sorted(dossier.glob("*[Pp]rism*.AppImage")):
            if os.access(appimage, os.X_OK):
                candidats.append([str(appimage)])
    return candidats


def lancer_minecraft(config: dict) -> bool:
    """Ouvre le launcher Minecraft Java (sans attendre). Retourne False s'il est introuvable."""
    chemin_config = config.get("launcher_minecraft", "")
    if chemin_config:
        candidats = [shlex.split(chemin_config)] if " " in chemin_config else [[chemin_config]]
    else:
        candidats = _candidats_launcher_minecraft()
    for commande in candidats:
        executable = commande[0]
        if not (Path(executable).exists() or shutil.which(executable)):
            continue
        print(f"[minecraft] Ouverture de {' '.join(commande)}")
        try:
            subprocess.Popen(commande, stdin=subprocess.DEVNULL,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True
        except OSError as exc:
            print(f"[minecraft] Échec ({exc}), essai suivant…")
    print("[minecraft] Launcher Minecraft Java introuvable : renseignez 'launcher_minecraft' dans config.json "
          "(ex. \"flatpak run com.mojang.Minecraft\") ou lancez Minecraft à la main "
          "(Multijoueur > Connexion directe > localhost).")
    return False


def attendre_fin_processus(processus: subprocess.Popen) -> None:
    while processus.poll() is None:
        time.sleep(1)
