# Conventions et revue des templates de Sébastien

Lecture statique des dix fichiers reçus ; aucun script de template exécuté ou importé. Les fichiers reçus restent inchangés. Les références ci-dessous donnent leur empreinte pour identifier la version relue.

## Conventions retenues

- En-tête de rôle/version/historique pour les nouveaux modules et mention des requis concernés, sans présumer leur conformité.
- Commentaires par parties : dépendances, préparation, contrôles, dessin, sortie ; expliquer surtout les choix, unités et limites.
- Docstrings indiquant le rôle, les entrées/sorties et les refus contrôlés.
- Dessin dans une fonction recevant `ax, xdata, ydata` ; fenêtre, lecture CSV et logique temporelle séparées.
- Tests unittest et preuves datées. Une fonction ne doit pas rester en production sans usage justifié.

Les API existantes restent stables ; les noms ne sont pas tous renommés pour ressembler visuellement aux templates. Le style commun sera étendu aux prochains modules. La revue 3006 reste une lecture humaine de l'ensemble du code, pas un comptage de commentaires.

## Apport de chaque template

### `_csv_check(1).py`

Bilan CSV lisible. Le lecteur VISU conserve en plus les rejets et ne suppose pas toujours index.

SHA-256 : `946f331e6827822022f4fda5e91ef26473d373aa9594dc04934437d0dd9d21bf`.

### `_rate_limiter_class.py`

Rôle de classe, paramètres et sections. La logique de limitation de simulation ne fait pas partie de VISU.

SHA-256 : `5cd1bebbffdb99e33147894cfa8a3e53fdbffdfea73a0405f3e9636a5a9ae34c`.

### `_report_draw.py`

Composition de figures séparée du lecteur. Les noms de variables et huit axes imposés ne conviennent pas au lecteur générique.

SHA-256 : `dfcefb14065321acd152015e9322565926c9ff2f836d5fa2ebca65fd1980ee93`.

### `_template_filling.py`

Métadonnées et documentation de fonctions. Génération Word non intégrée, imports et fichiers propres au projet source.

SHA-256 : `fdad8aa19d4783bfdf7dee5801c137e0a6f85d6f1feb1de95a54a14443393f8a`.

### `_template_TRD_filling.py`

Liens entre essais, descriptions et requis. La matrice VISU conserve également les critères encore ouverts.

SHA-256 : `fa2fc98b89d5cf450e53eb3536c05d512d2843b82c0d6182e2d83a444b1d0b90`.

### `_unitary_test_class.py`

unittest, assertions explicites et sous-cas. Les assertions de blocs sont remplacées par celles du lecteur et du temps.

SHA-256 : `4089039ccefc1aeee925699f997f873f8d16c17507d0baf337b9c7e017336c22`.

### `_analog_draw.py`

Fonction recevant un axe, séries et libellés : organisation reprise dans src/_signal_draw.py.

SHA-256 : `9a15e1f845e07e0fe177b287bf119a90e08a706acb22c99e56bf80c25a7c36e2`.

### `_bool_draw.py`

Dessin séparé de la fenêtre. Le départ à zéro et le tracé en escalier ne sont pas repris sans justification métier.

SHA-256 : `a1011563119a816877238c8b2f98b6bcc7a20825783a0f266d7079f02460357a`.

### `_automated_report.py`

Traçabilité requis/tests/preuves. Export Word/Excel spécifique non intégré au runtime.

SHA-256 : `cf9431dec440234ffdac70bd5cf580504576095f4f3c9878d4686d70299ac0b9`.

### `_console_capture.py`

Principe de journalisation. Pas de remplacement global de stdout, stderr ou input dans Spyder ; journaux VISU dédiés.

SHA-256 : `46839ac235c2672d849a9dc6d0f94865a39a90ddb9b0c2fee714b867a8051406`.
