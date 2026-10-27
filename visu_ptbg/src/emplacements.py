"""Emplacement utilisateur des journaux — contribution au requis 3005.

Les CSV ne sont jamais écrits ici. Ce dossier contient seulement les résultats
automatiques. Il ne dépend ni du dossier courant ni du dossier d'installation.
Bibliothèque standard uniquement : os, sys et pathlib.
"""
import os
import sys
from pathlib import Path


def dossier_resultats() -> Path:
    """Choisir un emplacement utilisateur absolu sans le créer.

    Windows : LOCALAPPDATA ; Linux : XDG_STATE_HOME ou ~/.local/state.
    Une variable relative est ignorée pour éviter un résultat dépendant de la
    console. Les refus de création sont laissés à l'appelant, qui les affiche.
    """
    if sys.platform == 'win32':
        valeur = os.environ.get('LOCALAPPDATA', '')
        repli = Path.home() / 'AppData' / 'Local'
    else:
        valeur = os.environ.get('XDG_STATE_HOME', '')
        repli = Path.home() / '.local' / 'state'
    base = Path(valeur) if valeur and Path(valeur).is_absolute() else repli
    return base / 'VISU_PTBG' / 'resultats'
