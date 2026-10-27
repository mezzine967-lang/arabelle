# Reprendre VISU PTBG — guide pour Sébastien

Ce guide concerne la v1.0.0 candidate. Le projet utilise Python et la bibliothèque
standard pour lire/analyser les CSV. Tkinter affiche la fenêtre et Matplotlib
dessine les graphiques. Les calculs peuvent être testés sans ouvrir la fenêtre.

## Ajouts v1.0.0

Le point d'entrée du dépôt est `../lancer.py`, qui ouvre `MAIN.py`. Les
dépendances sont figées dans `../requirements.txt`. Ne pas travailler dans
l'ancienne copie de préparation `/workspace/arabelle-dev`.

- `src/groupe_binaire.py` valide les groupes de 2 à 8 colonnes Bool du même
  CSV et dessine leurs pistes. Les décalages Y sont graphiques uniquement.
- `src/curseurs.py` gère `motion_notify_event` et le suivi optionnel de la
  souris. `definir_condition` et `placer_horizontal` utilisent les lignes
  physiques du CSV ; un Bool absent/invalide n'autorise aucune mesure.
- `MAIN._dialogue_colonnes` prépare les Bool en arrière-plan. Le paramètre
  `preparer_signal(..., autoriser_vide=True)` conserve une colonne de groupe
  entièrement vide au lieu d'en inventer l'état. Les tracés ordinaires gardent
  leur refus explicite d'une colonne entièrement non affichable.
- `src/rapport_pdf.py`, `exporter_pdf_en_fond` : les captures de figures vivantes
  restent sur Tk ; les PNG figés sont passés à un processus Matplotlib isolé.
  L'annulation écarte le résultat avant écriture du fichier demandé. Ne jamais
  envoyer une figure Tk ou appeler Matplotlib dans le thread de travail partagé.
- `src/vue_signal.py`, `fermer_canvas` : annuler le rendu différé de TkAgg
  avant destruction, pour éviter un callback vers un onglet fermé.
- `tests/test_requis_v100.py` couvre les régressions métier ;
  `tests_gui/test_parcours_tk.py` teste les vraies fenêtres avec un DISPLAY.

Les types choisis dans l'arbre sont mémorisés par chemin, SHA-256 et colonne,
pendant la session. Ils ne changent jamais les données source.

## Parcours de lecture conseillé

1. Lire `README.md` et essayer un CSV de `donnees/`.
2. Lire `SourceTemps` et `examiner_source` dans `src/base_temps.py` : ils
   décrivent les paramètres d'un fichier et les résultats attendus.
3. Lire `read_csv` dans `src/diagnostic_csv.py` : il appelle les étapes de
   lecture, garde les lignes et construit le diagnostic.
4. Lire `preparer_inspection` dans `src/inspection_temps.py` pour le calcul
   de Δt, puis `preparer_signal` dans `src/signal_csv.py` pour les points.
5. Lire les actions `_ajouter`, `_configurer`, `_examiner_intervalles` et
   `_afficher_courbe` dans `MAIN.py` pour suivre les clics de l'utilisateur.

Le chemin principal est : clic dans MAIN → PaquetCSV → examiner_source →
read_csv → diagnostic affiché. Chaque source garde son propre profil ; aucune
source ne donne implicitement son horloge à une autre.

## Où modifier quoi

Les heures HH:MM:SS sont interprétées par `_temps_decimal` dans diagnostic_csv.
Il ne faut pas modifier `_decimal`, qui sert aussi aux signaux et aux profils.
Les calculs sur des heures sont en secondes ; le texte brut est conservé.

Le masquage du moniteur de la courbe est dans `src/vue_signal.py`, fonction
`basculer_moniteur`. L'autorisation vient de `construire_moniteur` ; ne jamais
la déduire uniquement de la visibilité graphique ou de la zone zoomée.

La lisibilité v0.7.8 est dans `src/trace_signal.py` : `resumer_moniteur` met
en mots les résultats ; `creer_figure` gère formes, tailles et transparences.
Les commentaires expliquent directement les choix de dessin dans le code.
Ne pas placer de nouvelle règle de calcul dans ces fonctions.

