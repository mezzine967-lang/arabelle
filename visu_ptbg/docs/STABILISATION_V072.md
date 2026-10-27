# Stabilisation du Lot 1 — v0.7.2, 26 octobre 2026

## Résultat et périmètre

La lecture des CSV qui changent pendant l'analyse est sécurisée. Le diagnostic
compte correctement les couples non calculables même si aucun timestamp n'est
valide. Aucun traitement CSV ou temporel n'a été déplacé dans MAIN.py.

La structure et la revue Copilot sont décrites dans `REVUE_COPILOT_LOT1.md`.
Cette version poursuit uniquement le Lot 1 et conserve les croix ainsi que
l'inspection Δt déjà demandées par Mourad. Le plan Excel n'a pas été modifié.

## Défauts reproduits avant correction

Les cinq nouveaux tests de `tests/test_import_lot1.py` ont d'abord été exécutés
sur le code v0.7.1 : quatre échecs d'assertion et une erreur non interceptée.
Les fichiers utilisés sont synthétiques et temporaires.

| Cas | Comportement v0.7.1 constaté | Correction v0.7.2 |
|---|---|---|
| Le fichier change, est interprété puis retrouve ses octets initiaux | Diagnostic accepté avec l'empreinte d'un autre contenu que celui interprété | SHA-256 des octets réellement lus pendant le parsing, comparé au contrôle initial |
| Le fichier grandit après le contrôle initial et est rétabli avant le contrôle final | Dépassement de la limite accepté lors du parsing | Comptage des octets pendant le parsing, refus au premier octet excédentaire |
| Un caractère NUL apparaît pendant le parsing puis disparaît | Cellule acceptée malgré le contrôle initial | Contrôle des lignes décodées pendant le parsing |
| L'encodage devient invalide pendant le parsing | UnicodeDecodeError sort de l'import et empêche le fichier suivant d'être analysé | Refus CsvDiagnosticError isolé par le mécanisme existant du paquet |
| Tous les timestamps sont invalides | Zéro couple non calculable pour trois lignes | Deux couples non calculables, aucun faux pas ni zéro de remplacement |

Le lecteur effectue toujours trois passages. Il ne verrouille pas le fichier
source et ne prétend pas fournir un instantané transactionnel. Le diagnostic
n'est publié que si les empreintes des contenus lus concordent.

## Diff expliqué fichier par fichier, depuis la v0.7.1

| Fichier | Modification et raison |
|---|---|
| `src/diagnostic_csv.py` | Petit adaptateur `_LectureBornee` pour compter/hacher pendant la lecture, ouverture contrôlée et erreur d'encodage explicite ; compteur des couples initialisé avant les retours anticipés ; version 0.7.2 |
| `tests/test_import_lot1.py` | Cinq régressions couvrant les défauts ci-dessus et un utilitaire de simulation limité aux fichiers temporaires |
| `MAIN.py` | Numéro affiché 0.7.2 ; aucun nouveau parcours graphique |
| `verifier_robustesse.py` | Numéro et nom du journal 0.7.2 ; fonctionnement du lanceur inchangé |
| `demarrer_diagnostic.py` | Message de cible mis à jour pour Windows et SLES 15 SP7 |
| `README.md`, `docs/DEPENDANCES.md` | Version, parcours d'essai et double cible actualisés |
| `AGENTS.md`, `MISSION_CODEX.md` | Consigne de code lisible et état de la mission actualisés |
| `docs/REPRENDRE_LE_CODE.md` | Guide pour Sébastien : parcours de lecture, fonctions à modifier, exemple, raisons des précautions |
| `docs/STABILISATION_V072.md`, preuves et diffs | Revue et traçabilité de cette stabilisation |

Diffs textuels inclus : `DIFF_V071_V072.patch` pour cette reprise et
`DIFF_V060_V072.patch` pour l'ensemble depuis la dernière version testée par
Mourad. Ils excluent les journaux générés, les preuves historiques et les caches.

## Vérifications

Résultat local : **95 tests rapides réussis et 1 test d'intégration réussi ;
0 échec, 0 erreur, 0 test ignoré**. Les 36 fichiers surveillés sont inchangés
pendant les essais ; les six CSV et trois scripts de référence sont identiques
aux octets archivés en v0.6.0.

La preuve `preuve_tests_linux_v072.json` détaille les résultats structurés
unittest, l'environnement, les empreintes avant/après et la correspondance des
CSV/scripts de référence avec l'archive v0.6.0.

La suite rapide couvre notamment UTF-8/UTF-16, BOM, fins de lignes CRLF,
champs multilignes, lignes rejetées, temps invalides, précision décimale,
absence de pont entre voisins non contigus, croix et vrais zéros. L'essai de
volume est séparé. Les tests de dessin utilisent Matplotlib Agg.

Le contrôle d'intégrité de cette livraison couvre aussi les scripts racine
et `tests_integration/`, en complément du périmètre du lanceur existant.
Il vérifie l'absence de mutation pendant les essais ; les modifications
intentionnelles décrites ci-dessus ne sont pas présentées comme inchangées.

## Limites et risques restants

- Le nouvel adaptateur intervient avant le décodage : risque de régression sur
  encodages, fins de lignes et provenance, couvert par les tests existants et
  l'essai de volume. Les essais natifs Windows/SLES restent nécessaires.
- La lecture est en flux, mais les enregistrements restent en mémoire. La
  limite de 50 MiB n'est pas une garantie de consommation RAM ni de performance.
- L'IHM reste synchrone. Tâche de fond, progression, annulation et sélection
  guidée des colonnes sont des travaux ultérieurs.
- Le lanceur conserve son extraction du résumé unittest par texte et son
  périmètre historique ; les preuves structurées et le contrôle étendu de
  cette livraison sont complémentaires. Modernisation à traiter séparément.
- Version unique et journalisation commune restent à faire. Aucun refactoring
  transversal n'a été ajouté au Lot 1.
- Les unités/origines entre PLC, le jitter et la règle permettant de conclure
  à une perte ne sont pas encore définis. Les signaux textuels n'ont pas de
  correspondance numérique arbitraire.
- Aucun exécutable n'est produit et aucun essai sur Linux générique ne vaut
  qualification SLES 15 SP7. La suite peut réussir sans valider tous les requis.

Prochaine étape utilisateur : suivre le parcours court du README sous Windows.
Le Lot 2 nécessite ensuite une décision humaine sur les règles temporelles.
