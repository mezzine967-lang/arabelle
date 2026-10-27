# Cible Windows 11 64 bits et registre des dépendances

## Décision communiquée par Sébastien

- système principal : Windows 11, 64 bits ;
- interpréteur attendu : Python 3.11, cohérent avec la version utilisée par Spyder ;
- chaque module et sa version doivent être tracés ;
- toute montée de version de Python ou d'un module impose une analyse d'impact.

La seconde cible demandée au projet reste SLES 15 SP7. Une réussite sous
Windows ne constitue donc pas automatiquement une qualification SLES.

## Dépendances directes de VISU

| Élément | Utilisation | Version à retenir |
|---|---|---|
| Python | moteur et bibliothèque standard | branche 3.11, version exacte à relever sur le poste cible |
| Tcl/Tk et `tkinter` | interface graphique | versions liées à l'installation Python cible |
| Matplotlib | graphiques du signal et de la base de temps | version installée à relever puis à qualifier |
| Spyder | environnement de développement, non requis par le moteur | version du poste Arabelle à relever |

Les Lots 2A et 2B n'ajoutent aucune dépendance externe. Les modules du Lot 2A
(`decimal`, `statistics`, `collections`, `dataclasses`, `typing`) appartiennent
à Python 3.11 ; le Lot 2B réutilise Matplotlib.

## Dépendances transitives à tracer

Le relevé automatique couvre Matplotlib, NumPy, contourpy, cycler, fonttools,
kiwisolver, packaging, Pillow, pyparsing, python-dateutil et six. Leur présence
et leur version sont consignées dans `resultats/environnement_*.json` au
lancement de l'interface. Une dépendance absente n'est jamais installée
automatiquement par VISU.

## Procédure de qualification Windows

1. Lancer la v0.7.7 avec le Python 3.11 64 bits réellement fourni avec Spyder.
2. Conserver le fichier `resultats/environnement_*.json` produit au lancement.
3. Exécuter `verifier_robustesse.py` et conserver son journal JSON.
4. Vérifier qu'aucun test n'est en échec ou ignoré et que les sources restent inchangées.
5. Tester manuellement l'ouverture, l'import de plusieurs CSV, la base de temps,
   la courbe et les croix sur un fichier contenant une cellule vide.
6. Après acceptation, figer dans la documentation les versions exactes observées.

Il serait incorrect de recopier les versions du poste Linux de développement
et de les annoncer comme compatibles Windows sans cet essai.

