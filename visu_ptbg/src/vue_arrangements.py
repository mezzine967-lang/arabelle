"""Onglets graphiques persistants, modèles à un ou deux panneaux (5106, 5300).

Chaque panneau garde son propre signal, son horloge et son moniteur. Deux PLC
peuvent être affichés ensemble, sans suggérer qu'ils ont une origine commune.
"""
import tkinter as tk
from tkinter import ttk, messagebox


MODELES = ("Un panneau", "Deux panneaux côte à côte", "Deux panneaux superposés")


class Arrangements(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        commandes = ttk.Frame(self)
        commandes.pack(fill="x")
        self.modele = tk.StringVar(value=MODELES[0])
        ttk.Combobox(commandes, textvariable=self.modele, values=MODELES,
                     state="readonly", width=30).pack(side="left")
        ttk.Button(commandes, text="Nouvel onglet", command=self.nouveau).pack(side="left")
        ttk.Button(commandes, text="Fermer l'onglet", command=self.fermer).pack(side="left")
        ttk.Button(commandes, text="Curseur global (même CSV)", command=self.lier).pack(side="left")
        self.onglets = ttk.Notebook(self)
        self.onglets.pack(fill="both", expand=True)
        self.pages = {}
        self.numero = 0
        self.nouveau()

    def nouveau(self):
        self.numero += 1
        modele = self.modele.get()
        page = ttk.Frame(self.onglets)
        page.vues = []
        page.modele = modele
        page.numero = self.numero
        page.capacite = 1 if modele == MODELES[0] else 2
        # Garder une surface lisible pour chaque moniteur, même sur un écran
        # étroit. Les barres donnent accès aux zones qui dépassent la fenêtre.
        page.rowconfigure(0, weight=1)
        page.columnconfigure(0, weight=1)
        canevas = tk.Canvas(page, highlightthickness=0)
        canevas.grid(row=0, column=0, sticky="nsew")
        vertical = ttk.Scrollbar(page, orient="vertical", command=canevas.yview)
        horizontal = ttk.Scrollbar(page, orient="horizontal", command=canevas.xview)
        vertical.grid(row=0, column=1, sticky="ns")
        horizontal.grid(row=1, column=0, sticky="ew")
        canevas.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
        page.panneaux = ttk.Panedwindow(canevas, orient="vertical" if modele == MODELES[2] else "horizontal")
        item = canevas.create_window(0, 0, window=page.panneaux, anchor="nw")
        def dimensionner(evenement):
            largeur = max(evenement.width, 760 * (2 if modele == MODELES[1] else 1))
            hauteur = max(evenement.height, 520 * (2 if modele == MODELES[2] else 1))
            canevas.itemconfigure(item, width=largeur, height=hauteur)
            canevas.configure(scrollregion=(0, 0, largeur, hauteur))
        canevas.bind("<Configure>", dimensionner)
        self.pages[str(page)] = page
        self.onglets.add(page, text=f"Vue {self.numero}")
        self.onglets.select(page)
        return page

    def active(self):
        return self.pages.get(self.onglets.select())

    def ajouter(self, signal, moniteur, decimale):
        from vue_signal import VueSignal
        page = self.active()
        if page is None or len(page.vues) >= page.capacite:
            page = self.nouveau()
        vue = VueSignal(page.panneaux, signal, moniteur, decimale)
        page.panneaux.add(vue, weight=1)
        page.vues.append(vue)
        self.onglets.tab(page, text=f"Vue {page.numero} ({len(page.vues)}/{page.capacite})")
        return vue

    def fermer(self):
        page = self.active()
        if page is None:
            return
        self.onglets.forget(page)
        self.pages.pop(str(page))
        for vue in page.vues:
            vue.destroy()
        page.destroy()
        if not self.pages:
            self.nouveau()

    def vues_actives(self):
        page = self.active()
        if page is None or not page.vues:
            raise ValueError("Afficher au moins un signal dans l'onglet actif.")
        return page.vues

    def superposer(self, signal):
        vues = self.vues_actives()
        if not hasattr(vues[-1], "superposer"):
            raise ValueError("Créer un panneau temporel pour superposer des courbes.")
        vues[-1].superposer(signal)
        return vues[-1]

    def ajouter_xy(self, x, y, modele):
        from vue_xy import VueXY
        page = self.nouveau()
        vue = VueXY(page.panneaux, x, y, modele)
        page.panneaux.add(vue, weight=1)
        page.vues.append(vue)
        page.capacite = 1
        self.onglets.tab(page, text=f"Vue {page.numero} — X/Y")
        return vue

    def ajouter_groupe(self, signaux, modele, decimale):
        from groupe_binaire import verifier_groupe
        from vue_signal import VueSignal
        verifier_groupe(signaux)
        page = self.nouveau()
        vue = VueSignal(page.panneaux, signaux[0], modele, decimale, groupe=signaux)
        page.panneaux.add(vue, weight=1)
        page.vues.append(vue)
        page.capacite = 1
        self.onglets.tab(page, text=f"Vue {page.numero} — Groupe Bool")
        return vue

    def lier(self):
        from curseurs import meme_horloge
        try:
            vues = self.vues_actives()
            if any(not hasattr(v, "curseurs") for v in vues):
                raise ValueError("Le curseur temporel global ne s'applique pas à un axe X/Y.")
            if not all(meme_horloge(vues[0].signal, v.signal) for v in vues):
                raise ValueError("Le curseur commun exige ici le même CSV. Le repère entre PLC reste à définir avec Sébastien.")
            for vue in vues:
                vue.mode_curseur.set("Vertical")
                vue.curseurs.choisir("Vertical")
            def partager(x, cible):
                for vue in vues:
                    vue.curseurs.placer(x, cible, notifier=False)
                    vue.canvas.draw_idle()
            for vue in vues:
                vue.curseurs.sur_position = partager
        except ValueError as exc:
            messagebox.showinfo("Curseur global", str(exc), parent=self)
