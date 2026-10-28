"""Lecture contrôlée d'un fichier CSV PTBG.

Requis couverts (section 2.3 « File' Features ») :

- REQ_COMMON_KH_2300 : format préféré csv (autre extension = avertissement) ;
- REQ_COMMON_KH_2301 : séparateur virgule (« ; », tabulation, « | » = refus) ;
- REQ_COMMON_KH_2302 : texte UTF-8 (BOM toléré ; autre encodage lu mais signalé) ;
- REQ_COMMON_KH_2303 : pas de métadonnées (lignes « # » ou préambule signalés) ;
- REQ_COMMON_KH_2304 : première colonne = base de temps (quel que soit son nom) ;
- REQ_COMMON_KH_2308 : première ligne = en-têtes de colonnes ;
- REQ_COMMON_KH_2309 : en-têtes = noms des variables PLC (vides/doublons signalés) ;
- REQ_COMMON_KH_2310 : taille maximale (paramètre, voir config.py) ;
- REQ_COMMON_KH_4105 : lecture par blocs, annulable, sans blocage de l'IHM.

Principe de robustesse : une anomalie de CONTENU produit un constat (avec le
numéro de ligne) et la lecture continue ; seule une anomalie de FORMAT rendant
tout le fichier inexploitable lève ``CsvReadError``. Aucune valeur n'est
inventée : une cellule vide reste vide (NaN + masque), une ligne douteuse est
rejetée et listée plutôt que réparée.

Le fichier est lu LIGNE PHYSIQUE PAR LIGNE PHYSIQUE : un guillemet non fermé,
des octets nuls ou une cellule démesurée n'abîment que leur propre ligne et
jamais la suite du fichier ; les numéros de ligne cités sont exacts.

Cas traités sans perte des autres données :

- lignes vides ou entièrement vides (« ,,, ») : ignorées et comptées ;
- en-tête répété au milieu (fichiers concaténés) : ignoré et signalé ;
- ligne au mauvais nombre de champs (tronquée, en trop) : rejetée et listée ;
- virgules finales sans contenu (export de tableur) : tolérées ;
- octets nuls (écriture interrompue) : ligne rejetée, remplissage final compté ;
- dernière ligne sans fin de ligne : signalée (mesure peut-être incomplète) ;
- préambule de métadonnées de n'importe quelle largeur : repéré et ignoré ;
- absence d'en-tête : la 1re ligne de mesures est conservée, colonnes nommées ;
- octets non UTF-8 (fichier enregistré en Windows-1252) : lus, non-conformité signalée.

Chaque cellule est classée selon sa nature (vide, nombre, booléen texte,
texte libre, nombre non fini « nan »/« inf »). Le choix du type Bool/Float est
fait ensuite par ``signals.auto_type`` et peut être modifié par l'utilisateur
sans relire le fichier.
"""
from __future__ import annotations

import codecs
import csv
import hashlib
import io
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np

from ptbg.core.diagnostics import Issue, Severity
from ptbg.core.time_parser import looks_like_time

# Nature d'une cellule (tableau int8 ``kinds`` de chaque colonne).
# KIND_NONFINITE : nombre écrit « nan », « inf »… (valeur absente, pas un texte).
KIND_EMPTY, KIND_NUMBER, KIND_BOOL, KIND_TEXT, KIND_NONFINITE = 0, 1, 2, 3, 4

CHUNK_ROWS = 20_000        # lignes converties en numpy par bloc
SNIFF_ROWS = 50            # lignes examinées pour repérer l'en-tête
SEPARATOR_SAMPLE = 30      # lignes examinées pour contrôler le séparateur
MAX_DETAILED_ISSUES = 20   # au-delà, les lignes rejetées sont résumées
EXCERPT_CHARS = 60         # extrait d'une ligne rejetée cité dans le constat

ProgressCallback = Callable[[float], None]


def _cp1252_fallback(error):
    """Décodage de secours : un octet non UTF-8 est lu en Windows-1252.

    C'est l'encodage d'un CSV enregistré par Excel sous Windows (« é », « ° ») :
    les noms restent lisibles et les nombres, en ASCII, ne sont pas touchés.
    L'emploi de ce secours est toujours signalé comme non-conformité (REQ 2302)."""
    if not isinstance(error, UnicodeDecodeError):
        raise error
    return error.object[error.start:error.end].decode("cp1252", errors="replace"), error.end


