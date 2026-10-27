"""Préparer le Time Base Monitor sans dépendre de tkinter.

Le module transforme le diagnostic d'un seul CSV en état, message et repères
graphiques. Les positions sont calculées dans la base de temps native du fichier.
Aucun alignement entre sources, aucune correction et aucune perte ne sont déduits.
"""
from __future__ import annotations

# === 1. Conversion prudente d'un timestamp en position relative ===
from decimal import Decimal, localcontext
from typing import Any

from base_temps import SourceTemps
from diagnostic_csv import _temps_decimal as _decimal


def _borner_marqueurs(modele: dict[str, Any]) -> dict[str, Any]:
    """Limiter les objets graphiques tout en conservant le compte complet."""
    nombre = modele.get("nombre_marqueurs", len(modele["marqueurs"]))
    modele["nombre_marqueurs"] = nombre
    modele["marqueurs_tronques"] = nombre > min(len(modele["marqueurs"]), 50)
    modele["marqueurs"] = modele["marqueurs"][:50]
    if modele.get("avertissements_csv") and modele["masquage_autorise"]:
        modele["masquage_autorise"] = False
        modele["niveau"] = "avertissement"
        modele["message"] += " Avertissements CSV à consulter."
    return modele


def _position(valeur: str | None, debut: str | None, fin: str | None,
              decimale: str) -> float | None:
    """Retourner une position de 0 à 1, ou None si l'axe n'est pas calculable."""
    nombre = _decimal(valeur or "", decimale)
    origine = _decimal(debut or "", decimale)
    borne = _decimal(fin or "", decimale)
    if nombre is None or origine is None or borne is None or borne <= origine:
        return None
    with localcontext() as contexte:
        contexte.prec = 4100
        position = (nombre - origine) / (borne - origine)
    return float(position) if Decimal(0) <= position <= Decimal(1) else None


# === 2. État synthétique et repères des anomalies connues ===
def construire_moniteur(source: SourceTemps, resultat: dict[str, Any]) -> dict[str, Any]:
    """Construire le modèle graphique d'un fichier avec une règle de masquage.

    `masquage_autorise` n'est vrai que si la lecture temporelle est complète,
    strictement croissante et régulière selon le contrôle disponible. Un pas
    positif variable sans profil explicite reste à qualifier par l'utilisateur.
    """
    modele: dict[str, Any] = {
        "etat": "indisponible", "niveau": "erreur", "message": "Diagnostic indisponible.",
        "masquage_autorise": False, "debut": None, "fin": None,
        "unite": source.unite, "repere_pas": None, "marqueurs": [],
    }
    if "erreur" in resultat:
        modele["message"] = resultat["erreur"]["message"]
        return _borner_marqueurs(modele)
    diagnostic = resultat["diagnostic_csv"]
    modele["avertissements_csv"] = bool(diagnostic["warnings"] or diagnostic["errors"])
    temps = diagnostic["time"]
    if temps and temps.get("unite_calcul"):
        modele["unite"] = temps["unite_calcul"]
    if temps is None:
        modele["message"] = "La première colonne temporelle est indisponible."
        return _borner_marqueurs(modele)
    debut = temps.get("minimum_raw") or temps["start_raw"]
    fin = temps.get("maximum_raw") or temps["end_raw"]
    modele.update({"debut": debut, "fin": fin,
                   "repere_pas": source.pas_attendu or temps["regular_step"]})
    if not temps["numeric"] or diagnostic["data_rows"] < 2:
        modele["message"] = "La colonne de temps contient une valeur invalide ou pas assez de données."
        return _borner_marqueurs(modele)
    if diagnostic["rejected_rows"] or diagnostic["errors"] or not diagnostic["analysis_complete"]:
        modele["message"] = "Lecture partielle : la stabilité temporelle ne peut pas être conclue."
        return _borner_marqueurs(modele)

    # Doublons et retours viennent du diagnostic brut ; ils existent même sans
    # période normale fournie par l'utilisateur.
    evaluation = resultat["evaluation_pas"]
    modele["nombre_marqueurs"] = len(temps["anomalies"]) + (
        evaluation["ecarts_positifs"] if evaluation["effectuee"] else 0)
    for anomalie in temps["anomalies"][:50]:
        modele["marqueurs"].append({
            "type": anomalie["code"], "ligne": anomalie["line"],
            "temps": anomalie["after_raw"],
            "position": _position(anomalie["after_raw"], debut, fin, source.decimale),
        })

    # Les écarts positifs ne sont qualifiés qu'après saisie du pas et de sa
    # tolérance. Ils restent des écarts à examiner, pas des pertes prouvées.
    if evaluation["effectuee"]:
        for anomalie in evaluation["exemples_ecarts_positifs"][:max(0, 50 - len(modele["marqueurs"]))]:
            modele["marqueurs"].append({
                "type": "pas_hors_tolerance", "ligne": anomalie["ligne"],
                "temps": anomalie["temps_apres"], "pas": anomalie["pas_observe"],
                "temps_avant": anomalie["temps_avant"],
                "position": _position(anomalie["temps_apres"], debut, fin, source.decimale),
            })
        nombre_ecarts = (evaluation["doublons_adjacents"] + evaluation["retours_arriere"] +
                         evaluation["ecarts_positifs"])
        if nombre_ecarts:
            modele.update({"etat": "anomalie", "niveau": "avertissement",
                           "message": f"{nombre_ecarts} anomalie(s) temporelle(s) à examiner."})
        else:
            modele.update({"etat": "regulier", "niveau": "ok", "masquage_autorise": True,
                           "message": "Base de temps régulière selon le pas et la tolérance saisis."})
        return _borner_marqueurs(modele)

    if temps["duplicate_count"] or temps["backward_count"]:
        nombre = (temps["duplicate_count"] or 0) + (temps["backward_count"] or 0)
        modele.update({"etat": "anomalie", "niveau": "avertissement",
                       "message": f"{nombre} doublon(s) ou retour(s) arrière détecté(s)."})
    elif temps["regular_step"] is not None:
        modele.update({"etat": "regulier_observe", "niveau": "ok", "masquage_autorise": True,
                       "message": "Période observée régulière ; unité et règle métier à confirmer."})
    else:
        modele.update({"etat": "a_configurer", "niveau": "avertissement",
                       "message": "Plusieurs pas positifs observés : renseigner le pas normal et sa tolérance."})
    return _borner_marqueurs(modele)
