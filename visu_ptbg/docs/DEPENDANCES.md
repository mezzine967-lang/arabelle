# Dépendances et compatibilité — v0.9.0

## Ajouts v0.9.0

Aucun package externe ajouté, aucune installation automatique.

| Composant | Utilisation nouvelle | Provenance |
|---|---|---|
| tkinter / ttk | Onglets, panneaux, scrollbars, dialogues, after pour les résultats | Python et runtime Tcl/Tk du poste |
| threading, queue | Travail de fond, annulation, publication dans le fil graphique | Bibliothèque standard Python |
| bisect, math | Consultation des timestamps réels, valeurs finies | Bibliothèque standard Python |
| io, dataclasses, datetime, pathlib, textwrap | Captures, métadonnées, chemins, texte | Bibliothèque standard Python |
| unittest, tempfile, hashlib | Résultats de tests structurés, fichiers temporaires, empreintes par blocs | Bibliothèque standard Python |
| Matplotlib | Curseurs, nuage X/Y, PNG en mémoire, PdfPages pour les rapports | Package existant, 3.10.8 observé ici |
| Pillow / NumPy | Lecture/rendu d'images utilisé par Matplotlib | Dépendances déjà présentes de Matplotlib |

Les versions exactes et contraintes transitives observées sont archivées dans
`environnement_linux_v090.json`. Le runtime de test est Python 3.12/Linux ;
syntaxe contrôlée pour Python 3.11, sans prétendre avoir testé ce runtime ici.
La cible reste Windows 11 x64 et SLES 15 SP7 x86-64. « Python 3.6 at least »
ne signifie pas à lui seul que toutes les versions depuis 3.6 doivent être
supportées : la version réellement autorisée sur SLES doit être confirmée.
Le code actuel requiert Python 3.11 comme cible de projet, pas Python 3.6.

PDF : Matplotlib PdfPages (backend intégré), captures à 180 dpi. Les en-têtes
sont du texte sélectionnable ; les graphiques sont des images figées.
Les pages sont A4 paysage (une vue), 16,5 × 8,3 pouces (deux vues côte à côte)
ou A3 portrait (deux superposées). Aucun reportlab/pypdf requis à l'exécution.
`pypdf` et Poppler sont utilisés uniquement pour la vérification de livraison.

Documentation officielle consultée :
https://matplotlib.org/stable/api/backend_pdf_api.html
https://matplotlib.org/stable/api/_as_gen/matplotlib.figure.Figure.savefig.html

Le travail de fond ne touche jamais Tkinter ni Matplotlib. Les callbacks Tk
appliquent les résultats, le tracé et le PDF restent dans le fil graphique.
L'annulation est coopérative entre fichiers et invalide le résultat à réception.
Les chemins d'aide sont relatifs à `MAIN.py`, sans commande Windows/Linux.

## Historique des versions précédentes

