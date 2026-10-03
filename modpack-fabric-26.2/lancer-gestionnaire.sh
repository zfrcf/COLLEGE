#!/usr/bin/env bash
# Lance le gestionnaire (macOS / Linux). Double-clic possible si le fichier est exécutable.
cd "$(dirname "$0")" || exit 1
if command -v python3 >/dev/null 2>&1; then
  exec python3 gestionnaire.py "$@"
else
  echo "Python 3 n'est pas installé : https://www.python.org/downloads/"
  exit 1
fi
