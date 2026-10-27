# État des requis — VISU PTBG v0.9.0

Les 64 lignes du document source sont reprises ; le double identifiant 2201 est conservé. **Implémenté** signifie présent dans le logiciel, pas réceptionné par Sébastien. Les essais natifs Windows/SLES et la revue humaine restent ouverts. Les énoncés originaux sont repris de la matrice source ; ses anciennes couleurs/statuts ne sont pas utilisés.

Validation locale : tests rapides et intégration consignés dans resultats/ ; rapport de démonstration contrôlé visuellement. Aucune fenêtre Tk native n’a été essayée ici (absence de serveur d’affichage).

| Requis | État actuel | Réalisation / limite |
|---|---|---|
| 2100 | Implémenté, essai natif requis | Pas propre à chaque source ; tests base_temps. Volumes cibles non qualifiés. |
| 2101 | Implémenté, essai natif requis | Plusieurs CSV et plusieurs panneaux indépendants, sans recalage. |
| 2102 | Partiel | Horloges indépendantes préservées. Comparaison temporelle entre PLC encore ouverte. |
| 2103 | Implémenté, essai natif requis | Timestamps, profils et hash propres à chaque source ; vues figées explicitement. |
| 2104 | Partiel | Anomalies locales diagnostiquées. Déphasage inter-PLC non établi. |
| 2105 | Implémenté, essai natif requis | Ajout de CSV ou dossier récursif, désormais en arrière-plan. |
| 2200 | Implémenté, essai natif requis | Bool true/false ou choix explicite Bool pour 0/1 ; points mesurés, aucun état inventé. |
| 2201 (Float) | Implémenté, essai natif requis | Float affiché et superposable ; groupes binaires : encodage et sémantique à préciser. |
| 2201 (groupe binaire) | À clarifier / non réalisé | Float affiché et superposable ; groupes binaires : encodage et sémantique à préciser. |
| 2300 | Implémenté, essai natif requis | Lecteur CSV testé. |
| 2301 | Implémenté, essai natif requis | Virgule prise en charge. |
| 2302 | Implémenté, essai natif requis | UTF-8 avec ou sans BOM. |
| 2303 | Implémenté, essai natif requis | Aucune métadonnée ajoutée aux CSV ; originaux en lecture seule. |
| 2304 | Implémenté, essai natif requis | La première colonne est toujours le temps. |
| 2305 | À clarifier / non réalisé | Titre « Time stamp configuration » : portée autonome à confirmer. |
| 2306 | Implémenté, essai natif requis | HH:MM:SS et fractions jusqu’à 9 chiffres ; aucune date ou journée suivante inventée. |
| 2307 | Implémenté, essai natif requis | Compteur numérique exact, unité explicite ; pas de règle inventée de rebouclage. |
| 2308 | Implémenté, essai natif requis | En-tête lu, anomalies de structure diagnostiquées. |
| 2309 | Partiel | Noms affichés ; espaces externes normalisés par le lecteur existant. |
| 2310 | À clarifier / non réalisé | xxxMo non renseigné. Borne de prototype 50 MiB et 500 000 points graphiques. |
| 3000 | Partiel | Architecture commune, essais Windows 11 x64 / SLES 15 SP7 x86-64 encore nécessaires. |
| 3001 | Partiel | Cible Python 3.11 ; syntaxe contrôlée, exécution ici sous Python 3.12. Pas de support Python 3.6 annoncé. |
| 3002 | Implémenté, essai natif requis | MAIN assemble l’interface ; algorithmes, captures, curseurs et dessins dans src. |
| 3003 | Implémenté, essai natif requis | Fonctions métier et vues réparties en modules dédiés, documentés. |
| 3004 | Partiel | Registre et versions observées v090 joints ; ensemble des versions cibles à qualifier. |
| 3005 | Implémenté, essai natif requis | Chemins portables, sorties utilisateur, absence de commande système spécifique ; mécanismes documentés. |
| 3006 | Implémenté, essai natif requis | Commentaires dans les modules ajoutés, guide de reprise et README actualisés. |
| 3007 | Partiel | Nettoyage local effectué ; audit exhaustif des fonctions historiques non réalisé. |
| 4100 | Partiel | Raster, stabilité, incréments, jitter et anomalies testés ; seuils métier et volumes encore à qualifier. |
| 4101 | Partiel | Croix aux champs vides, anomalies temporelles ; déphasage inter-PLC non couvert. |
| 4102 | Implémenté, essai natif requis | Moniteur quantitatif automatique pour chaque panneau et pour X/Y, sur l’axe temps du CSV. |
| 4103 | Implémenté, essai natif requis | Masquage autorisé seulement selon le diagnostic sans avertissement/erreur. |
| 4104 | Implémenté, essai natif requis | Moniteur systématiquement inclus dans chaque capture PDF, même masqué à l’écran. |
| 4105 | Partiel | Lectures/diagnostics en arrière-plan, annulation sans application du résultat. Rendu/PDF encore synchrone. |
| 4106 | Implémenté, essai natif requis | Raster et tolérance saisis par fichier, diagnostic associé. |
| 4107 | À clarifier / non réalisé | Origine absolue, fuseau et sens de « Clock Jitter ignored » à définir avec Sébastien. |
| 5100 | Implémenté, essai natif requis | Menu principal en haut. |
| 5101 | Implémenté, essai natif requis | Version, aide README, historique/requis et registre des packages ouverts depuis Informations. |
| 5102 | Implémenté, essai natif requis | Utilisateur/date/version/activité en bas, journal horodaté accessible ; journal de session en mémoire. |
| 5103 | Implémenté, essai natif requis | Arbre à gauche. |
| 5104 | Partiel | Graphiques à droite et zones défilantes ; DPI et petite résolution à essayer sur cible. |
| 5105 | Implémenté, essai natif requis | Arbre masquable. |
| 5106 | Implémenté, essai natif requis | Plusieurs onglets graphiques persistants avec zoom et contenu propres. |
| 5200 | Implémenté, essai natif requis | Racine du paquet. |
| 5201 | Implémenté, essai natif requis | Sources enfants du paquet. |
| 5202 | Partiel | Bool/Float indicatifs dans l’arbre ; 0/1 ambigu sans convention métier, choix explicite au tracé. |
| 5203 | Implémenté, essai natif requis | Première colonne temporelle et profil propres au fichier affichés. |
| 5300 | Implémenté, essai natif requis | Trois modèles : un panneau, deux côte à côte, deux superposés. |
| 5400 | Implémenté, essai natif requis | Curseur vertical activable par panneau. |
| 5401 | Implémenté, essai natif requis | Lecture de l’échantillon enregistré le plus proche ; timestamp brut, valeur brute, ligne, absence et doublons explicites. |
| 5402 | Partiel | Fenêtre à droite avec toutes les courbes superposées. Lecture au clic, pas encore de suivi continu à la souris. |
| 5403 | Implémenté, essai natif requis | Double curseur C1/C2 avec timestamp affiché automatiquement. |
| 5404 | Partiel | Texte identique à 5403 : comportement implémenté, distinction documentaire à confirmer. |
| 5405 | Partiel | Curseur global des panneaux du même CSV ; global entre PLC distincts non réalisé. |
| 5406 | Implémenté, essai natif requis | Curseur horizontal réservé à Float, refusé sur Bool. |
| 5407 | À clarifier / non réalisé | Opération conditionnelle et règle si Bool absent à définir. |
| 5408 | Implémenté, essai natif requis | Nuage et point de lecture X/Y du même CSV ; couples présents sur la même ligne uniquement. |
| 5500 | À clarifier / non réalisé | Énoncé vide. |
| 6000 | Implémenté, essai natif requis | Export PDF utilisant Matplotlib PdfPages. |
| 6001 | Implémenté, essai natif requis | En-tête et zone graphique par page. |
| 6002 | Implémenté, essai natif requis | Export direct de l’onglet actif et composition manuelle de captures. |
| 6003 | Implémenté, essai natif requis | Export automatique de l’onglet graphique actif, avec moniteurs. |
| 6004 | Implémenté, essai natif requis | Captures successives de vues, zooms, curseurs et X/Y dans l’ordre d’ajout. |
| 6005 | Implémenté, essai natif requis | Version, émetteur, date, sources, projet, unité, référence optionnelle et SHA-256 des sources. Aucun fichier projet n’existe encore. |

