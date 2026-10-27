"""Lecture contrôlée d'un fichier CSV PTBG.

Requis couverts (section 2.3 « File' Features ») :

- REQ_COMMON_KH_2300 : format préféré csv (autre extension = avertissement) ;
- REQ_COMMON_KH_2301 : séparateur virgule (« ; » ou tabulation = erreur) ;
- REQ_COMMON_KH_2302 : texte UTF-8 strict (BOM UTF-8 toléré et signalé) ;
- REQ_COMMON_KH_2303 : pas de métadonnées (lignes « # » ou préambule signalés) ;
- REQ_COMMON_KH_2304 : première colonne = base de temps (quel que soit son nom) ;
- REQ_COMMON_KH_2308 : première ligne = en-têtes de colonnes ;
- REQ_COMMON_KH_2309 : en-têtes = noms des variables PLC (vides/doublons signalés) ;
- REQ_COMMON_KH_2310 : taille maximale (paramètre, voir config.py) ;
- REQ_COMMON_KH_4105 : lecture par blocs, annulable, sans blocage de l'IHM.

Principe de robustesse : une anomalie de CONTENU (ligne mal formée, cellule
vide, texte inattendu) produit un constat et la lecture continue ; seule une
anomalie de FORMAT rendant le fichier illisible lève ``CsvReadError``. Les
valeurs ne sont jamais inventées : une cellule vide reste vide (NaN + masque).

Chaque cellule est classée selon sa nature (vide, nombre, booléen texte,
texte libre). Le choix du type Bool/Float est fait ensuite par
``signals.auto_type`` et peut être modifié par l'utilisateur sans relire le
fichier.
"""
from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from ptbg.core.diagnostics import Issue, Severity

# Nature d'une cellule (tableau int8 ``kinds`` de chaque colonne).
KIND_EMPTY, KIND_NUMBER, KIND_BOOL, KIND_TEXT = 0, 1, 2, 3

CHUNK_ROWS = 20_000        # lignes converties en numpy par bloc
SNIFF_ROWS = 50            # lignes examinées pour détecter un préambule
MAX_DETAILED_ISSUES = 20   # au-delà, les lignes rejetées sont résumées

ProgressCallback = Callable[[float], None]


class CsvReadError(Exception):
    """Le fichier ne peut pas être lu ; ``issues`` explique pourquoi."""

    def __init__(self, issues: list[Issue]) -> None:
        super().__init__("; ".join(issue.message for issue in issues))
        self.issues = issues


class ReadCancelled(Exception):
    """L'utilisateur a annulé la lecture (bouton Annuler de la barre d'état)."""


@dataclass
class RawColumn:
    """Contenu brut converti d'une colonne de variable (hors base de temps)."""
    name: str
    index: int                      # position dans le CSV (0 = base de temps)
    values: np.ndarray              # float64 : nombre, ou 1/0 pour true/false, NaN sinon
    kinds: np.ndarray               # int8 : KIND_* de chaque cellule
    codes: np.ndarray | None        # int32 : code du texte libre (-1 si pas texte)
    categories: list[str]           # textes libres distincts, dans l'ordre d'apparition
    binary_numbers: bool            # tous les nombres valent 0 ou 1
    has_zero: bool
    has_one: bool

    def count(self, kind: int) -> int:
        return int(np.count_nonzero(self.kinds == kind))


@dataclass
class CsvTable:
    """Résultat de lecture d'un fichier."""
    path: Path
    size_bytes: int
    sha256: str
    header: list[str]               # noms normalisés (uniques, non vides)
    time_raw: list[str]             # textes bruts de la 1re colonne (REQ 2304)
    line_numbers: np.ndarray        # int64 : ligne physique de chaque échantillon
    columns: list[RawColumn]        # variables, dans l'ordre du CSV
    issues: list[Issue] = field(default_factory=list)

    @property
    def time_name(self) -> str:
        return self.header[0]

    @property
    def n_samples(self) -> int:
        return len(self.time_raw)


