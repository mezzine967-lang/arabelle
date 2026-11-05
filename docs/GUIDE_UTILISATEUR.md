# Guide d'utilisation — VISU PTBG 1.1.0

Analyseur graphique des fichiers CSV de perturbographie (PTBG) produits par les PLC
TXS Compact. Ce guide est le **fichier d'aide** de l'outil (menu Information > Fichier
d'aide, touche F1).

| § | Sujet | On y trouve |
|---|---|---|
| 1 | Démarrer | lancement, zones de la fenêtre |
| 2 | Ouvrir des données | format attendu, fichiers abîmés, paquets de données |
| 3 | L'arbre des données | actions sur fichiers et variables, types |
| 4 | Base de temps et TBM | contrôles, réglages, diagnostic, axe absolu |
| 5 | Onglets et modèles | dispositions, zoom, Vue d'origine, légendes |
| 6 | Curseurs | simple, double, global, horizontal, condition, X/Y |
| 7 | Traitement conditionnel | statistiques pendant qu'une condition est vraie |
| 8 | Rapports PDF | automatique, pas à pas, contenu d'une page |
| 9 | Projet | enregistrer et rouvrir une analyse |
| 10 | Information et préférences | menu Information, réglages |
| 11 | En cas de problème | symptômes et solutions |
| 12 | Raccourcis | clavier et souris en un coup d'œil |

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

Format attendu : CSV, séparateur virgule, UTF-8, sans
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
| préambule de métadonnées, lignes « # » | ignorés, signalés (non-conformité : métadonnées non prévues) |
| pas de ligne d'en-têtes | la 1re ligne de mesures est **conservée**, colonnes nommées Colonne_1, Colonne_2… |
| en-tête répété au milieu (fichiers mis bout à bout) | ignoré, signalé |
| virgules en fin de ligne | tolérées |
| octets non UTF-8 (fichier enregistré en Windows-1252), UTF-16 | fichier **lu**, marqué en **ERREUR** (non-conformité : encodage autre que UTF-8) avec la 1re ligne fautive |
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
- **Bulle d'aide** : la souris posée sur une ligne affiche son texte complet (utile quand
  l'arbre est étroit et que les colonnes sont tronquées). Idem dans le panneau de lecture.

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
| Stabilité | part des Δt dans la tolérance, jitter max, déphasages, changements de fréquence |
| Croissance continue | aucun horodatage dupliqué ni retour arrière |
| Données manquantes | trous de k périodes (k − 1 échantillons manquants) |
| Lisibilité, horodatages aberrants | horodatage illisible ; horodatage isolé à plus de 10 périodes de ses deux voisins (ex. « 00:00:00 » au milieu d'un essai à 18 h, ou « 23:59:59 » au milieu d'un essai à 0 h 10), signalé en erreur et exclu du calcul du raster, sans compter de faux passage de minuit ; il reste affiché à son instant brut (case « Masquer… » de Base de temps > Configurer pour le retirer des courbes ; seuil de 10 périodes réglable dans Outils > Préférences) |

Le **Time Base Monitor**, en bas de chaque onglet, montre les Δt de chaque fichier affiché
(ou Δt / période quand les fichiers ont des périodes différentes), la période et sa bande
de tolérance, et les anomalies (▼ trou, ◆ déphasage, ✖ doublon / retour arrière,
✚ horodatage illisible, ★ horodatage aberrant, trait mixte = changement de fréquence).
Le titre donne le statut général. La légende, **hors de la courbe** pour ne jamais la
masquer (sur la ligne du titre quand elle y tient), donne pour chaque fichier son nom court
et sa période, son statut s'il n'est pas OK, puis le nombre de chaque sorte d'anomalie.
L'échelle verticale s'adapte aux Δt mesurés : de 0,5 à 1,5 période pour un raster régulier
(les petits écarts restent visibles), jusqu'à 2,6 périodes s'il y a des trous. À l'écran,
**survoler un marqueur** affiche le détail de l'anomalie (fichier, instant, ligne du CSV,
Δt) et un **clic droit** sur la courbe ouvre le diagnostic complet d'un fichier. Dans le
rapport PDF, le résumé de chaque fichier est sur la page de traçabilité.

