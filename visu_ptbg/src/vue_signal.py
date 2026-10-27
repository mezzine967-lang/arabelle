# -----------------------------------------------------------------------------
# VISU PTBG — V00.06.00 — première vue de signal
# Requis concernés : 5104, 3003, 3006 ; périmètre partiel détaillé dans docs.
# Historique : séparation lecture, dessin et intégration dans la fenêtre.
# -----------------------------------------------------------------------------
"""Widget tkinter pour afficher une figure et zoomer dans ses deux axes.

Le moteur FigureCanvasTkAgg est instancié dans la fenêtre de VISU, sans
plt.show() et sans utiliser la fenêtre de courbes de Spyder. Les données et
les règles temporelles restent dans les modules de traitement.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox

from trace_signal import creer_figure


def fermer_canvas(canvas):
    """Annuler le rendu Tk différé avant de détruire son widget.

    TkAgg garde l'identifiant du after_idle : sans l'annuler, fermer un onglet
    juste après un curseur laisse un callback visant un widget détruit.
    """
    identifiant = getattr(canvas, "_idle_draw_id", None)
    if identifiant is not None:
        canvas.get_tk_widget().after_cancel(identifiant)
        canvas._idle_draw_id = None
    canvas.stop_event_loop()


def basculer_moniteur(axe_signal, axe_temps, autorise: bool) -> bool:
    """Changer la visibilité du moniteur si le diagnostic autorise son retrait.

    La décision provient du diagnostic, jamais d'une couleur ou du zoom. En cas
    d'avertissement, l'axe reste visible et la fonction retourne False.
    """
    if not autorise:
        return False
    visible = not axe_temps.get_visible()
    axe_temps.set_visible(visible)
    # L'axe de temps est partagé : ses étiquettes doivent rester visibles sur
    # le signal lorsque le moniteur est masqué.
    axe_signal.tick_params(labelbottom=not visible)
    axe_signal.set_xlabel("" if visible else axe_temps.get_xlabel())
    return True


class VueSignal(ttk.Frame):
    """Héberger le canevas et une barre de navigation, sans export de rapport."""

    def __init__(self, parent, signal, moniteur, decimale=".", *, groupe=None):
        # === 1. Importer seulement quand la fonction graphique est demandée ===
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
        super().__init__(parent)
        try:
            self.signal = signal
            self.signaux = list(groupe) if groupe else [signal]
            self.groupe = bool(groupe)
            self.moniteur = moniteur
            if groupe:
                from groupe_binaire import creer_figure_groupe
                self.figure, self.axe_signal, self.axe_temps = creer_figure_groupe(groupe, moniteur, decimale)
            else:
                self.figure, self.axe_signal, self.axe_temps = creer_figure(signal, moniteur, decimale)
            self.canvas = FigureCanvasTkAgg(self.figure, master=self)
            self.masquage_autorise = bool(moniteur.get("masquage_autorise"))
            self.bouton_moniteur = ttk.Button(
                self, text="Masquer le Time Base Monitor", command=self._basculer_moniteur,
                state="normal" if self.masquage_autorise else "disabled")
            self.bouton_moniteur.pack(side="top", anchor="w")
            # Les commandes de lecture ne dépendent pas du zoom Matplotlib.
            commandes = ttk.Frame(self)
            commandes.pack(fill="x")
            from curseurs import Curseurs
            self.mode_curseur = tk.StringVar(value="Aucun")
            modes = Curseurs.MODES if signal.type_signal == "Float" else Curseurs.MODES[:-1]
            liste = ttk.Combobox(commandes, textvariable=self.mode_curseur,
                                 values=modes, state="readonly", width=18)
            liste.pack(side="left")
            self.liste_modes = liste
            liste.bind("<<ComboboxSelected>>", self._choisir_curseur)
            self.cible = tk.IntVar(value=0)
            for i in range(2):
                ttk.Radiobutton(commandes, text=f"C{i+1}", variable=self.cible, value=i,
                                command=self._choisir_cible).pack(side="left")
            ttk.Button(commandes, text="Lectures...", command=self._ouvrir_lectures).pack(side="left")
            self.suivi = tk.BooleanVar(value=False)
            ttk.Checkbutton(commandes, text="Suivi souris", variable=self.suivi,
                            command=self._choisir_suivi).pack(side="left")
            if signal.type_signal == "Float":
                ttk.Button(self, text="Retirer la condition Bool",
                           command=lambda: self.curseurs.definir_condition(None)).pack(anchor="w")
            self.texte_lecture = "Choisir un curseur, puis cliquer sur un échantillon."
            self.popup = None
            self.curseurs = Curseurs(self.figure, self.axe_signal, self.axe_temps,
                                     signal, self._lecture)
            for supplement in self.signaux[1:]:
                self.curseurs.ajouter(supplement)

            class BarreNavigation(NavigationToolbar2Tk):
                """Garder le zoom/déplacement ; les rapports seront une étape dédiée."""
                toolitems = tuple(item for item in NavigationToolbar2Tk.toolitems if item[0] != "Save")

            self.barre = BarreNavigation(self.canvas, self, pack_toolbar=False)
            self.barre.update()
            self.barre.pack(side="bottom", fill="x")
            self.canvas.get_tk_widget().pack(side="top", fill="both", expand=True)
            self.canvas.draw()
        except Exception:
            # Une erreur d'initialisation ne laisse pas de widget partiel visible.
            self.destroy()
            raise

    def _choisir_curseur(self, _evenement=None):
        self.curseurs.choisir(self.mode_curseur.get())
        if self.mode_curseur.get() != "Aucun":
            self._ouvrir_lectures()

    def _choisir_cible(self):
        self.curseurs.cible = self.cible.get()

    def _choisir_suivi(self):
        self.curseurs.suivi = self.suivi.get()
        if self.suivi.get():
            if self.mode_curseur.get() not in ("Vertical", "Double vertical"):
                self.mode_curseur.set("Vertical")
                self._choisir_curseur()
            self._ouvrir_lectures()

    def superposer(self, signal):
        from curseurs import meme_horloge, Curseurs
        from _signal_draw import sample_chart
        if self.groupe:
            raise ValueError("Créer un nouveau groupe pour modifier la liste de ses colonnes.")
        if not meme_horloge(self.signal, signal):
            raise ValueError("Pour superposer, choisir le même CSV. Les autres sources restent dans des panneaux indépendants.")
        if (self.signal.raster_temps, self.signal.tolerance_temps) != (signal.raster_temps, signal.tolerance_temps):
            raise ValueError("Les profils temporels diffèrent. Créer un nouveau panneau avec le profil actuel.")
        if any(s.colonne == signal.colonne for s in self.signaux):
            raise ValueError("Ce signal est déjà affiché dans le panneau.")
        if signal.type_signal != self.signal.type_signal:
            raise ValueError("Séparer Bool et Float dans deux panneaux pour préserver leurs échelles.")
        if len(self.signaux) >= 8:
            raise ValueError("Ce panneau atteint la limite de présentation de 8 signaux ; créer un autre panneau.")
        self.curseurs.ajouter(signal)
        self.signaux.append(signal)
        teinte = ("#d65f00", "#7040a0", "#278350", "#a52243", "#9a7000", "#4565b0", "#555555")[len(self.signaux)-2]
        ligne = sample_chart(self.axe_signal, signal.temps, signal.valeurs, "", "Valeurs",
                             " / ".join(s.colonne for s in self.signaux),
                             relier_points=signal.relier_points and signal.type_signal != "Bool",
                             indices_coupures=signal.indices_coupures)
        ligne.set_color(teinte)
        ligne.set_label(signal.colonne)
        if signal.indices_croix:
            self.axe_signal.plot([signal.temps[i] for i in signal.indices_croix],
                                 [signal.valeurs[i] for i in signal.indices_croix],
                                 linestyle="None", marker="x", color="#dc6a00", markersize=8, zorder=4)
        self.axe_signal.legend(fontsize=8, loc="upper left")
        self.axe_signal.relim(visible_only=True)
        if signal.type_signal == "Float":
            self.axe_signal.autoscale(enable=True, axis="y")
        self.canvas.draw_idle()

    def _lecture(self, texte):
        self.texte_lecture = texte
        if self.popup is not None and self.popup.winfo_exists():
            self.lecture.configure(state="normal")
            self.lecture.delete("1.0", "end")
            self.lecture.insert("1.0", texte)
            self.lecture.configure(state="disabled")

    def _ouvrir_lectures(self):
        if self.popup is None or not self.popup.winfo_exists():
            self.popup = tk.Toplevel(self)
            self.popup.title(f"Lectures — {self.signal.colonne}")
            self.popup.geometry("460x240")
            self.lecture = tk.Text(self.popup, wrap="word")
            self.lecture.pack(fill="both", expand=True)
            self.popup.update_idletasks()
            # Placer à droite tout en restant à l'intérieur de l'écran.
            x = min(self.winfo_rootx() + self.winfo_width(), self.winfo_screenwidth() - 470)
            self.popup.geometry(f"+{max(0, x)}+{max(0, self.winfo_rooty())}")
        self._lecture(self.texte_lecture)
        self.popup.lift()

    def destroy(self):
        # Déconnecter les callbacks et fermer les lectures avec leur onglet.
        if hasattr(self, "canvas"):
            fermer_canvas(self.canvas)
        if hasattr(self, "curseurs"):
            self.curseurs.detruire()
        if getattr(self, "popup", None) is not None and self.popup.winfo_exists():
            self.popup.destroy()
        if hasattr(self, "figure"):
            self.figure.clear()
        super().destroy()

    def _basculer_moniteur(self):
        """Masquer ou réafficher le seul axe temporel sans toucher aux données."""
        if basculer_moniteur(self.axe_signal, self.axe_temps, self.masquage_autorise):
            visible = self.axe_temps.get_visible()
            self.bouton_moniteur.configure(text=("Masquer le Time Base Monitor" if visible
                else "Afficher le Time Base Monitor — masqué, aucun avertissement"))
            self.canvas.draw_idle()
