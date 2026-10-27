"""VISU PTBG — lecture et diagnostic CSV sans interface.

Rôle : lire les enregistrements, signaler les anomalies et permettre une
comparaison scénario/report lorsque leurs temps correspondent ligne à ligne.
Entrées : chemins CSV et options explicites d'encodage, séparateur et temps.
Sorties : objets de diagnostic et lignes conservées ; JSON sur la sortie
standard si ce module est lancé directement en ligne de commande.
Dépendances : bibliothèque standard uniquement ; cible de développement
Python 3.11, interpréteur 64 bits. Aucun besoin de Spyder à l'exécution.

Invariants : ni tri, ni recalage, ni remplacement des valeurs manquantes.
Les fichiers source ne sont jamais écrits. Les rejets restent consultables
avec leur texte décodé. Les octets et lignes physiques sont lus en flux sous
une limite de taille ; les enregistrements restent conservés par read_csv.

Requis : commentaires par blocs pour REQ_COMMON_KH_3006, séparation du
traitement pour 3003. Ces repères ne constituent pas une validation globale.
Voir docs/SUIVI_DOCUMENTATION.md pour le périmètre et les preuves de revue.
"""
from __future__ import annotations

# === 1. Dépendances et limites du prototype ===
# Les constantes définissent des garde-fous, pas des unités ou seuils métier.
import argparse
import codecs
import csv
import hashlib
import io
import itertools
import json
import math
import re
import sys
from dataclasses import asdict, dataclass, field
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

from version_visu import VERSION_VISU

VERSION = VERSION_VISU
MAX_FILE_BYTES = 50 * 1024 * 1024
NUMBER = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?\Z")
NONFINITE = {"nan", "+nan", "-nan", "inf", "+inf", "-inf", "infinity", "+infinity", "-infinity"}


# === 2. Erreurs contrôlées et objets échangés avec les lanceurs ===
# Les numéros de lignes physiques commencent à 1. Un enregistrement CSV peut
# couvrir plusieurs lignes si un champ entre guillemets contient des retours.
class CsvDiagnosticError(ValueError):
    """Refus explicite de lecture, à afficher par la CLI ou la future IHM."""

    def __init__(self, code: str, message: str, **details: Any):
        """Associer un code stable au message lisible et aux détails de refus."""
        super().__init__(message)
        self.code = code
        self.details = details

    def to_dict(self) -> dict[str, Any]:
        """Retourner code, message et détails pour les journaux des lanceurs."""
        return {"code": self.code, "message": str(self), "details": self.details}


@dataclass
class RejectedRow:
    """Enregistrement écarté des calculs, mais conservé avec son motif.

    raw_text contient le texte décodé et ses fins de lignes. fields vaut None
    lorsque la syntaxe empêche de déterminer les champs de manière fiable.
    """
    line_start: int
    line_end: int
    code: str
    reason: str
    raw_text: str
    fields: list[str] | None


@dataclass
class CsvRow:
    """Enregistrement de largeur valide, sans validation métier des valeurs.

    fields conserve les chaînes obtenues après interprétation de la syntaxe
    CSV ; raw_text conserve la représentation décodée, guillemets compris.
    """
    line_start: int
    line_end: int
    fields: list[str]
    raw_text: str


@dataclass
class TimeDiagnostic:
    """Constats sur les temps des seules lignes de structure valide.

    None signifie « non calculable », jamais zéro par défaut. duplicate_count
    compte les doublons adjacents ; repeated_value_count inclut les répétitions
    non adjacentes. Les valeurs résumées n'impliquent aucune unité confirmée.
    """
    column: str
    numeric: bool
    start: int | float | str | None
    end: int | float | str | None
    strictly_increasing: bool | None
    duplicate_count: int | None
    backward_count: int | None
    step_values: list[int | float | str]
    regular_step: int | float | str | None
    start_raw: str | None = None
    end_raw: str | None = None
    invalid_lines: list[int] = field(default_factory=list)
    repeated_value_count: int | None = None
    distinct_step_count: int = 0
    step_values_truncated: bool = False
    anomalies: list[dict[str, Any]] = field(default_factory=list)
    minimum_raw: str | None = None
    maximum_raw: str | None = None
    partial: bool = False
    local_interval_count: int = 0
    uncalculable_interval_count: int = 0
    format_temps: str = "compteur"
    unite_calcul: str | None = None


