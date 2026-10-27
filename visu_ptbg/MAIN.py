"""VISU PTBG : sélection CSV, diagnostic et Time Base Monitor.

Lancer ce fichier avec Spyder (F5) sous Python 3.11. MAIN construit seulement
l'interface. La lecture et les décisions temporelles sont dans src/.
Cette fenêtre inclut une vue de signal et son Time Base Monitor.
Dépendances : tkinter ; Matplotlib est chargé au premier tracé. Voir le registre.
"""
from __future__ import annotations

# === 1. Dépendances de présentation et appel au traitement séparé ===
import getpass
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

PROJET = Path(__file__).resolve().parent
if str(PROJET / "src") not in sys.path:
    sys.path.insert(0, str(PROJET / "src"))
from paquet_csv import PaquetCSV, decrire_source
from moniteur_temps import construire_moniteur
from signal_csv import preparer_signal
from environnement_visu import enregistrer_environnement
from version_visu import VERSION_VISU
from taches import TacheFond, importer_copie
from dataclasses import replace

VERSION = VERSION_VISU


class FenetreVISU:
    """Afficher les fichiers, leurs colonnes et un diagnostic par horloge."""

    def __init__(self, fenetre: tk.Tk) -> None:
        self.fenetre = fenetre
        self.paquet = PaquetCSV()
        self.tache = None
        self.journal_activite = []
        self.type_signal = tk.StringVar(value="Auto")
        self.indice_actif: int | None = None
        self.signal_choisi = tk.StringVar()
        self.fichier_affiche = tk.StringVar(value="Aucun fichier sélectionné")
        self.vue_signal = None
        self.vue_temps = None
        self.noeuds_signaux: dict[str, str] = {}
        self.types_signaux = {}  # Choix explicites par fichier, hash et colonne.
        self.temps_choisi = tk.StringVar()
        self.unite = tk.StringVar()
        self.pas = tk.StringVar()
        self.tolerance = tk.StringVar()
        self.profil_etat = tk.StringVar(
            value=("L'unité décrit les nombres du CSV ; la tolérance est l'écart maximal "
                   "accepté autour du pas, pas le jitter mesuré."),
        )
        self.activite = tk.StringVar(value="Choisir un ou plusieurs fichiers CSV.")
        self.moniteur_statut = tk.StringVar(value="Time Base Monitor — aucun fichier sélectionné")
        self.moniteur_modele: dict | None = None
        self.moniteur_visible = True
        self.fenetre.title(f"VISU PTBG — import CSV {VERSION}")
        largeur = min(1280, max(800, self.fenetre.winfo_screenwidth() - 80))
        hauteur = min(960, max(600, self.fenetre.winfo_screenheight() - 80))
        self.fenetre.geometry(f"{largeur}x{hauteur}")
        self._construire_menu()
        self._construire_contenu()
        from vue_rapports import Rapports
        self.rapports = Rapports(self.fenetre, self.arrangements, self._noter, self._lancer)
        self.activite.trace_add("write", self._journaliser)
        self.fenetre.protocol("WM_DELETE_WINDOW", self._fermer)
        for variable in (self.unite, self.pas, self.tolerance):
            variable.trace_add("write", self._indiquer_profil)

    # === 2. Fenêtre : arbre des fichiers et panneau de diagnostic séparé ===
    def _construire_menu(self) -> None:
        barre = tk.Menu(self.fenetre)
        fichiers = tk.Menu(barre, tearoff=False)
        fichiers.add_command(label="Ajouter des CSV...", command=self._ajouter)
        fichiers.add_command(label="Ajouter un dossier CSV...", command=self._ajouter_dossier)
        fichiers.add_command(label="Enregistrer le diagnostic...", command=self._enregistrer)
        fichiers.add_separator()
        fichiers.add_command(label="Quitter", command=self._fermer)
        barre.add_cascade(label="Fichier", menu=fichiers)
        informations = tk.Menu(barre, tearoff=False)
        informations.add_command(label="Version et sources", command=lambda: messagebox.showinfo(
            "Informations", f"VISU PTBG {VERSION}\nSources : CSV sélectionnés par l'utilisateur.\n"
            "Lecture : bibliothèque standard Python, module local diagnostic_csv.\n"
            "Historique : v0.7.6 moniteur Δt ; v0.7.7 catégories temporelles détaillées.\n"
            "Les versions installées sont relevées dans le dossier utilisateur VISU_PTBG/resultats. "
            "Le chemin exact est affiché dans la console au lancement."))
        informations.add_command(label="Aide", command=lambda: messagebox.showinfo(
            "Aide", "Ajoute plusieurs CSV, puis choisis un fichier dans l'arbre. "
            "Sa première colonne est la base de temps. Indique si nécessaire son unité, son pas attendu et sa tolérance. "
            "Appuie sur Analyser ce fichier. Le Time Base Monitor reste visible en cas d'avertissement. "
            "Pour tracer : onglet Courbe, choisir le signal, puis Afficher le signal. "
            "Pour examiner les temps : onglet Base de temps, Examiner les intervalles. "
            "Le graphique des écarts suit les numéros de ligne ; son axe X n'est pas un temps. "
            "Les points restent aux temps du fichier ; aucune synchronisation entre fichiers."))
        barre.add_cascade(label="Informations", menu=informations)
        informations.add_separator()
        informations.add_command(label="Fichier d'aide (README)", command=lambda: self._document(PROJET / "README.md"))
        informations.add_command(label="Historique et requis", command=lambda: self._document(PROJET / "docs/VALIDATION_V100.md"))
        informations.add_command(label="Bibliothèques et packages", command=lambda: self._document(PROJET / "docs/DEPENDANCES.md"))
        informations.add_command(label="Journal d'activité", command=self._voir_activite)
        rapports = tk.Menu(barre, tearoff=False)
        rapports.add_command(label="Exporter l'onglet actif en PDF...", command=lambda: self.rapports.exporter())
        rapports.add_command(label="Ajouter l'onglet actif au rapport manuel", command=lambda: self.rapports.ajouter())
        rapports.add_command(label="Exporter le rapport manuel...", command=lambda: self.rapports.exporter(manuel=True))
        rapports.add_command(label="Vider la composition manuelle", command=lambda: self.rapports.vider())
        barre.add_cascade(label="Rapport", menu=rapports)
        self.fenetre.config(menu=barre)

    def _construire_contenu(self) -> None:
        self.zone = ttk.Frame(self.fenetre, padding=10)
        self.zone.pack(fill="both", expand=True)
        self.zone.columnconfigure(1, weight=1)
        self.zone.rowconfigure(1, weight=1)
        ttk.Button(self.zone, text="Ajouter des CSV...", command=self._ajouter).grid(row=0, column=0, sticky="w")
        ttk.Button(self.zone, text="Ajouter un dossier CSV...", command=self._ajouter_dossier).grid(
            row=0, column=1, sticky="w", padx=8)
        ttk.Button(self.zone, text="Masquer/afficher l'arbre", command=self._basculer_arbre).grid(
            row=0, column=1, sticky="e", padx=8)
        self.volet_arbre = ttk.Frame(self.zone)
        self.volet_arbre.grid(row=1, column=0, sticky="nsew", pady=8)
        ttk.Label(self.volet_arbre, text="Sources de données").pack(anchor="w")
        self.arbre = ttk.Treeview(self.volet_arbre, show="tree", selectmode="browse", height=12)
        self.arbre.column("#0", width=210, minwidth=110)
        self.arbre.pack(fill="both", expand=True)
        self.arbre.insert("", "end", iid="paquet", text="Paquet CSV", open=True)
        self.arbre.bind("<<TreeviewSelect>>", self._selectionner)

        droit = ttk.Frame(self.zone)
        droit.grid(row=1, column=1, sticky="nsew", padx=(12, 0), pady=8)
        droit.columnconfigure(0, weight=1)
        droit.rowconfigure(3, weight=1)
        ttk.Label(droit, textvariable=self.fichier_affiche).grid(row=0, column=0, sticky="w")
        profil = ttk.Frame(droit)
        profil.grid(row=1, column=0, sticky="ew", pady=8)
        ttk.Label(profil, text="Temps (1re colonne)").grid(row=0, column=0, sticky="w", padx=4)
        ttk.Label(profil, textvariable=self.temps_choisi, width=16, relief="sunken", anchor="w").grid(
            row=1, column=0, padx=4, sticky="ew")
        profil.columnconfigure(0, weight=1)
        for position, (etiquette, variable) in enumerate((
            ("Unité native", self.unite), ("Pas attendu", self.pas),
            ("Tolérance du pas", self.tolerance),
        ), start=1):
            ttk.Label(profil, text=etiquette).grid(row=0, column=position, sticky="w", padx=4)
            ttk.Entry(profil, textvariable=variable, width=16).grid(row=1, column=position, padx=4, sticky="ew")
            profil.columnconfigure(position, weight=1)
        ttk.Button(profil, text="Analyser ce fichier", command=self._configurer).grid(
            row=1, column=4, padx=5)
        ttk.Label(droit, textvariable=self.profil_etat, wraplength=720).grid(
            row=2, column=0, sticky="w", pady=(0, 6))
        self.onglets = ttk.Notebook(droit)
        self.onglets.grid(row=3, column=0, sticky="nsew")
        diagnostic = ttk.Frame(self.onglets)
        diagnostic.columnconfigure(0, weight=1)
        diagnostic.rowconfigure(0, weight=1)
        self.onglets.add(diagnostic, text="Diagnostic")
        self.details = tk.Text(diagnostic, wrap="word", state="disabled", width=65)
        self.details.grid(row=0, column=0, sticky="nsew")
        defilement = ttk.Scrollbar(diagnostic, command=self.details.yview)
        defilement.grid(row=0, column=1, sticky="ns")
        self.details.configure(yscrollcommand=defilement.set)

        # Inspection exacte indépendante de Matplotlib ; dessin demandé séparément.
        self.onglet_temps = ttk.Frame(self.onglets)
        self.onglets.add(self.onglet_temps, text="Base de temps")
        ttk.Button(self.onglet_temps, text="Examiner les intervalles",
                   command=self._examiner_intervalles).pack(anchor="w", padx=6, pady=5)
        self.conteneur_temps = ttk.Frame(self.onglet_temps)
        self.conteneur_temps.pack(fill="both", expand=True)
        self.indication_temps = ttk.Label(self.conteneur_temps,
            text="Choisir un fichier, appliquer son profil, puis Examiner les intervalles.", wraplength=650)
        self.indication_temps.pack(pady=20)

        # La vue de signal est créée à la demande : un import Matplotlib absent
        # ne bloque pas le lecteur ni le diagnostic des autres fichiers.
        self.onglet_courbe = ttk.Frame(self.onglets)
        self.onglets.add(self.onglet_courbe, text="Courbe")
        choix_signal = ttk.Frame(self.onglet_courbe, padding=5)
        choix_signal.pack(fill="x")
        # Deux lignes évitent que les actions importantes disparaissent à
        # droite sur les petits écrans et avec la mise à l'échelle Windows.
        outils_signal = ttk.Frame(self.onglet_courbe, padding=(5, 0, 5, 4))
        outils_signal.pack(fill="x")
        ttk.Label(choix_signal, text="Signal :").pack(side="left")
        self.liste_signaux = ttk.Combobox(choix_signal, textvariable=self.signal_choisi,
                                         state="readonly", width=28)
        self.liste_signaux.pack(side="left", padx=6)
        self.liste_signaux.bind("<<ComboboxSelected>>", self._restaurer_type)
        ttk.Button(choix_signal, text="Afficher le signal", command=self._afficher_courbe).pack(side="left")
        ttk.Button(outils_signal, text="Superposer un signal", command=lambda: self._afficher_courbe(True)).pack(side="left")
        ttk.Label(choix_signal, text=" Type :").pack(side="left")
        choix_type = ttk.Combobox(choix_signal, textvariable=self.type_signal, values=("Auto", "Float", "Bool"),
                                  width=7, state="readonly")
        choix_type.pack(side="left")
        choix_type.bind("<<ComboboxSelected>>", self._memoriser_type)
        ttk.Button(outils_signal, text="Nuage X/Y...", command=self._afficher_xy).pack(side="left", padx=5)
        ttk.Button(outils_signal, text="Groupe Bool...", command=self._groupe_bool).pack(side="left")
        ttk.Button(outils_signal, text="Condition Bool...", command=self._condition_bool).pack(side="left", padx=5)
        self.conteneur_courbe = ttk.Frame(self.onglet_courbe)
        self.conteneur_courbe.pack(fill="both", expand=True)
        from vue_arrangements import Arrangements
        self.arrangements = Arrangements(self.conteneur_courbe)
        self.arrangements.pack(fill="both", expand=True)
        # La courbe est l'activité principale ; les onglets de diagnostic et de
        # base de temps restent accessibles à côté lorsqu'ils sont nécessaires.
        self.onglets.select(self.onglet_courbe)

        # === 2a. Axe toujours créé ; masquage permis uniquement si son état est OK ===
        moniteur = ttk.Frame(diagnostic, padding=(0, 8, 0, 0))
        moniteur.grid(row=1, column=0, columnspan=2, sticky="ew")
        moniteur.columnconfigure(0, weight=1)
        ttk.Label(moniteur, textvariable=self.moniteur_statut).grid(row=0, column=0, sticky="w")
        self.bouton_moniteur = ttk.Button(moniteur, text="Masquer le moniteur",
                                          command=self._basculer_moniteur, state="disabled")
        self.bouton_moniteur.grid(row=0, column=1, sticky="e")
        self.moniteur_canvas = tk.Canvas(moniteur, height=130, background="#f7f7f7",
                                         highlightthickness=1, highlightbackground="#c8c8c8")
        self.moniteur_canvas.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(5, 0))
        self.moniteur_canvas.bind("<Configure>", lambda _event: self._tracer_moniteur())
        self._afficher("Ajoute des CSV pour afficher un diagnostic temporel par fichier.\n"
                       "Les horloges ne sont ni triées ni synchronisées.")
        ttk.Label(self.fenetre, textvariable=self.activite, anchor="w").pack(fill="x", padx=10)
        travail = ttk.Frame(self.fenetre)
        travail.pack(fill="x", padx=10)
        self.progression = ttk.Progressbar(travail, mode="indeterminate")
        self.progression.pack(side="left", fill="x", expand=True)
        self.bouton_annuler = ttk.Button(travail, text="Annuler le calcul", command=self._annuler, state="disabled")
        self.bouton_annuler.pack(side="left")
        ttk.Button(travail, text="Journal d'activité", command=self._voir_activite).pack(side="left")
        ttk.Label(self.fenetre, text=f"Utilisateur : {getpass.getuser()}  |  "
                  f"Date : {datetime.now():%d/%m/%Y}  |  VISU {VERSION}").pack(anchor="w", padx=10, pady=(0, 8))

    # === 3. Actions : ouvrir, choisir, préciser un profil et revoir ce fichier ===
    def _ajouter(self) -> None:
        chemins = filedialog.askopenfilenames(parent=self.fenetre, title="Choisir les CSV du paquet",
                                             filetypes=[("Fichiers CSV", "*.csv"), ("Tous les fichiers", "*.*")])
        if not chemins:
            return
        self._lancer(lambda annulation, publier: importer_copie(self.paquet, list(chemins), annulation, publier),
                     self._import_termine)

    def _ajouter_dossier(self) -> None:
        dossier = filedialog.askdirectory(parent=self.fenetre, title="Choisir un dossier de CSV")
        if not dossier:
            return
        def calcul(annulation, publier):
            from decouverte_csv import decouvrir_csv
            publier(("progression", "Découverte des CSV dans les sous-dossiers..."))
            return importer_copie(self.paquet, decouvrir_csv(dossier), annulation, publier)
        self._lancer(calcul, self._import_termine)

    def _import_termine(self, paquet):
        nombre = len(paquet.sources) - len(self.paquet.sources)
        self.paquet = paquet
        self._actualiser_arbre()
        self.activite.set(f"{nombre} fichier(s) ajouté(s) ; {len(self.paquet.sources)} au total.")
        if nombre:
            self.arbre.selection_set(f"f{len(self.paquet.sources) - 1}")
            self._selectionner()

    def _actualiser_arbre(self) -> None:
        self.noeuds_signaux.clear()
        for enfant in self.arbre.get_children("paquet"):
            self.arbre.delete(enfant)
        for indice, (source, resultat) in enumerate(zip(self.paquet.sources, self.paquet.resultats)):
            identifiant = f"f{indice}"
            self.arbre.insert("paquet", "end", iid=identifiant, text=Path(source.fichier).name, open=False)
            if "erreur" in resultat:
                self.arbre.insert(identifiant, "end", text="Lecture ou profil à corriger")
                continue
            diagnostic = resultat["diagnostic_csv"]
            temps = diagnostic["time"]
            self.arbre.insert(identifiant, "end", text=f"Temps (1re colonne) : {temps['column'] if temps else 'indisponible'}")
            for colonne in diagnostic["columns"]:
                if temps and colonne == temps["column"]:
                    continue
                typage = diagnostic["inferred_types"].get(colonne, "inconnu")
                typage = {"booléen": "Bool", "numérique": "Float"}.get(typage, typage)
                choix = self.types_signaux.get((str(source.fichier), diagnostic["sha256"], colonne), "Auto")
                libelle = f"{typage} indicatif" if choix == "Auto" else f"{choix} choisi"
                original = diagnostic.get("original_columns", diagnostic["columns"])[diagnostic["columns"].index(colonne)]
                noeud = self.arbre.insert(identifiant, "end", text=f"{original} ({libelle})")
                self.noeuds_signaux[noeud] = colonne

    def _selectionner(self, _evenement: object = None) -> None:
        selection = self.arbre.selection()
        if not selection or selection[0] == "paquet":
            return
        noeud = selection[0]
        while self.arbre.parent(noeud) != "paquet":
            noeud = self.arbre.parent(noeud)
        indice = int(noeud[1:])
        if indice != self.indice_actif:
            self._effacer_inspection()
        self.indice_actif = indice
        source, resultat = self.paquet.sources[indice], self.paquet.resultats[indice]
        self.fichier_affiche.set(f"Fichier sélectionné : {Path(source.fichier).name} — réglages de sa base de temps")
        diagnostic = resultat.get("diagnostic_csv", {})
        temps = diagnostic.get("time")
        self.temps_choisi.set(temps["column"] if temps else "")
        self.unite.set(source.unite or "")
        self.pas.set(source.pas_attendu or "")
        self.tolerance.set(source.tolerance or "")
        self._afficher(decrire_source(source, resultat))
        self._actualiser_moniteur(source, resultat)
        colonnes = [colonne for colonne in diagnostic.get("columns", [])
                    if not temps or colonne != temps["column"]]
        self.liste_signaux.configure(values=colonnes)
        demande = self.noeuds_signaux.get(selection[0])
        if demande in colonnes:
            self.signal_choisi.set(demande)
        elif self.signal_choisi.get() not in colonnes:
            self.signal_choisi.set(colonnes[0] if colonnes else "")
        self._restaurer_type()

    def _cle_type(self):
        if self.indice_actif is None:
            return None
        source = self.paquet.sources[self.indice_actif]
        diagnostic = self.paquet.resultats[self.indice_actif].get("diagnostic_csv", {})
        return str(source.fichier), diagnostic.get("sha256"), self.signal_choisi.get()

    def _restaurer_type(self, _evenement=None):
        self.type_signal.set(self.types_signaux.get(self._cle_type(), "Auto"))

    def _memoriser_type(self, _evenement=None):
        cle = self._cle_type()
        if cle is not None:
            selection = self.arbre.selection()
            self.types_signaux[cle] = self.type_signal.get()
            self._actualiser_arbre()
            if selection:
                self.arbre.selection_set(f"f{self.indice_actif}")
            self._noter("Type mémorisé pour cette colonne et cette lecture du CSV.")

    def _configurer(self) -> None:
        if self.indice_actif is None:
            messagebox.showinfo("Fichier", "Choisis d'abord un fichier dans l'arbre.")
            return
        indice = self.indice_actif
        source = replace(self.paquet.sources[indice], unite=self.unite.get().strip() or None,
                         pas_attendu=self.pas.get().strip() or None,
                         tolerance=self.tolerance.get().strip() or None)
        def calcul(_annulation, _publier):
            from base_temps import examiner_paquet
            return examiner_paquet([source])["sources"][0]
        def appliquer(bilan):
            self.paquet.sources[indice], self.paquet.resultats[indice] = source, bilan
            self._effacer_inspection()
            self._actualiser_arbre()
            self.arbre.selection_set(f"f{indice}")
            self._selectionner()
            self._noter("Diagnostic mis à jour. Les vues déjà ouvertes gardent leur profil de capture.")
        self._lancer(calcul, appliquer)

    def _profil_applique(self) -> bool:
        if self.indice_actif is None:
            return False
        source = self.paquet.sources[self.indice_actif]
        saisi = tuple(v.get().strip() for v in (self.unite, self.pas, self.tolerance))
        applique = tuple(v or "" for v in (source.unite, source.pas_attendu, source.tolerance))
        return saisi == applique

    def _indiquer_profil(self, *_args):
        message = ("L'unité décrit les nombres du CSV ; la tolérance est l'écart maximal "
                   "accepté autour du pas, pas le jitter mesuré.")
        if self.indice_actif is not None and not self._profil_applique():
            message = "Réglages modifiés : cliquer sur Analyser ce fichier pour les appliquer."
        self.profil_etat.set(message)

    # === 3a. Examiner le temps avant de poursuivre les outils d'analyse ===
    def _effacer_inspection(self):
        if self.vue_temps is not None:
            self.vue_temps.destroy()
            self.vue_temps = None
        self.indication_temps.pack(pady=20)

    def _examiner_intervalles(self):
        if self.indice_actif is None:
            messagebox.showinfo("Base de temps", "Choisis d'abord un fichier dans l'arbre.")
            return
        if not self._profil_applique():
            messagebox.showinfo("Profil", "Clique sur Analyser ce fichier pour appliquer les champs modifiés.")
            return
        source, resultat = self.paquet.sources[self.indice_actif], self.paquet.resultats[self.indice_actif]
        def calcul(_annulation, _publier):
            from inspection_temps import preparer_inspection
            return preparer_inspection(source, resultat)
        def appliquer(inspection):
            from vue_temps import VueTemps
            self._effacer_inspection()
            self.vue_temps = VueTemps(self.conteneur_temps, inspection)
            self.indication_temps.pack_forget()
            self.vue_temps.pack(fill="both", expand=True)
            self.onglets.select(self.onglet_temps)
            self.activite.set(f"Intervalles examinés : {Path(inspection.fichier).name}. Temps bruts conservés.")
        self._lancer(calcul, appliquer)

    def _basculer_arbre(self) -> None:
        if self.volet_arbre.winfo_ismapped():
            self.volet_arbre.grid_remove()
        else:
            self.volet_arbre.grid()

    def _afficher(self, texte: str) -> None:
        self.details.configure(state="normal")
        self.details.delete("1.0", "end")
        self.details.insert("1.0", texte)
        self.details.configure(state="disabled")

    # === 4. Représenter l'état temporel sans transformer ni recaler les données ===
    def _actualiser_moniteur(self, source, resultat) -> None:
        """Préparer puis rendre visible le moniteur du fichier nouvellement choisi."""
        self.moniteur_modele = construire_moniteur(source, resultat)
        self.moniteur_visible = True
        self.moniteur_canvas.grid()
        self.bouton_moniteur.configure(text="Masquer le moniteur")
        if self.moniteur_modele["masquage_autorise"]:
            self.bouton_moniteur.configure(state="normal")
        else:
            self.bouton_moniteur.configure(state="disabled")
        self.moniteur_statut.set(f"Time Base Monitor — {self.moniteur_modele['message']}")
        self._tracer_moniteur()

    def _tracer_moniteur(self) -> None:
        """Dessiner un axe natif et les cinquante premiers repères d'anomalie."""
        canevas = self.moniteur_canvas
        canevas.delete("all")
        modele = self.moniteur_modele
        if not modele or not self.moniteur_visible:
            return
        largeur = max(canevas.winfo_width(), 150)
        x_debut, x_fin, y = 55, largeur - 55, 58
        couleurs = {"ok": "#17823b", "avertissement": "#b05a00", "erreur": "#b42318"}
        couleur = couleurs.get(modele["niveau"], "#555555")
        canevas.create_line(x_debut, y, x_fin, y, fill=couleur, width=4)
        canevas.create_line(x_debut, y - 8, x_debut, y + 8, fill="#333333")
        canevas.create_line(x_fin, y - 8, x_fin, y + 8, fill="#333333")
        canevas.create_text(x_debut, y + 22, text=str(modele["debut"] or "début"), anchor="n")
        canevas.create_text(x_fin, y + 22, text=str(modele["fin"] or "fin"), anchor="n")
        unite = modele["unite"] or "unité inconnue"
        pas = modele["repere_pas"] if modele["repere_pas"] is not None else "non qualifié"
        canevas.create_text((x_debut + x_fin) / 2, 17, text=f"Pas de référence : {pas} | {unite}",
                            fill="#333333")
        couleurs_marqueurs = {"temps_duplique": "#e69500", "retour_arriere": "#c00000",
                              "pas_hors_tolerance": "#7b2cbf"}
        for marqueur in modele["marqueurs"]:
            position = marqueur["position"]
            if position is None:
                continue
            x = x_debut + (x_fin - x_debut) * position
            canevas.create_line(x, y - 20, x, y + 14,
                                fill=couleurs_marqueurs.get(marqueur["type"], "#c00000"), width=2)
        canevas.create_text(x_debut, 112, anchor="w", text="Orange : doublon | Rouge : retour | Violet : pas hors tolérance", fill="#444444")
        if modele.get("marqueurs_tronques"):
            canevas.create_text(x_fin, 96, text=f"{len(modele['marqueurs'])}/{modele['nombre_marqueurs']} repères affichés",
                                anchor="e", fill="#b42318")

    def _basculer_moniteur(self) -> None:
        """Masquer seulement un bilan OK et conserver une confirmation textuelle."""
        if not self.moniteur_modele:
            return
        if self.moniteur_visible:
            if not self.moniteur_modele["masquage_autorise"]:
                return
            self.moniteur_visible = False
            self.moniteur_canvas.grid_remove()
            self.bouton_moniteur.configure(text="Afficher le moniteur")
            self.moniteur_statut.set("Time Base Monitor masqué — base de temps observée régulière.")
        else:
            self.moniteur_visible = True
            self.moniteur_canvas.grid()
            self.bouton_moniteur.configure(text="Masquer le moniteur")
            self.moniteur_statut.set(f"Time Base Monitor — {self.moniteur_modele['message']}")
            self._tracer_moniteur()

    # === 5. Tracé à la demande, sans changer les données ni le backend de Spyder ===
    def _afficher_courbe(self, superposer=False) -> None:
        """Préparer les points puis construire le widget graphique ; signaler un refus."""
        if self.indice_actif is None or not self.signal_choisi.get():
            messagebox.showinfo("Signal", "Choisis d'abord un fichier et un signal.")
            return
        source = self.paquet.sources[self.indice_actif]
        profil_affiche = tuple(v.get().strip() for v in (self.unite, self.pas, self.tolerance))
        profil_applique = tuple(v or "" for v in (source.unite, source.pas_attendu, source.tolerance))
        if profil_affiche != profil_applique:
            messagebox.showinfo("Profil", "Clique sur Analyser ce fichier pour appliquer les champs modifiés.")
            return
        resultat = self.paquet.resultats[self.indice_actif]
        colonne, typage = self.signal_choisi.get(), self.type_signal.get()
        def calcul(_annulation, _publier):
            signal = preparer_signal(source, resultat, colonne, typage)
            modele = construire_moniteur(source, resultat)
            return signal, modele
        def appliquer(contenu):
            signal, modele = contenu
            self.vue_signal = (self.arrangements.superposer(signal) if superposer else
                               self.arrangements.ajouter(signal, modele, source.decimale))
            self.onglets.select(self.onglet_courbe)
            self.activite.set(f"Signal affiché : {signal.colonne} — {Path(source.fichier).name}")
        self._lancer(calcul, appliquer)

    # Le fil de travail ne lit aucune StringVar et ne touche aucun widget.
    # Seul ce contrôleur applique les résultats complets depuis after().
    def _lancer(self, calcul, appliquer):
        if self.tache is not None:
            messagebox.showinfo("Calcul en cours", "Attendre la fin du calcul ou demander son annulation.")
            return False
        self.tache = TacheFond(calcul)
        self.progression.start(15)
        self.bouton_annuler.configure(state="normal")
        self._noter("Calcul en cours...")
        def surveiller():
            for nature, contenu in self.tache.lire():
                if nature == "progression":
                    self._noter(contenu)
                    continue
                # Une annulation peut arriver après publication mais avant la
                # relève Tk : vérifier aussi le drapeau à cet instant.
                annule = self.tache.annulation.is_set() or nature == "annule"
                self.tache = None
                self.progression.stop()
                self.bouton_annuler.configure(state="disabled")
                if annule:
                    self._noter("Calcul annulé ; résultat écarté, état précédent conservé.")
                elif nature == "erreur":
                    self._noter("Calcul non terminé : " + contenu)
                    messagebox.showerror("Analyse", contenu)
                else:
                    try:
                        appliquer(contenu)
                    except (ImportError, OSError, ValueError, RuntimeError, tk.TclError) as exc:
                        self._noter("Affichage non terminé : " + str(exc))
                        messagebox.showerror("Affichage", str(exc))
                return
            self.fenetre.after(80, surveiller)
        self.fenetre.after(80, surveiller)
        return True

    def _annuler(self):
        if self.tache is not None:
            self.tache.annuler()
            self.bouton_annuler.configure(state="disabled")
            self._noter("Annulation demandée ; la lecture en cours doit se terminer proprement.")

    def _dialogue_colonnes(self, titre, multiple, appliquer):
        """Choix explicite ; aucun 0/1 numérique n'est déclaré Bool en silence."""
        if self.indice_actif is None or not self._profil_applique():
            messagebox.showinfo(titre, "Choisir un CSV et appliquer son profil temporel.")
            return
        source = self.paquet.sources[self.indice_actif]
        resultat = self.paquet.resultats[self.indice_actif]
        if "erreur" in resultat:
            messagebox.showinfo(titre, "Corriger la lecture ou le profil du CSV.")
            return
        colonnes = [c for c in resultat["diagnostic_csv"]["columns"] if c != resultat["diagnostic_csv"]["time"]["column"]]
        dialogue = tk.Toplevel(self.fenetre)
        dialogue.title(titre)
        ttk.Label(dialogue, text="Bool : true/false ou 0/1. Toute autre valeur reste invalide.",
                  wraplength=480).pack(padx=10, pady=8)
        liste = tk.Listbox(dialogue, selectmode="extended" if multiple else "browse",
                           exportselection=False, width=55, height=min(12, max(3, len(colonnes))))
        for colonne in colonnes:
            liste.insert("end", colonne)
        liste.pack(fill="both", expand=True, padx=10)
        def valider():
            choix = [colonnes[i] for i in liste.curselection()]
            if not choix or (multiple and not 2 <= len(choix) <= 8):
                messagebox.showinfo(titre, "Choisir 2 à 8 colonnes." if multiple else "Choisir une colonne.", parent=dialogue)
                return
            def calcul(_annulation, _publier):
                signaux = [preparer_signal(source, resultat, c, "Bool", autoriser_vide=True) for c in choix]
                return signaux, construire_moniteur(source, resultat)
            def terminer(contenu):
                signaux, modele = contenu
                appliquer(signaux, modele, source.decimale)
                diagnostic = resultat["diagnostic_csv"]
                for c in choix:
                    self.types_signaux[(str(source.fichier), diagnostic["sha256"], c)] = "Bool"
                self._actualiser_arbre()
            if self._lancer(calcul, terminer):
                dialogue.destroy()
        ttk.Button(dialogue, text="Appliquer", command=valider).pack(anchor="e", padx=10, pady=10)

    def _groupe_bool(self):
        def appliquer(signaux, modele, decimale):
            self.vue_signal = self.arrangements.ajouter_groupe(signaux, modele, decimale)
            self.onglets.select(self.onglet_courbe)
            self._noter(f"Groupe de {len(signaux)} Bool : pistes et lectures indépendantes, sans interpolation.")
        self._dialogue_colonnes("Groupe de colonnes Bool", True, appliquer)

    def _condition_bool(self):
        try:
            vue = self.arrangements.vues_actives()[-1]
            if not hasattr(vue, "curseurs") or vue.signal.type_signal != "Float":
                raise ValueError("Afficher d'abord un panneau temporel Float dans l'onglet actif.")
        except ValueError as exc:
            messagebox.showinfo("Condition Bool", str(exc), parent=self.fenetre)
            return
        def appliquer(signaux, _modele, _decimale):
            if not vue.winfo_exists():
                raise ValueError("Le panneau a été fermé ; afficher de nouveau le signal Float.")
            vue.curseurs.definir_condition(signaux[0])
            vue.mode_curseur.set("Horizontal")
            vue._choisir_curseur()
            self._noter(f"Lecture horizontale : {signaux[0].colonne} vrai sur la même ligne uniquement.")
        self._dialogue_colonnes("Condition Bool du dernier panneau Float", False, appliquer)

    def _afficher_xy(self):
        if self.indice_actif is None or not self._profil_applique():
            messagebox.showinfo("X/Y", "Choisir un CSV et appliquer son profil temporel.")
            return
        source, resultat = self.paquet.sources[self.indice_actif], self.paquet.resultats[self.indice_actif]
        colonnes = self.liste_signaux.cget("values")
        if len(colonnes) < 2:
            messagebox.showinfo("X/Y", "Deux colonnes de signal sont nécessaires.")
            return
        dialogue = tk.Toplevel(self.fenetre)
        dialogue.title("Nuage X/Y — même CSV, aucune interpolation")
        choix = []
        for i, axe in enumerate(("X", "Y")):
            ttk.Label(dialogue, text=axe).grid(row=i, column=0, padx=8, pady=8)
            variable = tk.StringVar(value=colonnes[i])
            ttk.Combobox(dialogue, textvariable=variable, values=colonnes, state="readonly").grid(row=i, column=1)
            choix.append(variable)
        def afficher():
            x, y = (variable.get() for variable in choix)
            def calcul(_annulation, _publier):
                return (preparer_signal(source, resultat, x, "Float"),
                        preparer_signal(source, resultat, y, "Float"), construire_moniteur(source, resultat))
            def appliquer(contenu):
                self.arrangements.ajouter_xy(*contenu)
                self.onglets.select(self.onglet_courbe)
                self._noter(f"Nuage X/Y affiché : {x}, {y}. Appariement par ligne du même CSV.")
            if self._lancer(calcul, appliquer):
                dialogue.destroy()
        ttk.Button(dialogue, text="Afficher", command=afficher).grid(row=2, column=1, pady=8)

    def _fermer(self):
        if self.tache is not None:
            self.tache.annuler()
        self.fenetre.destroy()

    def _noter(self, message):
        self.activite.set(message)

    def _journaliser(self, *_args):
        self.journal_activite.append(f"{datetime.now().astimezone().isoformat(timespec='seconds')} | {self.activite.get()}")

    def _texte_fenetre(self, titre, texte):
        fenetre = tk.Toplevel(self.fenetre)
        fenetre.title(titre)
        fenetre.geometry("800x550")
        from tkinter.scrolledtext import ScrolledText
        zone = ScrolledText(fenetre, wrap="word")
        zone.pack(fill="both", expand=True)
        zone.insert("1.0", texte)
        zone.configure(state="disabled")

    def _document(self, chemin):
        try:
            self._texte_fenetre(chemin.name, chemin.read_text(encoding="utf-8"))
        except OSError as exc:
            messagebox.showerror("Documentation", str(exc))

    def _voir_activite(self):
        self._texte_fenetre("Journal de la session", "\n".join(self.journal_activite) or "Aucune action enregistrée.")

    # === 6. Journal sauvegardé seulement à la demande, CSV jamais écrits ===
    def _enregistrer(self) -> None:
        if not self.paquet.sources:
            messagebox.showinfo("Diagnostic", "Ajoute d'abord un fichier CSV.")
            return
        chemin = filedialog.asksaveasfilename(parent=self.fenetre, title="Enregistrer le diagnostic",
                                             defaultextension=".json", filetypes=[("JSON", "*.json")])
        if not chemin:
            return
        try:
            self.paquet.enregistrer_journal(chemin)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Enregistrement", str(exc))
            return
        self.activite.set(f"Diagnostic enregistré : {chemin}")


def main() -> None:
    """Ouvrir la fenêtre avec l'interpréteur courant, sans dépendre du kernel Spyder."""
    fenetre = tk.Tk()
    FenetreVISU(fenetre)
    try:
        preuve = enregistrer_environnement(PROJET, VERSION, fenetre)
        print(f"Configuration et dépendances enregistrées : {preuve}")
    except OSError as exc:
        print(f"Relevé d'environnement non enregistré : {exc}")
    fenetre.mainloop()


if __name__ == "__main__":
    main()
