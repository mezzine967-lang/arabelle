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
"""
from __future__ import annotations

import io
from dataclasses import dataclass

import numpy as np

from ptbg.core.csv_reader import (KIND_BOOL, KIND_EMPTY, KIND_NONFINITE, KIND_NUMBER, CsvTable, RawColumn,
                                  _line_blocks, _ReadStats, _split_line)
from ptbg.core.time_base import to_ns

PAGE_ROWS = 500          # lignes affichées par page


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


def time_steps_ms(seconds: np.ndarray, first: int, count: int) -> list[str]:
    """Δt avec la mesure précédente, en ms, pour les mesures ``first`` à ``first + count``.

    Différence de nanosecondes entières : aucun arrondi de flottant (voir en-tête)."""
    begin = max(first - 1, 0)
    ns = to_ns(seconds[begin:first + count])
    steps = np.diff(ns)
    if first == 0:
        steps = np.concatenate(([np.nan], steps))
    return [ns_as_ms(step) for step in steps]


def read_rows(table: CsvTable, column_indexes: list[int], first: int,
              count: int = PAGE_ROWS) -> tuple[list[RawRow], bool]:
    """Relit dans le fichier les mesures ``first`` à ``first + count`` (exclu).

    ``column_indexes`` : positions des colonnes dans le CSV (``RawColumn.index``).
    Renvoie les lignes et ``True`` si le fichier ne correspond plus à ce qui a
    été chargé (temps relu différent, ligne disparue). Lève ``OSError`` si le
    fichier n'est plus lisible."""
    first = max(0, min(first, table.n_samples))
    numbers = table.line_numbers[first:first + count].tolist()
    wanted = {line: first + offset for offset, line in enumerate(numbers)}
    rows: dict[int, RawRow] = {}
    if numbers:
        low, high = min(numbers), max(numbers)
        encoding, errors = table.decoding
        stats = _ReadStats()
        with open(table.path, "rb") as raw:
            handle = io.TextIOWrapper(raw, encoding=encoding, errors=errors, newline=None)
            for start, _, lines in _line_blocks(handle, stats):
                if start + len(lines) - 1 < low:
                    continue                      # bloc entièrement avant la page : sauté
                for number, text in enumerate(lines, start=start):
                    if number in wanted:
                        fields = _split_line(number, text, stats) or []
                        cells = [fields[i] if i < len(fields) else "" for i in column_indexes]
                        rows[number] = RawRow(wanted[number], number, fields[0] if fields else "", cells)
                if start + len(lines) - 1 >= high:
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
