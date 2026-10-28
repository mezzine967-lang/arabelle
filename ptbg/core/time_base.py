"""Analyse de la base de temps d'un fichier (section 3.1 « Time Base definition »).

Requis couverts :

- REQ_COMMON_KH_4100 : définition du raster et contrôle de
  - la VALEUR de la période (médiane des Δt, comparée au raster nominal),
  - la STABILITÉ de la période (Δt dans la tolérance, jitter mesuré),
  - la CROISSANCE CONTINUE (pas de doublon ni de retour arrière) ;
- REQ_COMMON_KH_4101 : repérage des incohérences : données manquantes
  (Δt ≈ k × période, k ≥ 2), mauvais phasage (Δt qui n'est pas un multiple
  de la période), changement de fréquence, horodatage illisible ;
- REQ_COMMON_KH_4105 : calcul vectorisé numpy en O(n), aucune exception pour
  une base de temps « malade », nombre d'événements mémorisés plafonné ;
- REQ_COMMON_KH_4106 : raster normal imposé par l'utilisateur ;
- REQ_COMMON_KH_4107 : horodatage absolu régularisé, jitter ignoré ;
- REQ_COMMON_KH_2100 / 2104 : fréquences quelconques, variations de
  fréquence et pertes de flux détectées sans perturber le traitement.

Vocabulaire :
  T    : période (raster) de référence d'un segment ;
  tol  : tolérance absolue = tolérance % × T ;
  Δt « normal »      : |Δt − T| ≤ tol  (le jitter dans la tolérance est ignoré) ;
  Δt « manque »      : |Δt − k·T| ≤ tol avec k ≥ 2 -> k − 1 échantillons manquants ;
  Δt « déphasage »   : Δt positif hors de la grille du raster ;
  horodatage aberrant : mesure isolée dont l'instant s'écarte de plus de
                       10 périodes de ses deux voisins, qui eux se suivent
                       normalement (ex. « 00:00:00 » au milieu d'un essai à
                       18 h) : signalée en ERREUR et exclue de l'analyse et
                       des courbes, au lieu de produire un faux retour
                       arrière suivi d'un faux trou de plusieurs heures ;
  segment            : portion du fichier à période constante ; un changement
                       de fréquence est une suite d'au moins N intervalles
                       consécutifs hors raster et cohérents entre eux.

Horodatage régularisé (« jitter ignoré », REQ 4107) : dans chaque bloc
d'échantillons alignés sur la grille, le rang de cycle k de chaque mesure est
connu (les manques sautent des rangs) ; une droite t = a + T·k est ajustée par
moindres carrés et remplace les temps bruts. Le jitter disparaît, les manques
restent visibles, aucune mesure n'est créée ni supprimée.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from ptbg.core.diagnostics import Severity


class EventKind(Enum):
    """Catégories d'événements temporels : libellé, libellé court, gravité."""
    INVALID = ("Horodatage illisible", "illisible(s)", Severity.ERROR)
    OUTLIER = ("Horodatage aberrant isolé", "aberrant(s)", Severity.ERROR)
    DUPLICATE = ("Horodatage dupliqué (Δt = 0)", "doublon(s)", Severity.ERROR)
    BACKWARD = ("Retour arrière du temps (Δt < 0)", "retour(s) arrière", Severity.ERROR)
    MISSING = ("Données manquantes", "trou(s)", Severity.WARNING)
    PHASE = ("Déphasage (Δt hors raster)", "déphasage(s)", Severity.WARNING)
    FREQUENCY = ("Changement de fréquence", "changement(s) de fréquence", Severity.WARNING)

    @property
    def label(self) -> str:
        return self.value[0]

    @property
    def short(self) -> str:
        return self.value[1]

    @property
    def severity(self) -> Severity:
        return self.value[2]


def ms(seconds: float) -> str:
    """Durée en millisecondes, arrondie à la nanoseconde : 0.02 -> « 20 »."""
    if not np.isfinite(seconds):
        return "—"
    text = f"{seconds * 1e3:.6f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


@dataclass(frozen=True)
class TimeEvent:
    """Un événement : ``index`` est l'échantillon qui SUIT l'intervalle fautif."""
    kind: EventKind
    index: int
    dt_s: float
    detail: str = ""


