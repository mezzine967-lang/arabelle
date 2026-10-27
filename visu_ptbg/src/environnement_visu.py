# -----------------------------------------------------------------------------
# VISU PTBG — V00.06.00 — première vue de signal
# Requis concernés : 3004, 3005, 3006 ; périmètre partiel détaillé dans docs.
# Historique : séparation lecture, dessin et intégration dans la fenêtre.
# -----------------------------------------------------------------------------
"""Relever les dépendances observées sans installer ni mettre à jour un module.

REQ_COMMON_KH_3004/3005 : noter Python, OS, architecture, versions et contraintes
déclarées des distributions. Ces observations ne constituent pas une preuve de
compatibilité du futur exécutable. Les marqueurs Requires-Dist restent bruts.
"""
from __future__ import annotations

# === 1. Bibliothèque standard et liste des distributions de la vue graphique ===
import json
import platform
import struct
import sys
from datetime import datetime
from importlib import metadata
from pathlib import Path
from emplacements import dossier_resultats

DISTRIBUTIONS = ("matplotlib", "numpy", "contourpy", "cycler", "fonttools",
                 "kiwisolver", "packaging", "Pillow", "pyparsing", "python-dateutil", "six")


def relever_environnement(version: str, racine_tk=None) -> dict:
    """Collecter les versions réellement présentes dans l'interpréteur courant.

    Tk est relevé sur la fenêtre quand elle existe. Les étiquettes de roues
    Python renseignent ABI/plateforme déclarées ; elles peuvent être absentes
    d'une installation Conda. Aucune compatibilité n'est déduite d'une absence.
    """
    resultat = {
        "visu": version, "date": datetime.now().astimezone().isoformat(),
        "python": platform.python_version(), "interpreteur": sys.executable,
        "os": platform.platform(), "machine": platform.machine(),
        "bits_interpreteur": struct.calcsize("P") * 8,
        "bibliotheque_standard": "Version liée à l'interpréteur Python observé.",
        "backend_voulu": "FigureCanvasTkAgg (figure intégrée, sans pyplot)",
        "tcl": None, "tk": None, "distributions": {},
        "qualification": "Environnement observé ; validation cible et exécutable distinctes.",
    }
    if racine_tk is not None:
        resultat["tcl"] = str(racine_tk.tk.call("info", "patchlevel"))
        resultat["tk"] = str(racine_tk.tk.call("package", "require", "Tk"))
    for nom in DISTRIBUTIONS:
        try:
            distribution = metadata.distribution(nom)
            roue = distribution.read_text("WHEEL") or ""
            resultat["distributions"][nom] = {
                "version": distribution.version,
                "requires_python": distribution.metadata.get("Requires-Python"),
                "requires_dist": distribution.requires or [],
                "tags_roue": [ligne[5:] for ligne in roue.splitlines() if ligne.startswith("Tag: ")],
            }
        except metadata.PackageNotFoundError:
            resultat["distributions"][nom] = {"version": None, "etat": "métadonnées absentes"}
    return resultat


# === 2. Preuve datée, distincte des données d'entrée ===
def enregistrer_environnement(projet: Path, version: str, racine_tk=None) -> Path:
    """Sauvegarder le relevé JSON ; laisser l'appelant signaler un refus d'écriture."""
    # `projet` est conservé pour les appelants historiques. Une installation
    # peut être en lecture seule : le relevé va dans le dossier utilisateur.
    dossier = dossier_resultats()
    dossier.mkdir(parents=True, exist_ok=True)
    chemin = dossier / f"environnement_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
    with chemin.open("x", encoding="utf-8") as flux:
        json.dump(relever_environnement(version, racine_tk), flux, ensure_ascii=False, indent=2)
    return chemin
