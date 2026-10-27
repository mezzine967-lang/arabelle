# Documentation du code VISU PTBG 0.3.1

Cette passe documente le code existant avant de développer la suite. Elle ajoute des repères par grandes parties, le rôle des fonctions, leurs entrées/sorties et les principales limites. Elle ne documente pas chaque ligne et n'ajoute pas de fonctionnalité.

## Requis concerné et état réel

Source relue : `NCS00ICOMMON----ES010.docx`, révision A du 13/10/2026, section des requis de développement. Le requis `REQ_COMMON_KH_3006` indique : « Code source shall be commented ».

Le détail « par grandes parties, pas ligne par ligne » correspond à la consigne de Mourad dans la conversation. C'est la règle de rédaction appliquée ici, pas une citation supplémentaire de la spécification.

| Requis | Travail de cette révision | Vérification du requis | État |
| --- | --- | --- | --- |
| REQ_COMMON_KH_3006 | Commentaires par blocs et descriptions dans les six fichiers Python développés pour le diagnostic et ses tests | Relecture des en-têtes, fonctions et décisions ; contrôle automatique de présence des descriptions ; revue de compréhension par Mourad | Documenté et revu sur ce périmètre par l'assistant ; revue utilisateur et couverture du futur logiciel complet encore ouvertes |
| REQ_COMMON_KH_3003 | Séparation existante entre lecteur, lanceur et tests explicitée, sans réorganisation | Examiner les responsabilités et, plus tard, vérifier que l'IHM appelle les traitements dédiés | Partiel ; aucune clôture dans cette révision |
| REQ_COMMON_KH_3004 | Absence de dépendances externes du lecteur/lanceurs/tests rappelée dans les en-têtes | Vérifier les imports ; documenter séparément toute future bibliothèque, version et compatibilité avec l'interpréteur | Partiel ; registre complet du logiciel final à établir |
| REQ_COMMON_KH_3005 | Limite des preuves Windows/Linux rappelée | Documenter les mécanismes de portabilité, puis essais sur chaque cible confirmée | Ouvert ; la présence de commentaires ne valide pas la compatibilité OS |
| REQ_COMMON_KH_3007 | Rôle de chaque fonction expliqué ; aucune fonction ajoutée à ces six fichiers | Revue des appels et de l'utilité de chaque fonction sur le périmètre du produit final | Revue globale encore ouverte ; pas de validation automatique par le nombre de tests |

Cette table suit uniquement la présente révision. Elle ne remplace pas le plan Excel et la matrice complète des requis ; ceux-ci ne sont pas modifiés dans cette passe. Aucun autre requis n'est déclaré validé ici.

## Périmètre commenté

| Fichier | Rôle et découpage expliqués |
| --- | --- |
| `src/diagnostic_csv.py` | Dépendances ; objets/erreurs ; conversion numérique ; lecture/encodage ; séparateur/types ; temps ; lecture des enregistrements ; comparaison ; ligne de commande |
| `demarrer_diagnostic.py` | Configuration observée ; lecture des cinq exemples ; comparaison LIM/PID ; enregistrement du bilan |
| `verifier_robustesse.py` | Empreintes ; processus de test neuf ; environnement ; résultats ; journal daté |
| `tests/test_diagnostic_csv.py` | Trois cas simples dont les résultats peuvent être vérifiés à la main |
| `tests/test_nouveaux_cas.py` | Cinq cas : données réelles archivées, BOM, valeurs absentes et ligne ajoutée |
| `tests/test_robustesse_csv.py` | Trente-cinq cas de robustesse regroupés et expliqués ; rôle des utilitaires de test |

Les fichiers de `references_simulation/` sont des copies de sources reçues, pas des modules du lecteur. Ils sont conservés à l'identique, tout comme les six CSV de `donnees/`. Leur conservation ne vaut pas revue de conformité au requis 3006. Si leur code est intégré au produit, il faudra le revoir, le documenter et tracer ses dépendances séparément. `_csv_check.py` a été étudié mais n'est pas intégré.

