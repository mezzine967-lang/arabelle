# Lot 2B — qualification détaillée du Time Base Monitor — v0.7.7

## But

Le moteur temporel distinguait déjà le jitter, les trous probables et les
changements de fréquence probables. La v0.7.6 affichait encore ces situations
sous une catégorie graphique générale « hors tolérance ».

La v0.7.7 fait utiliser au graphique les mêmes catégories que le moteur :

- dans la tolérance ;
- jitter hors tolérance ;
- trou probable ;
- changement de fréquence probable ;
- timestamp dupliqué ;
- retour en arrière.

Le mot « probable » reste obligatoire pour les trous et changements de
fréquence. Aucun point, aucune valeur et aucune croix ne sont ajoutés au CSV.

## Tolérance du pas

La tolérance est exprimée dans la même unité native que le pas attendu. Pour un
pas de 10 ms et une tolérance de 0,2 ms, un Δt compris entre 9,8 et 10,2 ms est
accepté. La tolérance est donc une limite de décision ; le jitter mesuré est
l'écart réellement observé entre le Δt et le raster.

Le texte de l'interface précise désormais cette différence. Aucun pourcentage
ni valeur métier par défaut n'est imposé quand l'utilisateur saisit un profil.

## Organisation simple du code

- `src/analyse_temps.py` calcule et classe les intervalles ;
- `qualifier_intervalles` expose ces catégories à la préparation graphique ;
- `src/signal_csv.py` convertit les valeurs exactes pour Matplotlib ;
- `src/trace_signal.py` choisit seulement les couleurs et les libellés.

Le graphique ne possède donc plus une règle concurrente pour décider si un
écart est un jitter ou un trou probable.

## Vérification

`tests/test_moniteur_quantitatif.py` vérifie séparément :

- un jitter isolé ;
- un multiple du raster classé comme trou probable ;
- trois intervalles successifs classés comme changement de fréquence probable ;
- la présence du libellé « Jitter hors tolérance » dans la figure.

Les essais automatisés ne remplacent pas la revue interactive sous Windows 11
et SLES 15 SP7. Les croix de données manquantes ne sont pas modifiées par ce lot.
L'image `exemples/Time_Base_Monitor_categories_v077.png` montre les catégories
sur un exemple synthétique, sans prétendre représenter un défaut réel de PLC.
