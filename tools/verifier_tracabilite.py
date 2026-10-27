"""Vérifie que CHAQUE requis du document Word est tracé (aucun requis oublié).

Usage : python tools/verifier_tracabilite.py

Pour chaque identifiant REQ_COMMON_KH_xxxx lu dans
docs/specification/NCS00ICOMMON----ES010_RevA.docx (bibliothèque standard :
zipfile + expressions régulières), le script contrôle qu'il est cité :

1. dans la matrice docs/TRACABILITE_REQUIS.md ;
2. dans le code (ptbg/ ou MAIN.py) — sauf requis purement documentaires ;
3. dans au moins un test (tests/).

Code de sortie 0 si tout est tracé, 1 sinon (utilisable en intégration).
"""
from __future__ import annotations

import re
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "specification" / "NCS00ICOMMON----ES010_RevA.docx"
MATRIX = ROOT / "docs" / "TRACABILITE_REQUIS.md"

# Requis vérifiés par la documentation et les tests d'architecture plutôt que
# par une ligne de code précise (ils portent sur le code lui-même).
DOCUMENTARY = {"REQ_COMMON_KH_3006", "REQ_COMMON_KH_3007"}


def spec_requirements(path: Path = SPEC) -> dict[str, int]:
    """Identifiants du Word et nombre d'occurrences (2201 apparaît deux fois)."""
    xml = zipfile.ZipFile(path).read("word/document.xml").decode("utf-8")
    text = re.sub(r"<[^>]+>", "", xml)
    found: dict[str, int] = {}
    for identifier in re.findall(r"REQ_COMMON_KH_\d{4}", text):
        found[identifier] = found.get(identifier, 0) + 1
    return found


def _mentions(identifier: str, text: str) -> bool:
    """Cité en entier, ou par son numéro dans un contexte « REQ » (ex. « REQ 4103 »)."""
    number = identifier[-4:]
    return identifier in text or re.search(r"REQ[^\n]{0,40}\b" + number + r"\b", text) is not None


def check() -> list[str]:
    """Liste des manques (vide si la traçabilité est complète)."""
    code = "\n".join(p.read_text(encoding="utf-8") for p in list((ROOT / "ptbg").rglob("*.py")) + [ROOT / "MAIN.py"])
    tests = "\n".join(p.read_text(encoding="utf-8") for p in (ROOT / "tests").glob("test_*.py"))
    matrix = MATRIX.read_text(encoding="utf-8") if MATRIX.exists() else ""
    problems = []
    for identifier in spec_requirements():
        if identifier not in matrix:
            problems.append(f"{identifier} absent de docs/TRACABILITE_REQUIS.md")
        if identifier not in DOCUMENTARY and not _mentions(identifier, code):
            problems.append(f"{identifier} non cité dans le code")
        if not _mentions(identifier, tests):
            problems.append(f"{identifier} non couvert par un test")
    return problems


if __name__ == "__main__":
    requirements = spec_requirements()
    problems = check()
    print(f"{len(requirements)} identifiants ({sum(requirements.values())} lignes) dans {SPEC.name}")
    for problem in problems:
        print("  MANQUE :", problem)
    print("Traçabilité complète." if not problems else f"{len(problems)} manque(s).")
    sys.exit(1 if problems else 0)
