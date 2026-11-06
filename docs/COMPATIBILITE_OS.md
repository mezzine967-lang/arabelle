# Compatibilité Windows 11 / Windows Server 2025 — REQ_COMMON_KH_3000 et 3005

Cibles (décision du relecteur, 06/11/2026 : plus de double compatibilité, Linux abandonné) :

- **Windows 11 64 bits** : poste bureautique individuel (développement sous **Spyder 6**) ;
- **Windows Server 2025** : VM partagée du lab, utilisée en **Bureau à distance (RDP)** via
  la jumpbox d'accès au lab. L'utilisateur ne voit pas de différence avec son poste ; il
  peut rapatrier ses données sur son PC par RDP ; les données peuvent rester sur la VM,
  qui est sauvegardée.

L'énoncé du REQ 3000 demande encore SLES 15 SP7 : il est à mettre à jour (point ouvert
n° 4). Aucun exécutable n'est produit pour l'instant : l'outil s'exécute depuis ses sources
Python (l'environnement Spyder étant figé, ce mode est le seul possible au poste).

| Section | Contenu |
|---|---|
| § 1 | où sont isolées les différences entre systèmes, sujet par sujet |
| § 1 bis | ce qui change sur la VM Windows Server 2025 en Bureau à distance |
| § 2 | comment lancer l'outil |
| § 3 | installation hors Spyder (en ligne ou hors ligne) |
| § 4 | ce qui reste à vérifier, et où (poste Windows 11, VM Windows Server 2025) |
| § 5 | **fiche d'essai de réception** à remplir sur chaque poste cible |

## 1. Principe : un seul code, les différences isolées

Tout ce qui dépend du système est regroupé dans **`ptbg/system/compat.py`**. Aucun autre
module ne teste le système d'exploitation (contrôle automatique :
`tests/test_architecture.py::test_os_specific_code_is_centralized`). Le code reste écrit
de façon portable (chemins `pathlib`, aucun chemin codé en dur), sans viser d'autre
système que Windows.

