"""Dialogues des outils d'analyse.

- ``GroupDialog``                : groupe binaire (REQ_COMMON_KH_2201, 2e occurrence) ;
- ``HorizontalCursorDialog``     : curseur horizontal (REQ 5406) conditionné par
                                   un ou plusieurs Bool (REQ 5407) ;
- ``XYDialog``                   : nuage X/Y et mode du curseur X/Y (REQ 5408) ;
- ``ConditionalProcessingWindow``: statistiques sous condition (section 4.5,
                                   REQ 5500 sans énoncé : proposition documentée).
"""
from __future__ import annotations

import csv
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from ptbg.core.arrangement import AxleState, CurveRef
from ptbg.core.conditional import (STATS_HEADER, Condition, ConditionTerm, conditional_statistics, evaluate)
from ptbg.core.data_package import SourceFile, Workspace
from ptbg.gui.dialogs.base import Dialog


def _labels(sources: list[SourceFile]) -> list[str]:
    """Libellés uniques des fichiers (deux CSV peuvent porter le même nom)."""
    labels = []
    for source in sources:
        label = source.name
        while label in labels:
            label += "*"
        labels.append(label)
    return labels


class GroupDialog(Dialog):
    """Choix du nom et des membres Bool d'un groupe ; result = (nom, membres)."""

    def __init__(self, parent, source: SourceFile, preselected: list[str]) -> None:
        """Mémorise le fichier et les Bool présélectionnés, puis ouvre le dialogue modal."""
        self.source, self.preselected = source, preselected
        super().__init__(parent, f"Groupe binaire — {source.name}")

    def body(self, master):
        """Champ du nom et liste des Bool du fichier (le 1er choisi = bit 0)."""
        ttk.Label(master, text="Nom du groupe :").grid(row=0, column=0, sticky="w")
        self.name = tk.StringVar(value="Groupe_" + (self.preselected[0] if self.preselected else "1"))
        entry = ttk.Entry(master, textvariable=self.name, width=40)
        entry.grid(row=0, column=1, sticky="w")
        ttk.Label(master, text="Bits du groupe (le 1er = bit 0) :").grid(row=1, column=0, columnspan=2, sticky="w",
                                                                         pady=(6, 0))
        self.names = self.source.bool_names()
        self.listbox = tk.Listbox(master, selectmode="extended", height=min(14, max(4, len(self.names))), width=50,
                                  exportselection=False)
        for position, name in enumerate(self.names):
            self.listbox.insert("end", name)
            if name in self.preselected:
                self.listbox.selection_set(position)
        self.listbox.grid(row=2, column=0, columnspan=2, sticky="nsew")
        if not self.names:
            ttk.Label(master, text="Aucune variable Bool dans ce fichier (forcer le type si besoin).",
                      foreground="#c62828").grid(row=3, column=0, columnspan=2)
        return entry

    def validate(self) -> bool:
        """Exige un nom et au moins deux bits."""
        if not self.name.get().strip() or len(self.listbox.curselection()) < 2:
            messagebox.showerror("Groupe binaire", "Donner un nom et choisir au moins deux Bool.", parent=self)
            return False
        return True

    def apply(self) -> None:
        """Résultat : (nom, membres dans l'ordre des bits)."""
        self.result = (self.name.get().strip(), [self.names[i] for i in self.listbox.curselection()])


