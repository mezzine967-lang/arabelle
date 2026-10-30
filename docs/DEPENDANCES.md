# Dépendances, versions et impacts de montée de version — REQ_COMMON_KH_3004

> « All additional packages or library implemented shall be documented and strictly
> aligned with the kernel version. » — le « kernel » est ici l'interpréteur Python
> (vocabulaire de Spyder : *kernel* de la console IPython).

Principe retenu : **le minimum de bibliothèques tierces**. L'outil n'utilise que la
bibliothèque standard de Python, **numpy** et **matplotlib**, toutes présentes dans
l'environnement de Spyder 6 : rien n'est à installer au poste Windows, et l'installation
SLES se limite à un environnement virtuel avec 11 wheels binaires (aucune compilation).

## En bref

| Question | Réponse | Section |
|---|---|---|
| Quel Python ? | **3.11** (référence) ; code prévu pour 3.10 à 3.14 ; 64 bits | § 1 |
| Quelles bibliothèques ? | numpy 2.4.6 et matplotlib 3.10.9 (directes) + 9 transitives de matplotlib, toutes figées dans `requirements.txt` | § 2 |
| Et la bibliothèque standard ? | liste complète des modules utilisés et de leur rôle | § 3 |
| Que faut-il tester ? | la suite de tests sur le poste Windows / Spyder et sur la VM Linux SLES 15 SP7 fournie par l'entreprise | § 4 |
| Que faire avant une montée de version ? | effets connus et procédure d'analyse d'impact en 5 étapes | § 5 |
| Installer sans Internet ? | wheels préparées sur un poste connecté | § 6 |
| Version tableur ? | `docs/recapitulatif/Dependances_versions_VISU_PTBG.xlsx` : lisez-moi, ce que l'outil utilise (avec le risque de chaque élément), ce qui se passe si on change une version, tests à réaliser, procédure de montée et relevé des postes à remplir | — |

## 1. Interpréteur Python

| Élément | Valeur |
|---|---|
| Version de référence (développement) | **Python 3.11** (Spyder 6 au poste Windows ; `python311` du module Python 3 de SLES 15 SP7) |
| Versions prévues | 3.10 à 3.14 (versions de Python acceptées par les bibliothèques figées) ; à confirmer par les tests (§ 4) |
| Version minimale acceptée par le code | 3.10 (`ptbg/version.py`, `MIN_PYTHON`) — contrôlée au lancement par `MAIN.py` |
| Architecture | 64 bits (Windows 11 x64 et SLES x86-64, les cibles du projet). Des wheels 32 bits existent pour certains paquets, mais ce mode n'est ni ciblé ni testé |
| Python 3.6 (REQ 3001) | Non retenu : fin de vie en décembre 2021, dernières versions compatibles numpy 1.19 / matplotlib 3.3 ; le relecteur indique qu'un Python 3.11 est disponible sur SLES 15. Question ouverte n° 3 du récapitulatif Excel (onglet « Points ouverts »). |

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
| `dataclasses`, `enum`, `typing`, `collections`, `itertools`, `copy` | structures de données ; `itertools` (`chain`, `repeat`) pour la lecture par blocs |
| `threading`, `queue`, `traceback` | lecture et analyse en arrière-plan (REQ 4105) |
| `pathlib`, `os` | chemins portables, renommage atomique du PDF, chemins relatifs du projet |
| `uuid` | identifiants des fichiers et paquets |
| `textwrap` | mise en page des textes du PDF |
| `getpass` | nom de l'utilisateur (barre d'état, émetteur du rapport) |
| `platform`, `struct`, `sys`, `importlib` (`importlib.metadata`) | relevé de l'environnement (REQ 3004) |
| `subprocess`, `ctypes` | ouverture du PDF (xdg-open sous Linux), écran haute résolution et mémoire du processus sous Windows |
| `resource` | mémoire maximale du processus sous Linux (banc de performance) ; module propre à Unix, importé seulement hors Windows (`system/compat.py`) |

### 3 bis. Composants système

| Cible | Composant | Rôle |
|---|---|---|
| Windows 11 | Spyder 6 (interpréteur intégré) **ou** Python 3.11 64 bits de python.org avec l'option « tcl/tk and IDLE » | interpréteur + Tk 8.6 |
| SLES 15 SP7 | `python311`, `python311-tk` (module « Python 3 » de SLES), `python311-pip` | interpréteur, Tk 8.6, pip |
| SLES 15 SP7 | `glibc` ≥ 2.28 (2.38 fournie) | requis par les wheels manylinux de numpy, contourpy, pillow |
| SLES 15 SP7 | session graphique X11 (bureau ou `ssh -X`) ; `xdg-utils` (facultatif) | affichage ; ouverture du PDF généré |

