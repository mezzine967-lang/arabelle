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

Présentation (remarques du relecteur) : sous le titre, rien que la courbe des
Δt. Une seule légende, HORS de la courbe pour ne jamais la masquer, donne la
couleur, la période et le statut de chaque fichier puis le compte de chaque
sorte d'anomalie, au-dessus de la courbe (écran et rapport). À l'écran, le détail d'une anomalie (fichier, instant, ligne CSV,
Δt) s'affiche au survol de son marqueur et le diagnostic complet s'ouvre par
un clic droit ; dans le rapport, le détail de la conversion et des contrôles
de chaque fichier est sur la page de traçabilité.
"""
from __future__ import annotations

import textwrap

import numpy as np
from matplotlib.lines import Line2D

from ptbg.core.data_package import SourceFile, Timeline
from ptbg.core.diagnostics import Severity, worst
from ptbg.core.time_base import EventKind, ms
from ptbg.core.time_parser import format_absolute
from ptbg.plotting.styles import CURVE_COLORS, EVENT_STYLE, FONT_SMALL, SEVERITY_COLORS, apply_grid

TITLE = "Time Base Monitor"
LEGEND_COLUMNS = 4        # colonnes au plus de la légende placée au-dessus de la courbe
LEGEND_COLUMN_IN = 2.7    # largeur d'une colonne de cette légende (pouces)
LEGEND_ROW_IN = 0.17      # hauteur d'une rangée de cette légende (pouces)


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
    if source.analysis.excluded.size and source.time_settings.hide_aberrant:
        mode += f", {source.analysis.excluded.size} horodatage(s) aberrant(s) masqué(s)"
    assumed = " (unité SUPPOSÉE, à confirmer)" if conversion.unit_assumed else ""
    text = (f"{source.name} [{source.time_status().label}] : {conversion.description}{assumed} ; {origin} ; "
            f"affichage {mode}\n    {analysis.summary()}")
    if source.time_settings.operator_note:
        text += f"\n    Diagnostic opérateur : {source.time_settings.operator_note}"
    return text


def wrap_text(text: str, chars: int) -> str:
    """Texte coupé à ``chars`` caractères par ligne ; les suites gardent le retrait
    de leur ligne (rien n'est rogné au bord de la figure)."""
    out = []
    for line in text.split("\n"):
        indent = " " * (len(line) - len(line.lstrip()) + 4)
        out += textwrap.wrap(line, max(chars, 20), subsequent_indent=indent) or [""]
    return "\n".join(out)


def legend_columns(width_in: float) -> int:
    """Colonnes de la légende pour une courbe large de ``width_in`` pouces."""
    return max(1, min(LEGEND_COLUMNS, int(width_in / LEGEND_COLUMN_IN)))


def text_height_in(sources: list[SourceFile], width_in: float) -> float:
    """Hauteur (pouces) du bandeau au-dessus de la courbe : titre et rangées de la légende."""
    entries = len(_legend_handles(_loaded(sources)))
    return 0.24 + LEGEND_ROW_IN * -(-entries // legend_columns(width_in))


def _loaded(sources: list[SourceFile]) -> list[SourceFile]:
    """Fichiers dont la courbe des Δt peut être tracée."""
    return [s for s in sources if s.is_loaded and s.analysis.dt_values.size]


def _legend_handles(loaded: list[SourceFile]) -> list:
    """Entrées de la légende : chaque fichier (couleur, période, statut), puis chaque
    sorte d'anomalie avec son total."""
    handles = [Line2D([], [], color=CURVE_COLORS[position % len(CURVE_COLORS)], lw=1.5,
                      label=f"{source.name} : T = {ms(source.analysis.period_used_s)} ms — "
                            f"{source.time_status().label}")
               for position, source in enumerate(loaded)]
    totals = {kind: sum(s.analysis.event_counts[kind] for s in loaded) for kind in EVENT_STYLE
              if kind is not EventKind.FREQUENCY}
    handles += [Line2D([], [], marker=EVENT_STYLE[kind][0], ls="none", ms=6, color=EVENT_STYLE[kind][1],
                       mec="white", mew=0.5, label=f"{kind.label} ({count})")
                for kind, count in totals.items() if count]
    changes = sum(s.analysis.event_counts[EventKind.FREQUENCY] for s in loaded)
    if changes:
        handles.append(Line2D([], [], color=EVENT_STYLE[EventKind.FREQUENCY][1], ls="-.", lw=1.2,
                              label=f"{EventKind.FREQUENCY.label} ({changes})"))
    return handles


def confirmation_text(sources: list[SourceFile], chars: int) -> str:
    """Indication imprimée quand le TBM a été retiré de la mise en page (REQ 4104)."""
    status = monitor_status(sources)
    verdict = "CONFORME" if status <= Severity.INFO else f"NON CONFORME ({status.label})"
    lines = [f"{TITLE} retiré de la mise en page par l'émetteur — construction de la base de "
             f"temps vérifiée : {verdict}."]
    lines += [describe_source(source) for source in sources]
    return wrap_text("\n".join(lines), chars)


def draw_monitor(text_ax, plot_ax, sources: list[SourceFile], timeline: Timeline,
                 legend_xy=None) -> tuple[list, list]:
    """Dessine le TBM : titre + courbe des Δt, avec une légende hors de la courbe.

    Légende (voir l'en-tête) : au-dessus de la courbe ; ``legend_xy`` : place
    choisie à la souris (coin bas-gauche, fraction de la courbe).
    Renvoie les (ligne, x, y) des courbes de Δt, que le rendu réduit au zoom comme
    les autres courbes, et les marqueurs d'anomalie (x, y, texte du détail)."""
    status = monitor_status(sources) if sources else Severity.OK
    color = SEVERITY_COLORS[status]
    text_ax.set_axis_off()
    title = f"{TITLE} — statut : {status.label if sources else 'aucun fichier affiché'}"
    text_ax.text(0.0, 1.0, title, transform=text_ax.transAxes, va="top", ha="left",
                 fontsize=FONT_SMALL + 1, fontweight="bold", color=color)
    plot_ax.tick_params(labelsize=FONT_SMALL)
    apply_grid(plot_ax)
    for spine in plot_ax.spines.values():
        spine.set_edgecolor(color)
    loaded = _loaded(sources)
    if not loaded:
        plot_ax.set_ylabel("Δt (ms)", fontsize=FONT_SMALL)
        return [], []
    periods = [seg.period_s for s in loaded for seg in s.analysis.segments]
    # Périodes très différentes (ex. 1 ms et 20 ms) : Δt rapporté à la période
    # de chaque fichier, sinon le petit raster serait écrasé en bas de l'axe.
    relative = max(periods) > 1.5 * min(periods)
    plot_ax.set_ylabel("Δt / période" if relative else "Δt (ms)", fontsize=FONT_SMALL)
    top = 2.6 if relative else 2.6 * max(periods) * 1e3
    lines, markers = [], []
    for position, source in enumerate(loaded):
        lines.append(_draw_source(plot_ax, source, timeline, CURVE_COLORS[position % len(CURVE_COLORS)],
                                  top, relative, markers))
    handles = _legend_handles(loaded)
    columns = legend_columns(plot_ax.bbox.width / plot_ax.figure.dpi)
    if legend_xy:
        plot_ax.legend(handles=handles, loc=tuple(legend_xy), fontsize=FONT_SMALL - 1, framealpha=0.85,
                       ncol=columns)
    else:
        # Au-dessus de la courbe, sous le titre : aucune partie de la courbe n'est masquée.
        plot_ax.legend(handles=handles, loc="lower left", bbox_to_anchor=(0.0, 1.01), borderaxespad=0.0,
                       fontsize=FONT_SMALL - 1, frameon=False, ncol=columns, columnspacing=1.6)
    plot_ax.set_ylim(0, top * 1.08)
    return lines, markers


def _readable_neighbour_x(x_all: np.ndarray, indices: list[int]) -> np.ndarray:
    """Abscisse où montrer un horodatage illisible (REQ 4101) : celle de la
    mesure lisible qui le précède (ou qui le suit, en début de fichier)."""
    valid = np.flatnonzero(np.isfinite(x_all))
    if valid.size == 0:
        return np.full(len(indices), np.nan)
    rank = np.clip(np.searchsorted(valid, indices) - 1, 0, valid.size - 1)
    return x_all[valid[rank]]


def _event_detail(source, timeline, event, x: float) -> str:
    """Texte de la bulle d'une anomalie : fichier, sorte, instant, ligne CSV, détail."""
    line = source.line_of(event.index) if 0 <= event.index < source.analysis.n_samples else None
    where = f" — ligne CSV {line}" if line is not None else ""
    return "\n".join(part for part in (f"{source.name} : {event.kind.label}", f"{timeline.format(x)}{where}",
                                        event.detail) if part)


def _draw_source(ax, source, timeline, color, top, relative, markers: list):
    """Δt d'un fichier, période de référence par segment, bande de tolérance,
    anomalies ; les Δt hors échelle sont posés sur le bord supérieur (▲).
    ``relative`` : ordonnée = Δt / période du segment (sans unité). Chaque anomalie
    est ajoutée à ``markers`` (x, y, détail) pour la bulle de survol."""
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
        if kind in (EventKind.INVALID, EventKind.OUTLIER):        # instant inconnu ou faux
            ex = _readable_neighbour_x(x_all, [e.index for e in events])
        ey = np.clip([0.0 if not np.isfinite(e.dt_s) else e.dt_s * scale[min(np.searchsorted(analysis.dt_index, e.index), scale.size - 1)]
                      for e in events], 0, top)
        if kind is EventKind.FREQUENCY:
            for value in ex:
                ax.axvline(value, color=event_color, lw=1.2, ls="-.")
            ey = np.full(len(events), top / 2)
        else:
            ax.plot(ex, ey, marker, ls="none", ms=6, color=event_color, mec="white", mew=0.5)
        markers += [(float(x), float(y), _event_detail(source, timeline, event, x))
                    for x, y, event in zip(ex, ey, events)]
    return line, x, shown
