"""Rendu d'un onglet (``TabState``) dans une figure Matplotlib.

Utilisé à l'identique pour l'écran et pour le PDF (``for_print=True``).

Requis servis :
- REQ_COMMON_KH_5300 : grille d'axes issue du modèle ;
- REQ_COMMON_KH_4102 : Time Base Monitor ajouté automatiquement en bas de
  chaque disposition, sur le même axe des temps que les courbes ;
- REQ_COMMON_KH_4104 : à l'impression, TBM toujours présent, ou indication de
  conformité s'il a été retiré de la mise en page ;
- REQ_COMMON_KH_2200 / 2201 : Float en trait continu, Bool et Texte en
  escalier sur des pistes logiques, groupe binaire = pistes regroupées ;
- REQ_COMMON_KH_5400 à 5408 : dessin des curseurs et du nuage X/Y ;
- REQ_COMMON_KH_4101 : courbe interrompue sur un trou de la base de temps,
  croix sur les échantillons qui encadrent une cellule vide.

Les axes temporels d'un onglet partagent leur abscisse (``sharex``) : zoom et
déplacement sont synchronisés, ce qui réalise la synchronisation des axes
demandée par REQ_COMMON_KH_5405.
"""
from __future__ import annotations

import numpy as np
from matplotlib import style
from matplotlib.transforms import blended_transform_factory

from ptbg.core.arrangement import AxleState, TabState
from ptbg.core.curves import CurveData, resolve
from ptbg.core.data_package import Timeline, Workspace
from ptbg.core.readings import cursor_positions, horizontal_crossings, xy_data
from ptbg.core.conditional import evaluate, true_intervals
from ptbg.core.sampling import DisplayCurve, break_at, missing_markers, sample_at
from ptbg.core.signals import SignalType, short_label
from ptbg.core.xy import point_at_time
from ptbg.plotting import monitor
from ptbg.plotting.styles import (ACTIVE_AXLE_COLOR, CURSOR_COLORS, FONT_NORMAL, FONT_SMALL,
                                  SEVERITY_COLORS, curve_color)
from ptbg.plotting.time_axis import apply_time_axis, axis_title

LANE_STEP = 1.25        # espacement vertical des pistes logiques
LANE_HEIGHT = 0.8       # amplitude 0 -> 1 d'une piste
MAX_MARKERS = 3000      # croix / marqueurs dessinés au plus par courbe
MAX_SHADED = 400        # périodes de condition ombrées au plus
MAX_XY_POINTS = 20000
HSPACE = 0.45           # espace vertical entre axes (fraction de hauteur moyenne)


def _representable_limits(arrays) -> tuple[float, float] | None:
    """Limites à imposer si l'étendue des valeurs dépasse le flottant 64 bits.

    Des valeurs proches de ±1,8e308 (dépassement PLC) donnent une étendue
    infinie : Matplotlib ne peut plus construire sa transformation (« Singular
    matrix »). La vue est alors bornée à ±1e307 ; les valeurs ne sont pas
    modifiées et restent lisibles aux curseurs. None dans tous les autres cas."""
    finite = [values[np.isfinite(values)] for values in arrays]
    finite = [values for values in finite if values.size]
    if not finite:
        return None
    lo = min(float(values.min()) for values in finite)
    hi = max(float(values.max()) for values in finite)
    with np.errstate(over="ignore"):
        span = hi - lo
    return None if np.isfinite(span) else (max(lo, -1e307), min(hi, 1e307))


def _bound_axes(ax, xlim, ylim) -> None:
    """Applique ces limites, l'échelle automatique coupée AVANT (elle déborderait)."""
    if xlim:
        ax.set_autoscalex_on(False)
    if ylim:
        ax.set_autoscaley_on(False)
    if xlim:
        ax.set_xlim(*xlim)
    if ylim:
        ax.set_ylim(*ylim)


