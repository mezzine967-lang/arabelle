"""Essais sans écran du parcours de sélection qui alimente la fenêtre VISU."""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

# === 1. Charger le modèle de paquet sans ouvrir tkinter ni modifier les CSV ===
PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from paquet_csv import PaquetCSV, decrire_source


class PaquetCsvTests(unittest.TestCase):
    """Contrôler ajout, indépendance et correction d'un profil en erreur."""

    def test_selection_multiple_et_origines_independantes(self):
        with tempfile.TemporaryDirectory() as dossier:
            a, b = Path(dossier) / "a.csv", Path(dossier) / "b.csv"
            a.write_text("t_ms,v\n0,1\n10,0\n", encoding="utf-8")
            b.write_text("t_ms,v\n3,1\n13,0\n", encoding="utf-8")
            paquet = PaquetCSV()
            self.assertEqual(paquet.ajouter([a, b, a]), 2)
            self.assertEqual([r["diagnostic_csv"]["time"]["start"] for r in paquet.resultats], [0, 3])
            self.assertEqual(paquet.journal()["comparaison_entre_horloges"], "non_effectuee")
            self.assertIn("Comparaison avec les autres horloges : non effectuée", decrire_source(
                paquet.sources[0], paquet.resultats[0]))

    def test_configuration_locale_et_recuperation_apres_erreur(self):
        with tempfile.TemporaryDirectory() as dossier:
            a, b = Path(dossier) / "a.csv", Path(dossier) / "b.csv"
            a.write_text("index,v\n0,1\n10,0\n10,1\n30,0\n", encoding="utf-8")
            b.write_text("t_ms,v\n3,1\n13,0\n", encoding="utf-8")
            empreinte = hashlib.sha256(a.read_bytes()).hexdigest()
            paquet = PaquetCSV()
            paquet.ajouter([a, b])
            autre = paquet.resultats[1]
            erreur = paquet.configurer(0, "ms", "10", None)
            self.assertEqual(erreur["erreur"]["code"], "profil_temps_incomplet")
            valide = paquet.configurer(0, "ms", "10", "0")
            self.assertEqual(valide["evaluation_pas"]["doublons_adjacents"], 1)
            self.assertEqual(valide["evaluation_pas"]["ecarts_positifs"], 1)
            self.assertIs(paquet.resultats[1], autre)
            self.assertEqual(hashlib.sha256(a.read_bytes()).hexdigest(), empreinte)


if __name__ == "__main__":
    unittest.main()