class ConditionFrame(ttk.LabelFrame):
    """Jusqu'à trois termes « Bool = état » combinés par ET / OU (REQ 5407)."""

    ROWS = 3

    def __init__(self, master, workspace: Workspace, condition: Condition | None) -> None:
        """Construit les lignes fichier / signal / état et le choix ET / OU."""
        super().__init__(master, text="Condition Bool (optionnelle)", padding=6)
        self.sources = [s for s in workspace.loaded_files() if s.bool_names()]
        self.labels = _labels(self.sources)
        self.combine = tk.StringVar(value=condition.combine if condition else "AND")
        self.rows = []
        terms = list(condition.terms) if condition else []
        for row in range(self.ROWS):
            term = terms[row] if row < len(terms) else None
            file_var, signal_var, state_var = tk.StringVar(), tk.StringVar(), tk.StringVar(value="1 (vrai)")
            file_box = ttk.Combobox(self, textvariable=file_var, values=[""] + self.labels, state="readonly", width=26)
            signal_box = ttk.Combobox(self, textvariable=signal_var, state="readonly", width=24)
            state_box = ttk.Combobox(self, textvariable=state_var, values=["1 (vrai)", "0 (faux)"],
                                     state="readonly", width=8)
            file_box.grid(row=row, column=0, padx=2, pady=2)
            ttk.Label(self, text="signal").grid(row=row, column=1)
            signal_box.grid(row=row, column=2, padx=2)
            ttk.Label(self, text="=").grid(row=row, column=3)
            state_box.grid(row=row, column=4, padx=2)
            file_box.bind("<<ComboboxSelected>>", lambda _e, r=row: self._file_changed(r))
            self.rows.append((file_var, signal_var, state_var, signal_box))
            source = next((s for s in self.sources if term and s.id == term.file_id), None)
            if source is not None:
                file_var.set(self.labels[self.sources.index(source)])
                self._file_changed(row)
                signal_var.set(term.signal)
                state_var.set("1 (vrai)" if term.expected else "0 (faux)")
        combine = ttk.Frame(self)
        combine.grid(row=self.ROWS, column=0, columnspan=5, sticky="w")
        ttk.Radiobutton(combine, text="ET (toutes vraies)", value="AND", variable=self.combine).pack(side="left")
        ttk.Radiobutton(combine, text="OU (au moins une)", value="OR", variable=self.combine).pack(side="left")
        ttk.Label(self, foreground="#555555", wraplength=560, justify="left",
                  text="Même fichier : état lu sur la même ligne. Autre fichier : dernier état connu sur l'axe des "
                       "temps commun. Bool vide ou invalide : condition fausse.").grid(
            row=self.ROWS + 1, column=0, columnspan=5, sticky="w")

    def _file_changed(self, row: int) -> None:
        """Fichier choisi : propose ses signaux Bool."""
        file_var, signal_var, _state, signal_box = self.rows[row]
        if file_var.get() in self.labels:
            source = self.sources[self.labels.index(file_var.get())]
            signal_box["values"] = source.bool_names()
        else:
            signal_box["values"] = []
        signal_var.set("")

    def condition(self) -> Condition | None:
        """Condition saisie, ou None si aucune ligne n'est complète."""
        terms = []
        for file_var, signal_var, state_var, _box in self.rows:
            if file_var.get() in self.labels and signal_var.get():
                source = self.sources[self.labels.index(file_var.get())]
                terms.append(ConditionTerm(source.id, signal_var.get(), state_var.get().startswith("1")))
        return Condition(terms, self.combine.get()) if terms else None


class HorizontalCursorDialog(Dialog):
    """Niveau du curseur horizontal et condition ; result = (actif, niveau, condition)."""

    def __init__(self, parent, workspace: Workspace, axle: AxleState, suggested_level: float) -> None:
        """Mémorise l'axe et le niveau suggéré, puis ouvre le dialogue modal."""
        self.workspace, self.axle, self.suggested = workspace, axle, suggested_level
        super().__init__(parent, "Curseur horizontal (signal analogique)")

    def body(self, master):
        """Niveau du curseur et cadre de condition."""
        self.enabled = tk.BooleanVar(value=True)
        level = self.axle.h_level if self.axle.h_level is not None else self.suggested
        self.level = tk.StringVar(value=f"{level:.6g}")
        ttk.Checkbutton(master, text="Curseur horizontal actif sur l'axe", variable=self.enabled).grid(
            row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(master, text="Niveau :").grid(row=1, column=0, sticky="w")
        entry = ttk.Entry(master, textvariable=self.level, width=20)
        entry.grid(row=1, column=1, sticky="w")
        self.condition_frame = ConditionFrame(master, self.workspace, self.axle.h_condition)
        self.condition_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=6)
        ttk.Label(master, foreground="#555555", wraplength=560, justify="left",
                  text="Le niveau se déplace aussi à la souris (glisser la ligne ou Maj+clic). Seuls les "
                       "franchissements survenant pendant que la condition est vraie sont retenus ; les "
                       "périodes où elle est vraie sont ombrées.").grid(row=3, column=0, columnspan=2, sticky="w")
        return entry

    def validate(self) -> bool:
        """Le niveau doit être numérique."""
        try:
            self._level = float(self.level.get().replace(",", "."))
            return True
        except ValueError:
            messagebox.showerror("Curseur horizontal", "Le niveau doit être numérique.", parent=self)
            return False

    def apply(self) -> None:
        """Résultat : (actif, niveau, condition)."""
        self.result = (self.enabled.get(), self._level, self.condition_frame.condition())