@dataclass
class CsvDiagnostic:
    """Bilan traçable d'un fichier, et non certificat de conformité.

    analysis_complete indique seulement que la lecture a atteint sa fin.
    data_rows inclut les lignes de bonne largeur même si une valeur est invalide.
    sha256 porte sur les octets source ; original_columns garde l'en-tête avant
    retrait des espaces extérieurs. warnings et errors doivent être consultés.
    """
    path: str
    encoding: str
    delimiter: str
    columns: list[str]
    data_rows: int
    blank_rows: int
    malformed_rows: list[int]
    empty_cells_by_column: dict[str, int]
    inferred_types: dict[str, str]
    constant_columns: list[str]
    time: TimeDiagnostic | None
    warnings: list[str]
    rejected_rows: list[RejectedRow]
    errors: list[str]
    status: str
    analysis_complete: bool
    physical_lines: int
    original_columns: list[str]
    time_candidates: list[str]
    nonfinite_cells_by_column: dict[str, int]
    sha256: str
    size_bytes: int
    version: str = VERSION
    time_scope: str = "Lignes de structure valide uniquement ; aucune correction des données."


@dataclass
class CsvReadResult:
    """Réunir les lignes acceptées structurellement et le bilan avec les rejets."""
    diagnostic: CsvDiagnostic
    rows: list[CsvRow]


# === 3. Interprétation numérique sans modification du contenu d'origine ===
def _decimal(value: str, decimal: str = ".") -> Decimal | None:
    """Interpréter value en Decimal fini, ou retourner None sans lever d'erreur.

    decimal indique le point ou la virgule ; aucun séparateur de milliers n'est
    supposé. Les bornes de longueur/exposant limitent le coût des calculs. La
    chaîne d'entrée reste conservée ailleurs, y compris si elle est refusée ici.
    """
    token = value.strip()
    if decimal == ",":
        if "." in token:
            return None
        token = token.replace(",", ".")
    if len(token) > 1000 or not NUMBER.fullmatch(token):
        return None
    try:
        result = Decimal(token)
        # Borne de ressources explicite pour les nombres pathologiques.
        if not result.is_finite() or abs(result.as_tuple().exponent) > 1000:
            return None
        return result
    except (InvalidOperation, ValueError):
        return None


def _display_number(value: Decimal) -> int | float | str:
    """Préparer un Decimal fini pour l'affichage JSON, sans changer les calculs.

    Retour : entier si approprié, flottant d'affichage sinon, ou texte si le
    flottant déborde/s'annule. Un flottant d'affichage peut être arrondi ; les
    valeurs brutes restent la référence. Aucun NaN/infini n'est émis ici.
    """
    if value == value.to_integral_value() and value.adjusted() <= 300:
        return int(value)
    number = float(value)
    if not math.isfinite(number) or (number == 0 and value != 0):
        return str(value)
    return number


# === 4. Lecture bornée des octets et choix de l'encodage ===
def _read_text(path: Path, encoding: str | None, max_bytes: int) -> tuple[str, str, int]:
    """Contrôler path en flux et retourner encodage, SHA-256 et taille.

    encoding=None autorise UTF-8 et les BOM UTF-8/UTF-16, pas une détection
    universelle. max_bytes est une limite de ressources configurable.
    Erreurs : OSError pour l'accès ; CsvDiagnosticError pour taille, encodage
    ou caractère NUL. Aucun octet illisible n'est remplacé silencieusement.
    """
    if max_bytes < 1:
        raise CsvDiagnosticError("taille_limite_invalide", "La limite de taille doit être positive.")
    if path.stat().st_size > max_bytes:
        raise CsvDiagnosticError("fichier_trop_grand", f"Fichier au-delà de la limite de {max_bytes} octets.")
    # Le contrôle incrémental ne conserve ni l'intégralité des octets ni le
    # texte décodé. Le décodage strict valide aussi une séquence coupée au EOF.
    with path.open("rb") as stream:
        first = stream.read(4)
        stream.seek(0)
        if encoding is None:
            if first.startswith(codecs.BOM_UTF8):
                encoding = "utf-8-sig"
            elif first.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
                encoding = "utf-16"
            else:
                encoding = "utf-8"
        try:
            decoder = codecs.getincrementaldecoder(encoding)(errors="strict")
            digest = hashlib.sha256()
            taille = 0
            while chunk := stream.read(min(1024 * 1024, max_bytes + 1 - taille)):
                taille += len(chunk)
                if taille > max_bytes:
                    raise CsvDiagnosticError("fichier_trop_grand", f"Fichier au-delà de la limite de {max_bytes} octets.")
                digest.update(chunk)
                if "\x00" in decoder.decode(chunk):
                    raise CsvDiagnosticError("caractere_nul", "Caractère NUL détecté : vérifier le format ou l'encodage.")
            if "\x00" in decoder.decode(b"", final=True):
                raise CsvDiagnosticError("caractere_nul", "Caractère NUL détecté : vérifier le format ou l'encodage.")
        except (UnicodeError, LookupError) as exc:
            raise CsvDiagnosticError(
                "encodage_invalide", "Décodage impossible. Préciser l'encodage réel ; aucun remplacement de caractères effectué.",
                encoding=encoding,
            ) from exc
    return encoding, digest.hexdigest(), taille


