# Heures : REQ 2306 et extension du diagnostic 4100

`diagnostic_csv._temps_decimal` accepte les compteurs historiques ou une heure
HH:MM:SS[.fraction]. Les heures sont calculées en secondes depuis minuit avec
Decimal, jamais via une conversion en flottant. Le lecteur conserve chaque
chaîne brute, la provenance physique et les octets sources. Le format d'heure
valide va de 00:00:00 à 23:59:59.999999999.

Le diagnostic, le moteur, l'inspection, le signal et les positions du moniteur
emploient ce même parseur. Les fractions ont de 1 à 9 chiffres après le point.
La précision graphique est toujours contrôlée séparément de la précision du
calcul. Une cellule invalide reste une rupture locale. Les signaux ne passent
pas par le parseur temporel et leur comportement reste inchangé.

Les profils d'heures doivent utiliser s (ou aucune unité saisie). La valeur du
pas et sa tolérance sont en secondes ; aucune conversion silencieuse du profil.
Un compteur et une heure dans le même fichier provoquent un refus explicite.

## Limites et décisions nécessaires

- Sans date, un retour après minuit peut être un changement de jour ou une
  remise à zéro. Aucun lendemain ajouté automatiquement.
- 4107 : origine absolue, fuseau et signification de « Clock Jitter ignored »
  à confirmer. Un temps en secondes depuis minuit n'est pas un timestamp absolu.
- 4101 inter-PLC : référence temporelle et déphasage acceptable à préciser.
- 2310 : taille maximale toujours indiquée xxx Mo dans le requis.
- 5500 : énoncé vide ; aucun comportement ne peut en être déduit.
- Windows 11 et SLES : qualifications natives toujours nécessaires.

Ces points n'empêchent pas de poursuivre les fonctions indépendantes. Réactivité
de l'IHM, plusieurs signaux, modèles graphiques, curseurs et rapports restent
des développements à réaliser, et non des blocages techniques déclarés.

## Vérification

Exemple fourni : exemples/heures_nanosecondes.csv ; unité s, pas 0.01,
tolérance 0, signal `signal`. Le champ vide doit garder les croix sur ses
bords connus, sans valeur de remplacement.

Cette livraison inclut aussi emplacements.py, qui choisit un dossier
utilisateur pour le relevé d'environnement (3005). Aucun package ajouté.
Les tests rapides exécutés : 129 réussis, 0 échec, 0 ignoré ; intégration :
1 réussi. Environnement d'essai Linux/Python 3.12, pas de qualification native
Windows/SLES. Les fichiers surveillés restent inchangés pendant les tests.

`tests/test_heures.py` : nanosecondes, valeurs invalides, parcours complet,
intégrité du CSV, minuit, mélange de formats et unité incompatible. Les tests
historiques restent nécessaires pour les compteurs numériques et les croix.
