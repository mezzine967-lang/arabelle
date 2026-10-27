"""REQ 2201 : plusieurs colonnes Bool, sans mot binaire ni état recomposé.

Les décalages verticaux servent à séparer les pistes. Les lectures et les
étiquettes conservent les valeurs Bool réelles ; aucune donnée n'est modifiée.
"""
from curseurs import meme_horloge
from trace_signal import creer_figure


def verifier_groupe(signaux):
    if not 2 <= len(signaux) <= 8:
        raise ValueError("Choisir entre 2 et 8 colonnes Bool pour un groupe.")
    if len({s.colonne for s in signaux}) != len(signaux):
        raise ValueError("Chaque colonne doit apparaître une seule fois.")
    if any(s.type_signal != "Bool" or not meme_horloge(signaux[0], s) for s in signaux):
        raise ValueError("Le groupe doit contenir des Bool de la même lecture du CSV.")
    if any((s.raster_temps, s.tolerance_temps) !=
           (signaux[0].raster_temps, signaux[0].tolerance_temps) for s in signaux):
        raise ValueError("Les colonnes du groupe doivent partager le même profil temporel.")


def creer_figure_groupe(signaux, moniteur, decimale="."):
    verifier_groupe(signaux)
    note = "\n".join(f"{s.colonne} : {len(s.indices_vides)} cellule(s) vide(s), "
                     f"{len(s.indices_invalides)} invalide(s)" for s in signaux)
    note += "\nPistes Bool indépendantes ; croix aux bords des cellules vides uniquement."
    figure, axe, temps = creer_figure(signaux[0], moniteur, decimale, note_signal=note)
    axe.clear()
    ticks, libelles = [], []
    for numero, signal in enumerate(signaux):
        origine = 3 * (len(signaux) - 1 - numero)
        couleur = f"C{numero}"
        axe.plot(signal.temps, [v + origine for v in signal.valeurs],
                 linestyle="None", marker=".", markersize=3, color=couleur)
        if signal.indices_croix:
            axe.plot([signal.temps[i] for i in signal.indices_croix],
                     [signal.valeurs[i] + origine for i in signal.indices_croix],
                     linestyle="None", marker="x", color="#dc6a00", markersize=8)
        ticks.extend([origine, origine + 1])
        libelles.extend([f"{signal.colonne} : 0", f"{signal.colonne} : 1"])
        axe.axhspan(origine - .3, origine + 1.3, color=couleur, alpha=.04)
    axe.set_yticks(ticks, libelles, fontsize=8)
    axe.set_ylim(-.5, 3 * (len(signaux) - 1) + 1.5)
    axe.set_title("Groupe Bool — états mesurés, sans maintien entre échantillons", fontsize=10, loc="left")
    axe.tick_params(labelbottom=False)
    axe.grid(axis="x", alpha=.2)
    figure.subplots_adjust(left=.25)
    return figure, axe, temps
