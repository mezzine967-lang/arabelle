"""Contrôleur de l'application : toutes les ACTIONS de l'interface.

REQ_COMMON_KH_3003 : chaque action est externalisée ici ou dans un module
dédié ; MAIN.py se contente d'assembler les widgets (REQ_COMMON_KH_3002).
Le contrôleur reçoit les demandes des menus, de l'arbre et des onglets,
appelle les traitements de ``ptbg.core`` / ``ptbg.report`` et met à jour
l'affichage. Les lectures et analyses longues passent par ``BackgroundTask``
(REQ_COMMON_KH_4105) ; une erreur inattendue est journalisée et affichée sans
fermer l'outil.
"""
from __future__ import annotations

import hashlib
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog

import numpy as np

from ptbg.config import Settings
from ptbg.core.arrangement import TEMPLATES
from ptbg.core.csv_reader import ReadCancelled
from ptbg.core.data_package import SourceFile, Workspace, configure_time, load_source
from ptbg.core.diagnostic_report import file_report
from ptbg.core.multi_source import compare_sources
from ptbg.core.project import PROJECT_SUFFIX, ReportPage, load_project, save_project
from ptbg.core.signals import BinaryGroup, SignalType
from ptbg.gui.dialogs.analysis_dialogs import (ConditionalProcessingWindow, GroupDialog, HorizontalCursorDialog,
                                               XYDialog)
from ptbg.gui.dialogs.report_dialogs import HeaderDialog, PagesWindow, PreferencesDialog
from ptbg.gui.dialogs.time_base_dialog import TimeBaseDialog
from ptbg.gui.info_windows import TextWindow, read_document, sources_text, version_text
from ptbg.gui.tasks import BackgroundTask
from ptbg.gui.tree_panel import TreeRef
from ptbg.report.pdf_report import build_header, export_pdf
from ptbg.system.activity_log import ActivityLog
from ptbg.system.compat import open_with_default_application
from ptbg.system.environment import collect_environment
from ptbg.version import full_name

DEFAULT_TEMPLATE = "AL"


