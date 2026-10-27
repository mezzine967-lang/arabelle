"""Découvrir les CSV dans un dossier sans supposer leurs noms ou leur rôle."""
from __future__ import annotations

from pathlib import Path


def decouvrir_csv(dossier: str | Path) -> list[Path]:
    """Retourner les fichiers .csv de tout le dossier, triés par chemin relatif.

    Le suffixe est comparé sans tenir compte de la casse. Une sélection vide
    reste vide ; aucun fichier n'est créé, ouvert en écriture ou comparé ici.
    """
    racine = Path(dossier).expanduser().resolve()
    if not racine.is_dir():
        raise NotADirectoryError(f"Dossier CSV introuvable : {racine}")
    return sorted((p for p in racine.rglob("*") if p.is_file() and p.suffix.casefold() == ".csv"),
                  key=lambda p: p.relative_to(racine).as_posix().casefold())
