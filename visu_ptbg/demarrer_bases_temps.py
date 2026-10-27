"""Démo guidée : examiner des horloges distinctes sans les aligner.

Ouvrir dans Spyder et exécuter (F5). Les deux CSV sont lus, puis un journal JSON
daté est créé sous resultats/. Aucun CSV reçu ni script de simulation n'est écrit.
Bibliothèques : standard Python et modules locaux seulement. Requis 3006 : les
parties de ce lanceur et les choix de temps sont expliqués ci-dessous.
"""
from __future__ import annotations

# === 1. Utiliser le dossier du projet, pas le dossier courant de Spyder ===
import json
import sys
from datetime import datetime
from pathlib import Path

PROJET = Path(__file__).resolve().parent
if str(PROJET / "src") not in sys.path:
    sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_paquet
from diagnostic_csv import VERSION


def main() -> dict:
    """Analyser deux exemples archivés et retourner leur bilan indépendant.

    `index` n'a pas d'unité ni de pas attendu confirmé dans le scénario LIM.
    Pour la simulation, le script source construit `t_ms` via int(t*1000), donc
    l'exemple choisit explicitement 1 ms avec tolérance nulle sur ce journal
    entier. Cette convention de démo n'est pas un seuil métier des futurs PLC.
    Une erreur d'écriture du journal est affichée sans masquer le bilan console.
    """

    # === 2. Choisir les profils connus sans généraliser à tous les futurs CSV ===
    paquet = examiner_paquet([
        SourceTemps(PROJET / "donnees" / "scenari0002.csv", colonne_temps="index"),
        SourceTemps(PROJET / "donnees" / "simulation10_execution1.csv", colonne_temps="t_ms",
                    unite="ms", pas_attendu="1", tolerance="0"),
    ])

    # === 3. Afficher séparément les constats par source et les refus éventuels ===
    print(f"VISU PTBG — bases de temps, étape 2 (v{VERSION})")
    for fichier in paquet["sources"]:
        print(f"\nFichier : {Path(fichier['fichier']).name}")
        if "erreur" in fichier:
            print(f"  Lecture impossible : {fichier['erreur']['message']}")
            continue
        diagnostic = fichier["diagnostic_csv"]
        temps = diagnostic["time"]
        print(f"  Temps : {temps['column'] if temps else 'à choisir'} | unité : {fichier['unite'] or 'inconnue'}")
        print(f"  Pas observés : {temps['step_values'] if temps else 'indisponibles'}")
        evaluation = fichier["evaluation_pas"]
        if evaluation["effectuee"]:
            print(f"  Doublons : {evaluation['doublons_adjacents']} | retours : {evaluation['retours_arriere']}")
            print(f"  Écarts positifs au pas choisi : {evaluation['ecarts_positifs']}")
            for ecart in evaluation["exemples_ecarts_positifs"][:5]:
                print(f"  Écart lignes {ecart['ligne_precedente']}-{ecart['ligne']} : pas {ecart['pas_observe']}")
        else:
            print(f"  Pas attendu : non évalué. {evaluation['motif']}")
    print("\nComparaison entre horloges : non effectuée (origine et unités communes non établies).")

    # === 4. Conserver un bilan daté, sans modifier les fichiers d'entrée ===
    try:
        resultats = PROJET / "resultats"
        resultats.mkdir(exist_ok=True)
        chemin = resultats / f"bases_temps_v{VERSION.replace('.', '')}_{datetime.now():%Y%m%d_%H%M%S_%f}.json"
        with chemin.open("x", encoding="utf-8") as flux:
            json.dump(paquet, flux, ensure_ascii=False, indent=2, allow_nan=False)
        print(f"Journal enregistré : {chemin}")
    except OSError as exc:
        print(f"Diagnostic terminé, journal non enregistré : {exc}")
    return paquet


if __name__ == "__main__":
    main()
