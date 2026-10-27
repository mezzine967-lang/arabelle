# Arabelle — VISU PTBG 1.0.0

Application de diagnostic et de visualisation des CSV de PLC. Les sources
modifiables sont dans `visu_ptbg/`. L'archive et le document Word reçus restent
conservés comme références ; il n'est plus nécessaire d'extraire le ZIP.

## Installer et démarrer

Installer Python **3.11 ou 3.12** avec Tkinter. Sous Windows, inclure Tcl/Tk
dans l'installation Python ; sous Linux, installer le module Tkinter de
l'interpréteur utilisé. Aucun compte ni service distant requis.

Dans un terminal ouvert dans le dossier du dépôt :

```sh
python -m venv .venv
```

Activer l'environnement : `.venv\Scripts\activate` sous Windows,
ou `source .venv/bin/activate` sous Linux. Puis :

```sh
python -m pip install -r requirements.txt
python lancer.py
```

Dans Spyder, choisir ce même interpréteur et exécuter `visu_ptbg/MAIN.py`.
Sous Linux, une session graphique est nécessaire pour ouvrir la fenêtre.
Les versions figées sont celles du développement Linux ; la qualification
sur Windows 11 et SLES 15 SP7 reste distincte.

## Utiliser

1. Ajouter un CSV, plusieurs fichiers ou un dossier. La première colonne est
   toujours la base de temps. Chaque CSV conserve son profil et son diagnostic.
2. Renseigner l'unité native, le pas attendu et la tolérance, puis **Analyser
   ce fichier**. Ces réglages ne convertissent ni ne corrigent les timestamps.
3. Dans **Courbe**, choisir la variable et son type. Auto conserve les nombres
   comme Float ; pour un Bool 0/1, choisir explicitement Bool. Le choix est
   mémorisé par colonne et contenu du CSV pendant la session.
4. Afficher, superposer des signaux du même type et du même CSV, ou créer
   plusieurs onglets avec les modèles à un ou deux panneaux.
5. **Groupe Bool…** réunit 2 à 8 colonnes sur des pistes séparées, chacune
   étiquetée 0/1. Les points sont mesurés ; aucun maintien d'état n'est supposé.
6. Activer un curseur et **Suivi souris** pour lire au déplacement.
   C1/C2 donnent deux lectures indépendantes. Le curseur global relie les
   panneaux du même CSV. Désactiver le zoom/pan avant de lire les curseurs.
7. Sur un panneau Float, **Condition Bool…** choisit une colonne du même CSV.
   Un clic horizontal lit la valeur analogique autorisée la plus proche de
   l'ordonnée visée, uniquement si le Bool est vrai sur la **même ligne**.
   Les Bool absents/invalides et valeurs analogiques absentes sont exclus.
   Les doublons temporels ne fusionnent pas les lignes. **Retirer la condition
   Bool** rétablit la lecture sans filtre. Aucun échantillon n'est interpolé.
8. **Nuage X/Y…** affiche les couples valides de deux colonnes sur la même ligne.
9. Le menu **Rapport** exporte l'onglet actif ou compose des captures successives.
   Le Time Base Monitor figure dans le PDF même masqué à l'écran.
   Le rendu PDF utilise un processus séparé ; **Annuler le calcul** écarte
   le résultat avant publication. Les fichiers existants sont préservés.

Les croix orange restent réservées aux mesures encadrant des cellules
vides du signal : jamais un simple saut de temps ni une valeur invalide.

## Vérifier

Depuis `visu_ptbg/`, avec le même interpréteur :

```sh
python verifier_robustesse.py
python -m unittest discover -s tests_integration -v
python -m unittest discover -s tests_gui -v
```

La dernière suite exige un écran (ou Xvfb sous Linux). Elle ouvre de vraies
fenêtres Tkinter et teste les commandes de l'interface. Elle ne remplace pas
la réception humaine sur les systèmes cibles. Les deux premières suites
fonctionnent sans écran. En cloud, utiliser des dossiers accessibles en écriture
pour `MPLCONFIGDIR` et `XDG_STATE_HOME` si nécessaire.

## Couverture et limites

Le bilan actuel et les preuves sont dans
[docs/VALIDATION_V100.md](visu_ptbg/docs/VALIDATION_V100.md) et la
[matrice des 64 requis](visu_ptbg/docs/MATRICE_REQUIS_V100.json).

Sans référence commune entre PLC, le logiciel ne fabrique pas de temps absolu,
de recalage ou de déphasage inter-PLC. Les horloges restent indépendantes.
Le requis 5500 est vide ; le maximum « xxxMo » n'est pas défini.
Les garde-fous sont 50 MiB par CSV et 500 000 points graphiques.
Python 3.6 n'est pas pris en charge. Aucun exécutable Windows/SLES n'est livré.
Les captures et préparations de figures restent dans le fil graphique Tk ;
un rendu très volumineux peut encore ralentir la fenêtre.