@dataclass(frozen=True)
class Segment:
    """Portion à période constante (indices d'échantillons inclus)."""
    start: int
    end: int
    period_s: float


@dataclass
class Check:
    """Résultat d'un contrôle nommé de REQ 4100 / 4101."""
    name: str
    severity: Severity
    text: str


@dataclass
class TimeBaseAnalysis:
    """Résultat complet affiché dans le Time Base Monitor et le rapport."""
    n_samples: int
    n_valid: int
    start_s: float = np.nan
    end_s: float = np.nan
    period_estimated_s: float = np.nan
    period_nominal_s: float | None = None
    period_used_s: float = np.nan
    tolerance_s: float = np.nan
    tolerance_pct: float = 10.0
    dt_min_s: float = np.nan
    dt_max_s: float = np.nan
    dt_mean_s: float = np.nan
    dt_std_s: float = np.nan
    jitter_max_s: float = 0.0
    jitter_std_s: float = 0.0
    normal_ratio: float = 0.0
    missing_samples: int = 0
    checks: list[Check] = field(default_factory=list)
    events: list[TimeEvent] = field(default_factory=list)
    event_counts: Counter = field(default_factory=Counter)
    segments: list[Segment] = field(default_factory=list)
    regular_s: np.ndarray = field(default_factory=lambda: np.empty(0))
    dt_index: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))
    dt_values: np.ndarray = field(default_factory=lambda: np.empty(0))
    dt_kinds: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int8))
    excluded: np.ndarray = field(default_factory=lambda: np.empty(0, dtype=np.int64))  # aberrants

    @property
    def status(self) -> Severity:
        return max((check.severity for check in self.checks), default=Severity.OK)

    @property
    def duration_s(self) -> float:
        return self.end_s - self.start_s

    def summary(self) -> str:
        """Ligne de synthèse (arbre, Time Base Monitor, rapport)."""
        if self.n_valid < 2:
            return "Base de temps inexploitable"
        counts = ", ".join(f"{count} {kind.short}" for kind, count in self.event_counts.items())
        return (f"T = {ms(self.period_used_s)} ms ± {self.tolerance_pct:g} % ; "
                f"{self.normal_ratio * 100:.1f} % des Δt conformes ; "
                f"jitter max {ms(self.jitter_max_s)} ms"
                + (f" ; {counts}" if counts else " ; aucune anomalie"))


# Codes de classification des Δt (tableau ``dt_kinds``) pour le dessin du TBM.
DT_NORMAL, DT_MISSING, DT_PHASE, DT_DUPLICATE, DT_BACKWARD = 0, 1, 2, 3, 4
_KIND_OF_CODE = {DT_MISSING: EventKind.MISSING, DT_PHASE: EventKind.PHASE,
                 DT_DUPLICATE: EventKind.DUPLICATE, DT_BACKWARD: EventKind.BACKWARD}


OUTLIER_JUMP = 10      # écart minimal (en périodes) d'un horodatage aberrant isolé


def _isolated_outliers(t: np.ndarray, nominal: float | None) -> np.ndarray:
    """Positions (dans ``t``) des horodatages aberrants isolés (voir en-tête).

    Le temps saute de plus de ``OUTLIER_JUMP`` périodes en arrivant sur la
    mesure et repart aussitôt en sens inverse, alors que ses deux voisins se
    suivent (écart positif inférieur à ce saut). Une base de temps saine est
    croissante : un tel aller-retour n'est jamais un comportement normal."""
    if t.size < 3:
        return np.empty(0, dtype=np.int64)
    d = np.diff(t)
    positive = d[d > 0]
    period = nominal or (float(np.median(positive)) if positive.size else np.nan)
    if not (np.isfinite(period) and period > 0):
        return np.empty(0, dtype=np.int64)
    before, after, span = d[:-1], d[1:], t[2:] - t[:-2]
    jump = OUTLIER_JUMP * period
    spike = ((before > jump) & (after < -jump)) | ((before < -jump) & (after > jump))
    return np.flatnonzero(spike & (span > 0) & (span <= jump)) + 1


def _run_starts(mask: np.ndarray, min_length: int) -> np.ndarray:
    """Débuts des suites de True d'au moins ``min_length`` éléments."""
    if min_length <= 0 or mask.size == 0:
        return np.empty(0, dtype=np.int64)
    padded = np.concatenate(([False], mask, [False]))
    edges = np.flatnonzero(np.diff(padded.astype(np.int8)))
    starts, ends = edges[0::2], edges[1::2]
    return starts[(ends - starts) >= min_length]


