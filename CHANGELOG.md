# Historique des modifications — VISU PTBG

Affiché par Information > Historique des modifications (REQ_COMMON_KH_5101).
Chaque nouvelle version incrémente `ptbg/version.py` et ajoute une entrée en tête de ce
fichier : ce qui change, pourquoi (requis, remarque de relecture, anomalie constatée),
et le nombre de tests.

| Version | Date | En une ligne | Tests |
|---|---|---|---|
| 1.1.0 | 2026-11-04 | remarques du relecteur sur les premiers essais ; deux anomalies corrigées | 154 |
| 1.0.0 | 2026-10-29 | première version livrée pour revue des requis | 145 |

## 1.1.0 — 2026-11-04 — remarques du relecteur sur les premiers essais

Remarques de Sébastien après ses premiers essais (package simulation10 : 3 producteurs,
2 consommateurs). Elles sont suivies une par une dans
`docs/recapitulatif/Suivi_remarques_VISU_PTBG.xlsx`.

| Domaine | Changement | Pourquoi |
|---|---|---|
| Base de temps | un Δt pile à la limite de la tolérance (11 ms pour 10 ms ± 10 %) est conforme où qu'il soit dans le fichier | **anomalie** : producer2 et producer3 étaient en avertissement et pas producer1, avec les mêmes Δt (arrondi du calcul en flottant) |
| Base de temps | « jitter max » devient « écart max à la grille » | un Δt isolé de 9 ms décale la grille d'1 ms : ce n'est pas du jitter |
| Condition Bool d'un autre fichier | état inconnu (condition fausse) dans un trou de ce fichier et après sa fin | **anomalie** relevée à l'analyse de la matrice Framatome : un état était inventé pendant une perte |
| Global | Ctrl+Z / Ctrl+Y (menu Édition) ; bouton « maison » = toute la durée même après un changement d'onglet ; fermer un paquet ferme les onglets qui ne montraient que lui | remarques « fausses manips », « Home sans effet », « onglets 7 à 10 restés ouverts » |
| Curseurs | activer un curseur désactive la loupe et le place dans la vue affichée (curseur global au centre) | remarques « zoom non volontaire », « curseur à recentrer » |
| Axes | légende = nom de la variable (fichier seulement en cas d'homonymie) ; clic sur une courbe ou son entrée de légende = la sélectionner ; titre, unité et hauteur de chaque axe ; couleur, épaisseur et trait de chaque courbe | remarques sur la légende, la sélection, le titre, les unités, l'aspect et la hauteur |
| Rapport | pages en paysage ou en portrait ; graphique et lectures d'un onglet sur la même page | remarques « paysage ou portrait », « page unique » |
| Nuage X/Y | droite de régression retirée (corrélation r conservée) | remarque « virer la courbe de régression » |
| Time Base Monitor | à l'écran, plus de texte sous le titre : statut par fichier au coin de la courbe, détail d'une anomalie au survol, diagnostic au clic droit ; le rapport garde le texte détaillé | remarque « ne pas afficher les avertissements sous le titre » |

Non modifié : le « suivi souris » (remarque « semble inutile ») est le requis REQ 5402 ;
la question est posée dans le fichier de suivi. Deux nouveaux points ouverts (n° 19 et 20)
portent sur les interprétations faites pour le TBM et la « page unique ».

Les tests de cette version restent à lancer sur le poste Windows 11 / Spyder 6, puis sur la
VM Linux SLES 15 SP7 fournie par l'entreprise.

## 1.0.0 — 2026-10-29 — première version livrée

Version soumise à la revue de la spécification NCS/00/I/COMMON----/ES/010 Rev. A.
Les 64 lignes de requis sont tracées dans `docs/TRACABILITE_REQUIS.md` et dans le
récapitulatif Excel (`docs/recapitulatif/`), dont l'onglet « Points ouverts » rassemble
les 18 questions à faire valider (20 depuis la version 1.1.0).

| Domaine | Contenu |
|---|---|
| Lecture des CSV (§ 2.3) | contrôle du séparateur, de l'encodage UTF-8, de l'en-tête, des métadonnées et de la taille maximale ; fichiers abîmés lus sans exception, sans perte silencieuse ni valeur inventée, chaque anomalie citée avec sa ligne ; lecture en arrière-plan avec avancement et annulation |
| Signaux (§ 2.2) | types Bool / Float automatiques et forçables, états texte, groupes binaires (détectés ou créés) |
| Base de temps (§ 3.1) | compteurs (ns à h, cycles), heure à la nanoseconde avec passage de minuit, date-heure ; pré-déclenchement ; contrôles de période, stabilité, croissance, trous, déphasage, changements de fréquence, horodatages illisibles et aberrants ; réglages par fichier (période nominale, tolérance, origine absolue, décalage, affichage régularisé, diagnostic opérateur) |
| Plusieurs PLC (§ 2.1) | paquets de données, axe des temps relatif ou absolu, comparaison des sources |
| Time Base Monitor | dans chaque onglet ; masquage refusé en cas d'alerte |
| Diagnostic | par fichier : bilan, points à vérifier, tableaux, ligne CSV de chaque événement |
| Interface (§ 4.1 à 4.3) | menus, barre de chemin, arbre masquable, onglets fermables à 7 modèles de disposition, barre d'état, aide intégrée |
| Graphiques (§ 4.4) | axes quadrillés ; courbes réduites pour l'affichage sans perdre les pics ; cellules vides marquées, trous de temps visibles ; légendes, noms des pistes et étiquettes des curseurs déplaçables à la souris ; bouton « Vue d'origine » |
| Curseurs (§ 4.4) | simple, double (Δt, 1/Δt, ΔV), global, suivi souris avec panneau de lecture, horizontal avec franchissements, condition Bool, nuage X/Y avec corrélation ; valeurs lues sur les échantillons réels, jamais interpolées |
| Traitement conditionnel (§ 4.5) | statistiques des signaux pendant qu'une condition Bool est vraie, export CSV (proposition, énoncé 5500 vide) |
| Rapports (§ 5) | PDF automatique ou pas à pas, en-tête complet (REQ 6005), Time Base Monitor, lectures, page de traçabilité |
| Projet | fichier `.ptbg.json` (chemins relatifs, réglages, onglets, curseurs, pages du rapport) |
| Architecture (§ 6) | Python 3.11 de référence (code prévu pour 3.10 à 3.14), stdlib + numpy + matplotlib ; Windows 11 et SLES 15 SP7 depuis les mêmes sources, différences isolées dans `ptbg/system/compat.py` ; classeur des versions et dépendances (`docs/recapitulatif/Dependances_versions_VISU_PTBG.xlsx`) ; versions du poste Spyder 6 relevées |
| Qualité | 145 tests automatisés (dont l'interface réelle et un banc de fichiers abîmés) ; contrôle automatique de la traçabilité ; banc de mesure des performances (`tools/banc_performance.py`) |

Tests automatiques lancés sur le poste Windows 11 / Spyder 6 le 30/10/2026 : 144 sur 145
OK ; le seul en erreur cherchait le Word de la spécification, absent du dossier (corrigé :
ce contrôle est sauté quand le Word n'est pas dans `docs/specification/`).

Reste à faire avant de déclarer l'outil qualifié : réponses aux points ouverts ; essai de
réception sur le poste Windows 11 / Spyder 6 ; tests et essai de réception sur la
VM Linux SLES 15 SP7 fournie par l'entreprise ; essai sur les volumes réels de PTBG (voir la fin de
`docs/TRACABILITE_REQUIS.md`).
