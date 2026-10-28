# Dépendances, versions et impacts de montée de version — REQ_COMMON_KH_3004

> « All additional packages or library implemented shall be documented and strictly
> aligned with the kernel version. » — le « kernel » est ici l'interpréteur Python
> (vocabulaire de Spyder : *kernel* de la console IPython).

Principe retenu : **le minimum de bibliothèques tierces**. L'outil n'utilise que la
bibliothèque standard de Python, **numpy** et **matplotlib**, toutes présentes dans
l'environnement de Spyder 6 : rien n'est à installer au poste Windows, et l'installation
SLES se limite à un environnement virtuel avec 11 wheels binaires (aucune compilation).

## 1. Interpréteur Python

| Élément | Valeur |
|---|---|
| Version de référence (développement) | **Python 3.11** (Spyder 6 au poste Windows ; `python311` du module Python 3 de SLES 15 SP7) |
| Versions vérifiées (suite de tests complète, IHM comprise) | 3.10, 3.11, 3.12, 3.13, 3.14 — voir § 4 |
| Version minimale acceptée par le code | 3.10 (`ptbg/version.py`, `MIN_PYTHON`) — contrôlée au lancement par `MAIN.py` |
| Architecture | 64 bits (Windows 11 x64 et SLES x86-64, les cibles du projet). Des wheels 32 bits existent pour certains paquets, mais ce mode n'est ni ciblé ni testé |
| Python 3.6 (REQ 3001) | Non retenu : fin de vie en décembre 2021, dernières versions compatibles numpy 1.19 / matplotlib 3.3 ; le relecteur indique qu'un Python 3.11 est disponible sur SLES 15. Voir POINTS_OUVERTS.md. |

## 2. Bibliothèques tierces (figées dans `requirements.txt`)

Même fichier pour Windows 11 64 bits et SLES 15 SP7, de Python 3.11 à 3.14.

| Paquet | Version | Type | Utilisation dans VISU PTBG | Python supporté par cette version | Wheels utilisées | Licence |
|---|---|---|---|---|---|---|
| numpy | 2.4.6 | **directe** | tableaux des signaux, analyse vectorisée de la base de temps, curseurs, réduction d'affichage | ≥ 3.11 (cp311 à cp314) | win_amd64 ; manylinux_2_27/2_28 (glibc ≥ 2.28) | BSD-3-Clause (+ 0BSD, MIT, Zlib, CC0) |
| matplotlib | 3.10.9 | **directe** | courbes, TBM, curseurs, nuage X/Y, intégration Tk (TkAgg), PDF (PdfPages) | 3.10 à 3.14 | win_amd64 ; manylinux2014 (glibc ≥ 2.17) | licence Matplotlib (type PSF) |
| contourpy | 1.3.3 | transitive (matplotlib) | non utilisée directement | ≥ 3.11 | win_amd64 ; manylinux_2_27 | BSD-3-Clause |
| cycler | 0.12.1 | transitive (matplotlib) | non utilisée directement | ≥ 3.8 (pur Python) | py3-none-any | BSD-3-Clause |
| fonttools | 4.65.0 | transitive (matplotlib) | sous-ensembles de polices du PDF | ≥ 3.10 | win_amd64 ; manylinux2014 (ou pur Python) | MIT |
| kiwisolver | 1.4.9 | transitive (matplotlib) | non utilisée directement | ≥ 3.10 | win_amd64 ; manylinux2014 | BSD-3-Clause |
| packaging | 26.2 | transitive (matplotlib) | non utilisée directement | ≥ 3.8 (pur Python) | py3-none-any | Apache-2.0 ou BSD-2-Clause |
| pillow | 12.3.0 | transitive (matplotlib) | icônes de la barre d'outils, images | ≥ 3.10 | win_amd64 ; manylinux_2_27/2_28 | MIT-CMU |
| pyparsing | 3.3.2 | transitive (matplotlib) | non utilisée directement | ≥ 3.9 (pur Python) | py3-none-any | MIT |
| python-dateutil | 2.9.0.post0 | transitive (matplotlib) | non utilisée directement | ≥ 2.7 (pur Python) | py2.py3-none-any | Apache-2.0 / BSD-3-Clause |
| six | 1.17.0 | transitive (python-dateutil) | non utilisée directement | ≥ 2.7 (pur Python) | py2.py3-none-any | MIT |

