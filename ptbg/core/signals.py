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
c'est un booléen, l'utilisateur peut forcer le type. Les nombres écrits
« nan » / « inf » sont des valeurs absentes (comme une cellule vide), pas du
texte. Les lignes dont l'horodatage est illisible (ligne de total, de
commentaire...) ne participent pas au choix du type : elles ne sont pas
tracées et ne doivent pas changer un Bool en Float.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from ptbg.core.csv_reader import KIND_BOOL, KIND_EMPTY, KIND_NONFINITE, KIND_NUMBER, KIND_TEXT, RawColumn


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
    missing: np.ndarray       # bool : cellule VIDE (ou « nan » / « inf ») dans le CSV
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
            return short_label(self.categories[code]) if 0 <= code < len(self.categories) else "?"
        return f"{value:.6g}"


def short_label(text: str, limit: int = 40) -> str:
    """Libellé d'état abrégé pour l'affichage (une cellule peut être démesurée)."""
    return text if len(text) <= limit else text[:limit - 1] + "…"


def auto_type(column: RawColumn, ignore: np.ndarray | None = None) -> SignalType:
    """Type proposé automatiquement pour une colonne (règle du module).

    ``ignore`` : lignes à ne pas prendre en compte (horodatage illisible) ;
    ignoré s'il couvre tout le fichier (base de temps entièrement illisible)."""
    kinds = column.kinds
    binary, has_zero, has_one = column.binary_numbers, column.has_zero, column.has_one
    if ignore is not None and ignore.any() and not ignore.all():
        keep = ~ignore
        kinds = kinds[keep]
        numbers = column.values[keep][kinds == KIND_NUMBER]
        binary = bool(np.all((numbers == 0.0) | (numbers == 1.0)))
        has_zero, has_one = bool(np.any(numbers == 0.0)), bool(np.any(numbers == 1.0))
    n_number = int(np.count_nonzero(kinds == KIND_NUMBER))
    n_bool = int(np.count_nonzero(kinds == KIND_BOOL))
    n_text = int(np.count_nonzero(kinds == KIND_TEXT))
    filled = n_number + n_bool + n_text
    if filled == 0:
        return SignalType.FLOAT
    if n_text * 2 >= filled:
        return SignalType.TEXT
    if n_bool > 0 and (n_number == 0 or binary):
        return SignalType.BOOL
    if n_bool == 0 and n_number > 0 and binary and has_zero and has_one:
        return SignalType.BOOL
    return SignalType.FLOAT


def interpret(column: RawColumn, signal_type: SignalType | None = None,
              ignore: np.ndarray | None = None) -> SignalData:
    """Interprète une colonne brute selon le type demandé (auto si None).

    ``ignore`` est transmis à ``auto_type`` (lignes exclues du choix du type)."""
    automatic = auto_type(column, ignore)
    chosen = signal_type or automatic
    kinds = column.kinds
    missing = (kinds == KIND_EMPTY) | (kinds == KIND_NONFINITE)
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
            # Chaque valeur distincte (par nature) reçoit son libellé une seule fois,
            # dans l'ordre d'apparition ; valeurs comparées bit à bit (« -0 » ≠ « 0 »).
            groups, distinct = [], []
            for kind in (KIND_NUMBER, KIND_BOOL):
                where = np.flatnonzero(kinds == kind)
                if where.size:
                    bits, first, inverse = np.unique(column.values[where].view(np.int64),
                                                     return_index=True, return_inverse=True)
                    codes = np.empty(bits.size)
                    groups.append((where, codes, inverse.reshape(-1)))
                    distinct += [(int(where[f]), kind, b, codes, rank)
                                 for rank, (b, f) in enumerate(zip(bits.view(np.float64).tolist(), first.tolist()))]
            for _, kind, value, codes, rank in sorted(distinct, key=lambda item: item[0]):
                codes[rank] = lookup.setdefault(_number_label(value, kind), len(lookup))
            for where, codes, inverse in groups:
                values[where] = codes[inverse]
            categories = sorted(lookup, key=lookup.get)
        return SignalData(column.name, chosen, automatic, values, missing,
                          np.zeros(len(kinds), dtype=bool), categories)
    values = column.values
    invalid = kinds == KIND_TEXT
    if chosen is SignalType.BOOL:
        # Un nombre autre que 0/1 n'est pas un booléen : invalide, pas arrondi.
        not_binary = (kinds == KIND_NUMBER) & (values != 0.0) & (values != 1.0)
        invalid = invalid | not_binary
    if invalid.any():
        # Copie seulement s'il y a des valeurs à masquer : sinon la variable
        # partage les valeurs lues (non modifiables), sans doubler la mémoire.
        values = values.copy()
        values[invalid] = np.nan
        values.flags.writeable = False
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
