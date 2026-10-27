"""Types de signaux et groupes binaires (section 2.2 « Source' contents »).

- REQ_COMMON_KH_2200 : signal binaire -> type ``BOOL`` ;
- REQ_COMMON_KH_2201 : signal analogique flottant -> type ``FLOAT`` ;
- REQ_COMMON_KH_2201 (2e occurrence) : groupe de signaux binaires ->
  ``BinaryGroup`` (plusieurs colonnes Bool affichées et lues ensemble, avec
  la valeur du mot binaire correspondant) ;
- REQ_COMMON_KH_5202 : le type de chaque variable est affiché dans l'arbre.

Règle de typage automatique (modifiable par l'utilisateur, variable par
variable, sans relire le fichier) :

1. cellules « true/false » (toute casse) uniquement            -> BOOL ;
2. nombres valant tous 0 ou 1, avec au moins un 0 ET un 1      -> BOOL ;
3. majorité de textes non numériques (ex. « STOP », « ACTIVE ») -> TEXTE
   (états énumérés : hors spécification, affichés en escalier) ;
4. sinon                                                       -> FLOAT.

Une colonne constante à 0 (ou à 1) reste FLOAT : rien ne permet de dire que
c'est un booléen, l'utilisateur peut forcer le type.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from ptbg.core.csv_reader import KIND_BOOL, KIND_EMPTY, KIND_NUMBER, KIND_TEXT, RawColumn


class SignalType(Enum):
    BOOL = "Bool"
    FLOAT = "Float"
    TEXT = "Texte"

    @property
    def is_digital(self) -> bool:
        """Bool et Texte sont tracés en escalier sur des pistes logiques."""
        return self is not SignalType.FLOAT


@dataclass
class SignalData:
    """Valeurs d'une variable interprétées selon son type."""
    name: str
    type: SignalType
    auto_type: SignalType
    values: np.ndarray        # float64 ; NaN = cellule vide ou invalide
    missing: np.ndarray       # bool : cellule VIDE dans le CSV
    invalid: np.ndarray       # bool : cellule non vide incompatible avec le type
    categories: list[str] = field(default_factory=list)   # pour TEXTE : code -> libellé

    def format_value(self, value: float) -> str:
        """Valeur lisible pour les curseurs et rapports."""
        if not np.isfinite(value):
            return "—"
        if self.type is SignalType.BOOL:
            return "1 (vrai)" if value >= 0.5 else "0 (faux)"
        if self.type is SignalType.TEXT:
            code = int(value)
            return self.categories[code] if 0 <= code < len(self.categories) else "?"
        return f"{value:.6g}"


def auto_type(column: RawColumn) -> SignalType:
    """Type proposé automatiquement pour une colonne (règle du module)."""
    n_number = column.count(KIND_NUMBER)
    n_bool = column.count(KIND_BOOL)
    n_text = column.count(KIND_TEXT)
    filled = n_number + n_bool + n_text
    if filled == 0:
        return SignalType.FLOAT
    if n_text * 2 >= filled:
        return SignalType.TEXT
    if n_bool > 0 and (n_number == 0 or column.binary_numbers):
        return SignalType.BOOL
    if n_bool == 0 and n_number > 0 and column.binary_numbers and column.has_zero and column.has_one:
        return SignalType.BOOL
    return SignalType.FLOAT


def interpret(column: RawColumn, signal_type: SignalType | None = None) -> SignalData:
    """Interprète une colonne brute selon le type demandé (auto si None)."""
    automatic = auto_type(column)
    chosen = signal_type or automatic
    kinds = column.kinds
    missing = kinds == KIND_EMPTY
    if chosen is SignalType.TEXT:
        # Les nombres d'une colonne d'états deviennent eux aussi des libellés.
        categories = list(column.categories)
        values = np.full(len(kinds), np.nan)
        if column.codes is not None:
            is_text = kinds == KIND_TEXT
            values[is_text] = column.codes[is_text]
        lookup = {label: code for code, label in enumerate(categories)}
        other = (kinds == KIND_NUMBER) | (kinds == KIND_BOOL)
        if other.any():
            for position in np.flatnonzero(other):
                label = _number_label(column.values[position], kinds[position])
                values[position] = lookup.setdefault(label, len(lookup))
            categories = sorted(lookup, key=lookup.get)
        return SignalData(column.name, chosen, automatic, values, missing,
                          np.zeros(len(kinds), dtype=bool), categories)
    values = column.values.copy()
    invalid = kinds == KIND_TEXT
    if chosen is SignalType.BOOL:
        # Un nombre autre que 0/1 n'est pas un booléen : invalide, pas arrondi.
        not_binary = (kinds == KIND_NUMBER) & (values != 0.0) & (values != 1.0)
        invalid = invalid | not_binary
    values[invalid] = np.nan
    return SignalData(column.name, chosen, automatic, values, missing, invalid)


def _number_label(value: float, kind: int) -> str:
    if kind == KIND_BOOL:
        return "true" if value else "false"
    return f"{value:g}"


@dataclass
class BinaryGroup:
    """Groupe de signaux binaires (REQ_COMMON_KH_2201, 2e occurrence).

    ``members`` est ordonné : le 1er membre est le bit de poids faible (bit 0)
    du mot affiché dans les lectures de curseur.
    """
    name: str
    members: list[str]
    automatic: bool = False   # détecté par le nom (ex. VANNE[0], VANNE[1])

    def word(self, member_values: list[np.ndarray]) -> np.ndarray:
        """Valeur entière du mot binaire par échantillon (NaN si un bit manque)."""
        if not member_values:
            return np.empty(0)
        word = np.zeros(len(member_values[0]))
        for bit, values in enumerate(member_values):
            word = word + np.where(values >= 0.5, 1.0, 0.0) * (1 << bit)
            word[~np.isfinite(values)] = np.nan
        return word


_INDEXED_NAME = re.compile(r"^(?P<base>.+?)(?:\[(?P<i1>\d+)\]|\.(?P<i2>\d+))$")


def detect_indexed_groups(signals: dict[str, SignalData]) -> list[BinaryGroup]:
    """Propose un groupe pour les Bool nommés « BASE[i] » ou « BASE.i ».

    Au moins deux bits sont nécessaires. Les bits sont rangés par indice.
    """
    found: dict[str, list[tuple[int, str]]] = {}
    for name, signal in signals.items():
        match = _INDEXED_NAME.match(name)
        if match and signal.type is SignalType.BOOL:
            index = int(match.group("i1") or match.group("i2"))
            found.setdefault(match.group("base"), []).append((index, name))
    return [BinaryGroup(base, [name for _, name in sorted(bits)], automatic=True)
            for base, bits in found.items() if len(bits) >= 2]
