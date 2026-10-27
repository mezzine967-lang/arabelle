"""Requis 4101 (partiel) : un trou visible, bordé par des mesures réelles.

Les petits CSV ci-dessous sont temporaires. Les assertions portent sur les
coordonnées et les segments réellement envoyés à Matplotlib, pas sur une image
supposée correcte. Aucun test ne modifie les CSV de simulation du projet.
"""
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
from signal_csv import preparer_signal


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Matplotlib absent : rendu non vérifié")
class CoupuresSignalTests(unittest.TestCase):
    """La croix désigne un bord connu ; elle ne remplace jamais une absence."""

    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.addCleanup(self.dossier.cleanup)
        self.fichier = Path(self.dossier.name) / "signal.csv"

    def lire(self, texte, pas=None, tolerance=None):
        self.fichier.write_text(texte, encoding="utf-8")
        avant = self.fichier.read_bytes()
        source = SourceTemps(self.fichier, colonne_temps="t_ms", unite="ms",
                             pas_attendu=pas, tolerance=tolerance)
        resultat = examiner_source(source)
        signal = preparer_signal(source, resultat, "v")
        self.assertEqual(self.fichier.read_bytes(), avant)
        return source, resultat, signal

    def dessiner(self, texte, pas=None, tolerance=None):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from trace_signal import creer_figure
        source, resultat, signal = self.lire(texte, pas, tolerance)
        modele = construire_moniteur(source, resultat)
        figure, courbe, temps = creer_figure(signal, modele)
        FigureCanvasAgg(figure).draw()
        return signal, figure, courbe, temps, modele

    @staticmethod
    def croix(courbe):
        return [(float(x), float(y)) for ligne in courbe.lines if ligne.get_marker() == "x"
                for x, y in zip(ligne.get_xdata(), ligne.get_ydata())]

    @staticmethod
    def segments(courbe):
        from matplotlib.path import Path as Chemin
        ligne = courbe.lines[0]
        if ligne.get_linestyle() == "None":
            return []
        resultat, precedent = [], None
        for sommet, code in ligne.get_path().iter_segments(simplify=False):
            point = tuple(sommet[-2:])
            if code == Chemin.LINETO:
                resultat.append((precedent, point))
            precedent = point
        return resultat

    def test_trou_borde_par_dernier_et_premier_points_connus(self):
        signal, figure, courbe, temps, _ = self.dessiner(
            "t_ms,v\n0,0\n1,3\n2,\n3,\n4,1\n5,2\n")
        self.assertEqual(self.croix(courbe), [(1, 3), (4, 1)])
        self.assertEqual(self.segments(courbe), [((0, 0), (1, 3)), ((4, 1), (5, 2))])
        self.assertEqual(signal.temps, [0, 1, 2, 3, 4, 5])
        self.assertTrue(math.isnan(signal.valeurs[2]) and math.isnan(signal.valeurs[3]))
        self.assertEqual(len(figure.axes), 2)  # signal et moniteur, sans bande de croix
        courbe.set_xlim(0.5, 4.5)
        self.assertEqual(temps.get_xlim(), (0.5, 4.5))

    def test_ligne_rejetee_coupe_le_trait_sans_affirmer_une_perte(self):
        _, _, courbe, _, _ = self.dessiner(
            "t_ms,v\n0,0\n1,1\n2\n3,3\n4,4\n", "1", "0")
        self.assertEqual(self.croix(courbe), [])
        self.assertEqual(self.segments(courbe), [((0, 0), (1, 1)), ((3, 3), (4, 4))])

    def test_champ_csv_multiligne_ne_cree_pas_de_faux_trou(self):
        signal, _, courbe, _, _ = self.dessiner(
            't_ms,v,note\n0,1,"deux\nlignes"\n1,2,ok\n2,3,ok\n', "1", "0")
        self.assertEqual(signal.lignes, [2, 4, 5])
        self.assertEqual(self.croix(courbe), [])
        self.assertEqual(len(self.segments(courbe)), 2)

    def test_absence_aux_extremites_un_seul_bord_disponible(self):
        cas = [
            ("0,\n1,2\n2,3\n", [(1, 2)]),
            ("0,1\n1,2\n2,\n", [(1, 2)]),
            ("0,\n1,0\n2,\n", [(1, 0)]),
        ]
        for lignes, attendu in cas:
            with self.subTest(lignes=lignes):
                _, _, courbe, _, _ = self.dessiner("t_ms,v\n" + lignes)
                self.assertEqual(self.croix(courbe), attendu)

    def test_valeurs_invalides_ne_deviennent_pas_des_mesures_et_zero_reste_reel(self):
        signal, _, courbe, _, _ = self.dessiner(
            "t_ms,v\n0,0\n1,nan\n2,inf\n3,texte\n4,1e999\n5,0\n")
        self.assertEqual(self.croix(courbe), [])  # valeur invalide != cellule vide
        self.assertEqual(self.segments(courbe), [])
        self.assertTrue(all(math.isnan(v) for v in signal.valeurs[1:5]))

    def test_vide_dans_une_autre_colonne_ne_marque_pas_le_signal_affiche(self):
        _, _, courbe, _, _ = self.dessiner("t_ms,v,autre\n0,0,1\n1,1,\n2,2,3\n")
        self.assertEqual(self.croix(courbe), [])
        self.assertEqual(len(self.segments(courbe)), 2)

    def test_doublon_et_retour_interrompent_le_trait_sans_signifier_une_perte(self):
        _, _, courbe, _, _ = self.dessiner(
            "t_ms,v\n0,0\n1,1\n1,2\n0,3\n1,4\n", "1", "0")
        self.assertEqual(self.segments(courbe), [((0, 0), (1, 1)), ((0, 3), (1, 4))])
        self.assertEqual(self.croix(courbe), [])

    def test_grands_intervalles_coupes_sans_croix_meme_si_moniteur_limite(self):
        x, points = 0, [(0, 0)]
        for i in range(1, 61):
            prochain = x + (3 if i % 2 == 0 else 1)
            points.append((prochain, i))
            x = prochain
        texte = "t_ms,v\n" + "".join(f"{t},{v}\n" for t, v in points)
        signal, figure, courbe, _, modele = self.dessiner(texte, "1", "0")
        self.assertLess(len(modele["marqueurs"]), 30)
        self.assertEqual(self.croix(courbe), [])  # aucun champ vide dans ce CSV
        self.assertEqual(signal.temps, [t for t, _ in points])
        self.assertEqual(len(self.segments(courbe)), 30)
        self.assertTrue(all(b[0] - a[0] == 1 for a, b in self.segments(courbe)))
        self.assertTrue(any("perte de données non prouvée" in t.get_text() for t in figure.texts))

    def test_sans_profil_des_pas_irreguliers_restent_des_points_seuls(self):
        _, _, courbe, _, _ = self.dessiner("t_ms,v\n0,0\n1,1\n10,2\n11,3\n")
        self.assertEqual(courbe.lines[0].get_linestyle(), "None")
        self.assertEqual(self.croix(courbe), [])

    def test_tolerance_decimale_aux_bornes_ne_cree_pas_de_coupure(self):
        _, _, courbe, _, _ = self.dessiner(
            "t_ms,v\n0,0\n0.1,1\n0.21,2\n0.32,3\n", "0.1", "0.01")
        self.assertEqual(self.croix(courbe), [])
        self.assertEqual(len(self.segments(courbe)), 3)

    def test_pas_change_exige_de_reanalyser_avant_de_decouper_la_courbe(self):
        source, resultat, _ = self.lire("t_ms,v\n0,0\n1,1\n3,3\n", "1", "0")
        autre = SourceTemps(source.fichier, colonne_temps="t_ms", unite="ms",
                            pas_attendu="2", tolerance="0")
        with self.assertRaises(CsvDiagnosticError) as erreur:
            preparer_signal(autre, resultat, "v")
        self.assertEqual(erreur.exception.code, "profil_modifie")


if __name__ == "__main__":
    unittest.main()