codecs.register_error("ptbg_cp1252", _cp1252_fallback)


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
        except ValueError:
            values, kinds, codes = self._convert_slowly(cells)
        else:
            finite = np.isfinite(values)
            kinds = np.where(finite, KIND_NUMBER, KIND_NONFINITE).astype(np.int8)
            values[~finite] = np.nan
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
        """Classe chaque cellule : vide, booléen (true/false), nombre, non fini, texte."""
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
                        kind, has_text = KIND_TEXT, True
                        code = self.categories.setdefault(text, len(self.categories))
                    else:
                        if math.isfinite(number):
                            value, kind = number, KIND_NUMBER
                        else:
                            kind = KIND_NONFINITE
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
                         [_printable(text) for text in self.categories], self.binary,
                         self.has_zero, self.has_one)


def _printable(text: str) -> str:
    """Caractères de contrôle (octets parasites) remplacés par « ? » pour l'affichage."""
    return text if text.isprintable() else "".join(ch if ch.isprintable() else "?" for ch in text)


def _concat(chunks: list[np.ndarray], dtype) -> np.ndarray:
    return np.concatenate(chunks) if chunks else np.empty(0, dtype=dtype)


@dataclass
class _ReadStats:
    """Constats accumulés pendant la lecture, résumés à la fin (``_summarize``)."""
    empty_lines: int = 0
    comments: list[int] = field(default_factory=list)
    nul_padding: int = 0
    trimmed: int = 0
    repeated_headers: list[int] = field(default_factory=list)
    rejected: int = 0
    rejected_details: list[tuple[int, str, str, str]] = field(default_factory=list)
    last_line: int = 0
    last_terminated: bool = True
    last_accepted: int = 0          # n° de la dernière ligne gardée comme mesure

    def reject(self, line: int, reason: str, text: str, requirement: str = "REQ_COMMON_KH_2301") -> None:
        """Ligne écartée : comptée, et détaillée pour les premières."""
        self.rejected += 1
        if len(self.rejected_details) < MAX_DETAILED_ISSUES:
            excerpt = _printable(text.replace("\x00", "\\0")[:EXCERPT_CHARS])
            self.rejected_details.append((line, reason, excerpt, requirement))


# ----------------------------------------------------------- contrôles préalables
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
    return size, issues


def _digest(path: Path, cancel=None) -> tuple[str, bool]:
    """Empreinte SHA-256 (REQ 6005) et validité UTF-8, en un seul passage par blocs."""
    digest = hashlib.sha256()
    decoder = codecs.getincrementaldecoder("utf-8")()
    utf8 = True
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            if cancel is not None and cancel.is_set():
                raise ReadCancelled()
            digest.update(block)
            if utf8:
                try:
                    decoder.decode(block)
                except UnicodeDecodeError:
                    utf8 = False
    if utf8:
        try:
            decoder.decode(b"", final=True)
        except UnicodeDecodeError:
            utf8 = False
    return digest.hexdigest(), utf8


def _choose_encoding(path: Path, utf8: bool) -> tuple[str, str, list[Issue]]:
    """Encodage et gestion d'erreur de décodage, avec le constat associé (REQ 2302)."""
    with path.open("rb") as handle:
        head = handle.read(4)
    if head[:2] in (b"\xff\xfe", b"\xfe\xff"):
        return "utf-16", "replace", [Issue(
            Severity.ERROR, "Fichier encodé en UTF-16 : lu, mais l'encodage attendu est UTF-8.",
            1, "REQ_COMMON_KH_2302")]
    issues = []
    encoding = "utf-8"
    if head.startswith(b"\xef\xbb\xbf"):
        encoding = "utf-8-sig"
        issues.append(Issue(Severity.INFO, "Marque d'ordre UTF-8 (BOM) présente : tolérée.",
                            requirement="REQ_COMMON_KH_2302"))
    if utf8:
        return encoding, "strict", issues
    first, count = _non_utf8_lines(path)
    issues.append(Issue(Severity.ERROR,
                        f"Encodage non UTF-8 : {count} ligne(s) contiennent des octets invalides "
                        f"(1re : ligne {first}). Ces octets sont lus en Windows-1252 ; "
                        "enregistrer le fichier en UTF-8.", first, "REQ_COMMON_KH_2302"))
    return encoding, "ptbg_cp1252", issues


def _non_utf8_lines(path: Path) -> tuple[int, int]:
    """1re ligne contenant un octet non UTF-8 et nombre de lignes concernées."""
    first, count = 0, 0
    with path.open("rb") as handle:
        for number, line in enumerate(handle, start=1):
            try:
                line.decode("utf-8")
            except UnicodeDecodeError:
                count += 1
                first = first or number
    return first or 1, max(count, 1)