class _LignesCapturees:
    """Capturer seulement les lignes physiques de l'enregistrement CSV courant."""

    def __init__(self, lignes):
        self.lignes = iter(lignes)
        self.nombre = 0
        self.courantes: list[str] = []

    def __iter__(self):
        return self

    def __next__(self):
        ligne = next(self.lignes)
        self.nombre += 1
        self.courantes.append(ligne)
        return ligne


class _LectureBornee(io.RawIOBase):
    """Compter et hacher les octets effectivement transmis au lecteur CSV.

    Ce petit adaptateur s'intercale entre le fichier binaire et le décodeur
    standard Python. Il empêche un fichier qui grandit pendant la lecture de
    dépasser la limite. Le texte et les fins de lignes ne sont pas modifiés.
    """

    def __init__(self, fichier, limite: int):
        super().__init__()
        self.fichier = fichier
        self.limite = limite
        self.nombre_octets = 0
        self.empreinte = hashlib.sha256()

    def readable(self):
        return True

    def readinto(self, tampon):
        # Un seul octet au-delà de la limite suffit pour constater le refus.
        taille = min(len(tampon), self.limite - self.nombre_octets + 1)
        bloc = self.fichier.read(taille)
        self.nombre_octets += len(bloc)
        if self.nombre_octets > self.limite:
            raise CsvDiagnosticError("fichier_trop_grand",
                                     f"Fichier au-delà de la limite de {self.limite} octets.")
        self.empreinte.update(bloc)
        tampon[:len(bloc)] = bloc
        return len(bloc)


def _lignes_sans_nul(texte):
    """Contrôler aussi le texte lu pendant le parsing, après le premier contrôle."""
    for ligne in texte:
        if "\x00" in ligne:
            raise CsvDiagnosticError("caractere_nul",
                                     "Caractère NUL détecté : vérifier le format ou l'encodage.")
        yield ligne


@contextmanager
def _ouvrir_flux_csv(path: Path, encoding: str, limite: int, empreinte_attendue: str):
    """Ouvrir le texte avec les garde-fous actifs pendant toute l'interprétation.

    Les trois lectures doivent porter sur les mêmes octets : contrôle initial,
    parsing, contrôle final. Comparer seulement avant/après manquerait un CSV
    modifié temporairement puis rétabli. Une erreur de décodage devient un
    refus CSV connu, afin que l'import des autres fichiers puisse continuer.
    """
    with path.open("rb") as fichier:
        lecture = _LectureBornee(fichier, limite)
        try:
            with io.TextIOWrapper(io.BufferedReader(lecture), encoding=encoding,
                                  errors="strict", newline="") as texte:
                yield _lignes_sans_nul(texte)
        except UnicodeError as exc:
            raise CsvDiagnosticError(
                "encodage_invalide", "Décodage impossible pendant la lecture ; réanalyser le CSV.",
                encoding=encoding,
            ) from exc
        if lecture.empreinte.hexdigest() != empreinte_attendue:
            raise CsvDiagnosticError("fichier_modifie",
                                     "Le CSV a changé pendant sa lecture ; recommencer l'analyse.")


