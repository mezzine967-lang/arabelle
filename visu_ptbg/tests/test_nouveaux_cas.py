"""Tests sur données réelles archivées et cas synthétiques complémentaires.

Entrées : couple PID et simulation archivée, lus sans exécuter les simulateurs ;
petits CSV temporaires pour les autres cas. Sortie : assertions unittest.
Dépendances : bibliothèque standard et diagnostic_csv. Les valeurs attendues
décrivent ces exemples précis, pas un schéma imposé à tous les futurs fichiers.
Requis 3006 : rôle des groupes et intention de chaque test documentés.
"""

# === 1. Dépendances et chemins vers le lecteur et les données archivées ===
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from diagnostic_csv import analyse_csv, compare_csv


class NouveauxCasTests(unittest.TestCase):
    """Vérifier les exemples reçus puis quelques formats minimaux construits ici."""

    # === 2. Non-régression sur les fichiers réels, sans les modifier ===
    def test_pid_reel(self):
        """Le couple PID conserve ses dimensions, son temps et ses entrées communes."""
        scenario = ROOT / "donnees" / "scenari0045.csv"
        report = ROOT / "donnees" / "Test_PID_P_AS_scenari0045.csv"
        s, r = analyse_csv(scenario), analyse_csv(report)
        self.assertEqual((s.data_rows, r.data_rows), (1001, 1001))
        self.assertEqual((len(s.columns), len(r.columns)), (9, 18))
        self.assertEqual(s.time.regular_step, 20)
        self.assertEqual(r.time.end, 20000)
        self.assertNotIn("output", r.constant_columns)
        self.assertTrue(all(v == 0 for v in compare_csv(scenario, report)["shared_column_mismatches"].values()))

    def test_simulation_archivee_anomalies_preservees(self):
        """Conserver les deux doublons et cellules vides, avec empreinte inchangée."""
        path = ROOT / "donnees" / "simulation10_execution1.csv"
        before = hashlib.sha256(path.read_bytes()).hexdigest()
        d = analyse_csv(path)
        self.assertEqual(d.data_rows, 10001)
        self.assertEqual(d.time.duplicate_count, 2)
        self.assertEqual(d.time.step_values, [0.0, 1.0, 2.0])
        self.assertFalse(d.time.strictly_increasing)
        self.assertEqual(d.inferred_types["cons1_state"], "texte")
        self.assertGreater(d.empty_cells_by_column["pub_output"], 0)
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), before)

    # === 3. Cas synthétiques isolés : encodage, valeurs absentes et ajout de ligne ===
    def test_bom(self):
        """Le BOM UTF-8 ne doit pas devenir un caractère du premier nom de colonne."""
        with tempfile.TemporaryDirectory() as dossier:
            path = Path(dossier) / "bom.csv"
            path.write_text("index,value\n0,1\n20,2\n", encoding="utf-8-sig")
            self.assertEqual(analyse_csv(path).columns, ["index", "value"])

    def test_texte_et_valeur_absente_non_convertis_en_zero(self):
        """Identifier une colonne textuelle et compter une sortie vide, sans zéro fictif."""
        with tempfile.TemporaryDirectory() as dossier:
            path = Path(dossier) / "etat.csv"
            path.write_text("t_ms,etat,sortie\n0,STOP,\n1,ACTIVE,1\n", encoding="utf-8")
            d = analyse_csv(path)
        self.assertEqual(d.inferred_types["etat"], "texte")
        self.assertEqual(d.empty_cells_by_column["sortie"], 1)

    def test_ligne_supplementaire_valide_acceptee(self):
        """Une nouvelle ligne conforme est retenue et prolonge la borne temporelle."""
        with tempfile.TemporaryDirectory() as dossier:
            path = Path(dossier) / "plus.csv"
            path.write_text("index,value\n0,1\n20,2\n40,3\n60,4\n", encoding="utf-8")
            d = analyse_csv(path)
        self.assertEqual(d.data_rows, 4)
        self.assertEqual(d.time.end, 60)


if __name__ == "__main__":
    # Permettre le lancement de ce seul fichier, en complément du lanceur global.
    unittest.main()
