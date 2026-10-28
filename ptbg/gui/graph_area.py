"""Zone graphique principale, à droite (REQ_COMMON_KH_5104, 5106).

Un ``ttk.Notebook`` gère plusieurs onglets ; chacun porte une disposition
d'axes issue d'un modèle (REQ_COMMON_KH_5300) et son propre Time Base Monitor.
Chaque onglet se ferme par sa croix « × », par un clic molette ou par son
menu (clic droit : renommer, fermer).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ptbg.core.arrangement import TabState, template
from ptbg.gui.analysis_tab import AnalysisTab


def _cross(color: str) -> tk.PhotoImage:
    """Croix de fermeture 10 × 10 dessinée pixel par pixel (aucun fichier image)."""
    image = tk.PhotoImage(width=10, height=10)
    for i in range(1, 9):
        for x, y in ((i, i), (9 - i, i)):
            image.put(color, (x, y))
            image.put(color, (min(x + 1, 9), y))
    return image


def _closable_style() -> tuple:
    """Style « Closable.TNotebook » : une croix après le titre de chaque onglet.

    Élément d'image ttk (grise, rouge au survol) ; renvoie les images, à
    conserver. Si le thème ne s'y prête pas, les onglets restent fermables par
    le clic molette, le clic droit et Ctrl+W."""
    images = (_cross("#777777"), _cross("#c62828"), _cross("#8e0000"))
    style = ttk.Style()
    try:
        style.element_create("close", "image", images[0], ("active", "pressed", "!disabled", images[2]),
                             ("active", "!disabled", images[1]), border=6, sticky="")
    except tk.TclError:
        pass                                  # déjà créé (second carnet) : réutilisé
    try:
        style.layout("Closable.TNotebook", [("Closable.TNotebook.client", {"sticky": "nswe"})])
        style.layout("Closable.TNotebook.Tab", [
            ("Closable.TNotebook.tab", {"sticky": "nswe", "children": [
                ("Closable.TNotebook.padding", {"side": "top", "sticky": "nswe", "children": [
                    ("Closable.TNotebook.focus", {"side": "top", "sticky": "nswe", "children": [
                        ("Closable.TNotebook.label", {"side": "left", "sticky": ""}),
                        ("Closable.TNotebook.close", {"side": "left", "sticky": ""})]})]})]})])
    except tk.TclError:
        pass
    return images


class GraphArea(ttk.Frame):
    """Carnet d'onglets d'analyse ; chaque onglet est un ``AnalysisTab``."""

    def __init__(self, master, controller) -> None:
        """Carnet d'onglets ; un changement d'onglet est signalé au contrôleur."""
        # Taille demandée fixe (pas de propagation) : la largeur réclamée par la
        # figure et les barres d'outils ne doit pas imposer la taille de la fenêtre.
        super().__init__(master, width=900, height=600)
        self.pack_propagate(False)
        self.controller = controller
        self._close_images = _closable_style()
        self.notebook = ttk.Notebook(self, style="Closable.TNotebook")
        self.notebook.pack(fill="both", expand=True)
        self.tabs: list[AnalysisTab] = []
        self._counter = 0
        self._pressed: int | None = None
        self.notebook.bind("<<NotebookTabChanged>>", lambda _e: controller.on_tab_changed())
        self.notebook.bind("<ButtonPress-1>", self._on_press, add=True)
        self.notebook.bind("<ButtonRelease-1>", self._on_release, add=True)
        self.notebook.bind("<Button-2>", self._on_middle_click, add=True)
        self.notebook.bind("<Button-3>", self._on_context_menu, add=True)

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

    def _tab_at(self, event) -> AnalysisTab | None:
        """Onglet dont le titre est sous la souris, ou None."""
        try:
            index = self.notebook.index(f"@{event.x},{event.y}")
        except tk.TclError:
            return None
        return self.tabs[index] if 0 <= index < len(self.tabs) else None

    def _on_press(self, event):
        """Appui sur la croix d'un onglet : mémorisé jusqu'au relâchement."""
        if "close" in self.notebook.identify(event.x, event.y):
            self._pressed = self.notebook.index(f"@{event.x},{event.y}")
            self.notebook.state(["pressed"])
            return "break"                 # ne pas sélectionner l'onglet
        return None

    def _on_release(self, event) -> None:
        """Relâchement sur la même croix : l'onglet est fermé."""
        pressed, self._pressed = self._pressed, None
        self.notebook.state(["!pressed"])
        if pressed is not None and "close" in self.notebook.identify(event.x, event.y) \
                and self.notebook.index(f"@{event.x},{event.y}") == pressed:
            self.controller.close_tab(self.tabs[pressed])

    def _on_middle_click(self, event) -> None:
        """Clic molette sur un titre : fermeture de l'onglet."""
        tab = self._tab_at(event)
        if tab is not None:
            self.controller.close_tab(tab)

    def _on_context_menu(self, event) -> None:
        """Clic droit sur un titre : renommer ou fermer l'onglet."""
        tab = self._tab_at(event)
        if tab is None:
            return
        self.notebook.select(tab)
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label="Renommer l'onglet…", command=self.controller.rename_tab)
        menu.add_command(label="Fermer l'onglet", command=lambda: self.controller.close_tab(tab))
        menu.tk_popup(event.x_root, event.y_root)

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
