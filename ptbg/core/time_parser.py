"""Conversion de la 1re colonne (base de temps) en secondes.

Requis couverts :

- REQ_COMMON_KH_2304 : la première colonne est TOUJOURS la base de temps ;
- REQ_COMMON_KH_2305 : configuration de l'horodatage (``TimeBaseSettings``) ;
- REQ_COMMON_KH_2306 : heure « hh:mm:ss » avec fraction jusqu'à la
  nanoseconde, écrite « .123456789 » ou par groupes « .123.456.789 » ;
- REQ_COMMON_KH_2307 : compteur de temps (ns, µs, ms, s, min, h ou cycles PLC) ;
- REQ_COMMON_KH_4107 : horodatage absolu = origine absolue + temps relatif.

Remarque du relecteur sur 2305 (« attention au pretrig, temps négatif /
référence absolue ») : un compteur peut être NÉGATIF (échantillons de
pré-déclenchement) ; t = 0 est alors l'instant de déclenchement et l'origine
absolue saisie par l'utilisateur est la date-heure de ce déclenchement.

Précision : les heures et dates sont décodées en nanosecondes ENTIÈRES (entiers
Python, sans arrondi) puis converties en secondes relatives à la 1re mesure,
ce qui garde une résolution meilleure que la nanoseconde sur plusieurs jours
en flottant 64 bits. Les dates sont « naïves » : aucun fuseau horaire ni
changement d'heure n'est appliqué, l'heure affichée est celle du fichier.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum

import numpy as np

from ptbg.core.diagnostics import Issue, Severity

NS_PER_S = 1_000_000_000
DAY_NS = 86_400 * NS_PER_S


class TimeFormat(Enum):
    """Format de la colonne de temps."""
    AUTO = "auto"
    COUNTER = "counter"
    TIME_OF_DAY = "time_of_day"
    DATETIME = "datetime"

    @property
    def label(self) -> str:
        return {"auto": "Détection automatique", "counter": "Compteur de temps",
                "time_of_day": "Heure hh:mm:ss.fraction", "datetime": "Date et heure"}[self.value]


# Unités d'un compteur -> facteur vers la seconde (« cycle » : × période nominale).
UNIT_FACTORS = {"ns": 1e-9, "us": 1e-6, "ms": 1e-3, "s": 1.0, "min": 60.0, "h": 3600.0}
UNIT_LABELS = {"ns": "ns", "us": "µs", "ms": "ms", "s": "s", "min": "min", "h": "h",
               "cycle": "cycles PLC"}

_COUNTER_RE = re.compile(r"^[+-]?(\d+\.?\d*|\.\d+)([eE][+-]?\d+)?$")
_INTEGER_RE = re.compile(r"^[+-]?\d+$")
_TIME_OF_DAY_RE = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})((?:[.,:]\d+)*)$")
_ISO_DATETIME_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[T ](\d{1,2}):(\d{2}):(\d{2})((?:[.,]\d+)?)Z?$")
_FR_DATETIME_RE = re.compile(
    r"^(\d{2})/(\d{2})/(\d{4})[T ](\d{1,2}):(\d{2}):(\d{2})((?:[.,]\d+)?)$")
_DATE_ONLY_RES = (re.compile(r"^(\d{4})-(\d{2})-(\d{2})$"), re.compile(r"^(\d{2})/(\d{2})/(\d{4})$"))
_UNIT_IN_NAME_RE = re.compile(
    r"(?:^|[^a-zµ])(ns|us|µs|ms|s|sec|min|h)(?:$|[^a-z])", re.IGNORECASE)

DETECTION_SAMPLE = 200


@dataclass
class TimeBaseSettings:
    """Réglages de la base de temps d'un fichier (REQ 2305, 4106, 4107).

    - ``fmt`` / ``unit`` : AUTO par défaut ;
    - ``nominal_period_s`` : raster normal imposé par l'utilisateur (REQ 4106),
      None = période estimée sur le fichier ;
    - ``tolerance_pct`` : écart accepté autour de la période (None = préférence) ;
    - ``origin`` : référence absolue (date-heure du compteur 0 / du
      déclenchement, ou date du jour pour un format hh:mm:ss) ;
    - ``offset_s`` : décalage manuel pour aligner des PLC non synchronisés
      (REQ 2102, 2104) ; toujours affiché dans le Time Base Monitor ;
    - ``ignore_jitter`` : horodatage régularisé sur le raster (REQ 4107) ;
    - ``operator_note`` : diagnostic associé saisi par l'utilisateur (REQ 4106).
    """
    fmt: TimeFormat = TimeFormat.AUTO
    unit: str = "auto"
    nominal_period_s: float | None = None
    tolerance_pct: float | None = None
    origin: str = ""
    offset_s: float = 0.0
    ignore_jitter: bool = True
    operator_note: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        data["fmt"] = self.fmt.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TimeBaseSettings":
        settings = cls()
        for key, value in data.items():
            if key == "fmt":
                settings.fmt = TimeFormat(value)
            elif hasattr(settings, key):
                setattr(settings, key, value)
        return settings


@dataclass
class TimeConversion:
    """Résultat de conversion de la colonne de temps."""
    fmt: TimeFormat
    unit: str | None
    unit_assumed: bool                  # unité supposée (ni en-tête ni utilisateur)
    seconds: np.ndarray                 # float64, temps relatif ; NaN si illisible
    invalid: np.ndarray                 # bool : horodatage illisible
    origin_ns: int | None               # instant absolu (ns depuis 1970) de seconds == 0
    date_known: bool                    # False : heure du jour sans date connue
    description: str                    # conversion lisible (Time Base Monitor)
    issues: list[Issue] = field(default_factory=list)
    pretrig_samples: int = 0            # échantillons en temps négatif

    @property
    def is_absolute(self) -> bool:
        return self.origin_ns is not None


# ------------------------------------------------------------------ détection
def detect_format(raw: list[str]) -> TimeFormat | None:
    """Détecte le format dominant sur les premières valeurs non vides."""
    sample = [text.strip() for text in raw[:DETECTION_SAMPLE * 2] if text.strip()][:DETECTION_SAMPLE]
    if not sample:
        return None
    scores = {
        TimeFormat.COUNTER: sum(bool(_COUNTER_RE.match(t)) for t in sample),
        TimeFormat.TIME_OF_DAY: sum(bool(_TIME_OF_DAY_RE.match(t)) for t in sample),
        TimeFormat.DATETIME: sum(bool(_ISO_DATETIME_RE.match(t) or _FR_DATETIME_RE.match(t))
                                 for t in sample),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 0.8 * len(sample) else None


def unit_from_name(column_name: str) -> str | None:
    """Unité lue dans l'en-tête : « t_ms », « Temps (s) », « time[us] »..."""
    match = _UNIT_IN_NAME_RE.search(column_name)
    if not match:
        return None
    token = match.group(1).lower()
    return {"µs": "us", "sec": "s"}.get(token, token)


