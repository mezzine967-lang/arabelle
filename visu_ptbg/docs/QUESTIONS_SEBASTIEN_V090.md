# Questions à Sébastien — points qui demandent une décision

Les fonctions non qualifiées sous Windows/SLES ne sont pas déclarées validées.
Les questions ci-dessous sont préparées pour la revue, pas envoyées.

1. **Temps absolu / 4107, 2102, 2104 :** quelle origine/date/fuseau et quelle
   unité pour chaque PLC ? Existe-t-il un événement commun de référence ? Que
   signifie précisément « Clock Jitter ignored » : affichage, exclusion de
   diagnostic ou reconstruction d'une horloge ? Quel comportement aux retours
   de compteur et au passage à minuit ? Aucun recalage n'est effectué actuellement.
2. **Groupes binaires / deuxième 2201 :** plusieurs colonnes Bool regroupées,
   mot numérique contenant des bits, ou autre encodage ? Nombre/ordre des bits,
   noms, base de codage et valeurs invalides ? Fournir un exemple représentatif.
3. **Typage / 5202 :** les CSV ont-ils une convention qui distingue un Float
   limité à 0/1 d'un Bool ? Auto garde les nombres comme Float ; l'utilisateur
   peut choisir Bool. Des états textuels autres que true/false sont-ils attendus ?
4. **Traitement conditionnel / 5407 et 5500 vide :** quelle opération doit être
   conditionnée par le Bool : affichage d'un seuil, sélection de périodes,
   calcul de dépassements, autre ? Que faire quand le Bool est absent ?
5. **Taille / 2310 « xxxMo » :** maximum par CSV, nombre de sources/signaux,
   durée d'import et mémoire admissibles ? Les bornes actuelles sont provisoires.
6. **2305 et 5404 :** 2305 est-il seulement le titre des formats 2306/2307 ?
   5404 reprend exactement 5403 : même critère ou exigence différente ? Le
   double curseur existe ; l'identifiant dupliqué est conservé dans la matrice.
7. **Qualification / 3000-3004 :** versions autorisées de Python, Tcl/Tk,
   Matplotlib et dépendances sur SLES 15 SP7 ? Poste/VM disponible pour les
   essais natifs et les futurs builds ? Python 3.11 est la cible de développement.

Essais à organiser, sans nouvelle définition métier : réception visuelle Windows,
mise à l'échelle/DPI, parcours d'annulation, curseurs/superposition, export PDF,
essai équivalent SLES, puis performance sur les volumes réels.

Reste technique connu : rendu graphique/PDF encore synchrone, tableaux et points
conservés en mémoire, pas de packaging, types numériques indicatifs dans l'arbre.
Ce sont des travaux restant à qualifier/améliorer, pas tous des blocages métier.
