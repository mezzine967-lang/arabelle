"""Diagnostic quantitatif de la base de temps, indépendant de l'interface.

Le module distingue les faits (Δt, doublon, retour, valeur invalide) des
interprétations prudentes (trou ou changement de fréquence *probable*). Il ne
modifie, ne trie et n'interpole jamais les données du CSV.
"""
from __future__ import annotations

from collections import Counter
from decimal import Decimal, localcontext
from statistics import median
from typing import Any

from diagnostic_csv import CsvReadResult, _temps_decimal
from regles_temps import GRAVITE_ANOMALIE_TEMPORELLE, REGLES_TEMPS, ReglesTemps


def _texte(nombre: Decimal | None) -> str | None:
    """Conserver une écriture décimale exacte dans les sorties JSON."""
    return None if nombre is None else str(nombre)


def _proche(valeur: Decimal, reference: Decimal, tolerance: Decimal) -> bool:
    return abs(valeur - reference) <= tolerance


def _tolerance_relative(reference: Decimal, rapport: Decimal) -> Decimal:
    return abs(reference) * rapport


def _raster_estime(deltas: list[Decimal], regles: ReglesTemps) -> tuple[Decimal | None, Decimal | None, str | None]:
    """Estimer le groupe de Δt positifs majoritaire sans choisir en cas d'égalité."""
    if len(deltas) < 2:
        return None, None, "Moins de deux intervalles positifs calculables."
    groupes: list[list[Decimal]] = []
    for delta in sorted(deltas):
        for groupe in groupes:
            centre = median(groupe)
            if _proche(delta, centre, _tolerance_relative(centre, regles.tolerance_relative_inference)):
                groupe.append(delta)
                break
        else:
            groupes.append([delta])
    taille = max(len(groupe) for groupe in groupes)
    meilleurs = [groupe for groupe in groupes if len(groupe) == taille]
    if len(meilleurs) != 1 or taille < 2:
        return None, None, "Plusieurs rasters possibles : aucune valeur choisie arbitrairement."
    raster = median(meilleurs[0])
    tolerance = _tolerance_relative(raster, regles.tolerance_relative_inference)
    return raster, tolerance, None


def _intervalles(lecture: CsvReadResult, indice: int, decimale: str) -> tuple[list[dict[str, Any]], list[int]]:
    """Calculer seulement les couples de lignes voisines réellement exploitables."""
    lignes = lecture.rows
    valeurs = [_temps_decimal(ligne.fields[indice], decimale) for ligne in lignes]
    invalides = [ligne.line_start for ligne, valeur in zip(lignes, valeurs) if valeur is None]
    intervalles: list[dict[str, Any]] = []
    with localcontext() as contexte:
        contexte.prec = 4100
        for position, (avant, apres) in enumerate(zip(lignes, lignes[1:])):
            valeur_avant, valeur_apres = valeurs[position:position + 2]
            entree = {
                "ligne_precedente": avant.line_start,
                "ligne": apres.line_start,
                "temps_avant": avant.fields[indice],
                "temps_apres": apres.fields[indice],
                "delta_decimal": None,
                "nature": None,
            }
            if apres.line_start != avant.line_end + 1:
                entree["nature"] = "interruption_lecture"
            elif valeur_avant is None or valeur_apres is None:
                entree["nature"] = "temps_invalide"
            else:
                entree["delta_decimal"] = valeur_apres - valeur_avant
            intervalles.append(entree)
    return intervalles, invalides


def _marquer_changements_frequence(intervalles: list[dict[str, Any]], raster: Decimal,
                                   tolerance_normale: Decimal, regles: ReglesTemps) -> None:
    """Marquer une fréquence alternative seulement si elle forme une séquence durable."""
    position = 0
    while position < len(intervalles):
        delta = intervalles[position]["delta_decimal"]
        if delta is None or delta <= 0 or _proche(delta, raster, tolerance_normale):
            position += 1
            continue
        fin = position + 1
        groupe = [delta]
        while fin < len(intervalles):
            suivant = intervalles[fin]["delta_decimal"]
            if suivant is None or suivant <= 0:
                break
            centre = median(groupe)
            tolerance = _tolerance_relative(centre, regles.tolerance_relative_frequence)
            if _proche(suivant, centre, tolerance) and not _proche(suivant, raster, tolerance_normale):
                groupe.append(suivant)
                fin += 1
            else:
                break
        if len(groupe) >= regles.intervalles_min_changement_frequence:
            for indice in range(position, fin):
                intervalles[indice]["nature"] = "changement_frequence_probable"
        position = fin if fin > position else position + 1


def _classer_intervalles(intervalles: list[dict[str, Any]], raster: Decimal | None,
                         tolerance: Decimal | None, regles: ReglesTemps) -> int:
    """Qualifier les intervalles avec les mêmes règles pour le bilan et la vue.

    La fonction travaille uniquement sur les Δt déjà calculés. Elle retourne le
    nombre d'échantillons probablement manquants, sans en créer dans les données.
    """
    if raster is not None:
        _marquer_changements_frequence(intervalles, raster, tolerance, regles)

    manquants_probables = 0
    for item in intervalles:
        delta = item["delta_decimal"]
        if item["nature"] is not None:
            continue
        if delta == 0:
            item["nature"] = "temps_duplique"
        elif delta < 0:
            item["nature"] = "retour_arriere"
        elif raster is None:
            item["nature"] = "observe"
        elif _proche(delta, raster, tolerance):
            item["nature"] = "conforme_raster"
        else:
            multiple = int((delta / raster).to_integral_value())
            tolerance_multiple = tolerance * max(1, multiple)
            if multiple >= 2 and _proche(delta, raster * multiple, tolerance_multiple):
                item["nature"] = "trou_probable"
                item["echantillons_probablement_manquants"] = multiple - 1
                manquants_probables += multiple - 1
            else:
                item["nature"] = "jitter"
    return manquants_probables


