"""VISU PTBG — revue indépendante de la base de temps de plusieurs CSV.

Entrées : un fichier dont la première colonne est temporelle et, si connus,
un pas attendu et une tolérance dans son unité native. Sortie : un bilan par
source et un résumé de paquet. Ce module réutilise le lecteur conservateur et
ne modifie jamais les fichiers. Il ne synchronise pas les horloges.

Dépendances : bibliothèque standard Python et module local diagnostic_csv.
Les commentaires par parties documentent les décisions du requis 3006. La
revue constitue seulement une étape vers les requis 2103-2104 et 4100-4106.
"""
from __future__ import annotations

# === 1. Configuration explicite d'une source et dépendances locales ===
from dataclasses import asdict, dataclass
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from analyse_temps import analyser_base_temps
from diagnostic_csv import (
    MAX_FILE_BYTES, CsvDiagnosticError, CsvReadResult, _decimal, _temps_decimal, read_csv,
)


@dataclass(frozen=True)
class SourceTemps:
    """Décrire un fichier sans présumer l'origine ou l'unité de son horloge.

    colonne_temps reste disponible pour les appelants historiques, mais le
    lecteur exige qu'elle corresponde à la première colonne du CSV.
    pas_attendu et tolerance sont des nombres textuels dans l'unité native.
    Ils doivent être renseignés ensemble. Même une tolérance de zéro est un
    choix explicite, adapté uniquement si le profil de fichier le justifie.
    """

    fichier: str | Path
    colonne_temps: str | None = None
    unite: str | None = None
    pas_attendu: str | None = None
    tolerance: str | None = None
    separateur: str | None = None
    encodage: str | None = None
    decimale: str = "."
    taille_max_octets: int = MAX_FILE_BYTES


def _profil_numerique(source: SourceTemps) -> tuple[Decimal | None, Decimal | None]:
    """Valider les deux paramètres de pas, ou lever une erreur de configuration."""

    if (source.pas_attendu is None) != (source.tolerance is None):
        raise CsvDiagnosticError(
            "profil_temps_incomplet",
            "Le pas attendu et sa tolérance doivent être précisés ensemble.",
        )
    if source.pas_attendu is None:
        return None, None
    if not isinstance(source.pas_attendu, str) or not isinstance(source.tolerance, str):
        raise CsvDiagnosticError(
            "profil_temps_invalide", "Le pas et la tolérance doivent être des textes numériques explicites.",
        )
    pas = _decimal(source.pas_attendu, source.decimale)
    tolerance = _decimal(source.tolerance, source.decimale)
    if pas is None or pas <= 0 or tolerance is None or tolerance < 0:
        raise CsvDiagnosticError(
            "profil_temps_invalide",
            "Pas attendu strictement positif et tolérance positive ou nulle requis.",
        )
    return pas, tolerance


