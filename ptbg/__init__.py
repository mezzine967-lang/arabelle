"""Paquet applicatif VISU PTBG — analyseur graphique de perturbographie.

Organisation (voir docs/ARCHITECTURE.md) :

- ``ptbg.system``   : compatibilité Windows / SLES, environnement, journal d'activité ;
- ``ptbg.core``     : traitements purs (lecture CSV, base de temps, curseurs...),
                      sans Tkinter, donc testables sans écran ;
- ``ptbg.plotting`` : dessin Matplotlib commun à l'écran et au rapport PDF ;
- ``ptbg.report``   : génération des rapports PDF ;
- ``ptbg.gui``      : interface Tkinter (widgets, dialogues, contrôleur).

Le script ``MAIN.py`` à la racine ne fait qu'assembler l'interface
(REQ_COMMON_KH_3002) ; toutes les actions sont déléguées aux modules
ci-dessus (REQ_COMMON_KH_3003).
"""
