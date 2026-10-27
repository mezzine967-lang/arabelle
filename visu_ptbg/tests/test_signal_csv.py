"""Garanties du premier tracé : provenance, absences, précision et temps propre."""
import importlib.util
import math
import sys
import tempfile
import unittest
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_source
from diagnostic_csv import CsvDiagnosticError
from moniteur_temps import construire_moniteur
from paquet_csv import PaquetCSV
from signal_csv import preparer_signal


class SignalCsvTests(unittest.TestCase):
    """Créer de petits fichiers dont le résultat attendu est calculable à la main."""

    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.chemin = Path(self.dossier.name) / "test.csv"

    def analyser(self, texte):
        """Lire un CSV neuf et fournir le diagnostic utilisé par la préparation."""
        self.chemin.write_text(texte, encoding="utf-8")
        source = SourceTemps(self.chemin)
        return source, examiner_source(source)

    # === 1. Aucune réparation silencieuse ni interpolation des points ===
    def test_ordre_doublon_retour_absence_et_zero_conserves(self):
        source, resultat = self.analyser("t_ms,v\n3,0\n13,2\n13,\n8,4\n18,texte\n")
        signal = preparer_signal(source, resultat, "v")
        self.assertEqual(signal.temps, [3, 13, 13, 8, 18])
        self.assertEqual(signal.valeurs[:2], [0, 2])
        self.assertTrue(math.isnan(signal.valeurs[2]))
        self.assertEqual(signal.valeurs[3], 4)
        self.assertTrue(math.isnan(signal.valeurs[4]))
        self.assertEqual(signal.valeurs_absentes, 2)
        self.assertEqual(signal.lignes, [2, 3, 4, 5, 6])

    def test_ligne_rejetee_reste_comptee(self):
        source, resultat = self.analyser("t_ms,v\n0,0\n10\n20,2\n")
        signal = preparer_signal(source, resultat, "v")
        self.assertEqual(signal.temps, [0, 20])
        self.assertEqual(signal.lignes, [2, 4])
        self.assertEqual(signal.lignes_rejetees, 1)

    # === 2. Les refus protègent les temps et le lien avec le diagnostic courant ===
    def test_source_changee_impose_un_nouveau_diagnostic(self):
        source, resultat = self.analyser("t_ms,v\n0,0\n1,1\n")
        self.chemin.write_text("t_ms,v\n0,0\n2,1\n", encoding="utf-8")
        with self.assertRaises(CsvDiagnosticError) as erreur:
            preparer_signal(source, resultat, "v")
        self.assertEqual(erreur.exception.code, "fichier_modifie")

    def test_precision_float_ne_cree_pas_de_faux_doublon(self):
        source, resultat = self.analyser("t_ms,v\n9007199254740992,0\n9007199254740993,1\n")
        self.assertEqual(resultat["diagnostic_csv"]["time"]["duplicate_count"], 0)
        with self.assertRaises(CsvDiagnosticError) as erreur:
            preparer_signal(source, resultat, "v")
        self.assertEqual(erreur.exception.code, "precision_temps_graphique")

    def test_signal_texte_ou_temps_invalide_refuses_sans_crash(self):
        for texte, code in (("t_ms,v\n0,texte\n1,abc\n", "signal_non_numerique"),
                            ("t_ms,v\n0,0\n?,1\n", "temps_non_tracable")):
            with self.subTest(code=code):
                source, resultat = self.analyser(texte)
                with self.assertRaises(CsvDiagnosticError) as erreur:
                    preparer_signal(source, resultat, "v")
                self.assertEqual(erreur.exception.code, code)

    def test_enregistrement_ne_peut_pas_ecraser_un_fichier(self):
        self.chemin.write_text("t_ms,v\n0,0\n1,1\n", encoding="utf-8")
        original = self.chemin.read_bytes()
        paquet = PaquetCSV()
        paquet.ajouter([self.chemin])
        with self.assertRaises(ValueError):
            paquet.enregistrer_journal(self.chemin)
        journal = Path(self.dossier.name) / "preuve.json"
        paquet.enregistrer_journal(journal)
        avant = journal.read_bytes()
        with self.assertRaises(ValueError):
            paquet.enregistrer_journal(journal)
        self.assertEqual(journal.read_bytes(), avant)
        self.assertEqual(self.chemin.read_bytes(), original)


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Matplotlib absent : essais de rendu non exécutés")
class FigureSignalTests(unittest.TestCase):
    """Vérifier le rendu Agg réel, sans ouverture d'une fenêtre tkinter."""

    def test_points_et_reperes_partagent_les_temps_et_le_zoom(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from trace_signal import creer_figure
        source = SourceTemps(PROJET / "donnees/simulation10_execution1.csv",
                             colonne_temps="t_ms", unite="ms", pas_attendu="1", tolerance="0")
        resultat = examiner_source(source)
        signal = preparer_signal(source, resultat, "source")
        figure, courbe, temps = creer_figure(signal, construire_moniteur(source, resultat))
        FigureCanvasAgg(figure).draw()
        self.assertEqual([x for x in courbe.lines[0].get_xdata() if math.isfinite(x)], signal.temps)
        self.assertEqual(courbe.lines[0].get_linestyle(), "-")
        # Les points Δt sont désormais tracés sur cet axe. Repérer les traits
        # verticaux par leur géométrie au lieu de dépendre de l'ordre interne
        # des artistes Matplotlib.
        reperes = []
        for ligne in temps.lines:
            x = list(ligne.get_xdata())
            if len(x) == 2 and x[0] == x[1]:
                reperes.append(x[0])
        self.assertEqual(reperes, [1006, 9815, 4986])
        courbe.set_xlim(990, 1040)
        self.assertEqual(temps.get_xlim(), (990, 1040))
        self.assertEqual(temps.get_xlabel(), "t_ms [ms]")

    def test_croix_sur_courbe_pour_champ_vide_et_vrais_zeros_conserves(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from trace_signal import creer_figure
        with tempfile.TemporaryDirectory() as dossier:
            p = Path(dossier) / "absences.csv"
            p.write_text("t,v\n0,0\n1,\n2,5\n3,texte\n4,0\n", encoding="utf-8")
            s = SourceTemps(p)
            r = examiner_source(s)
            signal = preparer_signal(s, r, "v")
            fig, courbe, moniteur = creer_figure(signal, construire_moniteur(s, r))
            FigureCanvasAgg(fig).draw()
            self.assertEqual(signal.indices_vides, [1])
            self.assertEqual(signal.indices_invalides, [3])
            croix = [ligne for ligne in courbe.lines if ligne.get_marker() == "x"]
            self.assertEqual([list(l.get_xdata()) for l in croix], [[0, 2]])
            self.assertEqual([list(l.get_ydata()) for l in croix], [[0, 5]])
            self.assertEqual(len(fig.axes), 2)
            y = courbe.lines[0].get_ydata()
            self.assertTrue(math.isnan(y[1]) and math.isnan(y[3]))
            self.assertEqual((y[0], y[2], y[4]), (0, 5, 0))
            courbe.set_xlim(0.5, 3.5)
            self.assertEqual(moniteur.get_xlim(), (0.5, 3.5))

    def test_intervalle_hors_pas_marque_sans_creer_echantillon(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from trace_signal import creer_figure
        with tempfile.TemporaryDirectory() as dossier:
            p = Path(dossier) / "trou.csv"
            p.write_text("t,v\n0,1\n1,2\n3,4\n", encoding="utf-8")
            s = SourceTemps(p, pas_attendu="1", tolerance="0", unite="ms")
            r = examiner_source(s)
            signal = preparer_signal(s, r, "v")
            fig, courbe, moniteur = creer_figure(signal, construire_moniteur(s, r))
            FigureCanvasAgg(fig).draw()
            self.assertEqual([x for x in courbe.lines[0].get_xdata() if math.isfinite(x)], [0, 1, 3])
            self.assertFalse(any(l.get_marker() == "x" for l in courbe.lines))
            self.assertTrue(math.isnan(courbe.lines[0].get_xdata()[2]))  # coupure, pas mesure inventée
            self.assertEqual(len(courbe.patches), 1)
            self.assertTrue(any("perte de données non prouvée" in t.get_text() for t in fig.texts))


if __name__ == "__main__":
    unittest.main()
