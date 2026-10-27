"""Lecture CSV : REQ_COMMON_KH_2300 à 2310, 2200, 2201, 4105 (isolation des erreurs)."""
import threading
import unittest

import numpy as np

from helpers import EXAMPLES, TempFiles, counter_csv
from ptbg.config import Settings
from ptbg.core.csv_reader import KIND_EMPTY, CsvReadError, ReadCancelled, read_csv
from ptbg.core.data_package import load_source
from ptbg.core.diagnostics import Severity
from ptbg.core.signals import SignalType, auto_type, detect_indexed_groups, interpret


class CsvFormatTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()

    def tearDown(self):
        self.files.cleanup()

    def test_reads_examples_and_keeps_first_column_as_time(self):
        """REQ 2300 / 2304 / 2308 / 2309 sur les CSV reçus."""
        table = read_csv(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        self.assertEqual(table.time_name, "index")
        self.assertEqual(table.n_samples, 1000 + 1)
        self.assertEqual(len(table.columns), 17)
        self.assertEqual(table.line_numbers[0], 2)          # ligne 1 = en-tête
        self.assertEqual(len(table.sha256), 64)

    def test_semicolon_separator_rejected(self):
        """REQ 2301 : point-virgule refusé, même avec décimale à virgule."""
        path = self.files.write("pv.csv", "t;a;b\n0;1,5;0\n10;1,6;1\n")
        with self.assertRaises(CsvReadError) as ctx:
            read_csv(path)
        self.assertEqual(ctx.exception.issues[0].requirement, "REQ_COMMON_KH_2301")

    def test_non_utf8_rejected_with_requirement(self):
        """REQ 2302 : encodage UTF-8 strict."""
        path = self.files.write("latin.csv", "t,température\n0,1\n".encode("latin-1"))
        with self.assertRaises(CsvReadError) as ctx:
            read_csv(path)
        self.assertEqual(ctx.exception.issues[-1].requirement, "REQ_COMMON_KH_2302")

    def test_bom_tolerated_and_reported(self):
        path = self.files.write("bom.csv", "﻿t,a\n0,1\n1,2\n")
        table = read_csv(path)
        self.assertEqual(table.header[0], "t")
        self.assertTrue(any(i.requirement == "REQ_COMMON_KH_2302" for i in table.issues))

    def test_metadata_lines_reported_and_skipped(self):
        """REQ 2303 : préambule et lignes « # » signalés, données lues."""
        path = self.files.write("meta.csv", "Essai 3\n# commentaire\nt,a,b\n0,1,0\n# milieu\n10,2,1\n")
        table = read_csv(path)
        self.assertEqual(table.header, ["t", "a", "b"])
        self.assertEqual(table.n_samples, 2)
        self.assertGreaterEqual(sum(i.requirement == "REQ_COMMON_KH_2303" for i in table.issues), 2)

    def test_header_names_normalized(self):
        """REQ 2309 : noms vides et doublons renommés et signalés."""
        path = self.files.write("names.csv", "t,a,,a\n0,1,2,3\n")
        table = read_csv(path)
        self.assertEqual(table.header, ["t", "a", "Colonne_3", "a_2"])
        self.assertEqual(sum(i.requirement == "REQ_COMMON_KH_2309" for i in table.issues), 2)

    def test_numeric_first_line_flagged(self):
        """REQ 2308 : une 1re ligne numérique n'est pas un en-tête."""
        table = read_csv(self.files.write("noheader.csv", "0,1,2\n10,1,2\n"))
        self.assertTrue(any(i.requirement == "REQ_COMMON_KH_2308" for i in table.issues))

    def test_malformed_rows_rejected_without_blocking(self):
        path = self.files.write("bad.csv", "t,a,b\n0,1,2\n10,1\n20,1,2,3\n30,1,2,,\n40,5,6\n")
        table = read_csv(path)
        self.assertEqual(table.n_samples, 3)               # 0, 30 (virgules finales tolérées), 40
        self.assertEqual(list(table.line_numbers), [2, 5, 6])
        rejected = [i for i in table.issues if "rejetée" in i.message]
        self.assertEqual([i.line for i in rejected], [3, 4])

    def test_size_limit(self):
        """REQ 2310 : au-delà du maximum paramétré, le fichier est refusé."""
        path = self.files.write("big.csv", counter_csv(range(5000), {"a": list(range(5000))}))
        with self.assertRaises(CsvReadError) as ctx:
            read_csv(path, max_size_mb=0.01)
        self.assertEqual(ctx.exception.issues[0].requirement, "REQ_COMMON_KH_2310")

    def test_other_extension_warned(self):
        table = read_csv(self.files.write("data.txt", "t,a\n0,1\n"))
        self.assertTrue(any(i.requirement == "REQ_COMMON_KH_2300" for i in table.issues))

    def test_empty_and_one_column_files(self):
        with self.assertRaises(CsvReadError):
            read_csv(self.files.write("empty.csv", ""))
        with self.assertRaises(CsvReadError):
            read_csv(self.files.write("one.csv", "t\n0\n1\n"))

    def test_cancellation(self):
        path = self.files.write("c.csv", counter_csv(range(50000), {"a": [1] * 50000}))
        cancel = threading.Event()
        cancel.set()
        with self.assertRaises(ReadCancelled):
            read_csv(path, cancel=cancel)

    def test_large_file_progress(self):
        """REQ 4105 : lecture par blocs avec avancement."""
        n = 120_000
        path = self.files.write("large.csv", counter_csv(range(0, n * 10, 10), {"a": [0.5] * n, "b": ["true"] * n}))
        steps = []
        table = read_csv(path, progress=steps.append)
        self.assertEqual(table.n_samples, n)
        self.assertGreater(len(steps), 3)
        self.assertLessEqual(max(steps), 1.0)

    def test_unreadable_file_isolated(self):
        """REQ 4105 / 2105 : un fichier malade est conservé avec son diagnostic."""
        source = load_source(self.files.write("pv.csv", "t;a\n0;1\n"), Settings())
        self.assertFalse(source.is_loaded)
        self.assertEqual(source.status(), Severity.ERROR)


class SignalTypeTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()

    def tearDown(self):
        self.files.cleanup()

    def _columns(self, text):
        return {c.name: c for c in read_csv(self.files.write("s.csv", text)).columns}

    def test_auto_types(self):
        """REQ 2200 / 2201 / 5202 : Bool, Float, Texte selon le contenu."""
        cols = self._columns("t,b_txt,b_num,f,const0,state,mixed\n"
                             "0,True,0,1.5,0,STOP,1\n1,false,1,2.5,0,RUN,x\n2,TRUE,1,3,0,RUN,3\n")
        self.assertIs(auto_type(cols["b_txt"]), SignalType.BOOL)
        self.assertIs(auto_type(cols["b_num"]), SignalType.BOOL)
        self.assertIs(auto_type(cols["f"]), SignalType.FLOAT)
        self.assertIs(auto_type(cols["const0"]), SignalType.FLOAT)    # constante : pas un Bool
        self.assertIs(auto_type(cols["state"]), SignalType.TEXT)
        self.assertIs(auto_type(cols["mixed"]), SignalType.FLOAT)

    def test_empty_cells_stay_empty(self):
        """Aucune valeur inventée : vide = NaN + masque « missing »."""
        cols = self._columns("t,a\n0,1.0\n1,\n2,3.0\n")
        signal = interpret(cols["a"])
        self.assertTrue(np.isnan(signal.values[1]))
        self.assertTrue(signal.missing[1])
        self.assertEqual(cols["a"].count(KIND_EMPTY), 1)

    def test_forced_bool_marks_other_numbers_invalid(self):
        cols = self._columns("t,a\n0,0\n1,1\n2,0.5\n")
        signal = interpret(cols["a"], SignalType.BOOL)
        self.assertTrue(signal.invalid[2])
        self.assertTrue(np.isnan(signal.values[2]))
        self.assertEqual(signal.format_value(1.0), "1 (vrai)")

    def test_text_type_from_numbers(self):
        cols = self._columns("t,a\n0,STOP\n1,0\n2,RUN\n")
        signal = interpret(cols["a"], SignalType.TEXT)
        self.assertEqual(signal.format_value(signal.values[1]), "0")
        self.assertEqual(signal.format_value(signal.values[2]), "RUN")

    def test_indexed_binary_groups(self):
        """REQ 2201 (groupe binaire) : DI[0..2] regroupés, mot calculé bit à bit."""
        cols = self._columns("t,DI[0],DI[1],DI[2],x\n0,1,0,1,5\n1,0,1,1,6\n2,1,,0,7\n")
        signals = {name: interpret(col) for name, col in cols.items()}
        groups = detect_indexed_groups(signals)
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0].members, ["DI[0]", "DI[1]", "DI[2]"])
        word = groups[0].word([signals[m].values for m in groups[0].members])
        self.assertEqual(list(word[:2]), [5.0, 6.0])
        self.assertTrue(np.isnan(word[2]))                 # un bit manquant : mot indéfini


if __name__ == "__main__":
    unittest.main()
