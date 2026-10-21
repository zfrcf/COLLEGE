"""Infos réseau : IP locale, test des ports, instructions pour la Switch, pare-feu."""

from __future__ import annotations

import os
import socket
import subprocess

# DNS public du projet BedrockConnect (https://github.com/Pugmatt/BedrockConnect)
DNS_BEDROCKCONNECT_PRINCIPAL = "104.238.130.180"
DNS_BEDROCKCONNECT_SECONDAIRE = "8.8.8.8"


def ip_locale() -> str:
    """IP de la machine sur le réseau local (celle à saisir sur la Switch)."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Aucune donnée n'est envoyée : on laisse l'OS choisir l'interface de sortie.
        sock.connect(("1.1.1.1", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


def port_tcp_libre(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def port_udp_libre(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind(("0.0.0.0", port))
            return True
        except OSError:
            return False


def ports_a_verifier(config: dict) -> list[tuple[str, int, bool]]:
    """(libellé, port, libre) pour chaque port dont le serveur a besoin."""
    return [
        ("Java (TCP)", config["port_java"], port_tcp_libre(config["port_java"])),
        ("Bedrock RakNet (UDP)", config["port_bedrock"], port_udp_libre(config["port_bedrock"])),
        ("Bedrock signalisation NetherNet (TCP)", config["port_bedrock"], port_tcp_libre(config["port_bedrock"])),
        ("Bedrock NetherNet (UDP)", config["port_nethernet"], port_udp_libre(config["port_nethernet"])),
    ]


def instructions_switch(config: dict) -> str:
    ip = ip_locale()
    port_bedrock = config["port_bedrock"]
    port_nethernet = config["port_nethernet"]
    port_java = config["port_java"]
    return f"""
=====================================================================
  CONNEXION DEPUIS LA NINTENDO SWITCH
=====================================================================
  IP de ce PC sur le réseau local : {ip}
  Port Bedrock (à saisir sur la Switch) : {port_bedrock}
  (NetherNet : TCP {port_bedrock} + UDP {port_nethernet} ; RakNet : UDP {port_bedrock})
  Port Java (PC)                        : {port_java} (TCP)

  Pré-requis : la Switch et ce PC sont sur le MÊME réseau (même box /
  même Wi-Fi) et le serveur est démarré (option "Jouer" du menu).

  --- Méthode 1 : onglet "Amis" (monde en local, zéro réglage) --------
  Sur la Switch : Jouer > Amis > section "Jeux en réseau local".
  Le serveur apparaît tant que le port Bedrock est 19132 (port par
  défaut de Minecraft). Si la liste reste vide, utiliser la méthode 2.

  --- Méthode 2 : BedrockConnect (saisir l'IP soi-même) ---------------
  1. Switch : Paramètres de la console > Internet > Paramètres Internet
     > votre Wi-Fi > Modifier les paramètres > Paramètres DNS : Manuel
       DNS primaire   : {DNS_BEDROCKCONNECT_PRINCIPAL}
       DNS secondaire : {DNS_BEDROCKCONNECT_SECONDAIRE}
     Enregistrer, puis se reconnecter au Wi-Fi.
  2. Lancer Minecraft > Jouer > onglet Serveurs > choisir N'IMPORTE QUEL
     serveur en vedette (ex. The Hive). Un menu BedrockConnect s'ouvre.
  3. "Connect to a Server" / "Ajouter un serveur" :
       Adresse : {ip}      Port : {port_bedrock}
     Cocher "Add to server list" pour le retrouver la prochaine fois.
  4. Première connexion : Minecraft peut demander de faire confiance au
     serveur (connexion NetherNet par IP) → accepter.

  Astuce : pour revenir aux serveurs officiels, remettre le DNS en
  "Automatique" sur la Switch.

  Pare-feu : si la Switch ne voit rien, autoriser sur ce PC
  UDP {port_bedrock}, TCP {port_bedrock}, UDP {port_nethernet} et TCP {port_java}
  (option "Ouvrir le pare-feu" du menu).
=====================================================================
"""


def ouvrir_pare_feu_windows(config: dict) -> bool:
    """Ajoute les règles de pare-feu Windows (nécessite une console administrateur)."""
    regles = [
        ("MCSL Bedrock RakNet UDP", "UDP", config["port_bedrock"]),
        ("MCSL Bedrock signalisation NetherNet TCP", "TCP", config["port_bedrock"]),
        ("MCSL Bedrock NetherNet UDP", "UDP", config["port_nethernet"]),
        ("MCSL Java TCP", "TCP", config["port_java"]),
    ]
    if os.name != "nt":
        print("[réseau] L'ouverture automatique du pare-feu n'est prévue que sous Windows.")
        print("         Autorisez manuellement : " + ", ".join(f"{p} {port}" for _, p, port in regles))
        return False
    ok = True
    for nom, protocole, port in regles:
        commande = [
            "netsh", "advfirewall", "firewall", "add", "rule",
            f"name={nom}", "dir=in", "action=allow", f"protocol={protocole}", f"localport={port}",
        ]
        resultat = subprocess.run(commande, capture_output=True, text=True)
        if resultat.returncode == 0:
            print(f"[réseau] Règle ajoutée : {nom} ({protocole} {port})")
        else:
            ok = False
            print(f"[réseau] Échec pour {nom} : {resultat.stdout.strip() or resultat.stderr.strip()}")
            print("         → relancez le launcher en tant qu'administrateur.")
    return ok
