"""Onglet d'analyse graphique : une disposition d'axes et ses outils.

Requis servis (l'état est dans ``TabState``, le dessin dans plotting/renderer) :

- REQ_COMMON_KH_5104 / 5106 : zone graphique principale, un onglet par disposition ;
- REQ_COMMON_KH_5400 : curseur vertical simple, activé AXE PAR AXE (axe actif) ;
- REQ_COMMON_KH_5401 : il porte l'instant et la valeur de la courbe sélectionnée ;
- REQ_COMMON_KH_5402 : mode suivi (le curseur suit la souris) + panneau droit ;
- REQ_COMMON_KH_5403 / 5404 : double curseur, instants posés automatiquement ;
- REQ_COMMON_KH_5405 : curseur global sur tous les axes, déplacés ensemble ;
- REQ_COMMON_KH_5406 : curseur horizontal réservé aux axes analogiques ;
- REQ_COMMON_KH_5408 : désignation d'un point du nuage X/Y ;
- REQ_COMMON_KH_4103 : masquage du TBM refusé en cas d'alerte.

Souris : clic = placer le curseur, glisser = le déplacer, Maj+clic = niveau
du curseur horizontal, clic droit = menu de l'axe. Légende : glisser = la
déplacer (place conservée à l'écran, dans le projet et le rapport), clic sur
un nom = sélectionner cette courbe. Clavier : flèches gauche / droite =
échantillon précédent / suivant de la courbe sélectionnée.
Quand un outil de zoom ou de déplacement de la barre Matplotlib est actif,
les clics lui sont réservés.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk

import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure

from ptbg.core.arrangement import CurveRef, TabState
from ptbg.core.curves import resolve
from ptbg.core.readings import compute_readings, xy_data
from ptbg.core.sampling import step_index
from ptbg.core.signals import SignalType
from ptbg.core.xy import nearest_point
from ptbg.gui.reading_panel import ReadingPanel
from ptbg.plotting import monitor
from ptbg.plotting.renderer import TabRenderer
from ptbg.plotting.styles import ACTIVE_AXLE_COLOR, curve_color

PICK_TOLERANCE_PX = 8
FLOW_MARGIN = 4         # marge gauche et droite de la barre d'outils (pixels)
PANEL_WIDTH = 420       # largeur initiale du panneau de lecture (pixels)
CURSOR_MODES = (("none", "Aucun curseur vertical"), ("single", "Curseur simple"), ("double", "Double curseur"))


class FlowBar(ttk.Frame):
    """Barre d'outils dont les éléments passent à la ligne quand la largeur manque."""

    def __init__(self, master) -> None:
        """Barre vide ; ``add`` y range les éléments dans l'ordre."""
        super().__init__(master)
        self._items: list[tuple] = []          # (élément, espace après, début de ligne imposé)
        self._width = 0
        self.bind("<Configure>", self._reflow)

    def add(self, widget, gap: int = 4, new_line: bool = False):
        """Ajoute un élément (créé avec la barre pour parent) ; le renvoie."""
        self._items.append((widget, gap, new_line))
        return widget

    def _reflow(self, _event=None) -> None:
        """Place les éléments ligne par ligne selon la largeur disponible."""
        width = self.winfo_width()
        if width <= 1 or width == self._width:
            return
        self._width = width
        x, y, row_height = FLOW_MARGIN, 2, 0
        for widget, gap, new_line in self._items:
            needed, height = widget.winfo_reqwidth(), widget.winfo_reqheight()
            if x > FLOW_MARGIN and (new_line or x + needed > width - FLOW_MARGIN):
                x, y, row_height = FLOW_MARGIN, y + row_height + 2, 0
            widget.place(x=x, y=y)
            x += needed + gap
            row_height = max(row_height, height)
        self.configure(height=y + row_height + 2)


