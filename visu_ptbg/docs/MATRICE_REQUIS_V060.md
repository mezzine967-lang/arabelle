# Revue des requis — VISU PTBG v0.6.0

Source : `NCS00ICOMMON----ES010.docx` ; SHA-256 `16b9df5b1f443f4dfb1a601c99619d9acf7469a2e47eaddad9b993c387a1c182`.
Les 64 lignes sont conservées, dont deux occurrences de 2201. Le texte anglais ci-dessous est celui du document reçu.

**Aucun verdict de conformité globale n'est prononcé.** « Implémenté, revue ouverte » signifie que la fonction existe, pas qu'elle a été acceptée. Les tests automatisés ne couvrent pas toute la spécification. Les essais Windows des versions précédentes ne valident pas automatiquement v0.6.0.

Pour chaque ligne, exécuter la vérification, conserver sa preuve et renseigner le verdict avec Sébastien. Le JSON associé contient les mêmes champs pour un futur tableau de suivi. Le journal des tests prouve seulement les cas qui y sont effectivement exécutés ; les vérifications proposées ici ne sont pas toutes automatisées.

## Ordre de travail

1. Clarifier cible OS/Python, formats temporels, taille maximale, typage Bool/Float et origine/jitter. Continuer les contrôles indépendants en parallèle.
2. Qualifier lecture CSV, anomalies et temps propres à chaque fichier ; compléter les cas métier manquants.
3. Valider la première courbe et le moniteur sur Windows ; qualifier tôt le lancement hors Spyder et un premier empaquetage.
4. Développer timestamp absolu et analyse multi-source selon les décisions prises.
5. Ajouter types de signaux, arrangements, curseurs et vues XY avec tests liés aux requis.
6. Développer rapports PDF, puis effectuer la revue complète sur la cible avec les preuves de chaque ligne.

Les points ouverts ne doivent pas être remplacés par des hypothèses silencieuses. Les fonctions déjà développées restent révisables si une décision change.


## REQ_COMMON_KH_2100

**Énoncé :** The PLC can run at different frequencies. Preferred are 10 & 20ms, but the present tool can’t be disturbed by this aspect

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/base_temps.py ; tests/test_base_temps.py.
- **Vérification et résultat attendu :** Lire trois CSV à pas 10, 20 et 7,5 : restituer chaque pas sans imposer 10 ou 20.
- **Reste à faire :** Qualifier formats, volumes et réactivité sur cible.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2101

**Énoncé :** The PLC can consist of a system composed by several PLC

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/paquet_csv.py ; tests/test_paquet_csv.py.
- **Vérification et résultat attendu :** Charger au moins trois sources PLC : chaque fichier doit garder son identité et son bilan.
- **Reste à faire :** Analyse graphique simultanée de plusieurs PLC à développer.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2102

**Énoncé :** The PLC can be synchronized or not

- **État :** Partiel.
- **Réalisation / preuves partielles :** test_deux_fichiers_dephases_restent_independants.
- **Vérification et résultat attendu :** Charger deux sources à pas identique, décalées de 3 : aucun recalage implicite, décalage conservé.
- **Reste à faire :** Définir la comparaison temporelle entre PLC.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2103

**Énoncé :** Each PLC will produce its own package of data with its own timestamp.

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/base_temps.py ; src/signal_csv.py.
- **Vérification et résultat attendu :** Donner des timestamps distincts à deux CSV : retrouver chacun dans son diagnostic et sa courbe.
- **Reste à faire :** Qualification multi-source graphique.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2104

**Énoncé :** The collection of data from several sources can generate variation of frequencies, dephasing, or loss of data flow

- **État :** Partiel.
- **Réalisation / preuves partielles :** tests/test_base_temps.py ; tests/test_moniteur_temps.py.
- **Vérification et résultat attendu :** Injecter trou, changement de pas et déphasage : signaler les écarts sans réécrire les données.
- **Reste à faire :** Ne pas assimiler un trou à une perte certaine sans règle métier ; diagnostic inter-PLC à définir.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2105

