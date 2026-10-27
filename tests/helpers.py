"""Outils communs aux tests : fichiers CSV temporaires et chemins du projet."""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Les journaux et préférences des tests ne doivent pas polluer le poste.
_SANDBOX = Path(tempfile.mkdtemp(prefix="visu_ptbg_tests_"))
os.environ.setdefault("XDG_STATE_HOME", str(_SANDBOX / "state"))
os.environ.setdefault("XDG_CONFIG_HOME", str(_SANDBOX / "config"))
os.environ.setdefault("MPLBACKEND", "Agg")

EXAMPLES = ROOT / "data" / "exemples"
DEMO = ROOT / "data" / "demo"


class TempFiles:
    """Crée des fichiers dans un dossier temporaire supprimé en fin de test."""

    def __init__(self) -> None:
        self._dir = tempfile.TemporaryDirectory(prefix="visu_ptbg_")
        self.path = Path(self._dir.name)

    def write(self, name: str, content, encoding: str = "utf-8") -> Path:
        target = self.path / name
        if isinstance(content, bytes):
            target.write_bytes(content)
        else:
            target.write_text(content, encoding=encoding, newline="")
        return target

    def cleanup(self) -> None:
        self._dir.cleanup()


def counter_csv(times, columns: dict[str, list], time_name: str = "t_ms") -> str:
    """Texte CSV : 1re colonne = temps, puis les colonnes données."""
    header = [time_name] + list(columns)
    lines = [",".join(header)]
    for row, t in enumerate(times):
        lines.append(",".join([str(t)] + [str(values[row]) for values in columns.values()]))
    return "\n".join(lines) + "\n"
