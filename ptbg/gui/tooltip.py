"""Bulle d'aide des tableaux (arbre des données, panneau de lecture).

Quand le panneau est étroit, les colonnes sont tronquées (« AVERTIS… ») :
la souris posée une demi-seconde sur une ligne affiche son texte complet.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

DELAY_MS = 500          # attente avant l'affichage de la bulle
WRAP_PX = 520           # largeur maximale de la bulle avant retour à la ligne


class RowTooltip:
    """Affiche, au survol d'une ligne d'un ``ttk.Treeview``, le texte rendu par ``text_of(iid)``."""

    def __init__(self, tree: ttk.Treeview, text_of) -> None:
        """Branche la bulle sur les mouvements de souris du tableau."""
        self.tree, self.text_of = tree, text_of
        self.tip = None
        self.row = ""
        self.job = None
        tree.bind("<Motion>", self._motion, add=True)
        tree.bind("<Leave>", self._hide, add=True)
        tree.bind("<ButtonPress>", self._hide, add=True)

    def _motion(self, event) -> None:
        """Nouvelle ligne survolée : la bulle précédente disparaît, la suivante est programmée."""
        row = self.tree.identify_row(event.y)
        if row == self.row:
            return
        self._hide()
        self.row = row
        if row:
            self.job = self.tree.after(DELAY_MS, lambda: self._show(event.x_root, event.y_root))

    def _show(self, x: int, y: int) -> None:
        """Ouvre la bulle près de la souris."""
        self.job = None
        text = self.text_of(self.row) if self.tree.exists(self.row) else ""
        if not text:
            return
        self.tip = tk.Toplevel(self.tree)
        self.tip.wm_overrideredirect(True)
        self.tip.geometry(f"+{x + 14}+{y + 18}")
        tk.Label(self.tip, text=text, background="#ffffe0", foreground="#000000", relief="solid",
                 borderwidth=1, wraplength=WRAP_PX, justify="left", padx=5, pady=3).pack()

    def _hide(self, _event=None) -> None:
        """Ferme la bulle et annule celle qui était programmée."""
        if self.job is not None:
            self.tree.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None
        self.row = ""