## Points explicités dans les commentaires

- Une ligne de bonne largeur peut contenir une cellule invalide : « retenue » ne signifie pas « valide métier ».
- Les enregistrements rejetés gardent leur contenu et leur position physique ; ils ne sont pas simplement oubliés.
- Un enregistrement CSV peut couvrir plusieurs lignes physiques. Une syntaxe de guillemets cassée peut rendre toute la suite ambiguë.
- Un temps invalide empêche de calculer les statistiques temporelles ; il n'est pas remplacé par zéro.
- Un temps irrégulier n'est pas, à lui seul, la preuve d'une perte de données. Aucun recalage n'est effectué.
- Le calcul utilise des décimaux ; certains nombres du résumé JSON sont des flottants d'affichage. Le texte source reste disponible.
- La comparaison actuelle est textuelle et positionnelle, après contrôle numérique des temps. Ce n'est pas une synchronisation de PLC.
- Le typage est indicatif : une colonne 0/1 n'est pas automatiquement reconnue comme un signal binaire métier.
- Les limites de taille et de précision sont celles du prototype, pas des limites approuvées par la spécification.
- Le contrôle d'empreintes du lanceur surveille `donnees/`, `references_simulation/`, `src/` et `tests/`, pas les lanceurs eux-mêmes ni les journaux.

## Vérifier que la documentation n'a pas changé les calculs

La preuve détaillée est conservée dans `VERIFICATION_DOCUMENTATION_V031.json` :

1. Comparer les arbres syntaxiques Python avant/après, en excluant les descriptions et les seules chaînes de version/préfixe de journal identifiées. Les instructions de calcul et les assertions doivent rester identiques.
2. Vérifier la présence d'une description pour chaque module, classe et fonction des six fichiers concernés. Ce contrôle de présence ne prouve pas la qualité des explications ; la relecture reste nécessaire.
3. Exécuter les 43 tests avant et après la passe, puis le lanceur de robustesse mis à jour.
4. Comparer les diagnostics des cinq fichiers et les deux comparaisons avant/après, hors chemins des copies et numéro de version.
5. Comparer les empreintes des six CSV et des trois scripts de référence avec celles de la sauvegarde avant modification.
6. Extraire l'archive livrable dans un dossier neuf et y relancer les 43 tests.

Les essais de préparation sont réalisés sous Linux avec l'interpréteur enregistré dans la preuve. Ils ne sont pas des essais sur le poste Windows de Mourad. La preuve Windows déjà reçue reste celle des huit tests de v0.2 ; il faut un nouvel essai pour v0.3.1.

## Revue guidée sur le poste de Mourad

1. Garder l'ancien dossier et extraire l'archive dans un nouveau dossier `VISU_v031`.
2. Lire d'abord `demarrer_diagnostic.py` : les titres de parties permettent de suivre le parcours sans comprendre toutes les instructions Python.
3. Lire ensuite les parties 6 à 8 de `src/diagnostic_csv.py` : ce sont les règles de temps, lecture et comparaison. Signaler tout commentaire qui ne permet pas de comprendre la décision prise.
4. Dans Spyder, ouvrir `verifier_robustesse.py` et exécuter. Le titre attendu contient `v0.3.1`, le bilan attendu indique 43 tests réussis et `sources inchangées : True`.
5. Conserver le journal `resultats/tests_v031_...json`. La revue des commentaires et le résultat des tests sont deux preuves différentes.

Après cette revue, la prochaine étape sera de définir le contrat d'import et de temps à partir des requis, sans l'implémenter silencieusement dans cette révision. Restent notamment à trancher l'unité/origine de `index`, les horodatages absolus, le contrôle du temps en première colonne et les cibles de déploiement. Les mentions SLES 15 SP7 (3000), Python 3.6 au moins (3001), le maximum `xxxMo` (2310), l'identifiant 2201 dupliqué et le requis 5500 vide ne sont pas résolus par cette passe de commentaires.
