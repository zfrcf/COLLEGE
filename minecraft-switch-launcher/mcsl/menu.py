"""Menu console en français."""

from __future__ import annotations

import sys

from . import __version__, config as config_mod, plugins, reseau, serveur, telechargement


def _lire(invite: str, defaut: str = "") -> str:
    try:
        valeur = input(invite).strip()
    except EOFError:
        return defaut
    return valeur or defaut


def _entete(config: dict) -> None:
    installe = serveur.est_installe(config)
    etat = serveur.lire_etat(config)
    version = etat.get("version_minecraft", config["version_minecraft"])
    print("\n" + "=" * 60)
    print(f"  MCSL – Launcher serveur Minecraft local pour Switch  v{__version__}")
    print("=" * 60)
    print(f"  Serveur : {'installé (Paper ' + version + ')' if installe else 'non installé'}")
    print(f"  IP locale : {reseau.ip_locale()}   Bedrock : {config['port_bedrock']} (+{config['port_nethernet']})"
          f"   Java : {config['port_java']}")
    print(f"  Plugins : {', '.join(config['plugins']) or 'aucun'} (+ Geyser, Floodgate)")
    print("-" * 60)


def action_installer(config: dict) -> None:
    try:
        serveur.installer(config)
    except (telechargement.ErreurTelechargement, RuntimeError) as exc:
        print(f"\n!! Installation interrompue : {exc}")


def action_jouer(config: dict) -> None:
    if not serveur.est_installe(config):
        print("Le serveur n'est pas encore installé : installation d'abord.")
        action_installer(config)
        if not serveur.est_installe(config):
            return
    for nom, port, libre in reseau.ports_a_verifier(config):
        if not libre:
            print(f"!! Le port {nom} {port} est déjà utilisé (un autre serveur / Minecraft Bedrock ouvert ?).")
            if _lire("Continuer quand même ? [o/N] ", "n").lower() != "o":
                return

    def au_demarrage() -> None:
        print(reseau.instructions_switch(config))
        print("[serveur] Prêt ! Côté PC (Java) : Multijoueur > Connexion directe > localhost\n")
        if config.get("lancer_minecraft_avec_serveur"):
            serveur.lancer_minecraft(config)

    try:
        code = serveur.demarrer(config, au_demarrage=au_demarrage)
    except (telechargement.ErreurTelechargement, RuntimeError) as exc:
        print(f"\n!! {exc}")
        return
    print(f"\n[serveur] Arrêté (code {code}).")


def action_plugins(config: dict) -> None:
    while True:
        print("\n--- Plugins ---")
        installes = plugins.lister_installes(config)
        if installes:
            for nom, version in installes:
                print(f"  • {nom} ({version})")
        else:
            print("  (aucun plugin installé pour l'instant)")
        print(f"\n  Souhaités dans config.json : {', '.join(config['plugins']) or 'aucun'}")
        print("\n  1. Ajouter un plugin (slug Modrinth, ex. worldedit)")
        print("  2. Retirer un plugin")
        print("  3. Voir les suggestions")
        print("  4. Télécharger / mettre à jour maintenant")
        print("  0. Retour")
        choix = _lire("> ")
        if choix == "1":
            slug = _lire("Slug Modrinth : ").lower()
            if slug and slug not in config["plugins"]:
                if slug == "fastasyncworldedit" and "worldedit" in config["plugins"]:
                    config["plugins"].remove("worldedit")
                    print("  worldedit retiré (FAWE le remplace).")
                config["plugins"].append(slug)
                config_mod.sauvegarder(config)
        elif choix == "2":
            slug = _lire("Slug à retirer : ").lower()
            if slug in config["plugins"]:
                config["plugins"].remove(slug)
                config_mod.sauvegarder(config)
        elif choix == "3":
            for slug, description in plugins.PLUGINS_SUGGERES.items():
                print(f"  {slug:<22} {description}")
        elif choix == "4":
            if not serveur.est_installe(config):
                print("Installez d'abord le serveur (option 1 du menu principal).")
                continue
            try:
                etat = serveur.lire_etat(config)
                version = etat.get("version_minecraft") or telechargement.resoudre_version_paper(
                    config["version_minecraft"])
                plugins.installer_geyser_floodgate(config)
                plugins.installer_plugins_modrinth(config, version)
            except telechargement.ErreurTelechargement as exc:
                print(f"!! {exc}")
        elif choix == "0":
            return


def action_parametres(config: dict) -> None:
    champs = [
        ("version_minecraft", "Version Minecraft (latest ou ex. 26.3)"),
        ("ram_mo", "RAM du serveur en Mo"),
        ("port_bedrock", "Port Bedrock (Switch)"),
        ("port_nethernet", "Port NetherNet / WebRTC (UDP)"),
        ("port_java", "Port Java (PC)"),
        ("motd", "Nom affiché du serveur"),
        ("mode_jeu", "Mode de jeu (survival / creative)"),
        ("difficulte", "Difficulté (peaceful / easy / normal / hard)"),
        ("launcher_minecraft", "Chemin du launcher Minecraft Java (vide = auto)"),
        ("lancer_minecraft_avec_serveur", "Lancer Minecraft avec le serveur (true / false)"),
    ]
    print("\n--- Paramètres (Entrée pour conserver) ---")
    for cle, libelle in champs:
        actuel = config[cle]
        saisie = _lire(f"  {libelle} [{actuel}] : ", str(actuel))
        if isinstance(actuel, bool):
            config[cle] = saisie.lower() in ("true", "oui", "o", "1", "vrai")
        elif isinstance(actuel, int):
            try:
                config[cle] = int(saisie)
            except ValueError:
                print(f"    valeur ignorée : {saisie!r}")
        else:
            config[cle] = saisie
    config_mod.sauvegarder(config)
    print("Paramètres enregistrés. (Réinstallez si la version Minecraft a changé.)")


def boucle(config: dict) -> None:
    actions = {
        "1": ("Installer / mettre à jour le serveur (Paper + Geyser + Floodgate + plugins)", action_installer),
        "2": ("Jouer : démarrer le serveur (+ Minecraft Java)", action_jouer),
        "3": ("Gérer les plugins (WorldEdit, etc.)", action_plugins),
        "4": ("Afficher les instructions de connexion Switch", lambda c: print(reseau.instructions_switch(c))),
        "5": ("Ouvrir le pare-feu Windows (en administrateur)", reseau.ouvrir_pare_feu_windows),
        "6": ("Paramètres", action_parametres),
    }
    while True:
        _entete(config)
        for touche, (libelle, _) in actions.items():
            print(f"  {touche}. {libelle}")
        print("  0. Quitter")
        choix = _lire("> ")
        if choix == "0":
            return
        action = actions.get(choix)
        if action:
            action[1](config)
        else:
            print("Choix inconnu.")


def executer(arguments: list[str]) -> int:
    config = config_mod.charger()
    commande = arguments[0] if arguments else ""
    if commande in ("-h", "--help", "aide"):
        print("Usage : python launcher.py [installer | jouer | plugins | switch | parametres]")
        print("Sans argument : menu interactif.")
        return 0
    if commande == "installer":
        action_installer(config)
    elif commande == "jouer":
        action_jouer(config)
    elif commande == "plugins":
        action_plugins(config)
    elif commande == "switch":
        print(reseau.instructions_switch(config))
    elif commande == "parametres":
        action_parametres(config)
    elif commande:
        print(f"Commande inconnue : {commande}", file=sys.stderr)
        return 2
    else:
        boucle(config)
    return 0
