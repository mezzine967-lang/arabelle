"""Formats de temps : REQ_COMMON_KH_2304 à 2307, 4107 (origine absolue), pretrig, 4105 (vitesse)."""
import random
import unittest
from datetime import date

import numpy as np

import helpers  # noqa: F401  (chemin du projet)
from ptbg.core.time_parser import (NS_PER_S, TimeBaseSettings, TimeFormat, _clock_of_day_ns, _parse_datetime_text,
                                   _time_of_day_ns, convert_time_column, detect_format, format_absolute,
                                   parse_absolute, unit_from_name)
from ptbg.core.vector_parse import days_from_civil


class TimeParserTests(unittest.TestCase):
    def test_detect_formats(self):
        self.assertIs(detect_format(["0", "20", "40"]), TimeFormat.COUNTER)
        self.assertIs(detect_format(["12:00:00.1", "12:00:00.2"]), TimeFormat.TIME_OF_DAY)
        self.assertIs(detect_format(["2026-10-13 12:00:00", "2026-10-13T12:00:01.5"]), TimeFormat.DATETIME)
        self.assertIsNone(detect_format(["abc", "def"]))

    def test_unit_from_header(self):
        """REQ 2307 : unité lue dans le nom de la colonne."""
        self.assertEqual(unit_from_name("t_ms"), "ms")
        self.assertEqual(unit_from_name("Temps (s)"), "s")
        self.assertEqual(unit_from_name("time[us]"), "us")
        self.assertEqual(unit_from_name("timestamp_reel_ms"), "ms")
        self.assertIsNone(unit_from_name("index"))
        self.assertIsNone(unit_from_name("status"))

    def test_counter_with_assumed_unit_and_pretrig(self):
        """Pré-déclenchement : temps négatifs conservés, t = 0 = déclenchement."""
        result = convert_time_column(["-40", "-20", "0", "20"], "index", TimeBaseSettings(), "ms")
        self.assertTrue(result.unit_assumed)
        np.testing.assert_allclose(result.seconds, [-0.04, -0.02, 0.0, 0.02])
        self.assertEqual(result.pretrig_samples, 2)
        self.assertIsNone(result.origin_ns)

    def test_column_and_line_by_line_conversions_agree(self):
        """REQ 4105 / 2306 : la conversion de toute la colonne d'un coup donne exactement les
        instants de l'analyse ligne par ligne, écritures atypiques et fautives comprises."""
        rng = random.Random(2306)
        clocks = []
        for _ in range(3000):
            h, m, s = rng.randrange(24), rng.randrange(60), rng.randrange(60)
            fraction = rng.choice(["", ".5", ".123456789", ":250", ".123.456", ".123.456.789",
                                   ".1234567890", ".12.3", ".123:456"])
            text = rng.choice([f"{h:02d}", f"{h}"]) + f":{m:02d}:{s:02d}{fraction}"
            clocks.append(rng.choice([text, text, text, f" {text}", text.replace(":", ".", 1), "25:00:00", ""]))
        clock, valid = _clock_of_day_ns(clocks)
        self.assertEqual([int(v) if ok else None for v, ok in zip(clock, valid)],
                         [_time_of_day_ns(text) for text in clocks])
        dates = []
        for _ in range(3000):
            y, mo, d = rng.choice([2026, 2024, 1500, 2500, 0]), rng.randint(1, 13), rng.randint(1, 31)
            clock_text = f"{rng.randrange(24):02d}:{rng.randrange(60):02d}:{rng.randrange(60):02d}"
            clock_text += rng.choice(["", ".5", ".123456789", ".1234567890"])
            dates.append(rng.choice([f"{y:04d}-{mo:02d}-{d:02d}T{clock_text}", f"{y:04d}-{mo:02d}-{d:02d} {clock_text}Z",
                                     f"{d:02d}/{mo:02d}/{y:04d} {clock_text}", f" {y:04d}-{mo:02d}-{d:02d} {clock_text}"]))
        result = convert_time_column(dates, "date", TimeBaseSettings(fmt=TimeFormat.DATETIME))
        exact = []
        for text in dates:
            try:
                exact.append(_parse_datetime_text(text.strip()))
            except ValueError:
                exact.append(None)
        first = next(value for value in exact if value is not None)
        self.assertEqual(result.origin_ns, first)
        expected = [np.nan if value is None else (value - first) / NS_PER_S for value in exact]
        np.testing.assert_array_equal(result.seconds, expected)

    def test_calendar_days_match_python_dates(self):
        """Jours calendaires calculés en bloc = ``datetime.date`` (années bissextiles comprises)."""
        rng = np.random.default_rng(5)
        years, months, days = rng.integers(0, 10000, 5000), rng.integers(0, 14, 5000), rng.integers(0, 32, 5000)
        count, valid = days_from_civil(years, months, days)
        for y, m, d, n, ok in zip(years.tolist(), months.tolist(), days.tolist(), count.tolist(), valid.tolist()):
            try:
                expected = (date(y, m, d) - date(1970, 1, 1)).days
            except ValueError:
                expected = None
            self.assertEqual(n if ok else None, expected, (y, m, d))

    def test_big_integer_counter_with_odd_rows(self):
        """REQ 2307 : compteur en ns depuis 1970 converti en entiers exacts, y compris une
        valeur au-delà de 64 bits ; une écriture refusée par la règle reste illisible."""
        raw = [str(1_700_000_000_000_000_000 + 10_000_000 * i) for i in range(100)]
        raw[5] = " 1700000000050000000 "
        raw[7] = "99999999999999999999999"
        conversion = convert_time_column(raw, "t_ns", TimeBaseSettings())
        self.assertAlmostEqual(conversion.seconds[5], 0.05, places=12)
        self.assertAlmostEqual(conversion.seconds[99], 0.99, places=12)
        self.assertEqual(conversion.seconds[7], float(99999999999999999999999 - 1_700_000_000_000_000_000) * 1e-9)
        raw[3] = "1_700_000_000_030_000_000"                    # int() l'accepte, la règle non
        self.assertTrue(np.isnan(convert_time_column(raw, "t_ns", TimeBaseSettings()).seconds[3]))

    def test_counter_with_absolute_origin(self):
        """REQ 4107 : origine absolue saisie = instant du compteur 0."""
        settings = TimeBaseSettings(origin="2026-10-13 12:00:00")
        result = convert_time_column(["0", "20"], "t_ms", settings)
        self.assertEqual(format_absolute(result.origin_ns, 3), "2026-10-13 12:00:00.000")
        self.assertTrue(result.is_absolute)

    def test_cycle_unit_requires_period(self):
        bad = convert_time_column(["0", "1"], "cycle", TimeBaseSettings(unit="cycle"))
        self.assertTrue(np.isnan(bad.seconds).all())
        good = convert_time_column(["0", "1", "2"], "cycle", TimeBaseSettings(unit="cycle", nominal_period_s=0.02))
        np.testing.assert_allclose(good.seconds, [0, 0.02, 0.04])

    def test_big_integer_counter_keeps_precision(self):
        """Compteurs en ns depuis 1970 : pas de perte de précision."""
        raw = ["1760356800000000000", "1760356800000000001", "1760356800000000003"]
        result = convert_time_column(raw, "t_ns", TimeBaseSettings())
        np.testing.assert_allclose(result.seconds, [0, 1e-9, 3e-9], atol=1e-15)

    def test_time_of_day_fraction_styles_and_midnight(self):
        """REQ 2306 : hh:mm:ss.fraction jusqu'à la ns, groupes ms.µs.ns, minuit."""
        raw = ["23:59:59.999999999", "00:00:00.000000001", "00:00:00.000.000.003", "00:00:01,5"]
        result = convert_time_column(raw, "heure", TimeBaseSettings())
        np.testing.assert_allclose(result.seconds, [0, 2e-9, 4e-9, 1.500000001], atol=1e-12)
        self.assertTrue(any("minuit" in issue.message for issue in result.issues))
        self.assertFalse(result.date_known)

    def test_time_of_day_with_date(self):
        result = convert_time_column(["08:00:00", "08:00:01"], "h", TimeBaseSettings(origin="13/10/2026"))
        self.assertTrue(result.date_known)
        self.assertEqual(format_absolute(result.origin_ns, 0), "2026-10-13 08:00:00")

    def test_datetime_formats(self):
        raw = ["2026-10-13 12:00:00.5", "13/10/2026 12:00:01", "bad"]
        result = convert_time_column(raw, "date", TimeBaseSettings(fmt=TimeFormat.DATETIME))
        np.testing.assert_allclose(result.seconds[:2], [0, 0.5])
        self.assertTrue(result.invalid[2])

    def test_unknown_format_is_an_error_not_a_crash(self):
        result = convert_time_column(["a", "b"], "t", TimeBaseSettings())
        self.assertTrue(result.invalid.all())
        self.assertEqual(result.issues[0].requirement, "REQ_COMMON_KH_2305")

    def test_parse_and_format_absolute(self):
        value = parse_absolute("2026-10-13 12:34:56.123456789")
        self.assertEqual(format_absolute(value, 9), "2026-10-13 12:34:56.123456789")
        self.assertIsNone(parse_absolute("2026-13-40"))
        self.assertIsNone(parse_absolute("n'importe quoi"))

    def test_settings_roundtrip(self):
        settings = TimeBaseSettings(fmt=TimeFormat.COUNTER, unit="us", nominal_period_s=0.01, operator_note="ok")
        self.assertEqual(TimeBaseSettings.from_dict(settings.to_dict()), settings)


if __name__ == "__main__":
    unittest.main()
