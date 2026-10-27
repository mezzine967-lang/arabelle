# Lisibilité — v0.7.8

Périmètre : REQ_COMMON_KH_4102, présentation du moniteur existant. Le nom
Time Base Monitor, l'axe dédié et le zoom commun restent présents. Le requis
reste ouvert pour les futurs modèles et conversions temporelles.

## Changements fichier par fichier

- src/trace_signal.py : symboles distincts (cercle pour doublon, triangle pour
  trou probable, losange pour jitter), points normaux fins, guides discrets,
  marge verticale et résumé des intervalles du fichier entier. Commentaires
  directement dans les fonctions. Aucun calcul temporel ajouté.
- tests/test_moniteur_quantitatif.py : vérifie les comptes du résumé, le zoom
  partagé et l'absence de modification des objets de données par le dessin.
- src/version_visu.py : version 0.7.8.
- README, MISSION_CODEX et docs/REPRENDRE_LE_CODE : utilisation et maintenance.
- docs/DEPENDANCES.md et environnement_linux_v078.json : registre et versions
  observées des packages, distinctes d'une qualification Windows/SLES.

## Essai utilisateur

Ouvrir simulation10_execution2.csv, unité ms, pas 1, tolérance 0.5 ; afficher
prod2. Attendu : deux cercles orange à Δt=0, un triangle à Δt=2, résumé avec
2 doublons et 1 trou probable. Zoomer : les comptes restent ceux du fichier
entier. Les trous probables ne prouvent pas une perte ; seules les cellules
vides du signal autorisent les croix sur les mesures voisines.

## Limites

Rendu vérifié avec Matplotlib Agg, essai Tkinter Windows/SLES encore attendu.
La fenêtre Tkinter globale n'est pas redessinée dans ce lot ; sa mise à
l'échelle et les très petites fenêtres restent à qualifier. Les repères
verticaux historiques restent limités ; la série Δt et son résumé utilisent
tous les intervalles préparés. Une fréquence modifiée est comptée en
intervalles concernés, pas en événements indépendants.
