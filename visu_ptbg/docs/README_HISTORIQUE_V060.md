# VISU PTBG — première courbe v0.6.0

Windows 11 64 bits / Python 3.11 : environnement de développement retenu. Déploiement Windows pressenti, non confirmé.

## Nouveautés et revue des requis

Une courbe numérique avec son Time Base Monitor partageant le même axe X. Les points conservent leurs timestamps ; aucun recalage ni interpolation. Matplotlib est nécessaire au tracé, pas au diagnostic CSV. Le journal environnement_*.json relève les versions réellement installées, sans installer ni mettre à jour de module.

Les 64 lignes de la spécification sont suivies dans docs/MATRICE_REQUIS_V060.md et .json : état, réalisation, vérification attendue, reste à faire et verdict de revue encore ouvert. Les dix templates sont analysés dans docs/REVUE_TEMPLATES.md. Leurs conventions de fonctions de dessin et de commentaires par parties sont reprises.

## Essai de cette version

1. Extraire dans un nouveau dossier et conserver les anciens journaux.
2. Ouvrir verifier_robustesse.py puis F5 : attendu 66 tests, OK, aucun test ignoré, sources inchangées True. Un test graphique ignoré faute de Matplotlib ne valide pas le dessin.
3. Redémarrer le noyau Spyder pour ne pas conserver les anciens modules ; ouvrir MAIN.py puis F5.
4. Ajouter donnees/simulation10_execution1.csv ; sélectionner le fichier ; saisir colonne t_ms, unité ms, pas 1, tolérance 0 ; Analyser ce fichier.
5. Onglet Courbe : choisir un signal numérique et Afficher le signal. Vérifier les doublons à 1006 et 9815 ms et le pas hors tolérance à 4986 ms. Zoomer : les deux axes doivent suivre le même temps.
6. Conserver les journaux de tests et d’environnement. Essai interactif Windows de v0.6.0 encore à effectuer.

## Limites actuelles

Une seule courbe ; points seuls, sans escalier supposé. Les valeurs absentes ne deviennent pas zéro. Les timestamps perdant leur distinction lors de la conversion graphique sont refusés. Limite de prototype : 500000 points, non équivalente au requis de taille encore non renseigné. Lecture synchrone : réactivité sur gros fichiers non qualifiée.

Les types Bool/Float explicites, groupes binaires, temps absolus, analyse inter-PLC, arrangements multiples, curseurs, rapports PDF et exécutable restent à développer ou qualifier. La sauvegarde de la barre Matplotlib est désactivée : elle ne constitue pas le rapport demandé.

Le code cible Python 3.11, pas Python 3.6. Le texte historique SLES/Python 3.6 reste tracé pour adaptation à la cible confirmée ; il ne commande pas une migration de notre développement vers Linux. Aucun requis n’est déclaré globalement validé.

## Historique de la version précédente

Les indications suivantes décrivent v0.5.0 et ses preuves, pas la procédure de lancement v0.6.0. La mention ancienne « sans bibliothèque externe » concernait le diagnostic sans courbe.

# VISU PTBG — Time Base Monitor v0.5.0

Écrit pour Python 3.11 et sans bibliothèque externe. Les 49 tests de v0.3.2 ont réussi sur le poste de Mourad : Python 3.11.10, Windows, interpréteur 64 bits, « sources inchangées : True ». L'ouverture, la sélection multiple et les diagnostics de la fenêtre v0.4.0 ont ensuite été constatés sur ce poste. La v0.5.0 ajoute le premier Time Base Monitor et doit y être essayée.

La fenêtre permet de choisir plusieurs CSV, de parcourir les colonnes de chacun et de lire un bilan temporel par fichier. Le Time Base Monitor affiche un axe vert lorsque le pas observé est régulier et des repères colorés sur les anomalies connues. Il peut être masqué uniquement si le diagnostic ne contient ni avertissement ni erreur. Les fichiers gardent leurs propres temps ; aucune synchronisation entre PLC n'est déduite.

