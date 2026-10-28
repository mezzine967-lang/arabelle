"""Diagnostic complet d'un fichier, en texte Markdown (fenêtre « Diagnostic »).

Rassemble : contrôles de lecture (REQ 2300-2310), conversion et contrôles de
la base de temps (REQ 4100-4107), liste des événements avec la ligne
physique du CSV, et constats sur les valeurs (cellules vides).
"""
from __future__ import annotations

from ptbg.core.data_package import SourceFile, Timeline
from ptbg.core.time_base import ms
from ptbg.core.time_parser import format_absolute

MAX_LISTED_EVENTS = 300


def file_report(source: SourceFile, timeline: Timeline) -> str:
    """Texte Markdown du diagnostic complet d'un fichier (lecture, base de temps, valeurs)."""
    lines = [f"# Diagnostic — {source.name}", "", f"Chemin : {source.path}",
             f"Statut global : {source.status().label}", ""]
    if source.table:
        lines.append(f"Taille : {source.table.size_bytes} octets ; SHA-256 : {source.table.sha256}")
        lines.append(f"Échantillons : {source.table.n_samples} ; variables : {len(source.table.columns)}")
    lines += ["", "## Lecture du fichier", ""]
    lines += [f"- {issue.as_text()}" for issue in source.read_issues] or ["- Aucun constat de lecture."]
    if not source.is_loaded:
        return "\n".join(lines)
    conversion, analysis = source.conversion, source.analysis
    lines += ["", "## Base de temps", "", f"- Conversion : {conversion.description}"]
    if conversion.origin_ns is not None:
        lines.append(f"- Origine absolue : {format_absolute(conversion.origin_ns, 9, conversion.date_known)}")
    settings = source.time_settings
    lines.append(f"- Affichage : {'régularisé (jitter ignoré)' if settings.ignore_jitter else 'brut'} ; "
                 f"horodatages aberrants {'masqués' if settings.hide_aberrant else 'affichés'} ; "
                 f"décalage manuel {settings.offset_s:g} s")
    if settings.operator_note:
        lines.append(f"- Diagnostic opérateur : {settings.operator_note}")
    nominal = analysis.period_nominal_s
    lines.append(f"- Raster de référence : {ms(analysis.period_used_s)} ms "
                 + (f"(nominal saisi {ms(nominal)} ms)" if nominal else "(estimé sur le fichier)"))
    lines += [f"- {issue.as_text()}" for issue in conversion.issues]
    lines += [f"- {check.name} [{check.severity.label}] : {check.text}" for check in analysis.checks]
    lines += [f"- Segment {n} : échantillons {seg.start} à {seg.end}, période {ms(seg.period_s)} ms"
              for n, seg in enumerate(analysis.segments, start=1)]
    lines += ["", f"## Événements ({sum(analysis.event_counts.values())} au total)", ""]
    x = timeline.x(source)
    for event in analysis.events[:MAX_LISTED_EVENTS]:
        when = timeline.format(x[event.index]) if event.index < x.size else "—"
        lines.append(f"- ligne {source.line_of(event.index)} — {when} — {event.kind.label}"
                     + (f" — {event.detail}" if event.detail else ""))
    if len(analysis.events) > MAX_LISTED_EVENTS:
        lines.append(f"- … {len(analysis.events) - MAX_LISTED_EVENTS} autre(s) événement(s) mémorisé(s)")
    lines += ["", "## Valeurs", ""]
    lines += [f"- {issue.as_text()}" for issue in source.data_issues()] or ["- Aucune cellule vide."]
    return "\n".join(lines)
