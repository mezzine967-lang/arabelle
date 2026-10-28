# Compatibilité Windows 11 / SLES 15 SP7 — REQ_COMMON_KH_3000 et 3005

Cibles : **SUSE Linux Enterprise Server 15 SP7** (Service Unit de perturbographie) et
**Windows 11 64 bits** (postes de bureau, développement sous **Spyder 6**). Aucun
exécutable n'est produit : l'outil s'exécute depuis ses sources Python, identiques sur
les deux systèmes (l'environnement Spyder étant figé, ce mode est le seul possible au poste).

## 1. Principe : un seul code, les différences isolées

Toutes les différences entre systèmes sont regroupées dans **`ptbg/system/compat.py`**.
Aucun autre module ne teste le système d'exploitation (contrôle automatique :
`tests/test_architecture.py::test_os_specific_code_is_centralized`).

| Sujet | Windows 11 | SLES 15 SP7 | Mécanisme |
|---|---|---|---|
| Interpréteur | Spyder 6 (Python intégré) ou python.org 3.11 x64 | `python311` (module Python 3) | même code ; version vérifiée par `MAIN.py` |
| Interface graphique | Tk 8.6 fourni avec Python | `python311-tk` (Tk 8.6) | Tkinter (bibliothèque standard) ; Tk 9 également testé (exige matplotlib ≥ 3.10) ; compatibilité matplotlib / Tk vérifiée au démarrage (`tkagg_problem`) |
| Bibliothèques | celles de Spyder (rien à installer) ou `requirements.txt` | `requirements.txt` dans un venv (en ligne ou hors ligne) | mêmes wheels (win_amd64 / manylinux) ; versions relevées au démarrage |
| Chemins | `C:\...`, lecteurs, UNC | `/home/...` | `pathlib` partout ; aucun séparateur codé en dur |
| Chemins du projet | — | — | stockés relatifs au fichier projet avec « / » : un projet Windows se rouvre sous SLES (`core/project.py`) |
| Préférences | `%APPDATA%\VISU_PTBG\settings.json` | `~/.config/visu_ptbg/settings.json` | `user_config_dir()` |
| Journaux | `%LOCALAPPDATA%\VISU_PTBG\journal_AAAAMMJJ.log` | `~/.local/state/visu_ptbg/journal_AAAAMMJJ.log` | `user_state_dir()` ; dossier des sources jamais écrit (peut être en lecture seule) |
| Utilisateur | `USERNAME` | `LOGNAME` / `USER` | `getpass.getuser()` avec repli « inconnu » |
| Écran haute résolution | mise à l'échelle 125 / 150 % | résolution du serveur X | `enable_high_dpi()` (Windows) avant la création de la fenêtre |
| Absence d'écran | — | lancement sans session graphique | `display_problem()` : message clair (DISPLAY vide, utiliser le bureau ou `ssh -X`) |
| Ouverture du PDF | `os.startfile` | `xdg-open` | `open_with_default_application()` ; un échec est journalisé, jamais bloquant |
| Encodage des CSV | UTF-8 attendu (REQ 2302) | idem | décodage explicite UTF-8 (BOM toléré), jamais l'encodage local du système ; un fichier Windows-1252 ou UTF-16 est lu mais marqué en ERREUR (non-conformité citée avec sa ligne) |
| Fins de ligne CSV | CRLF | LF | flux texte avec `newline=None` : CRLF, LF et CR acceptés, même mélangés dans un fichier |
| Mémoire du processus (banc de performance) | `GetProcessMemoryInfo` (psapi, via `ctypes`) | `/proc/self/statm` et `resource.getrusage` | `process_memory_mb()` ; renvoie « inconnue » plutôt qu'une erreur |
| Polices des graphiques | — | — | DejaVu Sans, fournie avec matplotlib : rendu et PDF identiques |
| Caractères spéciaux de l'IHM | — | Tk 8.6 sous X11 ne gère pas les émojis | icônes dessinées pixel par pixel ; aucun émoji |
| Travail en arrière-plan | `multiprocessing` peu fiable sous Spyder | — | fils `threading` + file `queue` (`gui/tasks.py`) |
| Backend Matplotlib | Spyder impose souvent « inline » ou Qt | — | aucun `pyplot` ni `matplotlib.use()` : figures intégrées directement par `FigureCanvasTkAgg` |
| Fermeture | — | — | arrêt propre des minuteries Tk et du dessin différé (aucune erreur « invalid command name ») |

