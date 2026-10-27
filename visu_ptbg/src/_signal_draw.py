# -----------------------------------------------------------------------------
# VISU PTBG — dessin d'échantillons — V00.07.03
# Historique : première fonction de dessin indépendante de la fenêtre.
# Inspiration : signatures ax/xdata/ydata des templates de Sébastien.
# Requis concernés : 2200, 2201 (analogique), 3003, 3006 ; couverture partielle.
# -----------------------------------------------------------------------------
"""Dessiner sur un axe fourni ; aucune lecture CSV ni modification des données."""
from __future__ import annotations

import math


def sample_chart(ax, xdata, ydata, xdata_label, ydata_label, header,
                 *, relier_points=False, indices_coupures=()):
    """Afficher les mesures et, si permis, des segments interrompus aux trous.

    Le type Bool/Float et la conservation entre deux échantillons ne sont pas
    déduits des valeurs. Un tracé en escalier exigera une règle métier explicite.
    Les segments servent à lire la courbe : aucune mesure intermédiaire n'est
    calculée. Les NaN ajoutés ci-dessous sont des séparateurs de dessin seulement.
    Retourne l'artiste Matplotlib pour permettre son inspection dans les tests.
    """
    # === 1. Instructions graphiques : conserver chaque timestamp fourni ===
    coupures = set(indices_coupures)
    x_trace, y_trace = [], []
    for i, (x, y) in enumerate(zip(xdata, ydata)):
        if i in coupures:
            x_trace.append(math.nan)
            y_trace.append(math.nan)
        x_trace.append(x)
        y_trace.append(y)
    line, = ax.plot(x_trace, y_trace, linestyle="-" if relier_points else "None", marker=".",
                    linewidth=1.3,
                    markersize=3, color="#176a94", label=ydata_label)

    # === 2. Libellés et grille : ne pas imposer un début temporel à zéro ===
    ax.set_title(header, loc="left", fontsize=11)
    ax.set_xlabel(xdata_label)
    ax.set_ylabel(ydata_label)
    ax.grid(alpha=0.2)
    return line
