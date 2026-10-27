"""Vue tkinter de l'inspection temporelle, avec tableau paginé et tracé optionnel.

v0.7.0 — Les règles de calcul restent dans inspection_temps. Matplotlib n'est
chargé qu'au clic sur Graphique des écarts ; le tableau fonctionne sans lui.
"""
from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import messagebox, ttk

from inspection_temps import LIBELLES, resumer_inspection

TAILLE_PAGE = 200


class VueTemps(ttk.Frame):
    """Permettre de consulter chaque intervalle sans créer des milliers de widgets."""

    def __init__(self, parent, inspection):
        super().__init__(parent, padding=6)
        self.inspection = inspection
        self.page = 0
        self.fenetre_graphique = None
        self.axe = self.canvas = self.barre = None
        self.selection_graphique = None
        self.anomalies_seules = tk.BooleanVar(value=True)
        self.pagination = tk.StringVar()
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        # === 1. Les paramètres appliqués et les limites restent lisibles ===
        self.resume = ttk.Label(self, text=f"{Path(inspection.fichier).name} — {inspection.colonne}\n"
                                + resumer_inspection(inspection), justify="left", wraplength=720)
        self.resume.grid(row=0, column=0, sticky="ew", pady=(0, 5))
        self.bind("<Configure>", lambda e: self.resume.configure(wraplength=max(e.width - 20, 200)))
        ttk.Label(self, text="Δt = temps après − temps avant. Tous les nombres sont dans l'unité native du CSV.",
                  wraplength=700).grid(row=1, column=0, sticky="w", pady=(0, 5))
        commandes = ttk.Frame(self)
        commandes.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        ttk.Checkbutton(commandes, text="Points à examiner uniquement", variable=self.anomalies_seules,
                        command=self._filtrer).pack(side="left")
        ttk.Button(commandes, text="Graphique des écarts...", command=self._ouvrir_graphique).pack(side="right")
        tableau = ttk.Frame(self)
        tableau.grid(row=3, column=0, sticky="nsew")
        tableau.columnconfigure(0, weight=1)
        tableau.rowconfigure(0, weight=1)
        colonnes = ("lignes", "avant", "apres", "delta", "ecart", "constat")
        self.table = ttk.Treeview(tableau, columns=colonnes, show="headings", height=5, selectmode="browse")
        entetes = ("Lignes CSV", "Temps avant", "Temps après", "Δt", "Δt − pas", "Constat")
        for cle, titre, largeur in zip(colonnes, entetes, (105, 115, 115, 85, 85, 215)):
            self.table.heading(cle, text=titre)
            self.table.column(cle, width=largeur, minwidth=70, anchor="w", stretch=True)
        self.table.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(tableau, orient="vertical", command=self.table.yview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal = ttk.Scrollbar(tableau, orient="horizontal", command=self.table.xview)
        horizontal.grid(row=1, column=0, sticky="ew")
        self.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        self.table.bind("<<TreeviewSelect>>", self._selectionner)
        self.table.tag_configure("alerte", foreground="#9c4300")
        navigation = ttk.Frame(self)
        navigation.grid(row=4, column=0, sticky="ew", pady=4)
        self.precedent = ttk.Button(navigation, text="◀ Précédent", command=lambda: self._tourner(-1))
        self.precedent.pack(side="left")
        ttk.Label(navigation, textvariable=self.pagination).pack(side="left", padx=10)
        self.suivant = ttk.Button(navigation, text="Suivant ▶", command=lambda: self._tourner(1))
        self.suivant.pack(side="right")
        self.detail = tk.Text(self, height=4, wrap="word", state="disabled", relief="flat")
        self.detail.grid(row=5, column=0, sticky="ew")
        self._filtrer()

    # === 2. Pagination de tous les résultats, sans troncature cachée ===
    def _filtrer(self):
        self.indices = self.inspection.indices(self.anomalies_seules.get())
        self.page = 0
        self._page()

    def _tourner(self, direction):
        derniere = max(0, (len(self.indices) - 1) // TAILLE_PAGE)
        self.page = min(derniere, max(0, self.page + direction))
        self._page()

    def _page(self):
        self.table.delete(*self.table.get_children())
        debut = self.page * TAILLE_PAGE
        for indice in self.indices[debut:debut + TAILLE_PAGE]:
            v = self.inspection.intervalles[indice]
            self.table.insert("", "end", iid=str(indice), values=(
                f"{v.ligne_avant} → {v.ligne_apres}", v.temps_avant, v.temps_apres,
                str(v.delta) if v.delta is not None else "Non calculé",
                str(v.ecart) if v.ecart is not None else "Non comparé", LIBELLES[v.nature]),
                tags=("alerte",) if v.nature not in ("observe", "dans_tolerance") else ())
        total = len(self.indices)
        self.pagination.set(f"{debut + 1 if total else 0}–{min(debut + TAILLE_PAGE, total)} / {total} intervalles")
        self.precedent.configure(state="normal" if self.page else "disabled")
        self.suivant.configure(state="normal" if debut + TAILLE_PAGE < total else "disabled")
        texte = "Sélectionne un intervalle pour lire son détail exact et centrer son graphique."
        if not total:
            texte = ("Aucun point à examiner dans les couples disponibles. Décoche le filtre pour voir tous les intervalles. "
                     "Le bilan ci-dessus indique si une comparaison au pas attendu a été possible.")
        self._texte(texte)

    def _texte(self, texte):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("1.0", texte)
        self.detail.configure(state="disabled")

    def _intervalle_selectionne(self):
        selection = self.table.selection()
        return self.inspection.intervalles[int(selection[0])] if selection else None

    def _selectionner(self, _event=None):
        v = self._intervalle_selectionne()
        if v is None:
            return
        calcul = (f"Δt = {v.temps_apres} − ({v.temps_avant}) = {v.delta}"
                  if v.delta is not None else "Δt non calculé : continuité ou temps non exploitables.")
        self._texte(f"Lignes physiques {v.ligne_avant}–{v.fin_avant} puis {v.ligne_apres}–{v.fin_apres}. "
                    f"{LIBELLES[v.nature]}.\n{calcul}\n"
                    "Un pas hors tolérance est un constat ; sa cause et une éventuelle perte de données restent à établir.")
        if self.fenetre_graphique is not None:
            self._centrer(v)

    # === 3. Fenêtre de détail graphique fermée avec le diagnostic qui l'a créée ===
    def _centrer(self, v):
        if self.selection_graphique is not None:
            self.selection_graphique.remove()
        self.selection_graphique = self.axe.axvline(v.ligne_apres, color="#252525", linestyle=":", linewidth=1)
        marge = max(20, v.ligne_apres - v.ligne_avant)
        self.axe.set_xlim(max(1, v.ligne_avant - marge), v.ligne_apres + marge)
        self.canvas.draw_idle()

    def _ouvrir_graphique(self):
        if self.fenetre_graphique is not None:
            self.fenetre_graphique.lift()
            return
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            from trace_temps import creer_figure_temps
            figure, self.axe = creer_figure_temps(self.inspection)
            fenetre = tk.Toplevel(self)
            self.fenetre_graphique = fenetre
            fenetre.title("VISU — Time Base Monitor — " + Path(self.inspection.fichier).name)
            fenetre.geometry("920x560")
            fenetre.protocol("WM_DELETE_WINDOW", self._fermer_graphique)
            self.canvas = FigureCanvasTkAgg(figure, master=fenetre)

            class Barre(NavigationToolbar2Tk):
                toolitems = tuple(v for v in NavigationToolbar2Tk.toolitems if v[0] != "Save")

            self.barre = Barre(self.canvas, fenetre, pack_toolbar=False)
            self.barre.pack(side="bottom", fill="x")
            self.canvas.get_tk_widget().pack(fill="both", expand=True)
            self.canvas.draw()
            self.barre.update()
            self.barre.push_current()  # Home ramène à toutes les lignes, même après sélection.
            choisi = self._intervalle_selectionne()
            if choisi is not None:
                self._centrer(choisi)
        except (ImportError, OSError, ValueError, RuntimeError, tk.TclError) as exc:
            self._fermer_graphique()
            messagebox.showerror("Graphique non affiché", f"{exc}\n\nLe tableau exact reste consultable.", parent=self)

    def _fermer_graphique(self):
        if self.fenetre_graphique is not None:
            self.fenetre_graphique.destroy()
        self.fenetre_graphique = self.axe = self.canvas = self.barre = None
        self.selection_graphique = None

    def destroy(self):
        self._fermer_graphique()
        super().destroy()
