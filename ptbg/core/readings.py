"""Lectures des curseurs, communes au panneau droit et au rapport PDF.

- REQ_COMMON_KH_5401 : curseur simple -> instant + valeur de la courbe sélectionnée ;
- REQ_COMMON_KH_5402 : mode suivi -> liste des valeurs de TOUTES les courbes
  de l'axe (panneau de lecture à droite) ;
- REQ_COMMON_KH_5403 / 5404 : double curseur -> instants C1, C2 automatiques,
  Δt, 1/Δt et écart de valeur par courbe ;
- REQ_COMMON_KH_5405 : curseur global -> lecture sur tous les axes ;
- REQ_COMMON_KH_5406 / 5407 : curseur horizontal -> niveau, franchissements,
  éventuellement sous condition Bool ;
- REQ_COMMON_KH_5408 : point du nuage X/Y désigné.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ptbg.core.arrangement import AxleState, TabState
from ptbg.core.conditional import evaluate
from ptbg.core.curves import resolve
from ptbg.core.data_package import Timeline, Workspace
from ptbg.core.sampling import crossings, sample_at
from ptbg.core.signals import SignalType
from ptbg.core.xy import build_xy, point_at_time

HEADER = ("Axe", "Curseur", "Courbe", "Instant lu", "Valeur", "Ligne CSV")
MAX_LISTED_CROSSINGS = 5


@dataclass(frozen=True)
class ReadingRow:
    """Une ligne du panneau de lecture / du tableau du rapport."""

    axle: str
    cursor: str
    curve: str
    time: str
    value: str
    line: str

    def as_tuple(self) -> tuple:
        """Valeurs dans l'ordre des colonnes ``HEADER``."""
        return (self.axle, self.cursor, self.curve, self.time, self.value, self.line)


def cursor_positions(tab: TabState, axle: AxleState) -> list[tuple[str, float]]:
    """Curseurs verticaux actifs sur un axe : global, C1, C2."""
    positions = []
    if tab.global_cursor and tab.t_global is not None:
        positions.append(("Global", tab.t_global))
    if axle.cursor_mode in ("single", "double") and axle.t1 is not None:
        positions.append(("C1", axle.t1))
    if axle.cursor_mode == "double" and axle.t2 is not None:
        positions.append(("C2", axle.t2))
    return positions


def xy_data(axle: AxleState, workspace: Workspace, timeline: Timeline):
    """Nuage X/Y d'un axe, ou None s'il n'est pas configuré."""
    if axle.xy_x is None or axle.xy_y is None:
        return None
    cx, cy = resolve(axle.xy_x, workspace), resolve(axle.xy_y, workspace)
    if cx is None or cy is None:
        return None
    same = cx.source is cy.source
    max_gap = 0.5 * max(cx.source.analysis.period_used_s, cy.source.analysis.period_used_s)
    return build_xy(timeline.x(cx.source), cx.values, timeline.x(cy.source), cy.values, same, max_gap)


def horizontal_crossings(axle: AxleState, workspace: Workspace, timeline: Timeline):
    """(courbe, franchissements) du curseur horizontal, ou None."""
    curve = resolve(axle.selected_curve(), workspace) if axle.selected_curve() else None
    if not axle.h_enabled or axle.h_level is None or curve is None or curve.signal_type is not SignalType.FLOAT:
        return None
    x = timeline.x(curve.source)
    allowed = None
    if axle.h_condition and axle.h_condition.terms:
        allowed = evaluate(axle.h_condition, curve.source, workspace.find, timeline)
    return curve, crossings(x, curve.values, axle.h_level, allowed)


