# Revue des remarques Copilot et réalisation du lot 1

26 octobre 2026 — VISU PTBG v0.7.1, à vérifier sur Windows et SLES 15 SP7.

## Architecture lue

- `MAIN.py` affiche l'arbre, les profils temporels, le diagnostic, la courbe
  demandée par Mourad et l'inspection de la base de temps.
- `src/diagnostic_csv.py` lit les fichiers, conserve les lignes et produit le
  diagnostic brut. `src/base_temps.py` contrôle un pas saisi par fichier.
- `src/paquet_csv.py` isole chaque source ; `src/decouverte_csv.py` découvre les
  fichiers d'un dossier. `src/inspection_temps.py` détaille les couples de temps.
- `src/signal_csv.py`, `src/trace_signal.py`, `src/trace_temps.py`,
  `src/vue_signal.py`, `src/vue_temps.py` préparent et montrent les graphiques.
- `demarrer_diagnostic.py` et `demarrer_bases_temps.py` sont des démonstrations.
  `verifier_robustesse.py` lance les tests rapides, conserve le résultat et les
  empreintes des répertoires actuellement surveillés.
- `tests/` couvre les comportements rapides. `tests_integration/` sépare le
  cas volumineux. `donnees/` contient les six CSV de simulation archivés.
  `references_simulation/` contient les scripts reçus, non exécutés par VISU.

## Diagnostic des sept groupes de remarques

| Sujet Copilot | Verdict après lecture | Conséquence |
|---|---|---|
| Tous les CSV, casse et sous-dossiers | Vrai pour la démonstration : liste fixe. L'IHM acceptait déjà plusieurs fichiers choisis par l'utilisateur. | Découverte récursive et bouton dossier dans le lot 1. |
| Erreur locale, lignes incorrectes, numéros physiques, fichiers inchangés | Déjà couverts par `read_csv`, `examiner_paquet` et plusieurs tests, avec refus explicite des en-têtes non fiables. | Conservés ; nouveaux essais d'ensemble, sans réécriture. |
| Gros CSV intégralement chargés | Vrai : l'ancien lecteur créait octets, texte et liste des lignes avant le parsing, malgré une borne de 50 MiB. | Hachage/décodage et parcours des lignes en flux. Les enregistrements restent conservés pour l'API ; pas de performance contractuelle déduite. |
| `timestamp_reel_ms` non détecté | Vrai : la liste de noms candidats ne le contenait pas. | Reconnu quand unique. Avec `timestamp_ideal_ms`, choix explicite conservé. |
| Priorité automatique au timestamp « réel » | Hypothèse non établie par les CSV reçus, qui utilisent `index` ou `t_ms`. Le requis prévoit aussi un temps dans la première colonne. | **Pas d'auto-priorité** entre horloges : faire confirmer le schéma définitif avant de choisir. |
| Un temps invalide bloque toutes les statistiques | Vrai pour le diagnostic global v0.6.0 ; l'inspection v0.7.0 montrait déjà des couples locaux. | Bilan global partiel ; seuls les couples adjacents valides sont mesurés dans le diagnostic. |
| Raster, jitter, trous, changement de fréquence | Doublons, retours et pas hors tolérance existaient ; la notion de perte et les règles de jitter ne sont pas fixées. | Définition métier encore nécessaire, aucune perte affirmée automatiquement. |
| Comparaison des PLC par lignes | Faux pour le paquet : aucun alignement inter-PLC. Vrai pour la démo qui indexait deux couples fixes par position. `compare_csv` est volontairement limité aux scénarios/reports avec temps identiques, et refuse un décalage. | Démo appariée par noms explicites ; aucune comparaison des nouveaux PLC. |
| Interface bloquante et signaux multiples | Vrai : lecture synchrone ; l'affichage multi-signaux reste à faire. La sélection des profils existe, mais l'unité n'est pas une conversion. | À traiter plus tard avec une stratégie de fond/annulation sûre ; pas dans le lot CSV. |
| Monitor quantitatif et croix des valeurs absentes | Le Time Base Monitor initial montrait des repères ; les vues Δt et croix étaient déjà en cours sur demande directe de Mourad en v0.7.0. | Conservées dans la version livrée ; pas d'autre ajout graphique dans le lot 1. |
| Surveillance et bilan des tests | Vrai : `verifier_robustesse.py` ne hache pas `MAIN.py` ni les lanceurs, lit les fichiers surveillés d'un coup, et extrait le compte de tests du texte. Il distingue cependant déjà les tests ignorés et la validation globale. | Revue consignée ; refonte du lanceur et liaison requis ↔ tests réservées à un lot distinct. Contrôle SHA-256 séparé pour les fichiers racine dans cette livraison. |
| Version unique, journaux et gravités | Version encore dupliquée ; les résultats et numéros de lignes sont structurés dans les diagnostics, mais pas dans un journal commun à niveaux unifiés. | Travail transversal ultérieur, sans chambouler le lot 1. |