# === 5. Choix du séparateur et description indicative des colonnes ===
def _delimiter(lines: list[str], explicit: str | None) -> str:
    """Choisir un caractère séparateur à partir de l'en-tête ou du choix explicit.

    Plusieurs candidats lèvent CsvDiagnosticError plutôt que de deviner. Sans
    candidat, la virgule permet le cas d'une seule colonne. L'en-tête multiligne
    n'est pas couvert par cette détection sur la première ligne non vide.
    """
    if explicit is not None:
        if len(explicit) != 1 or explicit in "\r\n\x00\"":
            raise CsvDiagnosticError("separateur_invalide", "Le séparateur doit être un caractère autorisé unique.")
        return explicit
    # L'en-tête seul évite que des lignes dégradées imposent un faux dialecte.
    first = next((line for line in lines if line.strip()), "")
    candidates = []
    for candidate in (",", ";", "\t", "|"):
        try:
            row = next(csv.reader([first], delimiter=candidate, strict=True))
            if len(row) > 1:
                candidates.append(candidate)
        except (csv.Error, StopIteration):
            continue
    if len(candidates) > 1:
        raise CsvDiagnosticError("separateur_ambigu", "Plusieurs séparateurs possibles : préciser le séparateur.", candidates=candidates)
    return candidates[0] if candidates else ","  # fichier à une colonne possible


def _column_type(values: list[str], decimal: str) -> str:
    """Décrire values : vide, booléen, numérique, mixte ou texte, sans conversion.

    Seuls true/false sont reconnus comme booléens ici. Une colonne 0/1 reste
    numérique tant qu'un schéma métier ne permet pas d'en confirmer le sens.
    Ce résultat n'est donc pas encore le typage métier Bool/Float du requis 5202.
    """
    present = [v.strip() for v in values if v.strip()]
    if not present:
        return "vide"
    if {v.casefold() for v in present} <= {"true", "false"}:
        return "booléen"
    numeric = sum(_decimal(v, decimal) is not None for v in present)
    if numeric == len(present):
        return "numérique"
    if numeric or any(v.casefold() in NONFINITE for v in present):
        return "mixte"
    return "texte"


# === 6. Diagnostic de la base de temps, sans synchronisation ni correction ===
def _temps_decimal(value: str, decimal: str = ".") -> Decimal | None:
    """Lire un compteur ou HH:MM:SS[.fraction] en secondes exactes (REQ 2306).

    Jusqu'à neuf chiffres de fraction : pas de conversion par float/datetime,
    donc les nanosecondes restent distinctes. Aucune date ni journée suivante
    n'est inventée : minuit après 23 h reste un retour à examiner.
    Cette fonction concerne seulement le temps, jamais les valeurs de signal.
    """
    if ":" not in value:
        return _decimal(value, decimal)
    match = re.fullmatch(r"([0-9]{2}):([0-9]{2}):([0-9]{2})(?:\.([0-9]{1,9}))?", value.strip())
    if match is None:
        return None
    heure, minute, seconde = map(int, match.group(1, 2, 3))
    if heure > 23 or minute > 59 or seconde > 59:
        return None
    return Decimal(heure * 3600 + minute * 60 + seconde) + Decimal("0." + (match[4] or "0"))