def compute_readings(tab: TabState, workspace: Workspace, timeline: Timeline,
                     only_axle: int | None = None) -> list[ReadingRow]:
    """Toutes les lectures d'un onglet (ou d'un seul axe)."""
    rows: list[ReadingRow] = []
    for number, axle in enumerate(tab.axles, start=1):
        if only_axle is not None and number - 1 != only_axle:
            continue
        name = f"Axe {number}"
        if axle.kind == "xy":
            rows.extend(_xy_rows(name, axle, workspace, timeline, tab))
            continue
        positions = cursor_positions(tab, axle)
        for label, position in positions:
            for ref in axle.curves:
                curve = resolve(ref, workspace)
                if curve is None:
                    continue
                x = timeline.x(curve.source)
                sample = sample_at(x, curve.values, position, curve.hold, timeline.x_sorted(curve.source))
                if sample is None:
                    rows.append(ReadingRow(name, label, curve.label, timeline.format(position),
                                           "hors plage", "—"))
                    continue
                rows.append(ReadingRow(name, label, curve.label, timeline.format(sample.x),
                                       curve.format_at(sample.index),
                                       str(curve.source.line_of(sample.index))))
        rows.extend(_delta_rows(name, axle, workspace, timeline))
        rows.extend(_horizontal_rows(name, axle, workspace, timeline))
    return rows


def _delta_rows(name, axle, workspace, timeline) -> list[ReadingRow]:
    """Δt et Δvaleur du double curseur (REQ 5403 / 5404)."""
    if axle.cursor_mode != "double" or axle.t1 is None or axle.t2 is None:
        return []
    delta = axle.t2 - axle.t1
    frequency = f" ; 1/Δt = {1 / abs(delta):.6g} Hz" if delta else ""
    rows = [ReadingRow(name, "Δ", "C2 − C1", f"Δt = {delta:.9g} s{frequency}", "", "")]
    for ref in axle.curves:
        curve = resolve(ref, workspace)
        if curve is None or curve.signal_type is not SignalType.FLOAT:
            continue
        x = timeline.x(curve.source)
        ordered = timeline.x_sorted(curve.source)
        s1 = sample_at(x, curve.values, axle.t1, False, ordered)
        s2 = sample_at(x, curve.values, axle.t2, False, ordered)
        if s1 and s2 and np.isfinite(s1.value) and np.isfinite(s2.value):
            rows.append(ReadingRow(name, "Δ", curve.label, f"{s2.x - s1.x:.9g} s",
                                   f"ΔV = {s2.value - s1.value:.6g}", ""))
    return rows


def _horizontal_rows(name, axle, workspace, timeline) -> list[ReadingRow]:
    """Niveau et franchissements du curseur horizontal (REQ 5406 / 5407)."""
    result = horizontal_crossings(axle, workspace, timeline)
    if result is None:
        return []
    curve, found = result
    condition = f" sous condition {axle.h_condition.describe()}" if axle.h_condition and axle.h_condition.terms else ""
    rows = [ReadingRow(name, "H", curve.label, f"niveau {axle.h_level:.6g}",
                       f"{len(found)} franchissement(s){condition}", "")]
    for crossing in found[:MAX_LISTED_CROSSINGS]:
        rows.append(ReadingRow(name, "H", curve.label, timeline.format(crossing.x),
                               "montant" if crossing.rising else "descendant",
                               str(curve.source.line_of(crossing.index))))
    return rows


def _xy_rows(name, axle, workspace, timeline, tab) -> list[ReadingRow]:
    """Point désigné et corrélation du nuage X/Y (REQ 5408)."""
    data = xy_data(axle, workspace, timeline)
    if data is None:
        return []
    rows = [ReadingRow(name, "X/Y", f"{axle.xy_y.name} = f({axle.xy_x.name})", "", data.describe(), "")]
    instant = axle.xy_t if axle.xy_t is not None else (tab.t_global if tab.global_cursor else None)
    point = point_at_time(data, instant) if instant is not None else None
    if point is not None:
        source = workspace.find(axle.xy_x.file_id)
        rows.append(ReadingRow(name, "Point", f"X = {data.x[point]:.6g} ; Y = {data.y[point]:.6g}",
                               timeline.format(data.t[point]), "", str(source.line_of(int(data.index[point])))))
    return rows