**Énoncé :** Single or multiple files

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** src/paquet_csv.py ; tests/test_paquet_csv.py.
- **Vérification et résultat attendu :** Ouvrir un CSV, puis plusieurs : tous apparaissent ; un fichier invalide n'empêche pas les autres diagnostics.
- **Reste à faire :** Rejouer la sélection multiple sous Windows v0.6.0.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2200

**Énoncé :** Binary signal

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/_signal_draw.py ; tests/test_signal_csv.py.
- **Vérification et résultat attendu :** Tracer un signal 0/1 avec une cellule vide : conserver 0, 1 et l'absence.
- **Reste à faire :** Typage Bool explicite, rendu dédié et validation métier à faire.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2201 — occurrence 1

**Énoncé :** Analog signal type : float

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/signal_csv.py ; src/_signal_draw.py.
- **Vérification et résultat attendu :** Tracer des valeurs -2,5 / 0 / 4,75 : vérifier signes, amplitudes et timestamps.
- **Reste à faire :** Typage Float explicite et règle de tracé entre échantillons à définir.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2201 — occurrence 2

**Énoncé :** Binary group signal

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun traitement de groupe binaire.
- **Vérification et résultat attendu :** Fournir un groupe de bits connu et vérifier chaque état et l'ordre des bits affichés.
- **Reste à faire :** Définir encodage du groupe, ordre et rendu ; conserver ce second 2201 distinct.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2300

**Énoncé :** The preferred format shall be ‘csv’

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** src/diagnostic_csv.py ; tests/test_diagnostic_csv.py.
- **Vérification et résultat attendu :** Lire les CSV LIM et PID : 501 et 1001 lignes respectivement, noms et valeurs conservés.
- **Reste à faire :** Revue sur le corpus métier complet.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2301

**Énoncé :** Separator shall be a comma ‘,’

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** tests/test_robustesse_csv.py.
- **Vérification et résultat attendu :** Lire un CSV séparé par virgules contenant une virgule entre guillemets : ne pas créer de colonne supplémentaire.
- **Reste à faire :** Contrôler le profil par défaut sur les CSV métier.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2302

**Énoncé :** Text format UTF8

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** test_bom ; test_utf16_avec_bom ; lecteur UTF-8.
- **Vérification et résultat attendu :** Lire en UTF-8 des noms accentués avec/sans BOM : noms identiques sans caractère BOM ajouté.
- **Reste à faire :** Le support optionnel d'autres encodages ne remplace pas l'essai UTF-8.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2303

**Énoncé :** No additional meta data

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** test_fichier_source_non_modifie ; journaux séparés.
- **Vérification et résultat attendu :** Comparer les SHA-256 avant/après analyse, tracé et enregistrement : CSV strictement inchangés.
- **Reste à faire :** Faire confirmer le sens de « No additional meta data » ; aucun ajout dans les CSV.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2304

**Énoncé :** First column devoted to time base

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/diagnostic_csv.py ; choix explicite de colonne.
- **Vérification et résultat attendu :** Lire une première colonne temporelle au nom inhabituel : la sélectionner explicitement et vérifier son utilisation.
- **Reste à faire :** Ne pas choisir une autre colonne en silence ; politique première colonne à formaliser.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2305

**Énoncé :** Time stamp configuration:

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Énoncé limité à « Time stamp configuration: ».
- **Vérification et résultat attendu :** Faire définir les réglages attendus et leurs valeurs autorisées avec Sébastien.
- **Reste à faire :** Impossible de clôturer ce titre seul ; relier à 2306/2307.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2306

**Énoncé :** Hh:mn:s… micro, nanos…

- **État :** À développer.
- **Réalisation / preuves partielles :** Diagnostic numérique uniquement.
- **Vérification et résultat attendu :** Tester HH:MM:SS avec fractions micro/nanosecondes et franchissement de minuit : préserver ordre et précision.
- **Reste à faire :** Parseur, date de référence, fuseau et politique de passage de jour à définir.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2307