**Masquer le TBM** n'est possible que si aucune base de temps affichée n'a
d'avertissement ni d'erreur ; il réapparaît automatiquement si une alerte survient.

**Base de temps > Configurer…** (ou double-clic sur le fichier) :

| Réglage | Usage |
|---|---|
| Format, unité | imposer la lecture de la 1re colonne (compteur, heure, date-heure ; unité du compteur) |
| Période nominale, tolérance | raster attendu ; le diagnostic est recalculé |
| Origine absolue | date-heure du compteur 0, ou date du jour pour un horodatage hh:mm:ss |
| Décalage manuel | aligner un PLC non synchronisé (affiché dans le TBM) |
| Affichage régularisé | facultatif, voir ci-dessous |
| Masquer les horodatages aberrants | retire des courbes les horodatages aberrants isolés (ils restent signalés) |
| Diagnostic opérateur | texte libre, imprimé dans le TBM et le rapport |

Par défaut les courbes sont tracées sur l'**horodatage brut** du fichier : rien n'est
recalé. Le jitter qui reste dans la tolérance n'est pas compté comme anomalie, il est
mesuré et affiché : **jitter max** = plus grand écart d'un pas à la période (un pas de
11 ms pour une période de 10 ms donne 1 ms ; avec des temps entiers en ms, c'est un nombre
entier, vérifiable directement dans le CSV). Un Δt pile à la limite de la tolérance est conforme. L'option « Affichage régularisé » remplace l'affichage
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
s'appliquent à tous. Le bouton **maison** de la barre de zoom réaffiche toute la durée des
fichiers avec les échelles verticales automatiques, même après être passé par un autre
onglet. Le bouton **Vue d'origine** (aussi Affichage > Vue d'origine, Ctrl+0) fait de même
et remet en plus les légendes déplacées à leur place ; courbes et curseurs sont conservés.

**Annuler / rétablir** : **Ctrl+Z** annule la dernière action de l'onglet (courbe ajoutée ou
retirée, curseur déplacé, zoom, légende déplacée, titre, aspect…), **Ctrl+Y** la rétablit
(aussi menu Édition) ; jusqu'à 50 actions par onglet.

**Légendes et étiquettes** : tout ce qui est écrit sur le graphique se déplace à la souris
(glisser) : légende d'un axe, légende du Time Base Monitor, noms des pistes logiques,
étiquettes des curseurs (C1, C2, Global, Δt, curseur horizontal, point du nuage X/Y). Chaque
élément garde sa place après un redessin, dans le projet et dans le rapport PDF (à la même
place par rapport aux courbes). Déplacer une étiquette ne déplace pas le curseur. La légende
ne porte que le nom de la variable (le nom du fichier n'y est ajouté que si deux fichiers de
l'axe ont une variable du même nom). Un **clic sur une courbe**, ou sur son nom ou son trait
dans la légende, la sélectionne. Clic droit sur l'axe : masquer / afficher la légende, la
remettre à sa place automatique, remettre les étiquettes à leur place ;
**Vue d'origine** remet tout à sa place.

**Présentation d'un axe** (clic droit sur l'axe) :

