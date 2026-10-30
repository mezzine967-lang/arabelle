"""Petites icônes de statut dessinées pixel par pixel (aucun fichier image).

Les émojis sont évités : Tk 8.6 sous Linux ne sait pas afficher les
caractères hors du plan multilingue de base. Une icône est un disque coloré
(statut) ou un carré (type de nœud) de 12 × 12 pixels.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import font as tkfont

from ptbg.core.diagnostics import Severity
from ptbg.plotting.styles import SEVERITY_COLORS

SIZE = 12


def _disc(color: str) -> tk.PhotoImage:
    image = tk.PhotoImage(width=SIZE, height=SIZE)
    center, radius = (SIZE - 1) / 2, SIZE / 2 - 1
    for y in range(SIZE):
        for x in range(SIZE):
            # Seuls les pixels du disque sont posés : le reste reste transparent.
            if (x - center) ** 2 + (y - center) ** 2 <= radius ** 2:
                image.put(color, (x, y))
    return image


def _square(color: str) -> tk.PhotoImage:
    image = tk.PhotoImage(width=SIZE, height=SIZE)
    image.put(color, to=(2, 2, SIZE - 2, SIZE - 2))
    return image


class Icons:
    """Jeu d'icônes ; doit être créé après la fenêtre Tk (et conservé)."""

    def __init__(self) -> None:
        self.status = {severity: _disc(color) for severity, color in SEVERITY_COLORS.items()}
        self.package = _square("#1565c0")
        self.time = _square("#6a1b9a")
        self.bool = _square("#009E73")
        self.float = _square("#0072B2")
        self.text = _square("#E69F00")
        self.group = _square("#CC79A7")
        self.issue = _disc("#9e9e9e")

    def for_severity(self, severity: Severity) -> tk.PhotoImage:
        return self.status[severity]


def bold_font(size_delta: int = 0) -> tkfont.Font:
    """Police par défaut de Tk en gras (le nom « TkDefaultFont » dans un tuple
    n'est pas reconnu comme police nommée et donnerait une police de secours)."""
    font = tkfont.nametofont("TkDefaultFont").copy()
    size = font.cget("size")
    # Taille Tk positive = points, négative = pixels : on agrandit en valeur absolue.
    font.configure(weight="bold", size=size + size_delta if size > 0 else size - size_delta)
    return font
