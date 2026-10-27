# Base de temps et données absentes — v0.7.0

## Périmètre décidé le 26 octobre 2026

L'accès à la VM n'est pas encore disponible. À la demande de Mourad, le travail
continue sur l'interface, avec priorité à la base de temps et à une indication
visible des données absentes. La fabrication de l'exécutable reste à faire.
Le plan d'action Excel n'est pas modifié.

## Réalisation

L'inspection relit la source et vérifie son SHA-256 par rapport au diagnostic
appliqué. Les calculs sont séparés de la vue ; la bibliothèque standard suffit
au tableau. Matplotlib, déjà utilisé, reste optionnel pour le dessin.

Chaque couple porte les timestamps bruts et les plages physiques des deux
enregistrements CSV. Les champs multilignes sont respectés. Un rejet entre deux
lignes retenues ou un temps non numérique interdit la soustraction de ce couple.
Les autres intervalles exploitables restent consultables comme observations
locales ; le bilan global du pas reste suspendu selon les règles v0.6.0.

Les calculs utilisent Decimal, précision 4100, dans l'enveloppe numérique du
lecteur. Doublons, retours et pas positifs hors tolérance sont distingués.
La tolérance est inclusive ; un pas nul ou négatif reste une anomalie même si
elle est large. L'unité saisie n'effectue aucune conversion.

Le tableau présente tous les intervalles par pages de 200, avec un filtre sur
les points à examiner. Le résumé donne les six pas les plus fréquents avec leurs
occurrences et indique sa restriction quand nécessaire. Le graphique représente
Δt par numéro de ligne CSV, sans segments reliant les points. Un retour arrière
reste à sa place dans l'ordre d'enregistrement. Les coordonnées flottantes qui
fusionneraient deux Δt distincts sont refusées ; le tableau conserve les valeurs exactes.

Sur la courbe du signal, les valeurs non affichables restent NaN. Les cellules
vides sont marquées par une croix orange et les valeurs invalides/non traçables
par une croix rouge, dans une bande séparée sans échelle de valeur du signal.
Le zoom X est commun aux trois axes. Les vrais zéros restent des mesures.
Un intervalle hors tolérance est ombré entre ses deux temps connus. Aucune
valeur ni aucun instant manquant n'est reconstitué. Les repères temporels de
cette vue restent bornés et explicitement signalés comme en v0.6.0 ; le nouvel
inspecteur permet de parcourir tous les couples dans sa limite de 500000 lignes.

Si toute la colonne de signal est non affichable, le refus existant du tracé
est conservé. Un temps invalide ou une ligne rejetée ne reçoit pas une croix
positionnée arbitrairement : le diagnostic et l'inspection en rendent compte.

## Vérifications et essai Windows

La suite comporte 84 tests : les 66 tests précédents et 18 nouveaux cas.
Les ajouts vérifient le corpus de simulation, les lignes exactes, les tolérances
à leur limite, les grands compteurs, retours/doublons, rejets, temps absents,
champs multilignes, lectures partielles, sources modifiées et listes de plus de
200 anomalies. Les rendus Agg vérifient les points, les croix, le zoom commun
et l'absence de nouveaux échantillons dans un intervalle hors pas.

Le bilan machine est dans `preuve_tests_linux_v070.json`. Les graphiques sont
rendus et inspectés localement. Aucun serveur graphique natif n'est disponible
ici : la fenêtre tkinter, sa pagination, la fermeture des fenêtres de détail,
son redimensionnement et le parcours Windows doivent encore être essayés.
Les essais Windows rapportés pour v0.6.0 ne valident pas automatiquement v0.7.0.

Suivre le README, puis changer de fichier ou appliquer un nouveau profil et
vérifier que l'ancien détail et sa fenêtre graphique sont retirés. Modifier un
champ sans l'appliquer doit afficher le rappel et empêcher une nouvelle inspection.

## Requis concernés — état partiel, sans validation globale

| Requis | Apport | Reste ouvert |
|---|---|---|
| 2103 | Provenance et horodatages par couple | Origines et règles entre sources |
| 3003, 3006 | Calcul, dessin et widgets séparés et commentés | Revue humaine du code |
| 4100, 4101 | Δt exacts, comptes, localisation et dessin | Period continuous increase, phasage et causes |
| 4102 | Moniteur conservé dans la vue de signal | Ensemble des arrangements |
| 4105 | Ruptures explicites, sans faux intervalle | Réactivité/annulation sur gros volumes |
| 4106 | Pas et tolérance avec comparaison explicite | Règles métier et unités définitives |
| 4107 | Aucune construction absolue prétendue | Origine, pré-déclenchement et jitter |

Un écart de 2 ms sous un profil de 1 ms n'est pas à lui seul une preuve de
perte. La cadence du CSV reste distincte du cycle PLC. L'inspecteur ne met pas
en phase les PLC et ne conclut pas sur leur fonctionnement.
