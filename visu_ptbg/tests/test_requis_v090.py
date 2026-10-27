"""Régressions des nouveaux parcours ; identifiants requis dans les noms.

Les tests de calcul et de rendu utilisent des fichiers temporaires et Agg.
Ils ne remplacent pas les essais Tkinter natifs sous Windows 11 / SLES.
"""
import io
import math
import sys
import tempfile
import threading
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_source
from signal_csv import preparer_signal
from moniteur_temps import construire_moniteur
from curseurs import LecteurEchantillons, Curseurs, meme_horloge
from taches import TacheFond, importer_copie
from paquet_csv import PaquetCSV


class RequisSignalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fichier = Path(self.temp.name) / "source.csv"

    def signal(self, texte, type_signal="Auto", colonne="v"):
        self.fichier.write_text(texte, encoding="utf-8")
        source = SourceTemps(self.fichier)
        resultat = examiner_source(source)
        return preparer_signal(source, resultat, colonne, type_signal), construire_moniteur(source, resultat)

    def test_2200_bool_textuel_et_croix_limitees_aux_vides(self):
        s, _ = self.signal("t,v\n0,true\n1,\n2,false\n3,FAILED\n4,true\n", "Bool")
        self.assertEqual(s.type_signal, "Bool")
        self.assertEqual([s.valeurs[i] for i in (0,2,4)], [1,0,1])
        self.assertEqual(s.indices_vides, [1])
        self.assertEqual(s.indices_invalides, [3])
        self.assertEqual(s.indices_croix, [0,2])
        self.assertTrue(math.isnan(s.valeurs[3]))

    def test_2200_2201_auto_ne_confond_pas_mesure_01_et_bool(self):
        s, _ = self.signal("t,v\n0,0\n1,1\n")
        self.assertEqual(s.type_signal, "Float")
        s, _ = self.signal("t,v\n0,0\n1,1\n2,2\n", "Bool")
        self.assertEqual(s.type_signal, "Bool")
        self.assertEqual(s.indices_invalides, [2])
        s, _ = self.signal("t,v\n0,true\n1,false\n")
        self.assertEqual(s.type_signal, "Bool")

    def test_5401_aucune_valeur_inventee_dans_manque_et_doublons(self):
        s, _ = self.signal("t,v\n10,3.1234567890123456789\n20,\n30,5\n30,6\n5,2\n")
        lecteur = LecteurEchantillons(s)
        self.assertEqual(lecteur.proche(21), (20, [1]))
        self.assertIn("ABSENTE", lecteur.decrire([1]))
        self.assertEqual(lecteur.proche(29), (30, [2,3]))
        self.assertIn("3.1234567890123456789", lecteur.decrire([0]))
        self.assertEqual(s.temps, [10,20,30,30,5])
        with self.assertRaises(ValueError):
            lecteur.proche(math.nan)

    def test_5405_horloges_distinctes_pas_de_liaison(self):
        s, _ = self.signal("t,v\n0,1\n1,2\n")
        for autre in (replace(s, fichier="autre.csv"), replace(s, sha256="different"),
                      replace(s, unite_temps="s")):
            self.assertFalse(meme_horloge(s, autre))
        self.assertTrue(meme_horloge(s, replace(s, colonne="autre")))

    def test_5408_xy_sans_faux_couple_ni_interpolation(self):
        from vue_xy import couples_xy, figure_xy
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        s, modele = self.signal("t,v,w\n0,1,4\n1,,5\n2,3,\n3,7,8\n")
        source = SourceTemps(self.fichier)
        w = preparer_signal(source, examiner_source(source), "w")
        self.assertEqual(couples_xy(s,w), [(1,4,0,0,2), (7,8,3,3,5)])
        with self.assertRaises(ValueError):
            couples_xy(s, replace(w, fichier="autre.csv"))
        fig, axe, temps, _, _ = figure_xy(s,w,modele)
        FigureCanvasAgg(fig).draw()
        bornes_temps = temps.get_xlim()
        axe.set_xlim(2,5)
        self.assertEqual(temps.get_xlim(), bornes_temps)
        self.assertEqual(axe.get_xlabel(), "v")

    def test_5400_5403_curseurs_lecture_et_limites_preservees(self):
        from trace_signal import creer_figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        s, modele = self.signal("t,v\n100,1\n110,\n120,3\n")
        fig, axe, temps = creer_figure(s, modele)
        FigureCanvasAgg(fig)
        limites = axe.get_xlim()
        lectures = []
        curseurs = Curseurs(fig, axe, temps, s, lectures.append)
        self.assertEqual(axe.get_xlim(), limites)
        curseurs.choisir("Double vertical")
        curseurs.placer(101, 0)
        curseurs.placer(109, 1)
        self.assertEqual([c.get_xdata()[0] for c in curseurs.lignes], [100,110])
        self.assertIn("ABSENTE", lectures[-1])
        self.assertIn("C2: t=110", curseurs.annotation.get_text())
        curseurs.choisir("Aucun")
        self.assertFalse(any(c.get_visible() for c in curseurs.lignes))

    def test_5402_lectures_de_toutes_les_courbes(self):
        from trace_signal import creer_figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        s, modele = self.signal("t,v,w\n0,1,4\n1,2,5\n")
        source = SourceTemps(self.fichier)
        w = preparer_signal(source, examiner_source(source), "w")
        fig, axe, temps = creer_figure(s, modele)
        FigureCanvasAgg(fig)
        lectures = []
        curseurs = Curseurs(fig, axe, temps, s, lectures.append)
        curseurs.ajouter(w)
        curseurs.placer(1)
        self.assertIn("v=2", lectures[-1])
        self.assertIn("w=5", lectures[-1])

    def test_5406_horizontal_refuse_sur_bool(self):
        from trace_signal import creer_figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        s, modele = self.signal("t,v\n0,true\n1,false\n")
        fig, axe, temps = creer_figure(s, modele)
        FigureCanvasAgg(fig)
        curseurs = Curseurs(fig, axe, temps, s, lambda x: None)
        with self.assertRaises(ValueError):
            curseurs.choisir("Horizontal")
        self.assertEqual(axe.lines[0].get_linestyle(), "None")
        self.assertEqual(list(axe.get_yticks()), [0,1])

    def test_4104_6000_capture_rapport_restaure_moniteur_et_zoom(self):
        from trace_signal import creer_figure
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from rapport_pdf import capturer, generer_pdf, PageRapport
        s, modele = self.signal("t,v\n0,1\n1,2\n2,3\n")
        fig, axe, temps = creer_figure(s, modele)
        FigureCanvasAgg(fig)
        axe.set_xlim(.5,1.5)
        temps.set_visible(False)
        vue = SimpleNamespace(figure=fig, axe_signal=axe, axe_temps=temps, signal=s)
        capture = capturer(vue)
        self.assertFalse(temps.get_visible())
        self.assertEqual(axe.get_xlim(), (.5,1.5))
        self.assertTrue(capture.image.startswith(b"\x89PNG"))
        avant = self.fichier.read_bytes()
        pdf = Path(self.temp.name)/"rapport.pdf"
        generer_pdf(pdf, [PageRapport((capture,)), PageRapport((capture,))],
                    emetteur="Test", projet="PTBG", unite="Essai")
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF"))
        self.assertEqual(self.fichier.read_bytes(), avant)
        taille = pdf.stat().st_size
        with self.assertRaises(FileExistsError):
            generer_pdf(pdf, [PageRapport((capture,))], emetteur="Test", projet="PTBG", unite="Essai")
        self.assertEqual(pdf.stat().st_size, taille)
        with self.assertRaises(ValueError):
            generer_pdf(self.fichier, [PageRapport((capture,))], emetteur="Test", projet="PTBG", unite="Essai")
        with self.assertRaises(ValueError):
            generer_pdf(Path(self.temp.name)/"vide.pdf", [], emetteur="Test", projet="PTBG", unite="Essai")


