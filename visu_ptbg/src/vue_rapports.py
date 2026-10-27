"""Dialogue de rapport : vue active ou captures ajoutées dans l'ordre choisi."""
import getpass
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from rapport_pdf import PageRapport, capturer, exporter_pdf_en_fond


class Rapports:
    def __init__(self, fenetre, arrangements, informer, lancer):
        self.fenetre, self.arrangements = fenetre, arrangements
        self.informer, self.lancer = informer, lancer
        self.pages = []

    def capture_active(self):
        vues = self.arrangements.vues_actives()
        return PageRapport(tuple(capturer(vue) for vue in vues), self.arrangements.active().modele)

    def ajouter(self):
        try:
            self.pages.append(self.capture_active())
            self.informer(f"Rapport manuel : {len(self.pages)} page(s) figée(s), dans l'ordre d'ajout.")
        except (ValueError, OSError, RuntimeError) as exc:
            messagebox.showerror("Capture", str(exc), parent=self.fenetre)

    def vider(self):
        self.pages.clear()
        self.informer("Composition du rapport vidée ; fichiers PDF existants conservés.")

    def exporter(self, manuel=False):
        try:
            pages = tuple(self.pages) if manuel else (self.capture_active(),)
            if not pages:
                raise ValueError("Ajouter d'abord une vue au rapport manuel.")
        except (ValueError, OSError, RuntimeError) as exc:
            messagebox.showerror("Rapport", str(exc), parent=self.fenetre)
            return
        dialogue = tk.Toplevel(self.fenetre)
        dialogue.title(f"Rapport PDF — {len(pages)} page(s)")
        champs = {}
        for i, (cle, label, valeur) in enumerate((
            ("emetteur", "Émetteur", getpass.getuser()), ("projet", "Nom du projet", ""),
            ("unite", "Unité d'installation", ""), ("reference", "Référence projet (facultative)", ""),
        )):
            ttk.Label(dialogue, text=label).grid(row=i, column=0, sticky="w", padx=8, pady=6)
            variable = tk.StringVar(value=valeur)
            ttk.Entry(dialogue, textvariable=variable, width=45).grid(row=i, column=1, padx=8)
            champs[cle] = variable

        def enregistrer():
            valeurs = {cle: variable.get().strip() for cle, variable in champs.items()}
            if not all(valeurs[cle] for cle in ("emetteur", "projet", "unite")):
                messagebox.showerror("En-tête", "Émetteur, projet et unité sont nécessaires.", parent=dialogue)
                return
            chemin = filedialog.asksaveasfilename(parent=dialogue, defaultextension=".pdf",
                                                  filetypes=[("Rapport PDF", "*.pdf")])
            if not chemin:
                return
            def calcul(annulation, publier):
                return exporter_pdf_en_fond(chemin, pages, annulation, publier, **valeurs)
            def termine(destination):
                self.informer(f"Rapport enregistré : {destination} ({len(pages)} page(s)).")
            if self.lancer(calcul, termine):
                dialogue.destroy()

        ttk.Button(dialogue, text="Enregistrer...", command=enregistrer).grid(row=4, column=1, sticky="e", padx=8, pady=8)
