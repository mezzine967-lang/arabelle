"""Relevé et contrôle de l'environnement d'exécution (REQ_COMMON_KH_3004, 3005).

Usage (avec le même interpréteur que l'outil, par exemple dans la console Spyder) :

    python tools/audit_environnement.py            # rapport lisible
    python tools/audit_environnement.py --json f   # rapport + fichier JSON archivable

Le rapport liste Python (version, 32/64 bits), le système, Tcl/Tk et chaque
bibliothèque directe ou transitive : version installée, version figée dans
requirements.txt, statut (OK / différente / hors plage testée / absente).
Rien n'est installé ni modifié. Code de sortie 1 si un module indispensable
(tkinter, numpy, matplotlib) manque.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from ptbg.system.environment import collect_environment, missing_runtime_modules  # noqa: E402
from ptbg.version import full_name  # noqa: E402


def main(arguments: list[str]) -> int:
    """Affiche le relevé, l'écrit en JSON si demandé ; renvoie le code de sortie."""
    report = collect_environment()
    missing = missing_runtime_modules()
    print(f"Audit d'environnement — {full_name()}\n")
    print(report.as_text())
    if missing:
        print(f"\nMODULES INDISPENSABLES ABSENTS : {', '.join(missing)}")
    if "--json" in arguments:
        target = Path(arguments[arguments.index("--json") + 1])
        target.write_text(json.dumps({"tool": full_name(), "missing": missing, **asdict(report)},
                                     indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"\nRelevé JSON écrit : {target}")
    return 1 if missing else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
