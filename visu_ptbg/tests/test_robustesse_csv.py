"""Tests de robustesse CSV sur cas synthétiques, sans modifier les fichiers reçus.

Entrées : textes de test écrits dans un dossier temporaire neuf pour chaque cas.
Sorties : assertions unittest ; les refus attendus sont des résultats de test,
pas des pannes de la suite. Dépendances : bibliothèque standard et diagnostic_csv.
Requis 3006 : les groupes expliquent le risque vérifié ; les méthodes donnent
le résultat attendu. Un test réussi ne valide pas, à lui seul, un requis complet.
"""

# === 1. Dépendances, lecteur local et utilitaires de simulation d'erreur ===
import contextlib
import hashlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from diagnostic_csv import CsvDiagnosticError, analyse_csv, compare_csv, main, read_csv


class RobustesseCsvTests(unittest.TestCase):
    """Éprouver la conservation des données et les refus contrôlés du lecteur."""

    # === 2. Préparer chaque cas indépendamment et vérifier les codes de refus ===
    def setUp(self):
        """Créer un dossier isolé et programmer son nettoyage après chaque test."""
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def fichier(self, text, name="cas.csv", encoding="utf-8"):
        """Écrire text sous name dans le dossier temporaire et retourner son chemin."""
        path = self.root / name
        path.write_bytes(text.encode(encoding))
        return path

    def refus(self, path, code, **options):
        """Exiger CsvDiagnosticError et le code prévu avec les options de lecture données."""
        with self.assertRaises(CsvDiagnosticError) as raised:
            analyse_csv(path, **options)
        self.assertEqual(raised.exception.code, code)

    # === 3. Structure CSV : conserver les rejets et leurs positions exactes ===
    def test_lignes_courte_et_longue_conservees(self):
        """Tracer largeur incorrecte, champs bruts et fins de lignes sans tronquer."""
        path = self.fichier("index,value\r\n0,1\r\n20\r\n40,3,extra\r\n60,4\r\n")
        r = read_csv(path)
        self.assertEqual(r.diagnostic.data_rows, 2)
        self.assertEqual(r.diagnostic.malformed_rows, [3, 4])
        self.assertEqual([x.raw_text for x in r.diagnostic.rejected_rows], ["20\r\n", "40,3,extra\r\n"])
        self.assertEqual(r.diagnostic.rejected_rows[1].fields, ["40", "3", "extra"])
        self.assertTrue(r.diagnostic.analysis_complete)

    def test_ligne_vide_conservee(self):
        """Conserver la ligne vide dans les rejets avec son numéro physique."""
        r = analyse_csv(self.fichier("index,value\n0,1\n\n20,2\n"))
        self.assertEqual(r.blank_rows, 1)
        self.assertEqual(r.rejected_rows[0].line_start, 3)
        self.assertEqual(r.rejected_rows[0].raw_text, "\n")
        self.assertEqual(r.rejected_rows[0].code, "ligne_vide")

    def test_champ_multiligne_et_numeros_physiques(self):
        """Un champ sur deux lignes ne doit pas décaler la provenance des lignes suivantes."""
        r = read_csv(self.fichier('index,commentaire\r\n0,"premier\r\nsecond"\r\n20\r\n40,ok\r\n'))
        self.assertEqual(r.rows[0].fields[1], "premier\r\nsecond")
        self.assertEqual((r.rows[0].line_start, r.rows[0].line_end), (2, 3))
        self.assertEqual(r.diagnostic.rejected_rows[0].line_start, 4)
        self.assertEqual(r.rows[-1].line_start, 5)

    def test_guillemets_ouverts_conservent_toute_la_fin(self):
        """Une citation non fermée impose un bilan partiel et la conservation de la suite."""
        tail = '20,"inacheve\n40,3\n'
        r = analyse_csv(self.fichier("index,value\n0,1\n" + tail))
        self.assertEqual(r.data_rows, 1)
        self.assertFalse(r.analysis_complete)
        self.assertEqual(r.status, "error")
        self.assertEqual(r.rejected_rows[0].raw_text, tail)
        self.assertEqual((r.rejected_rows[0].line_start, r.rejected_rows[0].line_end), (3, 4))
        self.assertIsNone(r.rejected_rows[0].fields)

    # === 4. En-têtes et absence de données : éviter des diagnostics trompeurs ===
    def test_entete_repetee_rejetee(self):
        """Un en-tête répété au milieu des valeurs est tracé, pas analysé comme donnée."""
        r = analyse_csv(self.fichier("index,value\n0,1\nindex,value\n20,2\n"))
        self.assertEqual(r.data_rows, 2)
        self.assertEqual(r.rejected_rows[0].code, "entete_repetee")

    def test_entetes_dupliques_refuses(self):
        """Refuser les noms identiques après retrait des espaces extérieurs."""
        self.refus(self.fichier("index,value, value \n0,1,2\n"), "colonnes_dupliquees")

    def test_nom_colonne_vide_refuse(self):
        """Refuser une colonne sans nom au lieu d'en inventer un."""
        self.refus(self.fichier("index,,value\n0,1,2\n"), "entete_incomplete")

    def test_entete_absente_refusee(self):
        """Refuser une première ligne entièrement numérique comme en-tête supposé absent."""
        self.refus(self.fichier("0,1\n20,2\n"), "entete_absente")

    def test_fichier_vide_refuse(self):
        """Refuser le fichier vide et celui qui ne contient que des lignes blanches."""
        for content in ("", "\r\n  \r\n"):
            with self.subTest(content=content):
                self.refus(self.fichier(content), "fichier_vide")

    def test_entete_seule_non_validee_comme_temps_croissant(self):
        """Sans donnée, ne pas conclure que le temps progresse ou que les colonnes sont constantes."""
        r = analyse_csv(self.fichier("index,value\n"))
        self.assertEqual(r.data_rows, 0)
        self.assertEqual(r.constant_columns, [])
        self.assertIsNone(r.time.strictly_increasing)
        self.assertTrue(r.warnings)

    def test_point_unique_progression_non_evaluable(self):
        """Un point ne suffit ni pour la progression temporelle ni pour un pas régulier."""
        r = analyse_csv(self.fichier("index,value\n0,1\n"))
        self.assertIsNone(r.time.strictly_increasing)
        self.assertIsNone(r.time.regular_step)

    # === 5. Valeurs manquantes/non finies : aucun remplacement ni liaison fictive ===
    def test_temps_non_finis_invalides_ou_vides(self):
        """Un temps invalide bloque ses statistiques mais ne supprime pas la ligne source."""
        for value in ("NaN", "inf", "-Infinity", "", "inconnu"):
            with self.subTest(value=value):
                r = analyse_csv(self.fichier(f"index,value\n0,1\n{value},2\n40,3\n"))
                self.assertFalse(r.time.numeric)
                self.assertEqual(r.time.invalid_lines, [3])
                self.assertIsNone(r.time.duplicate_count)
                self.assertEqual(r.data_rows, 3)

    def test_cellules_non_finies_restees_brutes(self):
        """Conserver NaN/inf sous forme textuelle tout en produisant un résumé JSON valide."""
        r = read_csv(self.fichier("index,value\n0,NaN\n20,inf\n40,1\n"))
        self.assertEqual(r.diagnostic.nonfinite_cells_by_column["value"], 2)
        self.assertEqual(r.rows[0].fields[1], "NaN")
        json.dumps(r.diagnostic.time.__dict__, allow_nan=False)

    def test_colonne_mixte_signalee_sans_perte(self):
        """Signaler le mélange nombres/texte et conserver le texte original."""
        r = read_csv(self.fichier("index,value\n0,1\n20,panne\n40,3\n"))
        self.assertEqual(r.diagnostic.inferred_types["value"], "mixte")
        self.assertEqual(r.diagnostic.data_rows, 3)
        self.assertEqual(r.rows[1].fields[1], "panne")

    # === 6. Dialecte CSV et choix explicites quand l'interprétation est ambiguë ===
    def test_point_virgule_et_decimales_explicitement_configurees(self):
        """Lire le point-virgule et une décimale virgule demandée explicitement."""
        r = analyse_csv(self.fichier("temps;valeur\n0,1;1,25\n0,2;2,50\n"), decimal=",")
        self.assertEqual(r.delimiter, ";")
        self.assertEqual(r.time.regular_step, 0.1)
        self.assertEqual(r.inferred_types["valeur"], "numérique")

    def test_separateurs_tabulation_et_barre(self):
        """Reconnaître tabulation et barre verticale sur des en-têtes non ambigus."""
        for sep in ("\t", "|"):
            with self.subTest(sep=sep):
                r = analyse_csv(self.fichier(f"index{sep}value\n0{sep}1\n20{sep}2\n"))
                self.assertEqual(r.delimiter, sep)
                self.assertEqual(r.data_rows, 2)

    def test_separateur_dans_champ_entre_guillemets(self):
        """Une virgule protégée par des guillemets appartient à la cellule."""
        r = read_csv(self.fichier('index,commentaire\n0,"a,b"\n20,"c,d"\n'))
        self.assertEqual(r.rows[0].fields, ["0", "a,b"])
        self.assertEqual(r.diagnostic.rejected_rows, [])

    def test_separateur_ambigu_refuse_et_choix_explicite(self):
        """Exiger le choix utilisateur si deux séparateurs peuvent interpréter l'en-tête."""
        path = self.fichier("index,valeur;unite\n0,1;m\n20,2;m\n")
        self.refus(path, "separateur_ambigu")
        self.assertEqual(analyse_csv(path, delimiter=",").columns, ["index", "valeur;unite"])

    def test_premiere_colonne_temps_imposee(self):
        """Utiliser la première colonne et refuser une configuration qui en désigne une autre."""
        path = self.fichier("index,t_ms,value\n0,100,1\n20,120,2\n")
        self.assertEqual(analyse_csv(path).time.column, "index")
        self.assertEqual(analyse_csv(path, time_column="index").time.start, 0)
        self.refus(path, "premiere_colonne_temps", time_column="t_ms")
        self.refus(path, "premiere_colonne_temps", time_column="absent")

    # === 7. Précision et chronologie : calculer les écarts avant l'affichage ===
    def test_entiers_au_dela_precision_float(self):
        """Deux grands entiers consécutifs doivent garder leur différence de un."""
        r = analyse_csv(self.fichier("index,value\n9007199254740992,1\n9007199254740993,2\n"))
        self.assertTrue(r.time.strictly_increasing)
        self.assertEqual(r.time.regular_step, 1)
        self.assertEqual(r.time.end, 9007199254740993)

    def test_petits_pas_non_arrondis_a_zero(self):
        """Un pas de 10 puissance moins 13 reste positif, sans arrondi à zéro."""
        r = analyse_csv(self.fichier("temps,value\n0,1\n0.0000000000001,2\n0.0000000000002,3\n"))
        self.assertTrue(r.time.strictly_increasing)
        self.assertEqual(r.time.regular_step, 1e-13)

    def test_repetition_non_adjacente_et_retour_arriere(self):
        """Distinguer répétition non adjacente, doublon adjacent et retour arrière."""
        r = analyse_csv(self.fichier("index,value\n0,1\n20,2\n10,3\n20,4\n"))
        self.assertEqual(r.time.duplicate_count, 0)
        self.assertEqual(r.time.repeated_value_count, 1)
        self.assertEqual(r.time.backward_count, 1)
        self.assertEqual(r.time.anomalies[0]["line"], 4)

    # === 8. Intégrité du fichier, encodages et garde-fou de ressources ===
    def test_fichier_source_non_modifie(self):
        """Vérifier les octets avant/après et l'empreinte publiée, même avec un rejet."""
        path = self.fichier("index,value\r\n0,1\r\n20\r\n40,3\r\n")
        before = path.read_bytes()
        d = analyse_csv(path)
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(d.sha256, hashlib.sha256(before).hexdigest())

    def test_encodage_legacy_sans_guess(self):
        """Un fichier cp1252 illisible en UTF-8 exige le choix explicite de son encodage."""
        path = self.fichier("index,état\n0,arrêt\n20,marche\n", encoding="cp1252")
        self.refus(path, "encodage_invalide")
        r = read_csv(path, encoding="cp1252")
        self.assertEqual(r.rows[0].fields[1], "arrêt")

    def test_utf16_avec_bom(self):
        """Reconnaître UTF-16 au BOM et conserver les deux lignes de données."""
        r = analyse_csv(self.fichier("index\tvalue\r\n0\t1\r\n20\t2\r\n", encoding="utf-16"))
        self.assertEqual(r.encoding, "utf-16")
        self.assertEqual(r.data_rows, 2)

    def test_taille_bornee_refus_explicite(self):
        """Refuser un dépassement d'une petite limite choisie pour le test."""
        self.refus(self.fichier("index,value\n0,1\n"), "fichier_trop_grand", max_bytes=5)

    # === 9. Adaptateur CLI : les erreurs attendues deviennent des sorties lisibles ===
    def test_fichier_manquant_erreur_cli_structuree(self):
        """Un chemin absent produit le code retour 2 et une erreur JSON d'accès."""
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = main([str(self.root / "absent.csv")])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stream.getvalue())["scenario"]["error"]["code"], "acces_fichier")

    def test_permission_refusee_erreur_cli_structuree(self):
        """Simuler un refus d'accès ; cela ne certifie pas les ACL réelles de Windows."""
        stream = io.StringIO()
        with patch("diagnostic_csv._read_text", side_effect=PermissionError("accès refusé")), contextlib.redirect_stdout(stream):
            status = main(["test.csv"])
        self.assertEqual(status, 2)
        self.assertIn("accès refusé", stream.getvalue())

    def test_entete_dupliquee_erreur_cli_structuree(self):
        """La CLI transmet le code de refus des en-têtes dupliqués."""
        path = self.fichier("index,value,value\n0,1,2\n")
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = main([str(path)])
        self.assertEqual(status, 2)
        self.assertEqual(json.loads(stream.getvalue())["scenario"]["error"]["code"], "colonnes_dupliquees")

    def test_csv_incomplet_erreur_cli_partielle(self):
        """La CLI conserve le statut partiel et retourne 2 après une syntaxe cassée."""
        path = self.fichier('index,value\n0,1\n20,"ouvert\n')
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            status = main([str(path)])
        self.assertEqual(status, 2)
        self.assertFalse(json.loads(stream.getvalue())["scenario"]["analysis_complete"])

    # === 10. Comparaison positionnelle : refuser les alignements trompeurs ===
    def test_comparaison_refuse_rejets_ou_longueurs_differentes(self):
        """Des rejets ou longueurs différentes interdisent un compte d'écarts ligne à ligne."""
        a = self.fichier("index,value\n0,1\n20,2\n", "a.csv")
        for content in ("index,value\n0,1\n20\n", "index,value\n0,1\n20,2\n40,3\n", "index,value\n0,1\n\n20,2\n"):
            with self.subTest(content=content):
                result = compare_csv(a, self.fichier(content, "b.csv"))
                self.assertFalse(result["comparison_performed"])
                self.assertIsNone(result["shared_column_mismatches"])

    def test_comparaison_refuse_temps_decales(self):
        """Même longueur ne signifie pas même chronologie ; ne pas recaler implicitement."""
        a = self.fichier("index,value\n0,1\n20,2\n", "a.csv")
        b = self.fichier("index,value\n10,1\n30,2\n", "b.csv")
        self.assertFalse(compare_csv(a, b)["comparison_performed"])

    def test_comparaison_refuse_colonne_manquante(self):
        """Signaler une entrée absente du report et refuser la comparaison."""
        a = self.fichier("index,value\n0,1\n20,2\n", "a.csv")
        b = self.fichier("index\n0\n20\n", "b.csv")
        self.assertEqual(compare_csv(a, b)["missing_reference_columns"], ["value"])
        self.assertFalse(compare_csv(a, b)["comparison_performed"])

    def test_comparaison_refuse_temps_dupliques(self):
        """Des doublons dans les deux fichiers ne rendent pas leur alignement fiable."""
        a = self.fichier("index,value\n0,1\n0,2\n", "a.csv")
        b = self.fichier("index,value\n0,1\n0,2\n", "b.csv")
        self.assertFalse(compare_csv(a, b)["comparison_performed"])

    # === 11. Extension cohérente du schéma : ne pas figer le nombre de colonnes ===
    def test_colonne_supplementaire_valide_acceptee(self):
        """Une colonne ajoutée à l'en-tête et à toutes les lignes doit être acceptée."""
        r = analyse_csv(self.fichier("index,value,nouvelle_colonne\n0,1,STOP\n20,2,ACTIVE\n"))
        self.assertEqual(r.data_rows, 2)
        self.assertEqual(r.columns[-1], "nouvelle_colonne")
        self.assertEqual(r.rejected_rows, [])


if __name__ == "__main__":
    # Lancement isolé de ces cas ; le lanceur global découvre les trois fichiers.
    unittest.main()
