# Historique des modifications — VISU PTBG

| Version | Date | En une ligne | Tests |
|---|---|---|---|
| 1.1.0 | 2026-11-06 | remarques des premiers essais ; deux anomalies corrigées | 164 |
| 1.0.0 | 2026-10-29 | première version | 145 |

## 1.1.0 — 2026-11-06

**Corrections**

- Base de temps : un pas pile à la limite de la tolérance (11 ms pour 10 ms ± 10 %) est
  conforme où qu'il soit dans le fichier. Les pas, périodes et tolérances sont calculés en
  nanosecondes entières : 4988 − 4977 = 11 ms tout rond (avant, un arrondi mettait
  producer2 et producer3 en avertissement, pas producer1).
- Jitter max = plus grand écart d'un pas à la période, en valeur exacte (1 ms pour un pas de
  11 ms sur 10 ms).
- Condition sur un Bool d'un autre fichier : fausse pendant un trou de ce fichier et après
  sa fin (avant, son dernier état était gardé).

**Nouveautés**

- Valeurs du CSV : clic droit sur une variable (ou sur un marqueur du TBM > « Voir dans le
  CSV ») pour voir, ligne par ligne, le texte du fichier à côté de la valeur lue, le Δt et
  une remarque sur chaque anomalie ; case « Seulement les anomalies » ; double-clic sur une
  ligne = curseur global à cet instant.
- Barre sous le graphique, en français : Réinitialiser la vue, Zoomer, Déplacer la vue
  (Échap pour les relâcher), ← Retour arrière, Refaire →, Enregistrer en image.
- Ctrl+Z / Ctrl+Y (menu Édition) ; fermer un paquet ferme les onglets qui ne montraient
  que lui.
- Curseurs posés sur la mesure la plus proche (Δt exact, en ms) ; Ctrl + clic ou
  Ctrl + glisser pour un curseur libre. Activer un curseur relâche Zoomer / Déplacer et le
  place dans la vue affichée. Mode « suivi souris » retiré.
- Axes : titre, unité, hauteur (aussi en glissant la séparation entre deux axes), couleur,
  épaisseur et trait de chaque courbe ; clic sur une courbe ou sa légende pour la
  sélectionner ; légende = nom de la variable.
- Rapport : paysage ou portrait au choix ; page graphique seule, puis les lectures, puis
  la page d'identification des fichiers.
- Time Base Monitor : légende hors de la courbe, échelle adaptée aux Δt, détail d'une
  anomalie au survol.
- Nuage X/Y : droite de régression retirée.

## 1.0.0 — 2026-10-29 — première version

| Domaine | Contenu |
|---|---|
| Lecture des CSV | contrôle du séparateur, de l'encodage UTF-8, de l'en-tête, des métadonnées et de la taille maximale ; fichiers abîmés lus sans exception, sans perte silencieuse ni valeur inventée, chaque anomalie citée avec sa ligne ; lecture en arrière-plan avec avancement et annulation |
| Signaux | types Bool / Float automatiques et forçables, états texte, groupes binaires (détectés ou créés) |
| Base de temps | compteurs (ns à h, cycles), heure à la nanoseconde avec passage de minuit, date-heure ; pré-déclenchement ; contrôles de période, stabilité, croissance, trous, déphasage, changements de fréquence, horodatages illisibles et aberrants ; réglages par fichier (période nominale, tolérance, origine absolue, décalage, affichage régularisé, diagnostic opérateur) |
| Plusieurs PLC | paquets de données, axe des temps relatif ou absolu, comparaison des sources |
| Time Base Monitor | dans chaque onglet ; masquage refusé en cas d'alerte |
| Diagnostic | par fichier : bilan, points à vérifier, tableaux, ligne CSV de chaque événement |
| Interface | menus, barre de chemin, arbre masquable, onglets fermables à 7 modèles de disposition, barre d'état, aide intégrée |
| Graphiques | axes quadrillés ; courbes réduites pour l'affichage sans perdre les pics ; cellules vides marquées, trous de temps visibles ; légendes, noms des pistes et étiquettes des curseurs déplaçables à la souris ; bouton « Vue d'origine » |
| Curseurs | simple, double (Δt, 1/Δt, ΔV), global, suivi souris avec panneau de lecture, horizontal avec franchissements, condition Bool, nuage X/Y avec corrélation ; valeurs lues sur les échantillons réels, jamais interpolées |
| Traitement conditionnel | statistiques des signaux pendant qu'une condition Bool est vraie, export CSV |
| Rapports | PDF automatique ou pas à pas, en-tête complet, Time Base Monitor, lectures, page de traçabilité |
| Projet | fichier `.ptbg.json` (chemins relatifs, réglages, onglets, curseurs, pages du rapport) |
