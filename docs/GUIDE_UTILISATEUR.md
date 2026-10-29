# Guide d'utilisation — VISU PTBG 2.5.0

Analyseur graphique des fichiers CSV de perturbographie (PTBG) produits par les PLC
TXS Compact. Ce guide est le **fichier d'aide** de l'outil (menu Information > Fichier
d'aide, touche F1).

## 1. Démarrer

- **Windows 11 / Spyder 6** : ouvrir `MAIN.py`, appuyer sur **F5**.
- **SLES 15 SP7** : `install/lancer_sles.sh` (après `install/installer_sles.sh`).
- **Terminal** : `python MAIN.py fichier1.csv fichier2.csv` ouvre directement les fichiers.

La fenêtre comprend :

- en haut, la **barre de menus** et la **barre de chemin** (paquet > fichier > variable,
  onglet actif) avec des accès rapides ;
- à gauche, l'**arbre des données** (masquable : bouton « Masquer », bouton « Arbre » ou F9) ;
- à droite, la **zone graphique à onglets**, chaque onglet ayant son **Time Base Monitor**
  et un **panneau de lecture** des curseurs ;
- en bas, la **barre d'état** : utilisateur, date, dernier message du journal (cliquer
  pour le journal complet), version, barre d'avancement et bouton Annuler.

## 2. Ouvrir des données

**Fichier > Ouvrir des fichiers CSV…** (Ctrl+O) ou **Ouvrir un dossier de CSV…** (tous
les `.csv` du dossier et de ses sous-dossiers). La lecture se fait en arrière-plan : la
fenêtre reste utilisable et **Annuler** interrompt la lecture.

Format attendu (section 2.3 de la spécification) : CSV, séparateur virgule, UTF-8, sans
métadonnées, 1re ligne = noms des variables PLC, 1re colonne = base de temps. Un écart
est signalé dans le nœud **Diagnostic** du fichier, avec le numéro de ligne. Seul un
séparateur autre que la virgule (« ; », tabulation…) rend le fichier illisible, sans
empêcher la lecture des autres.

Un fichier abîmé est lu sans rien inventer ni perdre en silence :