class AnalysisTab(ttk.Frame):
    """Un onglet : barre d'outils, figure Matplotlib, panneau de lecture."""

    def __init__(self, notebook, controller, state: TabState) -> None:
        """Crée la barre d'outils et la zone graphique ; le dessin est fait par ``redraw``."""
        super().__init__(notebook)
        self.controller = controller
        self.state = state
        self.active_axle = 0
        self.renderer: TabRenderer | None = None
        self._drag: str | None = None
        self._legend_press = None          # (axe, x, y) du clic sur une légende
        self._pending_motion = None
        self._resize_job = None
        self._refresh_job = None
        self._background = None            # rendu figé sans curseurs (mise à jour rapide)
        self._build_toolbar()
        self._build_body()

    # ------------------------------------------------------------- widgets
    def _build_toolbar(self) -> None:
        """Deux lignes d'outils : sélection (axe, courbe) puis curseurs et TBM ; dans une
        fenêtre étroite, les outils passent à la ligne au lieu de sortir de l'écran."""
        bar = FlowBar(self)
        bar.pack(fill="x")
        self.axle_choice = tk.StringVar()
        self.curve_choice = tk.StringVar()
        self.cursor_mode = tk.StringVar(value="none")
        self.global_cursor = tk.BooleanVar(value=self.state.global_cursor)
        self.tracking = tk.BooleanVar(value=self.state.tracking)
        self.show_panel = tk.BooleanVar(value=True)
        bar.add(ttk.Label(bar, text=f"Modèle : {self.state.template.name}"), gap=10)
        axle = ttk.Frame(bar)
        ttk.Label(axle, text="Axe actif").pack(side="left")
        self.axle_box = ttk.Combobox(axle, textvariable=self.axle_choice, width=10, state="readonly")
        self.axle_box.pack(side="left", padx=(2, 0))
        self.axle_box.bind("<<ComboboxSelected>>", lambda _e: self.set_active_axle(self.axle_box.current()))
        bar.add(axle, gap=10)
        curve = ttk.Frame(bar)
        ttk.Label(curve, text="Courbe sélectionnée").pack(side="left")
        self.curve_box = ttk.Combobox(curve, textvariable=self.curve_choice, width=28, state="readonly")
        self.curve_box.pack(side="left", padx=(2, 0))
        self.curve_box.bind("<<ComboboxSelected>>", lambda _e: self._select_curve(self.curve_box.current()))
        bar.add(curve, gap=10)
        bar.add(ttk.Button(bar, text="Retirer la courbe", command=self.remove_selected_curve))
        bar.add(ttk.Button(bar, text="Vider l'axe", command=self.clear_axle))
        cursor = ttk.Menubutton(bar, text="Curseur vertical")
        menu = tk.Menu(cursor, tearoff=False)
        for value, label in CURSOR_MODES:
            menu.add_radiobutton(label=label, value=value, variable=self.cursor_mode,
                                 command=lambda v=value: self.set_cursor_mode(v))
        cursor["menu"] = menu
        bar.add(cursor, gap=8, new_line=True)
        bar.add(ttk.Checkbutton(bar, text="Curseur global", variable=self.global_cursor,
                                command=self._toggle_global), gap=8)
        bar.add(ttk.Checkbutton(bar, text="Suivi souris", variable=self.tracking,
                                command=self._toggle_tracking), gap=8)
        bar.add(ttk.Button(bar, text="Curseur horizontal…", command=self.controller.horizontal_cursor))
        bar.add(ttk.Button(bar, text="Nuage X/Y…", command=self.controller.configure_xy))
        self.tbm_button = bar.add(ttk.Button(bar, text="Masquer le TBM", width=15, command=self.toggle_monitor))
        bar.add(ttk.Button(bar, text="Vue d'origine", command=self.reset_view), gap=10)
        bar.add(ttk.Checkbutton(bar, text="Panneau de lecture", variable=self.show_panel, command=self._toggle_panel))

    def _build_body(self) -> None:
        """Figure Matplotlib intégrée à Tk, barre de zoom et panneau de lecture."""
        self.paned = tk.PanedWindow(self, orient="horizontal", sashwidth=6, sashrelief="raised")
        self.paned.pack(fill="both", expand=True)
        holder = ttk.Frame(self.paned)
        self.figure = Figure(figsize=(9, 6), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.figure, master=holder)
        self.toolbar = NavigationToolbar2Tk(self.canvas, holder, pack_toolbar=False)
        self.toolbar.update()
        self.toolbar.pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.paned.add(holder, minsize=400, stretch="always")
        self.panel = ReadingPanel(self.paned)
        self.paned.add(self.panel, width=PANEL_WIDTH, minsize=150, stretch="never")
        hint = ttk.Label(self, foreground="#555555", padding=(4, 0),
                         text="Clic : placer le curseur · Glisser : le déplacer · Maj+clic : niveau du curseur H · "
                              "Flèches gauche/droite : échantillon voisin · Légende : glisser pour la déplacer, "
                              "clic sur un nom pour sélectionner la courbe · Clic droit : menu de l'axe · "
                              "Loupe/croix de la barre : zoom/déplacement", justify="left")
        hint.pack(fill="x")
        hint.bind("<Configure>", lambda e: hint.configure(wraplength=max(e.width - 8, 200)))
        for name, handler in (("button_press_event", self._on_press), ("motion_notify_event", self._on_motion),
                              ("button_release_event", self._on_release), ("key_press_event", self._on_key),
                              ("draw_event", self._on_draw)):
            self.canvas.mpl_connect(name, handler)
        self.canvas.get_tk_widget().bind("<Configure>", self._on_resize, add=True)

    # --------------------------------------------------------------- dessin
    def sources(self):
        """Fichiers présents dans l'onglet (courbes, nuage X/Y, conditions)."""
        return [s for s in (self.controller.workspace.find(fid) for fid in self.state.file_ids()) if s]

    def redraw(self) -> None:
        """Reconstruction complète (contenu, disposition ou axe des temps changé)."""
        allowed, _reason = monitor.can_hide(self.sources())
        if not self.state.tbm_visible and not allowed:
            self.state.tbm_visible = True       # REQ 4103 : une alerte réaffiche le TBM
            self.controller.notify(f"Onglet « {self.state.title} » : Time Base Monitor réaffiché "
                                   "(alerte de base de temps).", "AVERTISSEMENT")
        self.renderer = TabRenderer(self.figure, self.state, self.controller.workspace,
                                    self.controller.workspace.timeline(),
                                    self.controller.settings.max_points_per_curve,
                                    active_axle=self.active_axle)
        self.renderer.draw()
        master = self.renderer.axes_time_master()
        if master is not None:
            master.callbacks.connect("xlim_changed", self._on_xlim_changed)
        self.toolbar.update()               # repère « origine » de la barre = vue actuelle
        self._full_draw()
        self.tbm_button.configure(text="Masquer le TBM" if self.state.tbm_visible else "Afficher le TBM")
        self._sync_toolbar()
        self.refresh_readings()

    def update_cursors(self) -> None:
        """Mise à jour légère : curseurs et lectures seulement.

        Les curseurs sont redessinés seuls sur le rendu figé du reste de la figure
        (« blitting ») : un mouvement de souris ne redessine ni les courbes, ni
        les axes, ni le TBM (fluidité avec de gros fichiers, REQ 4105)."""
        if self.renderer is None:
            return
        self.renderer.draw_cursors()
        if self._background is not None:
            self.canvas.restore_region(self._background)
            self.renderer.draw_cursor_artists()
            self.canvas.blit(self.figure.bbox)
        else:
            self.canvas.draw_idle()
        self.refresh_readings()

    def _full_draw(self) -> None:
        """Redessin complet différé ; le rendu figé des curseurs devient périmé."""
        self._background = None
        self.canvas.draw_idle()

    def _on_draw(self, event) -> None:
        """Après chaque dessin complet à l'écran : mémorise le rendu sans curseurs,
        puis y pose les curseurs (affichés avec le reste de la figure)."""
        if self.renderer is None or event.canvas is not self.canvas or self.canvas.is_saving():
            return
        self._background = self.canvas.copy_from_bbox(self.figure.bbox)
        self.renderer.draw_cursor_artists()

    def refresh_readings(self) -> None:
        """Recalcule le panneau de lecture à droite (REQ 5402)."""
        rows = compute_readings(self.state, self.controller.workspace, self.controller.workspace.timeline())
        self.panel.show(rows)

    def _on_xlim_changed(self, ax) -> None:
        """Zoom / déplacement : mémorise la fenêtre et planifie la réduction des points."""
        self.state.xlim = list(ax.get_xlim())
        if self._refresh_job is None:
            self._refresh_job = self.after(40, self._refresh_zoom)

    def _refresh_zoom(self) -> None:
        """Recalcule les points affichés pour la nouvelle fenêtre de temps."""
        self._refresh_job = None
        if self.renderer is not None:
            self.renderer.refresh_decimation()
            self._full_draw()

    def _on_resize(self, _event) -> None:
        """Redimensionnement : redessin complet différé (évite les redessins en rafale)."""
        self._background = None                 # rendu figé d'une autre taille
        if self.renderer is None:               # pas encore dessiné, ou onglet en cours de fermeture
            return
        if self._resize_job is not None:
            self.after_cancel(self._resize_job)
        self._resize_job = self.after(400, self._after_resize)

    def _after_resize(self) -> None:
        """Redessin complet après redimensionnement."""
        self._resize_job = None
        if self.renderer is not None:
            self.redraw()                      # recalcule la hauteur du bandeau du TBM

    # -------------------------------------------------------- axes, courbes
    def axle(self):
        """État de l'axe actif."""
        return self.state.axles[min(self.active_axle, len(self.state.axles) - 1)]

    def set_active_axle(self, index: int) -> None:
        """Désigne l'axe actif (cadre bleu) qui reçoit courbes et curseurs (REQ 5400)."""
        if index is None or index < 0 or index >= len(self.state.axles):
            return
        self.active_axle = index
        if self.renderer is not None:
            self.renderer.active_axle = index
            for position, ax in enumerate(self.renderer.axes):
                for spine in ax.spines.values():
                    spine.set_edgecolor(ACTIVE_AXLE_COLOR if position == index else "black")
                    spine.set_linewidth(2.0 if position == index else 0.8)
            self._full_draw()
        self._sync_toolbar()
        self.controller.on_tab_changed()

    def _sync_toolbar(self) -> None:
        """Aligne listes et cases de la barre d'outils sur l'état de l'onglet."""
        self.axle_box["values"] = [f"Axe {i + 1}" + (" (X/Y)" if a.kind == "xy" else "")
                                   for i, a in enumerate(self.state.axles)]
        self.axle_box.current(self.active_axle)
        axle = self.axle()
        labels = []
        for ref in axle.curves:
            curve = resolve(ref, self.controller.workspace)
            labels.append(curve.label if curve else f"{ref.name} (indisponible)")
        self.curve_box["values"] = labels
        if labels:
            self.curve_box.current(min(axle.selected, len(labels) - 1))
        else:
            self.curve_choice.set("")
        self.cursor_mode.set(axle.cursor_mode)
        self.global_cursor.set(self.state.global_cursor)
        self.tracking.set(self.state.tracking)

    def _select_curve(self, index: int) -> None:
        """Change la courbe sélectionnée de l'axe actif (valeur portée par le curseur)."""
        self.axle().selected = max(index, 0)
        self.redraw()

    def add_curves(self, refs: list[tuple[str, str, bool]], axle_index: int | None = None) -> None:
        """Ajoute des variables/groupes (file_id, nom, groupe ?) à un axe.

        Un axe porte soit des courbes analogiques, soit des pistes logiques :
        une courbe de l'autre famille est placée sur le premier axe
        compatible, ou refusée avec une explication.
        """
        if axle_index is not None:
            self.set_active_axle(axle_index)
        axle = self.axle()
        if axle.kind == "xy":
            self._assign_xy(refs)
            return
        workspace = self.controller.workspace
        used = sum(len(a.curves) for a in self.state.axles)
        for file_id, name, is_group in refs:
            ref = CurveRef(file_id, name, is_group, curve_color(used))
            curve = resolve(ref, workspace)
            if curve is None:
                continue
            target = self._compatible_axle(curve.signal_type.is_digital)
            if target is None:
                messagebox.showwarning(
                    "Axe incompatible",
                    f"« {name} » ({curve.signal_type.value}) ne peut pas rejoindre des courbes "
                    f"{'analogiques' if curve.signal_type.is_digital else 'logiques'}. Videz un axe ou "
                    "ouvrez un onglet avec un autre modèle.", parent=self)
                continue
            if any(c.file_id == file_id and c.name == name for c in target.curves):
                continue
            target.curves.append(ref)
            used += 1
            self.controller.notify(f"{name} ajouté à l'axe {self.state.axles.index(target) + 1} "
                                   f"de « {self.state.title} ».")
        self.redraw()

    def _compatible_axle(self, digital: bool):
        """Axe actif s'il convient, sinon premier axe temporel vide ou de même famille."""
        def family(axle):
            """None si l'axe est vide, sinon vrai pour un axe logique (Bool / Texte)."""
            curves = [resolve(r, self.controller.workspace) for r in axle.curves]
            curves = [c for c in curves if c is not None]
            return None if not curves else all(c.signal_type.is_digital for c in curves)

        candidates = [self.axle()] + [a for a in self.state.axles if a is not self.axle()]
        for axle in candidates:
            if axle.kind == "time" and family(axle) in (None, digital):
                return axle
        return None

    def _assign_xy(self, refs) -> None:
        """Glisser sur un axe X/Y : 1re variable en X puis en Y."""
        axle = self.axle()
        for file_id, name, is_group in refs:
            if is_group:
                continue
            ref = CurveRef(file_id, name)
            if axle.xy_x is None or axle.xy_y is not None:
                axle.xy_x, axle.xy_y = ref, None       # nouveau couple : X d'abord
            else:
                axle.xy_y = ref
        self.redraw()

    def remove_selected_curve(self) -> None:
        """Retire la courbe sélectionnée de l'axe actif."""
        axle = self.axle()
        if axle.curves:
            removed = axle.curves.pop(min(axle.selected, len(axle.curves) - 1))
            axle.selected = 0
            self.controller.notify(f"{removed.name} retiré de l'axe {self.active_axle + 1}.")
            self.redraw()

    def clear_axle(self) -> None:
        """Vide l'axe actif : courbes, nuage X/Y, curseurs et condition."""
        axle = self.axle()
        axle.curves.clear()
        axle.xy_x = axle.xy_y = None
        axle.h_enabled, axle.h_condition, axle.cursor_mode = False, None, "none"
        self.redraw()

    # ------------------------------------------------------------- curseurs
    def _view_fraction(self, fraction: float) -> float:
        """Instant situé à une fraction de la fenêtre visible (position initiale d'un curseur)."""
        master = self.renderer.axes_time_master() if self.renderer else None
        if master is None:
            return 0.0
        lo, hi = master.get_xlim()
        return lo + fraction * (hi - lo)

    def set_cursor_mode(self, mode: str) -> None:
        """REQ 5400 / 5403 : curseurs de l'axe actif ; instants posés automatiquement."""
        axle = self.axle()
        if axle.kind == "xy":
            messagebox.showinfo("Curseur", "Sur un nuage X/Y, cliquer sur un point pour le désigner.",
                                parent=self)
            self.cursor_mode.set("none")
            return
        axle.cursor_mode = mode
        if mode in ("single", "double") and axle.t1 is None:
            axle.t1 = self._view_fraction(0.35)
        if mode == "double" and axle.t2 is None:
            axle.t2 = self._view_fraction(0.65)
        self.update_cursors()

    def _toggle_global(self) -> None:
        """Case « Curseur global » : ligne commune à tous les axes (REQ 5405)."""
        self.state.global_cursor = self.global_cursor.get()
        if self.state.global_cursor and self.state.t_global is None:
            self.state.t_global = self._view_fraction(0.5)
        self.update_cursors()

    def _toggle_tracking(self) -> None:
        """Case « Suivi souris » : le curseur suit la souris (REQ 5402)."""
        self.state.tracking = self.tracking.get()
        if self.state.tracking and not self.state.global_cursor and self.axle().cursor_mode == "none":
            self.set_cursor_mode("single")
            self.cursor_mode.set("single")

    def _toggle_panel(self) -> None:
        """Affiche ou masque le panneau de lecture."""
        if self.show_panel.get():
            self.paned.add(self.panel, width=PANEL_WIDTH, minsize=150, stretch="never")
        else:
            self.paned.forget(self.panel)

    def reset_view(self) -> None:
        """Revient à la vue d'origine : toute la durée des fichiers, échelles verticales
        automatiques, légendes déplacées remises à leur place automatique. Les
        courbes, curseurs et réglages de l'onglet sont conservés (une légende
        masquée le reste)."""
        self.state.xlim = None
        for axle in self.state.axles:
            axle.ylim = None
            if axle.legend == "free":
                axle.legend, axle.legend_xy = "auto", None
        self.redraw()

    def set_legend(self, index: int, mode: str) -> None:
        """Légende de l'axe ``index`` : « auto » (place automatique) ou « hidden »."""
        axle = self.state.axles[index]
        axle.legend, axle.legend_xy = mode, None
        self.redraw()

    def _legend_under(self, event) -> int | None:
        """Indice de l'axe dont la légende est sous la souris."""
        for index, ax in enumerate(self.renderer.axes):
            legend = ax.get_legend()
            if legend is not None and legend.contains(event)[0]:
                return index
        return None

    def _legend_released(self, event) -> None:
        """Fin d'un clic sur une légende : elle a été déplacée (sa place est
        mémorisée) ou simplement cliquée (le nom visé devient la courbe sélectionnée)."""
        index, x0, y0 = self._legend_press
        self._legend_press = None
        ax = self.renderer.axes[index]
        legend = ax.get_legend()
        if legend is None:
            return
        axle = self.state.axles[index]
        if abs(event.x - x0) + abs(event.y - y0) > 3:
            # Glissée par Matplotlib : on retient son coin bas-gauche en fraction de l'axe,
            # ramené dans la figure pour qu'une légende lâchée au bord ne soit jamais perdue.
            box, figure = legend.get_window_extent(), self.figure.bbox
            left = min(max(box.x0, figure.x0), max(figure.x1 - box.width, figure.x0))
            bottom = min(max(box.y0, figure.y0), max(figure.y1 - box.height, figure.y0))
            x, y = ax.transAxes.inverted().transform((left, bottom))
            axle.legend, axle.legend_xy = "free", [float(x), float(y)]
            return
        if axle.kind != "time":
            return
        for position, text in enumerate(legend.get_texts()):
            if text.contains(event)[0]:
                self.set_active_axle(index)
                self._select_curve(position)
                return

    def toggle_monitor(self) -> None:
        """REQ 4103 : masquage possible seulement sans avertissement ni erreur."""
        if self.state.tbm_visible:
            allowed, reason = monitor.can_hide(self.sources())
            if not allowed:
                messagebox.showwarning("Time Base Monitor", reason, parent=self)
                return
            self.state.tbm_visible = False
            self.controller.notify(f"Time Base Monitor masqué dans « {self.state.title} » (base de temps conforme).")
        else:
            self.state.tbm_visible = True
        self.redraw()

    def _target_for(self, index, event) -> str | None:
        """Curseur à déplacer pour un clic sur l'axe ``index``."""
        axle = self.state.axles[index]
        if axle.h_enabled and event.ydata is not None:
            near_h = axle.h_level is not None and abs(
                event.inaxes.transData.transform((0, axle.h_level))[1] - event.y) <= PICK_TOLERANCE_PX
            if near_h or event.key == "shift" or (axle.cursor_mode == "none" and not self.state.global_cursor):
                return "H"
        if self.state.global_cursor:
            return "G"
        if axle.cursor_mode == "single":
            return "C1"
        if axle.cursor_mode == "double":
            to_px = event.inaxes.transData.transform
            d1 = abs(to_px((axle.t1, 0))[0] - event.x) if axle.t1 is not None else np.inf
            d2 = abs(to_px((axle.t2, 0))[0] - event.x) if axle.t2 is not None else np.inf
            return "C1" if d1 <= d2 else "C2"
        return None

    def _move(self, target: str, event) -> None:
        """Place le curseur visé à la position de la souris."""
        axle = self.axle()
        if target == "H" and event.ydata is not None:
            axle.h_level = float(event.ydata)
        elif target == "G" and event.xdata is not None:
            self.state.t_global = float(event.xdata)
        elif target in ("C1", "C2") and event.xdata is not None:
            setattr(axle, "t1" if target == "C1" else "t2", float(event.xdata))
        self.update_cursors()

    def _on_press(self, event) -> None:
        """Clic : légende, axe actif, menu contextuel, ou prise d'un curseur / d'un point X/Y."""
        if self.renderer is None or self.toolbar.mode:
            return
        if event.button == 1:
            index = self._legend_under(event)
            if index is not None:              # Matplotlib la déplace ; rien d'autre ne bouge
                self._legend_press = (index, event.x, event.y)
                return
        if event.inaxes is None:
            return
        index = self.renderer.axle_index_of(event.inaxes)
        if event.inaxes is self.renderer.tbm_plot:
            if event.button == 1 and self.state.global_cursor and event.xdata is not None:
                self._drag = "G"
                self._move("G", event)
            return
        if index is None:
            return
        if index != self.active_axle:
            self.set_active_axle(index)
        if event.button == 3:
            self.controller.axle_context_menu(self, index).tk_popup(int(event.guiEvent.x_root),
                                                                    int(event.guiEvent.y_root))
            return
        if event.button != 1:
            return
        axle = self.state.axles[index]
        if axle.kind == "xy":
            self._pick_xy(axle, event)
            return
        self._drag = self._target_for(index, event)
        if self._drag:
            self._move(self._drag, event)

    def _pick_xy(self, axle, event) -> None:
        """REQ 5408 : désigne le point du nuage le plus proche du clic."""
        data = xy_data(axle, self.controller.workspace, self.controller.workspace.timeline())
        if data is None or event.xdata is None:
            return
        x0, x1 = event.inaxes.get_xlim()
        y0, y1 = event.inaxes.get_ylim()
        point = nearest_point(data, event.xdata, event.ydata, x1 - x0, y1 - y0)
        if point is not None:
            axle.xy_t = float(data.t[point])
            if self.state.global_cursor:
                self.state.t_global = axle.xy_t
            self.update_cursors()

    def _on_motion(self, event) -> None:
        """Mouvement : glisser un curseur ou suivi souris, regroupés par ``after_idle``."""
        if self.renderer is None or event.inaxes is None or self.toolbar.mode or self._legend_press:
            return
        if self._drag:
            self._pending_motion = (self._drag, event)
        elif self.state.tracking and event.inaxes is not self.renderer.tbm_plot:
            index = self.renderer.axle_index_of(event.inaxes)
            if index is None or self.state.axles[index].kind == "xy":
                return
            if self.state.global_cursor:
                self._pending_motion = ("G", event)
            elif index == self.active_axle and self.state.axles[index].cursor_mode != "none":
                self._pending_motion = ("C1", event)
        else:
            return
        self.after_idle(self._apply_motion)        # regroupe les mouvements rapides

    def _apply_motion(self) -> None:
        """Applique le dernier mouvement en attente (un seul redessin par cycle)."""
        if self._pending_motion is not None:
            target, event = self._pending_motion
            self._pending_motion = None
            self._move(target, event)

    def _on_release(self, event) -> None:
        """Fin du glisser (curseur ou légende)."""
        self._drag = None
        if self._legend_press is not None and self.renderer is not None:
            self._legend_released(event)

    def _on_key(self, event) -> None:
        """Flèches : déplace le curseur actif à l'échantillon voisin de la courbe sélectionnée."""
        if event.key not in ("left", "right"):
            return
        axle = self.axle()
        curve = resolve(axle.selected_curve(), self.controller.workspace) if axle.selected_curve() else None
        if curve is None:
            return
        grid = self.controller.workspace.timeline().grid(curve.source)
        direction = 1 if event.key == "right" else -1
        if self.state.global_cursor and self.state.t_global is not None:
            self.state.t_global = step_index(grid, self.state.t_global, direction)
        elif axle.cursor_mode in ("single", "double") and axle.t1 is not None:
            axle.t1 = step_index(grid, axle.t1, direction)
        self.update_cursors()

    def dispose(self) -> None:
        """Annule les rafraîchissements différés avant destruction de l'onglet
        (évite les « invalid command name … » de Tk et du dessin Matplotlib)."""
        self.renderer = None                # plus aucun redessin planifié à partir d'ici
        for job in (self._resize_job, self._refresh_job):
            if job is not None:
                self.after_cancel(job)
        self._resize_job = self._refresh_job = None
        self.update_idletasks()             # exécute le dessin différé en attente
        self.figure.clear()

    def capture(self) -> TabState:
        """Copie figée de l'état avec le zoom courant (rapport pas à pas, REQ 6004)."""
        if self.renderer is not None:
            self.renderer.capture_view()
        return self.state.copy()

    def float_curve_selected(self) -> bool:
        """Le curseur horizontal exige une courbe Float sélectionnée (REQ 5406)."""
        axle = self.axle()
        curve = resolve(axle.selected_curve(), self.controller.workspace) if axle.selected_curve() else None
        return curve is not None and curve.signal_type is SignalType.FLOAT and axle.kind == "time"
