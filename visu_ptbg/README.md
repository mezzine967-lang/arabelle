# VISU PTBG — v1.0.0, version candidate

Le programme est désormais disponible directement dans le dépôt, sans devoir
extraire l'archive. Le guide courant est `../README.md` ; le bilan de couverture
est `docs/VALIDATION_V100.md`. Les sections v0.9.0 et antérieures ci-dessous
restent un historique et ne constituent pas les instructions de cette version.

Ajouts : groupe de plusieurs colonnes Bool, suivi continu du curseur,
lecture horizontale conditionnée par un Bool vrai sur la même ligne, typage
explicite par variable et export PDF dans un processus séparé.
Les essais Tkinter Linux utilisent maintenant un écran virtuel ; les essais
Windows/SLES et les fonctionnalités dépendant d'une référence commune entre
PLC restent distincts. Voir la matrice v100 pour chaque limite.

## Historique v0.9.0

Présentation actualisée : la courbe s'ouvre en premier, le fichier sélectionné
est indiqué au-dessus de ses réglages temporels, et les commandes graphiques
sont réparties sur deux lignes pour faciliter la lecture sur un petit écran.

## Nouveaux parcours

Cette version développe les requis suffisamment définis, sans recalage des PLC.
Les explications historiques ci-dessous restent datées de leur version.
L'état courant des 64 lignes de requis est dans **docs/AVANCEMENT_V090.md**.
Les questions à Sébastien sont dans **docs/QUESTIONS_SEBASTIEN_V090.md**.

1. Extraire entièrement le ZIP dans un nouveau dossier. Dans Spyder, redémarrer
   le noyau, ouvrir ce nouveau `MAIN.py`, puis F5. Le titre affiche **0.9.0**.
2. Ajouter des CSV : lecture, profil et préparation des signaux se font en
   arrière-plan. La barre d'activité indique le fichier traité. Annuler écarte
   le résultat ; la lecture en cours finit proprement avant une nouvelle tâche.
3. Dans Courbe, choisir un modèle (un panneau, deux côte à côte ou superposés),
   puis Nouvel onglet. Afficher ajoute un panneau ; un modèle plein ouvre un
   nouvel onglet. Les vues restent présentes quand la sélection de fichier change.
   Les ascenseurs permettent d'atteindre les graphiques sur un petit écran.
4. Superposer ajoute un autre signal du **même CSV** au dernier panneau actif.
   Même type Bool/Float et même profil requis. Chaque panneau conserve ses
   données et son profil au moment de sa création. Une nouvelle analyse du CSV
   ne réécrit pas les vues ouvertes : fermer/recréer une vue pour l'actualiser.
5. Auto reconnaît `true/false` comme Bool ; les nombres restent Float. Pour un
   signal binaire codé 0/1, choisir explicitement Bool. Les autres valeurs sont
   invalides. Aucun codage de ACTIVE/STANDBY/FAILED n'est supposé. Le Bool montre
   les états mesurés par des points ; aucun maintien entre mesures n'est inventé.
6. Choisir Vertical, Double vertical (boutons C1/C2) ou Horizontal pour un Float,
   puis cliquer dans le graphique. Désactiver le zoom/pan Matplotlib auparavant.
   La lecture donne le point enregistré le plus proche, sa ligne et son texte brut.
   Un champ vide reste ABSENT. Les doublons sont tous listés (20 montrés au plus).
   Lectures ouvre le panneau à droite. Aucun curseur ne crée de croix de perte.
7. Curseur global relie les panneaux temporels de l'onglet s'ils ont le même CSV,
   le même hash et la même unité. Il ne synchronise pas les horloges de PLC distincts.
   Changer le mode de curseur d'un panneau retire sa fonction d'émission globale.
8. Créer un nuage X/Y : sélectionner deux signaux Float du même CSV. Seuls les
   couples valides présents sur la même ligne sont dessinés. Cliquer sur un point
   donne les lignes concernées. Le moniteur conserve un axe temporel indépendant.
9. Menu Rapport : exporter l'onglet actif, ou ajouter successivement plusieurs
   vues/zooms au rapport manuel puis l'exporter. Chaque ajout fige la vue. Fournir
   émetteur, projet et unité d'installation ; référence facultative, SHA-256 des
   sources toujours présent. Les PDF existants ne sont jamais écrasés.
   Le moniteur apparaît toujours dans le PDF, même s'il était masqué à l'écran.