| Sujet | Windows 11 et Windows Server 2025 | Mécanisme |
|---|---|---|
| Interpréteur | Spyder 6 (Python intégré) ou python.org 3.11 x64 | même code ; version vérifiée par `MAIN.py` |
| Interface graphique | Tk 8.6 fourni avec Python | Tkinter (bibliothèque standard) ; Tk 9 également pris en charge (exige matplotlib ≥ 3.10) ; compatibilité matplotlib / Tk vérifiée au démarrage (`tkagg_problem`) |
| Bibliothèques | celles de Spyder (rien à installer) ou `requirements.txt` | mêmes fichiers d'installation (win_amd64) pour les deux ; versions relevées au démarrage |
| Chemins | `C:\...`, lecteurs, chemins réseau | `pathlib` partout ; aucun séparateur codé en dur |
| Chemins du projet | — | stockés relatifs au fichier projet avec « / » : un projet se rouvre d'un poste à l'autre (`core/project.py`) |
| Préférences | `%APPDATA%\VISU_PTBG\settings.json` | `user_config_dir()` |
| Journaux | `%LOCALAPPDATA%\VISU_PTBG\journal_AAAAMMJJ.log` | `user_state_dir()` ; dossier des sources jamais écrit (peut être en lecture seule) |
| Utilisateur | `USERNAME` | `getpass.getuser()` avec repli « inconnu » |
| Écran haute résolution | mise à l'échelle 125 / 150 % | `enable_high_dpi()` avant la création de la fenêtre |
| Ouverture du PDF | `os.startfile` (lecteur PDF par défaut) | `open_with_default_application()` ; un échec est journalisé, jamais bloquant |
| Encodage des CSV | UTF-8 attendu (REQ 2302) | décodage explicite UTF-8 (BOM toléré), jamais l'encodage local du système ; un fichier Windows-1252 ou UTF-16 est lu mais marqué en ERREUR (non-conformité citée avec sa ligne) |
| Fins de ligne CSV | CRLF (ou LF selon l'origine du fichier) | flux texte avec `newline=None` : CRLF, LF et CR acceptés, même mélangés dans un fichier |
| Mémoire du processus (banc de performance) | `GetProcessMemoryInfo` (psapi, via `ctypes`) | `process_memory_mb()` ; renvoie « inconnue » plutôt qu'une erreur |
| Polices des graphiques | — | DejaVu Sans, fournie avec matplotlib : rendu et PDF identiques sur tous les postes |
| Caractères spéciaux de l'IHM | — | icônes dessinées pixel par pixel ; aucun émoji |
| Travail en arrière-plan | `multiprocessing` peu fiable sous Spyder | fils `threading` + file `queue` (`gui/tasks.py`) |
| Backend Matplotlib | Spyder impose souvent « inline » ou Qt | aucun `pyplot` ni `matplotlib.use()` : figures intégrées directement par `FigureCanvasTkAgg` |
| Fermeture | — | arrêt propre des minuteries Tk et du dessin différé (aucune erreur « invalid command name ») |

## 1 bis. VM Windows Server 2025 en Bureau à distance

Windows Server 2025 et Windows 11 ont le même noyau (build 26100) : l'outil y prend
exactement les mêmes chemins de code Windows, avec les mêmes fichiers d'installation des
bibliothèques (win_amd64). Points propres à une VM partagée :

| Sujet | Sur la VM | Ce que fait l'outil |
|---|---|---|
| Plusieurs utilisateurs en même temps | une session RDP par personne | préférences et journaux dans le profil de chaque utilisateur (`%APPDATA%`, `%LOCALAPPDATA%`) : pas de mélange ; le dossier de l'outil peut être partagé en lecture seule (il n'y est jamais rien écrit) |
| Affichage | la mise à l'échelle suit celle du poste client (100 %, 125 %, 150 %…) | `enable_high_dpi()` : texte net, comme sur le poste |
| Fichiers | CSV et rapports sur la VM (sauvegardée), ou copiés vers le PC par RDP | chemins Windows, lecteurs et chemins réseau acceptés |
| Ouverture du PDF | lecteur PDF par défaut de la VM | si aucun n'est installé, l'échec est noté dans le journal et le PDF reste enregistré |
| Installation | pas forcément d'accès Internet depuis le lab | Python 3.11 de python.org (option « tcl/tk and IDLE ») puis `install\installer_windows.bat` ; hors ligne : fichiers d'installation préparés sur un poste connecté (DEPENDANCES.md § 6, plate-forme win_amd64) |
| Nom du système | — | Information > Sources affiche « Windows Server 2025 » (Python 3.11 renvoie « post2022Server », corrigé d'après le numéro de build) |

À vérifier sur la VM : que Spyder 6 s'y installe si on veut l'utiliser (sinon Python
3.11 suffit), le lecteur PDF par défaut, et l'essai du § 5 en Bureau à distance.

## 2. Lancement

| Cible | Commande |
|---|---|
| Windows 11, Spyder 6 | ouvrir `MAIN.py`, **Exécuter (F5)** ; conseillé : *Exécuter > Configuration par fichier > Exécuter dans une console dédiée* |
| Windows 11 ou VM Windows Server 2025, sans Spyder | `install\installer_windows.bat` une fois, puis `install\lancer_windows.bat` |
| Toute cible, terminal | `python MAIN.py [fichiers.csv ...]` |

Remarques Spyder 6 :
- la fenêtre Tk bloque la console tant qu'elle est ouverte (comportement normal) ;
- le dossier des sources est ajouté automatiquement au chemin d'import par `MAIN.py`,
  quel que soit le répertoire de travail de Spyder ;
- si numpy ou matplotlib étaient absents de l'environnement Spyder, `MAIN.py` l'indique
  clairement au lieu d'échouer (rien n'est installé automatiquement).

