"""Inspection des intervalles temporels, indépendante de l'interface.

v0.7.0 — requis 2103, 4100, 4101, 4105, 4106 : couverture partielle.
Entrées : source et diagnostic déjà appliqué. Sortie : intervalles exacts,
lignes physiques et comptes complets, dans l'ordre du CSV. Aucune écriture.
Les différences sont calculées en Decimal avant toute conversion graphique.
"""
from __future__ import annotations

# === 1. Modèle conservant les textes bruts et les positions dans le fichier ===
from collections import Counter
from dataclasses import dataclass
from decimal import Decimal, localcontext
from pathlib import Path

from base_temps import SourceTemps, _profil_numerique
from diagnostic_csv import CsvDiagnosticError, _temps_decimal, read_csv

MAX_LIGNES_INSPECTION = 500_000  # Limite du prototype, pas un seuil métier validé.
LIBELLES = {
    "dans_tolerance": "Dans la tolérance",
    "observe": "Pas positif observé",
    "temps_duplique": "Temps dupliqué",
    "retour_arriere": "Retour arrière",
    "pas_hors_tolerance": "Pas hors tolérance",
    "temps_invalide": "Temps non numérique / absent",
    "interruption_lecture": "Ligne(s) rejetée(s) entre les mesures",
}
A_EXAMINER = frozenset(LIBELLES) - {"dans_tolerance", "observe"}


@dataclass(frozen=True)
class IntervalleTemps:
    """Un couple de lignes retenues ; delta reste None si le lien est incertain."""

    ligne_avant: int
    fin_avant: int
    ligne_apres: int
    fin_apres: int
    temps_avant: str
    temps_apres: str
    delta: Decimal | None
    ecart: Decimal | None
    nature: str


@dataclass
class InspectionTemps:
    """Bilan local ; un pas positif observé n'est pas une conformité métier."""

    fichier: str
    colonne: str
    unite: str | None
    pas: Decimal | None
    tolerance: Decimal | None
    comparaison_effectuee: bool
    motif: str | None
    sha256: str
    lignes_retenues: int
    lignes_rejetees: int
    temps_invalides: int
    lecture_complete: bool
    intervalles: list[IntervalleTemps]
    comptes: dict[str, int]
    distribution: dict[Decimal, int]

    def indices(self, anomalies_seules: bool = True) -> list[int]:
        """Sélection complète, sans plafond d'exemples ; la vue la pagine."""
        return [i for i, v in enumerate(self.intervalles)
                if not anomalies_seules or v.nature in A_EXAMINER]