10. Informations ouvre l'aide, les packages et l'état des requis. Le bouton du
    bas ouvre le journal horodaté de la session (conservé en mémoire uniquement).

**Voir un résultat sans lancer la VISU :** ouvrir
`exemples/Rapport_demonstration_v090.pdf` (trois pages : croix, vue+zoom, X/Y).
Ce rapport utilise des données de simulation, pas une qualification de la perturbo.

**Tests :** `python verifier_robustesse.py` puis séparément
`python -m unittest discover -s tests_integration -v`.
Le premier lanceur utilise un résultat structuré, surveille aussi les fichiers
Python racine et calcule les SHA-256 par blocs. Un test ignoré donne un résultat
partiel et un code de sortie non nul. Le délai de 60 s concerne les tests rapides.

**Limites :** pas d'essai Tkinter natif dans l'environnement de développement
sans écran ; qualification Windows 11 x64 et SLES 15 SP7 encore nécessaire.
Le rendu des figures et du PDF utilise toujours le fil graphique : une très
grosse vue ou beaucoup de pages peut ralentir la fenêtre. Les limites mémoire
des CSV et du nombre de points restent celles du prototype (50 MiB / 500 000).
Les vues, captures de rapport et journal de session restent en mémoire : fermer
les vues inutiles / vider la composition après export. Aucun exécutable construit.

## Historique v0.8.0

## Heures avec fractions — requis 2306

Les relevés automatiques de dépendances sont maintenant écrits dans le dossier
utilisateur : Windows `%LOCALAPPDATA%/VISU_PTBG/resultats`, Linux
`$XDG_STATE_HOME/VISU_PTBG/resultats` ou `~/.local/state/VISU_PTBG/resultats`.
Le chemin réel est affiché dans la console. Les lanceurs de tests/démonstration
conservent leurs journaux de développement dans le projet.

La première colonne accepte maintenant HH:MM:SS ou HH:MM:SS.fraction, de 1 à
9 chiffres après le point. L'unité du profil est `s` (ou laissée vide) ; pas et
tolérance sont alors en secondes. Exemple : pas `0.01` pour 10 ms.
Le tableau conserve les heures brutes. Le graphique utilise des secondes depuis
minuit, explicitement indiquées sur son axe. Aucun jour suivant n'est supposé :
23:59:59 puis 00:00:00 reste un retour à examiner. Date et fuseau non définis.
Les compteurs numériques restent inchangés ; un mélange heures/compteurs est
refusé. Six tests supplémentaires couvrent cette évolution (126 tests rapides).
Voir `docs/HEURES_V080.md` et `docs/DEPENDANCES.md`.

## Requis 4103 : masquage du Time Base Monitor sur la courbe

Le bouton au-dessus de la figure permet de masquer ou réafficher le moniteur
quand le diagnostic l'autorise. Il est désactivé en présence d'un avertissement,
d'une erreur ou d'un état temporel non concluant. Lorsque le moniteur est
masqué, l'axe temporel reste indiqué sur la courbe ; les données restent intactes.
Voir `docs/MASQUAGE_MONITEUR_V079.md`. Le moteur et les calculs sont inchangés.

## Nouveauté : lisibilité du Time Base Monitor (requis 4102)

Les points réguliers sont plus fins ; les anomalies utilisent des symboles
distincts, avec une marge verticale pour voir les doublons à Δt=0. Le résumé
affiche le raster saisi/estimé, sa tolérance et les nombres d'intervalles par
catégorie sur le fichier entier (pas seulement la zone zoomée).
Les calculs, seuils, données et croix restent identiques à la v0.7.7.
Voir `docs/LISIBILITE_V078.md` et l'aperçu dans `exemples/Time_Base_Monitor_lisible_v078.png`.

**Bibliothèques/packages :** registre dans [docs/DEPENDANCES.md](docs/DEPENDANCES.md).
Les versions observées pendant cette livraison sont dans
`docs/environnement_linux_v078.json` ; elles ne sont pas une liste d'installation
validée pour Windows/SLES. Aucune dépendance ajoutée.

La v0.7.7 affiche dans le **Time Base Monitor** les catégories déjà calculées
par le moteur : jitter, trou probable et changement de fréquence probable.
Le graphique ne réduit plus tous ces cas au libellé général « hors tolérance ».
Le champ de l'interface devient « Tolérance du pas » : il s'agit de l'écart
maximal accepté autour du raster, et non d'une mesure de jitter. Voir
`docs/LOT2B_QUALIFICATION_MONITEUR_V077.md`.

