"""Panneau de lecture des curseurs, à droite de la zone graphique (REQ 5402).

En mode suivi, il liste la valeur croisée de TOUTES les courbes de l'axe
(et de tous les axes pour le curseur global), avec l'instant de
l'échantillon lu et sa ligne dans le CSV. Bouton « Copier » : texte
tabulé collable dans un tableur ou un rapport.
"""
from __future__ import annotations

from tkinter import ttk

from ptbg.core.readings import HEADER
from ptbg.gui.icons import bold_font
from ptbg.gui.tooltip import RowTooltip

WIDTHS = (42, 62, 160, 100, 110, 62)


class ReadingPanel(ttk.Frame):
    """Tableau des lectures de curseurs avec copie vers le presse-papiers."""

    def __init__(self, master) -> None:
        """Titre, bouton « Copier » et tableau défilant."""
        super().__init__(master, padding=2)
        top = ttk.Frame(self)
        top.pack(fill="x")
        self.bold = bold_font()
        ttk.Label(top, text="Lecture des curseurs", font=self.bold).pack(side="left")
        ttk.Button(top, text="Copier", command=self.copy, width=7).pack(side="right")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.table = ttk.Treeview(body, columns=HEADER, show="headings", height=8)
        for name, width in zip(HEADER, WIDTHS):
            self.table.heading(name, text=name)
            self.table.column(name, width=width, minwidth=40, stretch=name in ("Courbe", "Valeur"))
        RowTooltip(self.table, self._row_text)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.table.yview)
        xscroll = ttk.Scrollbar(body, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=scroll.set, xscrollcommand=xscroll.set)
        self.table.grid(row=0, column=0, sticky="nsew")
        scroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        self._rows: list = []

    def show(self, rows) -> None:
        """Remplace le contenu du tableau par les lectures données."""
        self._rows = rows
        self.table.delete(*self.table.get_children())
        for row in rows:
            self.table.insert("", "end", values=row.as_tuple())

    def _row_text(self, iid: str) -> str:
        """Texte complet d'une lecture (bulle d'aide), une colonne par ligne."""
        return "\n".join(f"{name} : {value}" for name, value in zip(HEADER, self.table.item(iid, "values"))
                         if str(value))

    def copy(self) -> None:
        """Copie les lectures (texte tabulé) dans le presse-papiers."""
        text = "\t".join(HEADER) + "\n" + "\n".join("\t".join(r.as_tuple()) for r in self._rows)
        self.clipboard_clear()
        self.clipboard_append(text)
