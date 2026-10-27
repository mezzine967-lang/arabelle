"""Lecture des échantillons : curseurs, croisements, réduction d'affichage.

Requis servis : REQ_COMMON_KH_5401 / 5402 / 5403 (valeur croisée par un
curseur vertical), 5406 / 5407 (curseur horizontal et croisements), 4105
(fluidité avec des millions de points).

Règle constante : AUCUNE interpolation de valeur. Le curseur lit
l'échantillon réel :
- Float : l'échantillon le plus proche dans le temps ;
- Bool / Texte / groupe : l'échantillon précédent (état maintenu jusqu'au
  suivant), ce qui correspond au tracé en escalier.
Le temps de l'échantillon lu et sa ligne CSV sont toujours restitués.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class Sample:
    """Échantillon lu par un curseur."""
    index: int          # indice dans le fichier
    x: float            # abscisse de l'échantillon (et non du curseur)
    value: float        # NaN si la cellule est vide ou invalide


# Recul toléré entre deux abscisses (s) : les arrondis flottants de l'horodatage
# régularisé (≈ 1e-15 s) ne doivent pas faire croire à un retour arrière.
ORDER_TOLERANCE_S = 1e-9


def is_sorted(x: np.ndarray) -> bool:
    """Vrai si les abscisses valides sont croissantes (recherche dichotomique possible)."""
    finite = x[np.isfinite(x)]
    return bool(finite.size < 2 or np.all(np.diff(finite) >= -ORDER_TOLERANCE_S))


def sample_at(x: np.ndarray, values: np.ndarray, position: float, hold: bool,
              sorted_x: bool | None = None) -> Sample | None:
    """Échantillon lu à l'abscisse ``position`` (voir règle du module).

    ``sorted_x`` évite de retester l'ordre à chaque mouvement de souris (le
    rendu le calcule une fois par courbe). Les abscisses non croissantes
    (doublons, retours arrière) restent lisibles par une recherche directe,
    plus lente mais exacte.
    """
    if x.size == 0 or not np.isfinite(position):
        return None
    if sorted_x is None:
        sorted_x = is_sorted(x)
    valid = np.isfinite(x)
    if sorted_x:
        candidates = None if valid.all() else np.flatnonzero(valid)
        xs = x if candidates is None else x[candidates]
        if xs.size == 0:
            return None
        right = int(np.searchsorted(xs, position, side="right"))
        if hold:
            if right == 0:
                return None             # avant le 1er échantillon : rien à maintenir
            k = right - 1
        else:
            lo, hi = max(right - 1, 0), min(right, xs.size - 1)
            k = lo if abs(xs[lo] - position) <= abs(xs[hi] - position) else hi
        pick = k if candidates is None else int(candidates[k])
    else:
        if hold:
            distance = np.where(valid & (x <= position), position - x, np.inf)
        else:
            distance = np.where(valid, np.abs(x - position), np.inf)
        if not np.isfinite(distance).any():
            return None
        pick = int(np.argmin(distance))
    return Sample(int(pick), float(x[pick]), float(values[pick]))


def step_index(x: np.ndarray, position: float, direction: int) -> float | None:
    """Abscisse de l'échantillon suivant (+1) ou précédent (-1) : flèches clavier."""
    finite = np.sort(x[np.isfinite(x)])
    if finite.size == 0:
        return None
    if direction > 0:
        i = int(np.searchsorted(finite, position, side="right"))
        return float(finite[min(i, finite.size - 1)])
    i = int(np.searchsorted(finite, position, side="left")) - 1
    return float(finite[max(i, 0)])