La v0.7.6 transforme l'axe présent sous la courbe en **Time Base Monitor
quantitatif** : chaque point montre un `Δt`, avec raster, tolérance et
anomalies sur la même base X que le signal. Voir
`docs/LOT2B_MONITEUR_QUANTITATIF_V076.md`.

La v0.7.5 ajoute le moteur du Lot 2A : raster configuré ou estimé, jitter,
doublons, retours arrière, trous probables, changements de fréquence probables,
timestamps invalides et statut complet/partiel. Aucun échantillon n'est créé.
Voir `docs/LOT2A_BASE_TEMPS_V075.md`.

La v0.7.4 applique le requis 2304 : **la première colonne est toujours la base
de temps**, quel que soit son nom. L'interface l'affiche en lecture seule et ne
cherche aucune autre colonne temporelle. Voir `docs/PREMIERE_COLONNE_V074.md`.

La v0.7.3 place les croix **sur les mesures réelles qui encadrent des cellules
vides du signal dans le CSV** : dernier point avant, premier point après,
et aucun trait à travers le manque. Un saut de temps seul ne produit pas de
croix. Voir `docs/CROIX_V073.md` pour la règle, les essais et le diff expliqué.

La v0.7.0 en cours ajoutait l'inspection détaillée des temps et les croix de
valeurs absentes, à la demande de Mourad. La v0.7.1 complète l'import CSV et
la détection temporelle après revue des remarques Copilot. Aucune nouvelle
bibliothèque n'est requise. Voir `docs/REVUE_COPILOT_LOT1.md`.
La v0.7.2 sécurise la lecture d'un CSV qui change pendant l'analyse et corrige
le compte des intervalles non calculables lorsque tous les temps sont invalides.
Voir `docs/STABILISATION_V072.md` pour la revue et les différences.

## Premier essai sur le poste Windows

1. Extraire entièrement le ZIP dans un nouveau dossier, par exemple `VISU_V080`.
   Conserver l'ancien dossier et ses journaux.
2. Dans Spyder, ouvrir `visu_ptbg/verifier_robustesse.py`, puis F5. Attendu :
   **129 tests rapides**, aucun test ignoré, réussite et sources inchangées à `True`.
3. Redémarrer le noyau Spyder pour décharger les anciens modules, puis ouvrir
   le **nouveau** `MAIN.py` et F5. Le titre doit indiquer **0.8.0**.
4. Ajouter `donnees/simulation10_execution1.csv`. La première colonne `t_ms`
   est affichée automatiquement. Renseigner `ms`, pas attendu `1`, tolérance
   `0`, puis **Analyser ce fichier**.
5. **Courbe → source → Afficher le signal** : le moniteur sous la courbe
   affiche le raster saisi à **1 ms**, les deux doublons à **Δt = 0** et le
   pas de **2 ms** vers **4986 ms**. Le zoom est commun aux deux axes.
   Choisir ensuite **pub_output → Afficher le signal** : les 16 cellules vides au
   début ne sont pas tracées. Une seule croix orange se trouve sur le premier
   point disponible, **(16 ms, 0)**. Zoomer autour de **0 à 35 ms**.
   Il n'y a pas de point connu avant le manque, donc pas de deuxième croix.
   Les vrais zéros restent des mesures ; aucune valeur de remplacement.
6. **Base de temps → Examiner les intervalles** : vérifier les trois lignes
   détaillées ci-dessous. Décocher le filtre pour parcourir tous les intervalles
   par pages de 200.
7. Cliquer sur **Graphique des écarts…**. L'axe X est le numéro de ligne CSV,
   et l'axe Y représente Δt. Choisir une anomalie dans le tableau centre ce
   graphique autour de la ligne concernée ; Home rétablit la vue complète.
8. Pour importer un répertoire complet, cliquer sur **Ajouter un dossier CSV…** :
   `.csv`, `.CSV` et les variantes de casse sont détectés dans les sous-dossiers.
   Chaque fichier conserve son propre diagnostic ; une erreur locale reste dans
   son nœud et n'interrompt pas les autres.

L'essai de volume est séparé : `python -m unittest discover -s tests_integration -v`.
Il génère un grand CSV temporaire ; le lanceur rapide garde son délai de 60 s.

