"""Cas de référence du détail temporel et de ses graphiques (v0.7.0).

Les fichiers dégradés sont créés dans un dossier temporaire. Les résultats
attendus utilisent des nombres exacts, pas le même calcul que la production.
"""
import hashlib
import importlib.util
import sys
import tempfile
import unittest
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_source
from diagnostic_csv import CsvDiagnosticError
from inspection_temps import preparer_inspection, resumer_inspection


class InspectionTempsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.fichier = Path(self.temp.name) / "essai.csv"

    def preparer(self, texte, **profil):
        self.fichier.write_text(texte, encoding="utf-8")
        source = SourceTemps(self.fichier, **profil)
        resultat = examiner_source(source)
        return source, resultat, preparer_inspection(source, resultat)

    def test_simulation_compte_complet_et_lignes_exactes(self):
        chemin = PROJET / "donnees/simulation10_execution1.csv"
        avant = hashlib.sha256(chemin.read_bytes()).hexdigest()
        s = SourceTemps(chemin, colonne_temps="t_ms", unite="ms", pas_attendu="1", tolerance="0")
        i = preparer_inspection(s, examiner_source(s))
        self.assertEqual(len(i.intervalles), 10000)
        self.assertEqual(i.distribution, {Decimal(1): 9997, Decimal(0): 2, Decimal(2): 1})
        self.assertEqual([(i.intervalles[k].ligne_avant, i.intervalles[k].ligne_apres,
                           str(i.intervalles[k].delta)) for k in i.indices()],
                         [(1008, 1009, "0"), (4987, 4988, "2"), (9817, 9818, "0")])
        self.assertEqual(hashlib.sha256(chemin.read_bytes()).hexdigest(), avant)

    def test_grands_compteurs_soustraits_avant_conversion_graphique(self):
        _, _, i = self.preparer("t,v\n9007199254740992,0\n9007199254740993,1\n9007199254740994,2\n")
        self.assertEqual([v.delta for v in i.intervalles], [Decimal(1), Decimal(1)])
        self.assertEqual(i.intervalles[0].temps_avant, "9007199254740992")

    def test_tolerance_inclusive_et_depassement_minime(self):
        _, _, i = self.preparer("t,v\n0,0\n0.9,1\n2.0,2\n3.10001,3\n", pas_attendu="1", tolerance="0.1")
        self.assertEqual([v.nature for v in i.intervalles],
                         ["dans_tolerance", "dans_tolerance", "pas_hors_tolerance"])
        self.assertEqual(i.intervalles[-1].ecart, Decimal("0.10001"))

    def test_doublons_et_retours_meme_avec_tolerance_large(self):
        _, _, i = self.preparer("t,v\n0,0\n1,1\n1,2\n0.5,3\n1.5,4\n", pas_attendu="1", tolerance="10")
        self.assertEqual([v.nature for v in i.intervalles],
                         ["dans_tolerance", "temps_duplique", "retour_arriere", "dans_tolerance"])
        self.assertEqual(i.intervalles[2].delta, Decimal("-0.5"))

    def test_rejet_interdit_un_intervalle_a_travers_la_ligne(self):
        _, _, i = self.preparer("t,v\n0,0\n1\n2,2\n3,3\n", pas_attendu="1", tolerance="0")
        self.assertFalse(i.comparaison_effectuee)
        self.assertIsNone(i.intervalles[0].delta)
        self.assertEqual(i.intervalles[0].nature, "interruption_lecture")
        self.assertEqual(i.intervalles[1].nature, "observe")
        self.assertEqual(i.distribution, {Decimal(1): 1})
        self.assertEqual(i.lignes_rejetees, 1)

    def test_champ_multiligne_ne_cree_pas_de_fausse_rupture(self):
        _, _, i = self.preparer('t,v\n0,"a\nb"\n1,c\n', pas_attendu="1", tolerance="0")
        v = i.intervalles[0]
        self.assertEqual((v.ligne_avant, v.fin_avant, v.ligne_apres), (2, 3, 4))
        self.assertEqual(v.nature, "dans_tolerance")

    def test_temps_absent_ne_devient_pas_zero_ni_un_pont(self):
        _, _, i = self.preparer("t,v\n0,0\n,1\n2,2\n3,3\n", pas_attendu="1", tolerance="0")
        self.assertEqual([v.delta for v in i.intervalles], [None, None, Decimal(1)])
        self.assertEqual(i.temps_invalides, 1)
        self.assertFalse(i.comparaison_effectuee)

    def test_sans_profil_unite_inconnue_et_pas_positifs_non_classes(self):
        _, _, i = self.preparer("index,v\n0,0\n1,1\n3,2\n")
        self.assertIsNone(i.unite)
        self.assertEqual(i.indices(), [])
        self.assertEqual(i.comptes, {"observe": 2})
        self.assertIn("non effectuée", resumer_inspection(i))
        self.assertNotIn("perte", resumer_inspection(i))

    def test_unite_saisie_ne_convertit_pas_les_nombres(self):
        s, r, i = self.preparer("t,v\n0,0\n1000,1\n", unite="ms")
        autre = replace(s, unite="s")
        j = preparer_inspection(autre, examiner_source(autre))
        self.assertEqual(i.intervalles, j.intervalles)
        with self.assertRaises(CsvDiagnosticError) as erreur:
            preparer_inspection(autre, r)
        self.assertEqual(erreur.exception.code, "profil_modifie")

    def test_csv_change_exige_un_nouveau_diagnostic(self):
        s, r, _ = self.preparer("t,v\n0,0\n1,1\n")
        self.fichier.write_text("t,v\n0,0\n2,1\n", encoding="utf-8")
        with self.assertRaises(CsvDiagnosticError) as erreur:
            preparer_inspection(s, r)
        self.assertEqual(erreur.exception.code, "fichier_modifie")

    def test_toutes_les_anomalies_restent_consultables(self):
        _, _, i = self.preparer("t,v\n" + "0,1\n" * 246, pas_attendu="1", tolerance="0")
        self.assertEqual(len(i.indices()), 245)
        self.assertEqual(i.intervalles[i.indices()[-1]].ligne_apres, 247)

    def test_lecture_partielle_reste_explicite(self):
        _, _, i = self.preparer('t,v\n0,0\n1,1\n2,"inacheve\n', pas_attendu="1", tolerance="0")
        self.assertFalse(i.lecture_complete)
        self.assertFalse(i.comparaison_effectuee)
        self.assertEqual(i.intervalles[0].nature, "observe")
        self.assertIn("lecture complète : non", resumer_inspection(i))

    def test_point_unique_aucun_intervalle_et_aucune_conformite(self):
        _, _, i = self.preparer("t,v\n0,0\n", pas_attendu="1", tolerance="0")
        self.assertEqual(i.intervalles, [])
        self.assertFalse(i.comparaison_effectuee)

    def test_plusieurs_noms_temporels_utilisent_la_premiere_colonne(self):
        self.fichier.write_text("t,temps,v\n0,1,1\n1,2,2\n", encoding="utf-8")
        s = SourceTemps(self.fichier)
        inspection = preparer_inspection(s, examiner_source(s))
        self.assertEqual(inspection.colonne, "t")
        self.assertEqual(inspection.intervalles[0].delta, Decimal("1"))