| Besoin | Fichier / point d'entrée | Test à consulter |
|---|---|---|
| Rechercher les CSV d'un dossier | `src/decouverte_csv.py`, `decouvrir_csv` | `tests/test_import_lot1.py` |
| Appliquer la première colonne comme temps | `src/diagnostic_csv.py`, `read_csv` | `tests/test_import_lot1.py`, `tests/test_robustesse_csv.py` |
| Gérer encodage, séparateur ou ligne incorrecte | `src/diagnostic_csv.py`, `read_csv` et ses fonctions de lecture | `tests/test_robustesse_csv.py` |
| Vérifier pas et tolérance | `src/base_temps.py`, `_profil_numerique` / `examiner_source` | `tests/test_base_temps.py` |
| Classer raster, jitter, trou et fréquence | `src/analyse_temps.py`, `analyser_base_temps` | `tests/test_analyse_temps_lot2a.py` |
| Modifier les seuils techniques | `src/regles_temps.py`, `ReglesTemps` | `tests/test_analyse_temps_lot2a.py` |
| Calculer le détail des intervalles | `src/inspection_temps.py`, `preparer_inspection` | `tests/test_inspection_temps.py` |
| Préparer points et valeurs absentes | `src/signal_csv.py`, `preparer_signal` | `tests/test_signal_csv.py` |
| Placer les bords des manques et couper les traits | `src/signal_csv.py`, `_bords_des_manques` et `_coupures_temporelles` | `tests/test_coupures_signal.py` |
| Préparer et tracer les Δt sous la courbe | `src/analyse_temps.py`, `qualifier_intervalles`, puis `src/signal_csv.py` et `src/trace_signal.py` | `tests/test_moniteur_quantitatif.py` |
| Modifier couleurs, croix ou axes | `src/trace_signal.py`, `src/trace_temps.py` | Tests de figures dans les deux fichiers de tests précédents |
| Changer le numéro de version | `src/version_visu.py` uniquement | Lancer `verifier_robustesse.py` |
| Modifier le tableau des intervalles | `src/vue_temps.py`, `VueTemps` | Essai manuel Tkinter, puis tests des calculs |
| Ajouter une commande à la fenêtre | `MAIN.py`, `FenetreVISU` | Essai manuel Windows / SLES |

## Exemple sans interface

Depuis le dossier contenant MAIN.py :

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path("src").resolve()))
from base_temps import SourceTemps, examiner_source
from inspection_temps import preparer_inspection