class TabRenderer:
    """Construit et met à jour le dessin d'un onglet."""

    def __init__(self, container, tab: TabState, workspace: Workspace, timeline: Timeline,
                 max_points: int, for_print: bool = False, active_axle: int | None = None,
                 height_in: float | None = None) -> None:
        """Mémorise l'état à dessiner ; ``draw`` construit la figure."""
        self.container = container          # Figure ou SubFigure
        # Hauteur réelle de la zone (pouces) : dimensionne le bandeau texte du TBM.
        self.height_in = height_in or container.figure.get_figheight()
        self.tab = tab
        self.workspace = workspace
        self.timeline = timeline
        self.max_points = max_points
        self.for_print = for_print
        self.active_axle = active_axle
        self.axes: list = []                # un axe Matplotlib par axe du modèle
        self.tbm_plot = None
        self._lines: list = []              # (axe, ligne, DisplayCurve : courbe complète)
        self._lanes: dict = {}              # (axe, courbe) -> (base, échelle) des pistes
        self._digital_axles: set = set()    # axes dessinés en pistes logiques
        self._cursor_artists: list = []
        self._h_cache: dict = {}

    # ------------------------------------------------------------------ build
    def sources_in_tab(self):
        """Fichiers référencés par l'onglet (pour le Time Base Monitor)."""
        return [s for s in (self.workspace.find(fid) for fid in self.tab.file_ids()) if s is not None]

    def draw(self) -> None:
        """(Re)construit tout le dessin, avec le style Matplotlib par défaut.

        Le contexte de style protège le rendu d'un style global modifié dans la
        console (Spyder, ``plt.style.use``…) sans toucher aux réglages de l'utilisateur.
        """
        with style.context("default"):
            self._draw_all()

    def _draw_all(self) -> None:
        self.container.clear()
        self.axes, self._lines, self._lanes, self._h_cache = [], [], {}, {}
        self._digital_axles, self._cursor_artists, self.tbm_plot = set(), [], None
        tpl = self.tab.template
        sources = self.sources_in_tab()
        with_tbm = self.tab.tbm_visible
        with_note = self.for_print and not with_tbm      # REQ 4104
        ratios = list(tpl.row_ratios)
        total = float(sum(ratios))
        if with_tbm:
            ratios.append(min(0.8 * total, 0.38 * total * (1 + 0.3 * max(len(sources) - 1, 0))))
        elif with_note:
            ratios.append(0.12 * total * (1 + 0.5 * len(sources)))
        grid = self.container.add_gridspec(
            len(ratios), tpl.ncols, height_ratios=ratios, width_ratios=list(tpl.col_ratios),
            left=0.075, right=0.985, top=0.965, bottom=0.075, hspace=HSPACE, wspace=0.22)
        master = None
        for index, (slot, axle) in enumerate(zip(tpl.slots, self.tab.axles)):
            spec = grid[slot.row:slot.row + slot.rowspan, slot.col:slot.col + slot.colspan]
            if slot.kind == "time":
                ax = self.container.add_subplot(spec, sharex=master)
                master = master or ax
            else:
                ax = self.container.add_subplot(spec)
            self.axes.append(ax)
            try:
                if axle.kind == "xy":
                    self._draw_xy_axle(index, ax, axle)
                else:
                    self._draw_time_axle(index, ax, axle)
            except Exception as exc:  # noqa: BLE001 - REQ 4105 : un axe en défaut n'empêche pas les autres
                self._axle_failed(ax, exc)
        if with_tbm:
            # Hauteur réelle de la bande TBM (formule de GridSpec avec hspace).
            rows = len(ratios)
            band_in = (self.height_in * 0.89 * rows * ratios[-1]
                       / (sum(ratios) * (rows + HSPACE * (rows - 1))))
            text_in = monitor.text_height_in(sources)
            text_share = text_in / max(band_in - text_in, 0.35)
            band = grid[tpl.nrows, :].subgridspec(2, 1, height_ratios=[text_share, 1], hspace=0.04)
            text_ax = self.container.add_subplot(band[0])
            self.tbm_plot = self.container.add_subplot(band[1], sharex=master)
            for line, x, y in monitor.draw_monitor(text_ax, self.tbm_plot, sources, self.timeline):
                self._lines.append((self.tbm_plot, line, DisplayCurve(x, y)))
            apply_time_axis(self.tbm_plot, self.timeline, True)
            self.tbm_plot.set_xlabel(axis_title(self.timeline), fontsize=FONT_SMALL)
        elif with_note:
            note_ax = self.container.add_subplot(grid[tpl.nrows, :])
            note_ax.set_axis_off()
            status = monitor.monitor_status(sources)
            note_ax.text(0.0, 1.0, monitor.confirmation_text(sources), transform=note_ax.transAxes,
                         va="top", ha="left", fontsize=FONT_SMALL - 0.5,
                         bbox=dict(boxstyle="round", fc="#f4f8f4", ec=SEVERITY_COLORS[status]))
        if master is not None:
            if self.tab.xlim:
                master.set_xlim(*self.tab.xlim)
            else:
                self._fit_time_range(master)
            if not with_tbm:
                master.set_xlabel(axis_title(self.timeline), fontsize=FONT_SMALL)
        self.refresh_decimation()
        self.draw_cursors()

    def _fit_time_range(self, master) -> None:
        """Vue initiale : toute la durée des fichiers affichés. Les horodatages
        aberrants isolés (signalés dans le TBM) ne servent pas au cadrage : ils
        restent dessinés, visibles en dézoomant, sans écraser toute la vue."""
        sources = [source for source in self.sources_in_tab() if source.is_loaded]
        abscissae = [self.timeline.x(source) if not source.analysis.excluded.size
                     else np.delete(self.timeline.x(source), source.analysis.excluded) for source in sources] \
            or [curve.x for _, _, curve in self._lines]
        bounds = []
        for x in abscissae:
            # Min / max sans copier les abscisses (NaN ignorés) ; ±inf : abscisses finies seules.
            lo, hi = (np.fmin.reduce(x), np.fmax.reduce(x)) if x.size else (np.nan, np.nan)
            if not (np.isfinite(lo) and np.isfinite(hi)):
                finite = x[np.isfinite(x)]
                lo, hi = (finite.min(), finite.max()) if finite.size else (np.nan, np.nan)
            if np.isfinite(lo):
                bounds.append((float(lo), float(hi)))
        if bounds:
            lo = min(low for low, _ in bounds)
            hi = max(high for _, high in bounds)
            pad = (hi - lo) * 0.01 or 1.0
            master.set_xlim(lo - pad, hi + pad)

    def _style_axle(self, index: int, ax) -> None:
        """Grille, titre « Axe n » et cadre bleu de l'axe actif."""
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=FONT_SMALL)
        ax.set_title(f"Axe {index + 1}", loc="left", fontsize=FONT_NORMAL, pad=3)
        if not self.for_print and index == self.active_axle:
            for spine in ax.spines.values():
                spine.set_edgecolor(ACTIVE_AXLE_COLOR)
                spine.set_linewidth(2.0)

    def _axle_failed(self, ax, exc: Exception) -> None:
        """Axe impossible à dessiner : il est vidé et l'erreur y est écrite (écran et PDF)."""
        self._lines = [entry for entry in self._lines if entry[0] is not ax]
        ax.clear()
        ax.text(0.5, 0.5, f"Affichage impossible : {type(exc).__name__} : {exc}", transform=ax.transAxes,
                ha="center", va="center", fontsize=FONT_NORMAL, color="#c62828", wrap=True)

    def _placeholder(self, ax, text: str) -> None:
        """Texte d'aide dans un axe vide (écran seulement, jamais dans le PDF)."""
        if not self.for_print:
            ax.text(0.5, 0.5, text, transform=ax.transAxes, ha="center", va="center",
                    fontsize=FONT_NORMAL, color="#777777")

    def _draw_time_axle(self, index: int, ax, axle: AxleState) -> None:
        """Axe temporel : analogique ou pistes logiques selon ses courbes."""
        self._style_axle(index, ax)
        apply_time_axis(ax, self.timeline, True)
        curves = [c for c in (resolve(ref, self.workspace) for ref in axle.curves) if c is not None]
        if not curves:
            self._placeholder(ax, "Double-cliquer ou glisser une variable de l'arbre ici")
            return
        if all(c.signal_type.is_digital for c in curves):
            self._digital_axles.add(index)
            self._draw_digital(index, ax, axle, curves)
        else:
            self._draw_analog(index, ax, axle, curves)
        if axle.ylim:
            ax.set_ylim(*axle.ylim)
        if not self.timeline.is_absolute and any(c.source.conversion.pretrig_samples for c in curves):
            ax.axvline(0.0, color="#555555", ls=":", lw=1.0)
            ax.text(0.0, 0.02, " déclenchement (t = 0)", transform=blended_transform_factory(ax.transData, ax.transAxes),
                    fontsize=FONT_SMALL - 1, color="#555555")

    def _register(self, ax, x, y, **style):
        """Trace une courbe (réduite pour l'affichage) et la mémorise pour le zoom."""
        line, = ax.plot(x[:2], y[:2], **style)
        self._lines.append((ax, line, DisplayCurve(x, y)))
        return line

    def _draw_analog(self, index, ax, axle, curves: list[CurveData]) -> None:
        """Courbes Float : trait continu, courbe sélectionnée épaissie, croix des cellules vides."""
        for position, curve in enumerate(curves):
            color = curve.ref.color or curve_color(position)
            selected = position == min(axle.selected, len(curves) - 1)
            x = self.timeline.x(curve.source)
            xb, yb = break_at(x, curve.values, curve.source.gap_starts())
            self._register(ax, xb, yb, color=color, lw=1.8 if selected else 1.0,
                           label=("► " if selected else "") + curve.label)
            if curve.signal is not None:
                marks = missing_markers(x, curve.values, curve.signal.missing)[:MAX_MARKERS]
                if marks.size:
                    ax.plot(x[marks], curve.values[marks], "x", color=color, ms=7, mew=1.6)
        _bound_axes(ax, None, _representable_limits([curve.values for curve in curves]))
        ax.legend(loc="best", fontsize=FONT_SMALL, framealpha=0.85)

    def _draw_digital(self, index, ax, axle, curves: list[CurveData]) -> None:
        """Pistes logiques empilées de haut en bas, étiquetées à gauche."""
        ticks, lane = [], 0
        for position, curve in enumerate(curves):
            color = curve.ref.color or curve_color(position)
            members = curve.members if curve.ref.is_group else [curve.signal]
            for member in members:
                base = -lane * LANE_STEP
                values = member.values
                scale = LANE_HEIGHT
                name = member.name
                if curve.ref.is_group and not member.name.startswith(curve.ref.name):
                    name = f"{curve.ref.name}.{member.name}"      # bit d'un groupe créé à la main
                if member.type is SignalType.TEXT:
                    scale = LANE_HEIGHT / max(len(member.categories) - 1, 1)
                    name += (" (" + "/".join(short_label(c, 20) for c in member.categories[:5])
                             + ("…" if len(member.categories) > 5 else "") + ")")
                x = self.timeline.x(curve.source)
                y = base + scale * values
                xb, yb = break_at(x, y, curve.source.gap_starts())
                selected = position == min(axle.selected, len(curves) - 1)
                self._register(ax, xb, yb, color=color, lw=1.6 if selected else 1.0, drawstyle="steps-post")
                marks = missing_markers(x, values, member.missing)[:MAX_MARKERS]
                if marks.size:
                    ax.plot(x[marks], y[marks], "x", color=color, ms=6, mew=1.4)
                self._lanes[(index, position)] = (base, scale)
                # Nom de la piste DANS l'axe : les noms longs ne sont pas tronqués.
                ax.text(0.003, base + LANE_HEIGHT + 0.05, ("► " if selected else "") + name,
                        transform=blended_transform_factory(ax.transAxes, ax.transData),
                        fontsize=FONT_SMALL, color=color, va="bottom", ha="left",
                        bbox=dict(fc="white", ec="none", alpha=0.75, pad=0.5))
                ticks += [base, base + LANE_HEIGHT]
                lane += 1
        ax.set_yticks(ticks)
        # Au-delà de 4 pistes, les étiquettes 0/1 se chevaucheraient : seuls les traits restent.
        ax.set_yticklabels(["0", "1"] * (len(ticks) // 2) if lane <= 4 else [], fontsize=FONT_SMALL - 1)
        ax.set_ylim(-(lane - 1) * LANE_STEP - 0.3, LANE_HEIGHT + 0.4)

    def _draw_xy_axle(self, index: int, ax, axle: AxleState) -> None:
        """Nuage X/Y, droite de régression et corrélation dans le titre (REQ 5408)."""
        self._style_axle(index, ax)
        data = xy_data(axle, self.workspace, self.timeline)
        if data is None:
            self._placeholder(ax, "Nuage X/Y : Outils > Nuage X/Y…")
            ax.set_title(f"Axe {index + 1} — nuage X/Y", loc="left", fontsize=FONT_NORMAL, pad=3)
            return
        step = max(1, data.n // MAX_XY_POINTS)
        ax.plot(data.x[::step], data.y[::step], ".", ms=2.5, color=curve_color(0), alpha=0.7)
        _bound_axes(ax, _representable_limits([data.x]), _representable_limits([data.y]))
        if np.isfinite(data.slope):
            span = np.array([data.x.min(), data.x.max()])
            ax.plot(span, data.slope * span + data.intercept, "--", color="#555555", lw=1.0,
                    label=f"régression (r = {data.r:.4f})")
            ax.legend(loc="best", fontsize=FONT_SMALL)
        ax.set_xlabel(f"X : {axle.xy_x.name}", fontsize=FONT_SMALL)
        ax.set_ylabel(f"Y : {axle.xy_y.name}", fontsize=FONT_SMALL)
        ax.set_title(f"Axe {index + 1} — X/Y : {data.describe()}", loc="left", fontsize=FONT_SMALL, pad=3)
        if axle.ylim:
            ax.set_ylim(*axle.ylim)

    # ------------------------------------------------------- mise à jour zoom
    def refresh_decimation(self) -> None:
        """Recalcule les points affichés pour le zoom courant (appelé après
        chaque zoom/déplacement) ; les petits nombres de points sont marqués."""
        for ax, line, curve in self._lines:
            lo, hi = ax.get_xlim()
            xd, yd = curve.window(lo, hi, self.max_points)
            line.set_data(xd, yd)
            visible = np.count_nonzero((xd >= lo) & (xd <= hi))
            line.set_marker("o" if visible < 120 else "")
            line.set_markersize(2.5)
        for ax in self.axes:
            if ax.lines and ax.get_autoscaley_on():
                ax.relim()
                ax.autoscale_view(scalex=False)

    def axes_time_master(self):
        """Premier axe temporel : les autres partagent son abscisse."""
        return next((ax for ax, axle in zip(self.axes, self.tab.axles) if axle.kind == "time"), None)

    # ---------------------------------------------------------------- curseurs
    def draw_cursors(self) -> None:
        """Redessine uniquement les curseurs (appelé à chaque mouvement)."""
        for artist in self._cursor_artists:
            artist.remove()
        self._cursor_artists = []
        for index, (ax, axle) in enumerate(zip(self.axes, self.tab.axles)):
            try:
                if axle.kind == "xy":
                    self._draw_xy_cursor(ax, axle)
                    continue
                self._draw_vertical_cursors(index, ax, axle)
                self._draw_horizontal_cursor(index, ax, axle)
            except Exception as exc:  # noqa: BLE001 - REQ 4105 : même règle que pour le tracé
                self._keep(ax.text(0.5, 0.02, f"Curseur non affichable : {exc}", transform=ax.transAxes,
                                   ha="center", va="bottom", fontsize=FONT_SMALL, color="#c62828"))
        if self.tbm_plot is not None and self.tab.global_cursor and self.tab.t_global is not None:
            self._keep(self.tbm_plot.axvline(self.tab.t_global, color=CURSOR_COLORS["Global"], ls="--", lw=1.1))

    def _keep(self, artist):
        """Mémorise un élément de curseur pour l'effacer au prochain redessin. À
        l'écran il est « animé » : redessiné seul, sans le reste de la figure
        (``draw_cursor_artists``) ; dans le PDF il est dessiné normalement."""
        if not self.for_print:
            artist.set_animated(True)
        self._cursor_artists.append(artist)
        return artist

    def draw_cursor_artists(self) -> None:
        """Dessine les seuls curseurs sur le rendu déjà présent (écran)."""
        for artist in self._cursor_artists:
            self.container.figure.draw_artist(artist)

    def _draw_vertical_cursors(self, index: int, ax, axle: AxleState) -> None:
        """Curseurs global, C1, C2 : ligne, instant, valeur de la courbe sélectionnée, Δt."""
        to_axes = blended_transform_factory(ax.transData, ax.transAxes)
        curve = resolve(axle.selected_curve(), self.workspace) if axle.selected_curve() else None
        for row, (label, position) in enumerate(cursor_positions(self.tab, axle)):
            color = CURSOR_COLORS[label]
            self._keep(ax.axvline(position, color=color, lw=1.2, ls="--" if label == "Global" else "-"))
            text = f"{label}  {self.timeline.format(position)}"
            if curve is not None:
                sample = sample_at(self.timeline.grid(curve.source), curve.values, position, curve.hold)
                if sample is not None:
                    text += f"\n{curve.ref.name} = {curve.format_at(sample.index)}"
                    y_mark = self._display_y(index, axle, curve, sample.value)
                    if y_mark is not None:
                        self._keep(ax.plot(sample.x, y_mark, "o", ms=6, mfc="none", mec=color, mew=1.5)[0])
            self._keep(ax.text(position, 0.98 - 0.2 * row, text, transform=to_axes, va="top", ha="left",
                               fontsize=FONT_SMALL, color=color, zorder=5,
                               bbox=dict(fc="white", ec=color, alpha=0.88, lw=0.6, pad=1.5)))
        if axle.cursor_mode == "double" and axle.t1 is not None and axle.t2 is not None:
            delta = axle.t2 - axle.t1
            self._keep(ax.annotate("", xy=(axle.t2, 0.06), xytext=(axle.t1, 0.06), xycoords=to_axes,
                                   arrowprops=dict(arrowstyle="<->", color="#333333", lw=1.0)))
            self._keep(ax.text((axle.t1 + axle.t2) / 2, 0.09, f"Δt = {delta:.9g} s", transform=to_axes,
                               ha="center", va="bottom", fontsize=FONT_SMALL,
                               bbox=dict(fc="#fffde7", ec="#999999", lw=0.5, pad=1.2)))

    def _display_y(self, index, axle, curve, value):
        """Ordonnée affichée d'une valeur (piste logique : base + échelle × valeur)."""
        if not np.isfinite(value) or curve.ref.is_group:
            return None
        if index in self._digital_axles:
            lane = self._lanes.get((index, min(axle.selected, len(axle.curves) - 1)))
            return None if lane is None else lane[0] + lane[1] * value
        return value

    def _draw_horizontal_cursor(self, index: int, ax, axle: AxleState) -> None:
        """Curseur horizontal (Float uniquement) et condition Bool (REQ 5406 / 5407)."""
        if not axle.h_enabled or axle.h_level is None:
            return
        key = (axle.h_level, axle.h_condition.describe() if axle.h_condition else "",
               tuple(s.revision for s in self.sources_in_tab()), axle.selected, len(axle.curves))
        cached = self._h_cache.get(index)
        if cached is None or cached[0] != key:
            result = horizontal_crossings(axle, self.workspace, self.timeline)
            intervals = []
            if result is not None and axle.h_condition and axle.h_condition.terms:
                curve = result[0]
                mask = evaluate(axle.h_condition, curve.source, self.workspace.find, self.timeline)
                intervals = true_intervals(self.timeline.x(curve.source), mask)
            cached = (key, result, intervals)
            self._h_cache[index] = cached
        _, result, intervals = cached
        if result is None:
            return
        curve, found = result
        color = CURSOR_COLORS["H"]
        self._keep(ax.axhline(axle.h_level, color=color, lw=1.2))
        for start, end in intervals[:MAX_SHADED]:
            self._keep(ax.axvspan(start, end, color="#ffb74d", alpha=0.18, lw=0))
        if found:
            fx = np.array([c.x for c in found[:MAX_MARKERS]])
            self._keep(ax.plot(fx, np.full(fx.size, axle.h_level), "|", ms=10, mew=1.5, color=color)[0])
        condition = f"\nsi {axle.h_condition.describe()}" if axle.h_condition and axle.h_condition.terms else ""
        self._keep(ax.text(0.995, axle.h_level, f"H = {axle.h_level:.6g} : {len(found)} franchissement(s){condition}",
                           transform=blended_transform_factory(ax.transAxes, ax.transData), ha="right",
                           va="top", fontsize=FONT_SMALL, color=color, zorder=6,
                           bbox=dict(fc="white", ec=color, alpha=0.85, lw=0.5, pad=1.2)))

    def _draw_xy_cursor(self, ax, axle: AxleState) -> None:
        """Point désigné du nuage : deux curseurs (X et Y) ou point de croisement seul."""
        data = xy_data(axle, self.workspace, self.timeline)
        if data is None:
            return
        marks = []
        instant = axle.xy_t if axle.xy_t is not None else (
            self.tab.t_global if self.tab.global_cursor else None)
        if instant is not None:
            marks.append(("X/Y", instant))
        time_axles = [a for a in self.tab.axles if a.kind == "time"]
        if time_axles:
            marks += [(label, x) for label, x in cursor_positions(self.tab, time_axles[0]) if label != "Global"]
        for label, instant in marks:
            point = point_at_time(data, instant)
            if point is None:
                continue
            px, py = data.x[point], data.y[point]
            color = CURSOR_COLORS[label]
            if label == "X/Y" and axle.xy_mode == "two_cursors":
                self._keep(ax.axvline(px, color=color, lw=1.0))
                self._keep(ax.axhline(py, color=color, lw=1.0))
            self._keep(ax.plot(px, py, "o", ms=9 if label == "X/Y" else 6, mfc="none", mec=color, mew=1.8)[0])
            self._keep(ax.annotate(f"{label} {self.timeline.format(data.t[point])}\nX = {px:.6g}\nY = {py:.6g}",
                                   (px, py), xytext=(8, 8), textcoords="offset points", fontsize=FONT_SMALL,
                                   color=color, bbox=dict(fc="white", ec=color, alpha=0.88, lw=0.5, pad=1.2)))

    # ------------------------------------------------------------- utilitaires
    def axle_index_of(self, mpl_axes) -> int | None:
        """Indice de l'axe du modèle correspondant à un axe Matplotlib cliqué."""
        for index, ax in enumerate(self.axes):
            if ax is mpl_axes:
                return index
        return None

    def capture_view(self) -> None:
        """Recopie le zoom courant dans l'état (avant une capture de rapport)."""
        time_axes = [ax for ax, axle in zip(self.axes, self.tab.axles) if axle.kind == "time"]
        if time_axes:
            self.tab.xlim = list(time_axes[0].get_xlim())
        for ax, axle in zip(self.axes, self.tab.axles):
            if not ax.get_autoscaley_on():
                axle.ylim = list(ax.get_ylim())