**Énoncé :** Time counter

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/diagnostic_csv.py ; tests grands entiers et petits pas.
- **Vérification et résultat attendu :** Lire un compteur régulier puis un retour à zéro : préserver les valeurs et signaler le retour.
- **Reste à faire :** Débordement du compteur, unité et conversion absolue à définir.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2308

**Énoncé :** First row devoted to column’s header

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** Tests en-tête absent, dupliqué, répété et vide.
- **Vérification et résultat attendu :** Lire un CSV valide puis sans en-tête : noms de la première ligne reconnus ou refus explicite.
- **Reste à faire :** Revue des règles de refus avec le métier.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2309

**Énoncé :** Composed by PLC’s variables names

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/diagnostic_csv.py ; tests LIM/PID.
- **Vérification et résultat attendu :** Comparer les noms du CSV et de l'arbre, accents/espaces internes inclus : aucune substitution métier.
- **Reste à faire :** Les espaces extérieurs sont normalisés : faire approuver ou adapter cette règle.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_2310

**Énoncé :** Maximal size xxxMo

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Limites de prototype, non seuils contractuels.
- **Vérification et résultat attendu :** Après fixation de xxx Mo, tester sous, à et au-dessus de la limite avec mesure mémoire/durée.
- **Reste à faire :** Fixer taille maximale, volumes et seuils de performance ; 500000 points n'est pas une valeur du requis.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3000

**Énoncé :** Final tool shall be compatible with SLES - SUSE 15 SP7: ‘SUSE Linux Enterprise Server 15SP7’ at least

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Essai Linux local non SLES ; Windows annoncé oralement.
- **Vérification et résultat attendu :** Sur SLES 15 SP7 convenu, installer/lancer/ouvrir/tracer/exporter puis archiver l'environnement et les résultats.
- **Reste à faire :** Windows 11 64 bits pressenti pour le déploiement, non confirmé ; adapter le requis écrit lors de la revue. Aucun essai SLES réalisé.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3001

**Énoncé :** Final tool shall be compatible with Python 3.6 at least

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Code ciblé Python 3.11 ; essais locaux Python 3.12.
- **Vérification et résultat attendu :** Confirmer la plage Python prise en charge, puis exécuter la suite et l'IHM sur chaque version retenue.
- **Reste à faire :** Le code actuel n'est pas compatible Python 3.6 ; 3.11 OK oralement ne prouve pas le support 3.6.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3002

**Énoncé :** MAIN.py script shall be devoted only to generate the GUI interface.

- **État :** Partiel.
- **Réalisation / preuves partielles :** MAIN.py : widgets, callbacks ; calculs dans src.
- **Vérification et résultat attendu :** Relire MAIN.py : aucun parseur CSV ni calcul temporel métier ; actions déléguées aux modules.
- **Reste à faire :** Revoir la frontière callbacks/configuration avec Sébastien.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3003

**Énoncé :** All action realized by the tool shall be best as possible externalized into a dedicated sub script or class.

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/diagnostic_csv.py, base_temps.py, paquet_csv.py, signal_csv.py, trace_signal.py.
- **Vérification et résultat attendu :** Appeler lecture, diagnostic et construction de figure sans démarrer MAIN : fonctionnement indépendant.
- **Reste à faire :** Poursuivre l'externalisation pour les futures fonctions.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3004

**Énoncé :** All additional packages or library implemented shall be documented and strictly aligned with the kernel version.

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/environnement_visu.py ; docs/DEPENDANCES.md.
- **Vérification et résultat attendu :** Archiver Python/OS/bits/Tcl/Tk et chaque version réellement chargée ; rejouer la suite et le tracé sur cible.
- **Reste à faire :** Verrouiller l'environnement cible et qualifier l'exécutable/transitives ; métadonnées seules insuffisantes.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3005

**Énoncé :** Compatibility mechanism between different OS Shall be documented.