## Diff du lot 1, fichier par fichier

| Fichier | Avant | Après |
|---|---|---|
| `src/decouverte_csv.py` | Absent | Parcours récursif, extensions insensibles à la casse, résultat trié. |
| `src/diagnostic_csv.py` | Lecture octets/texte/lignes entiers ; candidats exacts limités ; un temps invalide bloquait toute statistique. | Contrôle et hachage par blocs, lignes parcourues en flux ; noms temporels supplémentaires ; temps locaux seulement autour des ruptures, bilan global marqué partiel. |
| `src/paquet_csv.py` | Ajout de chemins fournis. | `ajouter_dossier` réutilise l'isolation existante entre fichiers. |
| `demarrer_diagnostic.py` | Cinq noms fixes ; paires comparées via `fichiers[0]` etc. | Tous les CSV découverts sont analysés ; seuls les couples LIM/PID nommés sont comparés. |
| `MAIN.py` | Sélection manuelle de fichiers. | Bouton/menu « Ajouter un dossier CSV… ». |
| `tests/test_import_lot1.py` | Absent | Découverte, intégrité, isolation d'un fichier erroné, ambiguïté temporelle, constat partiel et modification pendant lecture. |
| `tests_integration/test_import_volumes.py` | Absent | CSV UTF-8 de plus d'1 MiB testé séparément du délai de 60 secondes. |
| `README.md`, `docs/DEPENDANCES.md` | Décrivaient l'étape v0.7.0. | Décrivent la v0.7.1 et le nouveau parcours, sans déclarer les requis validés. |

L'archive v0.6.0 de référence est jointe au paquet de reprise pour permettre une
comparaison indépendante. Le tableau ci-dessus isole les changements du lot 1.

## Plan et risques

1. **Lot 1 — import et temps brut :** travaux ci-dessus, puis essai Windows et
   revue des cas réels ; aucune priorité métier de timestamp supposée.
2. **Lot 2 — règles de temps :** préciser origine, unité, pas, jitter et
   pré-déclenchement avec Sébastien avant temps absolu ou PLC comparés.
3. **Lot 3 — interface :** listes de colonnes, plusieurs signaux et sources,
   lecture en tâche de fond et annulation ; vérifier le comportement Windows.
4. **Lot 4 — analyse et validation :** curseurs/rapports après règles métier,
   tests par requis et environnement de livraison.

**Risque de régression du lot 1 :** la lecture en flux peut modifier la gestion
des retours à la ligne, des guillemets ou de l'encodage. Les tests couvrent ces
cas, dont UTF-16 et les champs multilignes ; la v0.7.1 doit encore être essayée
sur le poste Windows de Mourad. Un consommateur externe qui supposait
`step_values=[]` dès qu'un temps est invalide devra tenir compte du champ
`time.partial` : les pas affichés peuvent désormais provenir de couples locaux.
L'ajout de tous les fichiers d'un gros dossier reste synchrone dans l'IHM ; le
travail en arrière-plan relève d'un lot ultérieur. Les nombres de fichiers,
taille et temps d'analyse admissibles restent à fixer.

La suite n'autorise ni synchronisation automatique, ni interpolation, ni PDF.
Le lot 2 ne doit être lancé qu'après revue du lot 1 et clarification métier.