def _field_count(line: str, separator: str) -> int:
    """Nombre de champs d'une ligne pour un séparateur (guillemets respectés)."""
    try:
        return len(next(csv.reader([line], delimiter=separator)))
    except (csv.Error, StopIteration):
        return 1


def _check_separator(lines: list[str]) -> None:
    """REQ_COMMON_KH_2301 : les champs doivent être séparés par des virgules.

    Pour chaque séparateur candidat, on mesure la part des lignes qui ont le
    même nombre de champs (> 1) : c'est la signature d'un vrai séparateur. Le
    contrôle porte sur le texte brut : avec « ; » et une décimale à virgule
    (« 0;1,5;0 »), un découpage à la virgule produirait de faux champs. La
    virgule l'emporte en cas d'égalité."""
    def consistency(separator: str) -> float:
        widths = [count for count in (_field_count(line, separator) for line in lines) if count > 1]
        if not widths:
            return 0.0
        return widths.count(max(set(widths), key=widths.count)) / len(lines)

    comma = consistency(",")
    for separator, label in ((";", "point-virgule"), ("\t", "tabulation"), ("|", "barre verticale")):
        if consistency(separator) > comma:
            hint = " (la virgule y sert sans doute de séparateur décimal)" if separator == ";" else ""
            raise CsvReadError([Issue(Severity.ERROR,
                                      f"Séparateur « {label} » détecté{hint} : le séparateur doit "
                                      "être la virgule.", 1, "REQ_COMMON_KH_2301")])
    if comma == 0.0:
        raise CsvReadError([Issue(Severity.ERROR,
                                  "Une seule colonne : la 1re colonne est la base de temps et aucune "
                                  "variable n'est présente.", 1, "REQ_COMMON_KH_2304")])


# --------------------------------------------------------------- découpage des lignes
def _split_rows(handle, stats: _ReadStats):
    """Découpe chaque ligne physique en champs : renvoie (n° de ligne, champs).

    Les lignes vides, de commentaire « # » ou corrompues sont comptées ou
    rejetées ici. Une ligne sans guillemet est découpée directement à la
    virgule ; sinon le module ``csv`` l'analyse en mode strict, LIMITÉ À CETTE
    LIGNE : un guillemet non fermé ne peut pas avaler la suite du fichier."""
    number, terminated = 0, True
    for number, line in enumerate(handle, start=1):
        terminated = line.endswith("\n")
        text = line[:-1] if terminated else line
        if "\x00" in text:
            if text.strip("\x00 \t\r"):
                stats.reject(number, "octets nuls dans la ligne (zone corrompue ou écriture interrompue)",
                             text, "REQ_COMMON_KH_2302")
            else:
                stats.nul_padding += 1
            continue
        if text[:1] in ("", " ", "\t", "#", "\ufeff"):  # contrôles coûteux seulement si utiles
            text = text.lstrip("\ufeff")    # BOM d'un 2e fichier collé à la suite du 1er
            if not text.strip():
                stats.empty_lines += 1
                continue
            if text.lstrip().startswith("#"):
                stats.comments.append(number)
                continue
        if '"' in text:
            try:
                fields = next(csv.reader([text], strict=True))
            except csv.Error as exc:
                stats.reject(number, f"guillemets mal formés ({exc})", text)
                continue
        else:
            fields = text.split(",")
        if not fields[0].strip() and not any(cell.strip() for cell in fields):
            stats.empty_lines += 1           # « ,,,, » : aucune donnée
            continue
        yield number, fields
    stats.last_line, stats.last_terminated = number, terminated


def _width(fields: list[str]) -> int:
    """Nombre de champs sans les champs vides de fin (virgules finales)."""
    width = len(fields)
    while width > 1 and not fields[width - 1].strip():
        width -= 1
    return width


def _locate_header(first_rows: list[tuple[int, list[str]]]):
    """Repère l'en-tête et les lignes de métadonnées qui le précèdent (REQ 2303, 2308).

    La 1re ligne de MESURES est la première dont le 1er champ a la forme d'un
    horodatage et dont la largeur est la plus fréquente parmi ces lignes.
    L'en-tête est la dernière ligne non-mesure qui la précède ; tout ce qui est
    avant l'en-tête est un préambule de métadonnées, quelle que soit sa largeur.
    Renvoie (position de l'en-tête ou None s'il n'y en a pas, largeur des
    données, position de la 1re ligne de données)."""
    widths = [_width(fields) for _, fields in first_rows]
    data_like = [i for i, (_, fields) in enumerate(first_rows) if widths[i] >= 2 and looks_like_time(fields[0])]
    if data_like:
        data_widths = [widths[i] for i in data_like]
        dominant = max(set(data_widths), key=data_widths.count)
        first_data = next(i for i in data_like if widths[i] == dominant)
        labels = [i for i in range(first_data) if not looks_like_time(first_rows[i][1][0])]
        if not labels:
            return None, dominant, 0
        return labels[-1], dominant, labels[-1] + 1
    # Aucune mesure reconnaissable (horodatage illisible partout) : la largeur
    # la plus fréquente est celle du tableau, l'en-tête est la 1re ligne de cette largeur.
    dominant = max(set(widths), key=widths.count)
    header = next(i for i, width in enumerate(widths) if width >= dominant)
    return header, dominant, header + 1


