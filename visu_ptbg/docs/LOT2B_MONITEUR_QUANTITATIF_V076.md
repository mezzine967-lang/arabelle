# Lot 2B — Time Base Monitor quantitatif — v0.7.6

## But

Le petit axe placé sous chaque signal ne montre plus seulement une barre
d'état. Il affiche les intervalles `Δt = temps courant − temps précédent`,
dans l'unité native déclarée pour le CSV.

Lorsque le moteur du Lot 2A dispose d'un raster :

- le raster est dessiné en pointillés et identifié comme saisi ou estimé ;
- sa tolérance est représentée autour de lui ;
- l'écart vertical entre un point `Δt` et le raster matérialise l'écart
  temporel ;
- doublons, retours arrière et intervalles hors tolérance gardent des couleurs
  distinctes.

Le signal et le moniteur partagent le même axe temporel : zoomer ou déplacer
l'un conserve leur correspondance.

## Limites et règles de prudence

- Aucun intervalle n'est calculé à travers une ligne CSV rejetée.
- Aucun point n'est ajouté au CSV et aucun timestamp n'est corrigé.
- Un intervalle hors tolérance reste un constat temporel ; il ne prouve pas à
  lui seul une perte de donnée.
- Les croix orange de la courbe restent réservées aux cellules réellement
  vides du signal choisi.
- Les états textuels libres ne sont pas convertis en nombres : aucun codage
  `ACTIVE/STANDBY/FAILED` n'est imposé par cette version.
- Sans raster disponible, les points portent le libellé « Δt observés » :
  aucune conformité à une tolérance n'est annoncée.
- Des Δt ou bornes de tolérance exacts distincts que les flottants confondraient
  font refuser ce tracé. Le diagnostic et le tableau exact restent disponibles.

## Fichiers à lire

- `src/signal_csv.py` prépare les Δt à partir des nombres exacts `Decimal` ;
- `src/trace_signal.py` réalise uniquement le dessin ;
- `tests/test_moniteur_quantitatif.py` vérifie les valeurs, les ruptures et le
  rendu Matplotlib sans ouvrir Tkinter ;
- `exemples/Time_Base_Monitor_quantitatif_v076.png` montre le résultat attendu.

Cette évolution couvre partiellement les requis 4100, 4101, 4102 et 4106.
Elle ne développe ni synchronisation multi-PLC, ni interpolation, ni rapport.

## Changements fichier par fichier

Le diff complet se trouve dans `DIFF_V075_V076.patch`.

| Fichier | Changement |
|---|---|
| `src/signal_csv.py` | Prépare les Δt à partir des lignes adjacentes, contrôle la précision et conserve l'origine du raster. |
| `src/trace_signal.py` | Dessine Δt, raster et tolérance ; conserve les croix et le zoom partagé. |
| `tests/test_moniteur_quantitatif.py` | Ajoute les cas du nouveau moniteur, y compris raster absent/estimé, rejets et précision. |
| `tests/test_signal_csv.py` | Vérifie les repères verticaux sans supposer leur position dans la liste des artistes graphiques. |
| `src/version_visu.py` | Centralise le numéro 0.7.6. |
| `MAIN.py`, `src/diagnostic_csv.py`, `verifier_robustesse.py` | Lisent cette version commune et actualisent le court historique. |
| `README.md`, `MISSION_CODEX.md` | Décrivent cette étape et le parcours d'essai Windows. |
| `docs/REPRENDRE_LE_CODE.md` | Indique où reprendre le moniteur et le numéro de version. |
| `docs/DEPENDANCES.md`, `docs/CIBLE_WINDOWS_11.md` | Documentent la réutilisation des bibliothèques existantes. |

## Vérification et limites

117 tests rapides et 1 test d'intégration réussis, aucun échec et aucun test
ignoré sous Python 3.12/Linux. Les calculs et les rendus Matplotlib Agg sont
testés ; la syntaxe est contrôlée pour Python 3.11. Les CSV et scripts de
référence sont inchangés. La preuve couvre aussi les fichiers Python racine
avant/après les essais, en complément du contrôle du lanceur existant.

L'essai interactif Windows 11 et SLES 15 SP7 reste attendu. Une seule courbe
est affichée à la fois ; le tracé refuse encore un temps invalide, dont le
diagnostic reste consultable. Le moniteur détaillé utilise le raster du Lot 2A ;
le petit résumé de l'onglet Diagnostic conserve ses règles historiques.
Les traits verticaux et bandes d'exemples restent limités, mais la série Δt
affiche tous les intervalles calculables jusqu'à la limite du prototype.

Risques de régression ciblés : précision des Δt lors du passage au graphique,
continuité à travers un rejet, conservation des croix et lisibilité à petite
résolution. Les trois premiers sont couverts par les tests ; la mise à
l'échelle native Windows/SLES doit encore être essayée par l'utilisateur.