# ------------------------------------------------------------ dates absolues
def _fraction_to_ns(fraction: str) -> int | None:
    """« .5 » -> 500000000 ; « .123.456.789 » -> 123456789 ; sinon None."""
    groups = re.findall(r"[.,:](\d+)", fraction)
    if not groups:
        return 0
    if len(groups) == 1 and len(groups[0]) <= 9:
        return int(groups[0].ljust(9, "0"))
    if len(groups) <= 3 and all(len(group) == 3 for group in groups):
        value = 0
        for position, group in enumerate(groups):
            value += int(group) * 10 ** (6 - 3 * position)
        return value
    return None


def _epoch_ns(year, month, day, hour, minute, second, fraction_ns) -> int:
    """Instant naïf en nanosecondes depuis 1970-01-01 (ValueError si invalide)."""
    if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
        raise ValueError("heure invalide")
    days = (date(year, month, day) - date(1970, 1, 1)).days
    return (days * 86_400 + hour * 3600 + minute * 60 + second) * NS_PER_S + fraction_ns


def parse_absolute(text: str) -> int | None:
    """Analyse une date ou date-heure saisie (origine) ; None si invalide.

    Formats : AAAA-MM-JJ[ HH:MM:SS[.fraction]] ou JJ/MM/AAAA[ HH:MM:SS[.fraction]].
    """
    text = text.strip()
    try:
        for regex, order in ((_DATE_ONLY_RES[0], (0, 1, 2)), (_DATE_ONLY_RES[1], (2, 1, 0))):
            match = regex.match(text)
            if match:
                parts = [int(match.group(i + 1)) for i in order]
                return _epoch_ns(*parts, 0, 0, 0, 0)
        return _parse_datetime_text(text)
    except ValueError:
        return None


