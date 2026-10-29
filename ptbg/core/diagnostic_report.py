"""Diagnostic complet d'un fichier, en texte Markdown (fenêtre « Diagnostic »).

Rassemble : contrôles de lecture (REQ 2300-2310), conversion et contrôles de
la base de temps (REQ 4100-4107), liste des événements avec la ligne
physique du CSV, et constats sur les valeurs (cellules vides).

Présentation pensée pour être lue d'un coup d'œil : un bilan en clair en tête,
la liste des points à vérifier, puis le détail par section (tableaux pour
l'identité du fichier, les réglages, les segments et les événements). Chaque
constat commence par sa gravité entre crochets ([ERREUR], [AVERTISSEMENT],
[INFO], [OK]), colorée par la fenêtre d'affichage.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from ptbg.core.data_package import SourceFile, Timeline
from ptbg.core.diagnostics import Issue, Severity
from ptbg.core.time_base import ms
from ptbg.core.time_parser import format_absolute

MAX_LISTED_EVENTS = 300
MAX_HEADLINES = 12        # points à vérifier listés en tête (le détail suit)

VERDICTS = {
    Severity.OK: "fichier conforme, aucune anomalie détectée.",
    Severity.INFO: "fichier conforme ; quelques informations à connaître ci-dessous.",
    Severity.WARNING: "fichier exploitable, avec des points à vérifier avant de conclure.",
    Severity.ERROR: "certaines données ne sont pas fiables : lire les constats [ERREUR] avant toute analyse.",
}


def tag(severity: Severity) -> str:
    """Gravité entre crochets, en tête de ligne (colorée à l'écran)."""
    return f"[{severity.label}]"


def issue_line(issue: Issue) -> str:
    """Constat sur une ligne : gravité, message, ligne du CSV, requis."""
    where = f" — ligne {issue.line} du CSV" if issue.line is not None else ""
    req = f" ({issue.requirement.replace('REQ_COMMON_KH_', 'REQ ')})" if issue.requirement else ""
    return f"{tag(issue.severity)} {issue.message}{where}{req}"


def _size(n_bytes: int) -> str:
    """Taille lisible, avec le nombre exact d'octets."""
    for unit, scale in (("Mo", 1048576), ("ko", 1024)):
        if n_bytes >= scale:
            return f"{n_bytes / scale:.1f} {unit} ({n_bytes} octets)"
    return f"{n_bytes} octets"


def _cell(text) -> str:
    """Texte placé dans une cellule de tableau Markdown (barres verticales protégées)."""
    return str(text).replace("|", "\\|")


def _table(header: tuple, rows: list) -> list[str]:
    """Tableau Markdown."""
    lines = ["| " + " | ".join(header) + " |", "|" + "---|" * len(header)]
    return lines + ["| " + " | ".join(_cell(value) for value in row) + " |" for row in rows]


def _headlines(source: SourceFile) -> list[tuple[Severity, str]]:
    """Points à vérifier (avertissements et erreurs), les plus graves d'abord."""
    found = [(i.severity, issue_line(i)) for i in source.read_issues + source.data_issues()]
    if source.is_loaded:
        found += [(i.severity, issue_line(i)) for i in source.conversion.issues]
        found += [(c.severity, f"{tag(c.severity)} {c.name} : {c.text.split(' ; ')[0]}")
                  for c in source.analysis.checks]
    found = [item for item in found if item[0] >= Severity.WARNING]
    return sorted(found, key=lambda item: -item[0])


def file_report(source: SourceFile, timeline: Timeline) -> str:
    """Texte Markdown du diagnostic complet d'un fichier (lecture, base de temps, valeurs)."""
    status = source.status()
    path = Path(source.path)
    lines = [f"# Diagnostic — {source.name}", "",
             f"**Bilan : {tag(status)} {VERDICTS[status]}**", ""]
    headlines = _headlines(source)
    if headlines:
        lines += [f"## Points à vérifier ({len(headlines)})", ""]
        lines += [f"- {text}" for _sev, text in headlines[:MAX_HEADLINES]]
        if len(headlines) > MAX_HEADLINES:
            lines.append(f"- … {len(headlines) - MAX_HEADLINES} autre(s) : voir le détail ci-dessous.")
        lines.append("")
    identity = [("Fichier", path.name), ("Dossier", str(path.parent))]
    if source.table:
        identity += [("Taille", _size(source.table.size_bytes)),
                     ("Échantillons (lignes de données)", source.table.n_samples),
                     ("Variables", len(source.table.columns))]
    if source.is_loaded:
        x = timeline.x(source)
        finite = x[np.isfinite(x)]
        if finite.size > 1:
            identity.append(("Durée couverte", f"{float(finite.max() - finite.min()):.6g} s"))
    if source.table:
        identity.append(("Empreinte SHA-256", source.table.sha256))
    lines += ["## 1. Identité du fichier", ""] + _table(("Élément", "Valeur"), identity)
    lines += ["", "## 2. Lecture du fichier", "",
              "Séparateur, encodage, en-tête et nombre de colonnes de chaque ligne (REQ 2300 à 2310).", ""]
    lines += [f"- {issue_line(issue)}" for issue in source.read_issues] or \
        [f"- {tag(Severity.OK)} Aucun constat : le fichier a été lu sans écart."]
    if not source.is_loaded:
        return "\n".join(lines)
    conversion, analysis, settings = source.conversion, source.analysis, source.time_settings
    nominal = analysis.period_nominal_s
    setup = [("Colonne de temps", conversion.description)]
    if conversion.origin_ns is not None:
        setup.append(("Origine absolue", format_absolute(conversion.origin_ns, 9, conversion.date_known)))
    setup += [("Raster de référence", f"{ms(analysis.period_used_s)} ms "
               + (f"(nominal saisi : {ms(nominal)} ms)" if nominal else "(estimé sur le fichier)")),
              ("Tolérance", f"± {analysis.tolerance_pct:g} %"),
              ("Temps affiché", "régularisé (jitter ignoré)" if settings.ignore_jitter else "brut, tel que dans le fichier"),
              ("Horodatages aberrants", "masqués sur les courbes" if settings.hide_aberrant else "affichés"),
              ("Décalage manuel", f"{settings.offset_s:g} s")]
    if settings.operator_note:
        setup.append(("Diagnostic opérateur", settings.operator_note))
    lines += ["", "## 3. Base de temps", "", "### Réglages", ""] + _table(("Réglage", "Valeur"), setup)
    lines += ["", "### Contrôles", ""]
    lines += [f"- {issue_line(issue)}" for issue in conversion.issues]
    for check in analysis.checks:
        parts = [part.strip().rstrip(".") for part in check.text.split(" ; ") if part.strip()]
        if len(parts) == 1:
            lines.append(f"- {tag(check.severity)} {check.name} : {parts[0]}")
        else:
            lines.append(f"- {tag(check.severity)} {check.name}")
            lines += [f"  - {part}" for part in parts]
    if analysis.segments:
        lines += ["", "### Portions à période constante", ""]
        lines += _table(("Portion", "Lignes du CSV", "Échantillons", "Période"),
                        [(n, f"{source.line_of(seg.start)} à {source.line_of(seg.end)}",
                          seg.end - seg.start + 1, f"{ms(seg.period_s)} ms")
                         for n, seg in enumerate(analysis.segments, start=1)])
    total = sum(analysis.event_counts.values())
    lines += ["", f"## 4. Événements temporels ({total})", ""]
    if total:
        lines.append("Répartition : " + ", ".join(f"{count} {kind.short}"
                                                 for kind, count in analysis.event_counts.items()) + ".")
        lines += ["", "Chaque événement est repéré par sa ligne dans le CSV (à ouvrir dans un éditeur de texte).", ""]
        x = timeline.x(source)
        rows = [(source.line_of(event.index), timeline.format(x[event.index]) if event.index < x.size else "—",
                 event.kind.severity.label, event.kind.label, event.detail or "")
                for event in analysis.events[:MAX_LISTED_EVENTS]]
        lines += _table(("Ligne CSV", "Instant", "Gravité", "Événement", "Détail"), rows)
        if len(analysis.events) > MAX_LISTED_EVENTS:
            lines += ["", f"… {len(analysis.events) - MAX_LISTED_EVENTS} autre(s) événement(s) mémorisé(s) "
                          "(voir le Time Base Monitor)."]
    else:
        lines.append(f"- {tag(Severity.OK)} Aucun trou, déphasage, doublon ni retour arrière du temps.")
    lines += ["", "## 5. Valeurs des variables", ""]
    lines += [f"- {issue_line(issue)}" for issue in source.data_issues()] or \
        [f"- {tag(Severity.OK)} Aucune cellule vide ni valeur illisible."]
    lines += ["", "---", "Gravités : [ERREUR] donnée non fiable · [AVERTISSEMENT] à vérifier · "
                         "[INFO] information · [OK] conforme."]
    return "\n".join(lines)
