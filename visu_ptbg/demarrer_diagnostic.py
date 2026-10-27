"""VISU PTBG — diagnostic guidé des fichiers d'essai, sans interface.

Usage : ouvrir ce fichier dans Spyder et Exécuter (F5), ou le lancer avec Python.
Entrées : tous les CSV découverts sous donnees/ et ses sous-dossiers.
Sorties : résumé console, bilan retourné et nouveau journal JSON sous resultats/.
Dépendances : bibliothèque standard et module local diagnostic_csv. Les versions
des bibliothèques éventuellement installées sont relevées, pas importées.
Effets : création du dossier/journal de résultats uniquement ; CSV inchangés.
Requis 3006 : commentaires par parties ; la réussite ne valide pas tous les requis.
"""
from __future__ import annotations

# === 1. Dépendances et localisation du projet ===
# Partir du fichier courant permet de ne pas dépendre du dossier de travail Spyder.
import csv
import importlib.metadata
import json
import platform
import struct
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

PROJET = Path(__file__).resolve().parent
if str(PROJET / "src") not in sys.path:
    sys.path.insert(0, str(PROJET / "src"))
from diagnostic_csv import VERSION, CsvDiagnosticError, analyse_csv, compare_csv
from decouverte_csv import decouvrir_csv


def environnement() -> dict:
    """Retourner la configuration observée, sans certifier une plateforme cible.

    Aucun paramètre. Les modules optionnels absents sont signalés sans erreur.
    La taille d'un pointeur mesure les bits de l'interpréteur, pas à elle seule
    l'édition Windows ou la compatibilité de toutes les dépendances.
    """
    # === 2. Traçabilité de l'interpréteur et des versions installées ===
    versions = {}
    for nom in ("numpy", "scipy", "pandas", "matplotlib", "spyder-kernels"):
        try:
            versions[nom] = importlib.metadata.version(nom)
        except importlib.metadata.PackageNotFoundError:
            versions[nom] = "non installé dans cet interpréteur (non requis ici)"
    return {
        "python": platform.python_version(),
        "interpreteur": sys.executable,
        "systeme": platform.system(),
        "version_systeme": platform.version(),
        "architecture_interpreteur_bits": struct.calcsize("P") * 8,
        "versions_observees": versions,
        "dependances_externes_du_diagnostic": [],
    }


def main() -> dict:
    """Analyser les exemples archivés et retourner leur bilan structuré.

    Aucun argument : la liste des fichiers et les couples sont définis ci-dessous.
    Les erreurs connues de lecture sont enregistrées sans bloquer les autres
    fichiers. Une erreur d'écriture du journal est affichée, sans effacer le bilan.
    Aucun simulateur, graphique ou exécutable autonome n'est lancé par ce test.
    """
    # === 3. Identifier l'essai et rappeler les limites de son interprétation ===
    bilan = {"version": VERSION, "environnement": environnement(), "fichiers": [], "comparaisons": []}
    env = bilan["environnement"]
    print(f"VISU PTBG — diagnostic CSV v{VERSION}, sans interface")
    print(f"Python {env['python']} | {env['systeme']} | {env['architecture_interpreteur_bits']} bits")
    print("Cibles de livraison : Windows et SLES 15 SP7 ; environnements à qualifier.")
    print("Ce lancement enregistre la configuration observée, sans certifier la cible.")
    print("Les colonnes 'index' restent en unité non confirmée. Aucun recalage temporel.")

    # === 4. Analyser chaque CSV découvert, y compris en sous-dossier ===
    dossier = PROJET / "donnees"
    fichiers = decouvrir_csv(dossier)
    for chemin_csv in fichiers:
        nom = chemin_csv.relative_to(dossier).as_posix()
        print(f"\nFichier : {nom}")
        try:
            diagnostic = analyse_csv(chemin_csv)
        except (OSError, ValueError, UnicodeError, csv.Error) as exc:
            bilan["fichiers"].append({"fichier": nom, "erreur": exc.to_dict() if isinstance(exc, CsvDiagnosticError) else {"message": str(exc)}})
            print(f"  Lecture impossible : {exc}")
            continue
        # Le journal conserve le détail ; la console limite l'aperçu à cinq rejets.
        bilan["fichiers"].append(asdict(diagnostic))
        print(f"  {diagnostic.data_rows} lignes retenues | {len(diagnostic.columns)} colonnes")
        print(f"  {len(diagnostic.rejected_rows)} enregistrement(s) ou bloc(s) non retenu(s), conservés dans le journal")
        for rejet in diagnostic.rejected_rows[:5]:
            print(f"  Rejet lignes {rejet.line_start}-{rejet.line_end} : {rejet.reason}")
        for erreur in diagnostic.errors:
            print(f"  ERREUR : {erreur}")
        if diagnostic.time:
            temps = diagnostic.time
            print(f"  Temps candidat : {temps.column} | début {temps.start} | fin {temps.end}")
            print(f"  Pas observés : {temps.step_values}")
            print(f"  Doublons adjacents : {temps.duplicate_count} | retours arrière : {temps.backward_count}")
        for message in diagnostic.warnings:
            print(f"  ATTENTION : {message}")
        if not diagnostic.warnings and not diagnostic.errors:
            print("  Aucun avertissement parmi les contrôles de ce prototype.")

    # === 5. Comparer seulement deux couples de simulation connus et nommés ===
    # Les nouveaux CSV découverts et les sources PLC ne sont jamais appariés
    # automatiquement à une autre source selon leur position dans la liste.
    couples_connus = (("scenari0002.csv", "Test_LIM_AS_scenari0002.csv"),
                     ("scenari0045.csv", "Test_PID_P_AS_scenari0045.csv"))
    chemins_decouverts = set(fichiers)
    for scenario, report in couples_connus:
        if dossier / scenario not in chemins_decouverts or dossier / report not in chemins_decouverts:
            continue
        try:
            comparaison = compare_csv(dossier / scenario, dossier / report)
        except (OSError, ValueError, UnicodeError, csv.Error) as exc:
            comparaison = {"scenario": scenario, "report": report, "erreur": str(exc)}
        bilan["comparaisons"].append(comparaison)
    print("\nComparaisons scénario/report :")
    print(json.dumps(bilan["comparaisons"], ensure_ascii=False, indent=2))
    print("Comparaison ligne à ligne de ces couples seulement : ce n'est pas une synchronisation.")

    # === 6. Écrire une preuve d'essai datée sans écraser de journal existant ===
    # Le mode 'x' refuse un nom déjà présent ; une erreur d'écriture est signalée.
    sortie = PROJET / "resultats"
    try:
        sortie.mkdir(exist_ok=True)
        chemin = sortie / f"diagnostic_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        with chemin.open("x", encoding="utf-8") as fichier:
            json.dump(bilan, fichier, ensure_ascii=False, indent=2, allow_nan=False)
        print(f"\nJournal enregistré : {chemin}")
    except OSError as exc:
        print(f"\nDiagnostic terminé, mais journal non enregistré : {exc}")
    return bilan


if __name__ == "__main__":
    # Pas de lancement automatique si une autre partie du projet importe ce module.
    main()
