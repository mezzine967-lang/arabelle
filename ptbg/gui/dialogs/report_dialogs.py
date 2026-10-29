"""Dialogues du rapport PDF et des préférences.

- ``HeaderDialog``      : projet, unité, émetteur, référence (REQ_COMMON_KH_6005) ;
- ``PagesWindow``       : rapport pas à pas, pages ordonnées (REQ_COMMON_KH_6004) ;
- ``PreferencesDialog`` : taille maximale (REQ 2310), tolérance par défaut...
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

from ptbg.config import Settings
from ptbg.gui.dialogs.base import Dialog, ask_text
from ptbg.system.compat import current_user


class HeaderDialog(Dialog):
    """Saisie des champs libres de l'en-tête ; result = dict ou None."""

    def __init__(self, parent, settings: Settings) -> None:
        """Mémorise les préférences, puis ouvre le dialogue modal."""
        self.settings = settings
        super().__init__(parent, "En-tête du rapport")

    def body(self, master):
        """Champs libres de l'en-tête."""
        self.vars = {}
        fields = (("project_name", "Nom du projet"), ("project_unit", "Unité / tranche"),
                  ("issuer", f"Émetteur (vide = {current_user()})"),
                  ("project_reference", "Référence du projet / document"))
        first = None
        for row, (key, label) in enumerate(fields):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=getattr(self.settings, key))
            entry = ttk.Entry(master, textvariable=var, width=48)
            entry.grid(row=row, column=1, pady=2)
            self.vars[key] = var
            first = first or entry
        ttk.Label(master, foreground="#555555", wraplength=460, justify="left",
                  text="Version de l'outil, date, fichiers sources (SHA-256) et empreinte du fichier projet "
                       "sont ajoutés automatiquement.").grid(row=len(fields), column=0, columnspan=2, sticky="w")
        return first

    def apply(self) -> None:
        """Résultat : dictionnaire des champs saisis."""
        self.result = {key: var.get().strip() for key, var in self.vars.items()}


class PagesWindow(tk.Toplevel):
    """Liste ordonnée des pages capturées ; génération du PDF pas à pas."""

    def __init__(self, parent, controller) -> None:
        """Liste des pages et boutons d'organisation ; bouton de génération du PDF."""
        super().__init__(parent)
        self.title("Rapport pas à pas — pages")
        self.controller = controller
        self.listbox = tk.Listbox(self, width=80, height=12, exportselection=False)
        self.listbox.pack(fill="both", expand=True, padx=6, pady=6)
        buttons = ttk.Frame(self)
        buttons.pack(fill="x", padx=6, pady=(0, 6))
        for text, command in (("Monter", lambda: self._move(-1)), ("Descendre", lambda: self._move(1)),
                              ("Commentaire…", self._comment), ("Supprimer", self._delete),
                              ("Ajouter la vue active", self._add)):
            ttk.Button(buttons, text=text, command=command).pack(side="left", padx=2)
        ttk.Button(buttons, text="Générer le PDF…", command=controller.export_step_report).pack(side="right")
        self.refresh()

    def refresh(self) -> None:
        """Réaffiche la liste des pages dans leur ordre actuel."""
        self.listbox.delete(0, "end")
        for number, page in enumerate(self.controller.report_pages, start=1):
            comment = f" — {page.tab.comment}" if page.tab.comment else ""
            self.listbox.insert("end", f"{number}. {page.tab.title} (capture {page.captured_at}){comment}")

    def _selected(self) -> int | None:
        """Indice de la page sélectionnée, ou None."""
        selection = self.listbox.curselection()
        return selection[0] if selection else None

    def _move(self, step: int) -> None:
        """Déplace la page sélectionnée vers le haut (-1) ou le bas (+1)."""
        index = self._selected()
        pages = self.controller.report_pages
        if index is None or not 0 <= index + step < len(pages):
            return
        pages[index], pages[index + step] = pages[index + step], pages[index]
        self.refresh()
        self.listbox.selection_set(index + step)

    def _comment(self) -> None:
        """Modifie le commentaire imprimé sous le titre de la page."""
        index = self._selected()
        if index is None:
            return
        page = self.controller.report_pages[index]
        text = ask_text(self, "Commentaire de page", "Commentaire imprimé sous le titre :", page.tab.comment)
        if text is not None:
            page.tab.comment = text
            self.refresh()

    def _delete(self) -> None:
        """Supprime la page sélectionnée après confirmation."""
        index = self._selected()
        if index is not None and messagebox.askyesno("Rapport", "Supprimer cette page ?", parent=self):
            del self.controller.report_pages[index]
            self.refresh()

    def _add(self) -> None:
        """Capture la vue active comme nouvelle page."""
        self.controller.add_report_page()
        self.refresh()


class PreferencesDialog(Dialog):
    """Paramètres persistants ; result = dict des valeurs validées."""

    FIELDS = (
        ("max_file_size_mb", "Taille maximale d'un CSV (Mo) — REQ 2310 « xxxMo » à confirmer", float),
        ("tolerance_pct", "Tolérance par défaut de la période (%)", float),
        ("default_counter_unit", "Unité supposée d'un compteur sans unité (ns, us, ms, s)", str),
        ("frequency_change_min_run", "Intervalles consécutifs pour un changement de fréquence", int),
        ("aberrant_jump_periods", "Écart (périodes) d'un horodatage aberrant isolé", float),
        ("max_points_per_curve", "Points affichés par courbe avant réduction min/max", int),
    )

    def __init__(self, parent, settings: Settings) -> None:
        """Mémorise les préférences, puis ouvre le dialogue modal."""
        self.settings = settings
        super().__init__(parent, "Préférences")

    def body(self, master):
        """Un champ par préférence."""
        self.vars = {}
        for row, (key, label, _kind) in enumerate(self.FIELDS):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=str(getattr(self.settings, key)))
            ttk.Entry(master, textvariable=var, width=14).grid(row=row, column=1, sticky="w", padx=4)
            self.vars[key] = var
        return None

    def validate(self) -> bool:
        """Contrôle types et bornes avant enregistrement."""
        values = {}
        try:
            for key, _label, kind in self.FIELDS:
                values[key] = kind(self.vars[key].get().strip().replace(",", ".")) if kind is not str \
                    else self.vars[key].get().strip()
        except ValueError:
            messagebox.showerror("Préférences", "Valeur numérique invalide.", parent=self)
            return False
        if values["default_counter_unit"] not in ("ns", "us", "ms", "s", "min", "h"):
            messagebox.showerror("Préférences", "Unité inconnue.", parent=self)
            return False
        if values["max_file_size_mb"] <= 0 or values["frequency_change_min_run"] < 2 \
                or values["aberrant_jump_periods"] < 2 \
                or values["max_points_per_curve"] < 200 or not 0 < values["tolerance_pct"] < 100:
            messagebox.showerror("Préférences", "Valeur hors limites.", parent=self)
            return False
        self._values = values
        return True

    def apply(self) -> None:
        """Résultat : valeurs validées, prêtes à enregistrer."""
        self.result = self._values