class TachesTests(unittest.TestCase):
    def test_4105_resultat_publie_sans_executer_dans_fil_appelant(self):
        appelant = threading.get_ident()
        tache = TacheFond(lambda annulation, publier: threading.get_ident())
        self.assertTrue(tache.terminee.wait(2))
        nature, thread = tache.lire()[-1]
        self.assertEqual(nature, "resultat")
        self.assertNotEqual(thread, appelant)

    def test_4105_annulation_ne_publie_pas_un_resultat_valide(self):
        debut, finir = threading.Event(), threading.Event()
        def calcul(annulation, publier):
            debut.set()
            finir.wait(2)
            return 123
        tache = TacheFond(calcul)
        self.assertTrue(debut.wait(2))
        tache.annuler()
        finir.set()
        self.assertTrue(tache.terminee.wait(2))
        self.assertEqual(tache.lire()[-1][0], "annule")

    def test_4105_exception_isolee(self):
        def calcul(annulation, publier):
            raise OSError("lecture refusée")
        tache = TacheFond(calcul)
        self.assertTrue(tache.terminee.wait(2))
        self.assertEqual(tache.lire()[-1], ("erreur", "lecture refusée"))

    def test_2105_import_transactionnel(self):
        with tempfile.TemporaryDirectory() as dossier:
            a = Path(dossier)/"a.csv"
            a.write_text("t,v\n0,1\n1,2\n", encoding="utf-8")
            ancien = PaquetCSV()
            nouveau = importer_copie(ancien, [a], threading.Event(), lambda p: None)
            self.assertEqual(len(ancien.sources), 0)
            self.assertEqual(len(nouveau.sources), 1)
            annuler = threading.Event()
            annuler.set()
            self.assertEqual(len(importer_copie(ancien, [a], annuler, lambda p: None).sources), 0)


class LanceurTests(unittest.TestCase):
    def test_validation_structuree_ignore_ne_vaut_pas_reussite_complete(self):
        from executer_tests import ResultatStructure
        class Cas(unittest.TestCase):
            def test_ok(self):
                pass
            @unittest.skip("motif explicite")
            def test_ignore(self):
                pass
        resultat = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ResultatStructure).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Cas))
        bilan = resultat.bilan()
        self.assertEqual(bilan["statut"], "partielle")
        self.assertEqual(bilan["comptes"]["ignore"], 1)
        self.assertEqual(bilan["comptes"]["reussi"], 1)

    def test_validation_structuree_soustest_en_echec(self):
        from executer_tests import ResultatStructure
        class Cas(unittest.TestCase):
            def test_echec(self):
                with self.subTest(exemple=1):
                    self.fail("échec volontaire du sous-test")
        resultat = unittest.TextTestRunner(stream=io.StringIO(), resultclass=ResultatStructure).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(Cas))
        self.assertEqual(resultat.bilan()["statut"], "echec")
        self.assertEqual(resultat.bilan()["comptes"]["echoue"], 1)

    def test_surveillance_lanceurs_et_donnees(self):
        sys.path.insert(0, str(PROJET))
        from verifier_robustesse import empreintes_sources
        empreintes = empreintes_sources()
        self.assertIn("MAIN.py", empreintes)
        self.assertIn("verifier_robustesse.py", empreintes)
        self.assertTrue(any(p.startswith("donnees/") for p in empreintes))
