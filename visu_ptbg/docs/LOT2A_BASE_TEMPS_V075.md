# Lot 2A — moteur de diagnostic temporel — v0.7.5

Cette étape renforce les requis 4100, 4101, 4105 et 4106, ainsi qu'une partie
des requis 2305 à 2307. Elle ne réalise ni synchronisation multi-PLC, ni
interpolation, ni correction des fichiers.

## Faits et interprétations

Le moteur calcule chaque `Δt` entre deux lignes physiques voisines et valides.
Il distingue :

- les timestamps dupliqués ;
- les retours en arrière ;
- les timestamps invalides ;
- les interruptions dues à une ligne CSV rejetée ;
- le jitter, c'est-à-dire un écart positif isolé au raster ;
- un trou **probable**, proche d'un multiple entier du raster ;
- un changement de fréquence **probable**, seulement si une fréquence
  alternative persiste sur plusieurs intervalles consécutifs.

« Probable » est volontaire : le CSV ne prouve pas à lui seul la cause du
grand intervalle. Le programme n'ajoute aucun échantillon et ne déplace aucun
timestamp. Les croix de la courbe restent réservées aux cellules vides du
signal choisi ; un trou temporel ne crée pas de croix.

## Raster et tolérances

Le pas et la tolérance saisis par l'utilisateur sont prioritaires et restent
dans l'unité native indiquée. Sans profil saisi, le raster est estimé à partir
du groupe majoritaire de `Δt` positifs proches. Une égalité entre plusieurs
groupes donne « raster indisponible » : aucune valeur n'est choisie au hasard.

Les règles techniques communes sont centralisées dans `src/regles_temps.py` :

| Règle | Valeur v0.7.5 | Unité |
|---|---:|---|
| Tolérance d'inférence | 0,05 | rapport sans unité |
| Persistance d'un changement de fréquence | 3 | intervalles consécutifs |
| Regroupement d'une fréquence alternative | 0,05 | rapport sans unité |
| Exemples conservés dans le résumé | 50 | anomalies |

Ces valeurs sont des réglages techniques du prototype, pas des seuils métier
validés pour tous les PLC. Elles peuvent être modifiées dans un objet
`ReglesTemps` et doivent être qualifiées avant la livraison finale.

## Diagnostic complet ou partiel

Le diagnostic est complet uniquement si la lecture atteint la fin, sans ligne
rejetée ni timestamp invalide. Sinon, les intervalles locaux fiables continuent
d'être analysés et le résultat porte explicitement le statut `partiel`.

Chaque anomalie indique le type, la gravité, les numéros physiques des lignes,
les temps bruts et le `Δt` exact lorsqu'il est calculable.

## Compatibilité

Le Lot 2A utilise uniquement la bibliothèque standard de Python 3.11 :
`collections`, `dataclasses`, `decimal`, `statistics` et `typing`. Il n'ajoute
aucun paquet à installer. La cible principale demandée par Sébastien est
Windows 11 64 bits avec Python 3.11 dans l'environnement Spyder. La cible SLES
15 SP7 reste à qualifier sur la future VM.