## Énoncés du document source

### REQ_COMMON_KH_2100 — occurrence 1

The PLC can run at different frequencies. Preferred are 10 & 20ms, but the present tool can’t be disturbed by this aspect

État : **Implémenté, essai natif requis**. Pas propre à chaque source ; tests base_temps. Volumes cibles non qualifiés.

### REQ_COMMON_KH_2101 — occurrence 1

The PLC can consist of a system composed by several PLC

État : **Implémenté, essai natif requis**. Plusieurs CSV et plusieurs panneaux indépendants, sans recalage.

### REQ_COMMON_KH_2102 — occurrence 1

The PLC can be synchronized or not

État : **Partiel**. Horloges indépendantes préservées. Comparaison temporelle entre PLC encore ouverte.

### REQ_COMMON_KH_2103 — occurrence 1

Each PLC will produce its own package of data with its own timestamp.

État : **Implémenté, essai natif requis**. Timestamps, profils et hash propres à chaque source ; vues figées explicitement.

### REQ_COMMON_KH_2104 — occurrence 1

The collection of data from several sources can generate variation of frequencies, dephasing, or loss of data flow

État : **Partiel**. Anomalies locales diagnostiquées. Déphasage inter-PLC non établi.

### REQ_COMMON_KH_2105 — occurrence 1

