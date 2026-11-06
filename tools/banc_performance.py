"""Banc de performance sur des fichiers CSV PTBG réels (REQ_COMMON_KH_2310, 4105).

Usage (avec le même interpréteur que l'outil, par exemple dans la console Spyder) :

    python tools/banc_performance.py fichier1.csv [fichier2.csv ...]
    python tools/banc_performance.py --generer 500 [--colonnes 21] [--dossier D]

Pour chaque fichier : taille, lignes, colonnes, durée de lecture du CSV, de la
conversion et de l'analyse de la base de temps, de l'interprétation des
variables, débit (Mo/s) et mémoire du processus. ``--generer N`` crée d'abord
un fichier de synthèse d'environ N Mo (compteur 10 ms, Float et Bool true/false)
pour mesurer la taille maximale tenable par le poste. Sert à fixer la valeur
de REQ 2310 (préférence ``max_file_size_mb``) : copier la sortie dans la fiche
d'essai (docs/COMPATIBILITE_OS.md § 5). Rien n'est installé ni modifié.
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np  # noqa: E402

from ptbg.config import Settings  # noqa: E402
from ptbg.core.csv_reader import CsvReadError, read_csv  # noqa: E402
from ptbg.core.data_package import SourceFile, configure_time  # noqa: E402
from ptbg.system.compat import process_memory_mb  # noqa: E402
from ptbg.system.environment import collect_environment  # noqa: E402
from ptbg.version import full_name  # noqa: E402


def generate(target: Path, size_mb: float, columns: int) -> Path:
    """Écrit un CSV de synthèse d'environ ``size_mb`` Mo (moitié Float, moitié Bool)."""
    rng = np.random.default_rng(2310)
    floats = columns // 2
    bools = columns - 1 - floats
    header = ["t_ms"] + [f"F{i}" for i in range(floats)] + [f"B{i}" for i in range(bools)]
    written, start, block = 0, 0, 20_000
    with target.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(",".join(header) + "\n")
        while written < size_mb * 1048576:
            times = (start + np.arange(block)) * 10
            cells = [[str(t) for t in times]]
            cells += [[f"{v:.4f}" for v in 50 + rng.normal(0, 5, block)] for _ in range(floats)]
            cells += [["true" if v else "false" for v in rng.random(block) < 0.5] for _ in range(bools)]
            text = "\n".join(",".join(row) for row in zip(*cells)) + "\n"
            handle.write(text)
            written += len(text)
            start += block
    return target


def measure(path: Path, settings: Settings) -> str:
    """Lit, convertit et analyse un fichier ; renvoie la ligne de résultat."""
    size_mb = path.stat().st_size / 1048576
    start = time.perf_counter()
    try:
        table = read_csv(path, settings.max_file_size_mb)
    except CsvReadError as exc:
        return f"{path.name} : illisible — {exc}"
    read_s = time.perf_counter() - start
    source = SourceFile(path)
    source.table, source.read_issues = table, list(table.issues)
    configure_time(source, settings)
    time_s = time.perf_counter() - start - read_s
    for name in source.variable_names():
        source.signal(name)
    source.data_issues()
    total_s = time.perf_counter() - start
    current, peak = process_memory_mb()
    memory = "inconnue" if current is None else f"{current:.0f} Mo (max. {peak:.0f} Mo)"
    return (f"{path.name} : {size_mb:.1f} Mo, {table.n_samples} lignes × {len(table.header)} colonnes\n"
            f"    lecture {read_s:.2f} s ; base de temps {time_s:.2f} s ; variables "
            f"{total_s - read_s - time_s:.2f} s ; TOTAL {total_s:.2f} s ({size_mb / total_s:.1f} Mo/s)\n"
            f"    statut {source.status().label} ; mémoire du processus {memory}")


def main(arguments: list[str]) -> int:
    """Mesure les fichiers donnés (ou un fichier généré) ; renvoie le code de sortie."""
    settings = Settings.load()
    settings.max_file_size_mb = max(settings.max_file_size_mb, 100_000.0)   # mesure sans plafond
    paths = [Path(a) for a in arguments if not a.startswith("--") and a.lower().endswith(".csv")]
    if "--generer" in arguments:
        size = float(arguments[arguments.index("--generer") + 1])
        columns = int(arguments[arguments.index("--colonnes") + 1]) if "--colonnes" in arguments else 21
        folder = Path(arguments[arguments.index("--dossier") + 1]) if "--dossier" in arguments \
            else Path(tempfile.gettempdir())
        print(f"Génération d'un fichier de {size:g} Mo ({columns} colonnes)…")
        paths.append(generate(folder / f"banc_{size:g}Mo_{columns}col.csv", size, columns))
    if not paths:
        print(__doc__)
        return 2
    report = collect_environment()
    print(f"Banc de performance — {full_name()}\nPython {report.python_version} — {report.os_description} — "
          + ", ".join(f"{p.name} {p.installed}" for p in report.packages if p.name in ("numpy", "matplotlib")))
    for path in paths:
        print(measure(path, settings))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
