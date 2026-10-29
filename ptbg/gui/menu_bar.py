"""Barre de menus principale (REQ_COMMON_KH_5100) et section Information (5101).

Chaque entrée appelle une méthode du contrôleur (``gui/app.py``) : aucune
action n'est codée ici (REQ_COMMON_KH_3003). Les raccourcis clavier sont
indiqués dans les menus et liés à la fenêtre principale.
"""
from __future__ import annotations

import tkinter as tk

from ptbg.core.arrangement import TEMPLATES


class MenuBar:
    """Construit les menus Fichier, Affichage, Base de temps, Outils, Rapport, Information."""

    def __init__(self, root: tk.Tk, controller) -> None:
        """Crée les menus et les raccourcis clavier globaux."""
        self.controller = controller
        bar = tk.Menu(root, tearoff=False)   # Tk 8.6 : sinon entrée « détachable » cachée en tête
        c = controller
        self.time_mode = tk.StringVar(value="relative")
        self.tree_visible = tk.BooleanVar(value=True)

        # Fichier : sources (REQ 2105), paquets (REQ 5200), projet (REQ 6005).
        files = tk.Menu(bar, tearoff=False)
        files.add_command(label="Ouvrir des fichiers CSV…", accelerator="Ctrl+O", command=c.open_files)
        files.add_command(label="Ouvrir un dossier de CSV…", command=c.open_folder)
        files.add_separator()
        files.add_command(label="Nouveau paquet de données", command=c.new_package)
        files.add_command(label="Fermer la sélection de l'arbre", command=c.remove_selection)
        files.add_separator()
        files.add_command(label="Ouvrir un projet…", command=c.open_project)
        files.add_command(label="Enregistrer le projet", accelerator="Ctrl+S", command=c.save_project)
        files.add_command(label="Enregistrer le projet sous…", command=lambda: c.save_project(ask=True))
        files.add_separator()
        files.add_command(label="Quitter", accelerator="Ctrl+Q", command=c.quit)
        bar.add_cascade(label="Fichier", menu=files)

        # Affichage : arbre masquable (REQ 5105), onglets / modèles (REQ 5106, 5300), axe des temps (REQ 4107).
        view = tk.Menu(bar, tearoff=False)
        view.add_checkbutton(label="Afficher l'arbre des données", accelerator="F9",
                             variable=self.tree_visible, command=c.toggle_tree)
        templates = tk.Menu(view, tearoff=False)
        for item in TEMPLATES:
            templates.add_command(label=f"{item.name} — {item.description}",
                                  command=lambda key=item.key: c.new_tab(key))
        view.add_cascade(label="Nouvel onglet (modèle)", menu=templates)
        view.add_command(label="Renommer l'onglet…", command=c.rename_tab)
        view.add_command(label="Fermer l'onglet", accelerator="Ctrl+W", command=c.close_tab)
        view.add_command(label="Vue d'origine (toute la durée)", accelerator="Ctrl+0", command=c.reset_view)
        view.add_separator()
        view.add_radiobutton(label="Axe des temps relatif (s)", value="relative",
                             variable=self.time_mode, command=lambda: c.set_time_mode("relative"))
        view.add_radiobutton(label="Axe des temps absolu (horodatage)", value="absolute",
                             variable=self.time_mode, command=lambda: c.set_time_mode("absolute"))
        bar.add_cascade(label="Affichage", menu=view)

        # Base de temps : raster imposé (REQ 4106), diagnostic (REQ 4101), multi-PLC (REQ 2104), TBM (REQ 4103).
        timebase = tk.Menu(bar, tearoff=False)
        timebase.add_command(label="Configurer la base de temps du fichier…", command=c.configure_time_base)
        timebase.add_command(label="Diagnostic complet du fichier…", command=c.show_diagnostic)
        timebase.add_command(label="Comparer les sources (multi-PLC)…", command=c.compare_sources)
        timebase.add_separator()
        timebase.add_command(label="Masquer / afficher le Time Base Monitor", command=c.toggle_monitor)
        bar.add_cascade(label="Base de temps", menu=timebase)

        # Outils : groupes binaires (REQ 2201), curseurs H et X/Y (REQ 5406-5408), traitement conditionnel.
        tools = tk.Menu(bar, tearoff=False)
        tools.add_command(label="Créer un groupe binaire…", command=c.create_group)
        tools.add_command(label="Curseur horizontal et condition Bool…", command=c.horizontal_cursor)
        tools.add_command(label="Nuage X/Y (corrélation)…", command=c.configure_xy)
        tools.add_command(label="Traitement conditionnel…", command=c.conditional_processing)
        tools.add_separator()
        tools.add_command(label="Préférences…", command=c.preferences)
        bar.add_cascade(label="Outils", menu=tools)

        # Rapport PDF : en-tête (REQ 6005), automatique (REQ 6003), pas à pas (REQ 6004).
        report = tk.Menu(bar, tearoff=False)
        report.add_command(label="En-tête du rapport (projet, unité, émetteur)…", command=c.edit_report_header)
        report.add_separator()
        report.add_command(label="Rapport automatique de l'onglet actif…", accelerator="Ctrl+P",
                           command=c.automatic_report)
        report.add_separator()
        report.add_command(label="Pas à pas : ajouter la vue active", accelerator="Ctrl+K", command=c.add_report_page)
        report.add_command(label="Pas à pas : gérer les pages et générer le PDF…", command=c.manage_report_pages)
        bar.add_cascade(label="Rapport", menu=report)

        # Information : version, historique, sources, aide (REQ 5101) et journal (REQ 5102).
        info = tk.Menu(bar, tearoff=False)
        info.add_command(label="Version de l'outil", command=c.show_version)
        info.add_command(label="Historique des modifications", command=c.show_history)
        info.add_command(label="Sources (code, bibliothèques, fichiers)", command=c.show_sources)
        info.add_command(label="Fichier d'aide", accelerator="F1", command=c.show_help)
        info.add_separator()
        info.add_command(label="Journal d'activité", command=c.show_log)
        info.add_command(label="Traçabilité des requis", command=c.show_traceability)
        bar.add_cascade(label="Information", menu=info)
        root.config(menu=bar)

        # Raccourcis clavier valables dans toute l'application.
        for sequence, action in (("<Control-o>", c.open_files), ("<Control-s>", c.save_project),
                                 ("<Control-q>", c.quit), ("<Control-w>", c.close_tab), ("<Control-0>", c.reset_view),
                                 ("<Control-p>", c.automatic_report), ("<Control-k>", c.add_report_page),
                                 ("<F9>", c.toggle_tree), ("<F1>", c.show_help)):
            root.bind_all(sequence, lambda _event, action=action: action())