Single or multiple files

État : **Implémenté, essai natif requis**. Ajout de CSV ou dossier récursif, désormais en arrière-plan.

### REQ_COMMON_KH_2200 — occurrence 1

Binary signal

État : **Implémenté, essai natif requis**. Bool true/false ou choix explicite Bool pour 0/1 ; points mesurés, aucun état inventé.

### REQ_COMMON_KH_2201 — occurrence 1

Analog signal type : float

État : **Implémenté, essai natif requis**. Float affiché et superposable ; groupes binaires : encodage et sémantique à préciser.

### REQ_COMMON_KH_2201 — occurrence 2

Binary group signal

État : **À clarifier / non réalisé**. Float affiché et superposable ; groupes binaires : encodage et sémantique à préciser.

### REQ_COMMON_KH_2300 — occurrence 1

The preferred format shall be ‘csv’

État : **Implémenté, essai natif requis**. Lecteur CSV testé.

### REQ_COMMON_KH_2301 — occurrence 1

Separator shall be a comma ‘,’

État : **Implémenté, essai natif requis**. Virgule prise en charge.

### REQ_COMMON_KH_2302 — occurrence 1

Text format UTF8

État : **Implémenté, essai natif requis**. UTF-8 avec ou sans BOM.

### REQ_COMMON_KH_2303 — occurrence 1

No additional meta data

État : **Implémenté, essai natif requis**. Aucune métadonnée ajoutée aux CSV ; originaux en lecture seule.

### REQ_COMMON_KH_2304 — occurrence 1

First column devoted to time base

État : **Implémenté, essai natif requis**. La première colonne est toujours le temps.

### REQ_COMMON_KH_2305 — occurrence 1

Time stamp configuration:

État : **À clarifier / non réalisé**. Titre « Time stamp configuration » : portée autonome à confirmer.

### REQ_COMMON_KH_2306 — occurrence 1

Hh:mn:s… micro, nanos…