- **État :** Partiel.
- **Réalisation / preuves partielles :** pathlib, sys.executable, tkinter ; docs/DEPENDANCES.md.
- **Vérification et résultat attendu :** Tester chemins avec espaces/accents, accès refusé et démarrage sur chaque OS retenu.
- **Reste à faire :** Documenter puis tester le packaging et les différences OS effectives, notamment SLES.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3006

**Énoncé :** Code source shall be commented

- **État :** Partiel.
- **Réalisation / preuves partielles :** Commentaires par parties, docstrings ; docs/REVUE_TEMPLATES.md.
- **Vérification et résultat attendu :** Relire chaque module avec un tiers : rôle, entrées/sorties, unités, erreurs et limites retrouvables.
- **Reste à faire :** Revue humaine de tous les modules ; ne pas compter les commentaires comme validation.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_3007

**Énoncé :** No useless function hold into the scripts

- **État :** Partiel.
- **Réalisation / preuves partielles :** Modules de production séparés des références/tests.
- **Vérification et résultat attendu :** Revoir chaque fonction de production : appel réel ou API justifiée ; éliminer code mort et imports inutiles.
- **Reste à faire :** Revue statique et métier à renouveler à chaque évolution ; ne pas intégrer les templates entiers.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4100

**Énoncé :** The present tool shall define the time raster from the source and control check:
•	Period value
•	Period stability
•	Period continuous increase

- **État :** Partiel.
- **Réalisation / preuves partielles :** tests/test_base_temps.py ; tests/test_robustesse_csv.py.
- **Vérification et résultat attendu :** Tester temps régulier, variable, doublon, retour, vide et point unique : pas/progression corrects ou non évaluables.
- **Reste à faire :** Qualifier autres formats temporels et volumes.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4101

**Énoncé :** The present tool shall be capable to find and highlight the inconsistent time base like missing data or wrong phasing

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/moniteur_temps.py ; tests doublons/retours/pas.
- **Vérification et résultat attendu :** Simulation archivée : repères aux temps 1006 et 9815 (doublons), 4986 (pas 2 ms) avec pas attendu 1 ms.
- **Reste à faire :** Déphasage inter-PLC et perte de données ne sont pas diagnostiqués automatiquement.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4102

**Énoncé :** A dedicated graphical axle shall be devoted to detail the time base conversion and status. It shall be automatically present on each graphical template and call: Time Base Monitor.

- **État :** Partiel.
- **Réalisation / preuves partielles :** src/trace_signal.py ; test_points_et_reperes_partagent_les_temps_et_le_zoom.
- **Vérification et résultat attendu :** Afficher la courbe puis zoomer : axe Time Base Monitor présent, repères aux temps source, zoom commun.
- **Reste à faire :** Un seul arrangement disponible ; étendre à tous les futurs templates et conversions.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4103

**Énoncé :** The time base monitor can be hidden by the issuer only if no warning or error.

- **État :** Partiel.
- **Réalisation / preuves partielles :** tests/test_moniteur_temps.py ; MAIN._basculer_moniteur.
- **Vérification et résultat attendu :** CSV régulier : masquage du diagnostic possible ; doublon ou valeur absente : masquage refusé.
- **Reste à faire :** Le moniteur de la courbe reste toujours visible ; essai interactif Windows v0.6.0 à faire.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4104

**Énoncé :** The Time Base Monitor shall be automatically present into all reports. If removed for arrangement and indication shall appear to confirm the good construction or Time Base.

- **État :** À développer.
- **Réalisation / preuves partielles :** Pas de rapports exportés.
- **Vérification et résultat attendu :** Exporter chaque rapport avec anomalies : moniteur présent ; retrait autorisé seulement avec confirmation prévue.
- **Reste à faire :** Développer export et règle d'indication dans les rapports.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4105

**Énoncé :** In case of disturbance in the time base analysis, the treatment can’t be locked or unstable.