def normalize_header(raw_names: list[str], line: int) -> tuple[list[str], list[Issue]]:
    """Rend les noms de colonnes non vides et uniques (REQ 2308, 2309)."""
    issues, names, seen = [], [], set()
    numeric_names = 0
    for position, raw in enumerate(raw_names):
        name = _printable(raw.strip())
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
                            "La ligne d'en-têtes ne contient que des nombres : des noms de variables "
                            "PLC sont attendus.", line, "REQ_COMMON_KH_2308"))
    return names, issues


# ------------------------------------------------------------------------ lecture
def read_csv(path, max_size_mb: float = 500.0, progress: ProgressCallback | None = None,
             cancel=None) -> CsvTable:
    """Lit un fichier CSV PTBG et renvoie un ``CsvTable``.

    ``progress`` reçoit l'avancement (0..1) ; ``cancel`` est un
    ``threading.Event`` consulté à chaque bloc. Lève ``CsvReadError`` si le
    fichier est inexploitable, ``ReadCancelled`` en cas d'annulation.
    """
    path = Path(path)
    size, issues = _check_file(path, max_size_mb)
    sha, utf8 = _digest(path, cancel)
    encoding, errors, encoding_issues = _choose_encoding(path, utf8)
    issues.extend(encoding_issues)
    with path.open("rb") as raw:
        # newline=None : fins de ligne \n, \r\n et \r reconnues, même mélangées.
        handle = io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=None)
        stats = _ReadStats()
        rows = _split_rows(handle, stats)
        first_rows = []
        for row in rows:
            first_rows.append(row)
            if len(first_rows) >= SNIFF_ROWS:
                break
        if not first_rows:
            raise CsvReadError(issues + [Issue(Severity.ERROR, "Aucune ligne exploitable : fichier composé "
                                               "de lignes vides, de commentaires ou d'octets nuls.")])
        try:
            _check_separator([_rejoin(fields) for _, fields in first_rows[:SEPARATOR_SAMPLE]])
        except CsvReadError as exc:
            raise CsvReadError(issues + exc.issues)
        table = _parse(first_rows, rows, raw, size, path, sha, issues, stats, progress, cancel)
    return table


def _rejoin(fields: list[str]) -> str:
    """Texte d'une ligne recomposé depuis ses champs (guillemets remis si nécessaire)."""
    buffer = io.StringIO()
    csv.writer(buffer, lineterminator="").writerow(fields)
    return buffer.getvalue()


