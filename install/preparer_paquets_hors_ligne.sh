#!/bin/sh
# Prépare, sur un poste CONNECTÉ à Internet, les wheels nécessaires à une
# installation hors ligne sur le Service Unit SLES 15 SP7 (x86-64, Python 3.11).
# Le dossier produit (wheels_sles) est ensuite copié avec les sources, puis :
#     install/installer_sles.sh --hors-ligne wheels_sles
# Variables : PYTHON (interpréteur ayant pip), PYVER (défaut 3.11).
set -eu
PROJET="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON="${PYTHON:-python3}"
PYVER="${PYVER:-3.11}"
"$PYTHON" -m pip download --only-binary=:all: --implementation cp --python-version "$PYVER" \
    --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 \
    --platform manylinux_2_27_x86_64 --platform manylinux_2_28_x86_64 \
    -r "$PROJET/requirements.txt" -d "$PROJET/wheels_sles"
echo "Wheels prêtes dans $PROJET/wheels_sles"
