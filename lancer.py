"""Lanceur portable depuis le dépôt : python lancer.py."""
import runpy
import sys
from pathlib import Path


def main():
    if sys.version_info < (3, 11):
        raise SystemExit("VISU PTBG nécessite Python 3.11 ou plus récent.")
    try:
        import tkinter
        import matplotlib
    except ImportError as exc:
        raise SystemExit("Installer les dépendances avec python -m pip install -r requirements.txt. "
                         "Tkinter doit aussi être installé avec Python. Détail : " + str(exc)) from exc
    projet = Path(__file__).resolve().parent / "visu_ptbg"
    sys.path.insert(0, str(projet))
    try:
        runpy.run_path(str(projet / "MAIN.py"), run_name="__main__")
    except tkinter.TclError as exc:
        raise SystemExit("La fenêtre ne peut pas démarrer : vérifier l'écran et Tcl/Tk. " + str(exc)) from exc


if __name__ == "__main__":
    main()
