# Architecture de VISU PTBG 2.3.0 — pour reprendre le code

## 1. Vue d'ensemble

```
MAIN.py                      assemble la fenêtre (REQ 3002) — aucune logique métier
ptbg/
├── version.py               nom, version, spécification, Python minimal
├── config.py                préférences persistantes (taille max, tolérance, en-tête…)
├── system/                  dépendances au système (REQ 3000, 3004, 3005)
│   ├── compat.py            TOUTES les différences Windows / SLES
│   ├── environment.py       relevé Python / Tk / bibliothèques, plages testées
│   └── activity_log.py      journal d'activité (mémoire + fichier)
├── core/                    traitements purs : ni Tk ni Matplotlib (REQ 3003)
│   ├── diagnostics.py       gravités et constats
│   ├── csv_reader.py        lecture contrôlée des CSV (REQ 2300-2310)
│   ├── vector_parse.py      conversions de colonnes entières (nombres, horodatages) (REQ 4105)
│   ├── signals.py           types Bool / Float / Texte, groupes binaires (REQ 2200-2201)
│   ├── time_parser.py       formats de temps -> secondes, origine absolue (REQ 2305-2307)
│   ├── time_base.py         analyse du raster (REQ 4100-4107)
│   ├── data_package.py      fichiers, paquets, axe des temps commun (REQ 2101-2105)
│   ├── multi_source.py      comparaison inter-PLC (REQ 2102, 2104)
│   ├── sampling.py          lecture d'échantillons, réduction d'affichage, franchissements
│   ├── conditional.py       conditions Bool et statistiques (REQ 5407, 5500)
│   ├── xy.py                nuage X/Y et corrélation (REQ 5408)
│   ├── curves.py            courbe = variable ou groupe binaire
│   ├── readings.py          lectures des curseurs (panneau droit et PDF)
│   ├── arrangement.py       modèles de disposition et état d'un onglet (REQ 5300)
│   ├── project.py           fichier projet .ptbg.json, pages de rapport
│   └── diagnostic_report.py texte du diagnostic complet d'un fichier
├── plotting/                dessin Matplotlib, commun écran et PDF
│   ├── renderer.py          rendu d'un onglet : axes, courbes, curseurs, X/Y
│   ├── monitor.py           Time Base Monitor (REQ 4102-4104)
│   ├── time_axis.py         graduations relatives / absolues
│   └── styles.py            couleurs et tailles
├── report/
│   └── pdf_report.py        rapport automatique et pas à pas (REQ 6000-6005)
└── gui/                     interface Tkinter (section 4)
    ├── app.py               contrôleur : TOUTES les actions de l'IHM
    ├── menu_bar.py          menus (REQ 5100, 5101)
    ├── path_bar.py          barre de chemin et accès rapides (REQ 5100)
    ├── tree_panel.py        arbre des données (REQ 5103, 5105, 5200-5203)
    ├── graph_area.py        onglets (REQ 5104, 5106)
    ├── analysis_tab.py      un onglet : souris, clavier, curseurs (REQ 5400-5408)
    ├── reading_panel.py     panneau de lecture à droite (REQ 5402)
    ├── status_bar.py        barre d'état (REQ 5102)
    ├── info_windows.py      fenêtres Information et visualiseur Markdown (REQ 5101)
    ├── tasks.py             fils de travail (REQ 4105)
    ├── icons.py             icônes de statut dessinées
    └── dialogs/             base de temps, groupes, curseur H, X/Y, rapport, préférences
tests/                       unittest : core, rendu, PDF, IHM réelle, architecture
tools/                       audit d'environnement, traçabilité, données de démonstration
install/                     installation et lancement Windows / SLES
data/exemples/               CSV reçus (inchangés) ; data/demo/ : CSV de démonstration
docs/                        spécification, guide, dépendances, compatibilité, traçabilité
```

Règle de dépendance (vérifiée par `tests/test_architecture.py`) :

