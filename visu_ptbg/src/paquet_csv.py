"""État du paquet de CSV affiché dans VISU, sans dépendance à l'interface.

Un fichier représente une source avec ses propres paramètres temporels et son
propre résultat. Ajouter ou reconfigurer un fichier ne recale aucun autre CSV.
Les originaux sont uniquement lus. La couche graphique peut accéder aux
diagnostics bruts et à une description courte adaptée à son panneau de détail.
"""
from __future__ import annotations

# === 1. État et identité des fichiers, conservés dans leur ordre d'ouverture ===
from dataclasses import asdict, replace
import json
from pathlib import Path
from typing import Any

from base_temps import SourceTemps, examiner_paquet
from decouverte_csv import decouvrir_csv


class PaquetCSV:
    """Conserver les profils et bilans par fichier, y compris les erreurs."""

    def __init__(self) -> None:
        self.sources: list[SourceTemps] = []
        self.resultats: list[dict[str, Any]] = []

    def ajouter(self, chemins: list[str | Path]) -> int:
        """Lire les nouveaux CSV ; ignorer une nouvelle sélection du même chemin."""
        ajoutes = 0
        for brut in chemins:
            chemin = Path(brut).expanduser().resolve()
            if chemin in (Path(s.fichier) for s in self.sources):
                continue
            source = SourceTemps(chemin)
            resultat = examiner_paquet([source])["sources"][0]
            # Le requis 2304 impose la première colonne. La mémoriser dans le
            # profil évite que l'interface et les traitements divergent.
            if "erreur" not in resultat:
                source = replace(source, colonne_temps=resultat["diagnostic_csv"]["columns"][0])
            self.sources.append(source)
            self.resultats.append(resultat)
            ajoutes += 1
        return ajoutes

    def ajouter_dossier(self, dossier: str | Path) -> int:
        """Ajouter tous les CSV du dossier et des sous-dossiers, sans comparaison."""
        return self.ajouter(decouvrir_csv(dossier))

    def configurer(self, indice: int, unite: str | None, pas_attendu: str | None,
                   tolerance: str | None) -> dict[str, Any]:
        """Réexaminer un CSV avec son unité, son pas et sa tolérance.

        La colonne de temps n'est pas un choix : c'est la première. Le lecteur
        capture les erreurs de profil ou d'accès dans son bilan ;
        les autres profils et résultats restent à leur place dans le paquet.
        Les textes sont gardés pour permettre une correction visible.
        """
        nouveau = replace(self.sources[indice], unite=unite or None, pas_attendu=pas_attendu or None,
                          tolerance=tolerance or None)
        bilan = examiner_paquet([nouveau])["sources"][0]
        self.sources[indice] = nouveau
        self.resultats[indice] = bilan
        return bilan

    def journal(self) -> dict[str, Any]:
        """Obtenir un cliché JSON du paquet, sans aligner les fichiers."""
        return {
            "nombre_sources": len(self.sources),
            "sources": self.resultats,
            "comparaison_entre_horloges": "non_effectuee",
            "raison": "Origines et unités communes non établies par la lecture des CSV.",
            "profils": [{**asdict(s), "fichier": str(s.fichier)} for s in self.sources],
        }

    def enregistrer_journal(self, chemin: str | Path) -> None:
        """Créer un JSON neuf ; refuser l'écrasement d'un CSV ou d'un autre fichier."""
        destination = Path(chemin)
        if destination.suffix.lower() != ".json":
            raise ValueError("Le diagnostic doit être enregistré dans un nouveau fichier .json.")
        if destination.exists():
            raise ValueError("Ce fichier existe déjà : choisir un nouveau nom pour préserver son contenu.")
        contenu = json.dumps(self.journal(), ensure_ascii=False, indent=2, allow_nan=False)
        with destination.open("x", encoding="utf-8") as sortie:
            sortie.write(contenu)


# === 2. Descriptions pour la fenêtre, sans inventer une unité ni un défaut ===
def decrire_source(source: SourceTemps, resultat: dict[str, Any]) -> str:
    """Construire un bilan lisible à partir du diagnostic de ce seul fichier."""
    lignes = [f"Fichier : {source.fichier}"]
    if "erreur" in resultat:
        return "\n".join(lignes + [f"Lecture ou profil refusé : {resultat['erreur']['message']}"])
    diagnostic = resultat["diagnostic_csv"]
    temps = diagnostic["time"]
    lignes.extend([
        f"Lignes retenues : {diagnostic['data_rows']} | lignes rejetées : {len(diagnostic['rejected_rows'])}",
        f"Colonnes : {len(diagnostic['columns'])} | lecture : {diagnostic['status']}",
        f"Temps (première colonne) : {temps['column'] if temps else 'indisponible'} | unité : {source.unite or 'inconnue'}",
    ])
    if temps:
        lignes.extend([
            f"Début : {temps['start_raw']} | fin : {temps['end_raw']}",
            f"Pas observés : {temps['step_values']}" +
            (" (liste tronquée)" if temps["step_values_truncated"] else ""),
            f"Doublons adjacents : {temps['duplicate_count']} | retours arrière : {temps['backward_count']}",
        ])
    analyse = resultat["analyse_temporelle"]
    raster = analyse.get("raster")
    if raster and raster["valeur"] is not None:
        lignes.append(
            f"Raster {raster['origine']} : {raster['valeur']} ± {raster['tolerance']} "
            f"{source.unite or '(unité native inconnue)'}"
        )
    else:
        lignes.append(f"Raster : non déterminé. {analyse.get('motif') or ''}".rstrip())
    comptes = analyse.get("comptes", {})
    lignes.append(
        "Diagnostic temporel " + analyse["statut"] + " : "
        f"jitter {comptes.get('jitter', 0)} | trous probables {comptes.get('trou_probable', 0)} | "
        f"changements de fréquence probables {comptes.get('changement_frequence_probable', 0)}"
    )
    lignes.append(
        f"Échantillons probablement manquants : {analyse.get('echantillons_probablement_manquants', 0)} "
        "(estimation, aucune donnée ajoutée)"
    )
    evaluation = resultat["evaluation_pas"]
    if evaluation["effectuee"]:
        lignes.append(f"Pas attendu : {source.pas_attendu} ± {source.tolerance} {source.unite or '(unité du CSV non confirmée)'}")
        lignes.append(f"Intervalles positifs hors tolérance : {evaluation['ecarts_positifs']}")
        for exemple in evaluation["exemples_ecarts_positifs"]:
            lignes.append(f"  Lignes {exemple['ligne_precedente']}–{exemple['ligne']} : pas {exemple['pas_observe']}")
        if evaluation["exemples_tronques"]:
            lignes.append("  Autres écarts consignés dans le nombre total ; exemples limités à 20.")
    else:
        lignes.append(f"Comparaison à un pas attendu : non effectuée. {evaluation['motif']}")
    if diagnostic["rejected_rows"]:
        lignes.append("Des lignes rejetées sont conservées dans le journal ; bilan des pas suspendu.")
    if diagnostic["warnings"]:
        lignes.append("Avertissements :")
        lignes.extend(f"  • {avertissement}" for avertissement in diagnostic["warnings"])
    lignes.append("Comparaison avec les autres horloges : non effectuée.")
    return "\n".join(lignes)