def break_at(x: np.ndarray, y: np.ndarray, starts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Insère un NaN avant chaque indice de ``starts`` : la courbe est
    interrompue sur un trou de la base de temps au lieu de le traverser."""
    if starts.size == 0:
        return x, y
    return np.insert(x, starts, np.nan), np.insert(y, starts, np.nan)


def missing_markers(x: np.ndarray, values: np.ndarray, missing: np.ndarray) -> np.ndarray:
    """Indices des croix encadrant les cellules VIDES d'une variable.

    Pour chaque suite de cellules vides : le dernier échantillon connu avant
    et le premier connu après. Seules les cellules vides du CSV produisent des
    croix (pas un saut de temps, pas une valeur invalide).
    """
    if not missing.any():
        return np.empty(0, dtype=np.int64)
    known = np.isfinite(values) & ~missing
    padded = np.concatenate(([False], missing, [False])).astype(np.int8)
    edges = np.flatnonzero(np.diff(padded))
    run_starts, run_ends = edges[0::2], edges[1::2]   # [début, fin exclue)
    known_index = np.flatnonzero(known)
    markers = []
    for start, end in zip(run_starts, run_ends):
        before = known_index[known_index < start]
        after = known_index[known_index >= end]
        if before.size:
            markers.append(before[-1])
        if after.size:
            markers.append(after[0])
    return np.unique(np.array(markers, dtype=np.int64))


def decimate(x: np.ndarray, y: np.ndarray, x_min: float, x_max: float,
             max_points: int) -> tuple[np.ndarray, np.ndarray]:
    """Réduit une courbe pour l'affichage en conservant min et max par paquet.

    Les pics et les transitions logiques restent visibles, les NaN (ruptures)
    sont conservés. Les données d'origine ne sont pas modifiées : le curseur lit
    toujours les vrais échantillons.
    """
    if x.size <= max_points:
        return x, y
    if is_sorted(x):
        # Abscisses rendues monotones (NaN des ruptures neutralisés) pour la dichotomie.
        monotone = np.maximum.accumulate(np.where(np.isnan(x), -np.inf, x))
        lo = max(int(np.searchsorted(monotone, x_min, side="left")) - 1, 0)
        hi = min(int(np.searchsorted(monotone, x_max, side="right")) + 1, x.size)
        x, y = x[lo:hi], y[lo:hi]
    else:
        # Temps non monotone (retours arrière réels) : fenêtre par masque.
        keep = np.isnan(x) | ((x >= x_min) & (x <= x_max))
        x, y = x[keep], y[keep]
    if x.size <= max_points:
        return x, y
    buckets = max(max_points // 2, 1)
    size = int(np.ceil(x.size / buckets))
    pad = buckets * size - x.size
    xp = np.concatenate((x, np.full(pad, np.nan)))
    yp = np.concatenate((y, np.full(pad, np.nan))).reshape(buckets, size)
    nan_rows = np.isnan(yp)
    lo_idx = np.argmin(np.where(nan_rows, np.inf, yp), axis=1)
    hi_idx = np.argmax(np.where(nan_rows, -np.inf, yp), axis=1)
    first = np.minimum(lo_idx, hi_idx)
    second = np.maximum(lo_idx, hi_idx)
    base = np.arange(buckets) * size
    picks = np.stack((base + first, base + second), axis=1).ravel()
    out_x, out_y = xp[picks], yp.ravel()[picks]
    # Un paquet contenant une rupture la conserve (NaN après ses extrêmes).
    gap_rows = np.flatnonzero(nan_rows.any(axis=1) & ~nan_rows.all(axis=1))
    if gap_rows.size:
        insert_at = (gap_rows + 1) * 2
        out_x = np.insert(out_x, insert_at, np.nan)
        out_y = np.insert(out_y, insert_at, np.nan)
    return out_x, out_y


@dataclass(frozen=True)
class Crossing:
    """Franchissement d'un seuil par un signal analogique (REQ 5406)."""
    index: int          # 1er échantillon APRÈS le franchissement
    x: float
    rising: bool


def crossings(x: np.ndarray, y: np.ndarray, level: float,
              allowed: np.ndarray | None = None) -> list[Crossing]:
    """Franchissements du niveau ``level`` entre deux échantillons valides
    consécutifs. ``allowed`` (masque booléen) restreint aux instants où la
    condition est vraie sur LES DEUX échantillons (REQ 5407)."""
    valid = np.isfinite(y) & np.isfinite(x)
    if allowed is not None:
        valid &= allowed
    index = np.flatnonzero(valid)
    if index.size < 2:
        return []
    contiguous = np.diff(index) == 1          # pas de franchissement à travers un manque
    above = y[index] >= level
    change = (above[1:] != above[:-1]) & contiguous
    after = index[1:][change]
    return [Crossing(int(i), float(x[i]), bool(y[i] >= level)) for i in after]