def _parse(first_rows, rows, raw, size, path, sha, issues, stats, progress, cancel) -> CsvTable:
    """En-tête puis blocs de données convertis en numpy."""
    header_position, width, data_start = _locate_header(first_rows)
    for line, fields in first_rows[:header_position or 0]:
        issues.append(Issue(Severity.WARNING, "Ligne de métadonnées avant l'en-tête ignorée : « "
                            + _printable(",".join(fields)[:EXCERPT_CHARS]) + " ».", line, "REQ_COMMON_KH_2303"))
    if header_position is None:
        header_line = first_rows[0][0]
        header_fields = [f"Colonne_{i + 1}" for i in range(width)]
        issues.append(Issue(Severity.WARNING,
                            f"Pas de ligne d'en-têtes : la ligne {header_line} contient déjà des mesures ; "
                            f"elles sont conservées et les colonnes nommées Colonne_1 … Colonne_{width}.",
                            header_line, "REQ_COMMON_KH_2308"))
    else:
        header_line, header_fields = first_rows[header_position]
        # Champs vides de fin : gardés seulement s'il y a des données en face.
        header_fields = header_fields[:max(_width(header_fields), min(width, len(header_fields)))]
    names, name_issues = normalize_header(header_fields, header_line)
    issues.extend(name_issues)
    n_columns = len(names)
    # Toutes les mesures plus courtes que l'en-tête (dernières colonnes jamais écrites) :
    # ces lignes sont gardées, les colonnes sans données restent vides et sont signalées.
    short_width = width if 2 <= width < n_columns else None
    if short_width:
        issues.append(Issue(Severity.WARNING,
                            f"Les lignes de mesures n'ont que {width} champs pour {n_columns} en-têtes : "
                            f"colonne(s) {', '.join(names[width:])} sans données (laissées vides).",
                            header_line, "REQ_COMMON_KH_2308"))
    header_key = [cell.strip() for cell in header_fields] if header_position is not None else None
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

    def accept(line: int, fields: list[str]) -> None:
        """Contrôle le nombre de champs puis ajoute la ligne au bloc."""
        if len(fields) != n_columns:
            if len(fields) > n_columns and not any(cell.strip() for cell in fields[n_columns:]):
                fields = fields[:n_columns]          # virgules finales sans contenu : tolérées
                stats.trimmed += 1
            elif len(fields) == short_width:
                fields = fields + [""] * (n_columns - short_width)
            else:
                stats.reject(line, f"{len(fields)} champ(s) au lieu de {n_columns}", ",".join(fields))
                return
        if header_key is not None and fields[0].strip() == header_key[0] \
                and [cell.strip() for cell in fields] == header_key:
            stats.repeated_headers.append(line)     # fichiers concaténés
            return
        chunk.append(fields)
        line_numbers.append(line)
        stats.last_accepted = line
        if len(chunk) >= CHUNK_ROWS:
            flush()

    for line, fields in first_rows[data_start:]:
        accept(line, fields)
    for line, fields in rows:
        accept(line, fields)
    flush()
    _summarize(issues, stats, n_columns, len(time_raw))
    if not time_raw:
        raise CsvReadError(issues + [Issue(Severity.ERROR, "Aucune ligne de données exploitable après l'en-tête.",
                                           header_line + 1)])
    return CsvTable(path=path, size_bytes=size, sha256=sha, header=names, time_raw=time_raw,
                    line_numbers=np.array(line_numbers, dtype=np.int64),
                    columns=[builder.finish() for builder in builders], issues=issues)


def _summarize(issues: list[Issue], stats: _ReadStats, n_columns: int, n_accepted: int) -> None:
    """Transforme les compteurs de lecture en constats lisibles."""
    unfinished = not stats.last_terminated
    for line, reason, excerpt, requirement in stats.rejected_details:
        if unfinished and line == stats.last_line:
            reason += " ; dernière ligne non terminée : écriture probablement interrompue"
        issues.append(Issue(Severity.WARNING, f"Ligne rejetée : {reason} : « {excerpt} ».", line, requirement))
    if stats.rejected > len(stats.rejected_details):
        issues.append(Issue(Severity.WARNING,
                            f"{stats.rejected - len(stats.rejected_details)} autre(s) ligne(s) rejetée(s).",
                            requirement="REQ_COMMON_KH_2301"))
    if stats.rejected > n_accepted:
        issues.append(Issue(Severity.ERROR,
                            f"La plupart des lignes ({stats.rejected}) n'ont pas les {n_columns} colonnes de "
                            "l'en-tête : virgule utilisée comme séparateur décimal, ou en-tête incomplet ?",
                            requirement="REQ_COMMON_KH_2301"))
    if unfinished and stats.last_accepted == stats.last_line:
        issues.append(Issue(Severity.WARNING,
                            "Dernière ligne non terminée par un retour à la ligne : écriture peut-être "
                            "interrompue, vérifier cette dernière mesure.", stats.last_line))
    if stats.repeated_headers:
        issues.append(Issue(Severity.WARNING,
                            f"{len(stats.repeated_headers)} ligne(s) d'en-têtes répétée(s) au milieu des "
                            "données ignorée(s) (fichiers mis bout à bout ?).",
                            stats.repeated_headers[0], "REQ_COMMON_KH_2308"))
    if stats.nul_padding:
        issues.append(Issue(Severity.WARNING,
                            f"{stats.nul_padding} ligne(s) d'octets nuls ignorée(s) : fichier probablement "
                            "interrompu pendant l'écriture.", requirement="REQ_COMMON_KH_2302"))
    if stats.comments:
        issues.append(Issue(Severity.WARNING,
                            f"{len(stats.comments)} ligne(s) de commentaire/métadonnées « # » ignorée(s).",
                            stats.comments[0], "REQ_COMMON_KH_2303"))
    if stats.empty_lines:
        issues.append(Issue(Severity.INFO, f"{stats.empty_lines} ligne(s) vide(s) ignorée(s)."))
    if stats.trimmed:
        issues.append(Issue(Severity.INFO,
                            f"{stats.trimmed} ligne(s) terminée(s) par des virgules vides (tolérées)."))
