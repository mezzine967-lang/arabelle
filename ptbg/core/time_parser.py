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
64 bits ou entiers Python, sans arrondi) puis converties en secondes relatives
à la 1re mesure, ce qui garde une résolution meilleure que la nanoseconde sur
plusieurs jours en flottant 64 bits. Les dates sont « naïves » : aucun fuseau
horaire ni changement d'heure n'est appliqué, l'heure affichée est celle du fichier.

Vitesse (REQ_COMMON_KH_4105) : les écritures usuelles de largeur fixe
(``CLOCK_TEMPLATES``, ``DATETIME_TEMPLATES``) sont décodées pour toute la
colonne d'un coup (``vector_parse``) ; toute autre écriture (espaces, heure
« 7:05:00 » au milieu de « 10:05:00 », fraction « .123:456 »…) est reprise
ligne par ligne par l'expression régulière : le résultat est identique.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date
from enum import Enum

import numpy as np

from ptbg.core.diagnostics import Issue, Severity
from ptbg.core.vector_parse import days_from_civil, match_templates, parse_numbers

NS_PER_S = 1_000_000_000
DAY_NS = 86_400 * NS_PER_S
HALF_DAY_NS = DAY_NS // 2
# Dates décodées en entiers 64 bits : ± 50 000 jours autour de 1970 (1833 à 2106)
# gardent toute différence entre deux dates représentable sans dépassement.
SAFE_DAYS = 50_000


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

# Écritures de largeur fixe décodées d'un coup (voir vector_parse.match_templates) :
# heure sur 1 ou 2 chiffres, fraction « .f » ou « :f » de 1 à 9 chiffres, ou
# groupes de 3 chiffres « .mmm.uuu[.nnn] » (REQ 2306).
_HOURS = ("hh", "h")
_CLOCK_FRACTIONS = ([""] + [separator + "f" * digits for separator in ".:" for digits in range(1, 10)]
                    + [".fff.fff", ".fff.fff.fff"])
CLOCK_TEMPLATES = [hours + ":mm:ss" + fraction for hours in _HOURS for fraction in _CLOCK_FRACTIONS]
_DATETIME_CLOCKS = [hours + ":mm:ss" + fraction for hours in _HOURS
                    for fraction in [""] + ["." + "f" * digits for digits in range(1, 10)]]
DATETIME_TEMPLATES = (["YYYY-MM-DD~" + clock + zone for clock in _DATETIME_CLOCKS for zone in ("", "Z")]
                      + ["DD/MM/YYYY~" + clock for clock in _DATETIME_CLOCKS])

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
    - ``ignore_jitter`` : affichage régularisé sur le raster (option, REQ 4107) ;
      par défaut l'horodatage BRUT est affiché : le jitter dans la tolérance
      n'est simplement pas compté comme anomalie ;
    - ``hide_aberrant`` : ne pas placer sur les courbes les horodatages aberrants
      isolés (option) ; par défaut ils restent affichés à leur instant brut, et
      sont dans tous les cas signalés en ERREUR et exclus du calcul du raster ;
    - ``operator_note`` : diagnostic associé saisi par l'utilisateur (REQ 4106).
    """
    fmt: TimeFormat = TimeFormat.AUTO
    unit: str = "auto"
    nominal_period_s: float | None = None
    tolerance_pct: float | None = None
    origin: str = ""
    offset_s: float = 0.0
    ignore_jitter: bool = False
    hide_aberrant: bool = False
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
def looks_like_time(text: str) -> bool:
    """Vrai si le texte a la forme d'un horodatage (compteur, heure, date-heure).

    Sert aussi au lecteur CSV pour distinguer une ligne de mesures d'une ligne
    d'en-têtes ou de métadonnées."""
    text = text.strip()
    return bool(_COUNTER_RE.match(text) or _TIME_OF_DAY_RE.match(text)
                or _ISO_DATETIME_RE.match(text) or _FR_DATETIME_RE.match(text))