def _time_diagnostic(column: str, rows: list[CsvRow], column_index: int, decimal: str,
                     rejected_rows: list[RejectedRow], complete: bool) -> TimeDiagnostic:
    """Examiner la colonne column_index de rows et retourner un TimeDiagnostic.

    column nomme cette colonne ; decimal fixe son interprétation numérique.
    Une valeur temporelle invalide bloque le bilan global, mais n'empêche pas
    de mesurer un couple localement exploitable de part et d'autre. Une ligne
    rejetée interrompt la continuité ; aucun intervalle ne la franchit.
    Les écarts restent dans l'unité source non confirmée. Ni dates absolues,
    ni pertes d'échantillons prouvées, ni phasage entre fichiers ne sont déduits.
    """
    # 6a. Conserver les bornes brutes et repérer les temps non interprétables.
    values = [row.fields[column_index] for row in rows]
    formats = {"heure" if ":" in v else "compteur" for v in values
               if _temps_decimal(v, decimal) is not None}
    if len(formats) > 1:
        raise CsvDiagnosticError("formats_temps_melanges",
                                 "La première colonne mélange des heures et des compteurs ; aucune unité commune supposée.")
    numbers = [_temps_decimal(value, decimal) for value in values]
    invalid = [row.line_start for row, number in zip(rows, numbers) if number is None]
    result = TimeDiagnostic(column, bool(rows) and not invalid, None, None, None, None, None, [], None)
    result.format_temps = "heure" if "heure" in formats else "compteur"
    result.unite_calcul = "s" if result.format_temps == "heure" else None
    result.start_raw = values[0] if values else None
    result.end_raw = values[-1] if values else None
    result.invalid_lines = invalid
    result.partial = bool(invalid or rejected_rows or not complete)
    # Aucun couple n'est calculable avant la recherche des voisins valides.
    # Cela reste vrai si toutes les cellules temporelles sont invalides.
    result.uncalculable_interval_count = max(0, len(rows) - 1)
    if not rows:
        return result
    valid_indices = [i for i, value in enumerate(numbers) if value is not None]
    if not valid_indices:
        return result
    numeric = [numbers[i] for i in valid_indices]
    # Les extrémités du fichier ne sont pas forcément les bornes de l'axe
    # lorsqu'un temps revient en arrière. Conserver aussi les extrema bruts.
    result.minimum_raw = values[min(valid_indices, key=lambda i: numbers[i])]
    result.maximum_raw = values[max(valid_indices, key=lambda i: numbers[i])]
    if numbers[0] is not None:
        result.start = _display_number(numbers[0])
    if numbers[-1] is not None:
        result.end = _display_number(numbers[-1])
    result.repeated_value_count = len(numeric) - len(set(numeric))
    if len(rows) < 2:
        return result
    # 6b. Mesurer uniquement des enregistrements voisins valides et contigus.
    # Les mêmes intervalles globaux qu'en v0.6.0 subsistent sur un CSV sain.
    paires = [(i, a, b) for i, (a, b) in enumerate(zip(numbers, numbers[1:]))
              if a is not None and b is not None
              and rows[i + 1].line_start == rows[i].line_end + 1]
    result.local_interval_count = len(paires)
    result.uncalculable_interval_count = len(rows) - 1 - len(paires)
    if not paires:
        return result
    with localcontext() as context:
        context.prec = 4100
        steps = [b - a for _, a, b in paires]
    unique = sorted(set(steps))
    result.step_values = [_display_number(step) for step in unique[:20]]
    result.distinct_step_count = len(unique)
    result.step_values_truncated = len(unique) > 20
    result.strictly_increasing = (False if any(step <= 0 for step in steps)
                                  else None if result.partial else True)
    result.duplicate_count = sum(step == 0 for step in steps)
    result.backward_count = sum(step < 0 for step in steps)
    result.regular_step = (_display_number(unique[0])
                           if not result.partial and len(unique) == 1 and unique[0] > 0 else None)
    # 6c. Rattacher chaque doublon adjacent/retour arrière aux lignes physiques.
    # Les pas positifs variables sont résumés, sans conclure à une perte réelle.
    result.anomalies = [
        {"previous_line": rows[i].line_start, "line": rows[i+1].line_start,
         "code": "temps_duplique" if step == 0 else "retour_arriere",
         "before_raw": values[i], "after_raw": values[i+1]}
        for (i, _, _), step in zip(paires, steps) if step <= 0
    ]
    return result


