# Matrice de traçabilité des requis — VISU PTBG 2.1.0

Document de référence : **NCS/00/I/COMMON----/ES/010 Rev. A** (13/10/2026),
fichier `docs/specification/NCS00ICOMMON----ES010_RevA.docx`.
Le Word contient **64 lignes** de requis pour **63 identifiants** (REQ_COMMON_KH_2201
apparaît deux fois : « Analog signal type : float » et « Binary group signal »).

Contrôle automatique : `python tools/verifier_tracabilite.py` (et le test
`tests/test_architecture.py`) relit les identifiants **dans le Word** et vérifie que
chacun est cité ici, dans le code et dans au moins un test. Aucun requis n'est laissé de côté (aucun n'est oublié ; tous ne sont pas encore validés).

Légende du statut :

- **Implémenté et testé** : fonction présente et vérifiée par un test automatique ;
- **Implémenté — interprétation à valider** : réalisé selon une interprétation ou une
  valeur par défaut documentée dans [POINTS_OUVERTS.md](POINTS_OUVERTS.md), à confirmer
  par le rédacteur de la spécification ;
- **Proposition — énoncé vide** : l'énoncé de la Rev. A est vide ; une fonction est
  proposée, le requis ne peut pas être déclaré satisfait avant d'être rédigé ;
- **Implémenté — qualification … à faire** : réalisé et testé ici (Linux, données de
  test) ; l'essai sur les postes cibles (Windows 11 / SLES 15 SP7 réel) ou sur les volumes
  réels de PTBG reste à consigner (procédure dans [COMPATIBILITE_OS.md](COMPATIBILITE_OS.md)).

En résumé : **chaque requis a reçu une implémentation ou une proposition ; plusieurs règles
métier restent à valider, et la compatibilité Windows / SLES ainsi que les performances
sur les vrais fichiers ne sont pas encore qualifiées.** Le code est préparé pour les deux
systèmes ; il ne pourra être dit officiellement compatible qu'après ces essais.

## 2.1 Caractéristiques des sources

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_2100 | Fréquences différentes (10 et 20 ms préférées) sans perturber l'outil | Raster estimé par fichier (médiane des Δt) ; toute période acceptée ; hors 10/20 ms = simple information | `core/time_base.py` (`_add_checks`) | `test_time_base.test_preferred_frequencies_are_information_only` | Implémenté et testé |
| REQ_COMMON_KH_2101 | Système de plusieurs PLC | Paquet de données = un CSV par PLC ; plusieurs paquets possibles | `core/data_package.py` (`DataPackage`, `Workspace`) | `test_package_report.test_multi_plc_package_and_comparison` | Implémenté et testé |
| REQ_COMMON_KH_2102 | PLC synchronisés ou non | Chaque fichier garde sa base ; alignement par origine absolue (axe absolu) ou décalage manuel affiché ; comparaison inter-sources | `core/data_package.py` (`Timeline`), `core/multi_source.py` | `test_package_report.test_absolute_timeline_aligns_plcs`, `test_manual_offset` | Implémenté et testé |
| REQ_COMMON_KH_2103 | Chaque PLC produit son paquet avec son horodatage | Base de temps propre à chaque `SourceFile` | `core/data_package.py` | `test_package_report.test_multi_plc_package_and_comparison` | Implémenté et testé |
| REQ_COMMON_KH_2104 | Variations de fréquence, déphasage, perte de flux | Changement de fréquence (segments), déphasage interne (Δt hors grille) et inter-PLC (écart médian), fin de flux décalée | `core/time_base.py`, `core/multi_source.py` | `test_time_base.test_frequency_change_segments`, `test_package_report.test_phase_between_synchronised_plcs`, `test_loss_of_data_flow_between_plcs` | Implémenté et testé |
| REQ_COMMON_KH_2105 | Fichier unique ou multiple | Ouverture de plusieurs CSV ou d'un dossier (récursif) ; un fichier illisible n'empêche pas les autres | `gui/app.py` (`open_files`, `open_folder`, `_load`) | `test_csv_reader.test_unreadable_file_isolated`, `test_gui.test_tree_levels_and_types` | Implémenté et testé |