def detect_format(raw: list[str]) -> TimeFormat | None:
    """Format le plus représenté parmi des valeurs prises sur TOUT le fichier.

    L'échantillon réunit le début du fichier et des valeurs réparties jusqu'à
    la fin : quelques centaines de lignes illisibles en tête (ou une fin
    corrompue) ne font pas perdre toute la base de temps. Le format retenu doit
    couvrir au moins 10 % de l'échantillon ; les valeurs qui ne le respectent
    pas deviennent des horodatages illisibles, signalés un par un."""
    spread = np.linspace(0, len(raw) - 1, num=min(len(raw), DETECTION_SAMPLE * 2)).astype(int) if raw else []
    picked = raw[:DETECTION_SAMPLE] + [raw[i] for i in spread]
    sample = [text.strip() for text in picked if text.strip()]
    if not sample:
        return None
    scores = {
        TimeFormat.COUNTER: sum(bool(_COUNTER_RE.match(t)) for t in sample),
        TimeFormat.TIME_OF_DAY: sum(bool(_TIME_OF_DAY_RE.match(t)) for t in sample),
        TimeFormat.DATETIME: sum(bool(_ISO_DATETIME_RE.match(t) or _FR_DATETIME_RE.match(t))
                                 for t in sample),
    }
    best = max(scores, key=scores.get)
    return best if scores[best] >= 0.1 * len(sample) else None


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
    """Textes -> float64, NaN pour les valeurs illisibles ou non finies."""
    values, _ = parse_numbers(raw)
    values[~np.isfinite(values)] = np.nan
    return values


def _convert_counter(raw, name, settings, default_unit) -> TimeConversion:
    """REQ_COMMON_KH_2307 : compteur numérique -> secondes (négatif = pretrig)."""
    issues = []
    unit = settings.unit if settings.unit != "auto" else unit_from_name(name)
    assumed = unit is None
    if assumed:
        unit = default_unit
        # AVERTISSEMENT (et non information) : période et durées n'ont de sens que
        # si l'unité est juste ; le TBM reste affiché tant qu'elle n'est pas confirmée.
        issues.append(Issue(Severity.WARNING,
                            f"Unité du compteur « {name} » absente de l'en-tête : {UNIT_LABELS[unit]} SUPPOSÉE, "
                            "non confirmée. Période et durées n'ont de sens que si cette unité est juste : "
                            "la confirmer dans Base de temps > Configurer.", requirement="REQ_COMMON_KH_2307"))
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
    # Grands entiers (ex. nanosecondes depuis 1970) : calcul exact relatif. La
    # médiane décide : une seule valeur aberrante ne change pas la conversion.
    if finite.any() and np.median(np.abs(values[finite])) >= 2 ** 53:
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
    """Entiers exacts relatifs au 1er entier valide (évite la perte de précision).

    Conversion en entiers 64 bits pour toute la colonne ; un texte qui n'est pas
    un entier simple (« 1_000 », « 12.5 »…) ou qui dépasse 64 bits est repris par
    l'expression régulière et un entier Python exact."""
    ints, converted = (np.zeros(len(raw), dtype=np.int64), np.zeros(len(raw), dtype=bool))
    if not any("_" in text for text in raw):            # int() accepte « 1_000 », pas la règle
        ints, converted = parse_numbers(raw, np.int64)
    exact: dict[int, int | None] = {}                    # position -> entier Python (repris)
    big = converted & (np.abs(ints) > 2 ** 62)            # écart à la référence non garanti sur 64 bits
    for position in np.flatnonzero(~converted | big).tolist():
        text = raw[position].strip()
        exact[position] = int(text) if _INTEGER_RE.match(text) else None
    converted &= ~big
    first_fast = int(np.argmax(converted)) if converted.any() else len(raw)
    first_slow = next((p for p in sorted(exact) if exact[p] is not None), len(raw))
    if first_fast == len(raw) and first_slow == len(raw):
        return np.full(len(raw), np.nan), 0
    reference = int(ints[first_fast]) if first_fast < first_slow else exact[first_slow]
    values = np.full(len(raw), np.nan)
    if converted.any() and abs(reference) <= 2 ** 62:
        values[converted] = (ints[converted] - reference).astype(np.float64)
    else:
        exact.update((p, int(ints[p])) for p in np.flatnonzero(converted).tolist())
    for position, value in exact.items():
        if value is not None:
            values[position] = float(value - reference)
    return values, reference


