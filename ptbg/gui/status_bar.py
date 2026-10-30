"""Barre d'état en bas de la fenêtre (REQ_COMMON_KH_5102).

Résume : l'UTILISATEUR, la DATE (horloge mise à jour chaque seconde), le
JOURNAL D'ACTIVITÉ (dernier message ; un clic ouvre le journal complet) et la
VERSION de l'outil. Elle porte aussi la barre d'avancement et le bouton
« Annuler » des traitements longs (REQ_COMMON_KH_4105).
"""
from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from ptbg.system.activity_log import LogEntry
from ptbg.system.compat import current_user
from ptbg.version import full_name

LEVEL_COLORS = {"INFO": "#202020", "AVERTISSEMENT": "#b35900", "ERREUR": "#c62828"}


class StatusBar(ttk.Frame):
    """Barre d'état : utilisateur | date | journal | avancement | version."""

    def __init__(self, master, controller) -> None:
        """Champs utilisateur, date, journal (cliquable), version ; avancement masqué."""
        super().__init__(master, padding=(6, 2), relief="groove")
        self.controller = controller
        self._clock = tk.StringVar()
        self._activity = tk.StringVar(value="Prêt.")
        ttk.Label(self, text=f"Utilisateur : {current_user()}").pack(side="left")
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(self, textvariable=self._clock, width=27).pack(side="left")
        ttk.Separator(self, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Label(self, text=full_name()).pack(side="right")
        ttk.Separator(self, orient="vertical").pack(side="right", fill="y", padx=6)
        self._cancel = ttk.Button(self, text="Annuler", command=controller.cancel_task, width=8)
        self._progress = ttk.Progressbar(self, length=160, mode="determinate", maximum=1.0)
        self._activity_label = tk.Label(self, textvariable=self._activity, anchor="w", cursor="hand2")
        self._activity_label.pack(side="left", fill="x", expand=True)
        self._activity_label.bind("<Button-1>", lambda _e: controller.show_log())
        self._tick()

    def _tick(self) -> None:
        """Met l'horloge à jour chaque seconde."""
        self._clock.set("Date : " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self._tick_job = self.after(1000, self._tick)

    def stop_clock(self) -> None:
        """Arrête l'horloge avant la fermeture (sinon Tk signale un appel orphelin)."""
        self.after_cancel(self._tick_job)

    def show_entry(self, entry: LogEntry) -> None:
        """Écouteur du journal : affiche le dernier message (fil principal)."""
        self._activity.set(f"Journal : {entry.message}")
        self._activity_label.configure(fg=LEVEL_COLORS.get(entry.level, "#202020"))

    def start_progress(self) -> None:
        """Affiche la barre d'avancement et le bouton « Annuler »."""
        self._progress.configure(value=0.0)
        self._cancel.pack(side="right", padx=4)
        self._progress.pack(side="right", padx=4)

    def set_progress(self, fraction: float, text: str = "") -> None:
        """Avancement entre 0 et 1, avec un texte facultatif."""
        self._progress.configure(value=max(0.0, min(1.0, fraction)))
        if text:
            self._activity.set(text)

    def stop_progress(self) -> None:
        """Masque la barre d'avancement."""
        self._progress.pack_forget()
        self._cancel.pack_forget()
