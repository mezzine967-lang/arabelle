"""Nuage X/Y d'un seul CSV, avec point de lecture (requis 5408).

L'appariement utilise la ligne physique commune, jamais la proximité temporelle
entre deux PLC. Aucun coefficient de corrélation ni interpolation n'est ajouté.
"""
import math
from tkinter import ttk
from pathlib import Path

from curseurs import meme_horloge
from trace_signal import creer_figure


def couples_xy(x, y):
    """Retourner les vrais couples et leur provenance, dans l'ordre du CSV."""
    if not meme_horloge(x, y):
        raise ValueError("X et Y doivent provenir de la même lecture du même CSV.")
    if x.type_signal != "Float" or y.type_signal != "Float":
        raise ValueError("Le nuage X/Y utilise deux signaux Float.")
    par_ligne = {ligne: i for i, ligne in enumerate(y.lignes)}
    couples = []
    for i, ligne in enumerate(x.lignes):
        j = par_ligne.get(ligne)
        if j is not None and math.isfinite(x.valeurs[i]) and math.isfinite(y.valeurs[j]):
            couples.append((x.valeurs[i], y.valeurs[j], i, j, ligne))
    if not couples:
        raise ValueError("Aucun couple X/Y présent et valide sur une même ligne.")
    return couples


def figure_xy(x, y, modele):
    """Garder le moniteur natif ; l'axe XY est indépendant de l'axe temporel."""
    couples = couples_xy(x, y)
    note = (f"X/Y : {len(couples)} couples présents et valides sur {len(x.lignes)} lignes retenues.\n"
            f"{x.colonne} : {len(x.indices_vides)} cellule(s) vide(s), {len(x.indices_invalides)} invalide(s). "
            f"{y.colonne} : {len(y.indices_vides)} cellule(s) vide(s), {len(y.indices_invalides)} invalide(s).\n"
            "Moniteur : Δt du CSV sur son axe temporel, indépendant de l'axe X/Y.")
    fig, ancien, temps = creer_figure(x, modele, note_signal=note)
    emplacement = ancien.get_subplotspec()
    fig.delaxes(ancien)
    axe = fig.add_subplot(emplacement)
    points = axe.scatter([p[0] for p in couples], [p[1] for p in couples], s=12, color="#176a94", picker=7)
    axe.set_xlabel(x.colonne)
    axe.set_ylabel(y.colonne)
    axe.set_title(f"{Path(x.fichier).name} — X/Y, couples présents sur la même ligne", fontsize=10, loc="left")
    axe.grid(alpha=.2)
    return fig, axe, temps, points, couples


class VueXY(ttk.Frame):
    def __init__(self, parent, x, y, modele):
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        super().__init__(parent)
        self.signal, self.signaux, self.moniteur = x, [x,y], modele
        self.type_vue = "XY"
        self.figure, self.axe_signal, self.axe_temps, self.points, self.couples = figure_xy(x, y, modele)
        self.canvas = FigureCanvasTkAgg(self.figure, master=self)
        self.texte_lecture = "Cliquer sur un point du nuage : lecture de sa ligne CSV."
        ttk.Label(self, text=self.texte_lecture).pack(anchor="w")
        self.lecture = ttk.Label(self, wraplength=700)
        self.lecture.pack(anchor="w")
        self.anneau, = self.axe_signal.plot([], [], marker="o", markersize=10,
                                          markerfacecolor="none", markeredgecolor="#a1266d", linestyle="None")
        self.annotation = self.axe_signal.text(.02, .98, "", transform=self.axe_signal.transAxes,
                                               va="top", fontsize=8, bbox=dict(facecolor="white", alpha=.8))
        class Barre(NavigationToolbar2Tk):
            toolitems = tuple(item for item in NavigationToolbar2Tk.toolitems if item[0] != "Save")
        self.barre = Barre(self.canvas, self, pack_toolbar=False)
        self.barre.pack(side="bottom", fill="x")
        self.canvas.get_tk_widget().pack(fill="both", expand=True)
        self.connexion = self.canvas.mpl_connect("pick_event", self._choisir)
        self.canvas.draw()

    def _choisir(self, evenement):
        if evenement.artist is not self.points or self.barre.mode or len(evenement.ind) == 0:
            return
        # Plusieurs couples peuvent occuper le même pixel : tous sont nommés
        # (jusqu'à 20 lignes de lecture), sans sélectionner un doublon en secret.
        lignes = []
        for k in evenement.ind[:20]:
            px, py, i, j, ligne = self.couples[k]
            x, y = self.signaux
            lignes.append(f"Ligne {ligne} | t={x.temps_bruts[i]} | {x.colonne}={x.valeurs_brutes[i]} | {y.colonne}={y.valeurs_brutes[j]}")
        if len(evenement.ind) > 20:
            lignes.append(f"{len(evenement.ind)} couples dans la zone de sélection, 20 montrés.")
        self.texte_lecture = "\n".join(lignes)
        self.lecture.configure(text=self.texte_lecture)
        self.annotation.set_text("\n".join(lignes[:3]))
        self.anneau.set_data([self.couples[k][0] for k in evenement.ind], [self.couples[k][1] for k in evenement.ind])
        self.canvas.draw_idle()

    def destroy(self):
        from vue_signal import fermer_canvas
        fermer_canvas(self.canvas)
        self.canvas.mpl_disconnect(self.connexion)
        self.figure.clear()
        super().destroy()
