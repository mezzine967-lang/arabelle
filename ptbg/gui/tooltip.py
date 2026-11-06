"""Bulles d'aide : lignes des tableaux et boutons.

- Tableaux (arbre des données, panneau de lecture) : quand le panneau est
  étroit, les colonnes sont tronquées (« AVERTIS… ») ; la souris posée une
  demi-seconde sur une ligne affiche son texte complet (``RowTooltip``).
- Boutons (barre de navigation sous le graphique) : rôle du bouton au survol
  (``WidgetTooltip``).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

DELAY_MS = 500          # attente avant l'affichage de la bulle
WRAP_PX = 520           # largeur maximale de la bulle avant retour à la ligne


def _bubble(parent, text: str, x: int, y: int) -> tk.Toplevel:
    """Petite fenêtre jaune sans bordure de fenêtre, près du point (x, y) de l'écran."""
    tip = tk.Toplevel(parent)
    tip.wm_overrideredirect(True)
    tip.geometry(f"+{x + 14}+{y + 18}")
    tk.Label(tip, text=text, background="#ffffe0", foreground="#000000", relief="solid",
             borderwidth=1, wraplength=WRAP_PX, justify="left", padx=5, pady=3).pack()
    return tip


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
        self.tip = _bubble(self.tree, text, x, y)

    def _hide(self, _event=None) -> None:
        """Ferme la bulle et annule celle qui était programmée."""
        if self.job is not None:
            self.tree.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None
        self.row = ""


class WidgetTooltip:
    """Affiche ``text`` quand la souris reste une demi-seconde sur ``widget``."""

    def __init__(self, widget, text: str) -> None:
        """Branche la bulle sur l'entrée et la sortie de la souris."""
        self.widget, self.text = widget, text
        self.tip = None
        self.job = None
        widget.bind("<Enter>", self._schedule, add=True)
        widget.bind("<Leave>", self._hide, add=True)
        widget.bind("<ButtonPress>", self._hide, add=True)

    def _schedule(self, event) -> None:
        """Souris sur le bouton : bulle programmée."""
        self._hide()
        self.job = self.widget.after(DELAY_MS, lambda: self._show(event.x_root, event.y_root))

    def _show(self, x: int, y: int) -> None:
        """Ouvre la bulle près de la souris."""
        self.job = None
        self.tip = _bubble(self.widget, self.text, x, y)

    def _hide(self, _event=None) -> None:
        """Ferme la bulle et annule celle qui était programmée."""
        if self.job is not None:
            self.widget.after_cancel(self.job)
            self.job = None
        if self.tip is not None:
            self.tip.destroy()
            self.tip = None
