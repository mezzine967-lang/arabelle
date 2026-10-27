"""Nuage X/Y pour le contrôle de corrélation (REQ_COMMON_KH_5408).

Deux signaux sont associés point par point :
- même fichier : même ligne (même instant d'échantillonnage) ;
- fichiers différents : pour chaque échantillon X, l'échantillon Y le plus
  proche sur l'axe des temps commun, s'il est à moins d'une demi-période
  (sinon le point n'est pas formé : aucune interpolation).

Le curseur X/Y désigne un point du nuage ; il est affiché soit avec deux
curseurs (droite verticale en X et horizontale en Y), soit par le seul point
de croisement. Le coefficient de corrélation de Pearson et la droite de
régression aident au contrôle de corrélation.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class XYData:
    """Couples (X, Y) formés, instants associés et corrélation."""

    x: np.ndarray
    y: np.ndarray
    t: np.ndarray          # abscisse temporelle de chaque point (échantillon X)
    index: np.ndarray      # indice de l'échantillon X dans son fichier
    r: float               # corrélation de Pearson (NaN si indéfinie)
    slope: float
    intercept: float

    @property
    def n(self) -> int:
        return int(self.x.size)

    def describe(self) -> str:
        if self.n < 2 or not np.isfinite(self.r):
            return f"{self.n} point(s) ; corrélation indéfinie"
        return (f"{self.n} points ; r = {self.r:.4f} ; "
                f"régression Y = {self.slope:.6g} · X + {self.intercept:.6g}")


def _fit(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float]:
    if x.size < 2 or np.ptp(x) == 0 or np.ptp(y) == 0:
        return np.nan, np.nan, np.nan
    r = float(np.corrcoef(x, y)[0, 1])
    slope, intercept = np.polyfit(x, y, 1)
    return r, float(slope), float(intercept)


def build_xy(tx: np.ndarray, vx: np.ndarray, ty: np.ndarray, vy: np.ndarray,
             same_file: bool, max_gap_s: float) -> XYData:
    """Forme les couples (X, Y) valides."""
    if same_file:
        keep = np.isfinite(vx) & np.isfinite(vy) & np.isfinite(tx)
        index = np.flatnonzero(keep)
        x, y, t = vx[keep], vy[keep], tx[keep]
    else:
        order = np.argsort(ty, kind="stable")
        ty_sorted, vy_sorted = ty[order], vy[order]
        right = np.clip(np.searchsorted(ty_sorted, tx), 1, max(ty_sorted.size - 1, 1))
        left = right - 1
        choose_left = np.abs(tx - ty_sorted[left]) <= np.abs(ty_sorted[right] - tx)
        nearest = np.where(choose_left, left, right)
        gap = np.abs(ty_sorted[nearest] - tx)
        y_all = vy_sorted[nearest]
        keep = np.isfinite(vx) & np.isfinite(y_all) & np.isfinite(tx) & (gap <= max_gap_s)
        index = np.flatnonzero(keep)
        x, y, t = vx[keep], y_all[keep], tx[keep]
    r, slope, intercept = _fit(x, y)
    return XYData(x, y, t, index, r, slope, intercept)


def nearest_point(data: XYData, px: float, py: float, x_span: float, y_span: float) -> int | None:
    """Point du nuage le plus proche d'un clic (distance normalisée par l'échelle)."""
    if data.n == 0:
        return None
    dx = (data.x - px) / (x_span or 1.0)
    dy = (data.y - py) / (y_span or 1.0)
    return int(np.argmin(dx * dx + dy * dy))


def point_at_time(data: XYData, t: float) -> int | None:
    """Point dont l'instant est le plus proche de ``t`` (lien avec le curseur temporel)."""
    if data.n == 0 or not np.isfinite(t):
        return None
    return int(np.argmin(np.abs(data.t - t)))