```
gui  ──►  plotting, report  ──►  core  ──►  numpy
 │                                 ▲
 └─────────────────────────────────┘        system : utilisable par tous
```

`core` n'importe jamais `tkinter` ni `matplotlib` ; `plotting` et `report` n'importent
jamais `tkinter`. On peut donc tester et réutiliser les traitements sans interface.

## 2. Flux de données

1. **Lecture** (`gui/app.py::_load`, fil de travail) : `load_source()` →
   `read_csv()` (contrôles 2300-2310 ; texte lu par blocs de 512 Ki caractères en
   lignes physiques entières (`_line_blocks`) ; repérage de l'en-tête dans
   `_locate_header` sur les 50 premières lignes ; dans chaque bloc, les suites de
   lignes « ordinaires » de même largeur (`_ordinary_lines`) sont découpées d'un coup
   (`take_run`), toute autre ligne passe par `_split_line` et `accept` ; chaque
   cellule est classée vide / nombre / booléen / texte / non finie, colonne par
   colonne (`_ColumnBuilder`))
   → `convert_time_column()` (1re colonne → secondes + origine absolue, décodée pour
   toute la colonne par `vector_parse.match_templates`) → `analyze()` (raster,
   événements, horodatages aberrants, horodatage régularisé facultatif).
   Règle des conversions en bloc : numpy convertit la colonne entière ; ce qu'il refuse
   est repris par la fonction « une cellule / une ligne » d'origine (`_classify`,
   `_time_of_day_ns`, `_parse_datetime_text`…) : le résultat est identique, seule la
   vitesse change.
   `load_source()` ne lève jamais d'exception (sauf annulation) : toute erreur devient
   un constat ERREUR sur ce seul fichier (REQ 4105).
2. **Interprétation** à la demande : `SourceFile.signal(nom)` applique le type (auto ou
   forcé) sans relire le fichier ; résultat mis en cache, invalidé par `revision`.
3. **Affichage** : un onglet est un `TabState` (données pures) ; `TabRenderer` le dessine
   dans une figure Matplotlib. Le même `TabRenderer` dessine la page PDF.
4. **Axe des temps** : `Workspace.timeline()` renvoie un `Timeline` (relatif ou absolu) ;
   `Timeline.x(fichier)` donne les abscisses (mises en cache) de chaque échantillon.
5. **Curseurs** : positions stockées dans `TabState` / `AxleState` ; `core/readings.py`
   calcule les lectures (échantillon réel, jamais interpolé) sur une `TimeGrid` (abscisses
   finies et leur ordre, préparées une fois par fichier et par axe des temps) ;
   `TabRenderer.draw_cursors()` ne recrée que les curseurs, et `AnalysisTab.update_cursors()`
   les redessine seuls sur le rendu figé du reste de la figure (« blitting », rendu
   mémorisé à chaque dessin complet par `_on_draw`). Zoom : chaque courbe est une
   `DisplayCurve` dont l'ordre des abscisses n'est analysé qu'une fois. Nuage X/Y et mots
   binaires gardés en cache tant que leurs courbes ne changent pas.
6. **Rapport** : une page est une copie figée du `TabState` (`ReportPage`) ;
   `export_pdf()` dessine chaque page (en-tête + zone graphique + lectures) puis l'annexe.

## 3. Choix techniques et raisons