## 2. Lancement

| Cible | Commande |
|---|---|
| Windows 11, Spyder 6 | ouvrir `MAIN.py`, **Exécuter (F5)** ; conseillé : *Exécuter > Configuration par fichier > Exécuter dans une console dédiée* |
| Windows 11, sans Spyder | `install\installer_windows.bat` une fois, puis `install\lancer_windows.bat` |
| SLES 15 SP7 | `install/installer_sles.sh` une fois, puis `install/lancer_sles.sh [fichiers.csv]` |
| Toute cible, terminal | `python MAIN.py [fichiers.csv ...]` |

Remarques Spyder 6 :
- la fenêtre Tk bloque la console tant qu'elle est ouverte (comportement normal) ;
- le dossier des sources est ajouté automatiquement au chemin d'import par `MAIN.py`,
  quel que soit le répertoire de travail de Spyder ;
- si numpy ou matplotlib étaient absents de l'environnement Spyder, `MAIN.py` l'indique
  clairement au lieu d'échouer (rien n'est installé automatiquement).

## 3. Installation sur SLES 15 SP7

```
sudo zypper install python311 python311-tk python311-pip   # module « Python 3 » de SLES
install/installer_sles.sh                                   # crée .venv et installe requirements.txt
install/lancer_sles.sh
```

Hors ligne : préparer les wheels sur un poste connecté (`install/preparer_paquets_hors_ligne.sh`,
voir DEPENDANCES.md § 6) puis `install/installer_sles.sh --hors-ligne wheels_sles`.

Prérequis vérifiés pour SP7 : glibc 2.38 (les wheels exigent ≥ 2.28), Python 3.11 et
Tk disponibles dans le module Python 3 de SLES. Une version antérieure de SLES 15
(SP3 et avant, glibc 2.26) ne permettrait pas d'installer numpy 2.x en wheel.

## 4. Qualification réalisée ici

Linux x86-64, Python 3.10 à 3.14, Tk 8.6.14 et Tk 9.0.3, plusieurs versions de numpy et
matplotlib : voir DEPENDANCES.md § 4. Les wheels Windows (win_amd64) et SLES (manylinux)
de chaque Python 3.11 à 3.14 ont été vérifiées disponibles.

## 5. Essai de réception à consigner sur chaque cible (≈ 15 minutes)

1. Lancer l'outil (§ 2) ; vérifier dans la barre d'état l'utilisateur, la date, la
   version et le message de démarrage (versions de Python, Tk, numpy, matplotlib).
2. Information > Sources : relever le tableau des bibliothèques (statut OK attendu).
3. Ouvrir le dossier `data/demo/` : 4 fichiers, dont `non_conforme_point_virgule.csv` en
   ERREUR (séparateur) sans bloquer les autres.
4. Afficher P_circuit_bar (PLC A) et P_mesure_B (PLC B) ; poser un double curseur, un
   curseur global, activer le suivi souris ; vérifier le panneau de lecture.
5. Tenter de masquer le TBM (refus attendu : PLC_B a des avertissements).
6. Rapport > Rapport automatique : contrôler en-tête, TBM et page de traçabilité.
7. Enregistrer le projet, fermer, le rouvrir ; vérifier onglets et curseurs.
8. Sous SLES : refaire l'essai via `ssh -X` si le Service Unit est utilisé à distance.
9. Lancer `python -m unittest discover -s tests -v` (aucun échec attendu) et archiver
   la sortie avec celle de `python tools/audit_environnement.py`.
10. Performances (REQ 2310, 4105) : `python tools/banc_performance.py` sur quelques vrais
    fichiers PTBG (les plus gros disponibles), puis `python tools/banc_performance.py
    --generer 500` (fichier de synthèse de 500 Mo) ; archiver la sortie (durées, débit,
    mémoire). La taille maximale retenue doit laisser une marge de mémoire sur le poste.
