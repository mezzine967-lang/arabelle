# Historique des modifications — VISU PTBG

Affiché par Information > Historique des modifications (REQ_COMMON_KH_5101).
Chaque version incrémente `ptbg/version.py` et ajoute une entrée ici.

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

## 1.0.0 et antérieures — prototype Codex (archivé)

Prototype Tkinter développé par itérations v0.3 à v1.0.0 (lecture CSV, diagnostic
de base de temps, croix sur cellules vides, Time Base Monitor, premiers curseurs
et rapports). Sources conservées dans `archive/` ; les données d'exemple et les
scripts de simulation en ont été repris à l'identique. Les décisions de cette
phase ont été reprises : première colonne imposée comme temps, aucune valeur
inventée, croix réservées aux cellules vides, groupe binaire = colonnes Bool,
Bool de condition lu sur la même ligne.
