# Preuve d'essai v0.2 transmise par Mourad

Date de transmission : 23 octobre 2026. Provenance : sorties de console copiées par Mourad dans la conversation, pas une exécution distante sur son poste.

Environnement affiché : Python 3.11.10, Windows, interpréteur 64 bits. La ligne « cible Windows 11 » est une déclaration du programme, pas une vérification de l'édition du système.

Le diagnostic a lu les deux CSV LIM de 501 lignes, les deux CSV PID de 1001 lignes et la simulation de 10001 lignes. Les colonnes communes des couples scénario/report ne présentent aucun écart textuel ligne à ligne. Les deux doublons temporels et les valeurs absentes de la simulation ont été signalés. Un journal de diagnostic a été enregistré sur le poste de Mourad.

Sortie de la suite de tests transmise :

```text
Ran 8 tests in 0.306s

OK
```

Cas exécutés : temps régulier, lignes incorrectes/retour arrière, comparaison scénario/report, BOM UTF-8, ligne supplémentaire valide, couple PID réel, anomalies préservées de la simulation archivée, texte et valeur manquante non remplacée par zéro.

Portée : premier démarrage et huit tests de la version 0.2 sur ce poste. Cette preuve ne s'étend pas automatiquement à v0.3, aux autres configurations clientes, à la synchronisation, à l'IHM ou à la création d'un exécutable. Aucun requis complet n'est déclaré vérifié sur cette seule base.

## Retour utilisateur ultérieur sur la version commentée 0.3.1

Mourad a ensuite transmis les dernières lignes de sa console Spyder :

```text
Ran 43 tests in 1.625s

OK

Bilan : 43 tests | réussite : True | sources inchangées : True
```

Ce retour confirme la réussite de la suite de 43 tests et le contrôle des sources sur son poste. L'extrait ne reproduit pas la ligne de version, le chemin du journal, la version exacte de Python ni l'édition Windows de cette exécution. La nouvelle version 0.3.2 et ses six tests supplémentaires attendent leur propre essai sur le poste de Mourad.