def _split_frequency_segments(dt: np.ndarray, period: float, tol_frac: float,
                              min_run: int) -> list[tuple[int, int, float]]:
    """Découpe les Δt en segments de période constante.

    Un changement de fréquence est déclaré quand ``min_run`` intervalles
    consécutifs sont tous hors raster ET cohérents entre eux (écart relatif
    ≤ tolérance). Renvoie des triplets (début, fin exclue, période) en indices
    de Δt.

    Le changement suivant est cherché dans une fenêtre qui s'agrandit (× 4)
    tant qu'elle n'en contient pas : le coût reste proportionnel à la longueur
    du fichier, même avec des milliers de changements (REQ 4105). Une suite
    vue en entier dans la fenêtre est la même que dans tout le fichier : le
    résultat est identique à une recherche sur toute la fin du fichier.
    """
    segments = []
    start, current, first = 0, period, True
    while start < dt.size:
        change, window = None, max(64, 8 * min_run)
        while True:
            rest = dt[start:start + window]
            if rest.size >= max(min_run, 2):
                abnormal = (np.abs(rest - current) > tol_frac * current) & (rest > 0)
                steady = np.abs(np.diff(rest)) <= tol_frac * np.maximum(rest[:-1], rest[1:])
                linked = abnormal[:-1] & abnormal[1:] & steady
                starts = _run_starts(linked, min_run - 1)
                if not first:
                    starts = starts[starts >= 1]   # garantit la progression de la boucle
                if starts.size:
                    change = int(starts[0])
            if change is not None or start + window >= dt.size:
                break
            window *= 4
        if change is None:
            segments.append((start, dt.size, current))
            break
        if change > 0:
            segments.append((start, start + change, current))
        # change == 0 au 1er tour : le fichier démarre à une autre fréquence.
        current = float(np.median(rest[change:change + min_run]))
        start += change
        first = False
    return segments or [(0, dt.size, period)]


def _classify(dt: np.ndarray, period: float, tol: float) -> tuple[np.ndarray, np.ndarray]:
    """Classe chaque Δt (codes DT_*) et renvoie aussi le nombre de cycles k."""
    with np.errstate(divide="ignore", invalid="ignore", over="ignore"):
        cycles = np.rint(dt / period)
        # Un Δt gigantesque (horodatage corrompu) ne peut pas être situé sur la
        # grille à la tolérance près en flottant 64 bits : il reste « hors raster ».
        on_grid = (np.abs(dt - cycles * period) <= tol) & (np.abs(dt) * 1e-12 <= tol)
    codes = np.full(dt.size, DT_PHASE, dtype=np.int8)
    codes[on_grid & (cycles == 1)] = DT_NORMAL
    codes[on_grid & (cycles >= 2)] = DT_MISSING
    codes[dt == 0] = DT_DUPLICATE
    codes[dt < 0] = DT_BACKWARD
    return codes, cycles


def _regularize(t: np.ndarray, codes: np.ndarray, cycles: np.ndarray,
                segment_starts: list[int]) -> np.ndarray:
    """Horodatage régularisé par blocs alignés sur la grille (voir en-tête).

    Un bloc s'arrête à tout Δt hors grille et au début de chaque segment de
    fréquence (une droite unique ne peut pas représenter deux périodes)."""
    aligned = (codes == DT_NORMAL) | (codes == DT_MISSING)
    breaks = ~aligned
    breaks[[start for start in segment_starts if start > 0]] = True
    block = np.concatenate(([0], np.cumsum(breaks)))            # n° de bloc par mesure
    steps = np.concatenate(([0.0], np.where(aligned, cycles, 0.0)))
    rank = np.cumsum(steps)
    rank = rank - rank[np.searchsorted(block, block, side="left")]  # rang depuis le début du bloc
    count = np.bincount(block).astype(float)
    mean_rank = np.bincount(block, rank) / count
    mean_t = np.bincount(block, t) / count
    dk = rank - mean_rank[block]
    dtt = t - mean_t[block]
    sxx = np.bincount(block, dk * dk)
    sxy = np.bincount(block, dk * dtt)
    with np.errstate(divide="ignore", invalid="ignore"):
        slope = np.where(sxx > 0, sxy / sxx, 0.0)
    regular = mean_t[block] + slope[block] * dk
    small = count[block] < 3          # 1 ou 2 mesures : rien à lisser
    regular[small] = t[small]
    return regular


