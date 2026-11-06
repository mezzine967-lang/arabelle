"""Graduation de l'axe des temps (relatif en secondes ou horodatage absolu).

La précision affichée s'adapte à la fenêtre de zoom : on garde assez de
décimales pour distinguer les graduations, jusqu'à la nanoseconde.
"""
from __future__ import annotations

import math

from matplotlib.ticker import FuncFormatter, MaxNLocator

from ptbg.core.data_package import Timeline
from ptbg.core.time_parser import NS_PER_S, format_absolute


def _digits_for(span: float) -> int:
    """Décimales utiles pour une fenêtre de largeur ``span`` secondes."""
    if not math.isfinite(span) or span <= 0:
        return 3
    return max(0, min(9, int(math.ceil(-math.log10(span / 10.0))) + 1))


def apply_time_axis(ax, timeline: Timeline, show_labels: bool) -> None:
    """Installe la graduation temporelle sur un axe Matplotlib."""

    def tick(value, _position):
        span = abs(ax.get_xlim()[1] - ax.get_xlim()[0])
        digits = _digits_for(span)
        if timeline.is_absolute:
            return format_absolute(timeline.ref_ns + int(round(value * NS_PER_S)), digits, False)
        return f"{value:.{digits}f}"

    ax.xaxis.set_major_locator(MaxNLocator(nbins=8))
    ax.xaxis.set_major_formatter(FuncFormatter(tick))
    ax.tick_params(axis="x", labelbottom=show_labels)


def axis_title(timeline: Timeline) -> str:
    """Libellé de l'axe ; la date de référence figure dans le libellé absolu."""
    if timeline.is_absolute:
        reference = format_absolute(timeline.ref_ns, 0, timeline.with_date)
        return f"Horodatage absolu (référence {reference})"
    return "Temps relatif (s)"
