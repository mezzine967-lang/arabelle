# Première colonne temporelle — v0.7.4

Cette étape applique directement le requis `REQ_COMMON_KH_2304` : la première
colonne du CSV est consacrée à la base de temps. Son nom peut être `index`,
`t_ms`, `timestamp_reel_ms` ou tout autre texte ; sa position suffit.

## Comportement

- `read_csv` utilise toujours la première colonne pour le diagnostic temporel.
- Un autre nom évoquant un temps dans les colonnes suivantes ne change pas ce
  choix et reste disponible comme signal.
- L'interface affiche le nom de la première colonne dans un champ non modifiable.
- L'utilisateur configure encore l'unité native, le pas attendu et la tolérance.
- Un ancien appel logiciel qui demande une autre colonne reçoit l'erreur
  `premiere_colonne_temps` ; le CSV n'est pas qualifié globalement de non conforme.
- Les temps invalides continuent d'être signalés ligne par ligne et le
  diagnostic partiel existant est conservé.

La règle des croix de la v0.7.3 est inchangée : elles apparaissent sur les
mesures réelles qui encadrent des cellules vides du signal choisi. Un saut de
temps, un doublon, un retour arrière ou une valeur textuelle invalide ne crée
pas de croix.

## Fichiers modifiés

| Fichier | Rôle de la modification |
|---|---|
| `src/diagnostic_csv.py` | Imposer `columns[0]` comme temps, sans détection par nom. |
| `src/base_temps.py` | Documenter le contrat de la première colonne. |
| `src/paquet_csv.py` | Mémoriser cette colonne dans le profil du fichier. |
| `src/inspection_temps.py` | Adapter le message défensif au contrat imposé. |
| `MAIN.py` | Remplacer la saisie de colonne par un affichage non modifiable. |
| `tests/test_import_lot1.py` | Tester un nom inconnu et plusieurs noms évoquant un temps. |
| `tests/test_robustesse_csv.py` | Tester le refus d'une autre colonne demandée par un ancien appelant. |
| `tests/test_inspection_temps.py` | Vérifier que l'inspection utilise la première colonne. |
| `tests/test_paquet_csv.py` | Adapter l'appel de configuration de l'interface. |

Cette étape ne modifie pas les CSV, n'ajoute aucune synchronisation entre PLC
et ne change pas les règles d'unité, de pas, de tolérance ou de données
manquantes. Les fichiers de Sébastien restent des exemples et des tests, pas
une définition implicite du format.
