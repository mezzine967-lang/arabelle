"""Lot 2B : le Time Base Monitor montre les Δt sans inventer d'intervalle."""
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))

from base_temps import SourceTemps, examiner_source
from diagnostic_csv import CsvDiagnosticError
from moniteur_temps import construire_moniteur
from signal_csv import preparer_signal


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Matplotlib absent : rendu non vérifié")
class MoniteurQuantitatifTests(unittest.TestCase):
    def setUp(self):
        self.temporaire = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporaire.cleanup)
        self.fichier = Path(self.temporaire.name) / "signal.csv"

    def preparer(self, contenu, pas="10", tolerance="1"):
        self.fichier.write_text(contenu, encoding="utf-8")
        source = SourceTemps(
            self.fichier, unite="ms", pas_attendu=pas, tolerance=tolerance,
        )
        resultat = examiner_source(source)
        return source, resultat, preparer_signal(source, resultat, "v")

    def test_serie_contient_les_delta_et_leur_qualification(self):
        _, _, signal = self.preparer(
            "t_ms,v\n0,0\n10,1\n20,2\n35,3\n45,4\n"
        )
        self.assertEqual(signal.temps_intervalles, [10.0, 20.0, 35.0, 45.0])
        self.assertEqual(signal.deltas_temps, [10.0, 10.0, 15.0, 10.0])
        self.assertEqual(
            signal.natures_intervalles,
            ["conforme", "conforme", "jitter", "conforme"],
        )
        self.assertEqual(signal.raster_temps, 10.0)
        self.assertEqual(signal.tolerance_temps, 1.0)
        self.assertEqual(signal.origine_raster, "configure")
        with self.subTest(cas="raster indéterminé"):
            _, _, observe = self.preparer("t_ms,v\n0,0\n10,1\n30,2\n", None, None)
            self.assertIsNone(observe.raster_temps)
            self.assertEqual(observe.natures_intervalles, ["observe", "observe"])
        with self.subTest(cas="raster estimé"):
            _, _, estime = self.preparer("t_ms,v\n0,0\n10,1\n20,2\n", None, None)
            self.assertEqual(estime.raster_temps, 10.0)
            self.assertEqual(estime.origine_raster, "estime")
        with self.subTest(cas="deux Δt exacts confondus en flottants"):
            # Les abscisses restent distinctes ; ce sont les Δt 10^16 et
            # 10^16 + 1 qui ne doivent pas devenir un faux pas constant.
            with self.assertRaises(CsvDiagnosticError) as erreur:
                self.preparer("t_ms,v\n-10000000000000000,0\n0,1\n10000000000000001,2\n",
                              "10000000000000000", "0")
            self.assertEqual(erreur.exception.code, "precision_delta_graphique")

    def test_ligne_rejetee_ne_cree_pas_de_delta_a_travers_le_trou(self):
        _, _, signal = self.preparer(
            "t_ms,v\n0,0\n10,1\n20\n30,3\n40,4\n"
        )
        self.assertEqual(signal.temps_intervalles, [10.0, 40.0])
        self.assertEqual(signal.deltas_temps, [10.0, 10.0])

    def test_doublon_et_retour_restent_des_faits_distincts(self):
        _, _, signal = self.preparer(
            "t_ms,v\n0,0\n10,1\n10,2\n5,3\n15,4\n"
        )
        self.assertEqual(
            signal.natures_intervalles,
            ["conforme", "temps_duplique", "retour_arriere", "conforme"],
        )

    def test_vue_reutilise_jitter_trou_et_changement_du_moteur(self):
        with self.subTest(cas="jitter"):
            _, _, signal = self.preparer("t_ms,v\n0,0\n10,1\n20.4,2\n30.4,3\n", "10", "0.1")
            self.assertEqual(signal.natures_intervalles,
                             ["conforme", "jitter", "conforme"])
        with self.subTest(cas="trou probable"):
            _, _, signal = self.preparer("t_ms,v\n0,0\n10,1\n30,2\n40,3\n", "10", "0.1")
            self.assertEqual(signal.natures_intervalles,
                             ["conforme", "trou_probable", "conforme"])
        with self.subTest(cas="changement de fréquence probable"):
            _, _, signal = self.preparer(
                "t_ms,v\n0,0\n10,1\n20,2\n40,3\n60,4\n80,5\n90,6\n", "10", "0.1",
            )
            self.assertEqual(signal.natures_intervalles[2:5],
                             ["changement_frequence_probable"] * 3)

    def test_figure_trace_delta_raster_et_tolerance(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from matplotlib.backend_bases import ResizeEvent
        from trace_signal import creer_figure

        def verifier_vue_compacte(figure):
            canvas = FigureCanvasAgg(figure)
            figure.set_size_inches(8.1, 3.7)
            canvas.callbacks.process("resize_event", ResizeEvent("resize_event", canvas))
            canvas.draw()
            rendu = canvas.get_renderer()
            for texte in figure.texts:
                cadre = texte.get_window_extent(rendu)
                self.assertGreaterEqual(cadre.y0, 0, texte.get_text())
                self.assertLessEqual(cadre.x1, figure.bbox.x1, texte.get_text())
            libelle_x = figure.axes[1].xaxis.label.get_window_extent(rendu)
            haut_notes = max(texte.get_window_extent(rendu).y1 for texte in figure.texts)
            self.assertGreater(libelle_x.y0, haut_notes)

        source, resultat, signal = self.preparer(
            "t_ms,v\n0,0\n10,1\n20,2\n35,3\n45,4\n"
        )
        figure, _, axe_temps = creer_figure(
            signal, construire_moniteur(source, resultat),
        )
        verifier_vue_compacte(figure)
        libelles = axe_temps.get_legend_handles_labels()[1]
        self.assertIn("Dans la tolérance", libelles)
        self.assertIn("Jitter hors tolérance", libelles)
        self.assertIn("Raster saisi", libelles)
        self.assertIn("Tolérance", libelles)
        self.assertEqual(axe_temps.get_ylabel(), "Δt [ms]")
        self.assertEqual(axe_temps.get_title(loc="left"), "Time Base Monitor")
        self.assertTrue(any("écart vertical au raster" in texte.get_text() for texte in figure.texts))
        self.assertEqual(len(libelles), len(set(libelles)))
        for contenu, etiquette in (("t_ms,v\n0,0\n10,1\n30,2\n", "Δt observés"),
                                   ("t_ms,v\n0,0\n10,1\n20,2\n", "Raster estimé")):
            with self.subTest(etiquette=etiquette):
                source, resultat, signal = self.preparer(contenu, None, None)
                figure, _, axe_temps = creer_figure(signal, construire_moniteur(source, resultat))
                verifier_vue_compacte(figure)
                libelles = axe_temps.get_legend_handles_labels()[1]
                self.assertIn(etiquette, libelles)
                if signal.raster_temps is None:
                    self.assertNotIn("Dans la tolérance", libelles)
                    self.assertNotIn("Tolérance", libelles)

    def test_resume_et_dessin_preservent_les_resultats_4102(self):
        """REQ 4102 : les comptes décrivent tous les intervalles, sans mutation."""
        from copy import deepcopy
        from trace_signal import creer_figure, resumer_moniteur
        source, resultat, signal = self.preparer(
            "t_ms,v\n0,0\n10,1\n10,2\n30,3\n40,4\n", "10", "0.1")
        original = deepcopy(signal)
        diagnostic_original = deepcopy(resultat)
        resume = resumer_moniteur(signal)
        self.assertIn("1 doublon(s)", resume)
        self.assertIn("1 trou(s) probable(s)", resume)
        self.assertIn("±0.1 ms", resume)
        figure, courbe, moniteur = creer_figure(signal, construire_moniteur(source, resultat))
        # Un zoom doit conserver les coordonnées et le bilan du fichier entier.
        moniteur.set_xlim(5, 15)
        self.assertEqual(courbe.get_xlim(), moniteur.get_xlim())
        self.assertEqual(signal, original)
        self.assertEqual(resultat, diagnostic_original)
        self.assertEqual(resumer_moniteur(signal), resume)

    def test_masquage_4103_autorise_seulement_sans_avertissement(self):
        from trace_signal import creer_figure
        from vue_signal import basculer_moniteur
        for texte, attendu in (("t_ms,v\n0,0\n10,1\n20,2\n", True),
                               ("t_ms,v\n0,0\n10,1\n10,2\n", False)):
            with self.subTest(autorise=attendu):
                source, resultat, signal = self.preparer(texte, "10", "0")
                modele = construire_moniteur(source, resultat)
                self.assertEqual(modele["masquage_autorise"], attendu)
                figure, courbe, temps = creer_figure(signal, modele)
                self.assertEqual(basculer_moniteur(courbe, temps, attendu), attendu)
                self.assertEqual(temps.get_visible(), not attendu)
                if attendu:
                    self.assertEqual(courbe.get_xlabel(), temps.get_xlabel())
                    self.assertTrue(basculer_moniteur(courbe, temps, True))
                    self.assertTrue(temps.get_visible())


if __name__ == "__main__":
    unittest.main()
