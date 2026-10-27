# Vérification de livraison v0.9.0

- 145 tests rapides exécutés, 145 réussis, 0 échec, 0 erreur, 0 ignoré.
- 1 test d’intégration exécuté séparément, réussi, aucun ignoré.
- Total : 146 tests réussis. Tests en Python 3.12/Linux, rendu Matplotlib Agg.
- Empreintes avant/après tests identiques : sources Python, lanceurs racine,
  tests, exemples, CSV et scripts de référence surveillés.
- Tous les CSV et scripts de référence de v0.8.0 sont inchangés.
- Syntaxe des modules et de MAIN analysée pour Python 3.11 ; runtime 3.11 non exécuté ici.
- PDF de démonstration de trois pages : rendu avec Poppler, lecture des en-têtes
  avec pypdf, contrôle visuel des trois pages. Croisement de légende/curseurs
  repéré puis corrigé avant livraison. Exemple X/Y relu et notes rectifiées.
- Le premier lancement du nouveau sous-processus de tests a révélé un import
  racine manquant. Il a été corrigé ; la suite complète a été réexécutée avec succès.

## Ce qui n’est pas validé

Aucun écran/serveur d’affichage disponible ici : pas d’essai natif Tkinter.
Windows 11 x64 et SLES 15 SP7 x86-64 restent à qualifier. Les tests de calcul,
Agg et PDF ne prouvent pas à eux seuls les dialogues, les onglets, les DPI ni la
réactivité de tous les widgets sur ces cibles. Le README fournit le parcours.
Le rendu Matplotlib et PDF reste synchrone ; annulation de lecture coopérative.
Aucun exécutable fabriqué, aucune synchronisation inter-PLC.

## Fichiers et raisons des changements

| Fichier | Modification et but |
|---|---|
| MAIN.py | Raccordement des tâches, onglets, types, rapports, aide et journal de session |
| src/taches.py | Lecture hors du fil Tk, messages et annulation sans appliquer de résultat abandonné |
| src/signal_csv.py | Bool explicite et textes bruts pour lecture fidèle des curseurs |
| src/trace_signal.py | Présentation Bool et notes adaptées au X/Y ; calculs temporels inchangés |
| src/curseurs.py | Lecture des points réels, doublons/absences, curseurs simples/doubles/horizontaux |
| src/vue_signal.py | Commandes de curseurs, lectures à droite, superposition même CSV |
| src/vue_arrangements.py | Onglets persistants, trois dispositions, défilement et liaison des curseurs même CSV |
| src/vue_xy.py | Couples valides de la même ligne, axe temps indépendant, lecture des points |
| src/rapport_pdf.py | Captures figées, moniteur obligatoire, en-tête traçable et écriture sans écrasement |
| src/vue_rapports.py | Export actif ou composition ordonnée de captures |
| src/executer_tests.py | Résultats unittest structurés, sans analyse du texte console |
| verifier_robustesse.py | Hachage par blocs, surveillance racine, statuts complet/partiel/échec |
| src/version_visu.py | Source unique de version : 0.9.0 |
| tests/test_requis_v090.py | 16 nouveaux tests de régression avec références aux requis |
| exemples/demonstration_v090.py | Démonstration PDF reproductible à partir des simulations existantes |
| README.md et docs/ | Mode d’emploi, dépendances, matrice complète, questions Sébastien et guide de reprise |

Le diff textuel complet se trouve dans `DIFF_V080_V090.patch`.
L’état des requis distingue implémentation, limites et validation humaine.
