# -----------------------------------------------------------------------------
# VISU PTBG — V00.07.03 — signal et bords des données manquantes
# Requis concernés : 2103, 2200, 2201, 3003, 3006 ; périmètre partiel détaillé dans docs.
# Historique : séparation lecture, dessin et intégration dans la fenêtre.
# -----------------------------------------------------------------------------
"""Préparer les échantillons d'une colonne pour un affichage graphique.

Bibliothèque standard uniquement. Le lecteur conserve les textes d'origine ;
les flottants produits ici servent exclusivement au dessin. La préparation
refuse un fichier changé depuis son diagnostic et les temps non représentables.
Les cellules de signal invalides restent absentes, sans remplacement par zéro.
"""
from __future__ import annotations

# === 1. Structure de sortie et conversion destinée au tracé uniquement ===
import math
from dataclasses import dataclass, field
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any

from analyse_temps import qualifier_intervalles
from base_temps import SourceTemps, _profil_numerique
from diagnostic_csv import CsvDiagnosticError, _decimal, _temps_decimal, read_csv

MAX_POINTS_GRAPHIQUE = 500_000  # Limite de prototype, à qualifier avec les fichiers métier.


@dataclass
class SignalPrepare:
    """Échantillons retenus dans l'ordre du fichier, avec provenance et absences."""
    fichier: str
    colonne: str
    colonne_temps: str
    unite_temps: str | None
    temps: list[float]
    valeurs: list[float]
    lignes: list[int]
    valeurs_absentes: int
    lignes_rejetees: int
    lecture_complete: bool
    sha256: str
    indices_vides: list[int] = field(default_factory=list)
    indices_invalides: list[int] = field(default_factory=list)
    indices_coupures: list[int] = field(default_factory=list)
    indices_croix: list[int] = field(default_factory=list)
    relier_points: bool = False
    temps_intervalles: list[float] = field(default_factory=list)
    deltas_temps: list[float] = field(default_factory=list)
    natures_intervalles: list[str] = field(default_factory=list)
    raster_temps: float | None = None
    tolerance_temps: float | None = None
    origine_raster: str = "indisponible"
    format_temps: str = "compteur"
    type_signal: str = "Float"
    temps_bruts: list[str] = field(default_factory=list)
    valeurs_brutes: list[str] = field(default_factory=list)


def _flottant(nombre: Decimal | None) -> float | None:
    """Convertir un nombre fini ; refuser débordement et sous-débordement à zéro."""
    if nombre is None:
        return None
    valeur = float(nombre)
    if not math.isfinite(valeur) or (valeur == 0 and nombre != 0):
        return None
    return valeur


def _bords_des_manques(valeurs: list[float], indices_vides: list[int]) -> list[int]:
    """Marquer les mesures qui encadrent un bloc contenant une cellule vide.

    Une valeur invalide reste non traçable, mais ne prouve pas une perte.
    Un bloc composé uniquement de valeurs invalides ne produit donc pas de
    croix. Aux extrémités du fichier, on marque seulement le bord disponible.
    """
    vides = set(indices_vides)
    bords: set[int] = set()
    i = 0
    while i < len(valeurs):
        if math.isfinite(valeurs[i]):
            i += 1
            continue
        debut = i
        contient_un_vide = False
        while i < len(valeurs) and not math.isfinite(valeurs[i]):
            contient_un_vide = contient_un_vide or i in vides
            i += 1
        if contient_un_vide:
            if debut > 0:
                bords.add(debut - 1)
            if i < len(valeurs):
                bords.add(i)
    return sorted(bords)


def _coupures_temporelles(lignes, temps_exacts, pas, tolerance) -> list[int]:
    """Indices avant lesquels il faut interrompre le trait, sans ajouter de croix.

    Une ligne rejetée, un doublon, un retour ou un pas hors tolérance empêche
    la liaison graphique. Ces constats ne sont pas des preuves de perte.
    Examiner tous les couples : les exemples du moniteur sont volontairement
    limités et ne doivent jamais servir à décider des coupures de la courbe.
    """
    coupures = []
    with localcontext() as contexte:
        contexte.prec = 4100  # Même précision que le diagnostic temporel.
        for i in range(1, len(lignes)):
            if lignes[i].line_start != lignes[i - 1].line_end + 1:
                coupures.append(i)
                continue
            delta = temps_exacts[i] - temps_exacts[i - 1]
            if delta <= 0 or (pas is not None and abs(delta - pas) > tolerance):
                coupures.append(i)
    return coupures