## 4. Tests à réaliser

La suite complète (`python -m unittest discover -s tests -v`, 145 tests, interface comprise)
est à lancer sur chaque poste, puis la fiche d'essai de COMPATIBILITE_OS.md § 5.

| Poste | Python | Tcl/Tk | numpy | matplotlib | État |
|---|---|---|---|---|---|
| Windows 11 / Spyder 6 (relevé du 30/10/2026) | 3.11.10 | 8.6.13 | 2.2.0 | 3.9.3 | outil lancé, CSV du projet ouvert ; tests lancés le 30/10/2026 depuis la console Spyder : 145 tests, 144 OK ; le seul en erreur cherchait le Word de la spécification, absent du dossier (corrigé depuis : ce test est sauté sans le Word) |
| VM Linux SLES 15 SP7 fournie par l'entreprise | 3.11 (`python311`) | 8.6 (`python311-tk`) | 2.4.6 | 3.10.9 | à faire après installation (`install/installer_sles.sh`) |

Versions de l'environnement Spyder du poste (relevé Information > Sources) : contourpy 1.3.1,
cycler 0.12.1, fonttools 4.55.2, kiwisolver 1.4.7, packaging 24.2, pillow 11.0.0,
pyparsing 3.2.0, python-dateutil 2.9.0.post0, six 1.17.0. Elles diffèrent de
`requirements.txt` pour 8 paquets ; les tests passent avec ces versions (ci-dessus).

Disponibilité des wheels binaires : des wheels de chaque version figée existent pour
Python 3.11 à 3.14, en `win_amd64` (Windows 11) et en `manylinux` x86-64 (SLES 15 SP7) ;
à contrôler avec `pip download --only-binary=:all:` (§ 5.3, étape 2).

## 5. Montée de version : ce qui change et comment l'analyser

### 5.1 Effets connus d'une montée de Python

| Si l'on passe à… | numpy | matplotlib | Transitives | Code VISU PTBG |
|---|---|---|---|---|
| Python 3.12 ou 3.13 | inchangé (2.4.6) | inchangé (3.10.9) | inchangées | aucun changement prévu (à confirmer par les tests) |
| Python 3.14 | inchangé (2.4.6) | inchangé (3.10.9) | inchangées | aucun changement prévu (à confirmer par les tests) |
| Python 3.15 | **≥ 2.5.2** (premières wheels cp315) | **≥ 3.11.2** (3.10.x n'a pas de wheel cp315) | contourpy ≥ 1.4.0 ; pillow 12.3.0 convient ; vérifier kiwisolver et fonttools (§ 5.3, étape 2) | à requalifier (suite de tests) |
| Retour à Python 3.10 | **≤ 2.2.x** (numpy 2.3+ exige 3.11) | 3.10.9 possible | contourpy ≤ 1.3.2, fonttools ≤ 4.65 | code écrit pour numpy ≥ 1.24 (à confirmer par les tests) |

### 5.2 Effets connus d'une montée de bibliothèque

| Montée | Conséquence |
|---|---|
| numpy 2.5.x | **abandonne Python 3.11** (exige ≥ 3.12) : incompatible avec la référence 3.11 ; à tester si l'on passe à Python 3.12 ou plus |
| matplotlib 3.11.x | abandonne Python 3.10 ; à tester avant adoption |
| contourpy 1.4.x | exige Python ≥ 3.12 |
| fonttools ≥ 4.66 | exige Python ≥ 3.11 |
| pillow 13.x | exige Python ≥ 3.11 |
| python-dateutil 3.0.0 (octobre 2026) | **ajoute une nouvelle dépendance `tzdata`** : à évaluer avant adoption (non retenu) |
| numpy 1.x (environnement Spyder plus ancien) | code écrit pour numpy ≥ 1.24 ; à tester |
| matplotlib 3.6 à 3.9 | traitements, rendu et PDF prévus pour fonctionner (le poste Spyder a matplotlib 3.9.3 et Tk 8.6 : l'outil s'y lance) ; **avec Tk 9.0, l'intégration TkAgg de matplotlib < 3.10 échoue** (« Failed to load Tcl_SetVar ») : l'outil le détecte au démarrage et affiche un message clair |
| pyparsing ≥ 3.3 avec un matplotlib ancien (< 3.9) | avertissements `PyparsingDeprecationWarning` émis par matplotlib (pas par VISU PTBG) ; sans effet fonctionnel |
| Tcl/Tk 9.0 (Python récents « standalone », certaines distributions) | exige **matplotlib ≥ 3.10** ; Windows python.org 3.11, Spyder et SLES 15 SP7 fournissent Tk 8.6 |

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