Contraintes déclarées par matplotlib 3.10.9 : `contourpy>=1.0.1`, `cycler>=0.10`,
`fonttools>=4.22.0`, `kiwisolver>=1.3.1`, `numpy>=1.23`, `packaging>=20.0`, `pillow>=8`,
`pyparsing>=3`, `python-dateutil>=2.7`. contourpy 1.3.3 exige `numpy>=1.25`.

Composants « compilés » (sensibles à la version de Python, à l'OS et aux 32/64 bits,
remarque du relecteur sur REQ 3004) : numpy, matplotlib, contourpy, kiwisolver, pillow
(et fonttools en version accélérée). Les autres sont du Python pur, valables partout.

Aucune autre bibliothèque n'est utilisée à l'exécution : ni pandas, ni scipy, ni Qt,
ni reportlab. Les tests n'utilisent que `unittest` (bibliothèque standard).
Outil de développement facultatif : `vulture` 2.14 (détection de code mort, REQ 3007),
jamais requis pour exécuter l'outil.

## 3. Bibliothèque standard Python utilisée

Fournie avec l'interpréteur : rien à installer, version = celle de Python.

| Module | Utilisation |
|---|---|
| `tkinter` (et `tkinter.ttk`, `filedialog`, `messagebox`, `simpledialog`, `font`) | toute l'interface ; exige Tcl/Tk (voir § 3 bis) |
| `csv` | lecture des CSV, export des résultats du traitement conditionnel |
| `io` | flux texte décodé sur le fichier binaire (avancement de lecture) |
| `codecs` | contrôle UTF-8 par blocs et lecture de secours Windows-1252 des octets non UTF-8 (signalée, REQ 2302) |
| `hashlib` | SHA-256 des CSV, du projet et des modules (en-tête de rapport, Information > Sources) |
| `json` | préférences et fichier projet |
| `re` | formats de temps, unités dans les en-têtes, groupes binaires `NOM[i]` |
| `math` | valeurs finies, graduations de l'axe des temps |
| `datetime` | dates absolues, horloge de la barre d'état, journal |
| `dataclasses`, `enum`, `typing`, `collections`, `itertools`, `copy` | structures de données |
| `threading`, `queue`, `traceback` | lecture et analyse en arrière-plan (REQ 4105) |
| `pathlib`, `os` | chemins portables, renommage atomique du PDF, chemins relatifs du projet |
| `uuid` | identifiants des fichiers et paquets |
| `textwrap` | mise en page des textes du PDF |
| `getpass` | nom de l'utilisateur (barre d'état, émetteur du rapport) |
| `platform`, `struct`, `sys`, `importlib` (`importlib.metadata`) | relevé de l'environnement (REQ 3004) |
| `subprocess`, `ctypes` | ouverture du PDF (xdg-open sous Linux), écran haute résolution sous Windows |

### 3 bis. Composants système

| Cible | Composant | Rôle |
|---|---|---|
| Windows 11 | Spyder 6 (interpréteur intégré) **ou** Python 3.11 64 bits de python.org avec l'option « tcl/tk and IDLE » | interpréteur + Tk 8.6 |
| SLES 15 SP7 | `python311`, `python311-tk` (module « Python 3 » de SLES), `python311-pip` | interpréteur, Tk 8.6, pip |
| SLES 15 SP7 | `glibc` ≥ 2.28 (2.38 fournie) | requis par les wheels manylinux de numpy, contourpy, pillow |
| SLES 15 SP7 | session graphique X11 (bureau ou `ssh -X`) ; `xdg-utils` (facultatif) | affichage ; ouverture du PDF généré |

## 4. Campagne de compatibilité exécutée (Linux x86-64)

Suite complète (`python -m unittest discover -s tests`, IHM réelle sous Xvfb incluse),
chaque ligne dans un environnement virtuel neuf :

