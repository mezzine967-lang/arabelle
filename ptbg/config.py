"""Préférences de l'outil, modifiables par Outils > Préférences.

Les valeurs par défaut ci-dessous sont des CHOIX DOCUMENTÉS, à confirmer
lorsque la spécification les précisera (voir docs/POINTS_OUVERTS.md) :

- ``max_file_size_mb`` : le requis REQ_COMMON_KH_2310 indique « xxxMo » sans
  valeur. 500 Mo est retenu : un CSV de cette taille occupe environ 0,5 à 1 Go
  de mémoire une fois converti (8 octets par valeur numérique) ;
- ``tolerance_pct`` : écart toléré sur la période (jitter accepté, REQ 4107) ;
- ``default_counter_unit`` : unité supposée d'un compteur de temps dont
  l'en-tête ne précise pas l'unité (« index » des CSV d'exemple : ms) ;
- ``frequency_change_min_run`` : nombre d'intervalles consécutifs cohérents
  nécessaires pour déclarer un changement de fréquence (et non une perte).

Le fichier est stocké en JSON dans le dossier utilisateur (voir
system/compat.py) ; un fichier absent ou corrompu redonne les valeurs par
défaut sans bloquer le démarrage.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from ptbg.system.compat import current_user, ensure_dir, user_config_dir


@dataclass
class Settings:
    """Préférences persistantes de l'utilisateur."""

    # --- Fichiers d'entrée (REQ_COMMON_KH_2300 à 2310) ---
    max_file_size_mb: float = 500.0
    # --- Base de temps (REQ_COMMON_KH_4100 à 4107) ---
    tolerance_pct: float = 10.0
    default_counter_unit: str = "ms"
    frequency_change_min_run: int = 10
    preferred_periods_ms: tuple = (10.0, 20.0)  # REQ_COMMON_KH_2100
    max_stored_events: int = 5000
    # --- Affichage ---
    max_points_per_curve: int = 4000  # au-delà : réduction min/max (lisibilité + fluidité)
    # --- En-tête du rapport (REQ_COMMON_KH_6005) ---
    issuer: str = ""
    project_name: str = ""
    project_unit: str = ""
    project_reference: str = ""

    def effective_issuer(self) -> str:
        """Émetteur du rapport : saisi, sinon l'utilisateur de la session."""
        return self.issuer.strip() or current_user()

    # ----------------------------------------------------------------- disque
    @staticmethod
    def default_path() -> Path:
        return user_config_dir() / "settings.json"

    @classmethod
    def load(cls, path: Path | None = None) -> "Settings":
        """Charge les préférences ; ignore les clés inconnues ou invalides."""
        path = path or cls.default_path()
        settings = cls()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return settings
        known = {f.name: f for f in fields(cls)}
        for key, value in data.items():
            if key in known:
                default = getattr(settings, key)
                try:
                    # Conversion vers le type de la valeur par défaut.
                    setattr(settings, key, tuple(value) if isinstance(default, tuple)
                            else type(default)(value))
                except (TypeError, ValueError):
                    pass
        return settings

    def save(self, path: Path | None = None) -> str | None:
        """Enregistre ; renvoie un message d'erreur ou None."""
        path = path or self.default_path()
        if ensure_dir(path.parent) is None:
            return f"Dossier de préférences inaccessible : {path.parent}"
        try:
            path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False),
                            encoding="utf-8")
            return None
        except OSError as exc:
            return f"Préférences non enregistrées : {exc}"
