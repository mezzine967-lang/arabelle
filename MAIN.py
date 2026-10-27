"""VISU PTBG — script principal : construit l'interface graphique.

REQ_COMMON_KH_3002 : ce script est consacré UNIQUEMENT à la génération de
l'interface. Il vérifie que l'environnement permet d'ouvrir une fenêtre, puis
assemble les zones de la fenêtre principale (section 4.1 « Main GUI ») :

    ┌──────────────────────────────────────────────────────────────┐
    │ Barre de menus (REQ 5100) + barre de chemin / accès rapides  │
    ├───────────────┬──────────────────────────────────────────────┤
    │ Arbre des     │ Zone graphique à onglets (REQ 5104, 5106)    │
    │ données       │  - axes du modèle choisi (REQ 5300)          │
    │ (REQ 5103,    │  - Time Base Monitor automatique (REQ 4102)  │
    │  masquable    │  - panneau de lecture des curseurs (REQ 5402)│
    │  REQ 5105)    │                                              │
    ├───────────────┴──────────────────────────────────────────────┤
    │ Barre d'état : utilisateur, date, journal, version (REQ 5102)│
    └──────────────────────────────────────────────────────────────┘

Toutes les actions sont déléguées au contrôleur ``ptbg.gui.app.Application``
et aux modules de ``ptbg/`` (REQ_COMMON_KH_3003).

Lancement :
- Windows 11 / Spyder 6 : ouvrir ce fichier puis Exécuter (F5) ;
- Windows ou SLES 15 SP7 en terminal : ``python MAIN.py [fichiers.csv ...]``.
"""
import sys
from pathlib import Path

# Rend le paquet « ptbg » importable quel que soit le dossier courant
# (Spyder peut exécuter le script depuis un autre répertoire de travail).
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ptbg.version import MIN_PYTHON, full_name  # noqa: E402  (après la mise à jour de sys.path)

TREE_WIDTH = 380        # largeur initiale de l'arbre (pixels), modifiable au séparateur


def _environment_problem():
    """Raison empêchant l'ouverture de la fenêtre, ou None."""
    if sys.version_info < MIN_PYTHON:
        return f"{full_name()} nécessite Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]} ou plus récent."
    from ptbg.system.environment import missing_runtime_modules
    missing = missing_runtime_modules()
    if missing:
        return (f"Module(s) manquant(s) : {', '.join(missing)}. Voir README.md (installation) : "
                "tkinter est fourni avec Python (paquet python311-tk sous SLES), numpy et matplotlib "
                "s'installent avec « python -m pip install -r requirements.txt ».")
    from ptbg.system.compat import display_problem
    return display_problem()


def build_interface(root, settings=None, log=None):
    """Assemble les zones de la fenêtre principale ; renvoie le contrôleur.

    Utilisée par ``main()`` et par les tests d'interface (tests/test_gui.py),
    qui vérifient ainsi exactement la fenêtre livrée.
    """
    import tkinter as tk

    from ptbg.config import Settings
    from ptbg.gui.app import Application
    from ptbg.gui.graph_area import GraphArea
    from ptbg.gui.menu_bar import MenuBar
    from ptbg.gui.path_bar import PathBar
    from ptbg.gui.status_bar import StatusBar
    from ptbg.gui.tree_panel import TreePanel
    from ptbg.system.activity_log import ActivityLog

    root.title(full_name() + " — analyseur de perturbographie")
    controller = Application(root, settings or Settings.load(), log or ActivityLog())

    # Barre supérieure : menus (REQ 5100) puis chemin courant et accès rapides.
    menu = MenuBar(root, controller)
    path_bar = PathBar(root, controller)
    path_bar.pack(side="top", fill="x")

    # Barre d'état en bas (REQ 5102), placée avant la zone centrale pour rester visible.
    status = StatusBar(root, controller)
    status.pack(side="bottom", fill="x")

    # Zone centrale : arbre à gauche (REQ 5103), zone graphique plus large à droite
    # (REQ 5104) qui seule s'étire quand la fenêtre est agrandie.
    paned = tk.PanedWindow(root, orient="horizontal", sashwidth=6, sashrelief="raised")
    paned.pack(side="top", fill="both", expand=True)
    tree = TreePanel(paned, controller)
    graph = GraphArea(paned, controller)
    paned.add(tree, width=TREE_WIDTH, minsize=180, stretch="never")
    paned.add(graph, minsize=500, stretch="always")

    controller.attach(menu, path_bar, tree, graph, status, paned)
    root.protocol("WM_DELETE_WINDOW", controller.quit)
    return controller


def main() -> None:
    """Vérifie l'environnement, construit la fenêtre et lance la boucle Tk."""
    problem = _environment_problem()
    if problem:
        print(problem, file=sys.stderr)
        return

    import tkinter as tk

    from ptbg.system.compat import enable_high_dpi

    enable_high_dpi()                       # Windows : interface nette à 125 / 150 %
    root = tk.Tk()
    width = min(1600, root.winfo_screenwidth() - 60)
    height = min(1000, root.winfo_screenheight() - 90)
    root.geometry(f"{width}x{height}+20+20")
    root.minsize(1000, 650)
    from ptbg.system.environment import tkagg_problem
    problem = tkagg_problem(root)           # Matplotlib doit savoir dessiner dans ce Tk
    if problem:
        from tkinter import messagebox
        print(problem, file=sys.stderr)
        messagebox.showerror(full_name(), problem)
        root.destroy()
        return
    controller = build_interface(root)
    files = [a for a in sys.argv[1:] if Path(a).is_file()]
    if files:                               # fichiers passés en ligne de commande
        root.after(200, lambda: controller.open_files(files))
    root.mainloop()


if __name__ == "__main__":
    main()