| Situation | Ce que fait l'outil |
|---|---|
| ligne vide, ou « ,,,, » sans aucune valeur | ignorée, comptée (information) |
| ligne avec trop ou trop peu de champs (ligne tronquée, valeur en trop) | **rejetée et listée** avec son extrait ; jamais complétée (sa dernière valeur pourrait être coupée) ; sa place apparaît comme un trou dans la base de temps |
| guillemet non fermé, octets nuls (fichier interrompu pendant l'écriture) | seule la ligne concernée est rejetée ; un remplissage d'octets nuls en fin de fichier est signalé |
| dernière ligne sans retour à la ligne | gardée si elle est complète, avec un avertissement « vérifier cette dernière mesure » |
| préambule de métadonnées, lignes « # » | ignorés, signalés (non-conformité REQ 2303) |
| pas de ligne d'en-têtes | la 1re ligne de mesures est **conservée**, colonnes nommées Colonne_1, Colonne_2… |
| en-tête répété au milieu (fichiers mis bout à bout) | ignoré, signalé |
| virgules en fin de ligne | tolérées |
| octets non UTF-8 (fichier enregistré en Windows-1252), UTF-16 | fichier **lu**, marqué en **ERREUR** (non-conformité REQ 2302) avec la 1re ligne fautive |
| valeur « nan », « inf » | valeur absente (comme une cellule vide), comptée par variable |
| texte dans une colonne numérique, nombre ≠ 0/1 dans un Bool | non tracé, compté par variable ; le type reste modifiable |
| virgule décimale dans un fichier à virgules | fichier refusé avec l'explication, aucune fausse colonne n'est créée |

Les fichiers rejoignent le **paquet de données actif** (marqué « actif » dans l'arbre).
Pour un système de plusieurs PLC, mettre les fichiers de chaque essai dans un même paquet
(Fichier > Nouveau paquet de données pour en créer un autre ; clic droit sur un paquet >
Définir comme paquet actif).

## 3. L'arbre des données

```
Paquet de données 1 (actif)
└── plc_A.csv                 statut du fichier (vert, orange, rouge)
    ├── Base de temps : t_ms  format, période, statut de la base de temps
    ├── Groupes binaires (1)  ex. DI = DI[0..3]
    ├── Diagnostic (3)        constats de lecture, cellules vides
    └── variables…            nom, type Bool / Float / Texte, cellules vides
```

- **Double-clic** sur une variable : elle s'ajoute à l'axe actif de l'onglet.
- **Glisser-déposer** une variable sur un axe précis.
- **Clic droit** : ajouter à l'axe actif ou dans un nouvel onglet, **forcer le type**
  (Bool, Float, Texte, automatique), créer un groupe binaire avec la sélection,
  configurer la base de temps, diagnostic complet, fermer.
- **Filtrer** : saisir une partie du nom des variables.

Type automatique : `true/false` ou valeurs 0/1 (avec au moins un 0 et un 1) → Bool ;
textes d'états (« STOP », « ACTIVE ») → Texte ; sinon Float.

## 4. La base de temps et le Time Base Monitor (TBM)

La 1re colonne est convertie en secondes : compteur (ns, µs, ms, s, min, h, cycles PLC),
heure `hh:mm:ss.fraction` jusqu'à la nanoseconde (passage de minuit géré) ou date-heure.
Un compteur **négatif** correspond au **pré-déclenchement** : t = 0 est l'instant de
déclenchement (ligne pointillée « déclenchement » sur les axes).

Si l'en-tête du compteur ne précise pas son unité (colonne « index »…), l'unité de la
préférence (ms) est **supposée** : le fichier passe en **avertissement** (« unité SUPPOSÉE,
à confirmer ») et le TBM ne peut pas être masqué tant que l'unité n'est pas choisie dans
**Base de temps > Configurer…** (une case permet de l'appliquer d'un coup aux autres
fichiers dans le même cas).

Pour chaque fichier, l'outil contrôle :

| Contrôle | Signification |
|---|---|
| Valeur de la période | médiane des Δt, comparée à la période nominale si elle est saisie |
| Stabilité | part des Δt dans la tolérance, jitter, déphasages, changements de fréquence |
| Croissance continue | aucun horodatage dupliqué ni retour arrière |
| Données manquantes | trous de k périodes (k − 1 échantillons manquants) |
| Lisibilité, horodatages aberrants | horodatage illisible ; horodatage isolé à plus de 10 périodes de ses deux voisins (ex. « 00:00:00 » au milieu d'un essai à 18 h, ou « 23:59:59 » au milieu d'un essai à 0 h 10), signalé en erreur et exclu du calcul du raster, sans compter de faux passage de minuit ; il reste affiché à son instant brut (case « Masquer… » de Base de temps > Configurer pour le retirer des courbes ; seuil de 10 périodes réglable dans Outils > Préférences) |

Le **Time Base Monitor**, en bas de chaque onglet, montre pour chaque fichier affiché la
conversion appliquée, l'origine, le statut, les Δt (ou Δt / période quand les fichiers ont
des périodes différentes), la période et sa bande de tolérance, et les anomalies (▼ trou,
◆ déphasage, ✖ doublon / retour arrière, ✚ horodatage illisible, ★ horodatage aberrant,
trait mixte = changement de fréquence).

**Masquer le TBM** n'est possible que si aucune base de temps affichée n'a
d'avertissement ni d'erreur ; il réapparaît automatiquement si une alerte survient.

**Base de temps > Configurer…** (ou double-clic sur le fichier) permet d'imposer :
format, unité, **période nominale** et **tolérance** (diagnostic recalculé), **origine
absolue** (date-heure du compteur 0, ou date du jour pour un horodatage hh:mm:ss),
**décalage manuel** (aligner un PLC non synchronisé), un **affichage régularisé**
facultatif et un **diagnostic opérateur** libre, imprimé dans le TBM et le rapport.

Par défaut les courbes sont tracées sur l'**horodatage brut** du fichier : rien n'est
recalé. Le jitter qui reste dans la tolérance n'est pas compté comme anomalie, il est
mesuré et affiché (« jitter max »). L'option « Affichage régularisé » remplace l'affichage
par une droite ajustée sur le raster (les trous restent visibles, aucune mesure n'est
créée) ; le TBM indique toujours lequel des deux affichages est utilisé.

**Base de temps > Diagnostic complet** (ou double-clic sur le nœud Diagnostic) s'ouvre sur
un **bilan en une phrase** et la liste des **points à vérifier**, erreurs d'abord ; suivent
l'identité du fichier, la lecture, la base de temps (réglages, contrôles, portions à période
constante), le tableau des événements avec leur **ligne dans le CSV**, et les valeurs.
Chaque constat commence par sa gravité en couleur : [ERREUR] donnée non fiable,
[AVERTISSEMENT] à vérifier, [INFO] information, [OK] conforme. « Copier tout » et
« Enregistrer sous… » donnent le même texte.
**Base de temps > Comparer les sources** compare les PLC du paquet : recouvrement, fin de
flux décalée, fréquences, déphasage entre grilles d'échantillonnage.

