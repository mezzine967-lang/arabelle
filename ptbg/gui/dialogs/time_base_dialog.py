"""Configuration de la base de temps d'un fichier.

- REQ_COMMON_KH_2305 / 2306 / 2307 : format (compteur, heure, date-heure) et unité ;
- REQ_COMMON_KH_4106 : l'utilisateur impose le raster normal (période +
  tolérance) et saisit un diagnostic associé, imprimé dans le TBM et le rapport ;
- REQ_COMMON_KH_4107 : origine absolue (date-heure du compteur 0, c'est-à-dire
  du déclenchement en cas de pré-déclenchement) et choix « jitter ignoré » ;
- REQ_COMMON_KH_2102 : décalage manuel d'un PLC non synchronisé.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ptbg.core.data_package import SourceFile
from ptbg.core.time_base import ms
from ptbg.core.time_parser import UNIT_LABELS, TimeBaseSettings, TimeFormat, parse_absolute
from ptbg.gui.dialogs.base import Dialog

FORMATS = list(TimeFormat)
UNITS = ["auto"] + list(UNIT_LABELS)


def _float_or_none(text: str):
    """Texte -> nombre (virgule décimale acceptée) ; texte vide -> None."""
    text = text.strip().replace(",", ".")
    return float(text) if text else None


class TimeBaseDialog(Dialog):
    """Renvoie ``self.result`` = nouveau ``TimeBaseSettings`` ou None (annulé)."""

    def __init__(self, parent, source: SourceFile, default_tolerance: float, others_assumed: int = 0) -> None:
        """Mémorise le fichier et la tolérance par défaut, puis ouvre le dialogue modal.

        ``others_assumed`` : nombre d'autres fichiers dont l'unité de compteur est
        supposée ; s'il y en a, l'unité choisie peut leur être appliquée d'un coup."""
        self.source = source
        self.default_tolerance = default_tolerance
        self.others_assumed = others_assumed
        self.share_unit = False
        super().__init__(parent, f"Base de temps — {source.name}")

    def body(self, master):
        """Résumé de la détection, champs de réglage et diagnostic opérateur."""
        ts = self.source.time_settings
        analysis = self.source.analysis
        raw = ", ".join(self.source.table.time_raw[:4])
        info = (f"Colonne de temps (1re colonne, REQ 2304) : « {self.source.table.time_name} » — "
                f"premières valeurs : {raw}\nDétecté : {self.source.conversion.description}\n"
                f"Statut actuel : {self.source.time_status().label} — {analysis.summary()}")
        ttk.Label(master, text=info, wraplength=620, justify="left").grid(row=0, column=0, columnspan=3,
                                                                          sticky="w", pady=(0, 8))
        self.fmt = tk.StringVar(value=ts.fmt.label)
        self.unit = tk.StringVar(value=ts.unit)
        self.period = tk.StringVar(value="" if ts.nominal_period_s is None else ms(ts.nominal_period_s))
        self.tolerance = tk.StringVar(value="" if ts.tolerance_pct is None else f"{ts.tolerance_pct:g}")
        self.origin = tk.StringVar(value=ts.origin)
        self.offset = tk.StringVar(value=f"{ts.offset_s:g}" if ts.offset_s else "")
        self.ignore_jitter = tk.BooleanVar(value=ts.ignore_jitter)
        self.hide_aberrant = tk.BooleanVar(value=ts.hide_aberrant)
        rows = (
            ("Format de l'horodatage", ttk.Combobox(master, textvariable=self.fmt, state="readonly",
                                                    values=[f.label for f in FORMATS], width=30), ""),
            ("Unité du compteur", ttk.Combobox(master, textvariable=self.unit, state="readonly",
                                               values=UNITS, width=30),
             "auto = lue dans l'en-tête (t_ms, time[s]…), sinon préférence ; cycle = × période"),
            ("Période nominale (ms)", ttk.Entry(master, textvariable=self.period, width=32),
             f"vide = période estimée ({ms(analysis.period_estimated_s)} ms)"),
            ("Tolérance de la période (%)", ttk.Entry(master, textvariable=self.tolerance, width=32),
             f"vide = préférence ({self.default_tolerance:g} %) ; jitter accepté dans cette limite"),
            ("Origine absolue", ttk.Entry(master, textvariable=self.origin, width=32),
             "AAAA-MM-JJ HH:MM:SS.fraction (instant du compteur 0 / du déclenchement) ; "
             "pour hh:mm:ss : la date"),
            ("Décalage manuel (s)", ttk.Entry(master, textvariable=self.offset, width=32),
             "alignement d'un PLC non synchronisé (affiché dans le TBM)"),
        )
        for row, (label, widget, hint) in enumerate(rows, start=1):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky="w", padx=(0, 6), pady=2)
            widget.grid(row=row, column=1, sticky="w", pady=2)
            ttk.Label(master, text=hint, foreground="#555555", wraplength=330).grid(row=row, column=2, sticky="w")
        ttk.Checkbutton(master, text="Affichage régularisé sur le raster (jitter ignoré, REQ 4107) — "
                                     "décoché : horodatage brut du fichier (référence)",
                        variable=self.ignore_jitter).grid(row=7, column=0, columnspan=3, sticky="w", pady=4)
        ttk.Checkbutton(master, text="Masquer sur les courbes les horodatages aberrants isolés — décoché : "
                                     "affichés à leur instant brut (toujours signalés dans le TBM)",
                        variable=self.hide_aberrant).grid(row=8, column=0, columnspan=3, sticky="w", pady=2)
        ttk.Label(master, text="Diagnostic opérateur associé (REQ 4106) :").grid(row=9, column=0, columnspan=3,
                                                                                sticky="w")
        self.note = tk.Text(master, width=80, height=3, wrap="word")
        self.note.insert("1.0", ts.operator_note)
        self.note.grid(row=10, column=0, columnspan=3, sticky="ew")
        self.unit_to_others = tk.BooleanVar(value=False)
        if self.others_assumed:
            ttk.Checkbutton(master, text=f"Appliquer aussi cette unité aux {self.others_assumed} autre(s) "
                                         "fichier(s) dont l'unité est supposée (REQ 2307)",
                            variable=self.unit_to_others).grid(row=11, column=0, columnspan=3, sticky="w", pady=4)
        return rows[2][1]

    def validate(self) -> bool:
        """Vérifie période, tolérance, décalage, origine et unité « cycle »."""
        try:
            period = _float_or_none(self.period.get())
            tolerance = _float_or_none(self.tolerance.get())
            offset = _float_or_none(self.offset.get()) or 0.0
        except ValueError:
            messagebox.showerror("Base de temps", "Période, tolérance et décalage doivent être numériques.",
                                 parent=self)
            return False
        if (period is not None and period <= 0) or (tolerance is not None and not 0 < tolerance < 100):
            messagebox.showerror("Base de temps", "La période doit être > 0 et la tolérance entre 0 et 100 %.",
                                 parent=self)
            return False
        if self.origin.get().strip() and parse_absolute(self.origin.get()) is None:
            messagebox.showerror("Base de temps", "Origine illisible : utiliser AAAA-MM-JJ HH:MM:SS.fraction "
                                 "ou JJ/MM/AAAA HH:MM:SS.", parent=self)
            return False
        if self.unit.get() == "cycle" and period is None:
            messagebox.showerror("Base de temps", "L'unité « cycles PLC » exige la période nominale.", parent=self)
            return False
        self._values = (period, tolerance, offset)
        return True

    def apply(self) -> None:
        """Résultat : nouveaux réglages ``TimeBaseSettings`` du fichier."""
        period, tolerance, offset = self._values
        fmt = next(f for f in FORMATS if f.label == self.fmt.get())
        self.result = TimeBaseSettings(
            fmt=fmt, unit=self.unit.get(), nominal_period_s=None if period is None else period / 1000.0,
            tolerance_pct=tolerance, origin=self.origin.get().strip(), offset_s=offset,
            ignore_jitter=self.ignore_jitter.get(), hide_aberrant=self.hide_aberrant.get(),
            operator_note=self.note.get("1.0", "end").strip())
        self.share_unit = self.unit_to_others.get() and self.unit.get() != "auto"
