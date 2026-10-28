"""Paquets de données, fichiers sources et axe des temps commun.

Requis couverts :

- REQ_COMMON_KH_2101 / 2103 / 2105 : un système de plusieurs PLC produit un
  fichier par PLC avec son propre horodatage ; un paquet contient un ou
  plusieurs fichiers ;
- REQ_COMMON_KH_2102 : PLC synchronisés ou non : chaque fichier garde SA base
  de temps ; l'alignement se fait par l'origine absolue ou un décalage manuel
  explicite (jamais en silence) ;
- REQ_COMMON_KH_5200 / 5201 : niveau 1 de l'arbre = paquet de données (le
  paquet actif reçoit les fichiers ouverts), niveau 2 = fichiers CSV ;
- REQ_COMMON_KH_5202 / 5203 : variables typées et base de temps par fichier ;
- REQ_COMMON_KH_4105 : un fichier illisible est conservé avec son diagnostic
  sans empêcher le chargement ni l'analyse des autres.
"""
from __future__ import annotations

import traceback
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ptbg.config import Settings
from ptbg.core.csv_reader import KIND_EMPTY, KIND_NONFINITE, CsvReadError, CsvTable, ReadCancelled, read_csv
from ptbg.core.diagnostics import Issue, Severity, worst
from ptbg.core.signals import BinaryGroup, SignalData, SignalType, detect_indexed_groups, interpret
from ptbg.core.sampling import is_sorted
from ptbg.core.time_base import DT_MISSING, TimeBaseAnalysis, analyze
from ptbg.core.time_parser import NS_PER_S, TimeBaseSettings, TimeConversion, convert_time_column, format_absolute


@dataclass
class SourceFile:
    """Un fichier CSV (une source PLC) et tout ce qui en est déduit."""
    path: Path
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    table: CsvTable | None = None
    read_issues: list[Issue] = field(default_factory=list)
    time_settings: TimeBaseSettings = field(default_factory=TimeBaseSettings)
    conversion: TimeConversion | None = None
    analysis: TimeBaseAnalysis | None = None
    type_overrides: dict[str, SignalType] = field(default_factory=dict)
    groups: dict[str, BinaryGroup] = field(default_factory=dict)
    revision: int = 0          # incrémenté à chaque changement (invalide les caches)
    _signals: dict[str, SignalData] = field(default_factory=dict, repr=False)
    _x_cache: tuple | None = field(default=None, repr=False)   # (clé, abscisses, triées ?)
    _data_issues: tuple | None = field(default=None, repr=False)  # (révision, constats)

    # ------------------------------------------------------------ identité
    @property
    def name(self) -> str:
        return self.path.name

    @property
    def is_loaded(self) -> bool:
        return self.table is not None and self.analysis is not None

    @property
    def sha256(self) -> str:
        return self.table.sha256 if self.table else ""

    # --------------------------------------------------------------- statut
    def time_issues(self) -> list[Issue]:
        return list(self.conversion.issues) if self.conversion else []

    def time_status(self) -> Severity:
        """Statut de la BASE DE TEMPS (conditionne le masquage du TBM, REQ 4103)."""
        if not self.is_loaded:
            return Severity.ERROR
        return worst([self.analysis.status] + [issue.severity for issue in self.time_issues()])

    def data_issues(self) -> list[Issue]:
        """Constats sur les valeurs, par variable : cellules vides, nombres non
        finis (« nan », « inf »), valeurs incompatibles avec le type. Mis en
        cache par révision (l'arbre les consulte à chaque rafraîchissement)."""
        if not self.table:
            return []
        if self._data_issues is None or self._data_issues[0] != self.revision:
            self._data_issues = (self.revision, self._compute_data_issues())
        return self._data_issues[1]

    def _compute_data_issues(self) -> list[Issue]:
        """Calcul des constats de ``data_issues``."""
        def listing(pairs):
            """« nom (nombre), … » limité à 8 variables."""
            text = ", ".join(f"{name} ({count})" for name, count in pairs[:8])
            return text + (f" et {len(pairs) - 8} autre(s)" if len(pairs) > 8 else "")

        columns = self.table.columns
        issues = []
        empty = [(c.name, c.count(KIND_EMPTY)) for c in columns if c.count(KIND_EMPTY)]
        if empty:
            issues.append(Issue(Severity.WARNING, f"Cellules vides : {listing(empty)}. Elles restent vides "
                                "(aucune valeur inventée) et sont encadrées de croix sur les courbes.",
                                requirement="REQ_COMMON_KH_4101"))
        nonfinite = [(c.name, c.count(KIND_NONFINITE)) for c in columns if c.count(KIND_NONFINITE)]
        if nonfinite:
            issues.append(Issue(Severity.WARNING, f"Valeurs non numériques « nan » / « inf » : {listing(nonfinite)}. "
                                "Traitées comme des valeurs absentes.", requirement="REQ_COMMON_KH_4101"))
        invalid = [(c.name, int(np.count_nonzero(self.signal(c.name).invalid))) for c in columns]
        invalid = [(f"{name} : {self.signal(name).type.value}", count) for name, count in invalid if count]
        if invalid:
            issues.append(Issue(Severity.WARNING, f"Valeurs incompatibles avec le type : {listing(invalid)}. "
                                "Non tracées ; type modifiable par clic droit sur la variable.",
                                requirement="REQ_COMMON_KH_4101"))
        return issues

    def all_issues(self) -> list[Issue]:
        return self.read_issues + self.time_issues() + self.data_issues()

    def status(self) -> Severity:
        """Statut global du fichier (icône de l'arbre)."""
        return worst([self.time_status()] + [issue.severity for issue in self.all_issues()])

    # ------------------------------------------------------------ variables
    def variable_names(self) -> list[str]:
        return [column.name for column in self.table.columns] if self.table else []

    def signal(self, name: str) -> SignalData:
        """Variable interprétée selon son type (auto ou forcé), mise en cache."""
        if name not in self._signals:
            column = next(c for c in self.table.columns if c.name == name)
            # Lignes à horodatage illisible exclues du choix automatique du type.
            ignore = self.conversion.invalid if self.conversion is not None else None
            self._signals[name] = interpret(column, self.type_overrides.get(name), ignore)
        return self._signals[name]

    def set_type(self, name: str, signal_type: SignalType | None) -> None:
        """Force le type d'une variable (None = revenir au type automatique)."""
        if signal_type is None:
            self.type_overrides.pop(name, None)
        else:
            self.type_overrides[name] = signal_type
        self._signals.pop(name, None)
        self.revision += 1

    def bool_names(self) -> list[str]:
        return [n for n in self.variable_names() if self.signal(n).type is SignalType.BOOL]

    def float_names(self) -> list[str]:
        return [n for n in self.variable_names() if self.signal(n).type is SignalType.FLOAT]

    # ---------------------------------------------------------------- temps
    def display_seconds(self) -> np.ndarray:
        """Temps relatif affiché : brut (par défaut) ou régularisé (option « jitter
        ignoré », REQ 4107), plus le décalage manuel éventuel. Un horodatage
        aberrant isolé n'est pas placé sur l'axe (il est signalé dans le TBM)."""
        base = self.analysis.regular_s if self.time_settings.ignore_jitter else self.conversion.seconds
        seconds = base + float(self.time_settings.offset_s or 0.0)
        seconds[self.analysis.excluded] = np.nan      # horodatages aberrants : non placés
        return seconds

    def gap_starts(self) -> np.ndarray:
        """Indices des échantillons qui suivent un trou de données (rupture de courbe)."""
        analysis = self.analysis
        return analysis.dt_index[analysis.dt_kinds == DT_MISSING] if analysis else np.empty(0, int)

    def line_of(self, index: int) -> int:
        """Ligne physique du CSV pour un indice d'échantillon."""
        return int(self.table.line_numbers[index])


