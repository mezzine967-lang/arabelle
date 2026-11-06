"""Relecture des cellules d'origine d'un fichier (fenêtre « Valeurs du CSV »).

But : montrer, ligne par ligne, le texte EXACT écrit dans le CSV à côté de la
valeur que l'outil a lue, pour vérifier qu'aucune valeur n'est ajoutée,
interpolée ou modifiée (REQ_COMMON_KH_4100 / 5202).

Le fichier est relu sur le disque avec le même encodage et le même découpage
des champs que la lecture d'origine (``csv_reader``), seulement pour les
lignes demandées (une page à la fois). Si le temps relu ne correspond plus au
temps chargé, le fichier a changé depuis son chargement : c'est signalé.

Le Δt affiché est calculé en nanosecondes entières, comme l'analyse de la base
de temps : avec des temps entiers en millisecondes, il est entier lui aussi.

Remarques et filtre « seulement les anomalies » : pour chaque mesure, les
anomalies de temps trouvées par l'analyse de la base de temps (trou, déphasage,
doublon, retour arrière, horodatage illisible ou aberrant, changement de
fréquence) et les cellules à problème des variables affichées (vide, « nan » /
« inf », valeur incompatible avec le type). Rien n'est recalculé ici : ce sont
les constats déjà utilisés par le TBM, le diagnostic et les courbes.
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np

from ptbg.core.csv_reader import (KIND_BOOL, KIND_EMPTY, KIND_NONFINITE, KIND_NUMBER, CsvTable, RawColumn,
                                  _line_blocks, _ReadStats, _split_line)
from ptbg.core.data_package import SourceFile
from ptbg.core.time_base import _KIND_OF_CODE, EventKind, to_ns

PAGE_ROWS = 500          # lignes affichées par page

# Anomalies de temps d'une mesure, dans l'ordre de priorité croissante (la dernière
# trouvée l'emporte), avec le texte de la colonne « Remarque ».
TIME_REMARKS = {EventKind.FREQUENCY: "Changement de fréquence",
                EventKind.MISSING: "Trou : mesures manquantes avant",
                EventKind.PHASE: "Déphasage (Δt hors tolérance)",
                EventKind.DUPLICATE: "Horodatage en double (Δt = 0)",
                EventKind.BACKWARD: "Retour arrière du temps (Δt < 0)",
                EventKind.OUTLIER: "Horodatage aberrant (exclu de l'analyse)",
                EventKind.INVALID: "Horodatage illisible"}
TIME_KINDS = (None,) + tuple(TIME_REMARKS)          # code 0 = aucune anomalie de temps


@dataclass
class RawRow:
    """Une mesure : sa ligne dans le fichier et les textes d'origine des cellules."""
    sample: int             # n° de la mesure (0 = 1re mesure gardée)
    line: int               # ligne physique dans le fichier
    time_text: str          # texte de la 1re colonne relu dans le fichier
    cells: list[str]        # texte relu de chaque colonne demandée ("" si absente)


def number_text(value: float) -> str:
    """Nombre écrit au plus court sans perte (4988.0 -> « 4988 », 12.5 -> « 12.5 »)."""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def ns_as_ms(value_ns: float) -> str:
    """Durée en nanosecondes entières écrite en ms, calcul en entiers (11 000 000 -> « 11 »)."""
    if not np.isfinite(value_ns):
        return ""
    sign, value = ("-" if value_ns < 0 else ""), abs(int(value_ns))
    whole, rest = divmod(value, 1_000_000)
    return f"{sign}{whole}" + (f".{rest:06d}".rstrip("0") if rest else "")


def value_text(column: RawColumn, sample: int) -> str:
    """Valeur lue par l'outil pour une cellule, telle qu'elle est utilisée."""
    kind = int(column.kinds[sample])
    if kind == KIND_EMPTY:
        return "(vide)"
    if kind == KIND_NONFINITE:
        return "(non fini : laissé vide)"
    if kind in (KIND_NUMBER, KIND_BOOL):
        return number_text(column.values[sample])
    code = int(column.codes[sample]) if column.codes is not None else -1
    return f"texte « {column.categories[code]} »" if 0 <= code < len(column.categories) else "(texte)"


def time_steps_ms(seconds: np.ndarray, samples: np.ndarray) -> list[str]:
    """Δt de chaque mesure de ``samples`` avec la mesure qui la précède dans le fichier,
    en ms (vide pour la 1re mesure ou un horodatage illisible).

    Différence de nanosecondes entières : aucun arrondi de flottant (voir en-tête)."""
    samples = np.asarray(samples, dtype=np.int64)
    steps = np.full(samples.size, np.nan)
    later = samples > 0
    steps[later] = to_ns(seconds[samples[later]]) - to_ns(seconds[samples[later] - 1])
    return [ns_as_ms(step) for step in steps]


