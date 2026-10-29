"""Identité de l'outil : nom, version, date et document de spécification.

Ces constantes sont affichées dans la section Information (REQ_COMMON_KH_5101),
la barre d'état (REQ_COMMON_KH_5102) et l'en-tête des rapports
(REQ_COMMON_KH_6005). Toute livraison doit incrémenter ``TOOL_VERSION`` et
ajouter une entrée dans ``CHANGELOG.md``.
"""

TOOL_NAME = "VISU PTBG"
TOOL_VERSION = "2.5.1"
TOOL_DATE = "2026-10-29"

# Document de référence des requis implémentés.
SPECIFICATION = "NCS/00/I/COMMON----/ES/010 Rev. A (13/10/2026)"

# Plus ancienne version de Python sur laquelle le code est vérifié.
# Voir docs/DEPENDANCES.md pour la matrice complète (REQ_COMMON_KH_3001).
MIN_PYTHON = (3, 10)


def full_name() -> str:
    """Retourne « VISU PTBG 2.5.1 », utilisé dans les titres et rapports."""
    return f"{TOOL_NAME} {TOOL_VERSION}"
