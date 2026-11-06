"""Base commune des boîtes de dialogue : boutons en français.

``tkinter.simpledialog.Dialog`` (bibliothèque standard) affiche « OK » et
« Cancel » ; l'interface de l'outil étant en français, ses dialogues
affichent « OK » et « Annuler » (mêmes raccourcis : Entrée, Échap).
"""
from __future__ import annotations

from tkinter import simpledialog, ttk


class Dialog(simpledialog.Dialog):
    """Dialogue modal de la bibliothèque standard, boutons « OK » / « Annuler »."""

    def buttonbox(self) -> None:
        """Boutons du bas : OK (Entrée) et Annuler (Échap)."""
        box = ttk.Frame(self)
        ttk.Button(box, text="OK", width=10, command=self.ok, default="active").pack(side="left", padx=5, pady=5)
        ttk.Button(box, text="Annuler", width=10, command=self.cancel).pack(side="left", padx=5, pady=5)
        self.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)
        box.pack()


class TextQuery(Dialog):
    """Saisie d'une ligne de texte (remplace ``simpledialog.askstring``)."""

    def __init__(self, parent, title: str, prompt: str, initial: str = "") -> None:
        """Mémorise la question et la valeur proposée, puis ouvre le dialogue."""
        self.prompt, self.initial = prompt, initial
        super().__init__(parent, title)

    def body(self, master):
        """Question et champ de saisie (sélectionné, prêt à être remplacé)."""
        ttk.Label(master, text=self.prompt, justify="left").pack(anchor="w", padx=5)
        self.entry = ttk.Entry(master, width=48)
        self.entry.insert(0, self.initial)
        self.entry.select_range(0, "end")
        self.entry.pack(fill="x", padx=5, pady=4)
        return self.entry

    def apply(self) -> None:
        """Résultat : le texte saisi."""
        self.result = self.entry.get()


def ask_text(parent, title: str, prompt: str, initial: str = "") -> str | None:
    """Texte saisi par l'utilisateur, ou None s'il annule."""
    return TextQuery(parent, title, prompt, initial).result
