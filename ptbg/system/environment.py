"""Relevé de l'environnement d'exécution (REQ_COMMON_KH_3004, 3005, 5101).

Le requis 3004 impose que chaque bibliothèque soit documentée et alignée sur
la version du « kernel » Python. Ce module :

1. relève la version de Python, l'architecture (32/64 bits), l'OS, Tcl/Tk ;
2. relève la version installée de chaque bibliothèque utilisée, directe ou
   transitive (via ``importlib.metadata``, bibliothèque standard) ;
3. compare ces versions aux plages TESTÉES (``TESTED_RANGES``) et aux versions
   figées de ``requirements.txt``.

Il n'installe et ne met à jour AUCUN paquet : c'est essentiel sous Spyder 6
dont l'environnement (kernel) est figé. Un écart est signalé, jamais corrigé.
"""
from __future__ import annotations

import platform
import re
import struct
import sys
from dataclasses import dataclass, field
from importlib import metadata
from pathlib import Path

from ptbg.system.compat import project_root

# Bibliothèques nécessaires à l'exécution : nom de distribution -> rôle.
# Les deux premières sont des dépendances DIRECTES (importées par le code) ;
# les suivantes sont des dépendances TRANSITIVES de Matplotlib.
RUNTIME_PACKAGES = {
    "numpy": "directe — calcul vectoriel (lecture, base de temps, curseurs)",
    "matplotlib": "directe — courbes, Time Base Monitor, rapport PDF",
    "contourpy": "transitive (matplotlib) — tracé de contours, non utilisé directement",
    "cycler": "transitive (matplotlib) — cycles de styles",
    "fonttools": "transitive (matplotlib) — polices intégrées au PDF",
    "kiwisolver": "transitive (matplotlib) — calcul de mise en page",
    "packaging": "transitive (matplotlib) — comparaison de versions",
    "pillow": "transitive (matplotlib) — images (icônes de la barre d'outils)",
    "pyparsing": "transitive (matplotlib) — analyse du texte mathématique",
    "python-dateutil": "transitive (matplotlib) — dates",
    "six": "transitive (python-dateutil) — compatibilité Python 2/3",
}

# Plages de versions sur lesquelles la suite de tests a été exécutée avec
# succès (bornes incluses, comparaison sur majeur.mineur). Mettre à jour
# APRÈS chaque nouvelle campagne (voir docs/DEPENDANCES.md, section 5).
TESTED_RANGES = {
    "python": ("3.10", "3.14"),
    "numpy": ("1.24", "2.5"),
    "matplotlib": ("3.6", "3.11"),
}


def _version_tuple(text: str) -> tuple[int, ...]:
    """« 2.4.6 » -> (2, 4, 6) ; ignore les suffixes (rc1, .post0...)."""
    numbers = re.findall(r"\d+", text.split("+")[0])
    return tuple(int(n) for n in numbers[:3])


def in_tested_range(name: str, version: str) -> bool:
    """Vrai si la version (majeur.mineur) appartient à la plage testée."""
    bounds = TESTED_RANGES.get(name)
    if not bounds:
        return True
    current = _version_tuple(version)[:2]
    return _version_tuple(bounds[0])[:2] <= current <= _version_tuple(bounds[1])[:2]


@dataclass
class PackageInfo:
    """Version installée d'une bibliothèque et sa conformité."""
    name: str
    role: str
    installed: str | None
    pinned: str | None
    requires_python: str | None
    tested: bool

    @property
    def status(self) -> str:
        if self.installed is None:
            return "ABSENT"
        if self.pinned and self.installed != self.pinned:
            return "DIFFÉRENT DE requirements.txt" if self.tested else "HORS PLAGE TESTÉE"
        return "OK" if self.tested else "HORS PLAGE TESTÉE"


