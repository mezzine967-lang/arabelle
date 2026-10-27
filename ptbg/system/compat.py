"""Mécanismes de compatibilité Windows 11 / SLES 15 SP7.

REQ_COMMON_KH_3000 (SLES 15 SP7 + double compatibilité Windows) et
REQ_COMMON_KH_3005 (mécanisme de compatibilité documenté).

Toutes les différences entre systèmes d'exploitation sont regroupées ICI,
pour qu'aucun autre module n'ait à tester ``sys.platform``. Le détail et les
justifications sont dans docs/COMPATIBILITE_OS.md.

Principes :
- chemins manipulés uniquement avec ``pathlib`` (pas de séparateur codé en dur) ;
- dossiers utilisateur conformes à chaque OS (APPDATA / XDG) ;
- aucune commande shell propre à un OS dans les traitements ;
- les fonctions ne lèvent pas d'exception pour un simple confort (DPI,
  ouverture d'un PDF) : un échec est renvoyé à l'appelant qui le journalise.
"""
from __future__ import annotations

import getpass
import os
import subprocess
import sys
from pathlib import Path

APP_DIR_NAME = "VISU_PTBG"

IS_WINDOWS = sys.platform.startswith("win")
IS_LINUX = sys.platform.startswith("linux")


def current_user() -> str:
    """Nom de l'utilisateur de la session (barre d'état, émetteur du rapport).

    ``getpass.getuser`` lit USERNAME sous Windows et LOGNAME/USER sous Linux ;
    il peut échouer dans certains conteneurs sans variable : on renvoie alors
    « inconnu » plutôt que de bloquer l'application.
    """
    try:
        return getpass.getuser()
    except Exception:  # noqa: BLE001 - toute erreur ici n'est qu'informative
        return "inconnu"


def user_config_dir() -> Path:
    """Dossier des préférences utilisateur (fichier settings.json).

    Windows : %APPDATA%\\VISU_PTBG ; Linux : $XDG_CONFIG_HOME/visu_ptbg
    (par défaut ~/.config/visu_ptbg).
    """
    if IS_WINDOWS:
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / APP_DIR_NAME
    base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config")
    return base / APP_DIR_NAME.lower()


def user_state_dir() -> Path:
    """Dossier des journaux d'activité et relevés d'environnement.

    Windows : %LOCALAPPDATA%\\VISU_PTBG ; Linux : $XDG_STATE_HOME/visu_ptbg
    (par défaut ~/.local/state/visu_ptbg). Ce dossier est distinct du dossier
    du programme, qui peut être en lecture seule sur le Service Unit.
    """
    if IS_WINDOWS:
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
        return base / APP_DIR_NAME
    base = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state")
    return base / APP_DIR_NAME.lower()


def ensure_dir(path: Path) -> Path | None:
    """Crée le dossier si besoin ; renvoie None si les droits l'interdisent."""
    try:
        path.mkdir(parents=True, exist_ok=True)
        return path
    except OSError:
        return None


def display_problem() -> str | None:
    """Indique pourquoi aucune fenêtre ne pourra s'ouvrir, sinon None.

    Sous Linux (SLES), une session graphique est nécessaire : variable DISPLAY
    (X11, y compris « ssh -X ») ou WAYLAND_DISPLAY. Sous Windows, il y a
    toujours un bureau.
    """
    if IS_LINUX and not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return ("Aucune session graphique détectée (variable DISPLAY vide). "
                "Sur le Service Unit, lancer l'outil depuis le bureau ou via « ssh -X ».")
    return None


def enable_high_dpi() -> None:
    """Rend l'interface nette sur les écrans Windows à mise à l'échelle (125 %, 150 %).

    Sans cet appel, Windows agrandit une image floue de la fenêtre. Doit être
    appelé AVANT la création de la fenêtre Tk. Sans effet sous Linux, où Tk
    lit directement la résolution du serveur X. Si l'appel échoue (ancienne
    version de Windows, processus déjà configuré par Spyder), on continue.
    """
    if not IS_WINDOWS:
        return
    try:
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)  # 1 = « system DPI aware »
    except Exception:  # noqa: BLE001 - confort visuel uniquement
        pass


def open_with_default_application(path: Path) -> str | None:
    """Ouvre un fichier (PDF du rapport, aide) avec l'application par défaut.

    Windows : ``os.startfile`` ; Linux : ``xdg-open`` (paquet xdg-utils sur SLES).
    Renvoie un message d'erreur, ou None si la demande a été transmise.
    """
    try:
        if IS_WINDOWS:
            os.startfile(str(path))  # type: ignore[attr-defined]  # Windows seulement
        else:
            subprocess.Popen(["xdg-open", str(path)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return None
    except Exception as exc:  # noqa: BLE001 - l'appelant affiche le message
        return f"Ouverture impossible de {path} : {exc}"


def project_root() -> Path:
    """Dossier racine des sources (contient MAIN.py, docs/, data/)."""
    return Path(__file__).resolve().parents[2]
