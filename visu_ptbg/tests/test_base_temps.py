"""Tests de la revue de plusieurs horloges, sur CSV temporaires ou archivés.

Ces cas couvrent la séparation des sources et une tolérance explicitement
fournie. Ils ne prouvent ni synchronisation PLC, ni conformité globale.
"""
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

# === 1. Charger le module local sans importer les scripts de simulation ===
PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_paquet, examiner_source


class BaseTempsTests(unittest.TestCase):
    """Créer de petits CSV dont les écarts attendus sont calculables à la main."""

    def setUp(self):
        """Réserver un dossier isolé pour chaque essai."""
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.dossier = Path(self.temporary.name)

    def fichier(self, nom: str, texte: str) -> Path:
        """Créer un CSV UTF-8 éphémère et retourner son chemin."""
        chemin = self.dossier / nom
        chemin.write_text(texte, encoding="utf-8")
        return chemin

    # === 2. Deux sources avec des origines décalées gardent leurs propres temps ===
    def test_deux_fichiers_dephases_restent_independants(self):
        a = self.fichier("a.csv", "t_ms,v\n0,0\n10,1\n20,0\n")
        b = self.fichier("b.csv", "t_ms,v\n3,0\n13,1\n23,0\n")
        paquet = examiner_paquet([
            SourceTemps(a, pas_attendu="10", tolerance="0", unite="ms"),
            SourceTemps(b, pas_attendu="10", tolerance="0", unite="ms"),
        ])
        self.assertEqual(paquet["comparaison_entre_horloges"], "non_effectuee")
        self.assertEqual([s["diagnostic_csv"]["time"]["start"] for s in paquet["sources"]], [0, 3])
        self.assertTrue(all(s["evaluation_pas"]["pas_conforme_sur_lignes_lues"] for s in paquet["sources"]))

    # === 3. Une tolérance choisie évite de qualifier un petit jitter de défaut ===
    def test_pas_et_tolerance_configures(self):
        chemin = self.fichier("jitter.csv", "temps,v\n0,0\n10.1,1\n20.05,2\n")
        evaluation = examiner_source(SourceTemps(chemin, pas_attendu="10", tolerance="0.2"))["evaluation_pas"]
        self.assertTrue(evaluation["pas_conforme_sur_lignes_lues"])
        self.assertEqual(evaluation["ecarts_positifs"], 0)

    # === 4. Doublons et grands écarts restent distincts et localisables ===
    def test_anomalies_du_fichier_signalees_sans_correction(self):
        chemin = self.fichier("irregulier.csv", "t_ms,v\n0,0\n10,1\n10,2\n30,3\n")
        resultat = examiner_source(SourceTemps(chemin, pas_attendu="10", tolerance="0"))
        evaluation = resultat["evaluation_pas"]
        self.assertFalse(evaluation["pas_conforme_sur_lignes_lues"])
        self.assertEqual((evaluation["doublons_adjacents"], evaluation["ecarts_positifs"]), (1, 1))
        self.assertEqual(evaluation["exemples_ecarts_positifs"][0]["ligne"], 5)
        self.assertEqual(evaluation["exemples_ecarts_positifs"][0]["pas_observe"], "20")
        self.assertEqual(resultat["diagnostic_csv"]["time"]["duplicate_count"], 1)

    # === 5. Une ligne rejetée interdit de conclure sur les voisins retenus ===
    def test_rejet_suspend_evaluation_pas(self):
        chemin = self.fichier("ligne_courte.csv", "t_ms,v\n0,0\n10\n20,2\n")
        resultat = examiner_source(SourceTemps(chemin, pas_attendu="10", tolerance="0"))
        self.assertEqual(resultat["diagnostic_csv"]["rejected_rows"][0]["line_start"], 3)
        self.assertFalse(resultat["evaluation_pas"]["effectuee"])

    # === 6. Un refus sur une source ne masque pas les autres fichiers ===
    def test_source_absente_et_profil_incomplet_isoles(self):
        valide = self.fichier("ok.csv", "t_ms,v\n0,0\n1,1\n")
        paquet = examiner_paquet([
            SourceTemps(self.dossier / "absent.csv"),
            SourceTemps(valide, pas_attendu="1"),
            SourceTemps(valide, pas_attendu="1", tolerance="0"),
        ])
        self.assertEqual(paquet["sources"][0]["erreur"]["code"], "acces_fichier")
        self.assertEqual(paquet["sources"][1]["erreur"]["code"], "profil_temps_incomplet")
        self.assertTrue(paquet["sources"][2]["evaluation_pas"]["pas_conforme_sur_lignes_lues"])

    # === 7. Le fichier fourni conserve ses octets et expose ses anomalies ===
    def test_simulation_archivage_sans_modification(self):
        chemin = PROJET / "donnees" / "simulation10_execution1.csv"
        empreinte_avant = hashlib.sha256(chemin.read_bytes()).hexdigest()
        evaluation = examiner_source(SourceTemps(chemin, pas_attendu="1", tolerance="0", unite="ms"))["evaluation_pas"]
        self.assertTrue(evaluation["effectuee"])
        self.assertEqual((evaluation["doublons_adjacents"], evaluation["ecarts_positifs"]), (2, 1))
        self.assertEqual(evaluation["exemples_ecarts_positifs"][0]["pas_observe"], "2")
        self.assertEqual(hashlib.sha256(chemin.read_bytes()).hexdigest(), empreinte_avant)


if __name__ == "__main__":
    unittest.main()