- **État :** Partiel.
- **Réalisation / preuves partielles :** Tests anomalies, temps invalides et isolation des sources.
- **Vérification et résultat attendu :** Ouvrir un CSV perturbé puis un valide : diagnostic contrôlé, source inchangée, interface encore utilisable.
- **Reste à faire :** Lecture synchrone actuelle : réactivité gros fichiers et annulation à qualifier ; absence de blocage non prouvée.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4106

**Énoncé :** In case of disturbance in the time base analysis, the user can specify the normal raster with an associated diagnosis

- **État :** Partiel.
- **Réalisation / preuves partielles :** Profil pas/tolérance ; test_pas_et_tolerance_configures.
- **Vérification et résultat attendu :** Saisir pas attendu 1 et tolérance 0 sur simulation : pas 2 signalé ; reconfigurer et recalculer le bilan.
- **Reste à faire :** Valider les unités et le sens métier de la tolérance.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_4107

**Énoncé :** Constitute Absolute timestamp. Clock Jitter ignored

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Pas de construction de timestamp absolu.
- **Vérification et résultat attendu :** Définir origine commune et jitter admissible puis comparer une référence calculée à des données déphasées.
- **Reste à faire :** Aucune correction silencieuse ; politique absolu/jitter à valider avant implémentation.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5100

**Énoncé :** Top bar with main menu path

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** MAIN._construire_menu.
- **Vérification et résultat attendu :** Ouvrir la fenêtre : menu en haut, Ajouter et Enregistrer opérationnels.
- **Reste à faire :** Essai Windows v0.6.0.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5101

**Énoncé :** Specific ‘Information’ section including:
Tool version
History of changes
Sources
Help file

- **État :** Partiel.
- **Réalisation / preuves partielles :** Menu Informations ; README.
- **Vérification et résultat attendu :** Ouvrir Informations et Aide : version, historique, sources et aide accessibles et cohérents.
- **Reste à faire :** Compléter historique, références de code et véritable fichier d'aide accessible depuis le menu.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5102

**Énoncé :** Bottom bar summarizing:
User
Date
Activity log
Tool version

- **État :** Partiel.
- **Réalisation / preuves partielles :** MAIN : bandeau utilisateur/date/version et activité.
- **Vérification et résultat attendu :** Lancer, ajouter un fichier, analyser : identité/date/version correctes et activité actualisée.
- **Reste à faire :** Historique complet d'activités à développer ; une dernière action n'est pas un journal complet.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5103

**Énoncé :** Left area will contain the data tree viewer

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** MAIN._construire_contenu.
- **Vérification et résultat attendu :** Ouvrir plusieurs CSV : arbre à gauche et sélection fonctionnelle.
- **Reste à faire :** Essai Windows v0.6.0 et redimensionnement.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5104

**Énoncé :** Right area will be the main and wider section devoted to graphical analysis.

- **État :** Partiel.
- **Réalisation / preuves partielles :** MAIN ; onglet Courbe.
- **Vérification et résultat attendu :** Afficher puis redimensionner : graphique à droite plus large que l'arbre, libellés lisibles.
- **Reste à faire :** Qualifier petite résolution, mise à l'échelle Windows et données longues.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5105

**Énoncé :** Tree area can be hidden

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** MAIN._basculer_arbre.
- **Vérification et résultat attendu :** Masquer puis réafficher l'arbre : sélection et données conservées, zone droite redimensionnée.
- **Reste à faire :** Essai Windows v0.6.0.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5106

**Énoncé :** Graphical area can manage several tab to hold different arrangements

- **État :** À développer.
- **Réalisation / preuves partielles :** Diagnostic + une Courbe seulement.
- **Vérification et résultat attendu :** Créer deux arrangements graphiques, changer d'onglet : contenu et réglages distincts conservés.
- **Reste à faire :** Deux onglets dont un diagnostic ne satisfont pas plusieurs arrangements graphiques.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5200

**Énoncé :** Top Tree level correspond to the data package

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** MAIN._actualiser_arbre ; src/paquet_csv.py.
- **Vérification et résultat attendu :** Ajouter deux fichiers : une racine Paquet CSV les rassemble.
- **Reste à faire :** Revue Windows.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5201

