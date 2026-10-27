"""Tests initiaux du lecteur : chronologie, rejets et comparaison simple.

Entrées : petits CSV construits dans des dossiers temporaires, pas les originaux.
Sortie : assertions exécutées par unittest ; aucun journal propre à ce fichier.
Dépendances : bibliothèque standard et diagnostic_csv. Ces trois cas ne valent
pas validation de tous les requis. Documentation par parties : requis 3006.
"""

# === 1. Charger le lecteur local sans dépendre du dossier de travail ===
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from diagnostic_csv import analyse_csv, compare_csv


class DiagnosticCsvTests(unittest.TestCase):
    """Vérifier des résultats calculables à la main sur de petits exemples."""

    # === 2. Cas nominal de progression temporelle ===
    def test_regular_time_base(self):
        """Trois points espacés de 20 doivent produire un pas régulier sans alerte."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "regular.csv"
            path.write_text("index,value\n0,1\n20,2\n40,3\n", encoding="utf-8")
            result = analyse_csv(path)

        self.assertEqual(result.data_rows, 3)
        self.assertEqual(result.time.regular_step, 20)
        self.assertTrue(result.time.strictly_increasing)
        self.assertEqual(result.warnings, [])

    # === 3. Défaut de structure et retour temporel, sans correction implicite ===
    def test_bad_rows_and_time_are_reported(self):
        """La ligne courte est tracée ; seul le retour arrière des lignes retenues compte."""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.csv"
            path.write_text("index,value\n0,1\n20\n20,3\n10,4\n", encoding="utf-8")
            result = analyse_csv(path)

        self.assertEqual(result.malformed_rows, [3])
        self.assertEqual(result.time.duplicate_count, 0)
        self.assertEqual(result.time.backward_count, 1)
        self.assertTrue(result.warnings)

    # === 4. Comparaison des entrées communes, avec une sortie propre au report ===
    def test_scenario_report_comparison(self):
        """Un report enrichi garde les mêmes entrées et signale sa colonne supplémentaire."""
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            scenario = root / "scenario.csv"
            report = root / "report.csv"
            scenario.write_text("index,input\n0,1\n20,2\n", encoding="utf-8")
            report.write_text("index,input,output\n0,1,0\n20,2,1\n", encoding="utf-8")
            result = compare_csv(scenario, report)

        self.assertTrue(result["same_row_count"])
        self.assertEqual(result["report_extra_columns"], ["output"])
        self.assertEqual(result["shared_column_mismatches"], {"index": 0, "input": 0})


if __name__ == "__main__":
    # Exécution autonome possible ; la découverte unittest utilise la même classe.
    unittest.main()