## 3. Installation hors Spyder

```
Python 3.11 64 bits de python.org, option « tcl/tk and IDLE » cochée
install\installer_windows.bat      (crée .venv et installe requirements.txt)
install\lancer_windows.bat
```

Sans Internet (cas possible du lab) : préparer les fichiers d'installation sur un poste
connecté, les copier sur la VM avec les sources (Bureau à distance), puis les installer :
voir DEPENDANCES.md § 6.

## 4. Qualification à faire

| Poste | Ce qui est déjà constaté | Ce qui reste à faire |
|---|---|---|
| Windows 11 / Spyder 6 (poste de l'alternance) | l'outil se lance et ouvre un CSV du projet (relevé Information > Sources du 30/10/2026 : Python 3.11.10, Tk 8.6.13, numpy 2.2.0, matplotlib 3.9.3) ; tests de la version 1.0.0 lancés le 30/10/2026 depuis la console Spyder : 145 tests, 144 OK ; le seul en erreur demandait un fichier de référence absent du dossier (corrigé depuis : ce contrôle est sauté sans lui) | relancer les tests avec cette version (`import sys`, `%cd <dossier de l'outil>`, puis `!"{sys.executable}" -m unittest discover -s tests -v` ; attendu : « OK », avec « skipped=1 » : un contrôle de traçabilité est sauté), puis la fiche d'essai du § 5 |
| VM Windows Server 2025 (Bureau à distance) | — | installer (§ 3), lancer les tests (`python -m unittest discover -s tests -v`), puis la fiche d'essai du § 5 en Bureau à distance |

Des fichiers d'installation (wheels win_amd64) de chaque bibliothèque figée existent pour
Windows 11 et Windows Server 2025 (les mêmes) ; leur disponibilité se contrôle avec la
commande de DEPENDANCES.md § 5.3, étape 2.

## 5. Essai de réception à consigner sur chaque cible (≈ 15 minutes)

À imprimer ou recopier : une fiche par poste (Windows 11 / Spyder 6, VM Windows Server 2025).

| # | Action | Résultat attendu | OK ? / remarque |
|---|---|---|---|
| 1 | Lancer l'outil (§ 2) | barre d'état : utilisateur, date, version ; versions de Python, Tk, numpy, matplotlib dans Information > Sources | |
| 2 | Information > Sources | tableau des bibliothèques, statut OK ; le relever | |
| 3 | Fichier > Ouvrir un dossier de CSV > `data/demo/` | 4 fichiers ; `non_conforme_point_virgule.csv` en ERREUR (séparateur) sans bloquer les autres | |
| 4 | Afficher P_circuit_bar (PLC A) et P_mesure_B (PLC B) ; double curseur (glissé), curseur global | curseurs posés, panneau de lecture rempli (instant, valeur, ligne CSV) | |
| 5 | Bouton « Masquer le TBM » | refusé : PLC_B a des avertissements | |
| 6 | Rapport > Rapport automatique | PDF ouvert : en-tête, TBM, page de traçabilité | |
| 7 | Enregistrer le projet, fermer, le rouvrir | onglets et curseurs retrouvés | |
| 8 | Sur la VM : refaire les étapes 3 à 6 en Bureau à distance, depuis un poste à 100 % puis à 150 % d'affichage | même comportement, textes nets ; deux utilisateurs connectés en même temps gardent chacun leurs préférences | |
| 9 | `python -m unittest discover -s tests -v` puis `python tools/audit_environnement.py` | aucun échec ; archiver les deux sorties | |
| 10 | Performances (REQ 2310, 4105) : `python tools/banc_performance.py` sur les plus gros vrais fichiers PTBG, puis `--generer 500` (fichier de synthèse de 500 Mo) | durées, débit et mémoire archivés ; la taille maximale retenue laisse une marge de mémoire sur le poste | |