def _parse_datetime_text(text: str) -> int | None:
    for regex, order in ((_ISO_DATETIME_RE, (0, 1, 2)), (_FR_DATETIME_RE, (2, 1, 0))):
        match = regex.match(text)
        if match:
            ymd = [int(match.group(i + 1)) for i in order]
            fraction = _fraction_to_ns(match.group(7))
            if fraction is None:
                return None
            return _epoch_ns(*ymd, int(match.group(4)), int(match.group(5)),
                             int(match.group(6)), fraction)
    return None


def format_absolute(epoch_ns: int, digits: int = 6, with_date: bool = True) -> str:
    """Instant absolu lisible : « 2026-10-13 12:00:00.020000 »."""
    days, rest = divmod(epoch_ns, DAY_NS)
    seconds, fraction = divmod(rest, NS_PER_S)
    hours, rest_s = divmod(seconds, 3600)
    minutes, secs = divmod(rest_s, 60)
    clock = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    if digits > 0:
        clock += "." + f"{fraction:09d}"[:digits]
    if not with_date:
        return clock
    day = date.fromordinal(date(1970, 1, 1).toordinal() + days)
    return f"{day:%Y-%m-%d} {clock}"


# -------------------------------------------------------------- conversions
def _parse_numbers(raw: list[str]) -> np.ndarray:
    """Textes -> float64, NaN pour les valeurs illisibles (vectorisé si possible)."""
    try:
        values = np.array(raw, dtype=np.float64)
    except ValueError:
        values = np.array([_safe_float(text) for text in raw], dtype=np.float64)
    values[~np.isfinite(values)] = np.nan
    return values


