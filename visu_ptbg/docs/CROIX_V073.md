# Croix sur la courbe — étape v0.7.3

La demande de Mourad porte sur les données manquantes dans le CSV : une croix
sur le dernier point connu avant un manque, une autre sur le premier point
connu après, et un vide entre les deux. Les croix ne sont plus dans une bande
séparée. Elles gardent exactement les coordonnées des mesures présentes.

## Règle appliquée

Une cellule vide, ou composée seulement d'espaces, dans le **signal choisi**
constitue ici un manque constaté. Ce constat ne précise pas la cause du manque.
Plusieurs cellules vides consécutives forment un seul trou. S'il commence ou
finit le fichier, seul le bord disponible peut porter une croix. Une même
mesure bordant deux trous n'a qu'une croix. Un signal entièrement vide reste
refusé avec une explication, puisqu'aucune mesure ne peut servir de bord.

Un texte invalide, NaN, Inf ou une valeur non représentable n'est pas assimilé
à une preuve de perte : le trait est interrompu mais sans croix. Si un même
bloc non traçable contient aussi une cellule vide, ses mesures connues de part
et d'autre portent les croix. Une cellule vide dans une autre colonne ne
déclenche aucune croix pour le signal affiché.

Un doublon, un retour temporel, une ligne rejetée ou un pas hors tolérance
interrompt le trait **sans croix**. Un saut de temps seul ne prouve pas la perte
d'une ligne entière. Le diagnostic existant conserve ces anomalies. Sans pas
attendu ni pas régulier observé, les points restent isolés. Un temps invalide
empêche encore ce tracé de signal, tandis que le diagnostic partiel reste
accessible. Aucune interpolation ni synchronisation n'est ajoutée.

## Modifications, fichier par fichier

Le diff exact est dans `DIFF_V072_V073.patch`.

| Fichier | Modification et raison |
|---|---|
| `src/signal_csv.py` | Repérer les vrais points qui encadrent les cellules vides. Calculer séparément les interruptions temporelles sur tous les couples, en décimal exact. Vérifier que le profil appliqué correspond au diagnostic. |
| `src/_signal_draw.py` | Relier les échantillons permis et insérer des séparateurs de dessin aux coupures. Les listes de données ne sont pas modifiées. |
| `src/trace_signal.py` | Retirer la bande des croix. Placer les croix orange aux coordonnées réelles des bords sur la courbe. Conserver le moniteur temporel et le zoom commun. |
| `tests/test_coupures_signal.py` | Ajouter 11 tests des bords, segments, faux positifs, tolérance et changement de profil. |
| `tests/test_signal_csv.py` | Adapter les trois tests de rendu à la nouvelle règle et vérifier l'absence de croix pour un simple saut de temps. |
| `MAIN.py` | Actualiser la version affichée et l'historique, sans ajouter de logique métier. |
| `src/diagnostic_csv.py` | Actualiser uniquement le numéro de version ; aucune modification du lecteur. |
| `verifier_robustesse.py` | Actualiser uniquement la version affichée et celle des journaux. Les limites du lanceur recensées précédemment restent à traiter séparément. |
| `README.md` | Expliquer l'affichage et donner deux essais reproductibles. |
| `AGENTS.md`, `MISSION_CODEX.md` | Consigner la précision de Mourad et limiter la mission à cette étape. |
| `docs/REPRENDRE_LE_CODE.md` | Expliquer les deux fonctions nouvelles et le rôle des séparateurs graphiques pour Sébastien. |
| `docs/DEPENDANCES.md` | Identifier la version, sans dépendance supplémentaire. |
| `exemples/exemple_synthetique_croix.csv` | Ajouter un petit fichier d'essai avec 22 cellules réellement vides. Les six CSV reçus restent intacts. |
| `exemples/Croix_sur_la_courbe_v073.png` | Montrer le rendu obtenu avec le code de production à partir de cet exemple. |
| `docs/CROIX_V073.md`, `docs/DIFF_V072_V073.patch`, `docs/preuve_tests_linux_v073.json` | Expliquer et tracer la modification, les tests et l'intégrité des fichiers. |

Le document de requis est actualisé séparément : seule l'interprétation des
croix et la preuve de cette étape changent. Les textes des exigences et les
commentaires d'origine restent conservés.

## Tests et portée de la preuve

Le contrôle structuré exécute **106 tests rapides réussis**, puis **1 test
d'intégration réussi** dans un autre processus. Aucun échec, erreur ou test
ignoré. Le délai reste de 60 s pour les tests rapides et de 180 s pour
l'intégration. Le lanceur habituel est également essayé séparément.

La preuve `preuve_tests_linux_v073.json` contient les résultats unittest
structurés et les SHA-256 calculés par blocs avant/après. Les 38 fichiers
surveillés restent identiques pendant ces tests : sources, lanceurs racine,
tests, CSV, scripts de référence et nouvel exemple CSV. Les six CSV reçus et
les trois scripts de référence sont aussi comparés à l'archive v0.6.0 : leurs
octets sont inchangés. La preuve concerne Python 3.12/Linux et le moteur de
rendu Matplotlib Agg ; elle ne constitue pas un essai natif Windows/SLES.

| Requis concerné | Preuve de cette étape | Limite |
|---|---|---|
| 4101, partiel | Croisillons aux vrais bords et absence de segment à travers les cellules vides, testés sur le tracé réellement produit. | Le déphasage inter-PLC et la perte de lignes entières ne sont pas caractérisés. Essai humain attendu. |
| 2103, 3003, acquis préservés | Timestamps, ordre, vrais zéros et CSV d'origine conservés ; aucune valeur intermédiaire créée. | Ce contrôle ne requalifie pas tous les comportements temporels. |
| 3006, contribution | Noms explicites, petites fonctions commentées, guide de reprise et tests lisibles. | La maintenabilité reste à apprécier lors de la reprise par Sébastien. |

## Risques et limites à vérifier sur le poste

Le changement visible est le passage de points seuls à des segments lorsque le
profil le permet, avec des coupures explicites. Aucun modèle Bool/Float ni
tracé en escalier n'est déduit automatiquement. Des croix très proches peuvent
se superposer au zoom initial ; zoomer permet de les inspecter. Le rendu natif
Tkinter, Windows et SLES 15 SP7 reste à essayer. La limite de 500000 points,
la lecture synchrone et l'affichage d'un seul signal sont inchangés.

L'essai à faire est décrit au début du README. La suite attend le retour de
Mourad sur cet affichage. Aucun autre lot n'est commencé par cette livraison.