# === 7. Point d'entrée de lecture : structure, provenance et diagnostic ===
def read_csv(file_path: str | Path, *, delimiter: str | None = None,
             encoding: str | None = None, time_column: str | None = None,
             decimal: str = ".", max_bytes: int = MAX_FILE_BYTES) -> CsvReadResult:
    """Lire un CSV et retourner CsvReadResult, sans écrire dans le fichier.

    Paramètres : file_path désigne le CSV ; delimiter et encoding imposent
    éventuellement son séparateur et son encodage. Selon le requis 2304, la
    première colonne est toujours la base de temps. time_column est conservé
    pour les anciens appelants : s'il est renseigné, il doit désigner cette
    première colonne. decimal vaut '.' ou ','.
    max_bytes borne la lecture, à 50 MiB par défaut (limite du prototype).

    Résultat : lignes de structure valide dans rows ; rejets, avertissements
    et erreurs dans diagnostic. Les valeurs des cellules restent textuelles.
    Erreurs levées : OSError pour l'accès ; CsvDiagnosticError pour les refus
    de format ou d'options. Une syntaxe cassée en cours de données produit un
    résultat partiel et conserve la fin du fichier comme bloc non interprété.
    """
    # 7a. Décoder et préparer le parseur sans normaliser les fins de lignes.
    if decimal not in (".", ","):
        raise CsvDiagnosticError("decimale_invalide", "La marque décimale doit être '.' ou ','.")
    path = Path(file_path)
    selected_encoding, digest, size = _read_text(path, encoding, max_bytes)
    rows: list[CsvRow] = []
    rejects: list[RejectedRow] = []
    original_columns: list[str] | None = None
    columns: list[str] = []
    errors = []
    complete = True
    # 7b. Lire une ligne physique à la fois. Un enregistrement CSV peut en
    # utiliser plusieurs ; seules ses lignes sont gardées durant son parsing.
    with _ouvrir_flux_csv(path, selected_encoding, max_bytes, digest) as flux:
        debut = []
        for ligne in flux:
            debut.append(ligne)
            if ligne.strip():
                break
        if not any(ligne.strip() for ligne in debut):
            raise CsvDiagnosticError("fichier_vide", "Fichier vide ou ne contenant que des lignes vides.")
        separator = _delimiter([debut[-1]], delimiter)
        lignes = _LignesCapturees(itertools.chain(debut, flux))
        reader = csv.reader(lignes, delimiter=separator, strict=True)
        while True:
            first_line = reader.line_num + 1
            lignes.courantes.clear()
            try:
                values = next(reader)
            except StopIteration:
                break
            except csv.Error as exc:
                # Même si l'erreur survient avant EOF, conserver la suite comme
                # un bloc brut ; une reprise arbitraire fausserait les lignes.
                fin_brute = list(lignes.courantes)
                fin_brute.extend(lignes)
                if original_columns is None:
                    raise CsvDiagnosticError("entete_csv_invalide", f"En-tête CSV illisible : {exc}.",
                                             line_start=first_line, raw_text="".join(fin_brute)) from exc
                rejects.append(RejectedRow(first_line, lignes.nombre, "syntaxe_csv",
                                           f"{exc} ; suite conservée sans tentative de resynchronisation.",
                                           "".join(fin_brute), None))
                errors.append(f"Syntaxe CSV invalide à partir de la ligne {first_line}. Analyse partielle.")
                complete = False
                break
            last_line = reader.line_num
            raw_text = "".join(lignes.courantes)
            if not values or all(not value.strip() for value in values):
                rejects.append(RejectedRow(first_line, last_line, "ligne_vide", "Enregistrement sans valeur.", raw_text, values))
                continue
            # 7c. Conserver l'en-tête original et les numéros physiques.
            if original_columns is None:
                original_columns = values
                columns = [value.strip() for value in values]
                if any(not name for name in columns):
                    raise CsvDiagnosticError("entete_incomplete", "Nom de colonne vide.", line_start=first_line, raw_text=raw_text)
                if len(columns) != len(set(columns)):
                    raise CsvDiagnosticError("colonnes_dupliquees", "Noms de colonnes dupliqués après retrait des espaces extérieurs.", line_start=first_line, raw_text=raw_text, columns=columns)
                if all(_decimal(value, decimal) is not None for value in columns):
                    raise CsvDiagnosticError("entete_absente", "Première ligne entièrement numérique : en-tête explicite attendu.", line_start=first_line, raw_text=raw_text)
                continue
            # 7d. Une ligne isolément incorrecte est rejetée, les autres suivent.
            if len(values) != len(columns):
                rejects.append(RejectedRow(first_line, last_line, "nombre_colonnes", f"{len(values)} champs reçus ; {len(columns)} attendus.", raw_text, values))
            elif [value.strip() for value in values] == columns:
                rejects.append(RejectedRow(first_line, last_line, "entete_repetee", "En-tête répété dans les données.", raw_text, values))
            else:
                rows.append(CsvRow(first_line, last_line, values, raw_text))
        physical_lines = lignes.nombre
    # Le fichier a pu changer entre le contrôle et le parsing : ne jamais
    # associer le diagnostic à une empreinte d'un autre contenu.
    if _read_text(path, selected_encoding, max_bytes)[1] != digest:
        raise CsvDiagnosticError("fichier_modifie", "Le CSV a changé pendant sa lecture ; recommencer l'analyse.")
    if original_columns is None:
        raise CsvDiagnosticError("entete_absente", "Aucun en-tête exploitable.")
    # 7e. Décrire uniquement les lignes de structure valide. Les rejets sont
    # exclus des statistiques, mais présents dans le résultat pour la revue.
    by_column = {column: [row.fields[i] for row in rows] for i, column in enumerate(columns)}
    empty = {col: sum(not v.strip() for v in values) for col, values in by_column.items()}
    types = {col: _column_type(values, decimal) for col, values in by_column.items()}
    nonfinite = {col: sum(v.strip().casefold() in NONFINITE for v in values) for col, values in by_column.items()}
    warnings = []
    # 7f. Le requis 2304 fixe la position, indépendamment du nom de l'en-tête.
    # time_column ne permet pas de contourner cette règle : il sert uniquement
    # à détecter un ancien profil devenu incohérent avec le fichier.
    selected = columns[0]
    if time_column is not None and time_column != selected:
        raise CsvDiagnosticError(
            "premiere_colonne_temps",
            f"La base de temps est imposée par la première colonne : {selected}.",
            premiere_colonne=selected, colonne_demandee=time_column,
        )
    time = _time_diagnostic(selected, rows, 0, decimal, rejects, complete)
    # 7g. Transformer les constats en messages, sans modifier les données.
    if rejects:
        warnings.append(f"{len(rejects)} enregistrement(s) ou bloc(s) non retenu(s), conservés dans rejected_rows.")
    if not rows:
        warnings.append("Aucune ligne de données de structure valide.")
    if time is not None:
        if time.invalid_lines:
            warnings.append("Temps absent, invalide ou non fini : bilan global suspendu ; seuls les intervalles locaux fiables sont décrits.")
        elif time.partial:
            warnings.append("Lecture partielle ou lignes rejetées : bilan temporel global suspendu ; intervalles locaux seulement.")
        elif len(rows) < 2:
            warnings.append("Au moins deux temps valides sont nécessaires pour évaluer la progression.")
        elif not time.strictly_increasing:
            warnings.append(f"La colonne temporelle '{time.column}' n'est pas strictement croissante.")
        if time.distinct_step_count > 1:
            warnings.append("Plusieurs pas temporels observés ; aucune régularisation appliquée.")
    if any(empty.values()):
        warnings.append("Certaines cellules sont vides ; elles ne sont pas remplacées par zéro.")
    if any(nonfinite.values()):
        warnings.append("Valeurs NaN ou infinies présentes, conservées sous forme de texte brut.")
    if any(value == "mixte" for value in types.values()):
        warnings.append("Certaines colonnes mélangent des types : vérifier le schéma attendu.")
    # 7h. Assembler le bilan avec son périmètre, sa version et l'empreinte source.
    diagnostic = CsvDiagnostic(
        path=str(path), encoding=selected_encoding, delimiter=separator, columns=columns,
        data_rows=len(rows), blank_rows=sum(r.code == "ligne_vide" for r in rejects),
        malformed_rows=[r.line_start for r in rejects if r.code != "ligne_vide"],
        empty_cells_by_column=empty, inferred_types=types,
        constant_columns=[col for col, values in by_column.items() if values and len(set(values)) == 1],
        time=time, warnings=warnings, rejected_rows=rejects, errors=errors,
        status="error" if errors else "warning" if warnings else "ok",
        analysis_complete=complete, physical_lines=physical_lines, original_columns=original_columns,
        # Champ conservé pour compatibilité des journaux : il contient désormais
        # l'unique colonne imposée par sa position, pas une liste de suggestions.
        time_candidates=[selected], nonfinite_cells_by_column=nonfinite, sha256=digest, size_bytes=size,
    )
    return CsvReadResult(diagnostic, rows)