def _serie_temporelle(lignes, temps, intervalles, raster, tolerance):
    """Préparer pour Matplotlib les Δt déjà qualifiés par le moteur temporel.

    Les flottants retournés servent uniquement au dessin. Un intervalle absent
    de la série signifie que deux lignes retenues n'étaient pas voisines dans
    le CSV : aucun Δt n'est alors inventé entre elles.
    """
    positions, deltas, natures = [], [], []
    correspondance: dict[float, Decimal] = {}
    temps_par_ligne = {ligne.line_start: temps[i] for i, ligne in enumerate(lignes)}
    noms_vue = {
        "conforme_raster": "conforme",
        "observe": "observe",
        "jitter": "jitter",
        "trou_probable": "trou_probable",
        "changement_frequence_probable": "changement_frequence_probable",
        "temps_duplique": "temps_duplique",
        "retour_arriere": "retour_arriere",
    }

    def pour_graphique(nombre):
        """Refuser notamment deux Δt distincts devenant un faux pas constant."""
        valeur = _flottant(nombre)
        if valeur is None or (valeur in correspondance and correspondance[valeur] != nombre):
            raise CsvDiagnosticError(
                "precision_delta_graphique",
                "La précision des intervalles dépasse ce tracé ; consulter le tableau exact de la base de temps.",
            )
        correspondance[valeur] = nombre
        return valeur

    with localcontext() as contexte:
        contexte.prec = 4100
        if raster is not None:
            for nombre in (raster, tolerance, raster - tolerance, raster + tolerance):
                pour_graphique(nombre)
        for intervalle in intervalles:
            delta_exact = intervalle["delta_decimal"]
            nature = noms_vue.get(intervalle["nature"])
            if delta_exact is None or nature is None:
                continue
            delta = pour_graphique(delta_exact)
            positions.append(temps_par_ligne[intervalle["ligne"]])
            deltas.append(delta)
            natures.append(nature)
    if correspondance and not math.isfinite(max(correspondance) - min(correspondance)):
        raise CsvDiagnosticError("precision_delta_graphique",
                                 "L'étendue des intervalles dépasse ce tracé ; consulter le tableau exact.")
    return positions, deltas, natures


