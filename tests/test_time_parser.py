"""Formats de temps : REQ_COMMON_KH_2304 à 2307, 4107 (origine absolue), pretrig."""
import unittest

import numpy as np

import helpers  # noqa: F401  (chemin du projet)
from ptbg.core.time_parser import (TimeBaseSettings, TimeFormat, convert_time_column, detect_format,
                                   format_absolute, parse_absolute, unit_from_name)


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
