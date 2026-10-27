"""REQ 2306/4100 : heures, précision et limites sans date inventée."""
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from diagnostic_csv import _temps_decimal, CsvDiagnosticError, read_csv
from base_temps import SourceTemps, examiner_source
from inspection_temps import preparer_inspection
from signal_csv import preparer_signal


class HeuresTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.p = Path(self.tmp.name) / 'heures.csv'

    def test_precision_nanoseconde(self):
        self.assertEqual(_temps_decimal('23:59:59.999999999'), Decimal('86399.999999999'))
        self.assertEqual(_temps_decimal('00:00:00.000000001'), Decimal('0.000000001'))

    def test_invalides(self):
        for valeur in ('24:00:00', '12:60:00', '12:00:60', '12:00', '12:00:00.1234567890'):
            with self.subTest(valeur=valeur):
                self.assertIsNone(_temps_decimal(valeur))

    def test_parcours_complet_et_source_intacte(self):
        texte = 'temps,v\n12:30:00.000000001,0\n12:30:00.010000001,1\n12:30:00.020000001,2\n'
        self.p.write_text(texte, encoding='utf-8')
        source = SourceTemps(self.p, unite='s', pas_attendu='0.01', tolerance='0')
        resultat = examiner_source(source)
        self.assertEqual(resultat['analyse_temporelle']['raster']['valeur'], '0.01')
        inspection = preparer_inspection(source, resultat)
        self.assertEqual(inspection.intervalles[0].delta, Decimal('0.010000000'))
        signal = preparer_signal(source, resultat, 'v')
        self.assertEqual(signal.unite_temps, 's')
        self.assertEqual(signal.deltas_temps, [0.01, 0.01])
        self.assertEqual(self.p.read_text(encoding='utf-8'), texte)

    def test_minuit_reste_retour(self):
        self.p.write_text('t,v\n23:59:59,0\n00:00:00,1\n', encoding='utf-8')
        self.assertEqual(read_csv(self.p).diagnostic.time.backward_count, 1)

    def test_formats_melanges_refuses(self):
        self.p.write_text('t,v\n12:00:00,0\n43201,1\n', encoding='utf-8')
        with self.assertRaises(CsvDiagnosticError):
            read_csv(self.p)

    def test_unite_incompatible_refusee(self):
        self.p.write_text('t,v\n12:00:00,0\n12:00:01,1\n', encoding='utf-8')
        with self.assertRaises(CsvDiagnosticError) as erreur:
            examiner_source(SourceTemps(self.p, unite='ms'))
        self.assertEqual(erreur.exception.code, 'unite_heure')