<!-- RESULTATS_MATRICE -->
| Combinaison | Python | Tcl/Tk | numpy | matplotlib | Résultat | Remarque |
|---|---|---|---|---|---|---|
| py310-min-tk86 | 3.10.14 | 8.6.12 | 1.24.4 | 3.6.3 | 120 tests : OK, 12 tests IHM ignorés | IHM ignorée : Python « standalone » ancien, `_tkinter` intégré statiquement (artefact du banc de test, absent sous Windows / SLES) |
| py310-min-tk9 | 3.10.20 | 9.0.3 | 1.24.4 | 3.6.3 | 120 tests : OK, 12 tests IHM ignorés | IHM refusée au démarrage avec message clair : TkAgg de matplotlib 3.6 incompatible avec Tk 9 |
| py311-ref-tk86 | 3.11.9 | 8.6.12 | 2.4.6 | 3.10.9 | 120 tests : OK, 12 tests IHM ignorés | IHM ignorée : même artefact du banc de test (matplotlib le signale lui-même) |
| py311-ref-tk9 | 3.11.15 | 9.0.3 | 2.4.6 | 3.10.9 | 120 tests : OK |  |
| py311-old-tk86 | 3.11.9 | 8.6.12 | 1.26.4 | 3.8.4 | 120 tests : OK, 12 tests IHM ignorés | IHM ignorée : même artefact du banc de test |
| py311-mpl39-tk9 | 3.11.15 | 9.0.3 | 1.26.4 | 3.9.4 | 120 tests : OK, 12 tests IHM ignorés | IHM refusée au démarrage avec message clair : TkAgg de matplotlib 3.9 incompatible avec Tk 9 (matplotlib ≥ 3.10 requis) |
| py312-ref-tk86 | 3.12.3 | 8.6.14 | 2.4.6 | 3.10.9 | 120 tests : OK | Tk 8.6 « partagé » comme sous Windows (python.org, Spyder) et SLES |
| py313-ref-tk9 | 3.13.14 | 9.0.3 | 2.4.6 | 3.10.9 | 120 tests : OK |  |
| py314-ref-tk9 | 3.14.6 | 9.0.3 | 2.4.6 | 3.10.9 | 120 tests : OK |  |
| py312-latest-tk9 | 3.12.13 | 9.0.3 | 2.5.4 | 3.11.2 | 120 tests : OK |  |
| py314-latest-tk9 | 3.14.6 | 9.0.3 | 2.5.4 | 3.11.2 | 120 tests : OK |  |
| py312-old-tk86 | 3.12.3 | 8.6.14 | 1.26.4 | 3.8.4 | 120 tests : OK | Tk 8.6 « partagé » comme sous Windows (python.org, Spyder) et SLES |

Lecture : « 120 tests : OK » = lecture CSV, robustesse (fichiers abîmés), base de temps, curseurs, rendu, PDF, projet,
architecture **et** 12 tests de l'interface réelle (fenêtres Tk pilotées). Quand l'IHM est
ignorée, les 108 autres tests passent. La référence `requirements.txt` réussit intégralement
avec Tk 8.6 (famille Windows / Spyder / SLES) et Tk 9.0, de Python 3.11 à 3.14. Les
versions récentes (numpy 2.5.4, matplotlib 3.11.2) passent aussi : une future montée
sera sans modification du code.

Vérification de disponibilité des wheels binaires (installation simulée par `pip
install --dry-run --only-binary=:all:` avec les étiquettes de plateforme cibles) :
`requirements.txt` s'installe **sans compilation** pour Python 3.11, 3.12, 3.13 et 3.14,
en `win_amd64` (Windows 11) comme en `manylinux` x86-64 (SLES 15 SP7).

Les tests ont été exécutés sous Linux. L'exécution sous Windows 11 / Spyder 6 et sur le
Service Unit SLES 15 SP7 réel reste à consigner (procédure : COMPATIBILITE_OS.md § 5).

## 5. Montée de version : ce qui change et comment l'analyser

### 5.1 Effets connus d'une montée de Python