def analyze(seconds: np.ndarray, nominal_period_s: float | None = None,
            tolerance_pct: float = 10.0, min_run: int = 10, max_events: int = 5000,
            preferred_periods_ms=(10.0, 20.0)) -> TimeBaseAnalysis:
    """Analyse complète d'une base de temps en secondes (NaN = illisible)."""
    seconds = np.asarray(seconds, dtype=np.float64)
    valid_index = np.flatnonzero(np.isfinite(seconds))
    result = TimeBaseAnalysis(n_samples=seconds.size, n_valid=valid_index.size,
                              period_nominal_s=nominal_period_s, tolerance_pct=tolerance_pct,
                              regular_s=seconds.copy())
    invalid_index = np.flatnonzero(~np.isfinite(seconds))
    if invalid_index.size:
        result.event_counts[EventKind.INVALID] = int(invalid_index.size)
        result.events.extend(TimeEvent(EventKind.INVALID, int(i), np.nan)
                             for i in invalid_index[:max_events])
        result.checks.append(Check("Lisibilité", Severity.ERROR,
                                   f"{invalid_index.size} horodatage(s) illisible(s)."))
    outliers = _isolated_outliers(seconds[valid_index], nominal_period_s)
    if outliers.size:
        aberrant = valid_index[outliers]
        result.excluded = aberrant
        result.event_counts[EventKind.OUTLIER] = int(aberrant.size)
        result.events.extend(TimeEvent(EventKind.OUTLIER, int(i), np.nan, f"t brut = {seconds[i]:.9g} s")
                             for i in aberrant[:max_events])
        result.checks.append(Check("Horodatages aberrants", Severity.ERROR,
                                   f"{aberrant.size} horodatage(s) isolé(s) très éloigné(s) de leurs voisins : "
                                   "exclu(s) de l'analyse du raster et des courbes (valeur brute dans le "
                                   "diagnostic du fichier)."))
        valid_index = np.delete(valid_index, outliers)
        result.regular_s[aberrant] = np.nan
        result.n_valid = valid_index.size
    if valid_index.size < 2:
        result.checks.append(Check("Valeur de la période", Severity.ERROR,
                                   "Moins de deux horodatages valides : période indéfinissable."))
        return result

    t = seconds[valid_index]
    dt = np.diff(t)
    result.start_s, result.end_s = float(np.min(t)), float(np.max(t))
    positive = dt[dt > 0]
    estimated = float(np.median(positive)) if positive.size else np.nan
    result.period_estimated_s = estimated
    reference = nominal_period_s or estimated
    if not np.isfinite(reference) or reference <= 0:
        result.checks.append(Check("Croissance continue", Severity.ERROR,
                                   "Aucun intervalle positif : le temps ne progresse pas."))
        return result
    tol_frac = tolerance_pct / 100.0
    result.period_used_s, result.tolerance_s = reference, tol_frac * reference
    result.dt_min_s, result.dt_max_s = float(dt.min()), float(dt.max())
    result.dt_mean_s, result.dt_std_s = float(dt.mean()), float(dt.std())

    # 1) Segments de fréquence (REQ 2104), puis classement des Δt par segment.
    codes = np.empty(dt.size, dtype=np.int8)
    cycles = np.empty(dt.size)
    frequency_changes = []
    segment_starts = []
    for position, (begin, end, period) in enumerate(_split_frequency_segments(dt, reference, tol_frac, min_run)):
        segment_starts.append(begin)
        codes[begin:end], cycles[begin:end] = _classify(dt[begin:end], period, tol_frac * period)
        result.segments.append(Segment(int(valid_index[begin]), int(valid_index[end]), period))
        if position > 0:
            frequency_changes.append((begin, period))
    # 2) Événements (plafonnés), en indices d'échantillons du fichier.
    sample_after = valid_index[1:]
    for code, kind in _KIND_OF_CODE.items():
        where = np.flatnonzero(codes == code)
        if where.size == 0:
            continue
        result.event_counts[kind] = int(where.size)
        for i in where[:max_events]:
            detail = (f"{int(cycles[i]) - 1} échantillon(s) manquant(s)" if code == DT_MISSING
                      else f"Δt = {ms(dt[i])} ms")
            result.events.append(TimeEvent(kind, int(sample_after[i]), float(dt[i]), detail))
    for begin, period in frequency_changes:
        result.event_counts[EventKind.FREQUENCY] += 1
        result.events.append(TimeEvent(EventKind.FREQUENCY, int(valid_index[begin]), float(dt[begin]),
                                       f"nouvelle période {ms(period)} ms"))
    result.events.sort(key=lambda event: event.index)
    del result.events[max_events:]
    result.missing_samples = int(np.sum(cycles[codes == DT_MISSING] - 1))
    result.normal_ratio = float(np.count_nonzero(codes == DT_NORMAL) / dt.size)

    # 3) Horodatage régularisé (jitter ignoré) et mesure du jitter résiduel.
    regular = _regularize(t, codes, cycles, segment_starts)
    residual = t - regular
    result.jitter_max_s = float(np.max(np.abs(residual)))
    result.jitter_std_s = float(np.std(residual))
    result.regular_s[valid_index] = regular
    result.dt_index, result.dt_values, result.dt_kinds = sample_after, dt, codes

    _add_checks(result, codes, estimated, nominal_period_s, tol_frac, preferred_periods_ms)
    return result


