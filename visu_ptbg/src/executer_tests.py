"""Résultat structuré unittest, indépendant de la langue du compte rendu.

Ce sous-processus est appelé par verifier_robustesse.py. Un test ignoré ou
attendu en échec donne une réussite partielle, jamais une validation complète.
"""
import json
from pathlib import Path
import sys
import unittest


class ResultatStructure(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cas = {}

    def startTest(self, test):
        super().startTest(test)
        self.cas[test.id()] = {"id": test.id(), "etat": "en_cours"}

    def _noter(self, test, etat, motif=""):
        self.cas[test.id()] = {"id": test.id(), "etat": etat, "motif": motif}

    def addSuccess(self, test):
        super().addSuccess(test)
        self._noter(test, "reussi")

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self._noter(test, "echoue", self._exc_info_to_string(err, test))

    def addError(self, test, err):
        super().addError(test, err)
        self._noter(test, "erreur", self._exc_info_to_string(err, test))

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self._noter(test, "ignore", reason)

    def addExpectedFailure(self, test, err):
        super().addExpectedFailure(test, err)
        self._noter(test, "echec_attendu", self._exc_info_to_string(err, test))

    def addUnexpectedSuccess(self, test):
        super().addUnexpectedSuccess(test)
        self._noter(test, "succes_inattendu")

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            etat = "echoue" if issubclass(err[0], test.failureException) else "erreur"
            self._noter(test, etat, self._exc_info_to_string(err, test))

    def bilan(self):
        nombres = {etat: sum(c["etat"] == etat for c in self.cas.values()) for etat in
                   ("reussi", "echoue", "erreur", "ignore", "echec_attendu", "succes_inattendu")}
        statut = "complete" if self.testsRun and self.wasSuccessful() else "echec"
        if statut == "complete" and (nombres["ignore"] or nombres["echec_attendu"]):
            statut = "partielle"
        return {"nombre_tests": self.testsRun, "comptes": nombres, "statut": statut,
                "cas": list(self.cas.values())}


if __name__ == "__main__":
    # Un script lancé depuis src/ place src en tête de sys.path, pas le dossier
    # racine. Les tests importent aussi les lanceurs de démonstration racine.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    suite = unittest.defaultTestLoader.discover(sys.argv[1])
    resultat = unittest.TextTestRunner(verbosity=2, resultclass=ResultatStructure).run(suite)
    Path(sys.argv[2]).write_text(json.dumps(resultat.bilan(), ensure_ascii=False, indent=2), encoding="utf-8")
    sys.exit(0 if resultat.wasSuccessful() and resultat.testsRun else 1)
