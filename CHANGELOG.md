# Historique des modifications — VISU PTBG

Affiché par Information > Historique des modifications (REQ_COMMON_KH_5101).
Chaque version incrémente `ptbg/version.py` et ajoute une entrée ici.

## 2.3.0 — 2026-10-28 — statuts plus prudents, horodatages aberrants visibles

Suite à une relecture critique du récapitulatif :

- **Statuts** : REQ 5407 (Bool d'un autre fichier : dernier état maintenu) et REQ 5408
  (appariement de deux fichiers : échantillon le plus proche à moins d'une demi-période)
  passent en « interprétation à valider » : ces règles de rapprochement entre PLC ne sont
  pas décrites par les requis (points ouverts n° 12 et nouveau n° 18). Bilan : 47 implémentés
  et testés, 14 interprétations à valider, 1 proposition, 2 qualifications à faire.
- **Horodatage aberrant** (point ouvert n° 16) : toujours signalé en ERREUR et exclu du seul
  calcul du raster, mais désormais **affiché à son instant brut** sur les courbes (vue
  initiale cadrée sur les mesures normales) ; case « Masquer » par fichier (Base de temps >
  Configurer, enregistrée dans le projet) ; seuil de 10 périodes réglable (Outils >
  Préférences, `aberrant_jump_periods`), à valider.
- Matrice : un test cité prouve qu'un cas représentatif est vérifié, pas à lui seul que
  toute l'exigence l'est (précision ajoutée).
- Récapitulatif Excel : plus de `**` Markdown dans les cellules ; « Commentaires de
  Sébastien pris en compte : 4, dont 3 à valider » ; « requis avec au moins un test
  associé » au lieu d'une preuve de satisfaction.
- 132 tests (nouveau : horodatage aberrant visible, masquable, seuil réglable, cadrage).

## 2.2.0 — 2026-10-28 — performances sur gros fichiers

Modifications ciblées des modules existants ; aucune règle métier changée sauf la
correction de minuit ci-dessous. Résultats vérifiés IDENTIQUES à la 2.1.0 (tables lues,
constats, instants, analyses) par comparaison automatique sur plus de 10 000 fichiers et
séries abîmés générés au hasard, avec numpy 2.4 et numpy 1.24.

**Lecture CSV** (`core/csv_reader.py`, nouveau `core/vector_parse.py`)
- Lecture par blocs : les lignes ordinaires d'un bloc sont découpées d'un coup ; les
  lignes particulières (vides, commentaires, guillemets, octets nuls, en-tête répété,
  largeur différente) passent toujours une à une par les mêmes règles qu'avant.
- Colonnes non entièrement numériques (true/false, états, cases vides) converties sans
  boucle par cellule : chaque texte distinct est classé une fois, et dans une colonne de
  nombres les quelques cellules fautives sont isolées par dichotomie.
- Mémoire : les valeurs lues ne sont plus recopiées par variable (tableaux partagés,
  rendus non modifiables) ; blocs libérés au fil de l'assemblage.
- Repère (banc Linux, Python 3.11) : 1 million de lignes × 21 colonnes lues et analysées
  en 4,7 s (115 Mo, Bool 0/1), 7,0 s (150 Mo, Bool true/false) et 6,7 s (157 Mo, heure
  hh:mm:ss.ns), contre 7,8 s, 12,0 s et 13,1 s en 2.1.0 ; fichier de 500 Mo
  (3,66 millions de lignes) : 32 s et 1,6 Go au lieu de 61 s et 2,2 Go ; mémoire après
  chargement réduite d'environ 20 %.

**Base de temps** (`core/time_parser.py`, `core/time_base.py`)
- Heures « hh:mm:ss.fraction », dates-heures et grands compteurs (ns depuis 1970)
  convertis pour toute la colonne d'un coup ; toute écriture atypique est reprise ligne
  par ligne par l'expression régulière (résultat identique, entiers exacts).
- Changements de fréquence cherchés dans une fenêtre croissante : 80 000 changements
  analysés en 6 s au lieu de plusieurs minutes (REQ 4105).
- **Correction** (REQ 2306) : une heure isolée aberrante VERS L'AVANT (« 23:59:59 » au
  milieu d'un essai à 0 h 10) faisait compter un faux passage de minuit et décalait tout
  le reste du fichier d'un jour. Elle est maintenant traitée comme « 00:00:00 » au milieu
  d'un essai à 18 h : horodatage aberrant signalé, sans décalage.

**Affichage** (`core/sampling.py`, `plotting/renderer.py`, `gui/analysis_tab.py`)
- Curseurs redessinés seuls sur le rendu figé du reste de la figure (« blitting ») :
  suivi souris environ 20 ms au lieu de 240 ms, flèches environ 25 ms au lieu de 250 ms
  (1 million de points, 8 courbes et un nuage X/Y ; Tk 8.6 et Tk 9). Image identique au
  pixel près ; PDF inchangé.
- Abscisses des curseurs et ordre des courbes préparés une fois (et non à chaque
  mouvement ou zoom) ; nuage X/Y gardé en cache tant que ses courbes ne changent pas.
- Croix des cellules vides : calcul linéaire (300 000 suites de cellules vides en moins
  d'une seconde au lieu de plusieurs minutes, fenêtre figée).
- Type Texte forcé sur une colonne de nombres : libellés calculés par valeur distincte.

**Outils et documentation**
- `tools/banc_performance.py` : mesure lecture / base de temps / mémoire sur de vrais
  fichiers PTBG, ou sur un fichier de synthèse de N Mo (`--generer N`), pour fixer la
  taille maximale (REQ 2310) sur les postes cibles ; mémoire lue par
  `system/compat.py` (`process_memory_mb`).
- Récapitulatif Excel des requis : `docs/recapitulatif/Recapitulatif_requis_VISU_PTBG.xlsx`
  (synthèse par statut et par section, 64 lignes de requis avec énoncé du Word, commentaire
  de Sébastien, réalisation, programmes et tests, réponses aux 4 commentaires, 17 points
  ouverts avec colonne de réponse, 45 fichiers de programme, 131 tests). Matrice : REQ 5404
  cite explicitement son code et ses tests ; REQ 2303 cite `_locate_header` (ancien nom corrigé).
- COMPATIBILITE_OS.md : encodage et fins de ligne décrits comme en 2.1.0 (lecture
  signalée des fichiers non UTF-8, lecture ligne par ligne) ; banc ajouté à l'essai.
- 131 tests (11 nouveaux : coupures de blocs, colonnes mixtes, conversions en bloc,
  dates calendaires, grands entiers, heure aberrante vers l'avant, changements de
  fréquence, croix, nuage X/Y en cache, blitting) ; campagne de 7 combinaisons Python
  3.10 à 3.14, numpy 1.24 à 2.5, matplotlib 3.6 à 3.11, Tk 8.6 et 9 : toutes OK
  (DEPENDANCES.md § 4).

## 2.1.0 — 2026-10-28 — robustesse de la lecture et de la base de temps

Banc de 130 fichiers abîmés (et 40 corruptions aléatoires dans la suite de tests) :
aucune exception, aucune donnée saine perdue ou inventée, chaque anomalie citée avec sa ligne.

**Lecture CSV (défauts corrigés)**
- Un guillemet non fermé avalait toute la suite du fichier : la lecture se fait
  désormais ligne par ligne, seule la ligne fautive est rejetée.
- Des virgules finales sur les seules lignes de données faisaient perdre l'en-tête ;
  un préambule aussi large que le tableau était pris pour l'en-tête ; un fichier sans
  en-tête perdait sa 1re mesure : nouveau repérage de l'en-tête (`_locate_header`).
- En-tête répété au milieu (fichiers concaténés), lignes « ,,,, », octets nuls
  (fichier interrompu), dernière ligne non terminée : ignorés ou rejetés, et signalés.
- Une cellule de plus de 128 Ko faisait refuser le fichier ; « nan »/« inf » étaient
  pris pour du texte (une colonne Float pouvait devenir Texte).
- Octets non UTF-8 (Windows-1252) et UTF-16 : fichier lu et marqué en ERREUR avec la
  1re ligne fautive, au lieu d'être refusé en entier (REQ 2302).
- Point-virgule avec virgule décimale mieux détecté ; virgule décimale dans un fichier
  à virgules : refus expliqué au lieu de colonnes inventées.
- Une ligne au mauvais nombre de champs est citée avec son extrait.

**Base de temps**
- Horodatage brut affiché par défaut ; la régularisation devient une option (REQ 4107).
- Unité de compteur supposée : avertissement (TBM non masquable) jusqu'à confirmation,
  applicable d'un coup à plusieurs fichiers (REQ 2307).
- Horodatage aberrant isolé (ex. « 00:00:00 » au milieu d'un essai à 18 h) : une
  erreur au lieu d'un faux passage de minuit décalant tout le fichier d'un jour, ou
  d'un faux trou de plusieurs millions d'échantillons.
- Format de temps détecté sur tout le fichier (des lignes illisibles en tête ne font
  plus perdre la base de temps) ; une valeur aberrante ne change plus la conversion
  d'un compteur ; les lignes à horodatage illisible ne changent plus le type des variables.
- Horodatages illisibles et aberrants marqués dans le TBM.

**Affichage et isolation**
- Valeurs extrêmes (±1e308) : axe borné au lieu d'une erreur « Singular matrix ».
- Un axe impossible à dessiner affiche un message au lieu d'interrompre l'onglet ;
  une erreur imprévue sur un fichier le marque en erreur sans arrêter les autres.
- Constats par variable : cellules vides, valeurs non finies, valeurs incompatibles.

**Documentation** : statuts de la traçabilité reformulés (implémenté et testé /
interprétation à valider / proposition / qualification à faire) ; points ouverts complétés.

## 2.0.0 — 2026-10-27 — réécriture complète

Réécriture structurée de l'outil, couvrant les 64 lignes de requis de
NCS/00/I/COMMON----/ES/010 Rev. A (matrice : docs/TRACABILITE_REQUIS.md).

**Architecture**
- `MAIN.py` réduit à l'assemblage de la fenêtre (REQ 3002) ; contrôleur unique
  `ptbg/gui/app.py` ; traitements sans interface dans `ptbg/core/` (REQ 3003) ;
  dessin commun écran / PDF dans `ptbg/plotting/` ; rapport dans `ptbg/report/`.
- Différences Windows / SLES centralisées dans `ptbg/system/compat.py` (REQ 3005).
- Dépendances limitées à numpy et matplotlib, figées pour Python 3.11 à 3.14,
  Windows et SLES ; relevé de l'environnement au démarrage (REQ 3004).
- Contrôles automatiques : MAIN dédié à l'IHM, code commenté, aucune fonction
  inutile, traçabilité de chaque requis du Word (REQ 3006, 3007).

**Lecture et base de temps**
- Lecture par blocs, annulable, en arrière-plan ; contrôles de format
  (séparateur sur texte brut, UTF-8 strict, métadonnées, en-têtes, taille).
- Formats de temps : compteur (ns à h, cycles PLC, grands entiers exacts),
  hh:mm:ss jusqu'à la nanoseconde avec passage de minuit, date-heure ;
  pré-déclenchement en temps négatif ; origine absolue.
- Analyse du raster : valeur, stabilité, croissance continue, trous, déphasage,
  changements de fréquence par segments, horodatage régularisé (jitter ignoré),
  raster nominal imposé et diagnostic opérateur.
- Comparaison inter-PLC : fréquences, déphasage, perte de flux ; axe absolu.

**Interface**
- Barre de menus et de chemin, arbre masquable (paquets > fichiers > base de
  temps / groupes / diagnostic / variables typées), onglets à 7 modèles, Time
  Base Monitor automatique (masquage soumis au statut), barre d'état.
- Curseurs : simple par axe, suivi souris avec panneau de lecture, double avec
  Δt / ΔV, global, horizontal conditionné par Bool, nuage X/Y avec corrélation ;
  glisser-déposer, flèches clavier ; lecture des échantillons réels uniquement.
- Groupes binaires, types forçables, traitement conditionnel, projet `.ptbg.json`
  portable entre Windows et SLES.

**Rapports**
- PDF automatique et pas à pas, en-tête complet (version, émetteur, date,
  sources et SHA-256, projet, unité, référence et empreinte du projet), TBM ou
  indication de conformité, tableau des lectures, page de traçabilité.

**Qualité**
- 90 tests automatisés (unittest) dont l'interface réelle ; campagne Python 3.10
  à 3.14, Tk 8.6 et 9.0, numpy 1.24 à 2.5, matplotlib 3.6 à 3.11.

## 1.0.0 et antérieures — prototype

Prototype Tkinter développé par itérations v0.3 à v1.0.0 (lecture CSV, diagnostic
de base de temps, croix sur cellules vides, Time Base Monitor, premiers curseurs
et rapports), remplacé par la version 2.0.0 et retiré du livrable. Les données
d'exemple et les scripts de simulation de référence ont été conservés à l'identique
(`data/exemples/`, `data/references_simulation/`). Les décisions de cette
phase ont été reprises : première colonne imposée comme temps, aucune valeur
inventée, croix réservées aux cellules vides, groupe binaire = colonnes Bool,
Bool de condition lu sur la même ligne.
