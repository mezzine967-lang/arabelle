# Étape v0.4.0 : paquet de CSV et diagnostic dans une fenêtre

L'utilisateur ouvre `MAIN.py`, choisit un ou plusieurs CSV et voit chaque source dans un arbre. Chaque fichier expose ses colonnes et sa base de temps. Un panneau détail affiche les pas observés, doublons, retours arrière, avertissements et les écarts à un pas attendu lorsque l'utilisateur renseigne ensemble ce pas et sa tolérance. L'unité et l'origine de `index` ne sont pas présumées. Les erreurs de lecture ou de profil sont visibles, sans interrompre les autres fichiers.

La construction des éléments graphiques reste dans `MAIN.py`. `src/paquet_csv.py` garde la liste des profils et orchestre les analyses locales ; `src/base_temps.py` et `src/diagnostic_csv.py` font les calculs. Les entrées sont lues sans réécriture ; un JSON n'est enregistré qu'à la demande dans un chemin choisi. Le fichier peut être choisi deux fois dans le sélecteur sans être chargé deux fois. Les types affichés à côté des colonnes sont **indicatifs**, pas une validation Bool/Float métier.

| Requis | Avancement vérifiable dans cette étape | Encore à faire |
| --- | --- | --- |
| 2103–2105, 2300, 5200–5203 | Un paquet accepte plusieurs CSV, liste chaque fichier et sa colonne de temps avec un diagnostic distinct | Valider les vrais fichiers PLC séparés, les flux perdus, la nature des variables et la conformité du CSV final |
| 3002–3004, 3006 | `MAIN.py` construit l'IHM ; analyse dans `src` ; modules commentés par sections ; tkinter est standard | Registre final des dépendances et compatibilité SLES/Python 3.6 |
| 4100, 4101, 4105, 4106 | Pas, doublons et retours sont visibles ; pas/tolérance paramétrables ; erreur d'un CSV isolée | Critères métier, phasage entre sources et détection prouvée de pertes |
| 5100–5103, 5105 | Menu, informations/aide, barre d'activité et arbre escamotable ; version visible | Compléter ces zones dans l'IHM finale |
| 4102–4104, 4107, 5104, 5106 | Aucun graphique produit par cette étape | Time Base Monitor sur chaque vue/rapport, règle de masquage, temps absolu et onglets de graphes |

Preuves : les 49 tests de v0.3.2 ont réussi sous Windows 11 / Python 3.11.10 / 64 bits sur le poste utilisateur. Deux tests nouveaux vérifient le modèle de sélection, le profil en erreur puis corrigé, et la conservation des sources. L'essai visuel de `MAIN.py` doit être fait sur Windows par l'utilisateur ; les tests sans écran ne le prouvent pas.
