"""Time Base Monitor : axe dédié à la base de temps (REQ 4102, 4103, 4104).

- REQ_COMMON_KH_4102 : axe nommé « Time Base Monitor », présent
  automatiquement sous chaque modèle de disposition ; il détaille la
  CONVERSION (format brut -> secondes, unité, origine, régularisation) et le
  STATUT de chaque fichier affiché dans l'onglet, ainsi que les Δt mesurés,
  la période de référence, la tolérance et les anomalies ;
- REQ_COMMON_KH_4103 : masquage autorisé seulement sans avertissement ni
  erreur de base de temps (``can_hide``) ;
- REQ_COMMON_KH_4104 : présent dans tous les rapports ; s'il a été retiré de
  la mise en page, le rapport porte une indication confirmant la bonne
  construction de la base de temps (``confirmation_text``).
"""
from __future__ import annotations

import numpy as np

from ptbg.core.data_package import SourceFile, Timeline
from ptbg.core.diagnostics import Severity, worst
from ptbg.core.time_base import EventKind, ms
from ptbg.core.time_parser import format_absolute
from ptbg.plotting.styles import CURVE_COLORS, EVENT_STYLE, FONT_SMALL, SEVERITY_COLORS

TITLE = "Time Base Monitor"


def monitor_status(sources: list[SourceFile]) -> Severity:
    return worst(source.time_status() for source in sources)


def can_hide(sources: list[SourceFile]) -> tuple[bool, str]:
    """REQ 4103 : masquage possible seulement si aucune alerte de base de temps."""
    blocking = [s for s in sources if s.time_status() > Severity.INFO]
    if not blocking:
        return True, ""
    names = ", ".join(f"{s.name} ({s.time_status().label})" for s in blocking)
    return False, ("Le Time Base Monitor ne peut être masqué qu'en l'absence d'avertissement "
                   f"ou d'erreur de base de temps. Fichier(s) concerné(s) : {names}.")


def describe_source(source: SourceFile) -> str:
    """Texte de conversion et de statut d'un fichier (une ou deux lignes)."""
    if not source.is_loaded:
        return f"{source.name} : non chargé — {source.read_issues[0].message if source.read_issues else ''}"
    conversion, analysis = source.conversion, source.analysis
    if conversion.origin_ns is not None:
        origin = "origine " + format_absolute(conversion.origin_ns, 6, conversion.date_known)
    else:
        origin = "origine relative (non définie)"
    mode = "régularisé, jitter ignoré" if source.time_settings.ignore_jitter else "brut"
    assumed = " (unité supposée)" if conversion.unit_assumed else ""
    text = (f"{source.name} [{source.time_status().label}] : {conversion.description}{assumed} ; {origin} ; "
            f"affichage {mode}\n    {analysis.summary()}")
    if source.time_settings.operator_note:
        text += f"\n    Diagnostic opérateur : {source.time_settings.operator_note}"
    return text


def text_height_in(sources: list[SourceFile]) -> float:
    """Hauteur (pouces) du bandeau texte : titre + lignes de description."""
    lines = sum(describe_source(source).count("\n") + 1 for source in sources) or 1
    return 0.22 + 0.118 * lines


def confirmation_text(sources: list[SourceFile]) -> str:
    """Indication imprimée quand le TBM a été retiré de la mise en page (REQ 4104)."""
    status = monitor_status(sources)
    verdict = "CONFORME" if status <= Severity.INFO else f"NON CONFORME ({status.label})"
    lines = [f"{TITLE} retiré de la mise en page par l'émetteur — construction de la base de "
             f"temps vérifiée : {verdict}."]
    lines += [describe_source(source) for source in sources]
    return "\n".join(lines)


