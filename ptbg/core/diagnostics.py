"""Niveaux de gravité et constats partagés par la lecture et la base de temps.

Un « constat » (Issue) décrit un écart observé dans un fichier : il porte la
gravité, un message en clair, la ligne physique du CSV quand elle est connue
et le requis concerné. L'interface et le rapport n'inventent jamais de
gravité : ils affichent celle calculée ici.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


class Severity(IntEnum):
    """Gravité ordonnée : max() donne la gravité globale d'une liste."""
    OK = 0
    INFO = 1
    WARNING = 2
    ERROR = 3

    @property
    def label(self) -> str:
        return {0: "OK", 1: "INFO", 2: "AVERTISSEMENT", 3: "ERREUR"}[int(self)]


@dataclass(frozen=True)
class Issue:
    """Constat sur un fichier ou sa base de temps."""
    severity: Severity
    message: str
    line: int | None = None          # ligne physique du CSV (1 = en-tête)
    requirement: str | None = None   # ex. "REQ_COMMON_KH_2301" (traçabilité, non affiché)

    def as_text(self) -> str:
        """Texte affiché : gravité, message, ligne du CSV (le requis n'est pas écrit à l'écran)."""
        where = f" (ligne {self.line})" if self.line is not None else ""
        return f"{self.severity.label} : {self.message}{where}"


def worst(severities) -> Severity:
    """Gravité la plus élevée d'une suite (OK si vide)."""
    return max(severities, default=Severity.OK)
