"""Dessiner les écarts temporels sans confondre ligne CSV et timestamp.

v0.7.0 — Time Base Monitor détaillé. Le calcul exact précède le dessin ;
l'axe X représente l'ordre physique du fichier, même si le temps recule.
"""
from __future__ import annotations

import math
from decimal import Decimal, localcontext
from pathlib import Path

from inspection_temps import InspectionTemps, LIBELLES
from signal_csv import _flottant

COULEURS = {"dans_tolerance": "#23745a", "observe": "#37759b",
            "temps_duplique": "#bc7600", "retour_arriere": "#bf3030",
            "pas_hors_tolerance": "#7d3ab4"}


def creer_figure_temps(inspection: InspectionTemps):
    """Retourner figure et axe ; refuser une perte de distinction des Δt.

    Les mesures de temps invalides et les interruptions sont exclues du dessin
    et restent comptées dans son texte. Des points seuls évitent de franchir
    graphiquement les ruptures. Le tableau conserve toujours la valeur exacte.
    """
    from matplotlib.figure import Figure

    correspondances: dict[float, Decimal] = {}

    def graphique(nombre):
        valeur = _flottant(nombre)
        if valeur is None or (valeur in correspondances and correspondances[valeur] != nombre):
            raise ValueError("La précision des écarts dépasse ce tracé. Les valeurs exactes restent disponibles dans le tableau.")
        correspondances[valeur] = nombre
        return valeur

    groupes = {}
    for intervalle in inspection.intervalles:
        if intervalle.delta is not None:
            xs, ys = groupes.setdefault(intervalle.nature, ([], []))
            xs.append(intervalle.ligne_apres)
            ys.append(graphique(intervalle.delta))
    bornes = None
    if inspection.comparaison_effectuee:
        with localcontext() as contexte:
            contexte.prec = 4100
            bornes = tuple(graphique(v) for v in (
                inspection.pas - inspection.tolerance, inspection.pas,
                inspection.pas + inspection.tolerance))
    if correspondances and not math.isfinite(max(correspondances) - min(correspondances)):
        raise ValueError("L'étendue des écarts dépasse la capacité du graphique ; consulter le tableau.")

    figure = Figure(figsize=(9, 5), dpi=100, facecolor="white")
    axe = figure.add_subplot(111)
    figure.subplots_adjust(left=0.11, right=0.97, bottom=0.24, top=0.84)
    for nature, (xs, ys) in groupes.items():
        axe.plot(xs, ys, linestyle="None", marker=".", markersize=5,
                 color=COULEURS[nature], label=LIBELLES[nature])
    if bornes:
        axe.axhspan(bornes[0], bornes[2], color="#2f8b65", alpha=0.12,
                    label="Tolérance saisie")
        axe.axhline(bornes[1], linestyle="--", color="#32734d", linewidth=1,
                    label="Pas attendu")
    if groupes or bornes:
        axe.legend(loc="best", fontsize=8, ncol=2)
    if not groupes:
        axe.text(0.5, 0.5, "Aucun intervalle calculable", transform=axe.transAxes,
                 ha="center", va="center")
    axe.set_title("Time Base Monitor — écarts entre enregistrements", loc="left", fontsize=11)
    axe.set_xlabel("Ligne CSV de la mesure suivante (ordre du fichier)")
    axe.set_ylabel(f"Δt [{inspection.unite or 'unité inconnue'}]")
    axe.ticklabel_format(axis="both", style="plain", useOffset=False)
    axe.grid(alpha=0.18)
    figure.suptitle(Path(inspection.fichier).name, fontsize=10, x=0.11, ha="left")
    non_calculables = sum(v.delta is None for v in inspection.intervalles)
    bilan = (f"Pas attendu {inspection.pas} ± {inspection.tolerance}" if inspection.comparaison_effectuee
             else "Observations locales — comparaison au pas attendu non effectuée")
    figure.text(0.11, 0.11, bilan, fontsize=9)
    figure.text(0.11, 0.065, f"{non_calculables} intervalle(s) non calculable(s) | "
                f"{inspection.lignes_rejetees} rejet(s) CSV | lecture complète : "
                f"{'oui' if inspection.lecture_complete else 'non'}", fontsize=8)
    figure.text(0.11, 0.025, "Temps bruts conservés. Un écart ne prouve pas une perte de données.", fontsize=8, color="#555555")
    return figure, axe