def qualifier_intervalles(lecture: CsvReadResult, decimale: str,
                           raster: Decimal | None, tolerance: Decimal | None,
                           regles: ReglesTemps = REGLES_TEMPS) -> list[dict[str, Any]]:
    """Retourner les intervalles classés pour une vue, sans recalcul graphique.

    Le raster et la tolérance viennent du diagnostic déjà appliqué au fichier.
    Cette fonction permet au graphique de reprendre exactement les catégories
    du moteur : jitter, trou probable et changement de fréquence probable.
    """
    regles.valider()
    if raster is not None and tolerance is None:
        raise ValueError("Une tolérance est requise lorsqu'un raster est fourni.")
    diagnostic = lecture.diagnostic
    if diagnostic.time is None:
        return []
    indice = diagnostic.columns.index(diagnostic.time.column)
    intervalles, _ = _intervalles(lecture, indice, decimale)
    _classer_intervalles(intervalles, raster, tolerance, regles)
    return intervalles


def analyser_base_temps(lecture: CsvReadResult, decimale: str = ".",
                        pas_attendu: Decimal | None = None,
                        tolerance: Decimal | None = None,
                        unite: str | None = None,
                        regles: ReglesTemps = REGLES_TEMPS) -> dict[str, Any]:
    """Retourner un diagnostic complet ou partiel, avec lignes physiques.

    Un pas fourni par l'utilisateur est prioritaire. Sinon, le raster est estimé
    sur le groupe majoritaire des Δt positifs. « Probable » signifie que le
    fichier montre une forme compatible, pas qu'un échantillon perdu est prouvé.
    """
    regles.valider()
    if (pas_attendu is None) != (tolerance is None):
        raise ValueError("Le pas attendu et sa tolérance doivent être fournis ensemble.")
    if pas_attendu is not None and (pas_attendu <= 0 or tolerance < 0):
        raise ValueError("Le pas doit être positif et la tolérance positive ou nulle.")
    diagnostic = lecture.diagnostic
    if diagnostic.time is None:
        return {
            "statut": "insuffisant", "diagnostic_complet": False,
            "motif": "Première colonne temporelle indisponible.",
            "unite": unite, "raster": None, "comptes": {}, "anomalies": [],
        }
    indice = diagnostic.columns.index(diagnostic.time.column)
    intervalles, lignes_invalides = _intervalles(lecture, indice, decimale)
    positifs = [item["delta_decimal"] for item in intervalles
                if item["delta_decimal"] is not None and item["delta_decimal"] > 0]

    if pas_attendu is not None:
        raster = pas_attendu
        tolerance_effective = tolerance
        origine = "configure"
        motif_raster = None
    else:
        raster, tolerance_effective, motif_raster = _raster_estime(positifs, regles)
        origine = "estime" if raster is not None else "indisponible"

    manquants_probables = _classer_intervalles(
        intervalles, raster, tolerance_effective, regles,
    )

    comptes = Counter(item["nature"] for item in intervalles)
    anomalies: list[dict[str, Any]] = []
    for ligne in lignes_invalides:
        anomalies.append({
            "nature": "timestamp_invalide",
            "gravite": GRAVITE_ANOMALIE_TEMPORELLE["timestamp_invalide"], "ligne": ligne,
            "action": "Intervalle local non calculé ; donnée source conservée.",
        })
    for item in intervalles:
        nature = item["nature"]
        if nature not in GRAVITE_ANOMALIE_TEMPORELLE:
            continue
        anomalie = {
            "nature": nature, "gravite": GRAVITE_ANOMALIE_TEMPORELLE[nature],
            "ligne_precedente": item["ligne_precedente"], "ligne": item["ligne"],
            "temps_avant": item["temps_avant"], "temps_apres": item["temps_apres"],
            "delta": _texte(item["delta_decimal"]),
            "action": "Diagnostic uniquement ; aucune correction ni interpolation.",
        }
        if "echantillons_probablement_manquants" in item:
            anomalie["echantillons_probablement_manquants"] = item["echantillons_probablement_manquants"]
        anomalies.append(anomalie)

    partiel = bool(lignes_invalides or diagnostic.rejected_rows
                   or diagnostic.errors or not diagnostic.analysis_complete)
    statut = "partiel" if partiel else "complet"
    if raster is None:
        statut = "insuffisant" if not partiel else "partiel"
    calculables = sum(item["delta_decimal"] is not None for item in intervalles)
    return {
        "statut": statut,
        "diagnostic_complet": not partiel,
        "motif": motif_raster,
        "colonne": diagnostic.time.column,
        "unite": unite,
        "raster": {
            "valeur": _texte(raster), "origine": origine,
            "tolerance": _texte(tolerance_effective),
            "unite": unite or "unite_native_inconnue",
            "tolerance_relative_inference": str(regles.tolerance_relative_inference),
        },
        "intervalles_total": len(intervalles),
        "intervalles_calculables": calculables,
        "intervalles_non_calculables": len(intervalles) - calculables,
        "timestamps_invalides": len(lignes_invalides),
        "lignes_rejetees": len(diagnostic.rejected_rows),
        "echantillons_probablement_manquants": manquants_probables,
        "comptes": dict(comptes),
        "anomalies": anomalies[:regles.exemples_maximum],
        "anomalies_total": len(anomalies),
        "anomalies_tronquees": len(anomalies) > regles.exemples_maximum,
        "regles": {
            "intervalles_min_changement_frequence": regles.intervalles_min_changement_frequence,
            "tolerance_relative_frequence": str(regles.tolerance_relative_frequence),
            "exemples_maximum": regles.exemples_maximum,
        },
    }

