"""Robustesse de la lecture CSV et de la base de temps (REQ_COMMON_KH_4105, 2301-2310, 4101).

Chaque test vérifie trois choses sur un fichier « malade » : aucune exception,
aucune donnée saine perdue ou inventée, et un constat qui cite la bonne ligne.
"""
import random
import unittest
from unittest import mock

import numpy as np
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from helpers import TempFiles
from ptbg.config import Settings
from ptbg.core.arrangement import CurveRef, TabState
from ptbg.core.csv_reader import CsvReadError, read_csv
from ptbg.core.data_package import Workspace, load_source
from ptbg.core.diagnostics import Severity
from ptbg.core.readings import compute_readings
from ptbg.core.signals import SignalType
from ptbg.core.time_base import EventKind, analyze
from ptbg.core.time_parser import TimeBaseSettings, convert_time_column
from ptbg.plotting.renderer import TabRenderer

HEADER = "t_ms,analog,bit,etat\n"


def good_rows(n=100, start=0):
    """Lignes saines : compteur 10 ms, Float, Bool, Texte."""
    return "".join(f"{start + 10 * i},{np.sin(i / 7):.4f},{i // 10 % 2},{'MARCHE' if i % 30 < 15 else 'ARRET'}\n"
                   for i in range(n))


def messages(table_or_source):
    issues = table_or_source.issues if hasattr(table_or_source, "issues") else table_or_source.all_issues()
    return "\n".join(f"{issue.line}: {issue.message}" for issue in issues)


class CsvRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()

    def tearDown(self):
        self.files.cleanup()

    def read(self, content, name="cas.csv"):
        return read_csv(self.files.write(name, content))

    def test_unclosed_quote_only_loses_its_own_line(self):
        """Un guillemet non fermé n'avale plus la suite du fichier."""
        rows = good_rows().splitlines(keepends=True)
        rows[50] = '500,"0.5,1,ARRET\n'
        table = self.read(HEADER + "".join(rows))
        self.assertEqual(table.n_samples, 99)
        self.assertIn("52: Ligne rejetée : guillemets mal formés", messages(table))

    def test_quoted_fields_and_escaped_quotes(self):
        table = self.read('"t_ms","analog, V","etat"\n0,"1.5","dit ""ok"""\n10,"2.5","x"\n')
        self.assertEqual(table.header, ["t_ms", "analog, V", "etat"])
        self.assertEqual(table.columns[1].categories, ['dit "ok"', "x"])

    def test_trailing_commas_on_data_rows_keep_the_header(self):
        """Virgules finales sur les données seulement : l'en-tête n'est pas perdu."""
        data = "".join(line + ",\n" for line in good_rows().splitlines())
        table = self.read(HEADER + data)
        self.assertEqual(table.header, ["t_ms", "analog", "bit", "etat"])
        self.assertEqual(table.n_samples, 100)

    def test_preamble_of_same_width_is_metadata(self):
        """REQ 2303 : un préambule aussi large que le tableau n'est pas pris pour l'en-tête."""
        table = self.read("Projet,NCS,essai,3\nOperateur,X,Y,Z\n" + HEADER + good_rows())
        self.assertEqual(table.header, ["t_ms", "analog", "bit", "etat"])
        self.assertEqual(table.n_samples, 100)
        self.assertEqual(sum(i.requirement == "REQ_COMMON_KH_2303" for i in table.issues), 2)

    def test_missing_header_keeps_the_first_measure(self):
        """REQ 2308 : sans en-tête, la 1re ligne de mesures est conservée."""
        table = self.read(good_rows())
        self.assertEqual(table.n_samples, 100)
        self.assertEqual(table.header, ["Colonne_1", "Colonne_2", "Colonne_3", "Colonne_4"])
        self.assertEqual(table.line_numbers[0], 1)
        self.assertTrue(any(i.requirement == "REQ_COMMON_KH_2308" for i in table.issues))

    def test_repeated_header_and_concatenated_captures(self):
        table = self.read(HEADER + good_rows(50) + HEADER + good_rows(50, 500))
        self.assertEqual(table.n_samples, 100)
        self.assertIn("52: 1 ligne(s) d'en-têtes répétée(s)", messages(table))

    def test_blank_and_empty_field_rows_are_ignored(self):
        table = self.read("\n" + HEADER + good_rows(50) + "\n,,,\n   \n" + good_rows(50, 500) + ",,,\n")
        self.assertEqual(table.n_samples, 100)
        self.assertIn("5 ligne(s) vide(s) ignorée(s)", messages(table))

    def test_bom_of_a_second_concatenated_file(self):
        table = self.read("\ufeff" + HEADER + good_rows(20) + "\ufeff" + HEADER + good_rows(20, 200))
        self.assertEqual(table.n_samples, 40)
        self.assertIn("en-têtes répétée", messages(table))

    def test_header_longer_than_every_data_row(self):
        """Dernière colonne jamais écrite : les mesures sont gardées, la colonne reste vide."""
        table = self.read("t_ms,a,b,jamais_ecrite\n" + "".join(f"{10 * i},{i},{i % 2}\n" for i in range(50)))
        self.assertEqual(table.n_samples, 50)
        self.assertEqual(table.columns[2].name, "jamais_ecrite")
        self.assertTrue(np.all(np.isnan(table.columns[2].values)))
        self.assertIn("jamais_ecrite sans données", messages(table))

    def test_rows_with_wrong_width_rejected_and_quoted(self):
        rows = good_rows(10).splitlines(keepends=True)
        rows[3], rows[6] = "30,0.5\n", "60,0.5,1,ARRET,99\n"
        table = self.read(HEADER + "".join(rows))
        self.assertEqual(table.n_samples, 8)
        text = messages(table)
        self.assertIn("5: Ligne rejetée : 2 champ(s) au lieu de 4 : « 30,0.5 »", text)
        self.assertIn("8: Ligne rejetée : 5 champ(s) au lieu de 4", text)

    def test_interrupted_writing(self):
        """Fichier coupé pendant l'écriture : ligne tronquée ou remplissage d'octets nuls."""
        cut = self.read(HEADER + good_rows(10) + "100,0.12")
        self.assertEqual(cut.n_samples, 10)
        self.assertIn("dernière ligne non terminée", messages(cut))
        complete_but_unfinished = self.read(HEADER + good_rows(10) + "100,0.12,1,ARR")
        self.assertEqual(complete_but_unfinished.n_samples, 11)
        self.assertIn("12: Dernière ligne non terminée", messages(complete_but_unfinished))
        padded = self.read((HEADER + good_rows(10)).encode() + b"\x00" * 4096)
        self.assertEqual(padded.n_samples, 10)
        self.assertIn("octets nuls", messages(padded))

    def test_nul_bytes_inside_a_line_reject_only_that_line(self):
        rows = good_rows(10).splitlines(keepends=True)
        rows[4] = "40,0.5\x00\x00,1,ARRET\n"
        table = self.read(HEADER + "".join(rows))
        self.assertEqual(table.n_samples, 9)
        self.assertIn("6: Ligne rejetée : octets nuls", messages(table))

    def test_line_endings_cr_crlf_and_mixed(self):
        text = HEADER + good_rows(20)
        for variant in (text.replace("\n", "\r\n"), text.replace("\n", "\r"),
                        "".join(line + ("\r\n" if i % 2 else "\n") for i, line in enumerate(text.splitlines()))):
            with self.subTest(ending=repr(variant[10:30])):
                self.assertEqual(self.read(variant).n_samples, 20)

    def test_invalid_byte_in_the_middle_is_flagged_not_fatal(self):
        """REQ 2302 : un octet non UTF-8 isolé ne fait plus refuser tout le fichier."""
        data = (HEADER + good_rows()).encode()
        position = data.index(b"\n500,")
        table = self.read(data[:position] + b"\xff" + data[position:])
        self.assertEqual(table.n_samples, 100)
        issue = next(i for i in table.issues if i.requirement == "REQ_COMMON_KH_2302")
        self.assertIs(issue.severity, Severity.ERROR)
        self.assertEqual(issue.line, 51)

    def test_utf16_is_read_and_flagged(self):
        table = self.read((HEADER + good_rows(20)).encode("utf-16"))
        self.assertEqual(table.n_samples, 20)
        self.assertTrue(any(i.requirement == "REQ_COMMON_KH_2302" and i.severity is Severity.ERROR
                            for i in table.issues))

    def test_semicolon_with_decimal_comma_rejected(self):
        """REQ 2301 : même quand la virgule décimale donne autant de virgules que de « ; »."""
        with self.assertRaises(CsvReadError) as ctx:
            self.read("t_ms;analog\n" + "".join(f"{10 * i};{i},5\n" for i in range(30)))
        self.assertEqual(ctx.exception.issues[-1].requirement, "REQ_COMMON_KH_2301")

    def test_decimal_comma_in_comma_file_never_invents_columns(self):
        """Une virgule décimale dans un fichier à virgules : refus expliqué, pas de fausses colonnes."""
        with self.assertRaises(CsvReadError) as ctx:
            self.read("t_ms,analog\n" + "".join(f"{10 * i},{i},5\n" for i in range(30)))
        self.assertIn("séparateur décimal", "\n".join(i.message for i in ctx.exception.issues))

    def test_very_long_cell_is_handled(self):
        rows = good_rows(20).splitlines(keepends=True)
        rows[5] = "50,0.5,1," + "X" * 300_000 + "\n"
        table = self.read(HEADER + "".join(rows))
        self.assertEqual(table.n_samples, 20)


class ValueAndTimeRobustnessTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()
        self.settings = Settings()

    def tearDown(self):
        self.files.cleanup()

    def load(self, content, name="cas.csv"):
        return load_source(self.files.write(name, content), self.settings)

    def test_nan_and_inf_are_missing_values_not_text(self):
        values = ["nan" if i % 10 else f"{i}.5" for i in range(100)]
        source = self.load("t_ms,analog\n" + "".join(f"{10 * i},{v}\n" for i, v in enumerate(values)))
        signal = source.signal("analog")
        self.assertIs(signal.type, SignalType.FLOAT)
        self.assertTrue(signal.missing[1] and np.isnan(signal.values[1]))
        self.assertIn("« nan » / « inf » : analog (90)", messages(source))

    def test_trailer_line_does_not_change_types(self):
        """Une ligne de total en fin de fichier ne transforme pas un Bool en Float."""
        source = self.load(HEADER + good_rows() + "Total,1,2,3\n")
        self.assertIs(source.signal("bit").type, SignalType.BOOL)
        self.assertEqual(source.analysis.event_counts[EventKind.INVALID], 1)

    def test_time_format_found_despite_garbage_at_the_start(self):
        rows = "".join(f"x,{i % 2},0,A\n" for i in range(300))
        source = self.load(HEADER + rows + good_rows(300, 3000))
        self.assertEqual(source.analysis.event_counts[EventKind.INVALID], 300)
        self.assertAlmostEqual(source.analysis.period_used_s, 0.01)

    def test_isolated_bad_clock_value_does_not_shift_the_rest_by_a_day(self):
        """REQ 2306 : « 00:00:00 » isolé au milieu d'un essai à 18 h n'est pas un passage de minuit."""
        raw = [f"18:00:{i * 0.01:012.9f}" for i in range(200)]
        raw[100] = "00:00:00.000000000"
        conversion = convert_time_column(raw, "heure", TimeBaseSettings())
        self.assertAlmostEqual(conversion.seconds[199], 1.99, places=9)
        self.assertNotIn("minuit", " ".join(i.message for i in conversion.issues))
        real = [f"23:59:59.{i:02d}0" if i < 100 else f"00:00:00.{i - 100:02d}0" for i in range(200)]
        crossing = convert_time_column(real, "heure", TimeBaseSettings())
        self.assertAlmostEqual(crossing.seconds[150] - crossing.seconds[50], 1.0, places=9)

    def test_isolated_aberrant_timestamp_is_one_error_not_a_fake_gap(self):
        t = np.arange(200) * 0.01
        t[100] = 1e9
        result = analyze(t)
        self.assertEqual(result.event_counts[EventKind.OUTLIER], 1)
        self.assertEqual(result.missing_samples, 1)        # sa place dans le raster, pas 1e11 échantillons
        self.assertNotIn(EventKind.BACKWARD, result.event_counts)
        self.assertEqual(list(result.excluded), [100])
        self.assertIs(result.status, Severity.ERROR)

    def test_one_huge_counter_value_keeps_the_counter_origin(self):
        """Une valeur aberrante ne fait pas passer le compteur en « grands entiers relatifs »."""
        raw = [str(10 * i - 500) for i in range(200)]
        raw[100] = "100000000000000000000"
        conversion = convert_time_column(raw, "t_ms", TimeBaseSettings())
        self.assertAlmostEqual(conversion.seconds[0], -0.5)

    def test_assumed_unit_is_a_warning(self):
        """REQ 2307 : unité supposée = avertissement (période à confirmer), levé dès qu'elle est choisie."""
        source = self.load("index,a\n" + "".join(f"{20 * i},{i}\n" for i in range(50)))
        self.assertIs(source.time_status(), Severity.WARNING)
        self.assertIn("SUPPOSÉE", messages(source))

    def test_raw_timestamps_are_displayed_by_default(self):
        """REQ 4107 : l'affichage brut est la référence ; la régularisation est une option."""
        jitter = [10 * i + (0.3 if i % 2 else -0.3) for i in range(100)]
        source = self.load("t_ms,a\n" + "".join(f"{t},{i}\n" for i, t in enumerate(jitter)))
        self.assertFalse(source.time_settings.ignore_jitter)
        np.testing.assert_allclose(source.display_seconds(), np.array(jitter) / 1000)

    def test_unexpected_error_is_isolated_to_its_file(self):
        """REQ 4105 : une erreur imprévue sur un fichier le marque en erreur, sans exception."""
        path = self.files.write("a.csv", HEADER + good_rows())
        with mock.patch("ptbg.core.data_package.read_csv", side_effect=RuntimeError("panne simulée")):
            source = load_source(path, self.settings)
        self.assertFalse(source.is_loaded)
        self.assertIn("panne simulée", source.read_issues[0].message)
        with mock.patch("ptbg.core.data_package.read_csv", side_effect=OSError("réseau perdu")):
            self.assertIn("réseau perdu", load_source(path, self.settings).read_issues[0].message)

    def test_extreme_values_are_drawn(self):
        """Valeurs ±1e308 : l'axe se borne au lieu de lever « Singular matrix »."""
        values = [1e308 if i % 2 else -1e308 for i in range(100)]
        source = self.load("t_ms,a\n" + "".join(f"{10 * i},{v}\n" for i, v in enumerate(values)))
        ws = Workspace()
        ws.active_package.files.append(source)
        tab = TabState.from_template("XY", "extrêmes")
        tab.axles[0].curves = [CurveRef(source.id, "a")]
        tab.axles[0].cursor_mode, tab.axles[0].t1, tab.axles[0].t2 = "double", 0.1, 0.5
        tab.axles[2].xy_x = tab.axles[2].xy_y = CurveRef(source.id, "a")
        figure = Figure()
        FigureCanvasAgg(figure)
        TabRenderer(figure, tab, ws, ws.timeline(), 2000).draw()
        figure.canvas.draw()
        texts = [t.get_text() for t in figure.findobj() if hasattr(t, "get_text")]
        self.assertFalse(any("impossible" in text or "non affichable" in text for text in texts))
        compute_readings(tab, ws, ws.timeline())

    def test_random_corruptions_never_raise(self):
        """REQ 4105 : 40 corruptions aléatoires (octets, coupures, insertions) ; jamais d'exception,
        ni à la lecture, ni à l'analyse, ni au dessin."""
        base = (HEADER + good_rows(150)).encode()
        rng = random.Random(2026)
        for case in range(40):
            data = bytearray(base)
            for _ in range(rng.randint(1, 10)):
                position = rng.randrange(len(data))
                choice = rng.random()
                if choice < 0.3:
                    data[position] = rng.randrange(256)
                elif choice < 0.55:
                    del data[position:position + rng.randint(1, 30)]
                else:
                    data[position:position] = rng.choice([b",", b"\n", b'"', b"\x00", b"#", b";", b"\r", b"x"])
            with self.subTest(case=case):
                source = self.load(bytes(data), f"fuzz_{case}.csv")
                if not source.is_loaded:
                    self.assertTrue(source.read_issues)
                    continue
                ws = Workspace()
                ws.active_package.files.append(source)
                tab = TabState.from_template("AL", "fuzz")
                tab.axles[0].curves = [CurveRef(source.id, n) for n in source.float_names()[:3]]
                tab.axles[1].curves = [CurveRef(source.id, n) for n in source.bool_names()[:3]]
                tab.axles[0].cursor_mode, tab.axles[0].t1, tab.axles[0].t2 = "double", 0.2, 1.0
                figure = Figure()
                FigureCanvasAgg(figure)
                TabRenderer(figure, tab, ws, ws.timeline(), 2000).draw()
                figure.canvas.draw()
                compute_readings(tab, ws, ws.timeline())


if __name__ == "__main__":
    unittest.main()
