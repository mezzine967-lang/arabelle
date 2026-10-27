# Requis 4103 — masquage du moniteur de courbe

La vue du signal permet à l'utilisateur de masquer puis réafficher le Time Base
Monitor uniquement si le modèle de diagnostic autorise ce masquage. Si un
avertissement, une erreur ou une situation non concluante existe, le bouton
est désactivé. Le nom de la base de temps et son unité restent sur la courbe.
La décision ne dépend pas du zoom et aucune donnée ou règle n'est modifiée.

Fichiers : `src/vue_signal.py` assemble le bouton et sa fonction documentée ;
`tests/test_moniteur_quantitatif.py` contrôle les cas réguliers et dupliqués,
l'interdiction de masquage, le retour à l'affichage et le libellé temporel.
Les bibliothèques déjà employées sont répertoriées dans `DEPENDANCES.md`.

Limites : un seul modèle de courbe existe aujourd'hui. Les tests de dessin sont
réalisés sans fenêtre Tk native ; l'essai interactif Windows et SLES reste à
faire. Le diagnostic historique du modèle de masquage doit être revu lorsque
les règles temporelles seront acceptées par le métier. Requis non déclaré
globalement validé.