@unittest.skipUnless(importlib.util.find_spec("matplotlib"), "Matplotlib absent : rendu non vérifié")
class FigureTempsTests(unittest.TestCase):
    def test_ecarts_traces_dans_ordre_csv_sans_segments(self):
        from matplotlib.backends.backend_agg import FigureCanvasAgg
        from trace_temps import creer_figure_temps
        s = SourceTemps(PROJET / "donnees/simulation10_execution1.csv",
                        colonne_temps="t_ms", unite="ms", pas_attendu="1", tolerance="0")
        inspection = preparer_inspection(s, examiner_source(s))
        figure, axe = creer_figure_temps(inspection)
        FigureCanvasAgg(figure).draw()
        points = [ligne for ligne in axe.lines if ligne.get_linestyle() == "None"]
        self.assertEqual(sum(len(l.get_xdata()) for l in points), 10000)
        doublons = next(l for l in points if l.get_label() == "Temps dupliqué")
        self.assertEqual(list(doublons.get_xdata()), [1009, 9818])
        self.assertEqual(list(doublons.get_ydata()), [0, 0])
        self.assertEqual(axe.get_ylabel(), "Δt [ms]")
        self.assertIn("Ligne CSV", axe.get_xlabel())

    def test_perte_de_distinction_des_ecarts_refusee_au_dessin(self):
        from trace_temps import creer_figure_temps
        with tempfile.TemporaryDirectory() as dossier:
            p = Path(dossier) / "precision.csv"
            p.write_text("t,v\n0,0\n1,1\n2.0000000000000001,2\n", encoding="utf-8")
            s = SourceTemps(p)
            i = preparer_inspection(s, examiner_source(s))
            self.assertEqual(i.intervalles[1].delta, Decimal("1.0000000000000001"))
            with self.assertRaisesRegex(ValueError, "précision"):
                creer_figure_temps(i)


if __name__ == "__main__":
    unittest.main()
