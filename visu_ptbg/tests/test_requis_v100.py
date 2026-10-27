"""Cas métier décidés par Mourad : groupe Bool, suivi et condition par ligne."""
import math
from pathlib import Path
import sys
import tempfile
from dataclasses import replace
from threading import Event
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from base_temps import SourceTemps, examiner_source
from signal_csv import preparer_signal
from moniteur_temps import construire_moniteur
from curseurs import Curseurs
from groupe_binaire import creer_figure_groupe, verifier_groupe
from trace_signal import creer_figure
from matplotlib.backends.backend_agg import FigureCanvasAgg


class NouveauxRequisTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fichier = Path(self.temp.name) / "plc.csv"
        # Les doublons temporels ont des Bool différents : une jointure au
        # timestamp aurait autorisé des mesures interdites.
        self.fichier.write_text("t,v,a,b\n0,10,true,0\n1,20,false,1\n1,30,true,\n"
                                "2,40,,0\n3,50,FAILED,1\n4,,true,0\n5,60,true,1\n", encoding="utf-8")
        self.source = SourceTemps(self.fichier)
        self.resultat = examiner_source(self.source)
        self.modele = construire_moniteur(self.source, self.resultat)

    def signal(self, colonne, typage="Auto"):
        return preparer_signal(self.source, self.resultat, colonne, typage)

    def curseurs(self):
        signal = self.signal("v")
        fig, axe, temps = creer_figure(signal, self.modele)
        FigureCanvasAgg(fig)
        self.addCleanup(fig.clear)
        lectures = []
        curseurs = Curseurs(fig, axe, temps, signal, lectures.append)
        return curseurs, lectures

    def test_5402_suivi_selectionne_les_mesures_et_conserve_les_doublons(self):
        c, lectures = self.curseurs()
        c.choisir("Vertical")
        event = SimpleNamespace(inaxes=c.axe, xdata=1.1)
        c._mouvement(event)
        self.assertIsNone(c.positions[0])
        c.suivi = True
        c._mouvement(event)
        self.assertEqual(c.positions[0], (1, [1, 2]))
        self.assertIn("v=20", lectures[-1])
        self.assertIn("v=30", lectures[-1])
        compte = len(lectures)
        c._mouvement(SimpleNamespace(inaxes=c.axe, xdata=1.2))
        self.assertEqual(len(lectures), compte)

    def test_5402_suivi_respecte_zoom_axes_et_cible_double(self):
        c, _ = self.curseurs()
        c.suivi = True
        c.choisir("Double vertical")
        c.cible = 1
        c.figure.canvas.toolbar = SimpleNamespace(mode="zoom rect")
        c._mouvement(SimpleNamespace(inaxes=c.axe, xdata=4))
        self.assertEqual(c.positions, [None, None])
        c.figure.canvas.toolbar = None
        c._mouvement(SimpleNamespace(inaxes=c.moniteur, xdata=4))
        self.assertEqual(c.positions, [None, None])
        c._mouvement(SimpleNamespace(inaxes=c.axe, xdata=4))
        self.assertIsNone(c.positions[0])
        self.assertEqual(c.positions[1][0], 4)
        c.detruire()

    def test_5407_bool_vrai_sur_meme_ligne_uniquement(self):
        c, lectures = self.curseurs()
        c.definir_condition(self.signal("a", "Bool"))
        self.assertEqual(c.placer_horizontal(20), [0])  # égalité : première mesure
        self.assertEqual(c.placer_horizontal(29), [2])
        self.assertIn("v=30", lectures[-1])
        self.assertNotIn("v=20", lectures[-1])
        self.assertEqual(c.placer_horizontal(50), [6])  # FAILED exclu
        self.assertNotIn("v=50", lectures[-1])
        self.assertIn("a = vrai", c.annotation.get_text())

    def test_5407_aucun_bool_vrai_et_retrait_condition(self):
        c, lectures = self.curseurs()
        a = self.signal("a", "Bool")
        c.definir_condition(replace(a, valeurs=[0, 0, math.nan, math.nan, math.nan, 0, 0]))
        self.assertEqual(c.placer_horizontal(20), [])
        self.assertFalse(c.horizontale.get_visible())
        self.assertIn("Aucune mesure", lectures[-1])
        c.definir_condition(None)
        self.assertEqual(c.placer_horizontal(20), [1])

    def test_5407_refuse_autre_fichier_autre_hash_et_float(self):
        c, _ = self.curseurs()
        a = self.signal("a", "Bool")
        for autre in (replace(a, fichier="autre.csv"), replace(a, sha256="autre"), self.signal("v")):
            with self.assertRaises(ValueError):
                c.definir_condition(autre)

    def test_2201_groupe_mesures_brutes_absences_et_moniteur(self):
        signaux = [self.signal(c, "Bool") for c in ("a", "b")]
        avant = self.fichier.read_bytes()
        fig, axe, temps = creer_figure_groupe(signaux, self.modele)
        self.addCleanup(fig.clear)
        FigureCanvasAgg(fig).draw()
        self.assertEqual(temps.get_title(loc="left"), "Time Base Monitor")
        self.assertEqual(list(axe.lines[0].get_ydata())[:2], [4, 3])
        self.assertTrue(math.isnan(axe.lines[0].get_ydata()[3]))
        self.assertEqual(signaux[0].valeurs[:2], [1, 0])
        self.assertEqual(signaux[1].indices_vides, [2])
        self.assertEqual(signaux[0].indices_invalides, [4])
        self.assertEqual(self.fichier.read_bytes(), avant)
        from rapport_pdf import capturer
        capture = capturer(SimpleNamespace(figure=fig, axe_signal=axe, axe_temps=temps,
                                           signal=signaux[0], signaux=signaux))
        self.assertEqual(capture.signal, "a, b")
        self.assertTrue(capture.image.startswith(b"\x89PNG"))

    def test_2201_refuse_groupe_ambigu_ou_non_bool(self):
        a, b = self.signal("a", "Bool"), self.signal("b", "Bool")
        for groupe in ([a], [a, a], [a, self.signal("v")], [a, replace(b, sha256="autre")]):
            with self.assertRaises(ValueError):
                verifier_groupe(groupe)

    def test_2201_colonne_entierement_vide_conservee_sans_faux_etat(self):
        self.fichier.write_text("t,v,a,b\n0,10,true,\n1,20,false,\n", encoding="utf-8")
        self.resultat = examiner_source(self.source)
        self.modele = construire_moniteur(self.source, self.resultat)
        b = preparer_signal(self.source, self.resultat, "b", "Bool", autoriser_vide=True)
        self.assertTrue(all(math.isnan(v) for v in b.valeurs))
        self.assertEqual(b.indices_vides, [0, 1])
        self.assertEqual(b.indices_croix, [])
        fig, _, _ = creer_figure_groupe([self.signal("a", "Bool"), b], self.modele)
        self.addCleanup(fig.clear)
        FigureCanvasAgg(fig).draw()
        c, lectures = self.curseurs()
        c.definir_condition(b)
        self.assertEqual(c.placer_horizontal(10), [])
        self.assertIn("Aucune mesure", lectures[-1])

    def test_4105_export_processus_et_annulation_preservent_fichiers(self):
        from rapport_pdf import Capture, PageRapport, exporter_pdf_en_fond
        from io import BytesIO
        from matplotlib.figure import Figure
        fig = Figure(figsize=(1, 1))
        fig.add_subplot().plot([0, 1], [1, 0])
        image = BytesIO()
        fig.savefig(image, format="png")
        pages = (PageRapport((Capture(image.getvalue(), str(self.fichier), "a" * 64, "v", "", "2026-10-27"),)),)
        champs = dict(emetteur="Test", projet="PLC", unite="Simulation")
        destination = Path(self.temp.name) / "rapport.pdf"
        annulation = Event()
        exporter_pdf_en_fond(destination, pages, annulation, lambda x: None, **champs)
        avant = destination.read_bytes()
        self.assertTrue(avant.startswith(b"%PDF"))
        with self.assertRaises(ValueError):
            exporter_pdf_en_fond(destination, pages, annulation, lambda x: None, **champs)
        self.assertEqual(destination.read_bytes(), avant)
        annule = destination.with_name("annule.pdf")
        exporter_pdf_en_fond(annule, pages, annulation, lambda x: annulation.set(), **champs)
        self.assertFalse(annule.exists())


if __name__ == "__main__":
    unittest.main()