class Application:
    """État de la session et actions déclenchées par l'interface."""

    def __init__(self, root: tk.Tk, settings: Settings, log: ActivityLog) -> None:
        """Prépare l'état de la session ; les widgets sont fournis ensuite par ``attach``."""
        self.root = root
        self.settings = settings
        self.log = log
        self.workspace = Workspace()
        self.report_pages: list[ReportPage] = []
        self.project_path: Path | None = None
        self.project_hash = ""
        self.task: BackgroundTask | None = None
        self._pages_window: PagesWindow | None = None
        self.menu = self.path_bar = self.tree = self.graph = self.status = self.paned = None
        root.report_callback_exception = self._unexpected_error

    def attach(self, menu, path_bar, tree, graph, status, paned) -> None:
        """Reçoit les widgets construits par MAIN.py."""
        self.menu, self.path_bar, self.tree, self.graph, self.status, self.paned = (
            menu, path_bar, tree, graph, status, paned)
        self.log.add_listener(status.show_entry)
        self.graph.new_tab(DEFAULT_TEMPLATE)
        self.tree.refresh()
        environment = collect_environment()
        self.notify(f"Démarrage de {full_name()} — Python {environment.python_version} "
                    f"({environment.python_bits} bits), {environment.tk_version}, {environment.os_description}.")
        for package in environment.packages[:2]:          # numpy et matplotlib (directes)
            if package.status != "OK":
                self.notify(f"{package.name} {package.installed} : {package.status} (voir docs/DEPENDANCES.md).",
                            "AVERTISSEMENT")
        if not environment.python_tested():
            self.notify(f"Python {environment.python_version} hors de la plage testée.", "AVERTISSEMENT")

    # ------------------------------------------------------------ journal
    def notify(self, message: str, level: str = "INFO") -> None:
        """Ajoute un message au journal d'activité (barre d'état et fichier journal)."""
        self.log.log(message, level)

    def _unexpected_error(self, exc_type, exc, _traceback) -> None:
        """Aucune erreur imprévue ne ferme l'outil : elle est journalisée et montrée."""
        self.notify(f"Erreur inattendue : {exc_type.__name__} : {exc}", "ERREUR")
        messagebox.showerror("Erreur", f"{exc_type.__name__} : {exc}\n\nL'outil reste utilisable ; "
                             "le détail est dans le journal d'activité.", parent=self.root)

    def _busy(self) -> bool:
        """Vrai, et l'utilisateur est prévenu, si un traitement de fond est en cours."""
        if self.task is not None:
            messagebox.showinfo("Traitement en cours", "Attendre la fin du traitement ou l'annuler.",
                                parent=self.root)
            return True
        return False

    def cancel_task(self) -> None:
        """Bouton « Annuler » : demande l'arrêt coopératif du traitement en cours."""
        if self.task is not None:
            self.task.cancel()
            self.notify("Annulation demandée.", "AVERTISSEMENT")

    def _run(self, work, on_done, label: str) -> None:
        """Lance un traitement en arrière-plan avec barre d'avancement."""
        def done(result):
            """Fin normale : libère la tâche puis transmet le résultat."""
            self._end_task()
            on_done(result)

        def failed(exc, details):
            """Échec : journalise et affiche l'erreur ; l'outil reste utilisable."""
            self._end_task()
            self.notify(f"{label} : échec ({exc})", "ERREUR")
            messagebox.showerror(label, f"{exc}\n\n{details.splitlines()[-1]}", parent=self.root)

        self.status.start_progress()
        self.task = BackgroundTask(self.root, work, done, failed, self.status.set_progress).start()

    def _end_task(self) -> None:
        """Libère la tâche terminée et masque la barre d'avancement."""
        self.task = None
        self.status.stop_progress()

    # ------------------------------------------------------------ fichiers
    def open_files(self, paths=None) -> None:
        """Ouvre un ou plusieurs CSV (dialogue, ou chemins passés en ligne de commande)."""
        if self._busy():
            return
        if paths is None:
            paths = filedialog.askopenfilenames(parent=self.root, title="Ouvrir des fichiers CSV PTBG",
                                                filetypes=[("Fichiers CSV", "*.csv *.CSV"), ("Tous", "*.*")])
        if paths:
            self._load([Path(p) for p in paths])

    def open_folder(self) -> None:
        """Ouvre tous les CSV d'un dossier et de ses sous-dossiers (REQ 2105)."""
        if self._busy():
            return
        folder = filedialog.askdirectory(parent=self.root, title="Dossier contenant des CSV (sous-dossiers inclus)")
        if not folder:
            return
        paths = sorted(p for p in Path(folder).rglob("*") if p.is_file() and p.suffix.lower() == ".csv")
        if not paths:
            messagebox.showinfo("Ouvrir un dossier", "Aucun fichier .csv dans ce dossier.", parent=self.root)
            return
        self._load(paths)

    def _load(self, paths: list[Path], entries=None, after=None) -> None:
        """Lecture + analyse en arrière-plan ; chaque fichier est isolé (REQ 4105)."""
        settings = self.settings

        def work(task):
            """Fil de travail : lit et analyse chaque fichier (sans toucher à Tk)."""
            loaded = []
            for number, path in enumerate(paths):
                if task.cancel_event.is_set():
                    break
                task.progress(number / len(paths), f"Lecture de {path.name} ({number + 1}/{len(paths)})…")
                entry = entries[number] if entries else None
                try:
                    source = load_source(path, settings,
                                         lambda f, n=number: task.progress((n + f) / len(paths)),
                                         task.cancel_event,
                                         entry.time_settings if entry else None,
                                         entry.file_id if entry else None)
                except ReadCancelled:
                    break
                loaded.append((source, entry))
            return loaded

        def done(loaded):
            """Fil principal : range les fichiers dans leur paquet et rafraîchit l'IHM."""
            counts = {"OK": 0, "AVERTISSEMENT": 0, "ERREUR": 0}
            for source, entry in loaded:
                package = self.workspace.active_package
                if entry is not None:
                    package = next(p for p in self.workspace.packages if p.name == entry.package)
                    self._apply_project_entry(source, entry)
                package.files.append(source)
                label = source.status().label
                counts[label if label in counts else "OK"] += 1
                self.notify(f"{source.name} chargé dans « {package.name} » : {label}",
                            "ERREUR" if label == "ERREUR" else "AVERTISSEMENT" if label == "AVERTISSEMENT" else "INFO")
            if len(loaded) < len(paths):
                self.notify(f"Chargement interrompu : {len(loaded)}/{len(paths)} fichier(s).", "AVERTISSEMENT")
            self.notify(f"{len(loaded)} fichier(s) : {counts['OK']} conforme(s), {counts['AVERTISSEMENT']} avec "
                        f"avertissement, {counts['ERREUR']} en erreur. Double-cliquer une variable pour l'afficher.")
            self.tree.refresh()
            self.graph.redraw_all()
            if after:
                after()

        self._run(work, done, "Chargement des CSV")

    def _apply_project_entry(self, source: SourceFile, entry) -> None:
        """Réapplique types forcés et groupes d'un projet ; signale un CSV modifié."""
        if not source.is_loaded:
            return
        if entry.sha256 and entry.sha256 != source.sha256:
            self.notify(f"{source.name} a changé depuis l'enregistrement du projet (empreinte différente).",
                        "AVERTISSEMENT")
        for name, signal_type in entry.type_overrides.items():
            if name in source.variable_names():
                source.set_type(name, signal_type)
        source.groups = {g.name: g for g in entry.groups}

    def new_package(self) -> None:
        """Crée un paquet de données vide qui devient le paquet actif (REQ 5200)."""
        package = self.workspace.add_package()
        self.notify(f"« {package.name} » créé : il reçoit les prochains fichiers ouverts.")
        self.tree.refresh()

    def selected_source(self) -> SourceFile | None:
        """Fichier désigné dans l'arbre, ou le seul fichier chargé."""
        for ref in self.tree.selection():
            if ref.kind in ("file", "time", "var", "group", "issue", "diag", "groups"):
                return self.workspace.find(ref.owner_id)
        files = self.workspace.files()
        return files[0] if len(files) == 1 else None

    def _ask_source(self, title: str) -> SourceFile | None:
        """Fichier sélectionné dans l'arbre, sinon message invitant à en choisir un."""
        source = self.selected_source()
        if source is None:
            messagebox.showinfo(title, "Sélectionner d'abord un fichier dans l'arbre.", parent=self.root)
        return source

    def remove_selection(self) -> None:
        """Ferme les fichiers / paquets sélectionnés et retire leurs courbes des onglets."""
        refs = self.tree.selection()
        files = [self.workspace.find(r.owner_id) for r in refs if r.kind == "file"]
        packages = [p for p in self.workspace.packages if any(r.kind == "package" and r.owner_id == p.id for r in refs)]
        files = [f for f in files if f is not None]
        if not files and not packages:
            messagebox.showinfo("Fermer", "Sélectionner un fichier ou un paquet dans l'arbre.", parent=self.root)
            return
        names = ", ".join([p.name for p in packages] + [f.name for f in files])
        if not messagebox.askyesno("Fermer", f"Fermer : {names} ?", parent=self.root):
            return
        for package in packages:
            files += package.files
            self.workspace.remove_package(package)
        removed = {source.id for source in files}
        for source in files:
            self.workspace.remove_file(source)
        for tab in self.graph.tabs:
            for axle in tab.state.axles:
                axle.curves = [c for c in axle.curves if c.file_id not in removed]
                if (axle.xy_x and axle.xy_x.file_id in removed) or (axle.xy_y and axle.xy_y.file_id in removed):
                    axle.xy_x = axle.xy_y = None
        self.notify(f"Fermé : {names}.")
        self.tree.refresh()
        self.graph.redraw_all()

    # ---------------------------------------------------------------- arbre
    def on_tree_selection(self, refs: list[TreeRef]) -> None:
        """Met à jour la barre de chemin « paquet > fichier > variable »."""
        parts = []
        if refs:
            ref = refs[0]
            source = self.workspace.find(ref.owner_id)
            package = self.workspace.package_of(source) if source else next(
                (p for p in self.workspace.packages if p.id == ref.owner_id), None)
            parts = [p for p in (package.name if package else "", source.name if source else "", ref.name) if p]
        tab = self.graph.active_tab() if self.graph else None
        self.path_bar.show(parts, tab.state.title if tab else None)

    def on_tab_changed(self) -> None:
        """Changement d'onglet : met à jour la barre de chemin."""
        if self.tree is not None:
            self.on_tree_selection(self.tree.selection())

    def activate_tree_item(self, ref: TreeRef) -> None:
        """Double-clic : variable/groupe -> axe actif ; paquet -> actif ; fichier -> base de temps."""
        if ref.kind in ("var", "group"):
            self.add_refs([ref])
        elif ref.kind == "package":
            self._set_active_package(ref.owner_id)
        elif ref.kind in ("file", "time"):
            self.configure_time_base(self.workspace.find(ref.owner_id))
        elif ref.kind in ("issue", "diag"):
            self.show_diagnostic(self.workspace.find(ref.owner_id))

    def _set_active_package(self, package_id: str) -> None:
        """Rend actif un paquet : il recevra les prochains fichiers ouverts."""
        for index, package in enumerate(self.workspace.packages):
            if package.id == package_id:
                self.workspace.active_index = index
                self.notify(f"Paquet actif : {package.name}.")
        self.tree.refresh()

    def add_refs(self, refs: list[TreeRef], tab=None, axle_index=None) -> None:
        """Ajoute des variables / groupes de l'arbre à l'axe actif (ou à l'axe donné)."""
        items = [(r.owner_id, r.name, r.kind == "group") for r in refs if r.kind in ("var", "group")]
        tab = tab or self.graph.active_tab()
        if items and tab is not None:
            tab.add_curves(items, axle_index)

    def drop_tree_items(self, refs: list[TreeRef], x_root: int, y_root: int) -> None:
        """Glisser-déposer de l'arbre vers un axe de l'onglet actif."""
        tab = self.graph.active_tab()
        if tab is None or tab.renderer is None:
            return
        widget = tab.canvas.get_tk_widget()
        inside_x = x_root - widget.winfo_rootx()
        inside_y = y_root - widget.winfo_rooty()
        if not (0 <= inside_x < widget.winfo_width() and 0 <= inside_y < widget.winfo_height()):
            return
        display = (inside_x, widget.winfo_height() - inside_y)      # origine Matplotlib : en bas
        for index, ax in enumerate(tab.renderer.axes):
            if ax.bbox.contains(*display):
                self.add_refs(refs, tab, index)
                return
        self.add_refs(refs, tab)

    def tree_context_menu(self, widget, refs: list[TreeRef]):
        """Menu contextuel adapté au genre des éléments sélectionnés dans l'arbre."""
        menu = tk.Menu(widget, tearoff=False)
        kinds = {r.kind for r in refs}
        source = self.workspace.find(refs[0].owner_id) if refs else None
        if kinds & {"var", "group"}:
            menu.add_command(label="Ajouter à l'axe actif", command=lambda: self.add_refs(refs))
            sub = tk.Menu(menu, tearoff=False)
            for item in TEMPLATES:
                sub.add_command(label=item.name, command=lambda k=item.key: self.add_refs(refs, self.graph.new_tab(k)))
            menu.add_cascade(label="Afficher dans un nouvel onglet", menu=sub)
        if "var" in kinds and source is not None:
            types = tk.Menu(menu, tearoff=False)
            names = [r.name for r in refs if r.kind == "var"]
            types.add_command(label="Automatique", command=lambda: self.set_signal_type(source, names, None))
            for signal_type in SignalType:
                types.add_command(label=signal_type.value,
                                  command=lambda t=signal_type: self.set_signal_type(source, names, t))
            menu.add_cascade(label="Type de la variable", menu=types)
            menu.add_command(label="Créer un groupe binaire avec la sélection…",
                             command=lambda: self.create_group(source, names))
        if "group" in kinds and source is not None:
            menu.add_command(label="Supprimer le groupe",
                             command=lambda: self._delete_groups(source, [r.name for r in refs if r.kind == "group"]))
        if kinds & {"file", "time", "issue", "diag"} and source is not None:
            menu.add_command(label="Configurer la base de temps…", command=lambda: self.configure_time_base(source))
            menu.add_command(label="Diagnostic complet…", command=lambda: self.show_diagnostic(source))
            menu.add_command(label="Créer un groupe binaire…", command=lambda: self.create_group(source))
            menu.add_command(label="Fermer le fichier", command=self.remove_selection)
        if "package" in kinds:
            menu.add_command(label="Définir comme paquet actif",
                             command=lambda: self._set_active_package(refs[0].owner_id))
            menu.add_command(label="Renommer le paquet…", command=lambda: self._rename_package(refs[0].owner_id))
            menu.add_command(label="Comparer les sources (multi-PLC)…",
                             command=lambda: self.compare_sources(refs[0].owner_id))
            menu.add_command(label="Fermer le paquet", command=self.remove_selection)
        return menu if menu.index("end") is not None else None

    def _rename_package(self, package_id: str) -> None:
        """Renomme un paquet de données."""
        package = next((p for p in self.workspace.packages if p.id == package_id), None)
        name = package and simpledialog.askstring("Paquet", "Nouveau nom :", initialvalue=package.name,
                                                  parent=self.root)
        if name:
            package.name = name.strip()
            self.tree.refresh()

    def set_signal_type(self, source: SourceFile, names: list[str], signal_type) -> None:
        """Force le type Bool / Float / Texte, ou le type automatique (REQ 5202)."""
        for name in names:
            source.set_type(name, signal_type)
        self.notify(f"Type de {', '.join(names)} : {signal_type.value if signal_type else 'automatique'}.")
        self.tree.refresh()
        self.graph.redraw_all()

    def create_group(self, source: SourceFile | None = None, preselected=None) -> None:
        """Crée un groupe binaire (REQ 2201) à partir de Bool choisis dans un dialogue."""
        source = source or self._ask_source("Groupe binaire")
        if source is None or not source.is_loaded:
            return
        preselected = preselected or [r.name for r in self.tree.selection() if r.kind == "var"]
        dialog = GroupDialog(self.root, source, preselected)
        if dialog.result:
            name, members = dialog.result
            source.groups[name] = BinaryGroup(name, members)
            self.notify(f"Groupe binaire « {name} » créé ({len(members)} bits) dans {source.name}.")
            self.tree.refresh()

    def _delete_groups(self, source: SourceFile, names: list[str]) -> None:
        """Supprime des groupes binaires d'un fichier."""
        for name in names:
            source.groups.pop(name, None)
        self.tree.refresh()
        self.graph.redraw_all()

    # ----------------------------------------------------------- onglets
    def new_tab(self, key: str):
        """Ouvre un onglet depuis un modèle de disposition (REQ 5300)."""
        tab = self.graph.new_tab(key)
        self.notify(f"Nouvel onglet « {tab.state.title} ».")
        return tab

    def close_tab(self, tab=None) -> None:
        """Ferme un onglet (l'onglet actif par défaut) ; un onglet vide est recréé
        s'il n'en reste aucun."""
        tab = tab or self.graph.active_tab()
        if tab is not None:
            self.graph.close_tab(tab)
        if not self.graph.tabs:
            self.graph.new_tab(DEFAULT_TEMPLATE)

    def rename_tab(self) -> None:
        """Renomme l'onglet actif (titre repris dans le rapport)."""
        tab = self.graph.active_tab()
        title = tab and simpledialog.askstring("Onglet", "Nouveau titre :", initialvalue=tab.state.title,
                                               parent=self.root)
        if title:
            self.graph.rename_tab(tab, title.strip())
            self.on_tab_changed()

    def toggle_tree(self) -> None:
        """REQ 5105 : masquer / réafficher l'arbre."""
        if str(self.tree) in [str(pane) for pane in self.paned.panes()]:
            self._tree_width = self.tree.winfo_width()
            self.paned.forget(self.tree)
            self.menu.tree_visible.set(False)
        else:
            self.paned.add(self.tree, before=self.graph, width=getattr(self, "_tree_width", 380),
                           minsize=180, stretch="never")
            self.menu.tree_visible.set(True)

    def set_time_mode(self, mode: str) -> None:
        """Bascule l'axe des temps relatif / absolu (REQ 4107) ; curseurs remis à zéro."""
        if mode == "absolute" and not self.workspace.absolute_available():
            missing = [s.name for s in self.workspace.loaded_files() if s.conversion.origin_ns is None]
            messagebox.showwarning("Axe des temps absolu",
                                   "Chaque fichier doit avoir une origine absolue (horodatage hh:mm:ss ou "
                                   "date-heure, ou origine saisie dans Base de temps > Configurer).\n\n"
                                   f"Sans origine : {', '.join(missing) or 'aucun fichier chargé'}", parent=self.root)
            self.menu.time_mode.set(self.workspace.time_mode)
            return
        self.workspace.set_time_mode(mode)
        for tab in self.graph.tabs:          # les positions changent de repère : curseurs remis à zéro
            tab.state.xlim, tab.state.t_global, tab.state.global_cursor = None, None, False
            for axle in tab.state.axles:
                axle.t1 = axle.t2 = axle.xy_t = None
                axle.cursor_mode = "none"
        self.notify(f"Axe des temps : {'absolu' if mode == 'absolute' else 'relatif'} (curseurs réinitialisés).")
        self.graph.redraw_all()

    # ------------------------------------------------------ base de temps
    def configure_time_base(self, source: SourceFile | None = None) -> None:
        """Dialogue de base de temps puis réanalyse en arrière-plan (REQ 4106)."""
        source = source or self._ask_source("Base de temps")
        if source is None:
            return
        if not source.is_loaded:
            self.show_diagnostic(source)
            return
        assumed = [s for s in self.workspace.loaded_files() if s is not source and s.conversion.unit_assumed]
        dialog = TimeBaseDialog(self.root, source, self.settings.tolerance_pct, len(assumed))
        if dialog.result is None or self._busy():
            return
        changes = [(source, dialog.result)]
        if dialog.share_unit:     # unité confirmée d'un coup pour les autres PLC du même type
            changes += [(other, replace(other.time_settings, unit=dialog.result.unit)) for other in assumed]

        def work(_task):
            """Réanalyse de chaque fichier modifié (fil de travail)."""
            for target, settings in changes:
                configure_time(target, self.settings, settings)

        def done(_result):
            """Réanalyse terminée : rafraîchit l'arbre et les onglets."""
            for target, _settings in changes:
                self.notify(f"Base de temps de {target.name} reconfigurée : {target.time_status().label} — "
                            f"{target.analysis.summary()}")
            self.tree.refresh()
            self.graph.redraw_all()

        self._run(work, done, "Analyse de la base de temps")

    def show_diagnostic(self, source: SourceFile | None = None) -> None:
        """Fenêtre de diagnostic complet du fichier (lecture, base de temps, événements)."""
        source = source or self._ask_source("Diagnostic")
        if source is not None:
            TextWindow(self.root, f"Diagnostic — {source.name}", file_report(source, self.workspace.timeline()),
                       markdown=True)

    def compare_sources(self, package_id: str | None = None) -> None:
        """Fenêtre de comparaison des sources du paquet (REQ 2102, 2104)."""
        package = next((p for p in self.workspace.packages if p.id == package_id), self.workspace.active_package)
        issues = compare_sources(package.files, self.workspace.timeline())
        text = "\n".join([f"# Comparaison des sources — {package.name}", ""] +
                         [f"- {issue.as_text()}" for issue in issues]) if issues else \
            f"# Comparaison des sources — {package.name}\n\nAu moins deux fichiers chargés sont nécessaires."
        TextWindow(self.root, "Comparaison des sources", text, markdown=True)

    def toggle_monitor(self) -> None:
        """Masque ou réaffiche le TBM de l'onglet actif (règle de REQ 4103)."""
        tab = self.graph.active_tab()
        if tab is not None:
            tab.toggle_monitor()

    # --------------------------------------------------------------- outils
    def horizontal_cursor(self) -> None:
        """REQ 5406 : réservé aux signaux analogiques ; REQ 5407 : condition Bool."""
        tab = self.graph.active_tab()
        if tab is None:
            return
        if not tab.float_curve_selected():
            messagebox.showwarning("Curseur horizontal",
                                   "Le curseur horizontal ne s'applique qu'aux signaux analogiques : choisir un "
                                   "axe temporel et une courbe Float sélectionnée.", parent=self.root)
            return
        axle = tab.axle()
        curve_values = self.workspace.find(axle.selected_curve().file_id).signal(axle.selected_curve().name).values
        finite = curve_values[np.isfinite(curve_values)]
        suggested = float(np.median(finite)) if finite.size else 0.0
        dialog = HorizontalCursorDialog(self.root, self.workspace, axle, suggested)
        if dialog.result:
            axle.h_enabled, axle.h_level, axle.h_condition = dialog.result
            self.notify(f"Curseur horizontal axe {tab.active_axle + 1} : niveau {axle.h_level:.6g}"
                        + (f", condition {axle.h_condition.describe()}" if axle.h_condition else ""))
            tab.update_cursors()

    def configure_xy(self) -> None:
        """Choix des signaux X / Y du nuage de corrélation (REQ 5408)."""
        tab = self.graph.active_tab()
        if tab is None:
            return
        xy_axles = [i for i, a in enumerate(tab.state.axles) if a.kind == "xy"]
        if not xy_axles:
            if not messagebox.askyesno("Nuage X/Y", "L'onglet actif n'a pas d'axe X/Y. Ouvrir un onglet "
                                       "« Temporel + nuage X/Y » ?", parent=self.root):
                return
            tab = self.graph.new_tab("XY")
            xy_axles = [i for i, a in enumerate(tab.state.axles) if a.kind == "xy"]
        tab.set_active_axle(xy_axles[0])
        dialog = XYDialog(self.root, self.workspace, tab.axle())
        if dialog.result:
            axle = tab.axle()
            axle.xy_x, axle.xy_y, axle.xy_mode = dialog.result
            self.notify(f"Nuage X/Y : {axle.xy_y.name} = f({axle.xy_x.name}).")
            tab.redraw()

    def conditional_processing(self) -> None:
        """Ouvre la fenêtre de traitement conditionnel (section 4.5)."""
        ConditionalProcessingWindow(self.root, self.workspace, self.notify)

    def preferences(self) -> None:
        """Modifie les préférences ; réanalyse les bases de temps si les seuils changent."""
        before = (self.settings.tolerance_pct, self.settings.frequency_change_min_run,
                  self.settings.default_counter_unit, self.settings.aberrant_jump_periods)
        dialog = PreferencesDialog(self.root, self.settings)
        if not dialog.result:
            return
        for key, value in dialog.result.items():
            setattr(self.settings, key, value)
        error = self.settings.save()
        self.notify(error or "Préférences enregistrées.", "AVERTISSEMENT" if error else "INFO")
        after = (self.settings.tolerance_pct, self.settings.frequency_change_min_run,
                 self.settings.default_counter_unit, self.settings.aberrant_jump_periods)
        if before != after and self.workspace.loaded_files() and not self._busy():
            sources = self.workspace.loaded_files()
            self._run(lambda task: [configure_time(s, self.settings) for s in sources],
                      lambda _r: (self.tree.refresh(), self.graph.redraw_all(),
                                  self.notify("Bases de temps réanalysées avec les nouvelles préférences.")),
                      "Réanalyse des bases de temps")
        else:
            self.graph.redraw_all()

    def axle_context_menu(self, tab, index: int):
        """Menu contextuel d'un axe (clic droit)."""
        axle = tab.state.axles[index]
        menu = tk.Menu(self.root, tearoff=False)
        if axle.kind == "xy":
            menu.add_command(label="Choisir X et Y…", command=self.configure_xy)
            return menu
        for value, label in (("single", "Curseur vertical simple"), ("double", "Double curseur"),
                             ("none", "Aucun curseur vertical")):
            menu.add_command(label=label, command=lambda v=value: tab.set_cursor_mode(v))
        menu.add_separator()
        menu.add_command(label="Curseur horizontal et condition…", command=self.horizontal_cursor)
        if axle.h_enabled:
            menu.add_command(label="Retirer le curseur horizontal",
                             command=lambda: (setattr(axle, "h_enabled", False), tab.update_cursors()))
        if axle.curves:
            menu.add_separator()
            choose = tk.Menu(menu, tearoff=False)
            for position, ref in enumerate(axle.curves):
                choose.add_command(label=ref.name, command=lambda p=position: tab._select_curve(p))
            menu.add_cascade(label="Courbe sélectionnée", menu=choose)
            menu.add_command(label="Retirer la courbe sélectionnée", command=tab.remove_selected_curve)
            menu.add_command(label="Vider l'axe", command=tab.clear_axle)
        menu.add_command(label="Échelle Y automatique",
                         command=lambda: (setattr(axle, "ylim", None), tab.redraw()))
        return menu

    # --------------------------------------------------------------- rapport
    def edit_report_header(self) -> None:
        """Saisie des champs libres de l'en-tête du rapport (REQ 6005)."""
        dialog = HeaderDialog(self.root, self.settings)
        if dialog.result:
            for key, value in dialog.result.items():
                setattr(self.settings, key, value)
            self.settings.save()
            self.notify("En-tête du rapport mis à jour.")

    def _page_from_active_tab(self) -> ReportPage | None:
        """Capture figée de l'onglet actif avec l'axe des temps courant."""
        tab = self.graph.active_tab()
        if tab is None:
            return None
        timeline = self.workspace.timeline()
        return ReportPage(tab.capture(), timeline.mode, timeline.ref_ns)

    def automatic_report(self) -> None:
        """REQ 6003 : édition unique de l'onglet actif."""
        page = self._page_from_active_tab()
        if page is not None:
            self._export([page], f"rapport_auto_{datetime.now():%Y%m%d_%H%M%S}.pdf")

    def add_report_page(self) -> None:
        """REQ 6004 : ajoute la vue active (curseurs, zoom, X/Y...) comme page suivante."""
        page = self._page_from_active_tab()
        if page is None:
            return
        comment = simpledialog.askstring("Rapport pas à pas", "Commentaire de la page (facultatif) :",
                                         parent=self.root)
        if comment is None:
            return
        page.tab.comment = comment.strip()
        self.report_pages.append(page)
        self.notify(f"Page {len(self.report_pages)} ajoutée au rapport pas à pas : « {page.tab.title} ».")
        if self._pages_window is not None and self._pages_window.winfo_exists():
            self._pages_window.refresh()

    def manage_report_pages(self) -> None:
        """Fenêtre de gestion des pages du rapport pas à pas (une seule à la fois)."""
        if self._pages_window is not None and self._pages_window.winfo_exists():
            self._pages_window.lift()
        else:
            self._pages_window = PagesWindow(self.root, self)

    def export_step_report(self) -> None:
        """Génère le PDF pas à pas, pages dans l'ordre choisi (REQ 6004)."""
        if not self.report_pages:
            messagebox.showinfo("Rapport pas à pas", "Aucune page : utiliser Rapport > Pas à pas : ajouter la vue "
                                "active.", parent=self.root)
            return
        self._export(self.report_pages, f"rapport_pas_a_pas_{datetime.now():%Y%m%d_%H%M%S}.pdf")

    def _export(self, pages: list[ReportPage], default_name: str) -> None:
        """Demande le fichier, construit l'en-tête, écrit le PDF et propose de l'ouvrir."""
        path = filedialog.asksaveasfilename(parent=self.root, title="Enregistrer le rapport PDF",
                                            defaultextension=".pdf", initialfile=default_name,
                                            filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        header = build_header(self.settings, self.workspace, pages, self.project_path, self.project_hash)
        self.root.configure(cursor="watch")
        self.status.start_progress()
        try:
            def progress(number, count):
                """Fait avancer la barre d'état pendant l'écriture des pages."""
                self.status.set_progress(number / count, f"Rapport : page {number}/{count}…")
                self.root.update_idletasks()
            export_pdf(Path(path), pages, header, self.workspace, self.settings, progress)
        except Exception as exc:  # noqa: BLE001 - échec d'écriture affiché, outil conservé
            self.notify(f"Rapport non écrit : {exc}", "ERREUR")
            messagebox.showerror("Rapport PDF", f"Rapport non écrit : {exc}", parent=self.root)
            return
        finally:
            self.root.configure(cursor="")
            self.status.stop_progress()
        self.notify(f"Rapport PDF écrit ({len(pages)} page(s) + traçabilité) : {path}")
        if messagebox.askyesno("Rapport PDF", f"Rapport enregistré :\n{path}\n\nL'ouvrir ?", parent=self.root):
            error = open_with_default_application(Path(path))
            if error:
                self.notify(error, "AVERTISSEMENT")

    # --------------------------------------------------------------- projet
    def save_project(self, ask: bool = False) -> None:
        """Enregistre le projet ; son SHA-256 alimente l'en-tête des rapports (REQ 6005)."""
        path = self.project_path
        if ask or path is None:
            chosen = filedialog.asksaveasfilename(parent=self.root, title="Enregistrer le projet",
                                                  defaultextension=PROJECT_SUFFIX,
                                                  filetypes=[("Projet VISU PTBG", "*" + PROJECT_SUFFIX)])
            if not chosen:
                return
            path = Path(chosen)
        tabs = [tab.capture() for tab in self.graph.tabs]
        header = {key: getattr(self.settings, key) for key in
                  ("project_name", "project_unit", "issuer", "project_reference")}
        try:
            save_project(path, self.workspace, tabs, self.report_pages, header)
        except OSError as exc:
            messagebox.showerror("Projet", f"Enregistrement impossible : {exc}", parent=self.root)
            return
        self.project_path = path
        self.project_hash = hashlib.sha256(path.read_bytes()).hexdigest()
        self.notify(f"Projet enregistré : {path} (SHA-256 {self.project_hash[:16]}…)")

    def open_project(self) -> None:
        """Rouvre un projet : paquets, fichiers (relus), onglets et pages de rapport."""
        if self._busy():
            return
        chosen = filedialog.askopenfilename(parent=self.root, title="Ouvrir un projet",
                                            filetypes=[("Projet VISU PTBG", "*" + PROJECT_SUFFIX), ("Tous", "*.*")])
        if not chosen:
            return
        try:
            data = load_project(Path(chosen))
        except (OSError, ValueError, KeyError) as exc:
            messagebox.showerror("Projet", f"Projet illisible : {exc}", parent=self.root)
            return
        if self.workspace.files() and not messagebox.askyesno(
                "Projet", "Remplacer les données et onglets actuels par ceux du projet ?", parent=self.root):
            return
        self.workspace = Workspace()
        self.workspace.packages[0].name = data.packages[0] if data.packages else self.workspace.packages[0].name
        for name in data.packages[1:]:
            self.workspace.add_package(name)
        self.workspace.active_index = 0
        for tab in list(self.graph.tabs):
            self.graph.close_tab(tab)
        for key, value in data.header.items():
            setattr(self.settings, key, value)
        self.project_path = Path(chosen)
        self.project_hash = hashlib.sha256(self.project_path.read_bytes()).hexdigest()

        def restore():
            """Après rechargement des CSV : axe des temps, onglets et pages du projet."""
            if data.time_mode == "absolute" and self.workspace.absolute_available():
                self.workspace.set_time_mode("absolute")
                self.menu.time_mode.set("absolute")
            for state in data.tabs:
                self.graph.new_tab(state.template_key, state)
            if not self.graph.tabs:
                self.graph.new_tab(DEFAULT_TEMPLATE)
            self.report_pages = data.pages
            self.notify(f"Projet ouvert : {chosen}")

        self._load([entry.path for entry in data.files], data.files, restore)

    # ----------------------------------------------------------- information
    def show_version(self) -> None:
        """Information > Version de l'outil (REQ 5101)."""
        TextWindow(self.root, "Version de l'outil", version_text(), markdown=True)

    def show_history(self) -> None:
        """Information > Historique des modifications : CHANGELOG.md (REQ 5101)."""
        TextWindow(self.root, "Historique des modifications", read_document("CHANGELOG.md"), markdown=True)

    def show_sources(self) -> None:
        """Information > Sources : code, bibliothèques et fichiers (REQ 5101, 3004)."""
        TextWindow(self.root, "Sources", sources_text(self.workspace), markdown=True)

    def show_help(self) -> None:
        """Information > Fichier d'aide : docs/GUIDE_UTILISATEUR.md (REQ 5101)."""
        TextWindow(self.root, "Aide — " + full_name(), read_document("docs/GUIDE_UTILISATEUR.md"), markdown=True)

    def show_traceability(self) -> None:
        """Information > Traçabilité des requis : docs/TRACABILITE_REQUIS.md."""
        TextWindow(self.root, "Traçabilité des requis", read_document("docs/TRACABILITE_REQUIS.md"), markdown=True)

    def show_log(self) -> None:
        """Journal d'activité complet de la session (REQ 5102)."""
        where = f"Fichier journal : {self.log.file_path}\n\n" if self.log.file_path else ""
        TextWindow(self.root, "Journal d'activité", where + self.log.as_text())

    def quit(self) -> None:
        """Quitte, après confirmation si des données sont chargées."""
        if self.workspace.files() and not messagebox.askyesno("Quitter", f"Quitter {full_name()} ?",
                                                              parent=self.root):
            return
        self.notify("Fermeture de l'outil.")
        self.shutdown()

    def shutdown(self) -> None:
        """Arrêt propre : traitement annulé, minuteries arrêtées, onglets libérés."""
        if self.task is not None:
            self.task.cancel()
        self.status.stop_clock()
        for tab in list(self.graph.tabs):
            tab.dispose()
        self.root.destroy()