État : **Implémenté, essai natif requis**. HH:MM:SS et fractions jusqu’à 9 chiffres ; aucune date ou journée suivante inventée.

### REQ_COMMON_KH_2307 — occurrence 1

Time counter

État : **Implémenté, essai natif requis**. Compteur numérique exact, unité explicite ; pas de règle inventée de rebouclage.

### REQ_COMMON_KH_2308 — occurrence 1

First row devoted to column’s header

État : **Implémenté, essai natif requis**. En-tête lu, anomalies de structure diagnostiquées.

### REQ_COMMON_KH_2309 — occurrence 1

Composed by PLC’s variables names

État : **Partiel**. Noms affichés ; espaces externes normalisés par le lecteur existant.

### REQ_COMMON_KH_2310 — occurrence 1

Maximal size xxxMo

État : **À clarifier / non réalisé**. xxxMo non renseigné. Borne de prototype 50 MiB et 500 000 points graphiques.

### REQ_COMMON_KH_3000 — occurrence 1

Final tool shall be compatible with SLES - SUSE 15 SP7: ‘SUSE Linux Enterprise Server 15SP7’ at least

État : **Partiel**. Architecture commune, essais Windows 11 x64 / SLES 15 SP7 x86-64 encore nécessaires.

### REQ_COMMON_KH_3001 — occurrence 1

Final tool shall be compatible with Python 3.6 at least

État : **Partiel**. Cible Python 3.11 ; syntaxe contrôlée, exécution ici sous Python 3.12. Pas de support Python 3.6 annoncé.

### REQ_COMMON_KH_3002 — occurrence 1

MAIN.py script shall be devoted only to generate the GUI interface.

État : **Implémenté, essai natif requis**. MAIN assemble l’interface ; algorithmes, captures, curseurs et dessins dans src.

### REQ_COMMON_KH_3003 — occurrence 1

All action realized by the tool shall be best as possible externalized into a dedicated sub script or class.

État : **Implémenté, essai natif requis**. Fonctions métier et vues réparties en modules dédiés, documentés.

### REQ_COMMON_KH_3004 — occurrence 1

All additional packages or library implemented shall be documented and strictly aligned with the kernel version.

État : **Partiel**. Registre et versions observées v090 joints ; ensemble des versions cibles à qualifier.

### REQ_COMMON_KH_3005 — occurrence 1

Compatibility mechanism between different OS Shall be documented.

État : **Implémenté, essai natif requis**. Chemins portables, sorties utilisateur, absence de commande système spécifique ; mécanismes documentés.

### REQ_COMMON_KH_3006 — occurrence 1

Code source shall be commented

État : **Implémenté, essai natif requis**. Commentaires dans les modules ajoutés, guide de reprise et README actualisés.

### REQ_COMMON_KH_3007 — occurrence 1

No useless function hold into the scripts

État : **Partiel**. Nettoyage local effectué ; audit exhaustif des fonctions historiques non réalisé.

### REQ_COMMON_KH_4100 — occurrence 1

The present tool shall define the time raster from the source and control check:
•	Period value
•	Period stability
•	Period continuous increase

État : **Partiel**. Raster, stabilité, incréments, jitter et anomalies testés ; seuils métier et volumes encore à qualifier.

### REQ_COMMON_KH_4101 — occurrence 1

The present tool shall be capable to find and highlight the inconsistent time base like missing data or wrong phasing

État : **Partiel**. Croix aux champs vides, anomalies temporelles ; déphasage inter-PLC non couvert.

### REQ_COMMON_KH_4102 — occurrence 1

A dedicated graphical axle shall be devoted to detail the time base conversion and status. It shall be automatically present on each graphical template and call: Time Base Monitor.

État : **Implémenté, essai natif requis**. Moniteur quantitatif automatique pour chaque panneau et pour X/Y, sur l’axe temps du CSV.