| Choix | Raison |
|---|---|
| Tkinter (bibliothèque standard) | présent avec Python sous Windows et SLES (`python311-tk`) ; aucune licence ni paquet lourd ; fonctionne dans Spyder |
| Matplotlib sans `pyplot` | pas de conflit avec le backend graphique de la console Spyder ; même rendu écran / PDF |
| numpy seul (pas pandas) | moins de dépendances à qualifier (REQ 3004) ; lecture en flux maîtrisée |
| Fils (`threading`) plutôt que processus | `multiprocessing` est peu fiable dans Spyder sous Windows |
| Réduction min/max des points | courbes de millions de points fluides ; les pics restent visibles ; les curseurs lisent les vrais échantillons |
| Aucune interpolation, aucune valeur inventée | traçabilité d'un outil d'analyse d'anomalies : une cellule vide reste vide (croix), un trou de temps interrompt la courbe |
| Lecture ligne par ligne (et non `csv.reader` sur tout le fichier) | un guillemet non fermé ne peut plus avaler la suite du fichier ; numéros de ligne exacts ; découpage direct à la virgule plus rapide, module `csv` en mode strict seulement pour les lignes à guillemets |
| Blocs de lignes ordinaires découpés d'un coup, conversions de colonnes entières | un fichier de 500 Mo se lit en quelques dizaines de secondes ; les lignes et cellules particulières gardent leur traitement une à une, d'où des résultats identiques (vérifiés par comparaison automatique avec la 2.1.0) |
| Valeurs lues non modifiables et partagées par les variables | la règle « aucune valeur modifiée » est garantie par numpy (écriture refusée) ; pas de copie par variable, mémoire réduite |
| Curseurs « animés » (blitting) | un mouvement de souris ne redessine que les curseurs : fluidité avec des millions de points ; le PDF dessine les curseurs normalement |
| Ligne au mauvais nombre de champs rejetée, jamais complétée | sa dernière valeur pourrait être tronquée : mieux vaut un trou signalé qu'une valeur fausse |
| Robustesse vérifiée par un banc de fichiers abîmés | `tests/test_robustesse.py` : lignes tronquées ou en trop, guillemets, octets nuls, encodages, en-têtes absents ou répétés, horodatages aberrants, valeurs extrêmes, 40 corruptions aléatoires |
| Nanosecondes entières pour les dates | pas d'arrondi flottant sur des horodatages absolus à la nanoseconde (REQ 2306) |
| État des onglets en données pures | captures de rapport, projet JSON et tests sans écran |

## 4. Conventions de code

- Identifiants en anglais, commentaires et textes de l'IHM en français.
- Chaque module commence par une docstring qui cite les requis couverts
  (`REQ_COMMON_KH_xxxx`) ; `tools/verifier_tracabilite.py` s'appuie sur ces citations.
- Docstring pour chaque classe et fonction ; commentaires sur le « pourquoi ».
- Pas de fonction inutile : `tests/test_architecture.py::test_no_unused_functions`.
- Python ≥ 3.10 : `from __future__ import annotations`, `dataclasses` ; pas d'antislash
  dans les expressions de f-string (interdit avant Python 3.12).

## 5. Ajouter une fonctionnalité — exemples

**Nouveau modèle de disposition** : ajouter un `Template` dans `core/arrangement.py::TEMPLATES`
(grille, emplacements, ratios). Il apparaît automatiquement dans les menus ; le TBM est
ajouté sous la disposition par le rendu. Les tests vérifient la cohérence de la grille.

**Nouveau format de temps** : ajouter l'expression régulière et la fonction de conversion
dans `core/time_parser.py`, la valeur dans `TimeFormat`, puis un test dans
`tests/test_time_parser.py`.

**Nouvelle anomalie de base de temps** : ajouter le code dans `EventKind` et son
classement dans `core/time_base.py::_classify`, le style dans `plotting/styles.py`
(`EVENT_STYLE`), puis un test dans `tests/test_time_base.py`.

**Nouvelle action de menu** : écrire la méthode dans `gui/app.py`, l'entrée dans
`gui/menu_bar.py` ; le traitement lui-même va dans `core/`.

## 6. Tests

```
python -m unittest discover -s tests -v          # tout (IHM ignorée sans écran)
xvfb-run python -m unittest discover -s tests    # Linux sans écran : IHM incluse
python tools/verifier_tracabilite.py             # chaque requis du Word est tracé
python tools/audit_environnement.py              # versions présentes vs figées
python tools/banc_performance.py f.csv           # durées et mémoire sur de vrais fichiers
```