def _add_checks(result: TimeBaseAnalysis, codes: np.ndarray, estimated: float,
                nominal: float | None, tol_frac: float, preferred_periods_ms) -> None:
    """Traduit les comptages en contrôles lisibles (REQ 4100 / 4101)."""
    counts = result.event_counts
    # Valeur de la période.
    text = f"Période mesurée (médiane des Δt) : {ms(estimated)} ms"
    severity = Severity.OK
    if nominal:
        text += f" ; période nominale saisie : {ms(nominal)} ms"
        if abs(estimated - nominal) > tol_frac * nominal:
            severity = Severity.WARNING
            text += " -> ÉCART supérieur à la tolérance"
    elif not any(abs(estimated * 1e3 - p) <= tol_frac * p for p in preferred_periods_ms):
        text += " (hors des valeurs préférées " + "/".join(f"{p:g}" for p in preferred_periods_ms) \
                + " ms : information seulement, REQ 2100)"
    result.checks.append(Check("Valeur de la période", severity, text))
    # Stabilité de la période.
    unstable = counts.get(EventKind.PHASE, 0) + counts.get(EventKind.FREQUENCY, 0)
    result.checks.append(Check(
        "Stabilité de la période", Severity.WARNING if unstable else Severity.OK,
        f"{result.normal_ratio * 100:.2f} % des Δt à ± {result.tolerance_pct:g} % (± {ms(result.tolerance_s)} ms) ; "
        f"Δt min/moy/max {ms(result.dt_min_s)} / {ms(result.dt_mean_s)} / {ms(result.dt_max_s)} ms, "
        f"écart-type {ms(result.dt_std_s)} ms ; jitter max {ms(result.jitter_max_s)} ms, "
        f"écart-type {ms(result.jitter_std_s)} ms (ignoré dans la tolérance) ; "
        f"{counts.get(EventKind.PHASE, 0)} déphasage(s), {counts.get(EventKind.FREQUENCY, 0)} "
        "changement(s) de fréquence."))
    # Croissance continue.
    not_increasing = counts.get(EventKind.DUPLICATE, 0) + counts.get(EventKind.BACKWARD, 0)
    result.checks.append(Check(
        "Croissance continue", Severity.ERROR if not_increasing else Severity.OK,
        "Temps strictement croissant." if not not_increasing else
        f"{counts.get(EventKind.DUPLICATE, 0)} doublon(s) et {counts.get(EventKind.BACKWARD, 0)} "
        "retour(s) arrière."))
    # Données manquantes.
    gaps = counts.get(EventKind.MISSING, 0)
    result.checks.append(Check(
        "Données manquantes", Severity.WARNING if gaps else Severity.OK,
        f"{gaps} trou(s), {result.missing_samples} échantillon(s) manquant(s) au total." if gaps
        else "Aucun trou dans le raster."))