| Entrée du menu | Effet |
|---|---|
| Titre de l'axe… | remplace « Axe n » (vide = titre automatique) ; repris dans le rapport |
| Unité de l'axe… | écrite sur l'axe vertical et après les valeurs des curseurs (le CSV ne porte pas d'unité) |
| Hauteur de l'axe | agrandir, réduire, ou revenir à la hauteur du modèle. Plus direct : **glisser la séparation entre deux axes** (le curseur de la souris devient ↕) ; Ctrl+Z annule |
| Aspect de la courbe sélectionnée… | couleur (nuancier), épaisseur, trait (continu, tirets, pointillés, tirets-points) |

| Action sur un onglet | Comment |
|---|---|
| Fermer | croix **×** de son titre, clic molette sur le titre, clic droit sur le titre ou Ctrl+W ; s'il n'en reste aucun, un onglet vide est recréé (numérotation repartant de 1). Fermer un paquet ou un fichier ferme aussi les onglets qui ne montraient que lui |
| Renommer | clic droit sur le titre |
| Revenir à la vue de départ | bouton **Vue d'origine** ou Ctrl+0 |

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
| Double curseur | C1 et C2 posés automatiquement ; Δt, 1/Δt et ΔV par courbe |
| Curseur global | une ligne sur tous les axes (TBM compris), déplacée ensemble ; posée au centre de la vue affichée à chaque activation |
| Curseur horizontal | sur une courbe Float sélectionnée : niveau, franchissements montants / descendants |
| Condition Bool | dans le dialogue du curseur horizontal : 1 à 3 Bool (ET / OU) ; seuls les franchissements sous condition sont retenus ; périodes vraies ombrées |
| Nuage X/Y | Outils > Nuage X/Y : Y = f(X), corrélation r (pas de droite de régression) ; clic = désigner un point, affiché par deux curseurs ou par le seul point de croisement ; C1 / C2 reportés |

Souris : **clic sur une courbe** = la sélectionner ; **clic ailleurs** = placer le curseur ;
**glisser** = le déplacer (un curseur se saisit en priorité sur la courbe qu'il recouvre) ;
**Maj + clic** = niveau du curseur horizontal ; **clic droit** = menu de l'axe. Clavier :
**flèches gauche / droite** = échantillon précédent / suivant de la courbe sélectionnée.
Quand la loupe ou la croix de la barre d'outils est active, les clics servent au zoom ;
activer un curseur (simple, double, global, suivi, horizontal) la désactive et place le
curseur dans la vue affichée : pas de zoom involontaire.

Les valeurs lues sont celles des **échantillons réels** : le plus proche pour un Float,
l'état en cours pour un Bool. Le panneau de lecture indique l'instant de l'échantillon et
sa **ligne dans le CSV** ; « Copier » colle le tableau dans un tableur.

## 7. Traitement conditionnel

**Outils > Traitement conditionnel…** : choisir une condition Bool et des signaux
analogiques, un seuil facultatif, puis **Calculer** : nombre d'échantillons, durée, min,
max, moyenne, écart-type, nombre de périodes et durée au-dessus du seuil pendant que la
condition est vraie. Copier ou exporter en CSV.

## 8. Rapports PDF

| Commande | Effet |
|---|---|
| **Rapport > En-tête…** | nom du projet, unité / tranche, émetteur, référence |
| **Rapport automatique** (Ctrl+P) | la page graphique de l'onglet actif, ses lectures et la traçabilité |
| **+ Page pas à pas** (Ctrl+K) | capture la vue active (zoom, curseurs, légendes, nuage X/Y, condition) avec un commentaire ; recommencer après chaque réglage |
| **Gérer les pages…** | ordonner, commenter, supprimer les captures, puis **Générer le PDF** |

À chaque génération, l'outil demande l'orientation des pages A4 : **paysage** ou
**portrait** (le dernier choix est proposé). Le rapport est épuré :

| Page | Contenu |
|---|---|
| Graphique (une par capture) | l'en-tête, le titre de la capture, puis **uniquement les graphiques** (axes et Time Base Monitor) |
| Lectures | le tableau des lectures de curseurs de la capture (sur plusieurs pages s'il le faut) |
| Identification et traçabilité (dernière) | un tableau d'une ligne par fichier source (statut, période, Δt conformes, jitter max, anomalies), les seuls avertissements et erreurs, l'environnement |

Chaque page porte l'en-tête complet (outil, émetteur, date, projet, unité, référence, empreinte du projet, fichiers sources) ; le pied de page indique qui a émis le rapport et quand. Les étiquettes des curseurs ne se chevauchent jamais : si l'axe est trop bas,
elles se réduisent à l'instant (la valeur figure dans les pages de lectures).

Le style suit celui des rapports de test du projet : police à chasse fixe, axes quadrillés,
légendes des courbes à droite. Si le Time Base Monitor a été masqué, la page graphique porte
à sa place l'indication de conformité de la base de temps.

## 9. Projet

**Fichier > Enregistrer le projet** (Ctrl+S) crée un fichier `.ptbg.json` : paquets,
chemins des CSV (relatifs au projet), réglages de base de temps, types forcés, groupes,
onglets, curseurs et pages du rapport. **Ouvrir un projet** recharge le tout ; un CSV
modifié depuis l'enregistrement est signalé (empreinte différente). L'empreinte du projet
apparaît dans l'en-tête des rapports.

## 10. Information et préférences

Menu **Information** : version, historique des modifications, sources (empreinte de chaque
module, versions de Python, Tk et des bibliothèques), cette aide, journal d'activité,
traçabilité des requis.

| Outils > Préférences | Valeur par défaut |
|---|---|
| Taille maximale d'un CSV (valeur à confirmer) | 500 Mo |
| Tolérance par défaut de la période | 10 % |
| Unité supposée d'un compteur sans unité | ms |
| Intervalles consécutifs pour un changement de fréquence | 10 |
| Écart d'un horodatage aberrant isolé | 10 périodes |
| Points affichés par courbe avant réduction min/max | 4000 |

## 11. En cas de problème

| Symptôme | Cause et solution |
|---|---|
| Fichier rouge « ILLISIBLE » | voir son nœud Diagnostic : séparateur, encodage, taille maximale (Préférences) |
| TBM impossible à masquer | une base de temps affichée a un avertissement ou une erreur (voir le TBM) |
| Curseur qui ne bouge pas au clic | la loupe ou la croix de la barre d'outils est active : la désactiver (activer un curseur le fait automatiquement) |
| Fausse manipulation | Ctrl+Z (Édition > Annuler) |
| Axe absolu refusé | un fichier n'a pas d'origine absolue : la saisir dans Base de temps > Configurer |
| Rien ne s'affiche sous SLES à distance | se connecter avec `ssh -X` (session graphique requise) |
| Message sur une bibliothèque au démarrage | versions différentes de celles testées : voir Information > Sources et docs/DEPENDANCES.md |
| Lecture lente ou mémoire insuffisante sur de très gros fichiers | mesurer le poste avec `python tools/banc_performance.py fichier.csv` et ajuster la taille maximale (Outils > Préférences) |

## 12. Raccourcis

| Clavier | Action |
|---|---|
| Ctrl+O | ouvrir des fichiers CSV |
| Ctrl+S | enregistrer le projet |
| Ctrl+W | fermer l'onglet |
| Ctrl+0 | vue d'origine (toute la durée, échelles automatiques) |
| Ctrl+Z / Ctrl+Y | annuler / rétablir la dernière action de l'onglet |
| Ctrl+P | rapport automatique de l'onglet actif |
| Ctrl+K | ajouter la vue active au rapport pas à pas |
| F9 | afficher / masquer l'arbre des données |
| F1 | cette aide |
| Ctrl+Q | quitter |
| Flèche gauche / droite | curseur sur l'échantillon précédent / suivant de la courbe sélectionnée |

| Souris | Action |
|---|---|
| clic sur un axe | rend l'axe actif ; place le curseur |
| clic sur une courbe | la sélectionne (sa valeur est portée par les curseurs) |
| survol d'un marqueur du TBM | détail de l'anomalie |
| clic droit sur le TBM | diagnostic complet d'un fichier |
| glisser la séparation entre deux axes | change leur hauteur |
| glisser | déplace le curseur |
| Maj + clic | niveau du curseur horizontal |
| glisser une légende, un nom de piste ou une étiquette de curseur | le déplace (place conservée, curseur inchangé) |
| clic sur un nom ou un trait de la légende | sélectionne cette courbe |
| clic droit sur un axe | menu de l'axe (titre, unité, hauteur, curseurs, courbe sélectionnée et son aspect, échelle, légende) |
| double-clic sur une variable de l'arbre | l'ajoute à l'axe actif |
| glisser une variable de l'arbre sur un axe | l'ajoute à cet axe |
| clic molette sur le titre d'un onglet | ferme l'onglet |