def configure_time(source: SourceFile, settings: Settings,
                   time_settings: TimeBaseSettings | None = None) -> None:
    """(Re)calcule conversion et analyse de la base de temps (REQ 4106).

    Rapide : la colonne de temps brute est conservée, le fichier n'est pas relu.
    """
    if time_settings is not None:
        source.time_settings = time_settings
    ts = source.time_settings
    source.conversion = convert_time_column(source.table.time_raw, source.table.time_name, ts,
                                            settings.default_counter_unit)
    tolerance = ts.tolerance_pct if ts.tolerance_pct is not None else settings.tolerance_pct
    source.analysis = analyze(source.conversion.seconds, ts.nominal_period_s, tolerance,
                              settings.frequency_change_min_run, settings.max_stored_events,
                              settings.preferred_periods_ms)
    source._signals.clear()          # le type automatique dépend des horodatages lisibles
    source.revision += 1


def load_source(path, settings: Settings, progress=None, cancel=None,
                time_settings: TimeBaseSettings | None = None,
                file_id: str | None = None) -> SourceFile:
    """Lit, convertit et analyse un fichier. Un fichier illisible est renvoyé
    avec ses constats (``is_loaded`` faux) au lieu de lever une exception.
    ``file_id`` permet de garder l'identifiant d'un projet rouvert."""
    source = SourceFile(Path(path))
    if file_id:
        source.id = file_id
    if time_settings is not None:
        source.time_settings = time_settings
    try:
        source.table = read_csv(source.path, settings.max_file_size_mb, progress, cancel)
        source.read_issues = list(source.table.issues)
        configure_time(source, settings)
        for group in detect_indexed_groups({n: source.signal(n) for n in source.variable_names()}):
            source.groups[group.name] = group
    except CsvReadError as exc:
        source.table, source.read_issues = None, exc.issues
    except ReadCancelled:
        raise
    except OSError as exc:            # disque réseau perdu, fichier verrouillé ou supprimé...
        source.table, source.analysis = None, None
        source.read_issues = [Issue(Severity.ERROR, f"Lecture interrompue : {exc}")]
    except MemoryError:
        source.table, source.analysis = None, None
        source.read_issues = [Issue(Severity.ERROR, "Mémoire insuffisante pour ce fichier : réduire sa "
                                    "taille ou fermer d'autres fichiers.", requirement="REQ_COMMON_KH_2310")]
    except Exception as exc:  # noqa: BLE001 - REQ 4105 : un fichier ne bloque jamais les autres
        source.table, source.analysis = None, None
        where = traceback.extract_tb(exc.__traceback__)[-1]     # pour la maintenance
        source.read_issues = [Issue(Severity.ERROR, f"Erreur inattendue pendant l'analyse : "
                                    f"{type(exc).__name__} : {exc} ({Path(where.filename).name}:{where.lineno})")]
    return source


