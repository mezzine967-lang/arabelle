# Time Base Monitor v0.5.0

Le moniteur est créé automatiquement dans `MAIN.py` et actualisé à chaque sélection ou nouvelle analyse d'un CSV. `src/moniteur_temps.py` prépare son état indépendamment de tkinter. L'axe reprend les bornes temporelles du fichier sélectionné ; aucun axe commun n'est construit entre les sources.

Un axe vert signifie que les intervalles lus sont réguliers selon le contrôle disponible. Sans profil saisi, cela décrit seulement la régularité observée : l'unité et la règle métier restent à confirmer. Avec un pas attendu et une tolérance, l'état se réfère à ces choix. Les doublons sont orange, les retours arrière rouges et les intervalles positifs hors tolérance violets. Ces repères signalent des écarts à examiner ; ils ne prouvent pas seuls une perte de données.

Le bouton de masquage est actif uniquement lorsque l'état est sans avertissement ni erreur. Après masquage, une indication textuelle confirme l'état régulier. Une nouvelle sélection réaffiche automatiquement le moniteur. En présence d'une anomalie, d'une lecture partielle, d'un temps invalide ou de plusieurs pas non qualifiés, le bouton reste désactivé.

| Requis | Réalisation actuelle | Limite restante |
| --- | --- | --- |
| 4100 | Période observée, stabilité, doublons et retours arrière alimentent l'axe | Validation des périodes métier par type de source |
| 4101 | Les anomalies connues sont repérées à leur position temporelle | Un écart ne suffit pas à prouver une donnée manquante ou un mauvais phasage entre PLC |
| 4102 | Axe dédié nommé « Time Base Monitor », créé automatiquement dans la fenêtre | À intégrer aux futures vues de courbes |
| 4103 | Masquage bloqué si avertissement ou erreur | Essai visuel Windows de la nouvelle version |
| 4104 | Non réalisé | Le moniteur devra apparaître dans les futurs rapports graphiques, ou être remplacé par une confirmation conforme |
| 4105 | L'anomalie n'arrête ni la sélection ni l'analyse des autres CSV | Essais de charge sur les tailles réelles à confirmer |
| 4106 | Pas normal et tolérance restent saisissables avec diagnostic | Règles métier à fournir |
| 4107 | Non réalisé | Définition de l'horodatage absolu et règle précise sur le jitter |

Quatre tests sans écran couvrent le masquage d'un pas régulier, le positionnement d'un doublon, l'écart positif au pas choisi et le besoin de configuration en cas de pas variables. Avec les tests antérieurs, la suite locale comporte 55 cas. Le rendu tkinter doit être vérifié sur Windows 11 avec Python 3.11.10.