Les nouveaux parcours doivent encore être essayés sur Windows. Les tests locaux
incluent des rendus Matplotlib Agg, sans fenêtre native.

## Voir les deux croix comme sur le dessin de Mourad

Ajouter `exemples/exemple_synthetique_croix.csv`, choisir `t_ms`, unité `ms`,
pas attendu `10`, tolérance `0`, puis **Analyser ce fichier** et afficher
le signal `signal`. Ce petit CSV créé pour l'essai contient réellement
22 cellules vides, entre 550 et 760 ms inclus. Attendu : une croix sur
**(540 ms, 70,57)**, une autre sur **(770 ms, 18,81)**, un vide entre les deux.
L'image `exemples/Croix_sur_la_courbe_v073.png` montre le résultat du moteur.
Cet exemple est synthétique ; ce n'est pas une capture d'une perte sur un PLC.

## Ce que montrent les nouveaux repères

| Repère | Signification |
|---|---|
| Croix orange SUR la courbe | Mesure réelle à la limite d'un bloc contenant des cellules vides du signal choisi |
| Interruption sans croix | Valeur invalide, ligne rejetée ou rupture temporelle ; pas de perte affirmée automatiquement |
| Bande violette sur la courbe | Intervalle positif hors du pas et de la tolérance saisis ; perte non prouvée |
| Repère orange du Time Base Monitor | Temps dupliqué, distinct d'une cellule vide du signal |
| Repère rouge du Time Base Monitor | Retour en arrière du temps |

Les croix utilisent les coordonnées X et Y des mesures réellement présentes.
Il n'y a aucune bande séparée de croix. Une valeur invalide isolée ou un simple
écart temporel ne déclenche pas de croix. Une cellule vide dans une autre
colonne ne marque pas le signal affiché. Les champs contenant seulement des
espaces sont considérés comme vides. Si tout le signal est vide, le programme
explique qu'aucun point n'est affichable ; il n'invente pas de bord.
Une ligne entière rejetée coupe le trait, sans croix. Un temps illisible
empêche ce tracé de signal ; consulter le diagnostic et le tableau temporel.

## Résultat de référence : simulation10_execution1.csv

Avec `t_ms`, `ms`, pas `1`, tolérance `0` : 10001 mesures, 10000 intervalles,
9997 pas de 1 ms, deux pas nuls et un pas de 2 ms.

| Lignes physiques CSV | Temps avant → après (ms) | Δt (ms) | Constat |
|---|---|---:|---|
| 1008 → 1009 | 1006 → 1006 | 0 | Temps dupliqué |
| 4987 → 4988 | 4984 → 4986 | 2 | Trou probable ; perte non prouvée |
| 9817 → 9818 | 9815 → 9815 | 0 | Temps dupliqué |

Ces anomalies sont celles du fichier de simulation archivé. Elles ne sont pas
des preuves de pertes sur la perturbo. Le fichier source reste inchangé.

## Règles à retenir

- Δt = temps après − temps avant, calculé en décimal exact.
- Saisir `ms` ou `s` décrit l'unité native : cela ne convertit pas les nombres.
- Le pas attendu et la tolérance sont exprimés dans cette même unité.
- La tolérance est l'écart maximal accepté autour du pas attendu. Elle sert à
  qualifier le jitter mais n'est pas elle-même le jitter mesuré. Elle ne
  corrige pas les temps ; doublons et retours arrière restent signalés.
- Sans profil, un pas positif est seulement observé ; ce n'est pas une conformité métier.
- Les temps bruts, l'ordre et les lignes sont conservés. La nouvelle inspection
  ne calcule pas un intervalle à travers un rejet ou un temps invalide.
- Un CSV changé depuis le diagnostic doit être analysé à nouveau.
- La première colonne est le temps selon le requis 2304. Son nom n'est pas
  utilisé pour chercher une autre horloge dans le fichier.
- Un profil temporel modifié doit aussi être appliqué avant de tracer.
- Les segments relient seulement des mesures connues et consécutives. Les
  cellules non traçables, lignes rejetées, doublons, retours et pas hors
  tolérance interrompent ces segments. Aucun point intermédiaire n'est créé.
- Sans pas saisi ni pas régulier observé, le rendu conserve des points seuls.

## Limites et travail restant

Les origines du temps, le pré-déclenchement, le temps absolu, la politique de
jitter et l'alignement entre sources restent à définir et à implémenter.
Aucun recalage, rééchantillonnage ou comblement des absences n'est réalisé.