@dataclass
class DataPackage:
    """Paquet de données : niveau supérieur de l'arbre (REQ 5200)."""
    name: str
    files: list[SourceFile] = field(default_factory=list)
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])

    def status(self) -> Severity:
        return worst(source.status() for source in self.files)


@dataclass(frozen=True)
class Timeline:
    """Axe des temps commun aux courbes affichées.

    - ``relative`` : chaque fichier sur son temps relatif (0 = 1re mesure, ou
      instant de déclenchement pour un compteur avec pré-déclenchement) ;
    - ``absolute`` : chaque fichier placé à son horodatage absolu (REQ 4107),
      x = secondes depuis ``ref_ns`` ; les PLC synchronisés s'alignent alors
      naturellement (REQ 2102).
    """
    mode: str = "relative"
    ref_ns: int | None = None
    with_date: bool = True

    @property
    def is_absolute(self) -> bool:
        return self.mode == "absolute" and self.ref_ns is not None

    def x(self, source: SourceFile) -> np.ndarray:
        """Abscisses (s) des échantillons d'un fichier sur cet axe (mises en cache
        tant que le fichier et l'axe ne changent pas : lecture fluide des curseurs)."""
        return self._cached(source)[0]

    def x_sorted(self, source: SourceFile) -> bool:
        """Vrai si les abscisses du fichier sont croissantes (dichotomie possible)."""
        return self._cached(source)[1]

    def _cached(self, source: SourceFile) -> tuple[np.ndarray, bool]:
        key = (source.revision, self.mode, self.ref_ns)
        if source._x_cache is None or source._x_cache[0] != key:
            seconds = source.display_seconds()
            if self.is_absolute and source.conversion.origin_ns is not None:
                seconds = seconds + (source.conversion.origin_ns - self.ref_ns) / NS_PER_S
            source._x_cache = (key, seconds, is_sorted(seconds))
        return source._x_cache[1], source._x_cache[2]

    def format(self, x: float, digits: int = 6) -> str:
        """Instant lisible pour les curseurs, le panneau de lecture et le PDF."""
        if not np.isfinite(x):
            return "—"
        if self.is_absolute:
            return format_absolute(self.ref_ns + int(round(x * NS_PER_S)), digits, self.with_date)
        return f"{x:.{digits}f} s"


class Workspace:
    """Ensemble des paquets ouverts et choix de l'axe des temps."""

    def __init__(self) -> None:
        self.packages: list[DataPackage] = [DataPackage("Paquet de données 1")]
        self.active_index = 0
        self.time_mode = "relative"
        self._ref_ns: int | None = None

    @property
    def active_package(self) -> DataPackage:
        return self.packages[self.active_index]

    def add_package(self, name: str | None = None) -> DataPackage:
        package = DataPackage(name or f"Paquet de données {len(self.packages) + 1}")
        self.packages.append(package)
        self.active_index = len(self.packages) - 1
        return package

    def files(self) -> list[SourceFile]:
        return [source for package in self.packages for source in package.files]

    def loaded_files(self) -> list[SourceFile]:
        return [source for source in self.files() if source.is_loaded]

    def find(self, file_id: str) -> SourceFile | None:
        return next((source for source in self.files() if source.id == file_id), None)

    def package_of(self, source: SourceFile) -> DataPackage | None:
        return next((p for p in self.packages if source in p.files), None)

    def remove_file(self, source: SourceFile) -> None:
        for package in self.packages:
            if source in package.files:
                package.files.remove(source)
        if not self.loaded_files():
            self._ref_ns = None

    def remove_package(self, package: DataPackage) -> None:
        self.packages.remove(package)
        if not self.packages:
            self.packages.append(DataPackage("Paquet de données 1"))
        self.active_index = min(self.active_index, len(self.packages) - 1)

    def absolute_available(self) -> bool:
        """L'axe absolu exige une origine absolue pour CHAQUE fichier chargé."""
        loaded = self.loaded_files()
        return bool(loaded) and all(s.conversion.origin_ns is not None for s in loaded)

    def timeline(self) -> Timeline:
        """Axe courant. La référence absolue est figée à la 1re demande pour que
        l'ajout d'un fichier ne déplace pas les curseurs déjà posés."""
        if self.time_mode == "absolute" and self.absolute_available():
            loaded = self.loaded_files()
            if self._ref_ns is None:
                self._ref_ns = min(s.conversion.origin_ns for s in loaded)
            return Timeline("absolute", self._ref_ns, all(s.conversion.date_known for s in loaded))
        return Timeline("relative")

    def set_time_mode(self, mode: str) -> None:
        self.time_mode = mode
        self._ref_ns = None