| Si l'on passe à… | numpy | matplotlib | Transitives | Code VISU PTBG |
|---|---|---|---|---|
| Python 3.12 ou 3.13 | inchangé (2.4.6) | inchangé (3.10.9) | inchangées | aucun changement (testé) |
| Python 3.14 | inchangé (2.4.6) | inchangé (3.10.9) | inchangées | aucun changement (testé) |
| Python 3.15 | **≥ 2.5.2** (premières wheels cp315) | **≥ 3.11.2** (3.10.x n'a pas de wheel cp315) | contourpy ≥ 1.4.0 ; pillow 12.3.0 convient ; vérifier kiwisolver et fonttools (§ 5.3, étape 2) | à requalifier (suite de tests) |
| Retour à Python 3.10 | **≤ 2.2.x** (numpy 2.3+ exige 3.11) | 3.10.9 possible | contourpy ≤ 1.3.2, fonttools ≤ 4.65 | code compatible (testé avec numpy 1.24) |

### 5.2 Effets connus d'une montée de bibliothèque

| Montée | Conséquence |
|---|---|
| numpy 2.5.x | **abandonne Python 3.11** (exige ≥ 3.12) : incompatible avec la référence 3.11 ; code VISU testé compatible avec 2.5.4 sous 3.12 et 3.14 |
| matplotlib 3.11.x | abandonne Python 3.10 ; code VISU testé compatible (3.11.2) |
| contourpy 1.4.x | exige Python ≥ 3.12 |
| fonttools ≥ 4.66 | exige Python ≥ 3.11 |
| pillow 13.x | exige Python ≥ 3.11 |
| python-dateutil 3.0.0 (octobre 2026) | **ajoute une nouvelle dépendance `tzdata`** : à évaluer avant adoption (non retenu) |
| numpy 1.x (environnement Spyder plus ancien) | code compatible à partir de numpy 1.24 (testé 1.24.4 et 1.26.4) |
| matplotlib 3.6 à 3.9 | traitements, rendu et PDF compatibles (testés) ; IHM validée avec Tk 8.6 ; **avec Tk 9.0, l'intégration TkAgg de matplotlib < 3.10 échoue** (« Failed to load Tcl_SetVar ») : l'outil le détecte au démarrage et affiche un message clair |
| pyparsing ≥ 3.3 avec un matplotlib ancien (< 3.9) | avertissements `PyparsingDeprecationWarning` émis par matplotlib (pas par VISU PTBG) ; sans effet fonctionnel |
| Tcl/Tk 9.0 (Python récents « standalone », certaines distributions) | exige **matplotlib ≥ 3.10** (testé 3.10.9 et 3.11.2) ; Windows python.org 3.11, Spyder et SLES 15 SP7 fournissent Tk 8.6 |

### 5.3 Procédure d'analyse d'impact (à suivre avant toute montée)

1. Lire les notes de version (sections « API changes », « deprecations », « dropped
   support ») de chaque paquet modifié ; consulter son champ *Requires-Python*.
2. Vérifier que des wheels existent pour **les deux** cibles :
   `python -m pip download --only-binary=:all: --platform win_amd64 --python-version 3.11 -r requirements.txt -d wheels_win`
   puis `--platform manylinux2014_x86_64 --platform manylinux_2_28_x86_64` pour SLES.
3. Créer un environnement virtuel neuf avec les nouvelles versions, puis lancer
   `python tools/audit_environnement.py` et `python -m unittest discover -s tests -v`
   (zéro échec, zéro test ignoré hors absence d'écran).
4. Faire l'essai interactif court (COMPATIBILITE_OS.md § 5) sur chaque cible.
5. Mettre à jour `requirements.txt`, ce document (§ 2, § 4, § 5), les plages
   `TESTED_RANGES` de `ptbg/system/environment.py` et `CHANGELOG.md`.

Au démarrage, l'outil relève les versions réellement présentes et signale dans le
journal toute bibliothèque différente de `requirements.txt` ou hors plage testée
(`ptbg/system/environment.py`) — utile sous Spyder dont l'environnement est figé.

## 6. Installation hors ligne (Service Unit sans accès Internet)

Sur un poste connecté (Windows ou Linux, même architecture x86-64) :

```
python -m pip download --only-binary=:all: --python-version 3.11 --implementation cp ^
    --platform manylinux2014_x86_64 --platform manylinux_2_17_x86_64 ^
    --platform manylinux_2_27_x86_64 --platform manylinux_2_28_x86_64 ^
    -r requirements.txt -d wheels_sles
```

(script prêt à l'emploi : `install/preparer_paquets_hors_ligne.sh`). Copier le dossier
`wheels_sles` avec les sources sur le Service Unit puis :
`install/installer_sles.sh --hors-ligne wheels_sles`.
