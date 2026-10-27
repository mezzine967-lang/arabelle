# Règles du lecteur CSV v0.3

## Comportements testés

| Situation | Réponse du lecteur |
| --- | --- |
| Ligne ou colonne supplémentaire conforme au schéma du fichier | Conservée, pas de nombre de lignes ou de colonnes métier imposé |
| Trop ou trop peu de champs sur une ligne | Rejet tracé avec texte, champs, motif et plage de lignes physiques |
| Ligne vide / en-tête répété | Signalé et conservé dans `rejected_rows` |
| Guillemets non refermés / syntaxe CSV invalide | Lecture partielle, fin du fichier conservée sans tentative de reprise |
| Champ multiligne entre guillemets | Champ intact, début/fin physiques enregistrés |
| Nom de colonne vide ou dupliqué | Refus explicite, aucune colonne écrasée par un dictionnaire |
| Fichier manquant ou accès refusé | Erreur interceptée par les lanceurs, message et journal |
| Fichier vide / en-tête seul / point temporel unique | Pas de validation trompeuse de la progression temporelle |
| Nombre et texte mélangés | Valeurs conservées, type `mixte` signalé, schéma métier à confirmer |
| NaN, infini ou temps absent | Aucun remplacement par zéro, statistiques de temps non calculées si un temps est invalide |
| Plusieurs colonnes candidates pour le temps | Choix explicite demandé, pas de priorité arbitraire |
| Temps répété, retour arrière, plusieurs pas | Avertissements sans correction de la chronologie |
| Temps décalés entre scénario et report | Comparaison refusée, aucune synchronisation implicite |

## Sens des champs

`data_rows` compte les enregistrements de structure valide, même si une cellule est vide ou si un temps est invalide. Il ne signifie pas « lignes métier validées ». Les lignes de longueur incorrecte sont hors de ces statistiques mais restent dans `rejected_rows`. Le champ `time_scope` rappelle cette limite.

`analysis_complete` signifie que le parseur a atteint la fin du fichier. Il ne garantit pas l'absence de rejets ni la conformité à tous les requis. `status` vaut `ok`, `warning` ou `error`. Les erreurs de format en amont lèvent `CsvDiagnosticError` avec un code et des détails, sans supprimer le fichier source.

`raw_text` est le texte décodé avec fins de lignes conservées, pas une nouvelle copie binaire certifiée du fichier. Le fichier source reste intact, et son empreinte SHA-256 est relevée. Pour une erreur de décodage, le fichier source demeure la référence brute.

La comparaison de colonnes reste textuelle : `1` et `1.0` sont deux représentations différentes. L'égalité des temps est contrôlée numériquement avant la comparaison. Il ne s'agit pas d'une reconstruction multi-horloges.

## Encodage et profil

UTF-8 par défaut, reconnaissance des BOM UTF-8 et UTF-16. Un fichier Windows-1252 peut être lu avec `encoding="cp1252"` explicitement. Pas de repli automatique en Latin-1 qui ferait passer des octets incorrects pour du texte valide.

La détection du séparateur se fonde sur le premier en-tête non vide parmi virgule, point-virgule, tabulation et barre verticale. En cas d'ambiguïté, un choix explicite est nécessaire. Le profil suppose un en-tête explicite ; les préambules de métadonnées et formats à en-tête multiligne nécessitent un profil validé. Des champs de données multilignes entre guillemets sont pris en charge.

Décimale point par défaut, virgule sur sélection explicite. Les séparateurs de milliers ne sont pas interprétés. Les noms de colonnes sont normalisés uniquement par retrait des espaces extérieurs, et leurs noms d'origine restent disponibles.

## Ressources et limites

- Garde-fou de lecture à 50 MiB par fichier par défaut, configurable dans l'API. C'est une limite de ce prototype, pas une limite issue des requis. Le traitement en flux des très gros fichiers et les performances restent à développer et qualifier.
- Taille maximale d'un champ : limite courante du module standard `csv`, sans modification globale. Un dépassement produit un refus d'en-tête ou un diagnostic CSV partiel qui conserve le bloc restant.
- Analyse numérique limitée à 1000 caractères par valeur et à un exposant décimal de valeur absolue au plus 1000. Hors enveloppe, la valeur n'est pas déclarée numérique valide. Les valeurs originales sont conservées.
- Les écarts temporels sont calculés avec `Decimal`. Les résumés JSON utilisent des entiers, des flottants d'affichage ou du texte pour les extrêmes. Les temps bruts restent disponibles ; aucune conversion n'est réécrite dans les données.
- Le logiciel ne peut pas promettre de continuer après un manque de mémoire système ou une panne matérielle. Les refus contrôlés et les limites sont testés sur les cas fournis, pas sur tout fichier possible.
- Dates absolues, fuseaux horaires, identification des unités, politique de reprise métier et synchronisation : non implémentés.
- L'API peut lever une erreur contrôlée. L'IHM devra l'intercepter comme les lanceurs actuels ; ne pas appeler cette API en supposant un succès systématique.

## Dépendances et preuves

Le lecteur et les tests utilisent uniquement la bibliothèque standard Python. Les bibliothèques des scripts de simulation ne deviennent pas des dépendances du lecteur.

La sortie Windows/Python 3.11.10 transmise par Mourad concerne v0.2 et ses huit tests. La nouvelle suite de 43 tests est à relancer sur ce poste avec `verifier_robustesse.py`, qui produit un journal daté, relève l'interpréteur et vérifie que les sources n'ont pas changé pendant les tests.

Le journal `essai_linux_v03.json` provient de l'essai local sous Python 3.12.14/Linux 64 bits. Il ne constitue pas une preuve de réussite sur Windows/Python 3.11.

## Référence technique

Documentation officielle du module `csv`, Python 3.11 : https://docs.python.org/3.11/library/csv.html (consultée le 23 octobre 2026). Utilisation de `reader`, `strict=True`, des numéros de lignes physiques et de la conservation des fins de lignes. Cette documentation ne remplace pas le contrat de fichier métier.

Prochaine étape après l'essai Windows : définir explicitement le profil d'import et le contrat temporel à partir des requis, notamment l'unité et l'origine de `index`, avant tout recalage des données.