**Énoncé :** First Child level will be devoted to the csv file… from one source or several.

- **État :** Implémenté, revue ouverte.
- **Réalisation / preuves partielles :** MAIN._actualiser_arbre ; tests/test_paquet_csv.py.
- **Vérification et résultat attendu :** Sous la racine, retrouver chaque CSV et son chemin sans confusion de noms.
- **Reste à faire :** Revue Windows avec deux noms identiques dans des dossiers différents.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5202

**Énoncé :** Into each csv file, the tree shall detail all the variables contained with associated type Bool or Float.

- **État :** Partiel.
- **Réalisation / preuves partielles :** Arbre de colonnes ; types indicatifs du lecteur.
- **Vérification et résultat attendu :** Déplier un CSV à booléens et flottants : chaque variable doit avoir le type métier validé.
- **Reste à faire :** Types actuels numérique/texte ne constituent pas encore Bool/Float ; schéma explicite nécessaire.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5203

**Énoncé :** Into each csv file, the tree shall detail the dedicated time base

- **État :** Partiel.
- **Réalisation / preuves partielles :** Arbre et profil temporel par source.
- **Vérification et résultat attendu :** Déplier chaque fichier : retrouver sa base de temps ; changer le profil et vérifier l'actualisation.
- **Reste à faire :** Valider le comportement pour colonne ambiguë et timestamp absolu.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5300

**Énoncé :** Several templates shall be proposed including different arrangement of Axle

- **État :** À développer.
- **Réalisation / preuves partielles :** Un seul arrangement signal + moniteur.
- **Vérification et résultat attendu :** Choisir plusieurs templates : axes et moniteurs corrects, données préservées lors du changement.
- **Reste à faire :** Définir puis développer les arrangements.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5400

**Énoncé :** Vertical single Cursor: can be activated by axle

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun curseur métier.
- **Vérification et résultat attendu :** Activer un curseur sur un axe choisi : un seul axe concerné, désactivation possible.
- **Reste à faire :** Curseurs à développer après règles temporelles.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5401

**Énoncé :** Vertical single Cursor: hold time stamp value and cross value of selected curve

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun curseur métier.
- **Vérification et résultat attendu :** Placer le curseur sur un échantillon connu : timestamp et valeur de la courbe sélectionnée exacts.
- **Reste à faire :** Définir lecture entre échantillons et aux temps doublonnés.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5402

**Énoncé :** Vertical single Cursor: tracking reading mode adding the list of crossed value from all the axle’s curves into a right popup

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun popup de suivi.
- **Vérification et résultat attendu :** Sur axe multitraces, déplacer le curseur : liste à droite avec chaque valeur et absence explicite.
- **Reste à faire :** Définir lecture aux bases de temps différentes.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5403

**Énoncé :** Double Vertical Cursor: Time stamp is mandatory and automated for each cursor

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun double curseur.
- **Vérification et résultat attendu :** Activer deux curseurs : chacun affiche automatiquement son timestamp et se déplace indépendamment.
- **Reste à faire :** Implémentation et règle sur temps absents à faire.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5404

**Énoncé :** Double Vertical Cursor: Time stamp is mandatory and automated for each cursor

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Texte identique à 5403 dans la source.
- **Vérification et résultat attendu :** Faire confirmer la distinction, puis appliquer un essai séparé ou un lien explicite vers 5403.
- **Reste à faire :** Ne pas supprimer ce requis comme doublon sans décision.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5405

**Énoncé :** Global cursor = global synchronization of axles. Cursor appear over all axles and moving in same time

- **État :** À développer.
- **Réalisation / preuves partielles :** Zoom partagé signal/moniteur seulement.
- **Vérification et résultat attendu :** Déplacer le curseur global sur plusieurs axes : tous restent au même instant selon le référentiel défini.
- **Reste à faire :** Zoom commun ne vaut pas curseur global ; définir référence temporelle.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5406