Version 0.8.0 : aucun package ajouté ou mis à jour. Le parseur d'heures utilise
`re.fullmatch` (validation stricte du format) et `decimal.Decimal` (secondes
exactes jusqu'aux nanosecondes), tous deux de la bibliothèque standard Python.
Les tracés réutilisent Matplotlib et Tkinter. Les versions de l'environnement
de livraison restent à qualifier sur Windows 11 et SLES 15 SP7.

`emplacements.py` utilise os/sys/pathlib (bibliothèque standard) pour les
journaux automatiques dans LOCALAPPDATA (Windows) ou XDG_STATE_HOME (Linux).
Le relevé au lancement n'est plus écrit à côté du programme. Le chemin exact
est affiché dans la console ; les erreurs de permission sont interceptées par
MAIN. Les anciens relevés sont conservés à leur emplacement historique.

La v0.7.9 utilise Tkinter et Matplotlib déjà documentés ci-dessous pour masquer
ou réafficher l'axe. Aucune bibliothèque ou dépendance externe supplémentaire.

## Modification v0.7.8 (requis 3004)

Aucune installation, mise à jour ou nouvelle dépendance externe. Le dessin
réutilise Matplotlib (Figure, axes, symboles, légendes) et son intégration
TkAgg existante. `collections.Counter` compte les catégories pour le résumé ;
`textwrap.fill` adapte les textes à la largeur. Ces deux modules sont fournis
avec Python, sans paquet pip à installer. Les calculs temporels sont inchangés.

Le relevé `environnement_linux_v078.json` archive Python, OS, Tcl/Tk lorsqu'ils
sont observables et les versions/métadonnées des packages installés :
Matplotlib, NumPy, contourpy, cycler, fonttools, kiwisolver, packaging, Pillow,
pyparsing, python-dateutil et six. Les exigences transitives sont incluses dans
le relevé existant. La qualification Windows 11 x64 et SLES 15 SP7 reste ouverte.

La v0.7.7 réutilise les catégories du moteur temporel dans le graphique. Elle
n'ajoute aucune bibliothèque ni aucun comportement propre à Windows ou Linux.

La v0.7.6 réutilise Matplotlib pour le moniteur quantitatif et n'ajoute aucune
dépendance. La version du programme est centralisée dans `src/version_visu.py`.

La v0.7.5 ajoute le moteur du Lot 2A avec seulement des modules de la
bibliothèque standard Python 3.11. Aucun paquet externe supplémentaire n'est
nécessaire. La décision Windows de Sébastien et la procédure de qualification
sont détaillées dans `CIBLE_WINDOWS_11.md`.

La v0.7.4 impose la première colonne comme temps sans ajouter de dépendance.

La v0.7.3 modifie le tracé des manques avec les bibliothèques déjà utilisées.
Aucune dépendance supplémentaire. Les limites de qualification restent les mêmes.

La v0.7.0 ajoute uniquement des modules locaux pour inspecter les intervalles et
signaler les absences. Elle réutilise tkinter et Matplotlib : aucune nouvelle
bibliothèque n'est nécessaire. Les calculs exacts utilisent decimal et
collections de la bibliothèque standard. Le tableau fonctionne sans Matplotlib.
La v0.7.1 parcourt les lignes et calcule le SHA-256 des CSV par blocs ; les
enregistrements de `read_csv` restent conservés en mémoire sous la limite
provisoire de 50 MiB par fichier. L'import d'un dossier est encore synchrone.

Poste de développement de Mourad : Windows, Python 3.11, interpréteur 64 bits.
La cible de livraison confirmée est double : Windows et SLES 15 SP7.
L'édition Windows de livraison et l'environnement Python/Tcl/Tk/Matplotlib
autorisé sur SLES restent à préciser. Le code actuel ne prend pas en charge
Python 3.6 : cette ancienne mention documentaire reste un écart à résoudre
dans la qualification, pas une compatibilité acquise.
La v0.7.2 ajoute uniquement `io` et `contextlib` de la bibliothèque standard.

## Bibliothèques

Le lecteur, les calculs et les journaux utilisent la bibliothèque standard Python. L'IHM utilise tkinter et son runtime Tcl/Tk. La courbe ajoute Matplotlib, importé à la demande. Aucun module n'est installé ou mis à jour automatiquement.

Matplotlib fait intervenir notamment NumPy, contourpy, cycler, fonttools, kiwisolver, packaging, Pillow, pyparsing et python-dateutil, ce dernier dépendant de six. Le relevé `environnement_*.json` contient leurs versions réellement présentes, contraintes Requires-Python/Requires-Dist et étiquettes de plateforme/ABI WHEEL lorsqu'elles existent. Les dépendances conditionnelles déclarées restent à examiner sur la cible. Les bits s'appliquent à l'interpréteur et aux composants compilés ; un module Python pur n'a pas nécessairement une variante 32/64 bits.

Au lancement de MAIN, ce relevé est enregistré avec Python, OS, architecture et versions Tcl/Tk observées. Le relevé local joint dans `preuve_environnement_linux_v060.json` documente l'essai Linux, sans constituer un environnement Windows approuvé. Il ne faut pas installer aveuglément ces versions sur le poste de Mourad.

## Mécanismes entre OS — requis 3005

- Chemins gérés avec pathlib ; aucune lettre de lecteur imposée au moteur.
- Tests lancés avec sys.executable, donc le même interpréteur que le lanceur.
- Encodage, séparateur et décimale explicites, sans dépendre silencieusement de la locale.
- Pas de commande shell propre à un OS pour analyser les données.
- Erreurs d'accès remontées dans le diagnostic ; tests de permission simulés distincts des ACL réelles Windows.
- FigureCanvasTkAgg intégré sans pyplot ni changement du backend global de Spyder.

## Qualification à compléter — requis 3004/3005

1. Archiver l'environnement réel sur chacune des deux cibles Windows et SLES 15 SP7.
2. Vérifier les contraintes de toutes les dépendances ; exécuter les tests sans cas ignoré et l'essai interactif. Puis figer les versions directes et transitives retenues et leur méthode d'installation.
3. Tester chemins avec accents/espaces, accès refusé, affichage/DPI et gros fichiers sur le poste cible.
4. Lorsque les environnements seront disponibles, préparer et tester les livrables
   propres à chaque cible, hors Spyder, et documenter les modules embarqués.
   La construction des exécutables n'est pas le périmètre du Lot 2B actuel.
5. Pour toute montée de Python ou d'un module : analyser l'impact sur l'ensemble et rejouer les essais concernés avant acceptation.

L'exécutable n'est pas encore réalisé. L'exécution dans Spyder et les métadonnées des paquets ne prouvent pas sa compatibilité. Les détails des vérifications et des écarts sont dans la matrice des requis.