**Affichage > Axe des temps absolu** place chaque fichier à son horodatage absolu
(disponible quand chaque fichier a une origine absolue).

## 5. Onglets et modèles

**Nouvel onglet** (barre rapide ou menu Affichage) propose 7 modèles : 1, 2, 3 ou 4 axes,
analogique + logique, grille 2 × 2, temporel + nuage X/Y. Les axes temporels d'un onglet
partagent le même temps : zoom et déplacement (loupe et croix de la barre d'outils)
s'appliquent à tous. Le bouton **Vue d'origine** (aussi Affichage > Vue d'origine, Ctrl+0)
réaffiche toute la durée des fichiers avec les échelles verticales automatiques et remet les
légendes déplacées à leur place ; courbes et curseurs sont conservés.

**Légendes** : glisser une légende avec la souris la déplace ; elle garde sa place après un
redessin, dans le projet et dans le rapport PDF. Un clic sur un nom de la légende
sélectionne cette courbe. Clic droit sur l'axe : masquer / afficher la légende, ou la
remettre à sa place automatique.

Fermer un onglet : croix **×** de son titre, clic molette sur le titre, clic droit sur le
titre (renommer / fermer) ou Ctrl+W. S'il n'en reste aucun, un onglet vide est recréé.

Un axe porte soit des courbes **analogiques** (Float), soit des **pistes logiques** (Bool,
Texte, groupes binaires). Une variable de l'autre famille est placée automatiquement sur
le premier axe compatible.

Barre d'outils de l'onglet : axe actif (aussi par clic sur l'axe, cadre bleu), **courbe
sélectionnée** (sa valeur est portée par les curseurs), retirer la courbe, vider l'axe.

Sur les courbes : une **croix** encadre chaque cellule vide du CSV (dernier point connu
avant, premier après) ; la courbe est **interrompue** sur un trou de la base de temps ;
aucune valeur n'est jamais inventée ni interpolée.

## 6. Curseurs

| Outil | Utilisation |
|---|---|
| Curseur vertical simple | « Curseur vertical > Curseur simple » : sur l'axe actif ; étiquette = instant + valeur de la courbe sélectionnée |
| Suivi souris | le curseur suit la souris ; le panneau de droite liste toutes les courbes de l'axe |
| Double curseur | C1 et C2 posés automatiquement ; Δt, 1/Δt et ΔV par courbe |
| Curseur global | une ligne sur tous les axes (TBM compris), déplacée ensemble |
| Curseur horizontal | sur une courbe Float sélectionnée : niveau, franchissements montants / descendants |
| Condition Bool | dans le dialogue du curseur horizontal : 1 à 3 Bool (ET / OU) ; seuls les franchissements sous condition sont retenus ; périodes vraies ombrées |
| Nuage X/Y | Outils > Nuage X/Y : Y = f(X), corrélation r, régression ; clic = désigner un point, affiché par deux curseurs ou par le seul point de croisement ; C1 / C2 reportés |

Souris : **clic** = placer le curseur ; **glisser** = le déplacer ; **Maj + clic** = niveau du
curseur horizontal ; **clic droit** = menu de l'axe. Clavier : **flèches gauche / droite** =
échantillon précédent / suivant de la courbe sélectionnée. Quand la loupe ou la croix de
la barre d'outils est active, les clics servent au zoom (la désactiver pour les curseurs).

Les valeurs lues sont celles des **échantillons réels** : le plus proche pour un Float,
l'état en cours pour un Bool. Le panneau de lecture indique l'instant de l'échantillon et
sa **ligne dans le CSV** ; « Copier » colle le tableau dans un tableur.

## 7. Traitement conditionnel

**Outils > Traitement conditionnel…** : choisir une condition Bool et des signaux
analogiques, un seuil facultatif, puis **Calculer** : nombre d'échantillons, durée, min,
max, moyenne, écart-type, nombre de périodes et durée au-dessus du seuil pendant que la
condition est vraie. Copier ou exporter en CSV.

## 8. Rapports PDF

- **Rapport > En-tête…** : nom du projet, unité / tranche, émetteur, référence.
- **Rapport automatique** (Ctrl+P) : une page de l'onglet actif.
- **Pas à pas** : **+ Page pas à pas** (Ctrl+K) capture la vue active (zoom, curseurs,
  nuage X/Y, condition) avec un commentaire ; recommencer après chaque réglage ;
  **Gérer les pages…** pour ordonner, commenter, supprimer, puis **Générer le PDF**.

Chaque page, au format des rapports de test du projet (police à chasse fixe, axes
quadrillés, légendes à droite), comporte l'en-tête — à gauche : version de l'outil,
émetteur, date, projet et unité, référence et empreinte du projet, fichiers sources et
SHA-256 ; à droite : page, nombre de fichiers, de courbes, de lectures et statut de la base
de temps —, le titre de la capture, la zone graphique avec le
**Time Base Monitor** (ou, s'il a été masqué, l'indication de conformité de la base de
temps) et le tableau des lectures de curseurs. Une dernière page de **traçabilité** reprend
empreintes complètes, diagnostics de base de temps et environnement d'exécution.

## 9. Projet

**Fichier > Enregistrer le projet** (Ctrl+S) crée un fichier `.ptbg.json` : paquets,
chemins des CSV (relatifs au projet), réglages de base de temps, types forcés, groupes,
onglets, curseurs et pages du rapport. **Ouvrir un projet** recharge le tout ; un CSV
modifié depuis l'enregistrement est signalé (empreinte différente). L'empreinte du projet
apparaît dans l'en-tête des rapports.

## 10. Information et préférences

Menu **Information** : version, historique des modifications, sources (empreinte de chaque
module, versions de Python, Tk et des bibliothèques), cette aide, journal d'activité,
traçabilité des requis. **Outils > Préférences** : taille maximale d'un CSV, tolérance par
défaut, unité supposée d'un compteur, seuil de changement de fréquence, nombre de points
affichés par courbe.

## 11. En cas de problème

| Symptôme | Cause et solution |
|---|---|
| Fichier rouge « ILLISIBLE » | voir son nœud Diagnostic : séparateur, encodage, taille maximale (Préférences) |
| TBM impossible à masquer | une base de temps affichée a un avertissement ou une erreur (voir le TBM) |
| Curseur qui ne bouge pas au clic | la loupe ou la croix de la barre d'outils est active : la désactiver |
| Axe absolu refusé | un fichier n'a pas d'origine absolue : la saisir dans Base de temps > Configurer |
| Rien ne s'affiche sous SLES à distance | se connecter avec `ssh -X` (session graphique requise) |
| Message sur une bibliothèque au démarrage | versions différentes de celles testées : voir Information > Sources et docs/DEPENDANCES.md |
| Lecture lente ou mémoire insuffisante sur de très gros fichiers | mesurer le poste avec `python tools/banc_performance.py fichier.csv` et ajuster la taille maximale (Outils > Préférences) |