def _clock_of_day_ns(raw: list[str]) -> tuple[np.ndarray, np.ndarray]:
    """Nanosecondes depuis minuit de chaque texte et validité (REQ 2306)."""
    matched, fields = match_templates(raw, CLOCK_TEMPLATES)
    clock = ((fields["h"] * 60 + fields["m"]) * 60 + fields["s"]) * NS_PER_S + fields["f"]
    valid = (matched >= 0) & (fields["h"] < 24) & (fields["m"] < 60) & (fields["s"] < 60)
    for position in np.flatnonzero(~valid).tolist():      # autre écriture : ligne par ligne
        value = _time_of_day_ns(raw[position])
        if value is not None:
            clock[position], valid[position] = value, True
    return clock, valid


def _day_offsets(clock: np.ndarray, valid: np.ndarray) -> tuple[np.ndarray, int]:
    """Jour (0, 1, 2…) de chaque mesure et nombre de passages de minuit.

    Sur la suite des heures lisibles : un recul de plus de 12 h est un passage
    de minuit, sauf pour une heure ISOLÉE aberrante, c'est-à-dire écartée de
    plus de 12 h de sa voisine précédente (vers l'avant ou vers l'arrière),
    dont la mesure suivante revient à moins de 12 h en arrière de cette
    voisine précédente (ex. « 00:00:00 » au milieu d'un essai à 18 h, ou
    « 23:59:59 » au milieu d'un essai à 00 h 10). Une telle heure ne change
    pas de jour : elle reste un horodatage aberrant, signalé par l'analyse de
    la base de temps, et ne décale pas tout le reste du fichier."""
    days = np.zeros(clock.size, dtype=np.int64)
    index = np.flatnonzero(valid)
    if index.size < 2:
        return days, 0
    c = clock[index]
    step = np.diff(c)                                    # step[k - 1] : arrivée sur c[k]
    backward = np.concatenate(([False], step < -HALF_DAY_NS))
    forward = np.concatenate(([False], step > HALF_DAY_NS))
    returns = np.zeros(c.size, dtype=bool)               # la mesure suivante revient près de la précédente
    returns[1:-1] = c[2:] >= c[:-2] - HALF_DAY_NS
    leaves_back = np.zeros(c.size, dtype=bool)           # la mesure suivante repart en arrière de > 12 h
    leaves_back[:-1] = step < -HALF_DAY_NS
    candidate = returns & (backward | (forward & leaves_back))
    # Deux candidates consécutives : la seconde a été jugée par rapport à la
    # première, écartée ; elle n'est donc pas aberrante (une sur deux dans une suite).
    positions = np.arange(c.size)
    run_start = candidate & ~np.concatenate(([False], candidate[:-1]))
    since_start = positions - np.maximum.accumulate(np.where(run_start, positions, 0))
    aberrant = candidate & (since_start % 2 == 0)
    after_aberrant = np.concatenate(([False], aberrant[:-1]))
    crossing = backward & ~aberrant & ~after_aberrant
    days[index] = np.cumsum(crossing)
    return days, int(np.count_nonzero(crossing))


def _convert_time_of_day(raw, name, settings) -> TimeConversion:
    """REQ_COMMON_KH_2306 : hh:mm:ss.fraction (jusqu'à la ns), passage de minuit géré
    (règle détaillée dans ``_day_offsets``)."""
    issues = []
    clock, valid = _clock_of_day_ns(raw)
    days, rollovers = _day_offsets(clock, valid)
    if rollovers:
        issues.append(Issue(Severity.INFO, f"{rollovers} passage(s) de minuit pris en compte.",
                            requirement="REQ_COMMON_KH_2306"))
    if rollovers <= SAFE_DAYS:
        seconds, first = _relative_seconds(clock + days * DAY_NS, valid)
    else:                                       # fichier pathologique : entiers Python exacts
        exact = {p: int(clock[p]) + int(days[p]) * DAY_NS for p in np.flatnonzero(valid).tolist()}
        seconds, first = _relative_seconds(clock, np.zeros(len(raw), dtype=bool), exact)
    date_ns = parse_absolute(settings.origin) if settings.origin else None
    date_known = date_ns is not None
    origin_ns = None if first is None else (date_ns or 0) + first
    description = f"Heure « {name} » hh:mm:ss.fraction -> s depuis la 1re mesure"
    if not date_known:
        issues.append(Issue(Severity.INFO, "Date non précisée : seule l'heure du jour est affichée "
                            "(date réglable dans Base de temps > Configurer).", requirement="REQ_COMMON_KH_4107"))
    return TimeConversion(TimeFormat.TIME_OF_DAY, None, False, seconds, ~np.isfinite(seconds),
                          origin_ns, date_known, description, issues)