class _ColumnBuilder:
    """Accumule les blocs de cellules texte d'une colonne et les convertit."""

    def __init__(self, name: str, index: int) -> None:
        self.name = name
        self.index = index
        self.value_chunks: list[np.ndarray] = []
        self.kind_chunks: list[np.ndarray] = []
        self.code_chunks: list[np.ndarray | None] = []
        self.categories: dict[str, int] = {}
        self.binary = True
        self.has_zero = False
        self.has_one = False

    def add(self, cells) -> None:
        """Convertit un bloc. Chemin rapide numpy, sinon cellule par cellule."""
        codes = None
        try:
            values = np.array(cells, dtype=np.float64)
            if not np.isfinite(values).all():   # « nan », « inf » écrits en clair
                raise ValueError
            kinds = np.full(len(values), KIND_NUMBER, dtype=np.int8)
        except ValueError:
            values, kinds, codes = self._convert_slowly(cells)
        numbers = values[kinds == KIND_NUMBER]
        if numbers.size:
            is_zero, is_one = numbers == 0.0, numbers == 1.0
            self.binary = self.binary and bool(np.all(is_zero | is_one))
            self.has_zero = self.has_zero or bool(is_zero.any())
            self.has_one = self.has_one or bool(is_one.any())
        self.value_chunks.append(values)
        self.kind_chunks.append(kinds)
        self.code_chunks.append(codes)

    def _convert_slowly(self, cells):
        """Classe chaque cellule : vide, booléen (true/false), nombre, texte."""
        values, kinds, codes = [], [], []
        has_text = False
        for cell in cells:
            text = cell.strip()
            value, kind, code = math.nan, KIND_EMPTY, -1
            if text:
                lowered = text.lower()
                if lowered == "true":
                    value, kind = 1.0, KIND_BOOL
                elif lowered == "false":
                    value, kind = 0.0, KIND_BOOL
                else:
                    try:
                        number = float(text)
                    except ValueError:
                        number = math.nan
                    if math.isfinite(number):
                        value, kind = number, KIND_NUMBER
                    else:
                        kind, has_text = KIND_TEXT, True
                        code = self.categories.setdefault(text, len(self.categories))
            values.append(value)
            kinds.append(kind)
            codes.append(code)
        return (np.array(values, dtype=np.float64), np.array(kinds, dtype=np.int8),
                np.array(codes, dtype=np.int32) if has_text else None)

    def finish(self) -> RawColumn:
        """Assemble les blocs convertis en une colonne complète."""
        values = _concat(self.value_chunks, np.float64)
        kinds = _concat(self.kind_chunks, np.int8)
        codes = None
        if any(chunk is not None for chunk in self.code_chunks):
            codes = np.concatenate([
                chunk if chunk is not None else np.full(len(v), -1, dtype=np.int32)
                for chunk, v in zip(self.code_chunks, self.value_chunks)])
        return RawColumn(self.name, self.index, values, kinds, codes,
                         list(self.categories), self.binary, self.has_zero, self.has_one)


def _concat(chunks: list[np.ndarray], dtype) -> np.ndarray:
    return np.concatenate(chunks) if chunks else np.empty(0, dtype=dtype)


