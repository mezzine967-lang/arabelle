"""REQ 3005 : choisir les résultats sans écrire dans l'installation."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from emplacements import dossier_resultats
from environnement_visu import enregistrer_environnement


class EmplacementsTests(unittest.TestCase):
    def test_releve_hors_installation(self):
        with tempfile.TemporaryDirectory() as tmp:
            installation = Path(tmp) / 'installation_absente'
            utilisateur = Path(tmp) / 'utilisateur'
            with patch('environnement_visu.dossier_resultats', return_value=utilisateur):
                fichier = enregistrer_environnement(installation, 'test')
            self.assertTrue(fichier.is_file())
            self.assertFalse(installation.exists())

    def test_xdg_absolu_et_repli(self):
        with patch('emplacements.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_STATE_HOME': '/tmp/visu_test'}):
            self.assertEqual(dossier_resultats(), Path('/tmp/visu_test/VISU_PTBG/resultats'))
        with patch('emplacements.sys.platform', 'linux'), patch.dict(os.environ, {'XDG_STATE_HOME': 'relatif'}):
            self.assertEqual(dossier_resultats(), Path.home() / '.local/state/VISU_PTBG/resultats')

    def test_refus_permission_propage(self):
        with patch('environnement_visu.dossier_resultats', return_value=Path('/inaccessible')):
            with patch.object(Path, 'mkdir', side_effect=PermissionError('Accès refusé')):
                with self.assertRaises(PermissionError):
                    enregistrer_environnement(Path('.'), 'test')
