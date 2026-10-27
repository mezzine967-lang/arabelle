"""Essai d'intégration distinct de la suite rapide à délai de 60 secondes."""
import sys
import tempfile
import unittest
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from diagnostic_csv import analyse_csv


class IntegrationImportTests(unittest.TestCase):
    def test_fichier_sur_plusieurs_blocs_et_utf8_conserve_lignes(self):
        # > 1 MiB : les lectures de hachage/décodage franchissent un bloc.
        with tempfile.TemporaryDirectory() as dossier:
            p = Path(dossier) / "long.CSV"
            p.write_text("index,etat\n" + "0,é\n" * 260_000 + "1,ok\n", encoding="utf-8")
            d = analyse_csv(p)
        self.assertEqual(d.data_rows, 260001)
        self.assertEqual(d.physical_lines, 260002)
        self.assertEqual(d.time.start, 0)
        self.assertEqual(d.time.end, 1)
        self.assertFalse(d.time.partial)


if __name__ == "__main__":
    unittest.main()
