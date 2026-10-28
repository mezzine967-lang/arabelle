# VISU PTBG 2.3.0 — analyseur graphique de perturbographie

Outil Python d'analyse des fichiers CSV de **perturbographie (PTBG)** produits par les PLC
Framatome TXS Compact (projet NPI-NCS), conforme à la spécification
**NCS/00/I/COMMON----/ES/010 Rev. A** (`docs/specification/`).

Il lit un ou plusieurs CSV (un par PLC), **contrôle la base de temps** de chacun
(période, stabilité, croissance continue, trous, déphasage, changements de fréquence),
l'affiche dans un **Time Base Monitor**, et offre l'analyse graphique des signaux Bool,
Float et groupes binaires : onglets à modèles de disposition, curseurs simple / double /
global / horizontal conditionné / X/Y, traitement conditionnel, rapports **PDF**
automatique et pas à pas.

![Fenêtre principale](docs/captures/01_vue_principale.png)

## Démarrer

| Poste | Démarrage |
|---|---|
| **Windows 11 + Spyder 6** | ouvrir `MAIN.py` puis **F5**. Rien à installer : numpy et matplotlib de Spyder suffisent |
| **SLES 15 SP7** | `sudo zypper install python311 python311-tk python311-pip`, puis `install/installer_sles.sh` (une fois) et `install/lancer_sles.sh` |
| Windows sans Spyder | Python 3.11 64 bits (python.org, avec Tcl/Tk), puis `install\installer_windows.bat` et `install\lancer_windows.bat` |
| Terminal | `python MAIN.py [fichiers.csv ...]` |

Pour essayer : ouvrir le dossier `data/demo/` (Fichier > Ouvrir un dossier de CSV) :
trois PLC (10 ms avec pré-déclenchement, 20 ms déphasé, horodatage hh:mm:ss.ns) et un
fichier non conforme. Les CSV reçus sont dans `data/exemples/`.

Exemple de rapport PDF produit par l'outil : [docs/exemples/rapport_exemple_demo.pdf](docs/exemples/rapport_exemple_demo.pdf).
Autres captures : [nuage X/Y](docs/captures/02_nuage_xy.png),
[diagnostic d'un fichier](docs/captures/03_diagnostic.png),
[configuration de la base de temps](docs/captures/04_configuration_base_de_temps.png),
[axe absolu passant minuit](docs/captures/05_axe_absolu_minuit.png).

Mode d'emploi complet : **[docs/GUIDE_UTILISATEUR.md](docs/GUIDE_UTILISATEUR.md)**
(aussi dans l'outil : Information > Fichier d'aide, F1).

## Dépendances

Python **3.11** (référence ; vérifié de 3.10 à 3.14), Tkinter (fourni avec Python),
**numpy** et **matplotlib** — rien d'autre. Versions figées dans `requirements.txt`,
identiques pour Windows et SLES de Python 3.11 à 3.14. Inventaire complet, licences,
versions de Python supportées et **impact d'une montée de version** :
[docs/DEPENDANCES.md](docs/DEPENDANCES.md). Compatibilité entre systèmes :
[docs/COMPATIBILITE_OS.md](docs/COMPATIBILITE_OS.md).

Contrôler un poste : `python tools/audit_environnement.py` (versions présentes / figées).
Mesurer les performances sur de vrais fichiers PTBG : `python tools/banc_performance.py fichiers.csv`
(ou `--generer 500` pour un fichier de synthèse de 500 Mo).

## Organisation du code

```
MAIN.py            construit l'interface, rien d'autre (REQ 3002)
ptbg/core/         traitements sans interface : CSV, base de temps, curseurs, X/Y…
ptbg/plotting/     dessin commun écran et PDF, Time Base Monitor
ptbg/report/       rapport PDF
ptbg/gui/          interface Tkinter : contrôleur, arbre, onglets, dialogues
ptbg/system/       compatibilité Windows / SLES, environnement, journal
tests/             132 tests automatisés (dont l'interface réelle et la robustesse)
tools/             audit d'environnement, banc de performance, traçabilité, données de démo
install/           installation et lancement Windows / SLES
docs/              guide, architecture, dépendances, compatibilité, traçabilité
```

Pour reprendre le code : **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Requis

Les 64 lignes de la spécification sont tracées dans
**[docs/TRACABILITE_REQUIS.md](docs/TRACABILITE_REQUIS.md)** (réalisation, code, test,
statut) : 47 implémentées et testées, 14 implémentées selon une interprétation à valider,
1 proposition (énoncé vide), 2 à qualifier sur cible ou sur volumes réels. Les
interprétations à faire valider sont dans **[docs/POINTS_OUVERTS.md](docs/POINTS_OUVERTS.md)**.
Récapitulatif Excel (requis, réalisation, programmes, tests, commentaires de la relecture) :
[docs/recapitulatif/](docs/recapitulatif/Recapitulatif_requis_VISU_PTBG.xlsx).

Robustesse : un fichier abîmé (ligne tronquée ou en trop, guillemet non fermé, octets
nuls, en-tête absent ou répété, encodage non UTF-8, horodatage aberrant…) est lu sans
exception, sans perte silencieuse ni valeur inventée ; chaque anomalie est citée avec sa
ligne (guide, § 2 ; `tests/test_robustesse.py`).

Performances (banc Linux, Python 3.11) : 1 million de lignes × 21 colonnes (115 à 157 Mo)
lues et analysées en 5 à 7 s, en arrière-plan ; curseurs fluides (moins de 30 ms par
mouvement) sur des courbes d'un million de points. Détail : [CHANGELOG.md](CHANGELOG.md).

```
python tools/verifier_tracabilite.py     # chaque requis du Word : matrice + code + test
```

## Tests

```
python -m unittest discover -s tests -v
```

Les tests d'interface ouvrent de vraies fenêtres ; ils sont ignorés sans écran (sous
Linux sans bureau : `xvfb-run python -m unittest discover -s tests`).

## Historique

[CHANGELOG.md](CHANGELOG.md). La version 2.0.0 remplace le prototype 1.0.0, archivé
dans `archive/`.