def file_sha256(path: Path, cancel=None) -> str:
    """Empreinte SHA-256 calculée par blocs (fichiers volumineux, REQ 6005)."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            if cancel is not None and cancel.is_set():
                raise ReadCancelled()
            digest.update(block)
    return digest.hexdigest()


def _check_file(path: Path, max_size_mb: float) -> tuple[int, list[Issue]]:
    """Contrôles préalables : accès, taille, extension."""
    issues = []
    try:
        size = path.stat().st_size
    except OSError as exc:
        raise CsvReadError([Issue(Severity.ERROR, f"Fichier inaccessible : {exc}")])
    if size == 0:
        raise CsvReadError([Issue(Severity.ERROR, "Fichier vide.")])
    if size > max_size_mb * 1024 * 1024:
        raise CsvReadError([Issue(
            Severity.ERROR,
            f"Taille {size / 1048576:.1f} Mo supérieure au maximum de {max_size_mb:g} Mo "
            "(modifiable dans Outils > Préférences).", requirement="REQ_COMMON_KH_2310")])
    if path.suffix.lower() != ".csv":
        issues.append(Issue(Severity.WARNING,
                            f"Extension « {path.suffix or 'aucune'} » : le format préféré est .csv.",
                            requirement="REQ_COMMON_KH_2300"))
    with path.open("rb") as handle:
        if handle.read(3) == b"\xef\xbb\xbf":
            issues.append(Issue(Severity.INFO, "Marque d'ordre UTF-8 (BOM) présente : tolérée.",
                                requirement="REQ_COMMON_KH_2302"))
    return size, issues


def _find_header(first_rows: list[tuple[int, list[str]]]) -> tuple[int, list[str], list[Issue]]:
    """Repère la ligne d'en-tête parmi les premières lignes lues.

    Le nombre de champs le plus fréquent est celui du tableau de données. Les
    lignes qui précèdent et ont MOINS de champs (ex. « Titre,essai 3 ») ou
    commencent par « # » sont des métadonnées interdites par
    REQ_COMMON_KH_2303 : elles sont signalées et ignorées. Renvoie la
    position de l'en-tête dans ``first_rows`` et l'en-tête débarrassé
    d'éventuelles virgules finales sans nom.
    """
    issues = []
    counts = [len(row) for _, row in first_rows if row and not row[0].lstrip().startswith("#")]
    if not counts:
        raise CsvReadError([Issue(Severity.ERROR, "Aucune ligne exploitable dans le fichier.")])
    dominant = max(set(counts), key=counts.count)
    for position, (line, row) in enumerate(first_rows):
        if not row:
            continue
        if row[0].lstrip().startswith("#") or len(row) < dominant:
            issues.append(Issue(Severity.WARNING,
                                "Ligne de métadonnées avant l'en-tête ignorée : « "
                                + ",".join(row)[:60] + " ».", line, "REQ_COMMON_KH_2303"))
            continue
        header = list(row)
        while len(header) > dominant and not header[-1].strip():
            header.pop()   # « a,b,c, » : la virgule finale ne crée pas de colonne
        return position, header, issues
    raise CsvReadError([Issue(Severity.ERROR, "En-tête introuvable.", requirement="REQ_COMMON_KH_2308")])


def _check_separator(path: Path) -> None:
    """REQ_COMMON_KH_2301 : les lignes doivent être séparées par des virgules.

    Le contrôle porte sur le TEXTE BRUT des 20 premières lignes utiles : avec
    « ; » et une décimale à virgule (« 0;1,5;0 »), un découpage à la virgule
    produirait de faux champs. Un séparateur est retenu s'il domine la virgule
    sur la majorité des lignes (une ligne de préambule isolée ne compte pas).
    """
    lines = []
    with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
        for line in handle:
            if line.strip() and not line.lstrip().startswith("#"):
                lines.append(line)
                if len(lines) >= 20:
                    break
    if not lines:
        return
    for separator, label in ((";", "point-virgule"), ("\t", "tabulation"), ("|", "barre verticale")):
        if sum(line.count(separator) > line.count(",") for line in lines) * 2 > len(lines):
            raise CsvReadError([Issue(Severity.ERROR,
                                      f"Séparateur « {label} » détecté : le séparateur doit être la virgule.",
                                      1, "REQ_COMMON_KH_2301")])
    if not any("," in line for line in lines):
        raise CsvReadError([Issue(Severity.ERROR,
                                  "Une seule colonne : la 1re colonne est la base de temps et aucune "
                                  "variable n'est présente.", 1, "REQ_COMMON_KH_2304")])


def normalize_header(raw_names: list[str], line: int) -> tuple[list[str], list[Issue]]:
    """Rend les noms de colonnes non vides et uniques (REQ 2308, 2309)."""
    issues, names, seen = [], [], set()
    numeric_names = 0
    for position, raw in enumerate(raw_names):
        name = raw.strip()
        if not name:
            name = f"Colonne_{position + 1}"
            issues.append(Issue(Severity.WARNING, f"En-tête vide en colonne {position + 1}, "
                                f"renommé « {name} ».", line, "REQ_COMMON_KH_2309"))
        try:
            float(name)
            numeric_names += 1
        except ValueError:
            pass
        unique, suffix = name, 2
        while unique in seen:
            unique, suffix = f"{name}_{suffix}", suffix + 1
        if unique != name:
            issues.append(Issue(Severity.WARNING, f"En-tête « {name} » en double, renommé « {unique} ».",
                                line, "REQ_COMMON_KH_2309"))
        seen.add(unique)
        names.append(unique)
    if numeric_names >= max(1, len(names) - 1):
        issues.append(Issue(Severity.WARNING,
                            "La première ligne ne contient que des nombres : une ligne d'en-têtes "
                            "(noms des variables PLC) est attendue.", line, "REQ_COMMON_KH_2308"))
    return names, issues


def read_csv(path, max_size_mb: float = 500.0, progress: ProgressCallback | None = None,
             cancel=None) -> CsvTable:
    """Lit un fichier CSV PTBG et renvoie un ``CsvTable``.

    ``progress`` reçoit l'avancement (0..1) ; ``cancel`` est un
    ``threading.Event`` consulté à chaque bloc. Lève ``CsvReadError`` si le
    fichier est illisible, ``ReadCancelled`` en cas d'annulation.
    """
    path = Path(path)
    size, issues = _check_file(path, max_size_mb)
    _check_separator(path)
    sha = file_sha256(path, cancel)
    stats = {"rejected": [], "empty_lines": 0, "comments": [], "trimmed": 0}
    with path.open("rb") as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8-sig", errors="strict", newline="")
        reader = csv.reader(text, delimiter=",", quotechar='"')
        try:
            table = _parse_rows(reader, raw, size, path, sha, issues, stats, progress, cancel)
        except UnicodeDecodeError:
            raise CsvReadError(issues + [Issue(
                Severity.ERROR, "Encodage non UTF-8 : octet invalide (enregistrer le fichier en UTF-8).",
                reader.line_num + 1, "REQ_COMMON_KH_2302")])
        except csv.Error as exc:
            raise CsvReadError(issues + [Issue(Severity.ERROR, f"Structure CSV illisible : {exc}.",
                                               reader.line_num, "REQ_COMMON_KH_2300")])
    _summarize_row_issues(table.issues, stats)
    return table


def _parse_rows(reader, raw, size, path, sha, issues, stats, progress, cancel) -> CsvTable:
    """Boucle de lecture : en-tête puis blocs de données convertis en numpy."""
    first_rows = []
    for row in reader:
        first_rows.append((reader.line_num, row))
        if len(first_rows) >= SNIFF_ROWS:
            break
    header_position, header_row, header_issues = _find_header(first_rows)
    issues.extend(header_issues)
    header_line = first_rows[header_position][0]
    names, name_issues = normalize_header(header_row, header_line)
    issues.extend(name_issues)
    n_columns = len(names)
    builders = [_ColumnBuilder(name, index) for index, name in enumerate(names[1:], start=1)]
    time_raw: list[str] = []
    line_numbers: list[int] = []
    chunk: list[list[str]] = []

    def flush() -> None:
        """Convertit le bloc de lignes accumulé (colonnes numpy) et publie l'avancement."""
        if not chunk:
            return
        columns = list(zip(*chunk))       # transposition rapide (C)
        time_raw.extend(columns[0])
        for builder, cells in zip(builders, columns[1:]):
            builder.add(cells)
        chunk.clear()
        if cancel is not None and cancel.is_set():
            raise ReadCancelled()
        if progress is not None:
            progress(min(1.0, raw.tell() / size))

    def accept(line: int, row: list[str]) -> None:
        """Filtre une ligne : vide, commentaire, nombre de champs ; sinon l'ajoute au bloc."""
        if not row or (len(row) == 1 and not row[0].strip()):
            stats["empty_lines"] += 1
            return
        if row[0].lstrip().startswith("#"):
            stats["comments"].append(line)
            return
        if len(row) != n_columns:
            # Virgules finales sans contenu : tolérées (export de tableur).
            if len(row) > n_columns and not any(cell.strip() for cell in row[n_columns:]):
                row = row[:n_columns]
                stats["trimmed"] += 1
            else:
                stats["rejected"].append((line, len(row)))
                return
        chunk.append(row)
        line_numbers.append(line)
        if len(chunk) >= CHUNK_ROWS:
            flush()

    for line, row in first_rows[header_position + 1:]:
        accept(line, row)
    for row in reader:
        accept(reader.line_num, row)
    flush()
    if not time_raw:
        raise CsvReadError(issues + [Issue(Severity.ERROR, "Aucune ligne de données après l'en-tête.",
                                           header_line + 1)])
    stats["n_columns"] = n_columns
    return CsvTable(path=path, size_bytes=size, sha256=sha, header=names, time_raw=time_raw,
                    line_numbers=np.array(line_numbers, dtype=np.int64),
                    columns=[builder.finish() for builder in builders], issues=issues)