# === 2. Examiner un fichier sans interpoler ni masquer les lignes rejetées ===
def examiner_source(source: SourceTemps) -> dict[str, Any]:
    """Retourner le diagnostic d'une source et son évaluation de pas éventuelle.

    Une erreur de lecture ou de profil est propagée à examiner_paquet. Une
    syntaxe incomplète, une ligne rejetée ou un temps invalide empêche
    l'évaluation du pas attendu : les voisins d'un rejet ne sont pas considérés
    comme deux échantillons consécutifs prouvés.
    """

    pas, tolerance = _profil_numerique(source)
    lecture: CsvReadResult = read_csv(
        source.fichier, time_column=source.colonne_temps,
        delimiter=source.separateur, encoding=source.encodage,
        decimal=source.decimale, max_bytes=source.taille_max_octets,
    )
    diagnostic = lecture.diagnostic
    temps = diagnostic.time
    # Une heure civile est convertie en secondes depuis minuit pour le calcul.
    # Le profil numérique saisi doit donc employer des secondes également.
    if temps and temps.format_temps == "heure" and source.unite not in (None, "s"):
        raise CsvDiagnosticError("unite_heure", "Pour HH:MM:SS, saisir l'unité s ; pas et tolérance sont en secondes.")
    resultat: dict[str, Any] = {
        "fichier": str(source.fichier),
        "unite": source.unite,
        "pas_attendu": source.pas_attendu,
        "tolerance": source.tolerance,
        "diagnostic_csv": asdict(diagnostic),
        # Lot 2A : diagnostic détaillé même si la lecture n'est que partielle.
        # L'ancienne evaluation_pas reste présente pour les vues existantes.
        "analyse_temporelle": analyser_base_temps(
            lecture, source.decimale, pas, tolerance, (temps.unite_calcul or source.unite) if temps else source.unite,
        ),
        "evaluation_pas": {"effectuee": False, "motif": None},
    }
    evaluation = resultat["evaluation_pas"]
    if pas is None:
        evaluation["motif"] = "Aucun pas attendu et aucune tolérance renseignés."
        return resultat
    if diagnostic.rejected_rows or diagnostic.errors or not diagnostic.analysis_complete:
        evaluation["motif"] = "Lecture partielle ou lignes rejetées : évaluation du pas suspendue."
        return resultat
    if temps is None:  # Garde défensive : le lecteur affecte toujours la première colonne.
        evaluation["motif"] = "Première colonne temporelle indisponible."
        return resultat
    if not temps.numeric or len(lecture.rows) < 2:
        evaluation["motif"] = "Au moins deux temps numériques valides sont nécessaires."
        return resultat

    # === 3. Mesurer les intervalles dans chaque fichier, dans son unité native ===
    # Les temps bruts sont reparsés en Decimal pour conserver les petits pas et
    # grands entiers ; cette boucle ne réécrit aucune cellule du CSV.
    indice = diagnostic.columns.index(temps.column)
    valeurs = [_temps_decimal(ligne.fields[indice], source.decimale) for ligne in lecture.rows]
    exemples: list[dict[str, Any]] = []
    nombre_ecarts = 0
    nombre_intervalles = 0
    with localcontext() as contexte:
        contexte.prec = 4100
        for i, (avant, apres) in enumerate(zip(valeurs, valeurs[1:])):
            nombre_intervalles += 1
            delta = apres - avant
            if delta > 0 and abs(delta - pas) > tolerance:
                nombre_ecarts += 1
                if len(exemples) < 20:
                    exemples.append({
                        "ligne_precedente": lecture.rows[i].line_start,
                        "ligne": lecture.rows[i + 1].line_start,
                        "pas_observe": str(delta),
                        "temps_avant": lecture.rows[i].fields[indice],
                        "temps_apres": lecture.rows[i + 1].fields[indice],
                    })
    # Les pas nuls/négatifs figurent déjà dans diagnostic_csv.time.anomalies.
    # Écart au pas attendu signifie seulement « à examiner », jamais « donnée
    # perdue » : jitter et règles métier doivent être confirmés séparément.
    evaluation.update({
        "effectuee": True,
        "motif": None,
        "intervalles_examines": nombre_intervalles,
        "ecarts_positifs": nombre_ecarts,
        "exemples_ecarts_positifs": exemples,
        "exemples_tronques": nombre_ecarts > 20,
        "doublons_adjacents": temps.duplicate_count,
        "retours_arriere": temps.backward_count,
        "pas_conforme_sur_lignes_lues": nombre_ecarts == 0 and temps.strictly_increasing is True,
    })
    return resultat


# === 4. Construire un paquet où chaque horloge garde son propre diagnostic ===
def examiner_paquet(sources: list[SourceTemps]) -> dict[str, Any]:
    """Examiner chaque source même si une autre échoue et retourner un paquet.

    Ce premier niveau n'effectue aucune comparaison entre fichiers. Des
    timestamps au même nom peuvent avoir des origines ou unités différentes.
    L'absence de recalage est mentionnée dans la sortie afin d'éviter qu'un
    appelant assimile les positions des lignes entre deux CSV.
    """

    resultats: list[dict[str, Any]] = []
    for source in sources:
        try:
            resultats.append(examiner_source(source))
        except (OSError, CsvDiagnosticError) as exc:
            erreur = exc.to_dict() if isinstance(exc, CsvDiagnosticError) else {
                "code": "acces_fichier", "message": str(exc),
            }
            resultats.append({"fichier": str(source.fichier), "erreur": erreur})
    return {
        "nombre_sources": len(sources),
        "sources": resultats,
        "comparaison_entre_horloges": "non_effectuee",
        "raison": "Origines et unités communes non établies par la lecture des CSV.",
    }