Pour comprendre le parcours avant de lancer les tests, ouvrir `demarrer_diagnostic.py` : les six parties expliquent successivement les dépendances, l'environnement, l'identification de l'essai, la lecture des fichiers, les comparaisons et le journal. Le détail des calculs est dans `src/diagnostic_csv.py`.

## Maintenant, dans Spyder

1. Extraire entièrement cette archive dans un nouveau dossier, par exemple `VISU_v050`. Garder le dossier précédent et ses journaux.
2. Ouvrir `visu_ptbg/verifier_robustesse.py`, puis Exécuter le fichier (F5 avec le raccourci habituel).
3. Résultat attendu : 55 tests, `OK`, `sources inchangées : True`. Les cas dégradés sont créés dans des dossiers temporaires, pas dans les fichiers reçus.
4. Ouvrir `visu_ptbg/MAIN.py`, puis F5 : cliquer sur **Ajouter des CSV…**, choisir par exemple `scenari0002.csv` et `simulation10_execution1.csv` dans `donnees/`. Cliquer dans l'arbre sur chaque fichier pour consulter son diagnostic.
5. Sur la simulation seulement, saisir `t_ms` comme colonne de temps, `ms` comme unité, `1` comme pas attendu et `0` comme tolérance, puis **Analyser ce fichier** : le moniteur reste visible et affiche trois repères, soit deux doublons et un intervalle positif hors tolérance. Dans le scénario, laisser l'unité de `index` inconnue : son axe vert indique uniquement un pas observé régulier de 20 ; son bouton de masquage est disponible.

Le journal des tests est créé dans `resultats/tests_v050_...json`. Un diagnostic enregistré depuis la fenêtre est un fichier JSON choisi par l'utilisateur ; aucun CSV n'est réécrit. La fenêtre demande tkinter dans l'interpréteur Python du poste : les tests du modèle ne remplacent pas un essai visuel Windows.

Pour observer le même diagnostic en console, ouvrir ensuite `visu_ptbg/demarrer_bases_temps.py` dans Spyder et appuyer sur F5. Le fichier LIM affiche son pas observé `20` sans unité supposée ; la simulation affiche les pas `0`, `1`, `2` et les deux doublons. Seul l'exemple de simulation demande explicitement un pas `1 ms` et une tolérance nulle. Le script enregistre un journal `resultats/bases_temps_v050_...json`. Aucun autre travail manuel dans le grand CSV n'est nécessaire.

Le lanceur de tests utilise le même interpréteur dans un nouveau processus. Il évite les anciennes versions de modules conservées dans une console Spyder déjà utilisée. Rien à installer pour ce contrôle.

## Relire les fichiers réels

Ouvrir `demarrer_diagnostic.py` dans une nouvelle console Spyder, puis Exécuter. Aucun argument requis. Le titre doit indiquer **v0.5.0**. Si l'ancienne version reste chargée, ne pas interpréter son résultat comme un test de v0.5.0.

Résultats attendus : 501 lignes pour chacun des deux CSV LIM, 1001 pour chacun des deux CSV PID, 10001 pour la première simulation archivée. La simulation conserve deux doublons temporels et les avertissements correspondants. Aucun graphique n'est attendu.

Ce lancement n'exécute pas le simulateur de Sébastien. Son utilisation ne nécessite ni NumPy, ni SciPy, ni pandas, ni Matplotlib. La configuration de l'interpréteur et les versions éventuellement installées sont enregistrées, mais elles ne constituent pas des dépendances du lecteur.

## Ajouts de v0.3