def _time_codes(source: SourceFile) -> np.ndarray:
    """Pour chaque mesure : rang dans ``TIME_KINDS`` de son anomalie de temps (0 = aucune)."""
    analysis = source.analysis
    codes = np.zeros(analysis.n_samples, dtype=np.int8)
    found = {EventKind.FREQUENCY: [segment.start for segment in analysis.segments[1:]],
             EventKind.OUTLIER: analysis.excluded,
             EventKind.INVALID: np.flatnonzero(~np.isfinite(source.conversion.seconds))}
    for code, kind in _KIND_OF_CODE.items():
        found[kind] = analysis.dt_index[analysis.dt_kinds == code]
    for kind in TIME_REMARKS:                      # ordre de priorité croissante
        codes[np.asarray(found.get(kind, []), dtype=np.int64)] = TIME_KINDS.index(kind)
    return codes


def anomaly_samples(source: SourceFile, columns: list[RawColumn]) -> np.ndarray:
    """N° des mesures qui ont une anomalie de temps ou une cellule à problème dans une
    des variables ``columns`` (filtre « seulement les anomalies »)."""
    flagged = _time_codes(source) > 0
    for column in columns:
        signal = source.signal(column.name)
        flagged |= signal.missing | signal.invalid
    return np.flatnonzero(flagged)


def remarks(source: SourceFile, columns: list[RawColumn], samples: np.ndarray) -> list[str]:
    """Texte de la colonne « Remarque » pour chaque mesure de ``samples`` (vide si rien)."""
    times = _time_codes(source)
    signals = [source.signal(column.name) for column in columns]
    result = []
    for sample in np.asarray(samples, dtype=np.int64).tolist():
        parts = [TIME_REMARKS[TIME_KINDS[times[sample]]]] if times[sample] else []
        for column, signal in zip(columns, signals):
            if column.kinds[sample] == KIND_EMPTY:
                parts.append(f"{column.name} vide")
            elif signal.missing[sample]:
                parts.append(f"{column.name} « nan » / « inf » (laissée vide)")
            elif signal.invalid[sample]:
                parts.append(f"{column.name} incompatible avec le type {signal.type.value} (non tracée)")
        result.append(" ; ".join(parts))
    return result


def read_rows(table: CsvTable, column_indexes: list[int], samples: np.ndarray) -> tuple[list[RawRow], bool]:
    """Relit dans le fichier les mesures ``samples`` (n° croissants, pas forcément
    consécutifs : filtre des anomalies).

    ``column_indexes`` : positions des colonnes dans le CSV (``RawColumn.index``).
    Renvoie les lignes et ``True`` si le fichier ne correspond plus à ce qui a
    été chargé (temps relu différent, ligne disparue). Lève ``OSError`` si le
    fichier n'est plus lisible."""
    samples = np.asarray(samples, dtype=np.int64)
    samples = samples[(samples >= 0) & (samples < table.n_samples)]
    numbers = table.line_numbers[samples].tolist()
    wanted = dict(zip(numbers, samples.tolist()))
    rows: dict[int, RawRow] = {}
    if numbers:
        low, high = min(numbers), max(numbers)
        encoding, errors = table.decoding
        stats = _ReadStats()
        with open(table.path, "rb") as raw:
            handle = io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=None)
            for start, _, lines in _line_blocks(handle, stats):
                last = start + len(lines) - 1
                if last < low:
                    continue                      # bloc entièrement avant les lignes voulues : sauté
                for number, text in enumerate(lines, start=start):
                    if number in wanted:
                        fields = _split_line(number, text, stats) or []
                        cells = [fields[i] if i < len(fields) else "" for i in column_indexes]
                        rows[number] = RawRow(wanted[number], number, fields[0] if fields else "", cells)
                if last >= high:
                    break
    changed = len(rows) != len(numbers)
    result = []
    for line in numbers:
        row = rows.get(line)
        if row is None:
            row = RawRow(wanted[line], line, "", [""] * len(column_indexes))
        changed = changed or row.time_text != table.time_raw[row.sample]
        result.append(row)
    return result, changed


def find_sample(table: CsvTable, line: int) -> int:
    """N° de la 1re mesure située à la ligne ``line`` du fichier ou après."""
    return int(np.searchsorted(table.line_numbers, line, side="left"))
