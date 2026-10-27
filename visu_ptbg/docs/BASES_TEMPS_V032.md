# Examen séparé des bases de temps version 0.3.2

La version 0.3.2 ajoute `src/base_temps.py` et le lanceur `demarrer_bases_temps.py`. La lecture CSV reste celle de `diagnostic_csv.py` ; chaque fichier reçoit son propre objet de diagnostic et conserve ses timestamps bruts. Cette étape sert à traiter plusieurs fichiers sans supposer que les mêmes numéros de ligne décrivent le même instant.

## Contrat et comportement

Pour chaque CSV, `SourceTemps` permet d'indiquer le nom de la colonne temporelle, l'unité si elle est connue, et éventuellement un pas attendu avec sa tolérance. Ces deux dernières valeurs sont des textes numériques explicites dans l'unité native du CSV. Aucun seuil ne vient automatiquement du nom `index` ou d'une fréquence supposée du PLC.

Le lecteur établit d'abord la structure, les lignes rejetées et les anomalies de temps. Si aucune ligne n'est rejetée et si au moins deux timestamps numériques sont disponibles, le module peut comparer chaque intervalle positif au pas et à la tolérance demandés. Il donne un compte et les vingt premiers exemples avec lignes physiques. Les doublons et retours arrière restent dans le diagnostic temporel du lecteur. Un intervalle hors tolérance est un **écart à examiner** : ce seul constat ne démontre pas une perte d'enregistrement ou une panne d'automate.

En cas de ligne rejetée, de syntaxe partielle, de temps invalide ou de profil incomplet, le résultat décrit pourquoi l'évaluation du pas n'a pas été effectuée. Une erreur d'accès sur un fichier est notée sans empêcher l'examen des autres. La comparaison temporelle *entre* fichiers reste explicitement « non effectuée », faute de confirmation de leur origine et unité communes.

## Jeu d'essai et preuves

La démonstration lit le scénario LIM et une exécution archivée de `Redundancy10.py`. Dans le scénario, `index` augmente de 20 en 20 ; son unité n'est pas déclarée. Dans la simulation, le script source construit `t_ms` à partir de secondes ; la démonstration utilise un pas demandé de 1 ms et une tolérance zéro sur le journal entier généré. Elle y retrouve deux doublons et un intervalle positif de 2 ms hors du pas demandé. Ces trois écarts de la colonne journal peuvent provenir du calcul et de la troncature des timestamps ; ils ne sont pas présentés comme trois pertes physiques.

Six nouveaux tests sous `tests/test_base_temps.py` couvrent : deux fichiers aux débuts décalés, une tolérance non nulle, la distinction doublon/écart positif, un rejet qui suspend l'évaluation, l'isolement d'un fichier absent ou d'un profil invalide, et les anomalies conservées de la simulation archivée. Avec les 43 tests antérieurs, la suite comporte 49 cas. Le résultat local est à compléter après exécution sur le poste cible ; ne pas reprendre la preuve Windows des 43 tests pour cette nouvelle version.

## Traçabilité des requis, sans clôture prématurée

| Requis | Apport de cette étape | Encore ouvert |
| --- | --- | --- |
| 2103, 2104, 2105 | Accepter plusieurs fichiers et conserver leurs diagnostics temporels séparés | Origines indépendantes, déphasage réel et pertes de flux à qualifier sur jeux métier |
| 4100 | Lister les pas observés, doublons, retours arrière ; comparer à un pas/tolérance fournis | Définition métier de la période et de sa stabilité selon le type de source |
| 4101 | Signaler les écarts de pas sur les lignes de structure valide | Prouver une donnée manquante ou un mauvais phasage exige des références supplémentaires |
| 4105, 4106 | Un fichier en défaut n'empêche pas le bilan des autres ; pas/tolérance configurables | Interaction avec la future interface et diagnostic saisi par l'utilisateur |
| 3004, 3006 | Bibliothèque standard uniquement ; fichier et fonctions commentés par parties | Matrice de dépendances et revue du produit final |

Les horodatages absolus (`hh:mm:ss`, sous-secondes, fuseau/origine), les unités de `index`, la comparaison de sources en temps absolu et le Time Base Monitor graphique restent à définir. La simulation archivée utilise une **seule colonne** `t_ms` pour tous les signaux ; séparer ses colonnes en cinq fichiers ne prouvera pas l'indépendance de cinq horloges. Les tests de deux fichiers décalés sont synthétiques et contrôlent seulement que les temps ne sont pas alignés artificiellement.
