# Historique des modifications — VISU PTBG

Affiché par Information > Historique des modifications (REQ_COMMON_KH_5101).
Chaque nouvelle version incrémente `ptbg/version.py` et ajoute une entrée en tête de ce
fichier : ce qui change, pourquoi (requis, remarque de relecture, anomalie constatée),
et le nombre de tests.

| Version | Date | En une ligne | Tests |
|---|---|---|---|
| 1.0.0 | 2026-10-29 | première version livrée pour revue des requis | 140 |

## 1.0.0 — 2026-10-29 — première version livrée

Version soumise à la revue de la spécification NCS/00/I/COMMON----/ES/010 Rev. A.
Les 64 lignes de requis sont tracées dans `docs/TRACABILITE_REQUIS.md` et dans le
récapitulatif Excel (`docs/recapitulatif/`), dont l'onglet « Points ouverts » rassemble
les 18 questions à faire valider.

| Domaine | Contenu |
|---|---|
| Lecture des CSV (§ 2.3) | contrôle du séparateur, de l'encodage UTF-8, de l'en-tête, des métadonnées et de la taille maximale ; fichiers abîmés lus sans exception, sans perte silencieuse ni valeur inventée, chaque anomalie citée avec sa ligne ; lecture en arrière-plan avec avancement et annulation |
| Signaux (§ 2.2) | types Bool / Float automatiques et forçables, états texte, groupes binaires (détectés ou créés) |
| Base de temps (§ 3.1) | compteurs (ns à h, cycles), heure à la nanoseconde avec passage de minuit, date-heure ; pré-déclenchement ; contrôles de période, stabilité, croissance, trous, déphasage, changements de fréquence, horodatages illisibles et aberrants ; réglages par fichier (période nominale, tolérance, origine absolue, décalage, affichage régularisé, diagnostic opérateur) |
| Plusieurs PLC (§ 2.1) | paquets de données, axe des temps relatif ou absolu, comparaison des sources |
| Time Base Monitor | dans chaque onglet ; masquage refusé en cas d'alerte |
| Diagnostic | par fichier : bilan, points à vérifier, tableaux, ligne CSV de chaque événement |
| Interface (§ 4.1 à 4.3) | menus, barre de chemin, arbre masquable, onglets fermables à 7 modèles de disposition, barre d'état, aide intégrée |
| Graphiques (§ 4.4) | axes quadrillés ; courbes réduites pour l'affichage sans perdre les pics ; cellules vides marquées, trous de temps visibles ; légendes déplaçables ; bouton « Vue d'origine » |
| Curseurs (§ 4.4) | simple, double (Δt, 1/Δt, ΔV), global, suivi souris avec panneau de lecture, horizontal avec franchissements, condition Bool, nuage X/Y avec corrélation ; valeurs lues sur les échantillons réels, jamais interpolées |
| Traitement conditionnel (§ 4.5) | statistiques des signaux pendant qu'une condition Bool est vraie, export CSV (proposition, énoncé 5500 vide) |
| Rapports (§ 5) | PDF automatique ou pas à pas, en-tête complet (REQ 6005), Time Base Monitor, lectures, page de traçabilité |
| Projet | fichier `.ptbg.json` (chemins relatifs, réglages, onglets, curseurs, pages du rapport) |
| Architecture (§ 6) | Python 3.11 de référence (3.10 à 3.14 vérifiés), stdlib + numpy + matplotlib ; Windows 11 et SLES 15 SP7 depuis les mêmes sources, différences isolées dans `ptbg/system/compat.py` |
| Qualité | 140 tests automatisés (dont l'interface réelle et un banc de fichiers abîmés) ; contrôle automatique de la traçabilité ; performances : 1 million de lignes × 21 colonnes lues et analysées en 5 à 7 s sur le banc Linux |

Reste à faire avant de déclarer l'outil qualifié : réponses aux points ouverts, essai de
réception sur Windows 11 / Spyder 6 et sur le Service Unit SLES 15 SP7, essai sur les
volumes réels de PTBG (voir la fin de `docs/TRACABILITE_REQUIS.md`).
