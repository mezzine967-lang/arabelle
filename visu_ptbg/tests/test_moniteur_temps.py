"""Tests du modèle du Time Base Monitor, sans nécessiter d'écran graphique."""
import sys
import tempfile
import unittest
from pathlib import Path

# === 1. Importer uniquement les traitements locaux ===
PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_source
from moniteur_temps import construire_moniteur


class MoniteurTempsTests(unittest.TestCase):
    """Vérifier états, repères et interdiction de masquer en cas d'anomalie."""

    def analyser(self, texte: str, **profil):
        """Créer un CSV temporaire et retourner source, bilan et modèle."""
        dossier = tempfile.TemporaryDirectory()
        self.addCleanup(dossier.cleanup)
        chemin = Path(dossier.name) / "source.csv"
        chemin.write_text(texte, encoding="utf-8")
        source = SourceTemps(chemin, **profil)
        resultat = examiner_source(source)
        return source, resultat, construire_moniteur(source, resultat)

    def test_periode_observee_reguliere_peut_etre_masquee(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n10,0\n20,1\n")
        self.assertEqual(modele["etat"], "regulier_observe")
        self.assertTrue(modele["masquage_autorise"])

    def test_doublon_positionne_et_moniteur_force_visible(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n10,0\n10,1\n20,0\n")
        self.assertEqual(modele["etat"], "anomalie")
        self.assertFalse(modele["masquage_autorise"])
        self.assertEqual(modele["marqueurs"][0]["type"], "temps_duplique")
        self.assertEqual(modele["marqueurs"][0]["position"], 0.5)

    def test_pas_hors_tolerance_ajoute_un_repere(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n10,0\n30,1\n", pas_attendu="10", tolerance="0")
        self.assertEqual(modele["marqueurs"][0]["type"], "pas_hors_tolerance")
        self.assertEqual(modele["marqueurs"][0]["pas"], "20")
        self.assertFalse(modele["masquage_autorise"])

    def test_pas_variables_sans_profil_demandent_configuration(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n10,0\n30,1\n")
        self.assertEqual(modele["etat"], "a_configurer")
        self.assertFalse(modele["masquage_autorise"])

    # === 3. La nouvelle vue graphique doit respecter les bornes et tous les avertissements ===
    def test_retour_arriere_utilise_les_extrema_et_non_la_derniere_ligne(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n20,0\n10,1\n")
        self.assertEqual((modele["debut"], modele["fin"]), ("0", "20"))
        self.assertEqual(modele["marqueurs"][0]["position"], 0.5)

    def test_avertissement_sur_valeur_absente_empeche_masquage(self):
        _, _, modele = self.analyser("t_ms,v\n0,1\n10,\n20,1\n")
        self.assertFalse(modele["masquage_autorise"])
        self.assertEqual(modele["niveau"], "avertissement")

    def test_troncature_des_ecarts_positifs_est_signalee(self):
        texte = "t_ms,v\n" + "".join(f"{i*2},1\n" for i in range(31))
        _, _, modele = self.analyser(texte, pas_attendu="1", tolerance="0")
        self.assertEqual(modele["nombre_marqueurs"], 30)
        self.assertEqual(len(modele["marqueurs"]), 20)
        self.assertTrue(modele["marqueurs_tronques"])

    def test_point_unique_ne_certifie_pas_la_periode(self):
        _, _, modele = self.analyser("t_ms,v\n3,1\n")
        self.assertEqual(modele["etat"], "indisponible")
        self.assertFalse(modele["masquage_autorise"])


if __name__ == "__main__":
    unittest.main()
