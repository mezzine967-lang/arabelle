"""Essais du lot CSV : parcours récursif, isolation et temps partiellement lisible.

Les fichiers sont synthétiques et conservés sous un dossier temporaire ; la
suite vérifie leur intégrité sans toucher aux CSV reçus de Sébastien.
"""
import contextlib
import hashlib
import io
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from decouverte_csv import decouvrir_csv
from diagnostic_csv import CsvDiagnosticError, analyse_csv, read_csv
from paquet_csv import PaquetCSV


class ImportLot1Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def creer(self, relative, texte):
        p = self.root / "donnees" / relative
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(texte, encoding="utf-8")
        return p

    def test_sous_dossiers_casse_extension_et_fichier_malade_isole(self):
        valide = self.creer("A.CSV", "index,v\n0,1\n1,2\n")
        degrade = self.creer("sous/B.cSv", "index,v\n0,1\n2\n3,3\n")
        refuse = self.creer("sous/C.csv", "index,v,v\n0,1,2\n")
        self.creer("sous/sauvegarde.csv.bak", "index,v\n0,1\n")
        avant = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in (valide, degrade, refuse)}
        chemins = decouvrir_csv(self.root / "donnees")
        self.assertEqual(chemins, [valide, degrade, refuse])
        paquet = PaquetCSV()
        self.assertEqual(paquet.ajouter_dossier(self.root / "donnees"), 3)
        self.assertEqual(paquet.ajouter_dossier(self.root / "donnees"), 0)
        self.assertEqual(paquet.resultats[0]["diagnostic_csv"]["data_rows"], 2)
        self.assertEqual(paquet.resultats[1]["diagnostic_csv"]["rejected_rows"][0]["line_start"], 3)
        self.assertEqual(paquet.resultats[2]["erreur"]["code"], "colonnes_dupliquees")
        self.assertEqual({p: hashlib.sha256(p.read_bytes()).hexdigest() for p in avant}, avant)

    def test_demo_ne_compare_pas_des_fichiers_ajoutes_arbitrairement(self):
        from demarrer_diagnostic import main
        self.creer("autre/a.csv", "t_ms,x\n0,1\n1,2\n")
        self.creer("autre/b.CSV", "t_ms,x\n0,5\n1,6\n")
        with patch("demarrer_diagnostic.PROJET", self.root), contextlib.redirect_stdout(io.StringIO()):
            bilan = main()
        self.assertEqual(len(bilan["fichiers"]), 2)
        self.assertEqual(bilan["comparaisons"], [])

    def test_premiere_colonne_est_le_temps_quel_que_soit_son_nom(self):
        inconnu = self.creer("inconnu.csv", "compteur_machine,v\n0,1\n1,2\n")
        diagnostic = analyse_csv(inconnu)
        self.assertEqual(diagnostic.time.column, "compteur_machine")
        self.assertEqual(diagnostic.time_candidates, ["compteur_machine"])

    def test_autre_nom_temporel_ne_remplace_pas_la_premiere_colonne(self):
        double = self.creer(
            "double.csv",
            "timestamp_ideal_ms,timestamp_reel_ms,v\n0,100,2\n1,101,3\n",
        )
        diagnostic = analyse_csv(double)
        self.assertEqual(diagnostic.time.column, "timestamp_ideal_ms")
        self.assertEqual(diagnostic.time.start, 0)
        with self.assertRaises(CsvDiagnosticError) as erreur:
            analyse_csv(double, time_column="timestamp_reel_ms")
        self.assertEqual(erreur.exception.code, "premiere_colonne_temps")

    def test_temps_invalide_ne_joint_pas_ses_voisins_et_garde_autres_constats(self):
        p = self.creer("partiel.csv", "t_ms,v\n0,1\n1,2\n?,3\n3,4\n3,5\n")
        d = analyse_csv(p)
        self.assertFalse(d.time.numeric)
        self.assertTrue(d.time.partial)
        self.assertEqual(d.time.invalid_lines, [4])
        self.assertEqual(d.time.local_interval_count, 2)
        self.assertEqual(d.time.uncalculable_interval_count, 2)
        self.assertEqual(d.time.duplicate_count, 1)
        self.assertEqual(d.time.anomalies[0]["line"], 6)
        self.assertEqual(d.time.step_values, [0, 1])
        self.assertIsNone(d.time.regular_step)

    def test_rejet_interrompt_le_pas_sans_effacer_un_retour_local(self):
        p = self.creer("rejet.csv", "t_ms,v\n0,1\n1\n2,2\n1,3\n")
        d = analyse_csv(p)
        self.assertTrue(d.time.partial)
        self.assertEqual(d.time.local_interval_count, 1)
        self.assertEqual(d.time.uncalculable_interval_count, 1)
        self.assertEqual(d.time.backward_count, 1)
        self.assertEqual(d.time.anomalies[0]["line"], 5)

    def test_csv_change_entre_controle_et_parsing_est_refuse(self):
        import diagnostic_csv
        p = self.creer("course.csv", "index,v\n0,1\n1,2\n")
        lecture_reelle = diagnostic_csv._read_text
        compte = 0

        def modifier(*args, **kwargs):
            nonlocal compte
            compte += 1
            resultat = lecture_reelle(*args, **kwargs)
            if compte == 1:
                p.write_text("index,v\n0,1\n2,2\n", encoding="utf-8")
            return resultat

        with patch("diagnostic_csv._read_text", side_effect=modifier):
            with self.assertRaises(CsvDiagnosticError) as exc:
                read_csv(p)
        self.assertEqual(exc.exception.code, "fichier_modifie")

    def _changer_pendant_lecture(self, chemin, contenu_temporaire):
        """Simuler un producteur qui change puis rétablit le CSV entre contrôles."""
        import diagnostic_csv
        original = chemin.read_bytes()
        controle_reel = diagnostic_csv._read_text
        appels = 0

        def controle(*args, **kwargs):
            nonlocal appels
            appels += 1
            if appels == 2:
                chemin.write_bytes(original)
            resultat = controle_reel(*args, **kwargs)
            if appels == 1:
                chemin.write_bytes(contenu_temporaire)
            return resultat

        return patch("diagnostic_csv._read_text", side_effect=controle)

    def test_octets_interpretes_correspondent_a_empreinte_meme_si_csv_retabli(self):
        chemin = self.creer("temporaire.csv", "index,v\n0,1\n1,2\n")
        with self._changer_pendant_lecture(chemin, b"index,v\n0,8\n1,9\n"):
            with self.assertRaises(CsvDiagnosticError) as erreur:
                read_csv(chemin)
        self.assertEqual(erreur.exception.code, "fichier_modifie")

    def test_croissance_pendant_parsing_respecte_limite(self):
        chemin = self.creer("grandit.csv", "index,v\n0,1\n")
        with self._changer_pendant_lecture(chemin, b"index,v\n" + b"0,1\n" * 100):
            with self.assertRaises(CsvDiagnosticError) as erreur:
                read_csv(chemin, max_bytes=32)
        self.assertEqual(erreur.exception.code, "fichier_trop_grand")

    def test_nul_apparu_pendant_parsing_refuse(self):
        chemin = self.creer("nul.csv", "index,v\n0,1\n")
        with self._changer_pendant_lecture(chemin, b"index,v\n0,\x00\n"):
            with self.assertRaises(CsvDiagnosticError) as erreur:
                read_csv(chemin)
        self.assertEqual(erreur.exception.code, "caractere_nul")

    def test_encodage_change_ne_bloque_pas_fichier_suivant(self):
        malade = self.creer("malade.csv", "index,v\n0,1\n")
        sain = self.creer("sain.csv", "index,v\n0,2\n1,3\n")
        paquet = PaquetCSV()
        with self._changer_pendant_lecture(malade, b"index,v\n0,\xff\n"):
            paquet.ajouter([malade, sain])
        self.assertEqual(paquet.resultats[0]["erreur"]["code"], "encodage_invalide")
        self.assertEqual(paquet.resultats[1]["diagnostic_csv"]["data_rows"], 2)

    def test_tous_temps_invalides_comptent_les_couples_non_calculables(self):
        chemin = self.creer("temps_invalides.csv", "t_ms,v\n?,1\n?,2\n?,3\n")
        temps = analyse_csv(chemin).time
        self.assertTrue(temps.partial)
        self.assertEqual(temps.local_interval_count, 0)
        self.assertEqual(temps.uncalculable_interval_count, 2)
        self.assertIsNone(temps.duplicate_count)
        self.assertIsNone(temps.regular_step)

if __name__ == "__main__":
    unittest.main()