class XYDialog(Dialog):
    """Choix des signaux X et Y ; result = (CurveRef X, CurveRef Y, mode du curseur)."""

    def __init__(self, parent, workspace: Workspace, axle: AxleState) -> None:
        """Mémorise l'axe X/Y à configurer, puis ouvre le dialogue modal."""
        self.workspace, self.axle = workspace, axle
        super().__init__(parent, "Nuage X/Y — contrôle de corrélation")

    def body(self, master):
        """Choix fichier / signal pour X et Y, et mode d'affichage du curseur X/Y."""
        self.sources = self.workspace.loaded_files()
        self.labels = _labels(self.sources)
        self.vars = {}
        for row, (axis, ref) in enumerate((("X", self.axle.xy_x), ("Y", self.axle.xy_y))):
            file_var, signal_var = tk.StringVar(), tk.StringVar()
            ttk.Label(master, text=f"Signal {axis} :").grid(row=row, column=0, sticky="w")
            file_box = ttk.Combobox(master, textvariable=file_var, values=self.labels, state="readonly", width=28)
            signal_box = ttk.Combobox(master, textvariable=signal_var, state="readonly", width=28)
            file_box.grid(row=row, column=1, padx=2, pady=2)
            signal_box.grid(row=row, column=2, padx=2)
            file_box.bind("<<ComboboxSelected>>", lambda _e, a=axis: self._file_changed(a))
            self.vars[axis] = (file_var, signal_var, signal_box)
            source = next((s for s in self.sources if ref and s.id == ref.file_id), None)
            if source is not None:
                file_var.set(self.labels[self.sources.index(source)])
                self._file_changed(axis)
                signal_var.set(ref.name)
        self.mode = tk.StringVar(value=self.axle.xy_mode)
        ttk.Radiobutton(master, text="Deux curseurs (droites X et Y)", value="two_cursors",
                        variable=self.mode).grid(row=2, column=0, columnspan=3, sticky="w")
        ttk.Radiobutton(master, text="Point de croisement seul", value="cross_point",
                        variable=self.mode).grid(row=3, column=0, columnspan=3, sticky="w")
        ttk.Label(master, foreground="#555555", wraplength=520, justify="left",
                  text="Même fichier : points formés sur la même ligne. Fichiers différents : échantillon Y le "
                       "plus proche à moins d'une demi-période, sans interpolation. Cliquer sur le nuage pour "
                       "désigner un point ; les curseurs C1/C2 du 1er axe temporel y sont reportés.").grid(
            row=4, column=0, columnspan=3, sticky="w", pady=4)

    def _file_changed(self, axis: str) -> None:
        """Fichier choisi : propose ses signaux Float et Bool."""
        file_var, signal_var, signal_box = self.vars[axis]
        if file_var.get() in self.labels:
            source = self.sources[self.labels.index(file_var.get())]
            signal_box["values"] = source.float_names() + source.bool_names()
        signal_var.set("")

    def validate(self) -> bool:
        """Fichier et signal obligatoires pour X et Y."""
        refs = []
        for axis in ("X", "Y"):
            file_var, signal_var, _box = self.vars[axis]
            if file_var.get() not in self.labels or not signal_var.get():
                messagebox.showerror("Nuage X/Y", f"Choisir le fichier et le signal {axis}.", parent=self)
                return False
            refs.append(CurveRef(self.sources[self.labels.index(file_var.get())].id, signal_var.get()))
        self._refs = refs
        return True

    def apply(self) -> None:
        """Résultat : (référence X, référence Y, mode du curseur X/Y)."""
        self.result = (self._refs[0], self._refs[1], self.mode.get())


