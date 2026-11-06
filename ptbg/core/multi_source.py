"""Comparaison des sources d'un système multi-PLC (REQ 2100, 2101, 2102, 2104).

Pour chaque couple de fichiers affichés sur le même axe des temps :

- recouvrement temporel et fin de flux décalée (perte de flux possible) ;
- fréquences différentes (10 ms / 20 ms par exemple) ;
- déphasage entre les grilles d'échantillonnage lorsque les périodes sont
  égales (médiane de l'écart au plus proche échantillon de l'autre source).

Ces résultats n'ont de sens que si l'axe des temps est COMMUN : axe absolu,
ou compteurs partant d'une même référence (PLC synchronisés). Le texte le
rappelle systématiquement ; aucun recalage n'est appliqué automatiquement :
l'utilisateur peut saisir un décalage dans la configuration de la base de temps.
"""
from __future__ import annotations

from itertools import combinations

import numpy as np

from ptbg.core.data_package import SourceFile, Timeline
from ptbg.core.diagnostics import Issue, Severity
from ptbg.core.time_base import ms

PHASE_SAMPLE = 2000   # échantillons utilisés pour estimer un déphasage


def _phase_offset(x_a: np.ndarray, x_b: np.ndarray, period: float) -> float | None:
    """Écart médian (s) entre les échantillons de B et le plus proche de A."""
    x_a = np.sort(x_a[np.isfinite(x_a)])
    x_b = x_b[np.isfinite(x_b)]
    if x_a.size < 2:
        return None
    lo, hi = max(x_a.min(), x_b.min()), min(x_a.max(), x_b.max())
    x_b = x_b[(x_b >= lo) & (x_b <= hi)][:PHASE_SAMPLE]
    if x_b.size == 0:
        return None
    right = np.clip(np.searchsorted(x_a, x_b), 1, x_a.size - 1)
    left = right - 1
    nearest = np.where(np.abs(x_b - x_a[left]) <= np.abs(x_a[right] - x_b), x_a[left], x_a[right])
    delta = x_b - nearest
    # Ramené dans [-T/2, T/2] : un déphasage est défini à une période près.
    folded = (delta + period / 2) % period - period / 2
    return float(np.median(folded))


def compare_sources(sources: list[SourceFile], timeline: Timeline) -> list[Issue]:
    """Constats inter-sources pour les fichiers donnés (chargés)."""
    loaded = [s for s in sources if s.is_loaded and s.analysis.n_valid >= 2]
    if len(loaded) < 2:
        return []
    basis = ("axe absolu" if timeline.is_absolute else
             "axe relatif : valable si les compteurs ont une référence commune (PLC synchronisés)")
    issues = [Issue(Severity.INFO, f"Comparaison de {len(loaded)} sources sur l'{basis}.",
                    requirement="REQ_COMMON_KH_2102")]
    spans = {s.id: timeline.x(s) for s in loaded}
    for a, b in combinations(loaded, 2):
        xa, xb = spans[a.id], spans[b.id]
        ta, tb = a.analysis.period_used_s, b.analysis.period_used_s
        pair = f"{a.name} / {b.name}"
        start = max(np.nanmin(xa), np.nanmin(xb))
        end = min(np.nanmax(xa), np.nanmax(xb))
        if end <= start:
            issues.append(Issue(Severity.WARNING, f"{pair} : aucun recouvrement temporel.",
                                requirement="REQ_COMMON_KH_2104"))
            continue
        tol = 2 * max(ta, tb)
        end_gap = np.nanmax(xa) - np.nanmax(xb)
        if abs(end_gap) > tol:
            late = b.name if end_gap > 0 else a.name
            issues.append(Issue(Severity.WARNING,
                                f"{pair} : fin de flux décalée de {abs(end_gap):.6g} s "
                                f"({late} s'arrête plus tôt : perte de flux possible).",
                                requirement="REQ_COMMON_KH_2104"))
        if abs(ta - tb) > 0.1 * min(ta, tb):
            issues.append(Issue(Severity.INFO, f"{pair} : fréquences différentes "
                                f"({ms(ta)} ms / {ms(tb)} ms), sans effet sur le traitement.",
                                requirement="REQ_COMMON_KH_2100"))
            continue
        offset = _phase_offset(xa, xb, ta)
        if offset is not None:
            severity = Severity.INFO if abs(offset) <= 0.1 * ta else Severity.WARNING
            issues.append(Issue(severity, f"{pair} : déphasage médian des échantillons "
                                f"{ms(offset)} ms (période {ms(ta)} ms).",
                                requirement="REQ_COMMON_KH_2104"))
    return issues