@dataclass
class EnvironmentReport:
    """Photographie de l'environnement affichée dans Information > Sources."""
    python_version: str
    python_executable: str
    python_bits: int
    os_description: str
    tk_version: str
    packages: list[PackageInfo] = field(default_factory=list)

    def python_tested(self) -> bool:
        return in_tested_range("python", platform.python_version())

    def as_text(self) -> str:
        """Rendu texte (fenêtre Information, journal, outil d'audit)."""
        lines = [
            f"Python        : {self.python_version} ({self.python_bits} bits)"
            + ("" if self.python_tested() else "  <-- HORS PLAGE TESTÉE"),
            f"Interpréteur  : {self.python_executable}",
            f"Système       : {self.os_description}",
            f"Tcl/Tk        : {self.tk_version}",
            "",
            f"{'Bibliothèque':<17}{'Installée':<13}{'Figée':<13}{'Statut':<30}Rôle",
        ]
        for pkg in self.packages:
            lines.append(f"{pkg.name:<17}{pkg.installed or '-':<13}{pkg.pinned or '-':<13}"
                         f"{pkg.status:<30}{pkg.role}")
        return "\n".join(lines)


def read_pinned_requirements(path: Path | None = None) -> dict[str, str]:
    """Lit les « nom==version » de requirements.txt (commentaires ignorés)."""
    path = path or project_root() / "requirements.txt"
    pins: dict[str, str] = {}
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            match = re.match(r"^\s*([A-Za-z0-9_.\-]+)\s*==\s*([^\s;#]+)", line)
            if match:
                pins[match.group(1).lower()] = match.group(2)
    except OSError:
        pass
    return pins


def _os_description() -> str:
    """Description lisible de l'OS ; sous Linux, lit /etc/os-release (SLES)."""
    if sys.platform.startswith("linux"):
        try:
            info = platform.freedesktop_os_release()  # Python >= 3.10
            return f"{info.get('PRETTY_NAME', 'Linux')} — noyau {platform.release()}"
        except OSError:
            pass
    return f"{platform.system()} {platform.release()} ({platform.version()})"


def _tk_version() -> str:
    """Version Tcl/Tk sans ouvrir de fenêtre (un interpréteur Tcl suffit)."""
    try:
        import tkinter

        return f"Tk {tkinter.Tcl().eval('info patchlevel')}"
    except Exception as exc:  # noqa: BLE001 - absence de Tk signalée en clair
        return f"indisponible ({exc})"


def collect_environment() -> EnvironmentReport:
    """Construit le relevé complet de l'environnement courant."""
    pins = read_pinned_requirements()
    packages = []
    for name, role in RUNTIME_PACKAGES.items():
        try:
            dist = metadata.distribution(name)
            installed = dist.version
            requires_python = dist.metadata.get("Requires-Python")
        except metadata.PackageNotFoundError:
            installed, requires_python = None, None
        tested = installed is not None and in_tested_range(name, installed)
        packages.append(PackageInfo(name, role, installed, pins.get(name), requires_python, tested))
    return EnvironmentReport(
        python_version=sys.version.split()[0],
        python_executable=sys.executable,
        python_bits=struct.calcsize("P") * 8,
        os_description=_os_description(),
        tk_version=_tk_version(),
        packages=packages,
    )


def tkagg_problem(root) -> str | None:
    """Vérifie que Matplotlib sait dessiner dans la fenêtre Tk, sinon explique pourquoi.

    L'extension TkAgg de Matplotlib dépend de la version de Tcl/Tk : par exemple
    matplotlib 3.6 à 3.8 échoue avec Tk 9.0 (« Failed to load Tcl_SetVar »),
    alors qu'il fonctionne avec Tk 8.6 (Windows python.org, Spyder, SLES).
    """
    try:
        import tkinter
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from matplotlib.figure import Figure

        holder = tkinter.Frame(root)
        canvas = FigureCanvasTkAgg(Figure(figsize=(1, 1), dpi=20), master=holder)
        canvas.draw()
        holder.destroy()
        return None
    except Exception as exc:  # noqa: BLE001 - toute incompatibilité est expliquée
        import matplotlib

        return (f"Matplotlib {matplotlib.__version__} ne peut pas dessiner avec {_tk_version()} : {exc}. "
                "Utiliser les versions de requirements.txt (voir docs/DEPENDANCES.md).")


def missing_runtime_modules() -> list[str]:
    """Modules indispensables absents (vérifié par MAIN.py avant l'IHM)."""
    missing = []
    for module in ("tkinter", "numpy", "matplotlib"):
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    return missing