def analyse_csv(file_path: str | Path, **options: Any) -> CsvDiagnostic:
    """Retourner seulement le bilan ; paramètres et erreurs identiques à read_csv."""
    return read_csv(file_path, **options).diagnostic


# === 8. Comparaison limitée de deux fichiers, pas de recalage multi-sources ===
def compare_csv(reference_path: str | Path, report_path: str | Path, **options: Any) -> dict[str, Any]:
    """Comparaison textuelle positionnelle, autorisée uniquement sur des temps identiques.

    Ce n'est pas une synchronisation. Refus explicite si des rejets, temps invalides,
    vides, non croissants ou des tailles différentes rendent le résultat trompeur.

    Paramètres : chemins du scénario de référence et de son report ; options
    de read_csv appliquées aux deux. Retour : dictionnaire contenant la décision,
    ses motifs et, si autorisé, le nombre d'écarts textuels par colonne commune.
    Les cellules '1' et '1.0' diffèrent textuellement, même si les temps sont
    comparés numériquement au préalable. OSError/CsvDiagnosticError sont propagées.
    """
    # 8a. Vérifier que les lignes et les colonnes correspondent avant de compter.
    reference, report = read_csv(reference_path, **options), read_csv(report_path, **options)
    a, b = reference.diagnostic, report.diagnostic
    shared = [col for col in a.columns if col in b.columns]
    missing = [col for col in a.columns if col not in b.columns]
    reasons = []
    if a.rejected_rows or b.rejected_rows or a.errors or b.errors:
        reasons.append("Des lignes sont rejetées ou l'analyse est partielle.")
    if not a.data_rows or not b.data_rows:
        reasons.append("Un fichier ne contient aucune donnée exploitable.")
    if a.data_rows != b.data_rows:
        reasons.append("Les nombres de lignes de données diffèrent.")
    if missing:
        reasons.append("Des colonnes du scénario sont absentes du report.")
    # 8b. Exiger une chronologie commune, valide et strictement croissante.
    if a.time is None or b.time is None or a.time.column != b.time.column:
        reasons.append("Les premières colonnes temporelles ne correspondent pas.")
    elif a.time.strictly_increasing is not True or b.time.strictly_increasing is not True:
        reasons.append("Les deux séries doivent avoir au moins deux temps valides strictement croissants.")
    elif a.data_rows == b.data_rows:
        ia, ib = a.columns.index(a.time.column), b.columns.index(b.time.column)
        decimal = options.get("decimal", ".")
        if a.time.format_temps != b.time.format_temps:
            reasons.append("Formats temporels différents : aucune origine commune supposée.")
        if any(_temps_decimal(x.fields[ia], decimal) != _temps_decimal(y.fields[ib], decimal) for x, y in zip(reference.rows, report.rows)):
            reasons.append("Les temps ne correspondent pas ligne à ligne. Aucun recalage tenté.")
    # 8c. None signifie « comparaison non effectuée », pas « aucun écart ».
    mismatches = None
    if not reasons:
        mismatches = {
            col: sum(x.fields[a.columns.index(col)] != y.fields[b.columns.index(col)] for x, y in zip(reference.rows, report.rows))
            for col in shared
        }
    return {
        "reference": str(reference_path), "report": str(report_path),
        "same_row_count": a.data_rows == b.data_rows,
        "reference_rows": a.data_rows, "report_rows": b.data_rows,
        "shared_columns": shared, "report_extra_columns": [col for col in b.columns if col not in a.columns],
        "missing_reference_columns": missing, "comparison_performed": not reasons,
        "refusal_reasons": reasons, "shared_column_mismatches": mismatches,
    }


