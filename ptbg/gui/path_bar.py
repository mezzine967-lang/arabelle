"""Barre supérieure : chemin courant et accès rapides (REQ_COMMON_KH_5100).

Sous la barre de menus, elle affiche le CHEMIN de l'élément sélectionné
(« Paquet > fichier.csv > variable ») et l'onglet actif, avec des boutons
vers les commandes les plus fréquentes des menus.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ptbg.core.arrangement import TEMPLATES


class PathBar(ttk.Frame):
    """Chemin de la sélection et boutons d'accès rapide."""

    def __init__(self, master, controller) -> None:
        """Boutons d'accès rapide et libellé du chemin courant."""
        super().__init__(master, padding=(6, 3))
        self.path = tk.StringVar(value="Aucune donnée : Fichier > Ouvrir des fichiers CSV…")
        c = controller
        ttk.Button(self, text="Ouvrir CSV…", command=c.open_files).pack(side="left")
        ttk.Button(self, text="Arbre", command=c.toggle_tree, width=6).pack(side="left", padx=(4, 0))
        new_tab = ttk.Menubutton(self, text="Nouvel onglet")
        menu = tk.Menu(new_tab, tearoff=False)
        for item in TEMPLATES:
            menu.add_command(label=item.name, command=lambda key=item.key: c.new_tab(key))
        new_tab["menu"] = menu
        new_tab.pack(side="left", padx=4)
        ttk.Button(self, text="Rapport auto…", command=c.automatic_report).pack(side="left")
        ttk.Button(self, text="+ Page pas à pas", command=c.add_report_page).pack(side="left", padx=4)
        ttk.Label(self, text="Chemin :").pack(side="left", padx=(12, 2))
        ttk.Label(self, textvariable=self.path, foreground="#1565c0").pack(side="left", fill="x", expand=True)
        ttk.Button(self, text="Aide", command=c.show_help, width=6).pack(side="right")

    def show(self, parts: list[str], tab_title: str | None) -> None:
        """Affiche « paquet > fichier > variable » et l'onglet actif."""
        text = "  >  ".join(parts) if parts else "—"
        if tab_title:
            text += f"     |     Onglet actif : {tab_title}"
        self.path.set(text)