source = SourceTemps(
    fichier="donnees/simulation10_execution1.csv",
    colonne_temps="t_ms", unite="ms", pas_attendu="1", tolerance="0",
)
resultat = examiner_source(source)
inspection = preparer_inspection(source, resultat)
print(inspection.comptes)
```

Le pas de 1 ms est choisi pour cette simulation. Ce n'est pas une valeur par
défaut à appliquer aux futurs fichiers PLC.

## Pourquoi certaines précautions existent

- `Decimal` calcule les différences avant toute conversion pour Matplotlib.
  Deux grands timestamps distincts ne doivent pas devenir un faux doublon.
- Un enregistrement CSV peut occuper plusieurs lignes physiques. `line_start`
  et `line_end` conservent cette provenance. Ne pas remplacer le lecteur par
  un simple `split(',')`.
- Un rejet ou un temps invalide interrompt la continuité : on ne soustrait pas
  les temps situés de part et d'autre pour prétendre mesurer un pas consécutif.
- `None` signifie « non calculable ». `0` est un résultat réel. Dans le tracé,
  `NaN` coupe le trait. Les croix se trouvent sur les mesures réelles qui
  encadrent un champ vide du signal : dernier point avant, premier point après.
  Un texte invalide ou un saut temporel seul ne produit aucune croix.
- `_coupures_temporelles` examine tous les couples contigus en Decimal.
  Il ne faut pas utiliser les exemples limités du moniteur pour décider où
  couper un trait. Les champs CSV multilignes sont pris en compte via `line_end`.
- `_signal_draw.sample_chart` ajoute des séparateurs NaN uniquement dans les
  coordonnées de dessin. Les listes de mesures de `SignalPrepare` sont intactes.
  Sans profil ni pas régulier observé, le rendu garde des points seuls.
- `qualifier_intervalles` applique au graphique les mêmes catégories que le
  bilan temporel. `_serie_temporelle` convertit ensuite les Δt exacts seulement
  pour Matplotlib. Deux lignes non contiguës ne sont jamais reliées par un
  intervalle inventé.
- Le requis 2304 impose la position du temps : `read_csv` utilise toujours
  `columns[0]`. Le nom de cette colonne ne sert pas à la reconnaître. Le champ
  `time_candidates` est conservé dans les anciens journaux/API, mais contient
  désormais seulement cette première colonne.
- Le contrôle initial choisit l'encodage et hache le fichier. Le parsing hache
  aussi les octets effectivement lus grâce à `_LectureBornee`. Le contrôle
  final compare encore le contenu. Cette protection détecte aussi un fichier
  temporairement modifié puis rétabli. Elle ne verrouille pas le fichier.
- `_LectureBornee` est un adaptateur de lecture standard Python : `readinto`
  remplit le tampon fourni par Python, compte les octets et calcule SHA-256.
  `TextIOWrapper` garde la gestion standard d'UTF-8/UTF-16 et des fins de lignes.

## Comment faire évoluer le code

Faire une petite modification à la fois. Reproduire un défaut sur un CSV
synthétique temporaire et ajouter un test qui échoue avant la correction.
Privilégier une fonction au nom explicite pour un comportement précis ;
commenter les choix et les limites plutôt que chaque instruction évidente.
Ne jamais corriger un CSV reçu pour faire passer un test.

Commandes : `python verifier_robustesse.py`, puis séparément
`python -m unittest discover -s tests_integration -v`. Les tests ne qualifient
pas à eux seuls une plateforme de livraison ni tous les requis métier.

## Limites connues

Lecture synchrone dans l'IHM, conservation des lignes en mémoire après lecture,
limite de 50 MiB par fichier et de 500000 lignes pour les vues détaillées.
La tolérance saisie permet de classer un jitter observé, mais sa valeur métier
reste à confirmer. La définition d'une perte, les origines et les unités entre
PLC restent à confirmer. Aucun texte ACTIVE/STANDBY/FAILED n'est converti
en chiffre arbitraire. Le lanceur de tests reste à moderniser (voir la revue).
Les numéros de version d'exécution restent dans MAIN, diagnostic_csv et
verifier_robustesse ; les mentions historiques dans docs ne sont pas à réécrire.
# Ajouts v0.9.0 : où modifier chaque comportement

Présentation : `MAIN._construire_contenu` organise les commandes et choisit
l'onglet Courbe au démarrage ; `_selectionner` met à jour le nom du fichier.

- `taches.py` : tâche de fond, file de messages, annulation ; aucun widget.
  `MAIN._lancer` reçoit ces messages avec after() puis met l'IHM à jour.
- `signal_csv.py` : lecture Bool/Float et conservation du texte brut pour les
  curseurs. Auto ne décide jamais qu'un signal numérique 0/1 est Bool.
- `curseurs.py` : index de consultation et artistes de curseur ; aucun calcul
  de raster. `LecteurEchantillons` reste utilisable sans Matplotlib ni Tk.
- `vue_signal.py` : panneau de courbes, fenêtre de lectures, superposition.
- `vue_arrangements.py` : onglets et dispositions ; défilement pour les écrans
  étroits. Chaque vue possède son propre signal et son propre moniteur.
- `vue_xy.py` : couples X/Y d'une même ligne du même CSV ; axe temporel indépendant.
- `rapport_pdf.py` : capture immuable, page, en-tête et export exclusif PDF.
  `vue_rapports.py` relie le menu aux dialogues, sans relire les CSV.
- `executer_tests.py` : sous-processus unittest, résultats structurés par test.
  `verifier_robustesse.py` contrôle aussi les lanceurs et hache par blocs.
- `tests/test_requis_v090.py` : régressions liées aux identifiants des requis.

Point de vigilance : Tkinter et Matplotlib restent utilisés dans le fil principal.
Ne pas déplacer le rendu PDF dans le thread de lecture : Matplotlib n'est pas
thread-safe. Si la réactivité du rendu doit être améliorée, prévoir un processus
isolé recevant une capture indépendante, et le tester sur les deux OS.

Les anciennes sections ci-dessous décrivent l'évolution historique.