## 2.2 Contenu des sources

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_2200 | Signal binaire | Type Bool (true/false ou 0/1), tracé en escalier sur piste logique | `core/signals.py`, `plotting/renderer.py` | `test_csv_reader.test_auto_types` | Implémenté et testé |
| REQ_COMMON_KH_2201 (1re ligne) | Signal analogique : float | Type Float, tracé continu, lu au plus proche échantillon | `core/signals.py` | `test_csv_reader.test_auto_types` | Implémenté et testé |
| REQ_COMMON_KH_2201 (2e ligne) | Signal groupe binaire | Groupe de Bool (détecté pour `NOM[i]`/`NOM.i` ou créé par l'utilisateur), pistes regroupées et mot binaire lu au curseur | `core/signals.py` (`BinaryGroup`), `core/curves.py` | `test_csv_reader.test_indexed_binary_groups`, `test_gui.test_tree_levels_and_types` | Implémenté — interprétation à valider (codage du groupe) |

## 2.3 Caractéristiques des fichiers

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_2300 | Format préféré csv | Toute extension lisible ; extension ≠ .csv signalée | `core/csv_reader.py` (`_check_file`) | `test_csv_reader.test_other_extension_warned` | Implémenté et testé |
| REQ_COMMON_KH_2301 | Séparateur virgule | Contrôle de cohérence du nombre de champs par séparateur candidat (« ; » avec virgule décimale, tabulation, « \| » refusés) ; lignes au mauvais nombre de champs rejetées, listées avec leur extrait ; virgule décimale dans un fichier à virgules : refus expliqué, aucune fausse colonne créée | `core/csv_reader.py` (`_check_separator`) | `test_csv_reader.test_semicolon_separator_rejected`, `test_robustesse.test_semicolon_with_decimal_comma_rejected`, `test_decimal_comma_in_comma_file_never_invents_columns`, `test_rows_with_wrong_width_rejected_and_quoted` | Implémenté et testé |
| REQ_COMMON_KH_2302 | Texte UTF-8 | Contrôle UTF-8 de tout le fichier ; BOM toléré (information) ; octets non UTF-8 lus en Windows-1252 et UTF-16 lu, avec non-conformité ERREUR citant la 1re ligne fautive (les mesures restent exploitables) ; octets nuls signalés | `core/csv_reader.py` | `test_csv_reader.test_non_utf8_read_but_flagged_with_requirement`, `test_bom_tolerated_and_reported`, `test_robustesse.test_invalid_byte_in_the_middle_is_flagged_not_fatal`, `test_utf16_is_read_and_flagged` | Implémenté — interprétation à valider (lecture signalée plutôt que refus) |
| REQ_COMMON_KH_2303 | Pas de métadonnées | Préambule de métadonnées repéré quelle que soit sa largeur (l'en-tête est la ligne qui précède la 1re ligne de mesures), lignes « # » ; signalés (non-conformité) et ignorés | `core/csv_reader.py` (`_find_header`) | `test_csv_reader.test_metadata_lines_reported_and_skipped`, `test_robustesse.test_preamble_of_same_width_is_metadata` | Implémenté et testé |
| REQ_COMMON_KH_2304 | 1re colonne = base de temps | Toujours la 1re colonne, quel que soit son nom | `core/csv_reader.py`, `core/time_parser.py` | `test_csv_reader.test_reads_examples_and_keeps_first_column_as_time` | Implémenté et testé |
| REQ_COMMON_KH_2305 | Configuration de l'horodatage | Dialogue Base de temps : format, unité, période, tolérance, origine absolue, décalage, jitter ; pré-déclenchement en temps négatif (remarque du relecteur) | `core/time_parser.py` (`TimeBaseSettings`), `gui/dialogs/time_base_dialog.py` | `test_time_parser.test_counter_with_assumed_unit_and_pretrig`, `test_unknown_format_is_an_error_not_a_crash` | Implémenté — interprétation à valider (pré-déclenchement) |
| REQ_COMMON_KH_2306 | hh:mn:s… micro, nanos… | `hh:mm:ss.fraction` jusqu'à 9 chiffres ou `.mmm.uuu.nnn`, passage de minuit, calcul en ns entières | `core/time_parser.py` (`_convert_time_of_day`) | `test_time_parser.test_time_of_day_fraction_styles_and_midnight` | Implémenté et testé |
| REQ_COMMON_KH_2307 | Compteur de temps | Compteur ns, µs, ms, s, min, h ou cycles PLC ; unité lue dans l'en-tête ; sinon unité de la préférence SUPPOSÉE et signalée en avertissement (TBM non masquable) jusqu'à confirmation, applicable d'un coup à plusieurs fichiers ; grands entiers exacts | `core/time_parser.py` (`_convert_counter`) | `test_time_parser.test_unit_from_header`, `test_cycle_unit_requires_period`, `test_big_integer_counter_keeps_precision`, `test_robustesse.test_assumed_unit_is_a_warning`, `test_gui.test_unit_confirmed_for_several_files` | Implémenté — interprétation à valider (unité d'un compteur sans unité) |
| REQ_COMMON_KH_2308 | 1re ligne = en-têtes | 1re ligne utile = en-tête ; sans en-tête, la 1re ligne de mesures est conservée et les colonnes nommées Colonne_1… ; en-tête répété au milieu (fichiers concaténés) ignoré et signalé | `core/csv_reader.py` (`normalize_header`) | `test_csv_reader.test_numeric_first_line_flagged`, `test_robustesse.test_missing_header_keeps_the_first_measure`, `test_repeated_header_and_concatenated_captures` | Implémenté et testé |
| REQ_COMMON_KH_2309 | Noms des variables PLC | Noms vides et doublons renommés et signalés | `core/csv_reader.py` (`normalize_header`) | `test_csv_reader.test_header_names_normalized` | Implémenté et testé |
| REQ_COMMON_KH_2310 | Taille maximale « xxxMo » | Paramètre `max_file_size_mb` (défaut 500 Mo, Outils > Préférences) ; fichier refusé au-delà | `config.py`, `core/csv_reader.py` | `test_csv_reader.test_size_limit` | Implémenté — interprétation à valider (valeur xxx) |

## 6 (Word) Architecture

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_3000 | Compatible SLES 15 SP7 au moins (+ Windows, remarque du relecteur) | Python + Tk + numpy + matplotlib, wheels vérifiées pour win_amd64 et manylinux (glibc 2.38 de SP7) ; scripts SLES et Windows ; Spyder 6 | `system/compat.py`, `install/` | `test_architecture.test_minimal_python_syntax`, campagne multi-versions | Implémenté — qualification sur cible à faire (Windows 11, SLES 15 SP7) |
| REQ_COMMON_KH_3001 | Compatible Python 3.6 au moins | Lu comme « 3.6 minimum » : code vérifié de 3.10 à 3.14, référence 3.11 (décision du relecteur : Python 3.11 sur SLES 15) | `version.py` (`MIN_PYTHON`) | `test_architecture.test_minimal_python_syntax` | Implémenté — interprétation à valider (3.6 strict exclu) |
| REQ_COMMON_KH_3002 | MAIN.py dédié à la génération de l'IHM | MAIN.py n'importe que l'IHM et ne contient que `build_interface` et `main` | `MAIN.py` | `test_architecture.test_main_only_builds_the_gui` | Implémenté et testé |
| REQ_COMMON_KH_3003 | Actions externalisées dans des sous-scripts ou classes | Contrôleur `gui/app.py`, traitements dans `core/`, dessin `plotting/`, rapport `report/` ; `core/` sans Tk | `ptbg/` | `test_architecture.test_processing_is_externalized_and_gui_free` | Implémenté et testé |
| REQ_COMMON_KH_3004 | Paquets documentés et alignés sur la version du noyau Python | `requirements.txt` figé et commenté, docs/DEPENDANCES.md (versions, licences, Python supportés, wheels, impacts de montée de version), relevé au démarrage | `system/environment.py`, `requirements.txt` | `test_architecture.test_third_party_libraries_are_documented_and_pinned` | Implémenté et testé |
| REQ_COMMON_KH_3005 | Mécanisme de compatibilité entre OS documenté | Différences d'OS centralisées dans `system/compat.py` ; docs/COMPATIBILITE_OS.md | `system/compat.py` | `test_architecture.test_os_specific_code_is_centralized` | Implémenté et testé |
| REQ_COMMON_KH_3006 | Code source commenté | Docstring par module, classe et fonction non triviale ; requis cités dans le code | tout `ptbg/` | `test_architecture.test_sources_are_commented` | Implémenté et testé |
| REQ_COMMON_KH_3007 | Aucune fonction inutile | Contrôle automatique : toute fonction définie est appelée ; analyse `vulture` | tout `ptbg/` | `test_architecture.test_no_unused_functions` | Implémenté et testé |

## 3.1 Définition de la base de temps

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_4100 | Raster défini et contrôlé : valeur, stabilité, croissance continue | 3 contrôles nommés (+ données manquantes), statut OK / AVERTISSEMENT / ERREUR | `core/time_base.py` (`analyze`, `_add_checks`) | `test_time_base.test_perfect_raster`, `test_duplicates_and_backward_are_errors` | Implémenté — interprétation à valider (tolérance 10 %, 10 intervalles) |
| REQ_COMMON_KH_4101 | Repérer et mettre en évidence les incohérences (données manquantes, mauvais phasage) | Trous (k × T), déphasage, doublons, retours arrière, horodatages illisibles et aberrants isolés ; marqueurs dans le TBM (y compris pour les horodatages illisibles), liste avec ligne CSV ; courbes interrompues ; croix sur cellules vides ; valeurs « nan »/« inf » et valeurs incompatibles avec le type comptées par variable | `core/time_base.py`, `plotting/monitor.py`, `core/sampling.py` | `test_time_base.test_missing_samples_detected_and_kept_in_regular_time`, `test_wrong_phasing_detected`, `test_robustesse.test_isolated_aberrant_timestamp_is_one_error_not_a_fake_gap`, `test_nan_and_inf_are_missing_values_not_text` | Implémenté et testé |
| REQ_COMMON_KH_4102 | Axe dédié « Time Base Monitor » détaillant conversion et statut, présent sur chaque template | Ajouté automatiquement sous chaque disposition, même axe des temps ; texte de conversion et statut par fichier | `plotting/monitor.py`, `plotting/renderer.py` | `test_package_report.test_every_template_has_time_base_monitor` | Implémenté et testé |
| REQ_COMMON_KH_4103 | Masquable seulement sans avertissement ni erreur | Bouton refusé avec explication ; réaffichage automatique si une alerte apparaît | `plotting/monitor.py` (`can_hide`), `gui/analysis_tab.py` | `test_package_report.test_monitor_hiding_rules`, `test_gui.test_monitor_hide_rules` | Implémenté et testé |
| REQ_COMMON_KH_4104 | Présent dans tous les rapports ; sinon indication de bonne construction | TBM sur chaque page ; s'il a été masqué, encadré « construction de la base de temps vérifiée : CONFORME » | `plotting/renderer.py`, `plotting/monitor.py` (`confirmation_text`) | `test_package_report.test_report_note_when_monitor_hidden` | Implémenté et testé |
| REQ_COMMON_KH_4105 | Traitement jamais bloqué ni instable | Lecture ligne par ligne par blocs, annulable, en arrière-plan ; une ligne malade (guillemet non fermé, octets nuls, cellule démesurée) n'atteint jamais la suite ; une erreur imprévue sur un fichier le marque en erreur sans arrêter les autres ; analyse vectorisée O(n), événements plafonnés ; axe en défaut remplacé par un message ; banc de 130 fichiers pathologiques et 40 corruptions aléatoires sans exception | `gui/tasks.py`, `core/csv_reader.py`, `core/data_package.py` (`load_source`), `core/time_base.py`, `plotting/renderer.py` | `test_robustesse` (29 cas dont `test_random_corruptions_never_raise`, `test_unexpected_error_is_isolated_to_its_file`), `test_time_base.test_pathological_inputs_never_raise`, `test_large_series_speed`, `test_csv_reader.test_cancellation` | Implémenté — qualification sur volumes réels à faire |
| REQ_COMMON_KH_4106 | L'utilisateur peut spécifier le raster normal avec un diagnostic associé | Période nominale + tolérance + diagnostic opérateur (imprimé dans le TBM et le rapport) | `gui/dialogs/time_base_dialog.py`, `core/data_package.py` (`configure_time`) | `test_time_base.test_user_nominal_period`, `test_package_report.test_project_roundtrip_with_relative_paths` | Implémenté et testé |
| REQ_COMMON_KH_4107 | Horodatage absolu ; jitter d'horloge ignoré | Origine absolue (hh:mm:ss, date-heure ou saisie) et axe absolu ; le jitter dans la tolérance n'est pas une anomalie ; affichage de l'horodatage BRUT par défaut, régularisation sur le raster en option par fichier (indiquée dans le TBM) | `core/time_parser.py`, `core/time_base.py` (`_regularize`), `core/data_package.py` (`Timeline`) | `test_time_base.test_jitter_ignored_within_tolerance`, `test_robustesse.test_raw_timestamps_are_displayed_by_default`, `test_package_report.test_absolute_timeline_aligns_plcs`, `test_gui.test_absolute_time_mode` | Implémenté — interprétation à valider (affichage brut par défaut) |

## 4.1 Fenêtre principale

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_5100 | Barre supérieure avec menu principal et chemin | Menus Fichier / Affichage / Base de temps / Outils / Rapport / Information + barre de chemin « paquet > fichier > variable » | `gui/menu_bar.py`, `gui/path_bar.py` | `test_gui.test_main_window_layout` | Implémenté et testé |
| REQ_COMMON_KH_5101 | Section Information : version, historique, sources, aide | Menu Information : version, CHANGELOG, sources (empreintes du code, bibliothèques, fichiers), aide, journal, traçabilité | `gui/info_windows.py` | `test_gui.test_information_windows_and_tree_toggle` | Implémenté et testé |
| REQ_COMMON_KH_5102 | Barre inférieure : utilisateur, date, journal, version | Barre d'état avec horloge, dernier message (clic = journal complet), version, avancement | `gui/status_bar.py`, `system/activity_log.py` | `test_gui.test_main_window_layout` | Implémenté et testé |
| REQ_COMMON_KH_5103 | Zone gauche = arbre des données | Arbre à gauche | `MAIN.py`, `gui/tree_panel.py` | `test_gui.test_main_window_layout` | Implémenté et testé |
| REQ_COMMON_KH_5104 | Zone droite principale et plus large | Zone graphique à droite, seule à s'étirer | `MAIN.py`, `gui/graph_area.py` | `test_gui.test_main_window_layout` | Implémenté et testé |
| REQ_COMMON_KH_5105 | Arbre masquable | Bouton « Masquer », barre d'accès rapide, menu Affichage, F9 | `gui/app.py` (`toggle_tree`) | `test_gui.test_information_windows_and_tree_toggle` | Implémenté et testé |
| REQ_COMMON_KH_5106 | Plusieurs onglets pour différentes dispositions | Onglets créés depuis un modèle, renommables, fermables | `gui/graph_area.py` | `test_gui.test_xy_tab_and_point_pick` | Implémenté et testé |

## 4.2 Arbre des données

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_5200 | Niveau supérieur = paquet de données | Paquets au 1er niveau ; le paquet actif est marqué | `gui/tree_panel.py` | `test_gui.test_tree_levels_and_types` | Implémenté et testé |
| REQ_COMMON_KH_5201 | 1er niveau enfant = fichiers CSV | Fichiers avec icône de statut | `gui/tree_panel.py` | `test_gui.test_tree_levels_and_types` | Implémenté et testé |
| REQ_COMMON_KH_5202 | Toutes les variables avec type Bool ou Float | Variables avec type (forçable par clic droit) ; Texte pour les états énumérés | `gui/tree_panel.py`, `core/signals.py` | `test_gui.test_tree_levels_and_types`, `test_package_report.test_type_override_and_report_text` | Implémenté — interprétation à valider (règle de typage, colonne constante) |
| REQ_COMMON_KH_5203 | Base de temps dédiée de chaque fichier | Nœud « Base de temps » (format, période, statut) | `gui/tree_panel.py` | `test_gui.test_tree_levels_and_types` | Implémenté et testé |

## 4.3 Modèles

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_5300 | Plusieurs modèles de disposition d'axes | 7 modèles : 1, 2, 3, 4 axes, analogique + logique, grille 2 × 2, temporel + X/Y | `core/arrangement.py` | `test_architecture.test_templates_fit_their_grid`, `test_package_report.test_every_template_has_time_base_monitor` | Implémenté et testé |

## 4.4 Outils graphiques

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_5400 | Curseur vertical simple activable par axe | Mode de curseur propre à chaque axe (axe actif) | `gui/analysis_tab.py`, `core/arrangement.py` | `test_gui.test_curves_cursors_mouse_and_keyboard` | Implémenté et testé |
| REQ_COMMON_KH_5401 | Porte l'instant et la valeur de la courbe sélectionnée | Étiquette : instant + valeur de l'échantillon réel de la courbe sélectionnée, point marqué | `plotting/renderer.py`, `core/sampling.py` | `test_package_report.test_cursor_labels_show_time_and_value`, `test_analysis_tools.test_nearest_and_hold_without_interpolation` | Implémenté — interprétation à valider (état maintenu des Bool) |
| REQ_COMMON_KH_5402 | Mode suivi + liste des valeurs de toutes les courbes de l'axe dans une fenêtre à droite | « Suivi souris » + panneau de lecture à droite (toutes les courbes, instant, ligne CSV) | `gui/analysis_tab.py`, `gui/reading_panel.py`, `core/readings.py` | `test_gui.test_tracking_mode` | Implémenté et testé |
| REQ_COMMON_KH_5403 | Double curseur : instant obligatoire et automatique pour chaque curseur | C1 et C2 posés d'office, instants affichés, Δt et 1/Δt, ΔV | `gui/analysis_tab.py`, `plotting/renderer.py` | `test_package_report.test_cursor_labels_show_time_and_value`, `test_gui.test_curves_cursors_mouse_and_keyboard` | Implémenté et testé |
| REQ_COMMON_KH_5404 | (identique à 5403) | Couvert par la même réalisation | idem 5403 | idem 5403 | Implémenté — interprétation à valider (énoncé dupliqué) |
| REQ_COMMON_KH_5405 | Curseur global synchronisant tous les axes | Ligne sur tous les axes (TBM compris), déplacée ensemble ; zoom commun (axe X partagé) | `plotting/renderer.py`, `gui/analysis_tab.py` | `test_gui.test_curves_cursors_mouse_and_keyboard` | Implémenté et testé |
| REQ_COMMON_KH_5406 | Curseur horizontal : signaux analogiques seulement | Refusé sur courbe Bool/Texte ; niveau, franchissements montants/descendants | `gui/app.py` (`horizontal_cursor`), `core/sampling.py` (`crossings`) | `test_gui.test_horizontal_cursor_only_on_float`, `test_analysis_tools.test_crossings_with_condition` | Implémenté et testé |
| REQ_COMMON_KH_5407 | Curseur horizontal conditionné par un Bool | Condition (1 à 3 Bool, ET/OU) ; franchissements retenus sous condition, périodes ombrées | `core/conditional.py`, `gui/dialogs/analysis_dialogs.py` | `test_analysis_tools.test_same_file_condition_uses_same_row`, `test_other_file_condition_holds_last_state` | Implémenté et testé |
| REQ_COMMON_KH_5408 | Curseur X/Y : deux curseurs ou point de croisement seul | Nuage X/Y, corrélation r et régression ; point désigné avec deux curseurs (X et Y) ou point seul ; C1/C2 reportés | `core/xy.py`, `plotting/renderer.py` | `test_analysis_tools.test_xy_same_file_and_cross_file`, `test_gui.test_xy_tab_and_point_pick` | Implémenté et testé |

## 4.5 Traitement conditionnel

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_5500 | *(énoncé vide dans la Rev. A)* | Proposition : statistiques (durée, min, max, moyenne, écart-type, durée au-dessus d'un seuil) des signaux analogiques pendant qu'une condition Bool est vraie ; export CSV | `core/conditional.py`, `gui/dialogs/analysis_dialogs.py` | `test_analysis_tools.test_conditional_statistics` | Proposition — énoncé vide à rédiger |

## 5 Sortie (rapport)

| Requis | Énoncé | Réalisation | Code | Test | Statut |
|---|---|---|---|---|---|
| REQ_COMMON_KH_6000 | Générer un rapport PDF | Matplotlib `PdfPages`, écriture atomique | `report/pdf_report.py` | `test_package_report.test_pdf_automatic_and_step_by_step` | Implémenté et testé |
| REQ_COMMON_KH_6001 | Modèle avec en-tête et zone graphique | En-tête + zone graphique (même rendu qu'à l'écran) + tableau des lectures | `report/pdf_report.py` | `test_package_report.test_pdf_automatic_and_step_by_step` | Implémenté et testé |
| REQ_COMMON_KH_6002 | Automatique ou pas à pas | Menu Rapport : automatique / pas à pas | `gui/app.py` | `test_gui.test_reports_and_project` | Implémenté et testé |
| REQ_COMMON_KH_6003 | Automatique = édition unique de l'onglet actif | Une page de l'onglet actif + traçabilité | `gui/app.py` (`automatic_report`) | `test_gui.test_reports_and_project` | Implémenté et testé |
| REQ_COMMON_KH_6004 | Pas à pas = génération séquentielle selon l'onglet actif (vue globale, analyse, curseurs, nuage X/Y…) | Captures figées successives (zoom, curseurs, X/Y, condition, commentaire), ordonnables | `gui/app.py` (`add_report_page`), `gui/dialogs/report_dialogs.py` (`PagesWindow`) | `test_gui.test_reports_and_project` | Implémenté et testé |
| REQ_COMMON_KH_6005 | En-tête : version, émetteur, date, fichiers sources, projet et unité, référence ou empreinte du projet | Tous ces champs ; SHA-256 des sources et du fichier projet ; annexe de traçabilité | `report/pdf_report.py` (`build_header`) | `test_package_report.test_pdf_automatic_and_step_by_step` | Implémenté — interprétation à valider (fichier projet .ptbg.json) |

## Synthèse

| Statut | Lignes |
|---|---|
| Implémenté et testé | 49 |
| Implémenté — interprétation à valider (voir POINTS_OUVERTS.md) | 12 |
| Proposition — énoncé vide à rédiger | 1 |
| Implémenté — qualification (cible ou volumes réels) à faire | 2 |
| **Total** | **64** |
