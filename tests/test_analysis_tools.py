"""Outils d'analyse : curseurs (5401-5405), horizontal (5406), condition (5407),
X/Y (5408), traitement conditionnel (5500), réduction d'affichage (4105)."""
import time
import unittest

import numpy as np

from helpers import TempFiles, counter_csv
from ptbg.config import Settings
from ptbg.core.arrangement import CurveRef, TabState
from ptbg.core.conditional import Condition, ConditionTerm, conditional_statistics, evaluate, true_intervals
from ptbg.core.data_package import Workspace, load_source
from ptbg.core.readings import compute_readings, xy_data
from ptbg.core.sampling import DisplayCurve, TimeGrid, break_at, crossings, missing_markers, sample_at, step_index
from ptbg.core.xy import build_xy, nearest_point, point_at_time


class SamplingTests(unittest.TestCase):
    x = np.array([0.0, 1.0, 2.0, 3.0])
    y = np.array([10.0, 11.0, np.nan, 13.0])

    def test_nearest_and_hold_without_interpolation(self):
        """REQ 5401 : valeur d'un échantillon réel, jamais interpolée."""
        grid = TimeGrid(self.x)
        self.assertEqual(sample_at(grid, self.y, 1.4, hold=False).value, 11.0)
        self.assertEqual(sample_at(grid, self.y, 1.6, hold=False).index, 2)      # case vide : NaN
        self.assertTrue(np.isnan(sample_at(grid, self.y, 1.6, hold=False).value))
        self.assertEqual(sample_at(grid, self.y, 1.9, hold=True).value, 11.0)
        self.assertIsNone(sample_at(grid, self.y, -1, hold=True))

    def test_unsorted_time_still_readable(self):
        x = np.array([0.0, 2.0, 1.0, 3.0])
        self.assertEqual(sample_at(TimeGrid(x), self.y, 1.1, hold=False).index, 2)

    def test_unreadable_timestamps_are_skipped(self):
        """Horodatage illisible (NaN) : jamais lu, l'échantillon voisin réel l'est."""
        grid = TimeGrid(np.array([0.0, np.nan, 2.0, 3.0]))
        self.assertEqual(sample_at(grid, self.y, 0.9, hold=False).index, 0)
        self.assertEqual(sample_at(grid, self.y, 1.9, hold=True).index, 0)
        self.assertEqual(step_index(grid, 0.0, 1), 2.0)

    def test_step_to_neighbour_sample(self):
        grid = TimeGrid(self.x)
        self.assertEqual(step_index(grid, 1.0, 1), 2.0)
        self.assertEqual(step_index(grid, 1.0, -1), 0.0)
        self.assertEqual(step_index(grid, 3.0, 1), 3.0)

    def test_decimate_keeps_extremes_and_gaps(self):
        x = np.arange(100_000, dtype=float)
        y = np.zeros(100_000)
        y[12_345] = 99.0
        y[50_000:50_010] = np.nan
        xd, yd = DisplayCurve(x, y).window(-np.inf, np.inf, 2000)
        self.assertLessEqual(xd.size, 2100)
        self.assertEqual(np.nanmax(yd), 99.0)
        self.assertTrue(np.isnan(yd).any())

    def test_decimate_window(self):
        x = np.arange(10_000, dtype=float) * 0.001
        curve = DisplayCurve(x, np.ones(10_000))
        xd, _ = curve.window(4.95, 5.05, 4000)
        self.assertLess(xd.size, 120)                       # fenêtre de zoom : vrais points
        np.testing.assert_allclose(np.diff(xd), 0.001)
        xd, _ = curve.window(1.0, 1.01, 4000)                 # 2e zoom : ordre déjà analysé
        self.assertAlmostEqual(xd[1], 1.0)

    def test_missing_markers_frame_empty_cells(self):
        """Croix sur le dernier point connu avant et le premier après une cellule vide."""
        values = np.array([1.0, np.nan, np.nan, 4.0, 5.0])
        missing = np.isnan(values)
        self.assertEqual(list(missing_markers(np.arange(5.0), values, missing)), [0, 3])

    def test_missing_markers_many_runs_stay_fast(self):
        """REQ 4105 : 300 000 suites de cellules vides traitées sans blocage (calcul
        linéaire ; l'ancienne recherche suite par suite prenait plusieurs minutes)."""
        n = 900_000
        values = np.arange(n, dtype=float)
        missing = np.zeros(n, dtype=bool)
        missing[1::3] = True
        values[missing] = np.nan
        start = time.perf_counter()
        marks = missing_markers(np.arange(n, dtype=float), values, missing)
        self.assertLess(time.perf_counter() - start, 10.0)
        self.assertEqual(marks.size, 2 * (n // 3))
        self.assertEqual(list(marks[:4]), [0, 2, 3, 5])

    def test_break_at_gaps(self):
        x, y = break_at(np.arange(4.0), np.arange(4.0), np.array([2]))
        self.assertTrue(np.isnan(x[2]) and np.isnan(y[2]))

    def test_crossings_with_condition(self):
        """REQ 5406 / 5407 : franchissements, restreints par la condition."""
        x = np.arange(6.0)
        y = np.array([0.0, 2.0, 0.0, 2.0, 0.0, 2.0])
        self.assertEqual(len(crossings(x, y, 1.0)), 5)
        allowed = np.array([True, True, True, False, False, False])
        found = crossings(x, y, 1.0, allowed)
        self.assertEqual([c.index for c in found], [1, 2])
        self.assertTrue(found[0].rising)


class ConditionalAndXYTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()
        self.ws = Workspace()
        times = list(range(0, 200, 20))
        a = self.files.write("a.csv", counter_csv(times, {
            "P": [0, 1, 2, 3, 4, 5, 6, 7, 8, 9], "Q": [0, 2, 4, 6, 8, 10, 12, 14, 16, 18],
            "cond": ["false", "true", "true", "true", "", "true", "false", "false", "true", "true"]}))
        b = self.files.write("b.csv", counter_csv(list(range(10, 210, 20)), {
            "R": [5] * 10, "flag": [0, 0, 1, 1, 1, 1, 1, 0, 0, 0]}))
        for path in (a, b):
            self.ws.active_package.files.append(load_source(path, Settings()))
        self.a, self.b = self.ws.files()

    def tearDown(self):
        self.files.cleanup()

    def test_same_file_condition_uses_same_row(self):
        mask = evaluate(Condition([ConditionTerm(self.a.id, "cond", True)]), self.a, self.ws.find,
                        self.ws.timeline())
        self.assertEqual(list(mask), [False, True, True, True, False, True, False, False, True, True])

    def test_other_file_condition_holds_last_state(self):
        mask = evaluate(Condition([ConditionTerm(self.b.id, "flag", True)]), self.a, self.ws.find,
                        self.ws.timeline())
        # A à 0,20,40..., B à 10,30,50... : état de B maintenu depuis son dernier échantillon.
        self.assertEqual(list(mask), [False, False, False, True, True, True, True, True, False, False])

    def test_and_or_combination(self):
        terms = [ConditionTerm(self.a.id, "cond", True), ConditionTerm(self.b.id, "flag", True)]
        timeline = self.ws.timeline()
        both = evaluate(Condition(terms, "AND"), self.a, self.ws.find, timeline)
        either = evaluate(Condition(terms, "OR"), self.a, self.ws.find, timeline)
        self.assertTrue(np.all(both <= either))
        self.assertEqual(Condition(terms, "OR").describe(), "cond = 1 OU flag = 1")

    def test_conditional_statistics(self):
        """Section 4.5 / REQ 5500 (proposition) : statistiques sous condition."""
        x = self.ws.timeline().x(self.a)
        mask = evaluate(Condition([ConditionTerm(self.a.id, "cond", True)]), self.a, self.ws.find,
                        self.ws.timeline())
        stats = conditional_statistics("P", x, self.a.signal("P").values, mask, level=2.5)
        self.assertEqual(stats.samples, 6)
        self.assertEqual((stats.minimum, stats.maximum), (1.0, 9.0))
        self.assertEqual(stats.intervals, 3)
        self.assertAlmostEqual(stats.duration_s, 0.06)
        self.assertEqual(len(true_intervals(x, mask)), 3)

    def test_xy_same_file_and_cross_file(self):
        """REQ 5408 : couples même ligne, ou plus proche à moins d'une demi-période."""
        timeline = self.ws.timeline()
        same = build_xy(timeline.x(self.a), self.a.signal("P").values, timeline.x(self.a),
                        self.a.signal("Q").values, True, 0.01)
        self.assertEqual(same.n, 10)
        self.assertAlmostEqual(same.r, 1.0)
        self.assertAlmostEqual(same.slope, 2.0)
        cross = build_xy(timeline.x(self.a), self.a.signal("P").values, timeline.x(self.b),
                         self.b.signal("R").values, False, 0.005)
        self.assertEqual(cross.n, 0)                        # B à ±10 ms : au-delà de 5 ms
        self.assertEqual(nearest_point(same, 4.1, 8.3, 9, 18), 4)
        self.assertEqual(point_at_time(same, 0.061), 3)

    def test_xy_cloud_is_cached_until_data_change(self):
        """REQ 5408 / 4105 : le nuage n'est pas reformé à chaque mouvement de souris, mais
        l'est dès qu'une de ses courbes change (type, base de temps…)."""
        axle = TabState.from_template("XY", "t").axles[2]
        axle.xy_x, axle.xy_y = CurveRef(self.a.id, "P"), CurveRef(self.a.id, "Q")
        first = xy_data(axle, self.ws, self.ws.timeline())
        self.assertIs(xy_data(axle, self.ws, self.ws.timeline()), first)
        self.a.set_type("Q", None)                              # révision du fichier incrémentée
        self.assertIsNot(xy_data(axle, self.ws, self.ws.timeline()), first)

    def test_readings_rows(self):
        """REQ 5401-5405 : lectures C1, C2, Δ, global et H."""
        tab = TabState.from_template("2A", "t")
        axle = tab.axles[0]
        axle.curves = [CurveRef(self.a.id, "P"), CurveRef(self.a.id, "cond")]
        axle.cursor_mode, axle.t1, axle.t2 = "double", 0.02, 0.08
        axle.h_enabled, axle.h_level = True, 4.5
        tab.global_cursor, tab.t_global = True, 0.1
        rows = compute_readings(tab, self.ws, self.ws.timeline())
        labels = [row.cursor for row in rows]
        for expected in ("Global", "C1", "C2", "Δ", "H"):
            self.assertIn(expected, labels)
        c1_p = next(r for r in rows if r.cursor == "C1" and r.curve.startswith("P"))
        self.assertEqual(c1_p.value, "1")
        self.assertEqual(c1_p.line, "3")
        delta = next(r for r in rows if r.cursor == "Δ" and r.curve.startswith("P"))
        self.assertIn("ΔV = 3", delta.value)


if __name__ == "__main__":
    unittest.main()