def _safe_float(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        return np.nan


def _convert_counter(raw, name, settings, default_unit) -> TimeConversion:
    """REQ_COMMON_KH_2307 : compteur numérique -> secondes (négatif = pretrig)."""
    issues = []
    unit = settings.unit if settings.unit != "auto" else unit_from_name(name)
    assumed = unit is None
    if assumed:
        unit = default_unit
        issues.append(Issue(Severity.INFO,
                            f"Unité du compteur « {name} » non précisée : {UNIT_LABELS[unit]} supposée "
                            "(à confirmer dans Base de temps > Configurer).", requirement="REQ_COMMON_KH_2307"))
    if unit == "cycle":
        if not settings.nominal_period_s:
            issues.append(Issue(Severity.ERROR, "Unité « cycles PLC » : la période nominale doit être "
                                "renseignée pour convertir le compteur.", requirement="REQ_COMMON_KH_2307"))
            nan = np.full(len(raw), np.nan)
            return TimeConversion(TimeFormat.COUNTER, unit, assumed, nan, np.ones(len(raw), bool),
                                  None, False, "Compteur en cycles sans période nominale", issues)
        factor = settings.nominal_period_s
    else:
        factor = UNIT_FACTORS[unit]
    values = _parse_numbers(raw)
    description = f"Compteur « {name} » en {UNIT_LABELS[unit]} × {factor:g} -> s"
    finite = np.isfinite(values)
    if finite.any() and np.nanmax(np.abs(values)) >= 2 ** 53:
        # Grands entiers (ex. nanosecondes depuis 1970) : calcul exact relatif.
        values, reference = _relative_big_integers(raw)
        description += f", relatif à la 1re valeur {reference}"
    seconds = values * factor
    invalid = ~np.isfinite(seconds)
    origin_ns = parse_absolute(settings.origin) if settings.origin else None
    if settings.origin and origin_ns is None:
        issues.append(Issue(Severity.WARNING, f"Origine absolue « {settings.origin} » illisible : ignorée."))
    pretrig = int(np.count_nonzero(seconds < 0))
    if pretrig:
        issues.append(Issue(Severity.INFO, f"{pretrig} échantillon(s) de pré-déclenchement (temps négatif) ; "
                            "t = 0 est l'instant de déclenchement.", requirement="REQ_COMMON_KH_2305"))
    return TimeConversion(TimeFormat.COUNTER, unit, assumed, seconds, invalid, origin_ns,
                          origin_ns is not None, description, issues, pretrig)


def _relative_big_integers(raw: list[str]) -> tuple[np.ndarray, int]:
    """Entiers exacts relatifs au 1er entier valide (évite la perte de précision)."""
    integers = [int(text) if _INTEGER_RE.match(text.strip()) else None for text in raw]
    reference = next((value for value in integers if value is not None), 0)
    return (np.array([np.nan if value is None else float(value - reference) for value in integers]),
            reference)


def _convert_time_of_day(raw, name, settings) -> TimeConversion:
    """REQ_COMMON_KH_2306 : hh:mm:ss.fraction (jusqu'à la ns), passage de minuit géré."""
    issues = []
    nanoseconds: list[int | None] = []
    day_offset, previous, rollovers = 0, None, 0
    for text in raw:
        match = _TIME_OF_DAY_RE.match(text.strip())
        value = None
        if match:
            hours, minutes, secs = (int(match.group(i)) for i in (1, 2, 3))
            fraction = _fraction_to_ns(match.group(4))
            if fraction is not None and hours < 24 and minutes < 60 and secs < 60:
                value = ((hours * 60 + minutes) * 60 + secs) * NS_PER_S + fraction + day_offset
                # Recul de plus de 12 h : passage de minuit, pas un retour arrière.
                if previous is not None and value < previous - DAY_NS // 2:
                    day_offset += DAY_NS
                    value += DAY_NS
                    rollovers += 1
                previous = value
        nanoseconds.append(value)
    if rollovers:
        issues.append(Issue(Severity.INFO, f"{rollovers} passage(s) de minuit pris en compte.",
                            requirement="REQ_COMMON_KH_2306"))
    seconds, first = _relative_seconds(nanoseconds)
    date_ns = parse_absolute(settings.origin) if settings.origin else None
    date_known = date_ns is not None
    origin_ns = None if first is None else (date_ns or 0) + first
    description = f"Heure « {name} » hh:mm:ss.fraction -> s depuis la 1re mesure"
    if not date_known:
        issues.append(Issue(Severity.INFO, "Date non précisée : seule l'heure du jour est affichée "
                            "(date réglable dans Base de temps > Configurer).", requirement="REQ_COMMON_KH_4107"))
    return TimeConversion(TimeFormat.TIME_OF_DAY, None, False, seconds, ~np.isfinite(seconds),
                          origin_ns, date_known, description, issues)


def _convert_datetime(raw, name) -> TimeConversion:
    """Date et heure complètes (ISO 8601 ou JJ/MM/AAAA) : déjà absolues."""
    nanoseconds = []
    for text in raw:
        try:
            nanoseconds.append(_parse_datetime_text(text.strip()))
        except ValueError:
            nanoseconds.append(None)
    seconds, first = _relative_seconds(nanoseconds)
    return TimeConversion(TimeFormat.DATETIME, None, False, seconds, ~np.isfinite(seconds),
                          first, first is not None,
                          f"Date-heure « {name} » -> s depuis la 1re mesure", [])


def _relative_seconds(nanoseconds: list[int | None]) -> tuple[np.ndarray, int | None]:
    """Nanosecondes entières -> secondes flottantes relatives à la 1re valeur."""
    first = next((value for value in nanoseconds if value is not None), None)
    if first is None:
        return np.full(len(nanoseconds), np.nan), None
    seconds = np.array([np.nan if value is None else (value - first) / NS_PER_S
                        for value in nanoseconds], dtype=np.float64)
    return seconds, first


def convert_time_column(raw: list[str], name: str, settings: TimeBaseSettings,
                        default_unit: str = "ms") -> TimeConversion:
    """Point d'entrée : convertit la 1re colonne selon les réglages."""
    fmt = settings.fmt if settings.fmt is not TimeFormat.AUTO else detect_format(raw)
    if fmt is None:
        examples = ", ".join(f"« {text} »" for text in raw[:3])
        nan = np.full(len(raw), np.nan)
        return TimeConversion(TimeFormat.AUTO, None, False, nan, np.ones(len(raw), dtype=bool), None,
                              False, "Format de temps non reconnu",
                              [Issue(Severity.ERROR, f"Format de la base de temps « {name} » non reconnu "
                                     f"({examples}). Formats acceptés : compteur, hh:mm:ss.fraction, "
                                     "date-heure.", 2, "REQ_COMMON_KH_2305")])
    if fmt is TimeFormat.COUNTER:
        result = _convert_counter(raw, name, settings, default_unit)
    elif fmt is TimeFormat.TIME_OF_DAY:
        result = _convert_time_of_day(raw, name, settings)
    else:
        result = _convert_datetime(raw, name)
    if settings.offset_s:
        result.description += f" ; décalage manuel {settings.offset_s:+.6g} s"
    return result