def _time_of_day_ns(text: str) -> int | None:
    """« hh:mm:ss.fraction » -> nanosecondes depuis minuit (None si illisible)."""
    match = _TIME_OF_DAY_RE.match(text.strip())
    if not match:
        return None
    hours, minutes, secs = (int(match.group(i)) for i in (1, 2, 3))
    fraction = _fraction_to_ns(match.group(4))
    if fraction is None or hours >= 24 or minutes >= 60 or secs >= 60:
        return None
    return ((hours * 60 + minutes) * 60 + secs) * NS_PER_S + fraction


def _convert_datetime(raw, name) -> TimeConversion:
    """Date et heure complètes (ISO 8601 ou JJ/MM/AAAA) : déjà absolues."""
    matched, fields = match_templates(raw, DATETIME_TEMPLATES)
    days, date_ok = days_from_civil(fields["Y"], fields["M"], fields["D"])
    fast = ((matched >= 0) & date_ok & (np.abs(days) <= SAFE_DAYS)
            & (fields["h"] < 24) & (fields["m"] < 60) & (fields["s"] < 60))
    nanoseconds = np.zeros(len(raw), dtype=np.int64)
    nanoseconds[fast] = (days[fast] * DAY_NS
                         + ((fields["h"][fast] * 60 + fields["m"][fast]) * 60 + fields["s"][fast]) * NS_PER_S
                         + fields["f"][fast])
    exact = {}                                        # autres écritures et dates lointaines : une à une
    for position in np.flatnonzero(~fast).tolist():
        try:
            value = _parse_datetime_text(raw[position].strip())
        except ValueError:
            value = None
        if value is not None:
            exact[position] = value
    seconds, first = _relative_seconds(nanoseconds, fast, exact)
    return TimeConversion(TimeFormat.DATETIME, None, False, seconds, ~np.isfinite(seconds),
                          first, first is not None,
                          f"Date-heure « {name} » -> s depuis la 1re mesure", [])


def _relative_seconds(nanoseconds: np.ndarray, valid: np.ndarray,
                      exact: dict[int, int] | None = None) -> tuple[np.ndarray, int | None]:
    """Nanosecondes entières -> secondes flottantes relatives à la 1re valeur.

    ``nanoseconds`` (entiers 64 bits) vaut pour les positions ``valid`` ;
    ``exact`` donne en entiers Python les instants des autres positions lisibles.
    Les écarts sont calculés en entiers exacts, puis convertis en secondes."""
    exact = dict(exact or {})
    seconds = np.full(len(valid), np.nan)
    first_fast = int(np.argmax(valid)) if valid.any() else len(valid)
    first_exact = min(exact, default=len(valid))
    if first_fast == len(valid) and first_exact == len(valid):
        return seconds, None
    first = int(nanoseconds[first_fast]) if first_fast < first_exact else exact[first_exact]
    if abs(first) <= 2 ** 62:                     # écart garanti sur 64 bits (|instants| ≤ 2^62)
        rows = np.flatnonzero(valid)
        offsets = nanoseconds[rows] - first
        seconds[rows] = offsets / NS_PER_S
        # Au-delà de 2^53 ns (104 jours), la division en flottants arrondirait deux
        # fois : ces écarts sont divisés en entiers Python (arrondi unique, exact).
        exact.update((p, int(nanoseconds[p])) for p in rows[np.abs(offsets) > 2 ** 53].tolist())
    else:
        exact.update((p, int(nanoseconds[p])) for p in np.flatnonzero(valid).tolist())
    for position, value in exact.items():
        seconds[position] = (value - first) / NS_PER_S
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
