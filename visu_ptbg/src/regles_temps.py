"""Règles centralisées du diagnostic temporel VISU PTBG.

Toutes les valeurs sans unité sont explicitement des rapports ou des nombres
d'intervalles. Les valeurs absolues sont calculées dans l'unité native du CSV.
Ce module utilise uniquement la bibliothèque standard de Python 3.11.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReglesTemps:
    """Paramètres techniques communs, séparés des choix saisis par l'utilisateur."""

    # Rapport sans unité utilisé seulement quand aucun pas/tolérance n'est saisi.
    tolerance_relative_inference: Decimal = Decimal("0.05")
    # Une autre fréquence doit persister ; un seul grand Δt reste un événement isolé.
    intervalles_min_changement_frequence: int = 3
    # Rapport sans unité servant à regrouper les Δt d'une fréquence alternative.
    tolerance_relative_frequence: Decimal = Decimal("0.05")
    # Limite d'affichage, jamais limite du comptage complet.
    exemples_maximum: int = 50

    def valider(self) -> None:
        """Refuser une configuration incohérente avant toute analyse."""
        if not Decimal("0") <= self.tolerance_relative_inference < Decimal("1"):
            raise ValueError("La tolérance relative d'inférence doit être comprise entre 0 et 1.")
        if not Decimal("0") <= self.tolerance_relative_frequence < Decimal("1"):
            raise ValueError("La tolérance relative de fréquence doit être comprise entre 0 et 1.")
        if self.intervalles_min_changement_frequence < 2:
            raise ValueError("Un changement de fréquence exige au moins deux intervalles.")
        if self.exemples_maximum < 1:
            raise ValueError("La limite d'exemples doit être positive.")


REGLES_TEMPS = ReglesTemps()

# Vocabulaire commun aux journaux et à la future vue du Lot 2B.
NIVEAUX_GRAVITE = ("INFO", "WARNING", "ERROR", "BLOCKING")
GRAVITE_ANOMALIE_TEMPORELLE = {
    "timestamp_invalide": "ERROR",
    "interruption_lecture": "ERROR",
    "temps_duplique": "WARNING",
    "retour_arriere": "ERROR",
    "jitter": "WARNING",
    "trou_probable": "WARNING",
    "changement_frequence_probable": "WARNING",
}

