# Mission courante — programme fonctionnel et couverture des requis, v1.0.0 candidate

Demande de Mourad : poursuivre le programme reçu dans GitHub jusqu'aux fonctions
réalisables et testées. Décisions confirmées dans cette conversation :

- Groupe binaire = plusieurs colonnes Bool à regrouper.
- Lecture horizontale conditionnelle = Bool vrai sur la même ligne ; Bool
  absent ou invalide exclu, sans interpolation.
- Aucune référence commune entre PLC n'est disponible. Ne pas fabriquer de
  temps absolu, de synchronisation ou de déphasage inter-PLC.

État courant : `docs/VALIDATION_V100.md` et `docs/MATRICE_REQUIS_V100.json`.
Les sections ci-dessous constituent l'historique de la mission précédente.

## Historique v0.9.0

La demande explicite de Mourad (« fait tout ce que tu peux réaliser ») autorise
les onglets, types, curseurs et rapports demandés par les requis. Les anciennes
interdictions de lots plus bas sont historiques. Aucune synchronisation,
interpolation ni exécutable ajouté. Voir docs/AVANCEMENT_V090.md et
docs/QUESTIONS_SEBASTIEN_V090.md pour le périmètre réel et les points ouverts.

La v0.9.0 ajoute travail de fond pour les lectures, arrangements persistants,
superposition du même CSV, curseurs, X/Y du même CSV, PDF et résultats de tests
structurés. Les calculs temporels existants sont conservés. Essai Tk natif requis.

Autorisation utilisateur : poursuivre les requis réalisables et identifier les
blocages précis. Cette étape ajoute HH:MM:SS.fraction (2306) et le dossier
utilisateur des journaux (contribution 3005). Les origines absolues et règles
inter-PLC restent à clarifier. Voir docs/HEURES_V080.md. Les autres fonctions
encore absentes sont du travail restant, pas automatiquement des blocages.

Requis 4102 : présentation plus lisible, symboles distincts et résumé du fichier
entier. Aucun changement des calculs ou seuils. Voir docs/LISIBILITE_V078.md.

**v0.7.7 :** reprendre dans le graphique les catégories du moteur temporel :
jitter, trou probable et changement de fréquence probable. La tolérance du pas
est expliquée comme une limite acceptable, pas comme le jitter mesuré. Les
croix restent exclusivement liées aux cellules vides du signal.

**v0.7.6 :** afficher les `Δt`, le raster et sa tolérance directement sous la
courbe du signal. Ne jamais calculer à travers une ligne rejetée et ne jamais
transformer un écart temporel en preuve automatique de perte de donnée. Les
croix v0.7.3 restent exclusivement liées aux cellules vides du signal.

Voir `docs/LOT2B_MONITEUR_QUANTITATIF_V076.md`.

## Étape précédente — moteur de base de temps

**v0.7.5 :** distinguer les faits temporels et les interprétations probables,
sans interpolation ni synchronisation. Les règles sont centralisées dans
`src/regles_temps.py`. La cible principale est Windows 11 64 bits avec Python
3.11 ; aucune dépendance externe n'est ajoutée par ce lot.

## Étape précédente — première colonne imposée comme temps

**v0.7.4, décision de Mourad du 27 octobre 2026 :** appliquer littéralement le
requis 2304. La première colonne de chaque CSV est la base de temps, quel que
soit son nom. L'interface l'affiche sans permettre d'en choisir une autre. Les
croix v0.7.3 restent sur la courbe et ne concernent que les cellules vides du
signal choisi. Voir `docs/PREMIERE_COLONNE_V074.md`.

## Étape précédente — croix sur la courbe aux données manquantes

**v0.7.3, étape demandée et précisée par Mourad le 26 octobre 2026 :**
une croix au dernier point connu avant une absence du signal dans le CSV,
une croix au premier point connu après, et un vide entre les deux. Les croix
sont sur la courbe, exclusivement pour les champs vides du signal choisi.
Un simple saut temporel ne prouve pas une perte et ne produit pas de croix.
Voir `docs/CROIX_V073.md`. Attendre le retour sur cet affichage avant la suite.

## Historique de la mission de stabilisation précédente