# === 9. Adaptateur de ligne de commande, indépendant d'une future IHM ===
def main(argv: list[str] | None = None) -> int:
    """Lire argv (ou les arguments système), afficher un JSON et retourner un code.

    0 : traitement terminé, éventuellement avec avertissements à lire.
    2 : refus de lecture, analyse partielle ou comparaison refusée.
    Les erreurs d'accès/format sont rendues lisibles ; argparse gère les options
    invalides via SystemExit. Ce point d'entrée n'est pas le futur MAIN.py IHM.
    """
    # 9a. Traduire les options CLI en options de lecture identiques pour les CSV.
    parser = argparse.ArgumentParser(description="Diagnostic CSV sans modification des données.")
    parser.add_argument("scenario")
    parser.add_argument("report", nargs="?")
    parser.add_argument("--delimiter")
    parser.add_argument("--encoding")
    parser.add_argument("--time-column")
    parser.add_argument("--decimal", choices=(".", ","), default=".")
    args = parser.parse_args(argv)
    options = {"delimiter": args.delimiter, "encoding": args.encoding, "time_column": args.time_column, "decimal": args.decimal}
    result: dict[str, Any] = {"version": VERSION}
    status = 0
    # 9b. Intercepter les refus connus et conserver un diagnostic par fichier.
    for label, filename in (("scenario", args.scenario), ("report", args.report)):
        if filename is None:
            continue
        try:
            diagnosis = analyse_csv(filename, **options)
            result[label] = asdict(diagnosis)
            if diagnosis.errors:
                status = 2
        except (OSError, CsvDiagnosticError) as exc:
            result[label] = {"error": exc.to_dict() if isinstance(exc, CsvDiagnosticError) else {"code":"acces_fichier", "message":str(exc)}}
            status = 2
    # 9c. Comparer seulement après les lectures, puis sérialiser un JSON strict.
    if args.report and status == 0:
        try:
            result["comparison"] = compare_csv(args.scenario, args.report, **options)
            if not result["comparison"]["comparison_performed"]:
                status = 2
        except (OSError, CsvDiagnosticError) as exc:
            result["comparison"] = {"comparison_performed": False, "error": str(exc)}
            status = 2
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))
    return status


if __name__ == "__main__":
    # L'import du module expose les fonctions sans lancer une analyse.
    sys.exit(main())