### REQ_COMMON_KH_4103 — occurrence 1

The time base monitor can be hidden by the issuer only if no warning or error.

État : **Implémenté, essai natif requis**. Masquage autorisé seulement selon le diagnostic sans avertissement/erreur.

### REQ_COMMON_KH_4104 — occurrence 1

The Time Base Monitor shall be automatically present into all reports. If removed for arrangement and indication shall appear to confirm the good construction or Time Base.

État : **Implémenté, essai natif requis**. Moniteur systématiquement inclus dans chaque capture PDF, même masqué à l’écran.

### REQ_COMMON_KH_4105 — occurrence 1

In case of disturbance in the time base analysis, the treatment can’t be locked or unstable.

État : **Partiel**. Lectures/diagnostics en arrière-plan, annulation sans application du résultat. Rendu/PDF encore synchrone.

### REQ_COMMON_KH_4106 — occurrence 1

In case of disturbance in the time base analysis, the user can specify the normal raster with an associated diagnosis

État : **Implémenté, essai natif requis**. Raster et tolérance saisis par fichier, diagnostic associé.

### REQ_COMMON_KH_4107 — occurrence 1

Constitute Absolute timestamp. Clock Jitter ignored

État : **À clarifier / non réalisé**. Origine absolue, fuseau et sens de « Clock Jitter ignored » à définir avec Sébastien.

### REQ_COMMON_KH_5100 — occurrence 1

Top bar with main menu path

État : **Implémenté, essai natif requis**. Menu principal en haut.

### REQ_COMMON_KH_5101 — occurrence 1

Specific ‘Information’ section including:
Tool version
History of changes
Sources
Help file

État : **Implémenté, essai natif requis**. Version, aide README, historique/requis et registre des packages ouverts depuis Informations.

### REQ_COMMON_KH_5102 — occurrence 1

Bottom bar summarizing:
User
Date
Activity log
Tool version

État : **Implémenté, essai natif requis**. Utilisateur/date/version/activité en bas, journal horodaté accessible ; journal de session en mémoire.

### REQ_COMMON_KH_5103 — occurrence 1

Left area will contain the data tree viewer

État : **Implémenté, essai natif requis**. Arbre à gauche.

### REQ_COMMON_KH_5104 — occurrence 1

Right area will be the main and wider section devoted to graphical analysis.

État : **Partiel**. Graphiques à droite et zones défilantes ; DPI et petite résolution à essayer sur cible.

### REQ_COMMON_KH_5105 — occurrence 1

Tree area can be hidden

État : **Implémenté, essai natif requis**. Arbre masquable.

### REQ_COMMON_KH_5106 — occurrence 1

Graphical area can manage several tab to hold different arrangements

État : **Implémenté, essai natif requis**. Plusieurs onglets graphiques persistants avec zoom et contenu propres.

### REQ_COMMON_KH_5200 — occurrence 1

Top Tree level correspond to the data package

État : **Implémenté, essai natif requis**. Racine du paquet.

### REQ_COMMON_KH_5201 — occurrence 1

First Child level will be devoted to the csv file… from one source or several.

État : **Implémenté, essai natif requis**. Sources enfants du paquet.

### REQ_COMMON_KH_5202 — occurrence 1

Into each csv file, the tree shall detail all the variables contained with associated type Bool or Float.

État : **Partiel**. Bool/Float indicatifs dans l’arbre ; 0/1 ambigu sans convention métier, choix explicite au tracé.

### REQ_COMMON_KH_5203 — occurrence 1

Into each csv file, the tree shall detail the dedicated time base

État : **Implémenté, essai natif requis**. Première colonne temporelle et profil propres au fichier affichés.

### REQ_COMMON_KH_5300 — occurrence 1

Several templates shall be proposed including different arrangement of Axle

État : **Implémenté, essai natif requis**. Trois modèles : un panneau, deux côte à côte, deux superposés.

### REQ_COMMON_KH_5400 — occurrence 1