def draw_monitor(text_ax, plot_ax, sources: list[SourceFile], timeline: Timeline) -> list:
    """Dessine le TBM : bandeau de texte (conversion/statut) + courbe des Δt.

    Renvoie les (ligne, x, y) des courbes de Δt pour que le rendu les réduise
    au zoom comme les autres courbes."""
    status = monitor_status(sources) if sources else Severity.OK
    color = SEVERITY_COLORS[status]
    text_ax.set_axis_off()
    title = f"{TITLE} — statut : {status.label if sources else 'aucun fichier affiché'}"
    text_ax.text(0.0, 1.0, title, transform=text_ax.transAxes, va="top", ha="left",
                 fontsize=FONT_SMALL + 1, fontweight="bold", color=color)
    body = "\n".join(describe_source(source) for source in sources)
    # Corps placé juste sous le titre (décalage en points, indépendant de la hauteur).
    text_ax.annotate(body, xy=(0.0, 1.0), xycoords="axes fraction", xytext=(0, -13),
                     textcoords="offset points", va="top", ha="left",
                     fontsize=FONT_SMALL - 0.5, family="DejaVu Sans Mono")
    plot_ax.tick_params(labelsize=FONT_SMALL)
    plot_ax.grid(True, alpha=0.3)
    for spine in plot_ax.spines.values():
        spine.set_edgecolor(color)
    loaded = [s for s in sources if s.is_loaded and s.analysis.dt_values.size]
    if not loaded:
        plot_ax.set_ylabel("Δt (ms)", fontsize=FONT_SMALL)
        return []
    periods = [seg.period_s for s in loaded for seg in s.analysis.segments]
    # Périodes très différentes (ex. 1 ms et 20 ms) : Δt rapporté à la période
    # de chaque fichier, sinon le petit raster serait écrasé en bas de l'axe.
    relative = max(periods) > 1.5 * min(periods)
    plot_ax.set_ylabel("Δt / période" if relative else "Δt (ms)", fontsize=FONT_SMALL)
    top = 2.6 if relative else 2.6 * max(periods) * 1e3
    lines = []
    for position, source in enumerate(loaded):
        lines.append(_draw_source(plot_ax, source, timeline, CURVE_COLORS[position % len(CURVE_COLORS)],
                                  top, position, relative))
    if any(e.kind is not EventKind.FREQUENCY for s in loaded for e in s.analysis.events):
        plot_ax.legend(loc="upper left", fontsize=FONT_SMALL - 1, framealpha=0.8, ncol=3)
    plot_ax.set_ylim(0, top * 1.08)
    return lines


def _draw_source(ax, source, timeline, color, top, position, relative):
    """Δt d'un fichier, période de référence par segment, bande de tolérance,
    anomalies ; les Δt hors échelle sont posés sur le bord supérieur (▲).
    ``relative`` : ordonnée = Δt / période du segment (sans unité)."""
    analysis = source.analysis
    x_all = timeline.x(source)
    x = x_all[analysis.dt_index]
    scale = np.full(analysis.dt_values.size, 1e3)       # ms
    if relative:
        for segment in analysis.segments:
            inside = (analysis.dt_index > segment.start) & (analysis.dt_index <= segment.end)
            scale[inside] = 1.0 / segment.period_s
    y = analysis.dt_values * scale
    shown = np.clip(y, 0, top)
    line, = ax.plot(x[:2], shown[:2], drawstyle="steps-pre", lw=0.9, color=color)
    over = y > top
    if over.any():
        ax.plot(x[over][:2000], np.full(min(int(over.sum()), 2000), top), "^", ms=4, color=color)
    for segment in analysis.segments:
        start, end = x_all[segment.start], x_all[min(segment.end, x_all.size - 1)]
        reference = 1.0 if relative else segment.period_s * 1e3
        tolerance = analysis.tolerance_pct / 100 * reference
        ax.hlines(reference, start, end, colors=color, linestyles="--", lw=0.8)
        ax.fill_between([start, end], reference - tolerance, reference + tolerance, color=color, alpha=0.08, lw=0)
    for kind, (marker, event_color) in EVENT_STYLE.items():
        events = [e for e in analysis.events if e.kind is kind]
        if not events:
            continue
        ex = x_all[[e.index for e in events]]
        ey = np.clip([0.0 if not np.isfinite(e.dt_s) else e.dt_s * scale[min(np.searchsorted(analysis.dt_index, e.index), scale.size - 1)]
                      for e in events], 0, top)
        if kind is EventKind.FREQUENCY:
            for value in ex:
                ax.axvline(value, color=event_color, lw=1.2, ls="-.")
        else:
            ax.plot(ex, ey, marker, ls="none", ms=6, color=event_color, mec="white", mew=0.5,
                    label=f"{kind.label} ({analysis.event_counts[kind]})")
    ax.text(0.995, 0.97 - 0.12 * position, f"{source.name} : T = {ms(analysis.period_used_s)} ms",
            transform=ax.transAxes, ha="right", va="top", fontsize=FONT_SMALL - 1, color=color)
    return line, x, shown