Une seule courbe de signal reste disponible. Les types
Bool/Float explicites, groupes binaires, arrangements, curseurs, rapports et
exécutable restent à compléter ou qualifier. L'inspection est bornée à 500000
lignes (limite de prototype). La lecture demeure synchrone ; performances et
réactivité sur gros fichiers restent à qualifier.

Développement visé : Python 3.11, Windows 64 bits. Les preuves locales concernent
Python 3.12/Linux ; elles ne remplacent pas les essais sur le poste de Mourad.
La cible de livraison est double : Windows et SUSE Linux Enterprise Server
15 SP7. Chaque cible devra être testée et empaquetée dans son propre
environnement. Le plan Excel n'est pas modifié par cette livraison ; aucun
requis n'est déclaré globalement validé.

## Organisation et preuves

- `MAIN.py` : interface et appels aux traitements.
- `src/inspection_temps.py` : calcul exact, ruptures et provenance.
- `src/decouverte_csv.py` : recherche récursive des CSV d'un dossier.
- `src/diagnostic_csv.py` : lecture des octets et des lignes physiques en flux,
  première colonne temporelle et statistiques locales partielles.
- `src/analyse_temps.py` : diagnostic Lot 2A des intervalles et du raster.
- `src/regles_temps.py` : seuils techniques centralisés et documentés.
- `src/vue_temps.py` : tableau paginé et navigation.
- `src/trace_temps.py` : graphique des Δt dans l'ordre des lignes CSV.
- `src/signal_csv.py`, `src/trace_signal.py` : signal et croix.
- `src/version_visu.py` : source unique du numéro de version.
- `tests/test_inspection_temps.py`, `tests/test_signal_csv.py` : cas temporels et rendu.
- `tests/test_coupures_signal.py` : bords réels, interruptions et absence de fausses croix.
- `docs/BASE_TEMPS_V070.md` : périmètre, essais et revue partielle des requis.
- `docs/REVUE_COPILOT_LOT1.md` : jugement des remarques et diff du lot 1.
- `AGENTS.md` : règles de travail et de lisibilité du code.
- `MISSION_CODEX.md` : étape actuelle des croix et mission précédente conservée.
- `docs/REPRENDRE_LE_CODE.md` : parcours de lecture et points de modification pour Sébastien.
- `docs/CROIX_V073.md`, `docs/DIFF_V072_V073.patch` : changements de cette étape.
- `docs/PREMIERE_COLONNE_V074.md` : application ciblée du requis 2304.
- `docs/LOT2A_BASE_TEMPS_V075.md` : règles et limites du moteur temporel.
- `docs/LOT2B_MONITEUR_QUANTITATIF_V076.md` : axe Δt, raster et limites du Lot 2B.
- `docs/LOT2B_QUALIFICATION_MONITEUR_V077.md` : catégories détaillées du moniteur et sens de la tolérance.
- `docs/preuve_tests_linux_v077.json` : bilan des 118 tests rapides et de l'essai d'intégration.
- `docs/DIFF_V076_V077.patch` : changements complets depuis la v0.7.6.
- `exemples/Time_Base_Monitor_categories_v077.png` : rendu synthétique des nouvelles catégories.
- `docs/CIBLE_WINDOWS_11.md` : cible Python 3.11 64 bits et qualification des paquets.
- `docs/preuve_tests_linux_v076.json` : bilan structuré et intégrité de cette version.
- `docs/DIFF_V075_V076.patch` : différences du code et de la documentation.
- `docs/preuve_tests_linux_v075.json` : preuve historique du moteur Lot 2A.
- `docs/preuve_tests_linux_v074.json` : preuve historique de la première colonne temporelle.
- `docs/preuve_tests_linux_v073.json` : preuve historique des croix de perte de données.
- `docs/preuve_tests_linux_v072.json` : preuve historique de la stabilisation.
- `docs/preuve_tests_linux_v071.json` : essai local de la suite rapide.
- `docs/DEPENDANCES.md` : bibliothèques et limites de qualification.
- `docs/MATRICE_REQUIS_V060.*` : état historique de la revue v0.6.0.
- `docs/README_HISTORIQUE_V060.md` : ancien mode d'emploi archivé.

Les scripts de simulation de Sébastien et les CSV sont conservés à l'identique.
Les anciens documents versionnés sont des preuves historiques, pas les
instructions de lancement de cette version.
