# VISU PTBG 1.0.0 — version candidate et couverture des requis

Le programme est livré sous forme de sources directement exécutables dans le
dépôt. Cette version complète les parcours réalisables décidés avec Mourad ;
elle ne constitue pas une réception de l'ensemble des requis.

## Décisions appliquées

- Le groupe binaire est un regroupement de plusieurs colonnes Bool du CSV.
- Le Bool de conditionnement doit être vrai sur la même ligne physique que
  la mesure analogique. Faux, absent et invalide sont exclus.
- Aucune référence commune entre PLC n'est disponible. Les horloges restent
  indépendantes, sans origine absolue ou déphasage fabriqué.

## Défauts et manques traités

| Requis / sujet | Constat dans la v0.9.0 | Réalisation et preuve |
|---|---|---|
| 2201, groupe binaire | Aucun regroupement de colonnes | `src/groupe_binaire.py`, bouton Groupe Bool ; pistes 0/1 distinctes, lecture de toutes les colonnes, moniteur et capture PDF. Tests de groupe v100 et parcours Tk. |
| 5402 | `Curseurs` n'écoutait que les clics | Suivi souris explicite, y compris C2 ; zoom/pan prioritaire et absence de rendu répété pour le même échantillon. Tests de mouvement et événement Motion natif Tk. |
| 5407 | Aucun filtre Bool | `definir_condition` et `placer_horizontal` : valeur analogique autorisée la plus proche de Y visé, provenance brute affichée. Tests de doublons temporels avec Bool différents et retrait de condition. |
| 5202 | Le choix du type restait global à la sélection | Choix par variable, fichier et SHA-256, affiché dans l'arbre et conservé pendant la session. Test de changement de colonne Tk. |
| 4105 | Rendu PDF synchrone sur le fil Tk | PNG figés transmis à un processus Matplotlib séparé. Annulation avant écriture de la destination et refus d'écrasement ; test de réactivité de la fenêtre pendant export. |
| Fermeture des onglets | Le test Tk révélait `invalid command name ... idle_draw` après fermeture | Rendu TkAgg différé annulé avant destruction du canevas. Les parcours de fermeture et export se terminent sans cette erreur. |
| Groupe/condition vide | Le lecteur refusait toute colonne sans mesure affichable | Permission explicite réservée à ces parcours ; aucune valeur ni croix créée lorsque toute la colonne est vide. Test dédié. |
| Traçabilité | La matrice héritée désignait une autre empreinte Word | Les 64 lignes, dont l'identifiant 2201 dupliqué, sont rapprochées du Word réellement présent. Son nom exact et son SHA-256 sont dans la matrice v100. |

## Vérifications exécutées

Environnement : Debian 13 x86-64, Python 3.12.14, Tcl/Tk 9.0.4,
Matplotlib 3.10.8 et NumPy 2.3.5. Installation des dépendances figées dans
un nouvel environnement virtuel, vérifiée avec `pip check`.

| Contrôle | Résultat |
|---|---|
| `python verifier_robustesse.py` | 154 tests réussis, 0 échec, 0 ignoré ; empreintes des sources inchangées pendant l'essai |
| `python -m unittest discover -s tests_integration -v` | 1 test de volume CSV réussi, 0 échec, 0 ignoré |
| `python -m unittest discover -s tests_gui -v`, avec DISPLAY/Xvfb | 5 parcours Tk/TkAgg réussis, 0 échec, 0 ignoré |
| Intégrité des données reçues | Les 6 CSV de `donnees/` et les 3 scripts de référence correspondent octet pour octet au ZIP reçu |

La preuve structurée est `docs/preuve_validation_v100.json`. Les tests Tk
ouvrent de vraies fenêtres et actionnent les commandes d'import, groupe,
condition, curseurs, typage, fermeture et export. Ils apportent une preuve Linux
sous Xvfb, pas une qualification Windows 11 ou SLES 15 SP7.

## Couverture des 64 lignes

`docs/MATRICE_REQUIS_V100.json` reprend chaque énoncé du Word reçu avant ses
annotations historiques, son occurrence, l'état, les preuves et le reste à faire.
Les états hérités « implémenté » ne valent pas validation métier et les tests
locaux n'établissent pas automatiquement une conformité complète.

Les limites qui empêchent d'annoncer « tous les requis validés » sont :

- **4107, 2102/2104 et 5405 entre PLC distincts** : aucune référence temporelle
  commune disponible. Pas de reconstruction d'un temps absolu ni de mesure
  de déphasage justifiable. Le curseur commun fonctionne entre panneaux du
  même CSV, dont le repère est établi.
- **2310** : la valeur « xxxMo » n'est pas renseignée. Les bornes actuelles
  restent 50 MiB par CSV et 500 000 points par tracé.
- **5500** : l'énoncé est vide dans le document ; aucun comportement inventé.
- **3000/3001/3004** : qualification Windows/SLES et versions autorisées à
  confirmer. Le code nécessite Python 3.11 minimum ; 3.12 a été exécuté ici.
  Python 3.6 n'est pas pris en charge.
- **4105, performance** : les captures et figures vivantes restent sur le fil
  Tk. L'export PDF est isolé, mais une très grosse capture peut ralentir
  momentanément la fenêtre. Volumes et DPI réels à qualifier.
- Les types explicites, fenêtres, rapports en composition et journaux de
  session restent en mémoire ; aucun fichier de projet persistant ni
  exécutable Windows/SLES n'est livré.

## Essai court sur le poste cible

1. Suivre `../../README.md` à la racine du dépôt pour installer et lancer.
2. Ouvrir un CSV réel, vérifier sa première colonne et renseigner son profil.
3. Afficher deux signaux, changer d'onglet et vérifier zoom et superposition.
4. Créer un groupe de Bool, puis vérifier une valeur vide et une invalide.
5. Sur un Float, choisir une condition Bool et vérifier les lignes autorisées.
6. Activer Suivi souris, C1/C2 puis un curseur global sur le même CSV.
7. Composer plusieurs captures, exporter le PDF, puis vérifier son en-tête,
   ses pages et chaque moniteur. Essayer aussi l'annulation d'un export.
8. Redimensionner et fermer les onglets ; contrôler la lisibilité avec le DPI
   habituel et les volumes réels, puis consigner le résultat de réception.
