"""Dessin Matplotlib, commun à l'écran (onglets) et au rapport PDF.

Un seul code de dessin garantit que le PDF montre exactement ce que l'analyste
a vu (REQ_COMMON_KH_6001, 6004). Aucun module n'utilise ``pyplot`` : les
figures sont créées explicitement, ce qui évite tout conflit avec le
« backend » graphique configuré dans la console de Spyder.
"""
