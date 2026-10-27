"""Résolution d'une courbe (``CurveRef``) en données affichables et lisibles.

Une courbe est soit une variable d'un fichier, soit un groupe binaire
(REQ_COMMON_KH_2201, 2e occurrence) dont la « valeur » est le mot formé par
ses bits. Ce module évite de dupliquer cette distinction dans le rendu, les
curseurs et le rapport.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ptbg.core.arrangement import CurveRef
from ptbg.core.data_package import SourceFile, Workspace
from ptbg.core.signals import SignalData, SignalType

# Mots binaires déjà calculés : (fichier, révision, groupe, membres) -> valeurs.
# Évite de recalculer un mot à chaque mouvement de souris en mode suivi.
_GROUP_WORDS: dict = {}


@dataclass
class CurveData:
    """Données d'une courbe prête à dessiner et à lire (variable ou groupe binaire)."""

    ref: CurveRef
    source: SourceFile
    signal_type: SignalType
    values: np.ndarray                       # variable, ou mot binaire du groupe
    signal: SignalData | None = None         # variable simple
    members: list[SignalData] = field(default_factory=list)   # groupe binaire

    @property
    def label(self) -> str:
        prefix = "Groupe " if self.ref.is_group else ""
        return f"{prefix}{self.ref.name} [{self.source.name}]"

    @property
    def hold(self) -> bool:
        """Lecture « état maintenu » pour les signaux logiques (voir sampling)."""
        return self.signal_type.is_digital

    def format_at(self, index: int) -> str:
        """Valeur lisible de l'échantillon ``index``."""
        if self.signal is not None:
            return self.signal.format_value(self.values[index])
        bits = [member.values[index] for member in self.members]
        if not all(np.isfinite(bits)):
            return "— (bit manquant)"
        text = " ".join(f"{m.name}={int(b >= 0.5)}" for m, b in zip(self.members, bits))
        return f"mot {int(self.values[index])} : {text}"


def resolve(ref: CurveRef, workspace: Workspace) -> CurveData | None:
    """Données d'une courbe, ou None si son fichier/variable n'existe plus."""
    source = workspace.find(ref.file_id)
    if source is None or not source.is_loaded:
        return None
    if ref.is_group:
        group = source.groups.get(ref.name)
        if group is None:
            return None
        members = [source.signal(name) for name in group.members if name in source.variable_names()]
        key = (source.id, source.revision, group.name, tuple(group.members))
        if key not in _GROUP_WORDS:
            if len(_GROUP_WORDS) > 64:
                _GROUP_WORDS.clear()
            _GROUP_WORDS[key] = group.word([m.values for m in members])
        return CurveData(ref, source, SignalType.BOOL, _GROUP_WORDS[key], members=members)
    if ref.name not in source.variable_names():
        return None
    signal = source.signal(ref.name)
    return CurveData(ref, source, signal.type, signal.values, signal=signal)
