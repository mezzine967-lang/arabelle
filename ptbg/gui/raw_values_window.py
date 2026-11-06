"""Fenêtre « Valeurs du CSV » : texte d'origine des cellules à côté de la valeur lue.

Ouverte par clic droit sur une ou plusieurs variables de l'arbre, ou par clic
droit sur un marqueur du Time Base Monitor (« Voir dans le CSV », la ligne de
l'anomalie est alors surlignée). Le fichier est relu sur le disque
(``core.raw_view``), une page de lignes à la fois.

- Colonne « Remarque » : anomalie de temps de la mesure et cellules à problème ;
  ces lignes sont teintées.
- Case « Seulement les anomalies » : n'affiche que ces lignes.
- Double-clic sur une ligne : le curseur global de l'onglet actif est placé à
  l'instant de cette mesure (lien entre le fichier et les courbes).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

import numpy as np

from ptbg.core.data_package import SourceFile
from ptbg.core.raw_view import (PAGE_ROWS, anomaly_samples, find_sample, read_rows, remarks, time_steps_ms,
                                value_text)

MAX_VARIABLES = 6        # variables affichées côte à côte au plus
CONTEXT_ROWS = 5         # lignes visibles au-dessus de la ligne recherchée
ANOMALY_COLOR = "#fde7d4"  # fond des lignes qui ont une remarque

NOTE = ("Texte du fichier : relu sur le disque, tel qu'il est écrit dans le CSV.   "
        "Valeur lue : ce que l'outil utilise pour les courbes et les calculs (une cellule vide reste vide, "
        "aucune valeur n'est ajoutée).   Δt : écart avec la mesure précédente, calculé en nanosecondes "
        "entières.   Double-clic sur une ligne : curseur global placé à cet instant sur les courbes.")


class RawValuesWindow(tk.Toplevel):
    """Tableau paginé : ligne du fichier, temps, Δt, remarque, puis texte et valeur lue par variable.

    ``on_pick(source, n° de mesure)`` est appelé au double-clic sur une ligne."""

    def __init__(self, parent, source: SourceFile, names: list[str], on_pick=None) -> None:
        super().__init__(parent)
        self.source, self.table, self.on_pick = source, source.table, on_pick
        by_name = {column.name: column for column in self.table.columns}
        self.columns = [by_name[name] for name in names if name in by_name][:MAX_VARIABLES]
        self.title(f"Valeurs du CSV — {source.name}")
        self.geometry("1100x620")
        self.samples = np.arange(self.table.n_samples)     # mesures parcourues (toutes ou anomalies)
        self.first = 0                                      # position de la page dans ``samples``
        self.rows, self.page = [], []
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill="x")
        for text, command in (("|<", self.first_page), ("<", self.previous_page),
                              (">", self.next_page), (">|", self.last_page)):
            ttk.Button(bar, text=text, width=3, command=command).pack(side="left")
        self.position = ttk.Label(bar, padding=(8, 0))
        self.position.pack(side="left")
        self.only_anomalies = tk.BooleanVar(value=False)
        ttk.Checkbutton(bar, text="Seulement les anomalies", variable=self.only_anomalies,
                        command=self.toggle_anomalies).pack(side="left", padx=12)
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
        keys = ["line", "time", "dt", "remark"] + [f"c{i}{part}" for i in range(len(self.columns)) for part in "fv"]
        self.view = ttk.Treeview(body, columns=keys, show="headings", selectmode="extended")
        headings = ["Ligne", f"{self.table.time_name} (fichier)", "Δt (ms)", "Remarque"]
        for column in self.columns:
            headings += [f"{column.name} (fichier)", f"{column.name} (valeur lue)"]
        for key, heading in zip(keys, headings):
            self.view.heading(key, text=heading)
            width = {"line": 70, "dt": 110, "remark": 300}.get(key, 170)
            self.view.column(key, width=width, minwidth=60, anchor="w" if key in ("time", "remark") else "e",
                             stretch=key not in ("line", "dt"))
        self.view.tag_configure("anomaly", background=ANOMALY_COLOR)
        self.view.bind("<Double-1>", self._on_double_click)
        vertical = ttk.Scrollbar(body, orient="vertical", command=self.view.yview)
        horizontal = ttk.Scrollbar(body, orient="horizontal", command=self.view.xview)
        self.view.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.view.grid(row=0, column=0, sticky="nsew")
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)
        ttk.Label(self, text=NOTE, wraplength=1060, foreground="#555555", padding=6).pack(fill="x")
        self.show_page(0)

    # --------------------------------------------------------------- pages
    def show_page(self, first: int) -> None:
        """Relit et affiche les mesures ``samples[first : first + PAGE_ROWS]``."""
        total = self.samples.size
        self.first = max(0, min(first, max(total - 1, 0)))
        page = self.samples[self.first:self.first + PAGE_ROWS]
        self.configure(cursor="watch")
        self.update_idletasks()
        try:
            self.rows, changed = read_rows(self.table, [c.index for c in self.columns], page)
            alert = ("Attention : le fichier sur le disque ne correspond plus à celui chargé "
                     "(modifié ou remplacé depuis) : les textes affichés peuvent différer." if changed else "")
        except OSError as exc:
            self.rows, alert = [], f"Fichier illisible sur le disque : {exc.strerror or exc}."
        finally:
            self.configure(cursor="")
        self.alert.configure(text=alert)
        shown = [row.sample for row in self.rows]
        steps = time_steps_ms(self.source.conversion.seconds, shown)
        notes = remarks(self.source, self.columns, shown)
        self.view.delete(*self.view.get_children())
        self.page = []           # textes affichés, gardés tels quels pour la copie
        for row, step, note in zip(self.rows, steps, notes):
            values = [str(row.line), row.time_text, step, note]
            for column, text in zip(self.columns, row.cells):
                values += [text, value_text(column, row.sample)]
            self.page.append(values)
            self.view.insert("", "end", values=values, tags=("anomaly",) if note else ())
        what = "Anomalies" if self.only_anomalies.get() else "Mesures"
        if self.rows:
            self.position.configure(text=f"{what} {self.first + 1} à {self.first + len(self.rows)} sur {total}")
        else:
            self.position.configure(text="Aucune anomalie" if self.only_anomalies.get()
                                    else f"Aucune mesure affichée sur {total}")

    def first_page(self) -> None:
        self.show_page(0)

    def previous_page(self) -> None:
        self.show_page(self.first - PAGE_ROWS)

    def next_page(self) -> None:
        if self.first + PAGE_ROWS < self.samples.size:
            self.show_page(self.first + PAGE_ROWS)

    def last_page(self) -> None:
        self.show_page(max(0, self.samples.size - PAGE_ROWS))

    def toggle_anomalies(self) -> None:
        """Case « Seulement les anomalies » : parcourt les lignes à remarque, ou toutes."""
        if self.only_anomalies.get():
            self.samples = anomaly_samples(self.source, self.columns)
        else:
            self.samples = np.arange(self.table.n_samples)
        self.show_page(0)

    def go_to_line(self) -> None:
        """Affiche la ligne du fichier saisie (ou la suivante parcourue) surlignée."""
        try:
            line = int(self.goto.get().strip())
        except ValueError:
            self.alert.configure(text="Numéro de ligne attendu (nombre entier).")
            return
        self.show_sample(find_sample(self.table, line))

    def show_sample(self, sample: int) -> None:
        """Mesure ``sample`` (ou la suivante parcourue) surlignée au milieu de sa page, les
        lignes d'avant visibles juste au-dessus."""
        target = int(np.searchsorted(self.samples, sample))
        self.show_page(max(0, min(target - PAGE_ROWS // 2, self.samples.size - PAGE_ROWS)))
        items = self.view.get_children()
        if not items:
            return
        item = items[min(max(target - self.first, 0), len(items) - 1)]
        self.view.selection_set(item)
        self.view.focus(item)
        position = items.index(item)
        self.view.yview_moveto(max(0, position - CONTEXT_ROWS) / len(items))

    def _on_double_click(self, event) -> None:
        """Double-clic sur une ligne : curseur global placé à l'instant de cette mesure."""
        item = self.view.identify_row(event.y)
        if item and self.on_pick is not None:
            self.on_pick(self.source, self.rows[self.view.index(item)].sample)

    def copy_page(self) -> None:
        """Copie la page affichée (colonnes séparées par des tabulations)."""
        lines = ["\t".join(self.view.heading(key, "text") for key in self.view["columns"])]
        lines += ["\t".join(values) for values in self.page]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))
