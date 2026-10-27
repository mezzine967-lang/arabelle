"""Lot 2A : raster, jitter, trous et changements probables, sans correction."""
import sys
import tempfile
import unittest
from pathlib import Path


PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))

from base_temps import SourceTemps, examiner_source


class AnalyseTempsLot2ATests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporaire.cleanup)
        self.dossier = Path(self.temporaire.name)

    def analyser(self, temps: list[str], pas: str | None = "10", tolerance: str | None = "0.1"):
        fichier = self.dossier / "temps.csv"
        fichier.write_text(
            "horloge,signal\n" + "".join(f"{temps_csv},{i}\n" for i, temps_csv in enumerate(temps)),
            encoding="utf-8",
        )
        source = SourceTemps(
            fichier, unite="ms", pas_attendu=pas, tolerance=tolerance,
        )
        return examiner_source(source)["analyse_temporelle"]

    def test_raster_configure_et_jitter_restant_distincts(self):
        analyse = self.analyser(["0", "10", "20.4", "30.4"])
        self.assertEqual(analyse["raster"]["valeur"], "10")
        self.assertEqual(analyse["raster"]["origine"], "configure")
        self.assertEqual(analyse["raster"]["unite"], "ms")
        self.assertEqual(analyse["comptes"]["jitter"], 1)
        self.assertEqual(analyse["anomalies"][0]["ligne"], 4)
        self.assertEqual(analyse["anomalies"][0]["delta"], "10.4")

    def test_trou_probable_compte_sans_inventer_de_mesure(self):
        analyse = self.analyser(["0", "10", "30", "40"])
        self.assertEqual(analyse["comptes"]["trou_probable"], 1)
        self.assertEqual(analyse["echantillons_probablement_manquants"], 1)
        trou = next(a for a in analyse["anomalies"] if a["nature"] == "trou_probable")
        self.assertEqual(trou["ligne_precedente"], 3)
        self.assertEqual(trou["ligne"], 4)
        self.assertIn("aucune correction", trou["action"])

    def test_changement_frequence_exige_plusieurs_intervalles_consecutifs(self):
        analyse = self.analyser(["0", "10", "20", "40", "60", "80", "90"])
        self.assertEqual(analyse["comptes"]["changement_frequence_probable"], 3)
        self.assertEqual(analyse["comptes"].get("trou_probable", 0), 0)
        self.assertEqual(analyse["regles"]["intervalles_min_changement_frequence"], 3)

    def test_doublon_retour_et_timestamp_invalide_sont_separes(self):
        analyse = self.analyser(["0", "10", "10", "5", "?", "15"])
        self.assertEqual(analyse["statut"], "partiel")
        self.assertFalse(analyse["diagnostic_complet"])
        self.assertEqual(analyse["comptes"]["temps_duplique"], 1)
        self.assertEqual(analyse["comptes"]["retour_arriere"], 1)
        self.assertEqual(analyse["timestamps_invalides"], 1)
        invalide = next(a for a in analyse["anomalies"] if a["nature"] == "timestamp_invalide")
        self.assertEqual(invalide["ligne"], 6)

    def test_raster_estime_sur_le_groupe_majoritaire(self):
        analyse = self.analyser(["0", "10.1", "20.0", "30.0"], None, None)
        self.assertEqual(analyse["raster"]["origine"], "estime")
        self.assertEqual(analyse["raster"]["valeur"], "10.0")
        self.assertEqual(analyse["raster"]["tolerance"], "0.500")
        self.assertEqual(analyse["statut"], "complet")

    def test_raster_ambigu_n_est_pas_choisi(self):
        analyse = self.analyser(["0", "10", "30"], None, None)
        self.assertEqual(analyse["statut"], "insuffisant")
        self.assertEqual(analyse["raster"]["origine"], "indisponible")
        self.assertIn("aucune valeur choisie", analyse["motif"])


if __name__ == "__main__":
    unittest.main()