**Énoncé :** Horizontal cursor: only applicable to analog signals

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun curseur horizontal.
- **Vérification et résultat attendu :** Activer sur Float puis Bool : autorisé seulement pour Float.
- **Reste à faire :** Dépend du typage métier.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5407

**Énoncé :** Horizontal cursor: can be conditioned by additional bool signal to realize conditional processing.

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun traitement conditionnel.
- **Vérification et résultat attendu :** Appliquer un masque Bool connu : seules les périodes autorisées participent au traitement horizontal.
- **Reste à faire :** Définir absence de valeur Bool et alignement des temps.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5408

**Énoncé :** Cursor X/Y: used for correlation control check - Two cursors are activated or the cross point only can be highlighted

- **État :** À développer.
- **Réalisation / preuves partielles :** Pas de vue XY.
- **Vérification et résultat attendu :** Utiliser deux séries de référence : vérifier les couples XY et le point ou les deux curseurs.
- **Reste à faire :** Définir appariement temporel avant corrélation.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_5500

**Énoncé :** [vide dans le document]

- **État :** À clarifier.
- **Réalisation / preuves partielles :** Énoncé vide dans le document.
- **Vérification et résultat attendu :** Faire compléter ou retirer formellement la ligne avant de définir un essai.
- **Reste à faire :** Aucun critère ne peut être inventé.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6000

**Énoncé :** The present tool shall be capable to generate a pdf report.

- **État :** À développer.
- **Réalisation / preuves partielles :** Pas d'export PDF.
- **Vérification et résultat attendu :** Générer un PDF, l'ouvrir dans un lecteur indépendant et vérifier texte/graphiques.
- **Reste à faire :** Choix bibliothèque PDF et qualification dépendances à faire.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6001

**Énoncé :** Report consist into a template containing Header and graphical area

- **État :** À développer.
- **Réalisation / preuves partielles :** Pas de template de rapport.
- **Vérification et résultat attendu :** Ouvrir un PDF produit : en-tête et zone graphique présents, sans coupure.
- **Reste à faire :** Développer mise en page.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6002

**Énoncé :** Report, can be generated automatically or step by step.

- **État :** À développer.
- **Réalisation / preuves partielles :** Aucun mode de rapport.
- **Vérification et résultat attendu :** Exécuter automatique puis pas-à-pas sur mêmes données : chaque mode produit le contenu demandé.
- **Reste à faire :** Deux parcours à développer et tester séparément.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6003

**Énoncé :** Automatic Report consist into a single edition of active graphical area to pdf file

- **État :** À développer.
- **Réalisation / preuves partielles :** Export barre Matplotlib désactivé.
- **Vérification et résultat attendu :** Sur vue active choisie, générer PDF : seule cette vue, axes et moniteur inclus.
- **Reste à faire :** Ne pas assimiler une sauvegarde PNG de Matplotlib au rapport requis.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6004

**Énoncé :** Manual step by step report generation consist into a sequential generation on order depending of graphical active tab. Permitting to push global view, and customize analysis, cursor, X/Y cloud…

- **État :** À développer.
- **Réalisation / preuves partielles :** Pas de composition séquentielle.
- **Vérification et résultat attendu :** Ajouter vue globale puis zoom avec curseur puis XY : vérifier ordre et réglages de chaque page.
- **Reste à faire :** Gestion de captures et assemblage PDF à développer.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.


## REQ_COMMON_KH_6005

**Énoncé :** Header shall contain following details:
Tool Version
Issuer
Date
Source File(s)
Project Name & Unit
Project file reference or Hash

- **État :** À développer.
- **Réalisation / preuves partielles :** Version/hash déjà dans journaux, pas rapport.
- **Vérification et résultat attendu :** Lire chaque en-tête PDF : version, émetteur, date, sources, projet/unité et référence ou hash présents et exacts.
- **Reste à faire :** Formulaire métadonnées et rendu à développer.
- **Revue Sébastien :** non prononcée ; date, environnement, résultat, preuve et visa à renseigner.
