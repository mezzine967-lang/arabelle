#!/bin/sh
# Installation de VISU PTBG sur SUSE Linux Enterprise Server 15 SP7 (REQ_COMMON_KH_3000).
#
# Prérequis système (une fois, administrateur) :
#     sudo zypper install python311 python311-tk python311-pip
#
# Usage :
#     install/installer_sles.sh                          # téléchargement depuis PyPI
#     install/installer_sles.sh --hors-ligne wheels_sles  # depuis un dossier de wheels
#
# Crée l'environnement virtuel .venv à la racine du projet et y installe les
# versions figées de requirements.txt. Rien n'est installé hors de ce dossier.
set -eu

PROJET="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3.11}"

if ! command -v "$PYTHON" >/dev/null 2>&1; then
    echo "Interpréteur $PYTHON introuvable : sudo zypper install python311 python311-tk python311-pip" >&2
    exit 1
fi
if ! "$PYTHON" -c "import tkinter" >/dev/null 2>&1; then
    echo "Tkinter absent pour $PYTHON : sudo zypper install python311-tk" >&2
    exit 1
fi

"$PYTHON" -m venv "$PROJET/.venv"
if [ "${1:-}" = "--hors-ligne" ]; then
    WHEELS="${2:?dossier de wheels attendu après --hors-ligne}"
    "$PROJET/.venv/bin/python" -m pip install --no-index --find-links "$WHEELS" -r "$PROJET/requirements.txt"
else
    "$PROJET/.venv/bin/python" -m pip install -r "$PROJET/requirements.txt"
fi
"$PROJET/.venv/bin/python" "$PROJET/tools/audit_environnement.py"
echo "Installation terminée. Lancement : install/lancer_sles.sh"
