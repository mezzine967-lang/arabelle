# Points ouverts — interprétations à faire valider

Chaque requis est réalisé (voir TRACABILITE_REQUIS.md). Lorsque l'énoncé de la Rev. A
est incomplet, ambigu ou commenté par le relecteur, l'interprétation retenue est
décrite ci-dessous ; elle est **paramétrable ou isolée dans un module**, de sorte qu'une
réponse différente ne remette pas l'architecture en cause.

| # | Requis | Question | Interprétation retenue | Où la modifier |
|---|---|---|---|---|
| 1 | REQ_COMMON_KH_2305 (commentaire « attention au pretrig ! temps négatif / référence absolue comme en ALSPA ? ») | Comment est représenté le pré-déclenchement ? | Un compteur peut être négatif ; t = 0 est l'instant de déclenchement ; l'origine absolue saisie est la date-heure de ce déclenchement. Les temps négatifs sont conservés et une ligne « déclenchement (t = 0) » est tracée. | `core/time_parser.py`, `plotting/renderer.py` |
| 2 | REQ_COMMON_KH_2310 « Maximal size xxxMo » | Quelle taille maximale ? | Paramètre `max_file_size_mb`, défaut **500 Mo** (≈ 0,5 à 1 Go de mémoire), modifiable dans Outils > Préférences. | `config.py` |
| 3 | REQ_COMMON_KH_3001 « Python 3.6 at least » (commentaire : upgrade Python 3.11 possible sur SLES 15) | 3.6 est-il un minimum ou une cible stricte ? | Lu comme un minimum : développement en **3.11**, code vérifié de 3.10 à 3.14. Python 3.6 (fin de vie 2021) n'est pas supporté : il imposerait numpy 1.19 / matplotlib 3.3. | `version.py` (`MIN_PYTHON`) |
| 4 | REQ_COMMON_KH_3000 (commentaire « ou Windows ? double compatibilité ») | Quelle cible ? | **Double compatibilité** Windows 11 64 bits (Spyder 6) et SLES 15 SP7, confirmée par le demandeur. | `system/compat.py` |
| 5 | REQ_COMMON_KH_2201 (2e occurrence) « Binary group signal » — identifiant dupliqué | Qu'est-ce qu'un groupe binaire dans les CSV PTBG ? Faut-il renuméroter l'exigence ? | Ensemble ordonné de colonnes Bool (bit 0 = 1er membre) : détecté automatiquement pour `NOM[i]` / `NOM.i`, ou créé par l'utilisateur ; affiché en pistes regroupées, lu comme mot binaire. Un mot entier codant des bits n'est pas décodé. | `core/signals.py` (`BinaryGroup`, `detect_indexed_groups`) |
| 6 | REQ_COMMON_KH_5202 « type Bool or Float » | Existe-t-il une convention de typage dans les CSV ? | Règle automatique : `true/false`, ou nombres 0/1 avec au moins un 0 et un 1 → Bool ; sinon Float. Une colonne constante reste Float. Colonnes d'états texte (« STOP », « ACTIVE », vus dans les CSV de simulation) → type Texte, hors spécification. Type forçable par variable. | `core/signals.py` (`auto_type`) |
| 7 | REQ_COMMON_KH_4107 « Constitute absolute timestamp. Clock jitter ignored » | Que signifie « jitter ignoré » ? | (a) le jitter dans la tolérance n'est pas une anomalie ; (b) l'horodatage affiché est **régularisé** : droite t = a + T·k ajustée par blocs alignés sur le raster (les trous restent visibles, aucune mesure créée). Option « horodatage brut » disponible par fichier. | `core/time_base.py` (`_regularize`), dialogue Base de temps |
| 8 | REQ_COMMON_KH_4107 / 2102 | D'où vient l'origine absolue d'un compteur ? | Horodatage hh:mm:ss (date saisissable) ou date-heure : absolu d'office. Compteur : origine saisie par l'utilisateur. L'axe absolu n'est proposé que si chaque fichier a une origine. Aucun recalage automatique entre PLC : décalage manuel explicite, affiché dans le TBM. | `core/data_package.py` (`Timeline`) |
| 9 | REQ_COMMON_KH_4100 / 4106 — tolérance | Quelle tolérance par défaut sur la période ? | **10 %** de la période (préférence), réglable par fichier ; un changement de fréquence = 10 intervalles consécutifs cohérents hors raster. | `config.py` |
| 10 | REQ_COMMON_KH_2307 — unité du compteur | Unité d'un compteur sans unité (colonne « index » des CSV fournis, pas de 20) ? | Lue dans l'en-tête (`t_ms`, `Temps (s)`, `time[us]`…), sinon **ms supposée** (information affichée dans le TBM), réglable. | `core/time_parser.py`, `config.py` |
| 11 | REQ_COMMON_KH_5404 (énoncé identique à 5403) | Exigence différente attendue (Δt, écart de valeurs ?) | Couvert par la même réalisation : C1 et C2 posés d'office avec leurs instants, plus Δt, 1/Δt et ΔV par courbe. | `plotting/renderer.py`, `core/readings.py` |
| 12 | REQ_COMMON_KH_5407 / 5500 (énoncé 5500 **vide**) | Quel traitement conditionnel est attendu ? | Curseur horizontal : franchissements retenus seulement si la condition Bool est vraie (même ligne pour le même fichier ; dernier état connu pour un autre fichier). Section 4.5 : statistiques sous condition (durée, min, max, moyenne, écart-type, durée au-dessus d'un seuil). | `core/conditional.py` |
| 13 | REQ_COMMON_KH_5401 « cross value » | Valeur interpolée ou échantillon ? | **Échantillon réel**, jamais interpolé : le plus proche pour un Float, l'état maintenu (précédent) pour un Bool ; instant et ligne CSV de l'échantillon affichés. | `core/sampling.py` |
| 14 | REQ_COMMON_KH_2301 / 2302 / 2303 | Faut-il refuser ou tolérer un fichier non conforme ? | Séparateur ≠ virgule et encodage ≠ UTF-8 : fichier **refusé** avec diagnostic (les autres fichiers restent chargés). Métadonnées, lignes « # », lignes mal formées : **tolérées et signalées**. | `core/csv_reader.py` |
| 15 | REQ_COMMON_KH_6005 « Project Name & Unit », « Project file reference or Hash » | Origine de ces champs ? | Saisis dans Rapport > En-tête ; référence = texte libre + nom du fichier projet `.ptbg.json` ; empreinte = SHA-256 du fichier projet enregistré ; SHA-256 de chaque CSV source. | `report/pdf_report.py` |

## Qualification restant à consigner

- Essai sur **Windows 11 / Spyder 6** au poste et sur le **Service Unit SLES 15 SP7** réel
  (procédure de 15 minutes : COMPATIBILITE_OS.md § 5) avec les versions réellement
  présentes, relevées par `python tools/audit_environnement.py`.
- Essai de performance sur les volumes réels de PTBG (taille, nombre de colonnes, de
  fichiers) pour confirmer la valeur de REQ 2310.
