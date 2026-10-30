"""Analyse de base de temps : REQ_COMMON_KH_4100, 4101, 4105, 4106, 4107, 2100, 2104."""
import time
import unittest

import numpy as np

import helpers  # noqa: F401
from ptbg.core.diagnostics import Severity
from ptbg.core.time_base import EventKind, analyze, ms


def raster(n, period=0.02, start=0.0):
    return start + period * np.arange(n, dtype=float)


class TimeBaseTests(unittest.TestCase):
    def test_perfect_raster(self):
        """REQ 4100 : valeur, stabilité, croissance continue conformes."""
        result = analyze(raster(500))
        self.assertAlmostEqual(result.period_estimated_s, 0.02)
        self.assertIs(result.status, Severity.OK)
        self.assertEqual([c.name for c in result.checks],
                         ["Valeur de la période", "Stabilité de la période", "Croissance continue",
                          "Données manquantes"])
        self.assertEqual(result.normal_ratio, 1.0)

    def test_preferred_frequencies_are_information_only(self):
        """REQ 2100 : 1 ms (hors 10/20 ms) ne perturbe pas le traitement."""
        result = analyze(raster(300, 0.001))
        self.assertIs(result.status, Severity.OK)
        self.assertIn("information", result.checks[0].text)

    def test_jitter_ignored_within_tolerance(self):
        """REQ 4107 : jitter toléré ; horodatage régularisé sur le raster."""
        rng = np.random.default_rng(1)
        t = raster(1000, 0.01) + rng.uniform(-0.0004, 0.0004, 1000)
        result = analyze(t, tolerance_pct=10)
        self.assertIs(result.status, Severity.OK)
        self.assertGreater(result.jitter_max_s, 0.0001)
        np.testing.assert_allclose(np.diff(result.regular_s), 0.01, atol=1e-6)

    def test_missing_samples_detected_and_kept_in_regular_time(self):
        """REQ 4101 : trou de 3 échantillons ; le trou reste visible après régularisation."""
        t = np.delete(raster(100), [40, 41, 42])
        result = analyze(t)
        self.assertEqual(result.event_counts[EventKind.MISSING], 1)
        self.assertEqual(result.missing_samples, 3)
        self.assertIs(result.status, Severity.WARNING)
        self.assertAlmostEqual(result.regular_s[40] - result.regular_s[39], 0.08, places=9)

    def test_wrong_phasing_detected(self):
        """REQ 4101 : Δt hors grille = déphasage."""
        t = raster(100)
        t[50:] += 0.007
        result = analyze(t)
        self.assertEqual(result.event_counts[EventKind.PHASE], 1)
        self.assertEqual(result.events[0].index, 50)

    def test_duplicates_and_backward_are_errors(self):
        """REQ 4100 : croissance continue."""
        t = raster(50)
        t[10] = t[9]
        t[30] = t[29] - 0.005
        result = analyze(t)
        self.assertEqual(result.event_counts[EventKind.DUPLICATE], 1)
        self.assertEqual(result.event_counts[EventKind.BACKWARD], 1)
        self.assertIs(result.status, Severity.ERROR)

    def test_frequency_change_segments(self):
        """REQ 2104 : 20 ms puis 40 ms -> deux segments, pas une perte en série."""
        t = np.concatenate([raster(200, 0.02), raster(100, 0.04, start=4.0)])
        result = analyze(t, min_run=10)
        self.assertEqual(len(result.segments), 2)
        self.assertAlmostEqual(result.segments[1].period_s, 0.04)
        self.assertEqual(result.event_counts[EventKind.FREQUENCY], 1)
        self.assertNotIn(EventKind.MISSING, result.event_counts)
        self.assertLess(result.jitter_max_s, 1e-9)        # régularisation par segment

    def test_user_nominal_period(self):
        """REQ 4106 : raster imposé ; écart signalé avec son diagnostic."""
        result = analyze(raster(100, 0.02), nominal_period_s=0.01)
        self.assertIs(result.checks[0].severity, Severity.WARNING)
        self.assertIn("ÉCART", result.checks[0].text)
        self.assertEqual(result.period_used_s, 0.01)

    def test_invalid_timestamps(self):
        t = raster(20)
        t[5] = np.nan
        result = analyze(t)
        self.assertEqual(result.event_counts[EventKind.INVALID], 1)
        self.assertIs(result.status, Severity.ERROR)

    def test_pathological_inputs_never_raise(self):
        """REQ 4105 : aucun blocage ni exception sur une base de temps malade."""
        rng = np.random.default_rng(7)
        cases = [np.array([]), np.array([1.0]), np.full(10, np.nan), np.zeros(100),
                 rng.normal(size=1000), np.linspace(10, 0, 50), np.array([0, 1e9, 2e9]),
                 np.concatenate([raster(10), [np.inf]])]
        for seconds in cases:
            with self.subTest(n=len(seconds)):
                result = analyze(np.asarray(seconds, dtype=float))
                self.assertIsInstance(result.status, Severity)
                self.assertTrue(result.summary())

    def test_events_are_capped(self):
        t = raster(20000)
        t[1::2] += 0.007                                   # un Δt sur deux hors grille
        result = analyze(t, max_events=100)
        self.assertEqual(len(result.events), 100)
        self.assertGreater(sum(result.event_counts.values()), 100)

    def test_large_series_speed(self):
        """REQ 4105 : 2 millions d'échantillons analysés en quelques secondes."""
        t = raster(2_000_000, 0.01)
        t[1_000_000:] += 0.05
        start = time.perf_counter()
        result = analyze(t)
        self.assertLess(time.perf_counter() - start, 10.0)
        self.assertEqual(result.event_counts[EventKind.MISSING], 1)

    def test_many_frequency_changes_stay_linear(self):
        """REQ 4105 / 2104 : 40 000 changements de fréquence analysés en quelques secondes
        (chaque changement est cherché dans une fenêtre, sans relire toute la fin du fichier)."""
        n = 480_000
        dt = np.where((np.arange(n) // 12) % 2 == 0, 0.01, 0.02)
        t = np.concatenate(([0.0], np.cumsum(dt)))
        start = time.perf_counter()
        result = analyze(t)
        self.assertLess(time.perf_counter() - start, 30.0)
        self.assertEqual(len(result.segments), 40_000)
        np.testing.assert_allclose([s.period_s for s in result.segments[:3]], [0.01, 0.02, 0.01])

    def test_ms_formatting(self):
        self.assertEqual(ms(0.02), "20")
        self.assertEqual(ms(3.55e-15), "0")
        self.assertEqual(ms(0.0100035), "10.0035")
        self.assertEqual(ms(np.nan), "—")


if __name__ == "__main__":
    unittest.main()