def _summarize_row_issues(issues: list[Issue], stats: dict) -> None:
    """Transforme les compteurs de lecture en constats lisibles."""
    rejected = stats["rejected"]
    for line, count in rejected[:MAX_DETAILED_ISSUES]:
        issues.append(Issue(Severity.WARNING,
                            f"Ligne rejetée : {count} champ(s) au lieu de {stats['n_columns']}.",
                            line, "REQ_COMMON_KH_2301"))
    if len(rejected) > MAX_DETAILED_ISSUES:
        issues.append(Issue(Severity.WARNING,
                            f"{len(rejected) - MAX_DETAILED_ISSUES} autre(s) ligne(s) rejetée(s) "
                            "pour un nombre de champs incorrect."))
    if stats["comments"]:
        issues.append(Issue(Severity.WARNING,
                            f"{len(stats['comments'])} ligne(s) de commentaire/métadonnées « # » ignorée(s).",
                            stats["comments"][0], "REQ_COMMON_KH_2303"))
    if stats["empty_lines"]:
        issues.append(Issue(Severity.INFO, f"{stats['empty_lines']} ligne(s) vide(s) ignorée(s)."))
    if stats["trimmed"]:
        issues.append(Issue(Severity.INFO,
                            f"{stats['trimmed']} ligne(s) terminée(s) par des virgules vides (tolérées)."))