- Lignes rejetées conservées avec texte décodé, champs quand ils sont lisibles, plage de lignes physiques, code et motif.
- Champs CSV entre guillemets, séparateurs internes et champs multilignes pris en charge avec numéros de lignes physiques.
- Syntaxe CSV cassée : arrêt prudent, diagnostic partiel et conservation de la fin du fichier, sans tentative de reprise hasardeuse.
- Refus explicites pour les en-têtes incomplets/dupliqués, fichiers vides, encodages illisibles et dépassement de taille.
- UTF-8, BOM UTF-8 et UTF-16 avec BOM reconnus. Les autres encodages demandent une sélection explicite, sans deviner ni remplacer les caractères.
- Temps non finis/invalides signalés. Plusieurs colonnes temporelles candidates nécessitent un choix explicite.
- Calcul des écarts temporels en décimal : pas d'arrondi automatique à 12 décimales ni de perte de précision due au passage préalable en flottant binaire.
- Comparaison scénario/report refusée si les données rejetées, les tailles ou les temps rendent une comparaison ligne à ligne trompeuse.

## Organisation

- `src/diagnostic_csv.py` : lecteur réutilisable, diagnostic et CLI.
- `MAIN.py` : construction de la fenêtre, choix des fichiers, arbre, panneau de détail et dessin du moniteur.
- `src/paquet_csv.py` : état et descriptions du paquet, indépendamment de tkinter.
- `tests/test_paquet_csv.py` : sélection multiple, erreur locale et sources inchangées.
- `src/moniteur_temps.py` : état, règle de masquage et positions des anomalies sur l'axe.
- `tests/test_moniteur_temps.py` : états régulier/anormal, repères et règle de masquage.
- `src/base_temps.py` : examen indépendant du pas temporel pour chaque CSV avec profil explicite.
- `demarrer_bases_temps.py` : démonstration guidée du nouvel examen, avec journal JSON.
- `demarrer_diagnostic.py` : essai guidé des CSV archivés et relevé d'environnement.
- `verifier_robustesse.py` : exécution des tests et journal de preuve.
- `donnees` : CSV d'origine et deux simulations archivées, inchangés.
- `references_simulation` : copies inchangées des trois scripts reçus, distinctes du lecteur VISU.
- `tests` : non-régression et fichiers synthétiques volontairement dégradés.
- `docs/VALIDATION_ETAPE1.md` : preuve d'essai v0.2 transmise par Mourad.
- `docs/BASES_TEMPS_V032.md` : périmètre et vérification de l'étape 2.
- `docs/SUIVI_DOCUMENTATION.md` : périmètre de la revue du requis 3006 et vérifications à réaliser.
- `docs/VERIFICATION_DOCUMENTATION_V031.json` : comparaison avant/après, empreintes et résultats des essais locaux de cette révision.
- `docs/ROBUSTESSE_V03.md` : règles, limites et points restant à développer.
- `docs/ANALYSE_20261023.md` et `docs/resultats_analyse.json` : historique des premières simulations v0.2, pas un résultat d'exécution v0.3.

## Utilisation technique

```bash
python src/diagnostic_csv.py donnees/scenari0045.csv donnees/Test_PID_P_AS_scenari0045.csv
python -m unittest discover -s tests -v
```

Pour un profil connu, utiliser par exemple `--delimiter ";" --decimal "," --encoding cp1252 --time-column temps`. Ces options sont des choix explicites, pas des règles confirmées pour tous les fichiers du projet.

L'API `read_csv()` retourne les lignes acceptées, leurs valeurs textuelles brutes, leurs positions physiques et le diagnostic. `analyse_csv()` retourne le diagnostic seul. Les refus contrôlés lèvent `CsvDiagnosticError` ou `OSError`, interceptés dans les lanceurs. La CLI renvoie 2 pour une erreur ou une comparaison refusée, 0 pour une analyse terminée (qui peut comporter des avertissements à lire).

Les originaux ne sont jamais modifiés. Aucune unité n'est inventée pour `index`, aucun tri, remplacement par zéro, recalage, interpolation ou rééchantillonnage n'est effectué. Cette fenêtre n'affiche encore ni courbes de signaux, ni rapport graphique, ni horodatage absolu : la validation complète des requis, de l'IHM et de l'exécutable reste à faire. Le document de spécification mentionne toujours SLES 15 SP7 (3000) et Python 3.6 au moins (3001) : le choix de développement Windows 11/Python 3.11 ne clôt pas à lui seul ces exigences de déploiement.
