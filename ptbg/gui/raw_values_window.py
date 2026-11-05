"""Fenêtre « Valeurs du CSV » : texte d'origine des cellules à côté de la valeur lue.

Ouverte par clic droit sur une ou plusieurs variables de l'arbre. Le fichier
est relu sur le disque (``core.raw_view``), une page de lignes à la fois.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ptbg.core.data_package import SourceFile
from ptbg.core.raw_view import PAGE_ROWS, find_sample, read_rows, time_steps_ms, value_text

MAX_VARIABLES = 6        # variables affichées côte à côte au plus

NOTE = ("Texte du fichier : relu sur le disque, tel qu'il est écrit dans le CSV.   "
        "Valeur lue : ce que l'outil utilise pour les courbes et les calculs (une cellule vide reste vide, "
        "aucune valeur n'est ajoutée).   Δt : écart avec la mesure précédente, calculé en nanosecondes "
        "entières.")


class RawValuesWindow(tk.Toplevel):
    """Tableau paginé : ligne du fichier, temps, Δt, puis texte et valeur lue par variable."""

    def __init__(self, parent, source: SourceFile, names: list[str]) -> None:
        super().__init__(parent)
        self.source, self.table = source, source.table
        by_name = {column.name: column for column in self.table.columns}
        self.columns = [by_name[name] for name in names if name in by_name][:MAX_VARIABLES]
        self.title(f"Valeurs du CSV — {source.name}")
        self.geometry("1000x620")
        self.first = 0
        self.rows, self.page = [], []
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill="x")
        for text, command in (("|<", self.first_page), ("<", self.previous_page),
                              (">", self.next_page), (">|", self.last_page)):
            ttk.Button(bar, text=text, width=3, command=command).pack(side="left")
        self.position = ttk.Label(bar, padding=(8, 0))
        self.position.pack(side="left")
        ttk.Button(bar, text="Copier la page", command=self.copy_page).pack(side="right")
        self.goto = tk.StringVar()
        ttk.Button(bar, text="Aller", command=self.go_to_line).pack(side="right", padx=(2, 8))
        entry = ttk.Entry(bar, textvariable=self.goto, width=10)
        entry.pack(side="right")
        entry.bind("<Return>", lambda _e: self.go_to_line())
        ttk.Label(bar, text="Ligne du fichier :").pack(side="right", padx=2)
        self.alert = ttk.Label(self, foreground="#c62828", padding=(6, 0))
        self.alert.pack(fill="x")
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        keys = ["line", "time", "dt"] + [f"c{i}{part}" for i in range(len(self.columns)) for part in "fv"]
        self.view = ttk.Treeview(body, columns=keys, show="headings", selectmode="extended")
        headings = ["Ligne", f"{self.table.time_name} (fichier)", "Δt (ms)"]
        for column in self.columns:
            headings += [f"{column.name} (fichier)", f"{column.name} (valeur lue)"]
        for key, heading in zip(keys, headings):
            self.view.heading(key, text=heading)
            width = {"line": 70, "dt": 110}.get(key, 170)
            self.view.column(key, width=width, minwidth=60, anchor="w" if key == "time" else "e",
                             stretch=key not in ("line", "dt"))
        vertical = ttk.Scrollbar(body, orient="vertical", command=self.view.yview)
        horizontal = ttk.Scrollbar(body, orient="horizontal", command=self.view.xview)
        self.view.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.view.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        ttk.Label(self, text=NOTE, wraplength=960, foreground="#555555", padding=6).pack(fill="x")
        self.show_page(0)

    # --------------------------------------------------------------- pages
    def show_page(self, first: int) -> None:
        """Relit et affiche les mesures ``first`` à ``first + PAGE_ROWS``."""
        total = self.table.n_samples
        self.first = max(0, min(first, max(total - 1, 0)))
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            self.rows, changed = read_rows(self.table, [c.index for c in self.columns], self.first)
            alert = ("Attention : le fichier sur le disque ne correspond plus à celui chargé "
                     "(modifié ou remplacé depuis) : les textes affichés peuvent différer." if changed else "")
        except OSError as exc:
            self.rows, alert = [], f"Fichier illisible sur le disque : {exc.strerror or exc}."
        finally:
            self.configure(cursor="")
        self.alert.configure(text=alert)
        steps = time_steps_ms(self.source.conversion.seconds, self.first, len(self.rows))
        self.view.delete(*self.view.get_children())
        self.page = []           # textes affichés, gardés tels quels pour la copie
        for row, step in zip(self.rows, steps):
            values = [str(row.line), row.time_text, step]
            for column, text in zip(self.columns, row.cells):
                values += [text, value_text(column, row.sample)]
            self.page.append(values)
            self.view.insert("", "end", values=values)
        last = self.first + len(self.rows)
        self.position.configure(text=f"Mesures {self.first + 1} à {last} sur {total}" if self.rows
                                else f"Aucune mesure affichée sur {total}")

    def first_page(self) -> None:
        self.show_page(0)

    def previous_page(self) -> None:
        self.show_page(self.first - PAGE_ROWS)

    def next_page(self) -> None:
        if self.first + PAGE_ROWS < self.table.n_samples:
            self.show_page(self.first + PAGE_ROWS)

    def last_page(self) -> None:
        self.show_page(max(0, self.table.n_samples - PAGE_ROWS))

    def go_to_line(self) -> None:
        """Page commençant à la ligne du fichier saisie (ou à la mesure suivante)."""
        try:
            line = int(self.goto.get().strip())
        except ValueError:
            self.alert.configure(text="Numéro de ligne attendu (nombre entier).")
            return
        self.show_page(find_sample(self.table, line))

    def copy_page(self) -> None:
        """Copie la page affichée (colonnes séparées par des tabulations)."""
        lines = ["\t".join(self.view.heading(key, "text") for key in self.view["columns"])]
        lines += ["\t".join(values) for values in self.page]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