# === 2. Vérifier fichier et profil avant de calculer un nouveau détail ===
def preparer_inspection(source: SourceTemps, resultat: dict) -> InspectionTemps:
    """Inspecter les voisins réels, sans franchir un rejet ni un temps invalide.

    Le bilan global du pas reste celui de base_temps : suspendu en cas de
    lecture partielle, rejet ou temps invalide. Les couples locaux exploitables
    restent consultables, explicitement comme observations. Aucun zéro ne
    remplace une valeur absente ; aucune perte ni synchronisation n'est déduite.
    """
    if "erreur" in resultat:
        raise CsvDiagnosticError("diagnostic_refuse", "Corriger le profil ou la lecture avant l'inspection.")
    if (Path(source.fichier).resolve() != Path(resultat["fichier"]).resolve()
            or any(resultat[cle] != getattr(source, cle)
                   for cle in ("unite", "pas_attendu", "tolerance"))):
        raise CsvDiagnosticError("profil_modifie", "Appliquer ce profil avec Analyser ce fichier.")
    pas, tolerance = _profil_numerique(source)
    lecture = read_csv(source.fichier, time_column=source.colonne_temps,
                      delimiter=source.separateur, encoding=source.encodage,
                      decimal=source.decimale, max_bytes=source.taille_max_octets)
    d = lecture.diagnostic
    if d.sha256 != resultat["diagnostic_csv"]["sha256"]:
        raise CsvDiagnosticError("fichier_modifie", "Le CSV a changé : cliquer sur Analyser ce fichier.")
    ancien_temps = resultat["diagnostic_csv"].get("time")
    if not d.time:
        raise CsvDiagnosticError("temps_absent", "La première colonne temporelle est indisponible.")
    if not ancien_temps or d.time.column != ancien_temps["column"]:
        raise CsvDiagnosticError("profil_modifie", "La colonne temporelle a changé : réanalyser le fichier.")
    if len(lecture.rows) > MAX_LIGNES_INSPECTION:
        raise CsvDiagnosticError("limite_inspection", f"Inspection limitée à {MAX_LIGNES_INSPECTION} lignes dans ce prototype ; diagnostic disponible.")
    indice = d.columns.index(d.time.column)
    evaluation = resultat["evaluation_pas"]
    compare = bool(evaluation["effectuee"])
    intervalles: list[IntervalleTemps] = []
    valeurs = [_temps_decimal(l.fields[indice], source.decimale) for l in lecture.rows]
    distribution: Counter = Counter()

    # === 3. Respecter l'ordre et les ruptures de la lecture, même en multiligne ===
    with localcontext() as contexte:
        contexte.prec = 4100  # Même enveloppe décimale que le lecteur.
        for i, (avant, apres) in enumerate(zip(lecture.rows, lecture.rows[1:])):
            a, b = valeurs[i:i + 2]
            delta = ecart = None
            if apres.line_start != avant.line_end + 1:
                nature = "interruption_lecture"
            elif a is None or b is None:
                nature = "temps_invalide"
            else:
                delta = b - a
                distribution[delta] += 1
                ecart = delta - pas if compare else None
                if delta == 0:
                    nature = "temps_duplique"
                elif delta < 0:
                    nature = "retour_arriere"
                elif compare:
                    nature = "pas_hors_tolerance" if abs(ecart) > tolerance else "dans_tolerance"
                else:
                    nature = "observe"
            intervalles.append(IntervalleTemps(
                avant.line_start, avant.line_end, apres.line_start, apres.line_end,
                avant.fields[indice], apres.fields[indice], delta, ecart, nature))
    return InspectionTemps(
        str(source.fichier), d.time.column, d.time.unite_calcul or source.unite, pas, tolerance,
        compare, evaluation.get("motif"), d.sha256, len(lecture.rows),
        len(d.rejected_rows), sum(v is None for v in valeurs), d.analysis_complete,
        intervalles, dict(Counter(v.nature for v in intervalles)), dict(distribution))


# === 4. Texte pédagogique commun à la vue et à ses vérifications ===
def resumer_inspection(inspection: InspectionTemps) -> str:
    """Distinguer observations, comparaison renseignée et bilan suspendu."""
    unite = inspection.unite or "unité inconnue"
    n = inspection.comptes
    lignes = [f"{inspection.lignes_retenues} mesures retenues | {len(inspection.intervalles)} couples de mesures | {unite}",
              f"Doublons : {n.get('temps_duplique', 0)} | retours arrière : {n.get('retour_arriere', 0)} | "
              f"intervalles non calculables : {sum(v.delta is None for v in inspection.intervalles)}"]
    if inspection.comparaison_effectuee:
        lignes.append(f"Pas attendu : {inspection.pas} ± {inspection.tolerance} | "
                      f"pas positifs hors tolérance : {n.get('pas_hors_tolerance', 0)}")
    else:
        lignes.append("Comparaison au pas attendu non effectuée. " + (inspection.motif or ""))
    if inspection.lignes_rejetees or inspection.temps_invalides or not inspection.lecture_complete:
        lignes.append(f"Rejets CSV : {inspection.lignes_rejetees} | temps invalides : {inspection.temps_invalides} | "
                      f"lecture complète : {'oui' if inspection.lecture_complete else 'non'}. Observations locales uniquement.")
    principaux = sorted(inspection.distribution.items(), key=lambda v: (-v[1], v[0]))[:6]
    if principaux:
        valeurs = " ; ".join(f"{d} ({n} fois)" for d, n in principaux)
        suffixe = " — 6 pas les plus fréquents" if len(inspection.distribution) > 6 else ""
        lignes.append(f"Δt observés : {valeurs}{suffixe}")
    return "\n".join(lignes)
