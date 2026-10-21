#!/usr/bin/env python3
"""MCSL – Launcher de serveur Minecraft local jouable depuis la Nintendo Switch.

Usage :
    python launcher.py              # menu interactif
    python launcher.py installer    # installe / met à jour Paper + Geyser + Floodgate + plugins
    python launcher.py jouer        # démarre le serveur (et Minecraft Java)
    python launcher.py switch       # affiche les instructions de connexion Switch
"""

import sys

if sys.version_info < (3, 10):
    sys.exit("Python 3.10 ou plus récent est nécessaire (https://www.python.org/downloads/).")

from mcsl.menu import executer  # noqa: E402

if __name__ == "__main__":
    try:
        sys.exit(executer(sys.argv[1:]))
    except KeyboardInterrupt:
        print("\nInterrompu.")
        sys.exit(130)
