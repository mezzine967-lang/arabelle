"""Conversions vectorisées de textes en nombres et en horodatages.

Requis servis : REQ_COMMON_KH_4105 (traitement jamais bloqué : un fichier de
plusieurs centaines de Mo est converti en quelques secondes), au service de
la lecture des CSV (REQ_COMMON_KH_2301) et de la base de temps
(REQ_COMMON_KH_2306, 2307).

Principe : la conversion d'une colonne entière est confiée à numpy ; seules
les cellules que numpy ne sait pas convertir sont reprises une à une par les
fonctions « scalaires » de référence des modules appelants. Le résultat est
donc IDENTIQUE à une conversion cellule par cellule : rien n'est arrondi,
deviné ni complété, seule la vitesse change.

- ``parse_numbers`` : textes -> nombres. numpy convertit une liste de textes
  avec ``float()`` / ``int()`` de Python (mêmes règles) ; quand un bloc
  contient une cellule non numérique, il est coupé en deux jusqu'à isoler les
  cellules fautives (quelques cellules vides ne ralentissent pas la colonne).
- ``match_templates`` : textes de largeur fixe (« hh:mm:ss.fffffffff »,
  « AAAA-MM-JJ hh:mm:ss »…) découpés par position sur leurs octets, comme le
  ferait l'expression régulière, mais pour toute la colonne d'un coup.
"""
from __future__ import annotations

import numpy as np

LEAF_SIZE = 16            # en dessous, les cellules d'un bloc fautif sont reprises une à une
DIGIT_FIELDS = "YMDhmsf"  # année, mois, jour, heure, minute, seconde, fraction


def parse_numbers(texts: list[str], dtype=np.float64) -> tuple[np.ndarray, np.ndarray]:
    """Convertit des textes en nombres (``float()`` ou ``int()`` de Python).

    Renvoie (valeurs, converti) : ``converti`` est faux pour une cellule que la
    conversion refuse (sa valeur vaut alors 0 ou NaN et ne doit pas être lue).
    Recherche dichotomique des cellules fautives : coût proche d'une
    conversion directe quand elles sont rares."""
    converter = float if np.dtype(dtype).kind == "f" else int
    values = np.zeros(len(texts), dtype=dtype)
    converted = np.ones(len(texts), dtype=bool)
    pending = [(0, len(texts))]
    while pending:
        start, end = pending.pop()
        if start >= end:
            continue
        try:
            values[start:end] = np.array(texts[start:end], dtype=dtype)
            continue
        except (ValueError, OverflowError):
            pass
        if end - start > LEAF_SIZE:
            middle = (start + end) // 2
            pending += [(middle, end), (start, middle)]
            continue
        for position in range(start, end):
            try:
                values[position] = converter(texts[position])
            except (ValueError, OverflowError):
                converted[position] = False
    if values.dtype.kind == "f":
        values[~converted] = np.nan
    return values, converted


def _byte_matrix(texts: list[str], rows: np.ndarray) -> np.ndarray:
    """Octets des textes retenus, une ligne par texte (complétée par des zéros)."""
    picked = texts if rows.size == len(texts) else [texts[i] for i in rows.tolist()]
    data = np.array(picked, dtype=np.bytes_)
    width = max(data.dtype.itemsize, 1)
    return data.view(np.uint8).reshape(len(picked), width)


def match_templates(texts: list[str], templates: list[str]) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Reconnaît des textes de largeur fixe décrits par des modèles.

    Dans un modèle, chaque lettre de ``DIGIT_FIELDS`` est un chiffre ASCII du
    champ de même nom ; « ~ » vaut « T » ou une espace ; tout autre caractère
    doit être présent tel quel. Renvoie l'indice du modèle reconnu pour chaque
    texte (-1 : aucun, le texte est à traiter par l'appelant) et la valeur
    entière des champs. Le champ « f » (fraction de seconde) est rendu en
    nanosecondes : « .5 » -> 500 000 000. Aucun contrôle de plage ici (heure < 24,
    jour du mois…) : il revient à l'appelant."""
    n = len(texts)
    matched = np.full(n, -1, dtype=np.int64)
    fields = {name: np.zeros(n, dtype=np.int64) for name in DIGIT_FIELDS if any(name in t for t in templates)}
    if n == 0:
        return matched, fields
    lengths = np.fromiter(map(len, texts), dtype=np.int64, count=n)
    by_length: dict[int, list[tuple[int, str]]] = {}
    for number, template in enumerate(templates):
        by_length.setdefault(len(template), []).append((number, template))
    candidates = np.isin(lengths, list(by_length)) & np.fromiter(map(str.isascii, texts), dtype=bool, count=n)
    rows = np.flatnonzero(candidates)
    if rows.size == 0:
        return matched, fields
    matrix = _byte_matrix(texts, rows)
    row_lengths = lengths[rows]
    for length in np.unique(row_lengths).tolist():
        same = np.flatnonzero(row_lengths == length)
        block = matrix[same, :length]
        free = np.ones(same.size, dtype=bool)
        for number, template in by_length[length]:
            digit_columns = [column for column, char in enumerate(template) if char in DIGIT_FIELDS]
            digits = block[:, digit_columns] - np.uint8(48)   # hors « 0 »..« 9 » : > 9 (modulo 256)
            ok = free & (digits <= 9).all(axis=1)
            for column, char in enumerate(template):
                if char == "~":
                    ok &= (block[:, column] == ord("T")) | (block[:, column] == ord(" "))
                elif char not in DIGIT_FIELDS:
                    ok &= block[:, column] == ord(char)
            if not ok.any():
                continue
            target = rows[same[ok]]
            matched[target] = number
            kept = digits[ok]                                 # octets : peu de mémoire temporaire
            for name in sorted(set(template) & set(DIGIT_FIELDS)):
                where = [rank for rank, column in enumerate(digit_columns) if template[column] == name]
                value = np.zeros(target.size, dtype=np.int64)
                for rank in where:
                    value = value * 10 + kept[:, rank]
                if name == "f":                               # fraction -> nanosecondes
                    value *= 10 ** (9 - len(where))
                fields[name][target] = value
            free &= ~ok
            if not free.any():
                break
    return matched, fields


def days_from_civil(year: np.ndarray, month: np.ndarray, day: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Jours depuis le 1970-01-01 (calendrier grégorien) et validité de la date.

    Mêmes dates valides que ``datetime.date`` : année 1 à 9999, mois 1 à 12,
    jour existant dans le mois (29 février des années bissextiles seulement)."""
    leap = ((year % 4 == 0) & (year % 100 != 0)) | (year % 400 == 0)
    month_days = np.array([31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=np.int64)
    in_range = (year >= 1) & (year <= 9999) & (month >= 1) & (month <= 12)
    last = month_days[np.clip(month, 1, 12) - 1] + (leap & (month == 2))
    valid = in_range & (day >= 1) & (day <= last)
    # Algorithme « days_from_civil » (H. Hinnant), exact en entiers.
    shifted = year - (month <= 2)
    era = shifted // 400
    year_of_era = shifted - era * 400
    day_of_year = (153 * (month + np.where(month > 2, -3, 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468, valid
