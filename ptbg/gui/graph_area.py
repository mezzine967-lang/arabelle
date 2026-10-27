"""Zone graphique principale, à droite (REQ_COMMON_KH_5104, 5106).

Un ``ttk.Notebook`` gère plusieurs onglets ; chacun porte une disposition
d'axes issue d'un modèle (REQ_COMMON_KH_5300) et son propre Time Base Monitor.
"""
from __future__ import annotations

from tkinter import ttk

from ptbg.core.arrangement import TabState, template
from ptbg.gui.analysis_tab import AnalysisTab


class GraphArea(ttk.Frame):
    """Carnet d'onglets d'analyse ; chaque onglet est un ``AnalysisTab``."""

    def __init__(self, master, controller) -> None:
        """Carnet d'onglets ; un changement d'onglet est signalé au contrôleur."""
        # Taille demandée fixe (pas de propagation) : la largeur réclamée par la
        # figure et les barres d'outils ne doit pas imposer la taille de la fenêtre.
        super().__init__(master, width=900, height=600)
        self.pack_propagate(False)
        self.controller = controller
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.tabs: list[AnalysisTab] = []
        self._counter = 0
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: controller.on_tab_changed())

    def new_tab(self, key: str, state: TabState | None = None) -> AnalysisTab:
        """Crée un onglet depuis un modèle (ou un état sauvegardé)."""
        self._counter += 1
        state = state or TabState.from_template(key, f"Analyse {self._counter} — {template(key).name}")
        tab = AnalysisTab(self.notebook, self.controller, state)
        self.tabs.append(tab)
        self.notebook.add(tab, text=state.title)
        self.notebook.select(tab)
        tab.redraw()
        return tab

    def active_tab(self) -> AnalysisTab | None:
        """Onglet affiché, ou None."""
        if not self.tabs:
            return None
        current = self.notebook.select()
        return next((tab for tab in self.tabs if str(tab) == current), self.tabs[-1])

    def close_tab(self, tab: AnalysisTab) -> None:
        """Libère proprement puis retire un onglet."""
        self.tabs.remove(tab)
        tab.dispose()
        self.notebook.forget(tab)
        tab.destroy()

    def rename_tab(self, tab: AnalysisTab, title: str) -> None:
        """Change le titre d'un onglet."""
        tab.state.title = title
        self.notebook.tab(tab, text=title)

    def redraw_all(self) -> None:
        """Redessine tous les onglets (données ou axe des temps modifiés)."""
        for tab in self.tabs:
            tab.redraw()