class ConditionalProcessingWindow(tk.Toplevel):
    """Statistiques des signaux analogiques pendant que la condition est vraie."""

    def __init__(self, parent, workspace: Workspace, notify) -> None:
        """Condition, choix des signaux, seuil optionnel et tableau des résultats."""
        super().__init__(parent)
        self.title("Traitement conditionnel")
        self.workspace, self.notify = workspace, notify
        self.condition_frame = ConditionFrame(self, workspace, None)
        self.condition_frame.pack(fill="x", padx=6, pady=4)
        pick = ttk.LabelFrame(self, text="Signaux analogiques à traiter", padding=4)
        pick.pack(fill="both", expand=True, padx=6)
        self.choices = [(s, name) for s in workspace.loaded_files() for name in s.float_names()]
        self.listbox = tk.Listbox(pick, selectmode="extended", height=8, exportselection=False)
        for source, name in self.choices:
            self.listbox.insert("end", f"{name}  [{source.name}]")
        self.listbox.pack(fill="both", expand=True)
        options = ttk.Frame(self)
        options.pack(fill="x", padx=6, pady=4)
        ttk.Label(options, text="Seuil optionnel :").pack(side="left")
        self.threshold = tk.StringVar()
        ttk.Entry(options, textvariable=self.threshold, width=12).pack(side="left", padx=4)
        ttk.Button(options, text="Calculer", command=self.compute).pack(side="left", padx=4)
        ttk.Button(options, text="Exporter CSV…", command=self.export).pack(side="right")
        ttk.Button(options, text="Copier", command=self.copy).pack(side="right", padx=4)
        self.table = ttk.Treeview(self, columns=STATS_HEADER, show="headings", height=8)
        for name in STATS_HEADER:
            self.table.heading(name, text=name)
            self.table.column(name, width=95, stretch=name == "Signal")
        self.table.pack(fill="both", expand=True, padx=6, pady=(0, 6))
        self.results: list = []

    def compute(self) -> None:
        """Calcule les statistiques de chaque signal choisi sous la condition."""
        condition = self.condition_frame.condition()
        if condition is None:
            messagebox.showerror("Traitement conditionnel", "Définir au moins un terme de condition.", parent=self)
            return
        try:
            level = float(self.threshold.get().replace(",", ".")) if self.threshold.get().strip() else None
        except ValueError:
            messagebox.showerror("Traitement conditionnel", "Seuil non numérique.", parent=self)
            return
        timeline = self.workspace.timeline()
        self.results = []
        for position in self.listbox.curselection():
            source, name = self.choices[position]
            mask = evaluate(condition, source, self.workspace.find, timeline)
            stats = conditional_statistics(f"{name} [{source.name}]", timeline.x(source),
                                           source.signal(name).values, mask, level)
            self.results.append(stats.as_row())
        self.table.delete(*self.table.get_children())
        for row in self.results:
            self.table.insert("", "end", values=row)
        self.notify(f"Traitement conditionnel ({condition.describe()}) : {len(self.results)} signal(aux).")

    def copy(self) -> None:
        """Copie le tableau (texte tabulé) dans le presse-papiers."""
        self.clipboard_clear()
        self.clipboard_append("\n".join("\t".join(r) for r in [STATS_HEADER] + self.results))

    def export(self) -> None:
        """Exporte le tableau en CSV (UTF-8, séparateur virgule)."""
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", encoding="utf-8", newline="") as handle:
                csv.writer(handle).writerows([STATS_HEADER] + self.results)
            self.notify(f"Résultats du traitement conditionnel exportés : {path}")
