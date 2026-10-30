#!/bin/sh
# Lance VISU PTBG sur SLES 15 SP7 avec l'environnement créé par installer_sles.sh.
# Une session graphique est nécessaire (bureau, ou « ssh -X » depuis un autre poste).
# Usage : install/lancer_sles.sh [fichier1.csv fichier2.csv ...]
set -eu
PROJET="$(cd "$(dirname "$0")/.." && pwd)"
exec "$PROJET/.venv/bin/python" "$PROJET/MAIN.py" "$@"
