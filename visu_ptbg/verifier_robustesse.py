"""VISU PTBG — lanceur de la suite de tests.

Usage : dans Spyder, ouvrir ce fichier puis Exécuter (F5).
Entrées : tests/, donnees/, sources et scripts de référence du projet.
Sorties : compte rendu console, bilan retourné et journal JSON daté dans resultats/.
Dépendances : bibliothèque standard uniquement ; aucun simulateur n'est exécuté.
Les tests synthétiques écrivent seulement dans leurs dossiers temporaires.

Un nouveau processus utilise le même interpréteur pour éviter les anciens modules
conservés dans une console Spyder. Cela n'est ni un test de l'IHM ni un essai
d'exécutable. Requis 3006 : chaque phase du contrôle est expliquée ci-dessous.
"""
from __future__ import annotations

# === 1. Dépendances et dossier du projet, indépendants du dossier de la console ===
import hashlib
import json
import os
import platform
import tempfile
import struct
import subprocess
import sys
from datetime import datetime
from pathlib import Path

PROJET = Path(__file__).resolve().parent
if str(PROJET / "src") not in sys.path:
    sys.path.insert(0, str(PROJET / "src"))
from version_visu import VERSION_VISU


def empreintes_sources() -> dict[str, str]:
    """Retourner les empreintes SHA-256 des données, références, src et tests.

    Aucun paramètre. Les caches __pycache__ sont exclus. Les fichiers Python
    racine, tests d’intégration et exemples sont inclus ; docs et journaux exclus. OSError est propagée à main.
    L'égalité avant/après vérifie les octets, pas la pertinence métier des fichiers.
    """
    # === 2. Préparer le contrôle de non-modification des fichiers surveillés ===
    fichiers = []
    for dossier in ("donnees", "references_simulation", "src", "tests", "tests_integration", "tests_gui", "exemples"):
        fichiers.extend(p for p in (PROJET / dossier).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    fichiers.extend(PROJET.glob("*.py"))
    def hacher(chemin):
        empreinte = hashlib.sha256()
        with chemin.open("rb") as fichier:
            for bloc in iter(lambda: fichier.read(1024 * 1024), b""):
                empreinte.update(bloc)
        return empreinte.hexdigest()
    return {str(p.relative_to(PROJET)): hacher(p) for p in sorted(fichiers)}


def main() -> dict:
    """Exécuter unittest dans un processus neuf et retourner le bilan de l'essai.

    Aucun argument. La durée maximale du sous-processus est de 60 secondes.
    Le bilan rapporte l'environnement, le nombre de tests et les empreintes.
    OSError/TimeoutExpired sont signalées ; un échec d'écriture du journal est
    affiché séparément. Une réussite ne certifie pas la conformité de tout VISU.
    """
    # === 3. Tracer l'environnement réel et la version testée ===
    print(f"VISU PTBG — vérification de robustesse v{VERSION_VISU}")
    print(f"Python {platform.python_version()} | {platform.system()} | {struct.calcsize('P') * 8} bits")
    print("Tests dans un processus neuf, avec cet interpréteur. Aucune installation nécessaire.")
    bilan = {
        "version_projet": VERSION_VISU, "date_locale": datetime.now().astimezone().isoformat(),
        "python": platform.python_version(), "systeme": platform.system(),
        "version_systeme": platform.version(), "bits_interpreteur": struct.calcsize("P") * 8,
        "interpreteur": sys.executable, "validation_complete_requis": False,
    }
    try:
        # === 4. Capturer l'état initial puis isoler l'exécution des tests ===
        # Ne pas installer de paquet et ne pas réutiliser une console déjà chargée.
        avant = empreintes_sources()
        environnement = os.environ.copy()
        environnement["PYTHONIOENCODING"] = "utf-8"
        environnement["PYTHONDONTWRITEBYTECODE"] = "1"
        with tempfile.TemporaryDirectory() as temporaire:
            resultat_json = Path(temporaire) / "tests.json"
            execution = subprocess.run(
                [sys.executable, str(PROJET / "src/executer_tests.py"), str(PROJET / "tests"), str(resultat_json)],
                cwd=PROJET, env=environnement, capture_output=True, text=True,
                encoding="utf-8", errors="replace", timeout=60, check=False,
            )
            # Un crash avant la création du JSON est un échec, pas zéro test OK.
            structure = json.loads(resultat_json.read_text(encoding="utf-8")) if resultat_json.exists() else {
                "nombre_tests": 0, "comptes": {}, "statut": "echec", "cas": []}
        texte = execution.stdout + execution.stderr
        print(texte)
        nombre = structure["nombre_tests"]
        nombre_ignores = structure["comptes"].get("ignore", 0)
        bilan["resultat_structure"] = structure
        bilan["statut"] = structure["statut"]
        inchange = avant == empreintes_sources()
        bilan.update({"code_retour": execution.returncode, "nombre_tests": nombre,
                      "sources_inchangees": inchange, "sha256_sources": avant,
                      "journal_tests": texte,
                      "tests_ignores": nombre_ignores,
                      "tests_reussis": execution.returncode == 0 and structure["statut"] == "complete" and inchange,
                      "suite_integralement_executee": structure["statut"] == "complete"})
        if not inchange or execution.returncode != 0:
            bilan["statut"] = "echec"
        print(f"Bilan : {nombre} tests | réussite : {bilan['tests_reussis']} | sources inchangées : {inchange}")
        if nombre_ignores:
            print(f"ATTENTION : {nombre_ignores} test(s) ignoré(s), lire leur motif ci-dessus ; couverture incomplète.")
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        bilan.update({"tests_reussis": False, "statut": "echec", "erreur": str(exc)})
        print(f"Vérification non terminée : {exc}")
    # === 6. Conserver le bilan, y compris si l'essai a échoué ou expiré ===
    try:
        dossier = PROJET / "resultats"
        dossier.mkdir(exist_ok=True)
        etiquette_version = VERSION_VISU.replace(".", "")
        chemin = dossier / f"tests_v{etiquette_version}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        with chemin.open("x", encoding="utf-8") as fichier:
            json.dump(bilan, fichier, indent=2, ensure_ascii=False, allow_nan=False)
        print(f"Journal enregistré : {chemin}")
    except OSError as exc:
        print(f"Journal non enregistré : {exc}")
    return bilan


if __name__ == "__main__":
    # L'import du module ne lance pas la suite de tests.
    resultat = main()
    if not resultat.get("tests_reussis"):
        raise SystemExit(1)
