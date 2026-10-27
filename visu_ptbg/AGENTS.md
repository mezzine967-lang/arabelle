# Consignes de travail — VISU PTBG

Lire `MISSION_CODEX.md`, puis `README.md` et
`docs/REVUE_COPILOT_LOT1.md` avant toute modification.

## Finalité du projet

VISU PTBG est une application Python/Tkinter de diagnostic et de visualisation
de fichiers CSV issus de plusieurs PLC. Les priorités sont la robustesse de
l'import CSV et la justesse de la base de temps. La cible de livraison est
double : Windows et SUSE Linux Enterprise Server 15 SP7.

## Règles non négociables

- Ne jamais modifier un CSV source ni un script de `references_simulation/`.
- Ne jamais inventer, interpoler ou synchroniser silencieusement une donnée.
- Une cellule absente reste absente. Pour une valeur vide du signal choisi,
  les croix sont SUR le dernier point connu avant le manque et le premier
  point connu après. Elles reprennent leurs valeurs réelles. Aucune bande
  séparée, aucun trait à travers le manque, aucune valeur de remplacement.
- Les croix sont réservées aux champs vides constatés dans le CSV. Un texte
  invalide, une ligne rejetée, un doublon ou un écart temporel ne suffit pas
  à affirmer une perte et ne déclenche pas de croix à lui seul.
- Un intervalle temporel anormal n'est pas, à lui seul, une preuve de perte
  d'échantillon.
- Employer « trou probable » et « changement de fréquence probable » pour les
  heuristiques du Lot 2A. Ne jamais créer un échantillon ni une croix à partir
  de ces seuls constats.
- Conserver les règles temporelles configurables dans `src/regles_temps.py` et
  indiquer l'unité ou le caractère sans unité de chaque seuil.
- Appliquer le requis 2304 : la première colonne du CSV est toujours la base
  de temps, quel que soit son nom. Ne pas chercher ni choisir une autre colonne.
- Ne pas comparer deux PLC ligne par ligne et ne pas recaler leurs horloges.
- Isoler les erreurs par fichier : un CSV malade ne doit pas bloquer les autres.
- Conserver les numéros physiques des lignes et les valeurs brutes utiles au
  diagnostic.
- Garder la logique métier dans `src/`, testable sans lancer Tkinter.
- Ne pas traiter une remarque Copilot comme une exigence : vérifier d'abord le
  code, les fichiers réels et les requis disponibles.
- Ne pas déclarer un requis validé uniquement parce que les tests passent.

## Méthode attendue

Mourad demande un code simple et expliqué pour que Sébastien puisse le
reprendre : noms explicites, petites fonctions à rôle unique, commentaires
sur les raisons et les limites, exemples d'utilisation. Éviter les abstractions
génériques sans besoin concret. Tenir à jour `docs/REPRENDRE_LE_CODE.md`.

1. Lire et comprendre l'état existant avant de coder.
2. Faire un audit court et citer le fichier ou le test qui prouve chaque défaut.
3. Corriger seulement les défauts confirmés et rester dans la mission courante.
4. Ajouter un test de régression utile pour chaque correction de comportement.
5. Exécuter les tests rapides puis les tests d'intégration séparément.
6. Donner le nombre de tests réussis, échoués et ignorés, les limites de
   l'environnement et la liste des fichiers modifiés.

Ne pas commencer la synchronisation multi-PLC, l'interpolation, le rapport PDF,
la fabrication des exécutables ni une refonte graphique générale sans nouvelle
demande explicite de Mourad.

