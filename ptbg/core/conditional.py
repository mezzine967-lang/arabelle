"""Traitement conditionnel par signaux Bool (REQ_COMMON_KH_5407 et section 4.5).

REQ_COMMON_KH_5407 : le curseur horizontal peut être conditionné par un
signal Bool supplémentaire. Ici, une ``Condition`` combine un ou plusieurs
termes « signal Bool = état attendu » par ET ou OU. Elle sert :

- au curseur horizontal : seuls les franchissements survenant pendant que la
  condition est vraie sont retenus ;
- au traitement conditionnel (section 4.5, REQ_COMMON_KH_5500 dont l'énoncé
  est VIDE dans la Rev. A) : statistiques des signaux analogiques pendant les
  périodes où la condition est vraie. Ce comportement est une proposition à
  valider (docs/POINTS_OUVERTS.md), construite uniquement sur 5407.

Règles sans interpolation :
- Bool du MÊME fichier : état lu sur la même ligne que la mesure analogique ;
- Bool d'un AUTRE fichier : état maintenu du dernier échantillon Bool
  antérieur, sur l'axe des temps commun (explicitement indiqué) ;
- Bool vide, invalide ou hors de sa plage de temps : condition FAUSSE.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from ptbg.core.data_package import SourceFile, Timeline


@dataclass
class ConditionTerm:
    """« signal = état » ; ``file_id`` désigne le fichier du signal Bool."""
    file_id: str
    signal: str
    expected: bool = True


@dataclass
class Condition:
    """Combinaison ET / OU de termes Bool ; vide = toujours vraie."""

    terms: list[ConditionTerm] = field(default_factory=list)
    combine: str = "AND"          # "AND" ou "OR"

    def describe(self) -> str:
        joiner = " ET " if self.combine == "AND" else " OU "
        return joiner.join(f"{term.signal} = {int(term.expected)}" for term in self.terms)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Condition":
        return cls([ConditionTerm(**term) for term in data.get("terms", [])], data.get("combine", "AND"))


def _term_state(term: ConditionTerm, target: SourceFile, find, timeline: Timeline) -> np.ndarray:
    """État du terme pour chaque échantillon du fichier cible."""
    source = find(term.file_id)
    if source is None or not source.is_loaded:
        return np.zeros(target.analysis.n_samples, dtype=bool)
    values = source.signal(term.signal).values
    if source is target:
        state = values
    else:
        xs, xt = timeline.x(source), timeline.x(target)
        order = np.argsort(xs, kind="stable")
        position = np.searchsorted(xs[order], xt, side="right") - 1
        state = np.full(xt.size, np.nan)
        inside = (position >= 0) & np.isfinite(xt)
        state[inside] = values[order][position[inside]]
    finite = np.isfinite(state)
    return finite & ((state >= 0.5) == term.expected)


def evaluate(condition: Condition, target: SourceFile, find, timeline: Timeline) -> np.ndarray:
    """Masque booléen : condition vraie sur chaque échantillon de ``target``.

    ``find`` est la fonction ``Workspace.find`` (résolution d'un file_id).
    """
    if not condition.terms:
        return np.ones(target.analysis.n_samples, dtype=bool)
    states = [_term_state(term, target, find, timeline) for term in condition.terms]
    combined = states[0]
    for state in states[1:]:
        combined = (combined & state) if condition.combine == "AND" else (combined | state)
    return combined


def true_intervals(x: np.ndarray, mask: np.ndarray) -> list[tuple[float, float]]:
    """Périodes (x début, x fin) où le masque est vrai, en échantillons consécutifs."""
    padded = np.concatenate(([False], mask, [False])).astype(np.int8)
    edges = np.flatnonzero(np.diff(padded))
    return [(float(x[a]), float(x[b - 1])) for a, b in zip(edges[0::2], edges[1::2])]


@dataclass
class ConditionalStats:
    """Statistiques d'un signal analogique pendant que la condition est vraie."""
    signal: str
    samples: int
    duration_s: float
    minimum: float
    maximum: float
    mean: float
    std: float
    intervals: int
    time_above_s: float | None = None     # si un seuil est fourni

    def as_row(self) -> list[str]:
        def fmt(value):
            return "—" if value is None or not np.isfinite(value) else f"{value:.6g}"
        return [self.signal, str(self.samples), fmt(self.duration_s), fmt(self.minimum),
                fmt(self.maximum), fmt(self.mean), fmt(self.std), str(self.intervals),
                fmt(self.time_above_s)]


STATS_HEADER = ["Signal", "Échantillons", "Durée (s)", "Min", "Max", "Moyenne",
                "Écart-type", "Périodes", "Durée ≥ seuil (s)"]


def conditional_statistics(name: str, x: np.ndarray, y: np.ndarray, mask: np.ndarray,
                           level: float | None = None) -> ConditionalStats:
    """Statistiques de ``y`` sur les échantillons où ``mask`` est vrai.

    La durée cumule les intervalles entre deux échantillons consécutifs tous
    deux sous condition (état maintenu jusqu'à l'échantillon suivant).
    """
    selected = mask & np.isfinite(y) & np.isfinite(x)
    values = y[selected]
    pairs = selected[:-1] & selected[1:]
    widths = np.diff(x)[pairs] if x.size > 1 else np.empty(0)
    intervals = len(true_intervals(x, selected))
    above = None
    if level is not None and x.size > 1:
        above = float(np.sum(np.diff(x)[pairs & (y[:-1] >= level)]))
    if values.size == 0:
        return ConditionalStats(name, 0, 0.0, np.nan, np.nan, np.nan, np.nan, 0, above)
    return ConditionalStats(name, int(values.size), float(np.sum(widths)), float(values.min()),
                            float(values.max()), float(values.mean()), float(values.std()),
                            intervals, above)