Vertical single Cursor: can be activated by axle

État : **Implémenté, essai natif requis**. Curseur vertical activable par panneau.

### REQ_COMMON_KH_5401 — occurrence 1

Vertical single Cursor: hold time stamp value and cross value of selected curve

État : **Implémenté, essai natif requis**. Lecture de l’échantillon enregistré le plus proche ; timestamp brut, valeur brute, ligne, absence et doublons explicites.

### REQ_COMMON_KH_5402 — occurrence 1

Vertical single Cursor: tracking reading mode adding the list of crossed value from all the axle’s curves into a right popup

État : **Partiel**. Fenêtre à droite avec toutes les courbes superposées. Lecture au clic, pas encore de suivi continu à la souris.

### REQ_COMMON_KH_5403 — occurrence 1

Double Vertical Cursor: Time stamp is mandatory and automated for each cursor

État : **Implémenté, essai natif requis**. Double curseur C1/C2 avec timestamp affiché automatiquement.

### REQ_COMMON_KH_5404 — occurrence 1

Double Vertical Cursor: Time stamp is mandatory and automated for each cursor

État : **Partiel**. Texte identique à 5403 : comportement implémenté, distinction documentaire à confirmer.

### REQ_COMMON_KH_5405 — occurrence 1

Global cursor = global synchronization of axles. Cursor appear over all axles and moving in same time

État : **Partiel**. Curseur global des panneaux du même CSV ; global entre PLC distincts non réalisé.

### REQ_COMMON_KH_5406 — occurrence 1

Horizontal cursor: only applicable to analog signals

État : **Implémenté, essai natif requis**. Curseur horizontal réservé à Float, refusé sur Bool.

### REQ_COMMON_KH_5407 — occurrence 1

Horizontal cursor: can be conditioned by additional bool signal to realize conditional processing.

État : **À clarifier / non réalisé**. Opération conditionnelle et règle si Bool absent à définir.

### REQ_COMMON_KH_5408 — occurrence 1

Cursor X/Y: used for correlation control check - Two cursors are activated or the cross point only can be highlighted

État : **Implémenté, essai natif requis**. Nuage et point de lecture X/Y du même CSV ; couples présents sur la même ligne uniquement.

### REQ_COMMON_KH_5500 — occurrence 1



État : **À clarifier / non réalisé**. Énoncé vide.

### REQ_COMMON_KH_6000 — occurrence 1

The present tool shall be capable to generate a pdf report.

État : **Implémenté, essai natif requis**. Export PDF utilisant Matplotlib PdfPages.

### REQ_COMMON_KH_6001 — occurrence 1

Report consist into a template containing Header and graphical area

État : **Implémenté, essai natif requis**. En-tête et zone graphique par page.

### REQ_COMMON_KH_6002 — occurrence 1

Report, can be generated automatically or step by step.

État : **Implémenté, essai natif requis**. Export direct de l’onglet actif et composition manuelle de captures.

### REQ_COMMON_KH_6003 — occurrence 1

Automatic Report consist into a single edition of active graphical area to pdf file

État : **Implémenté, essai natif requis**. Export automatique de l’onglet graphique actif, avec moniteurs.

### REQ_COMMON_KH_6004 — occurrence 1

Manual step by step report generation consist into a sequential generation on order depending of graphical active tab. Permitting to push global view, and customize analysis, cursor, X/Y cloud…

État : **Implémenté, essai natif requis**. Captures successives de vues, zooms, curseurs et X/Y dans l’ordre d’ajout.

### REQ_COMMON_KH_6005 — occurrence 1

Header shall contain following details:
Tool Version
Issuer
Date
Source File(s)
Project Name & Unit
Project file reference or Hash

État : **Implémenté, essai natif requis**. Version, émetteur, date, sources, projet, unité, référence optionnelle et SHA-256 des sources. Aucun fichier projet n’existe encore.