# === 2. Relire le même fichier et contrôler sa concordance avec le diagnostic ===
def preparer_signal(source: SourceTemps, resultat: dict[str, Any], colonne: str,
                    type_signal: str = "Auto", *, autoriser_vide: bool = False) -> SignalPrepare:
    """Lire une colonne numérique sans trier, resynchroniser ou interpoler.

    Des temps distincts qui deviennent le même flottant bloquent le tracé pour
    éviter de créer un faux doublon. Une cellule de signal absente/texte/non
    finie devient NaN dans la vue seulement. Les lignes rejetées du lecteur
    restent comptées dans la légende ; leur contenu reste dans le diagnostic.
    """
    if "erreur" in resultat:
        raise CsvDiagnosticError("diagnostic_refuse", "Corriger la lecture ou le profil avant d'afficher un signal.")
    if (Path(source.fichier).resolve() != Path(resultat["fichier"]).resolve()
            or any(resultat[cle] != getattr(source, cle)
                   for cle in ("unite", "pas_attendu", "tolerance"))):
        raise CsvDiagnosticError("profil_modifie", "Appliquer ce profil avec Analyser ce fichier avant de tracer.")
    pas, tolerance = _profil_numerique(source)
    lecture = read_csv(source.fichier, time_column=source.colonne_temps,
                      delimiter=source.separateur, encoding=source.encodage,
                      decimal=source.decimale, max_bytes=source.taille_max_octets)
    diagnostic = lecture.diagnostic
    if diagnostic.sha256 != resultat["diagnostic_csv"]["sha256"]:
        raise CsvDiagnosticError("fichier_modifie", "Le CSV a changé : cliquer sur Analyser ce fichier avant de tracer.")
    if not diagnostic.time or not diagnostic.time.numeric:
        raise CsvDiagnosticError("temps_non_tracable", "Choisir une colonne de temps numérique valide pour ce fichier.")
    ancien_temps = resultat["diagnostic_csv"].get("time")
    if not ancien_temps or ancien_temps["column"] != diagnostic.time.column:
        raise CsvDiagnosticError("profil_modifie", "La colonne temporelle a changé : réanalyser le fichier.")
    if colonne not in diagnostic.columns or colonne == diagnostic.time.column:
        raise CsvDiagnosticError("signal_absent", "Choisir une colonne de signal existante, différente de la colonne de temps.")
    if len(lecture.rows) > MAX_POINTS_GRAPHIQUE:
        raise CsvDiagnosticError("limite_graphique", f"Le tracé est limité à {MAX_POINTS_GRAPHIQUE} lignes dans ce prototype ; le diagnostic reste disponible.")

    # === 3. Garder tous les timestamps et n'afficher que les valeurs représentables ===
    it = diagnostic.columns.index(diagnostic.time.column)
    iy = diagnostic.columns.index(colonne)
    if type_signal not in ("Auto", "Bool", "Float"):
        raise ValueError("Le type du signal doit être Auto, Bool ou Float.")
    # 0/1 peut aussi être une mesure analogique : seul le choix explicite Bool
    # l'interprète comme binaire. true/false porte déjà cette information.
    if type_signal == "Auto":
        type_signal = "Bool" if diagnostic.inferred_types[colonne] == "booléen" else "Float"
    temps: list[float] = []
    temps_exacts: list[Decimal] = []
    valeurs: list[float] = []
    correspondance: dict[float, Decimal] = {}
    absentes = 0
    indices_vides: list[int] = []
    indices_invalides: list[int] = []
    for ligne in lecture.rows:
        exact = _temps_decimal(ligne.fields[it], source.decimale)
        x = _flottant(exact)
        if x is None or (x in correspondance and correspondance[x] != exact):
            raise CsvDiagnosticError("precision_temps_graphique", "Ces temps ne peuvent pas être représentés fidèlement par le moteur graphique ; diagnostic conservé.")
        correspondance[x] = exact
        brut = ligne.fields[iy].strip()
        if type_signal == "Bool":
            # Pas d'assimilation de ACTIVE/FAILED à un état : leur codage n'est
            # pas défini dans les requis. Une valeur illégale reste manquante.
            binaire = {"true": 1.0, "false": 0.0}.get(brut.casefold())
            nombre = _decimal(brut, source.decimale)
            y = binaire if binaire is not None else float(nombre) if nombre in (0, 1) else None
        else:
            y = _flottant(_decimal(brut, source.decimale))
        if y is None:
            (indices_vides if not ligne.fields[iy].strip() else indices_invalides).append(len(temps))
        temps.append(x)
        temps_exacts.append(exact)
        valeurs.append(y if y is not None else math.nan)
        absentes += y is None
    if absentes == len(valeurs) and not autoriser_vide:
        raise CsvDiagnosticError("signal_non_numerique", "Cette colonne ne contient aucune valeur numérique affichable.")
    if not math.isfinite(max(temps) - min(temps)):
        raise CsvDiagnosticError("precision_temps_graphique", "L'étendue temporelle dépasse la capacité du tracé.")

    # === 4. Séparer les coupures de prudence et les croix de données manquantes ===
    # Les NaN coupent déjà le trait. Les indices ci-dessous ajoutent les ruptures
    # de temps/lecture ; seuls les champs vides du signal autorisent les croix.
    coupures = _coupures_temporelles(lecture.rows, temps_exacts, pas, tolerance)
    croix = _bords_des_manques(valeurs, indices_vides)
    relier = pas is not None or diagnostic.time.regular_step is not None
    analyse = resultat["analyse_temporelle"]
    raster_brut = analyse.get("raster") or {}
    # analyser_base_temps sérialise toujours ses Decimal avec un point, même
    # quand le CSV d'origine emploie une virgule décimale.
    raster = _decimal(raster_brut.get("valeur") or "", ".")
    tolerance_raster = _decimal(raster_brut.get("tolerance") or "", ".")
    if raster is None:
        tolerance_raster = None
    intervalles_classes = qualifier_intervalles(
        lecture, source.decimale, raster, tolerance_raster,
    )
    positions_delta, deltas, natures = _serie_temporelle(
        lecture.rows, temps, intervalles_classes, raster,
        tolerance_raster or Decimal(0),
    )
    return SignalPrepare(str(Path(source.fichier)), colonne, diagnostic.time.column,
                         diagnostic.time.unite_calcul or source.unite, temps, valeurs, [r.line_start for r in lecture.rows],
                         absentes, len(diagnostic.rejected_rows), diagnostic.analysis_complete,
                         diagnostic.sha256, indices_vides, indices_invalides,
                         indices_coupures=coupures, indices_croix=croix,
                         relier_points=relier,
                         temps_intervalles=positions_delta, deltas_temps=deltas,
                         natures_intervalles=natures,
                         raster_temps=_flottant(raster),
                         tolerance_temps=_flottant(tolerance_raster),
                         origine_raster=raster_brut.get("origine", "indisponible"),
                         format_temps=diagnostic.time.format_temps,
                         type_signal=type_signal,
                         temps_bruts=[r.fields[it] for r in lecture.rows],
                         valeurs_brutes=[r.fields[iy] for r in lecture.rows])
