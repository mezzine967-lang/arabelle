"""Couleurs et tailles partagées par l'écran et le PDF.

Palette « Okabe-Ito » étendue : distinguable par les daltoniens, contrastée
sur fond blanc à l'écran comme à l'impression.
"""
from __future__ import annotations

from ptbg.core.diagnostics import Severity
from ptbg.core.time_base import EventKind

CURVE_COLORS = ("#0072B2", "#D55E00", "#009E73", "#CC79A7", "#E69F00",
                "#56B4E9", "#000000", "#8C564B", "#7F7F7F", "#B22222")

SEVERITY_COLORS = {
    Severity.OK: "#1a7f37",
    Severity.INFO: "#1a7f37",       # une information n'empêche pas la conformité
    Severity.WARNING: "#b35900",
    Severity.ERROR: "#c62828",
}

# Marqueurs des événements de base de temps dans le Time Base Monitor.
EVENT_STYLE = {
    EventKind.MISSING: ("v", "#c62828"),
    EventKind.PHASE: ("D", "#E69F00"),
    EventKind.DUPLICATE: ("X", "#000000"),
    EventKind.BACKWARD: ("X", "#7B1FA2"),
    EventKind.FREQUENCY: ("|", "#7B1FA2"),
}

CURSOR_COLORS = {"C1": "#c62828", "C2": "#6a1b9a", "Global": "#2e7d32", "H": "#ef6c00", "X/Y": "#c62828"}

ACTIVE_AXLE_COLOR = "#1565c0"
FONT_SMALL = 7
FONT_NORMAL = 8


def curve_color(position: int) -> str:
    """Couleur attribuée à la n-ième courbe ajoutée."""
    return CURVE_COLORS[position % len(CURVE_COLORS)]