**Mise à jour v0.7.2 :** la stabilisation a été poursuivie dans la conversation
initiale. Voir `docs/STABILISATION_V072.md`, les preuves et le diff associés.
Les consignes ci-dessous conservent le périmètre initial ; elles ne demandent
pas de refaire les corrections déjà présentes. Prochaine étape : essai humain
Windows du parcours README, qualification SLES lorsque l'environnement sera
accessible, puis décision sur le Lot 2.

## Situation de départ

La v0.6.0 est la dernière archive de référence conservée séparément. Le dossier
courant est une v0.7.1 de travail. Elle ajoute notamment :

- l'inspection quantitative des intervalles `Δt` ;
- des croix séparées pour les valeurs de signal absentes ou invalides, sans
  remplacer ces valeurs ;
- la découverte récursive des CSV, extension insensible à la casse ;
- l'isolation des erreurs par fichier ;
- une lecture davantage réalisée en flux ;
- la reconnaissance de nouveaux noms temporels, dont `timestamp_reel_ms` ;
- un diagnostic temporel partiel autour des lignes invalides, sans créer de
  faux intervalle à travers une rupture.

La preuve locale actuelle indique **90 tests rapides réussis, 0 échec,
0 ignoré**, puis **1 test d'intégration réussi** sous Python 3.12/Linux.
Cela ne constitue pas une qualification Windows ni SLES 15 SP7. Les essais
natifs Tkinter n'ont pas encore été réalisés dans cet environnement.

## Objectif de cette mission

Effectuer une relecture technique indépendante de la v0.7.1 et produire une
version candidate fiable pour l'essai humain sous Windows, sans ouvrir le Lot 2.

### 1. Auditer avant de modifier

Comparer le dossier courant à l'archive v0.6.0 fournie dans le paquet. Vérifier
en priorité :

- `src/diagnostic_csv.py` : lecture en flux, changement du fichier entre les
  passes, encodage, lignes multilignes, mémoire et exceptions non interceptées ;
- `src/inspection_temps.py` et `src/trace_temps.py` : calcul exact de `Δt`,
  provenance physique des lignes et absence de pont à travers un rejet ;
- `src/signal_csv.py` et `src/trace_signal.py` : une absence reste `NaN`, les
  vrais zéros restent des mesures et les croix ne créent aucune ordonnée ;
- `MAIN.py` : raccordement des nouveaux parcours sans déplacer de logique
  métier importante dans l'interface ;
- `verifier_robustesse.py` : limites déjà recensées sur le hachage des fichiers
  racine, la lecture entière pour SHA-256 et l'extraction textuelle du bilan.

Pour chaque problème trouvé, donner une preuve reproductible. Si une remarque
de Copilot ne correspond pas au code réel, la rejeter explicitement et ne pas
modifier le programme pour elle.

### 2. Corriger seulement les défauts confirmés du Lot 1

Le périmètre autorisé est l'import CSV robuste, la détection de la colonne
temporelle, le diagnostic temporel partiel et les repères déjà présents. Les
corrections doivent préserver les API existantes autant que possible et être
couvertes par des tests ciblés.

Cette ancienne consigne de choix entre noms temporels est remplacée en v0.7.4
par le requis 2304 : la position de la première colonne impose le temps.

### 3. Valider et rendre un bilan clair

Exécuter séparément :

```text
python verifier_robustesse.py
python -m unittest discover -s tests_integration -v
```

Le compte rendu final doit contenir :

- les problèmes confirmés et ceux écartés ;
- le diff expliqué fichier par fichier ;
- les tests exécutés, réussis, échoués et ignorés ;
- la confirmation d'intégrité des CSV et scripts de référence ;
- les limites restantes, notamment l'absence d'essai natif Windows/SLES ;
- une procédure courte d'essai manuel pour Mourad sous Windows.

## Suite prévue, mais hors de cette mission

Après validation humaine de la v0.7.1, le Lot 2 devra commencer par définir avec
le métier : unité et origine du temps, raster attendu par source, tolérance de
jitter, pré-déclenchement, règle permettant de parler d'échantillon manquant,
et sens de `timestamp_reel_ms` par rapport à `timestamp_ideal_ms`.

Tant que ces réponses manquent, ne pas implémenter de dérive d'horloge, de
synchronisation multi-PLC, d'interpolation ou de conclusion automatique sur
une perte de données.

