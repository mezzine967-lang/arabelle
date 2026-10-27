"""Arbre des données, zone gauche de la fenêtre.

- REQ_COMMON_KH_5103 : zone gauche = visualiseur de l'arborescence des données ;
- REQ_COMMON_KH_5105 : la zone peut être masquée (bouton « Masquer », F9, menu) ;
- REQ_COMMON_KH_5200 : niveau 1 = paquet de données (le paquet actif est marqué) ;
- REQ_COMMON_KH_5201 : niveau 2 = fichiers CSV d'une ou plusieurs sources ;
- REQ_COMMON_KH_5202 : dans chaque fichier, toutes les variables et leur type
  Bool / Float (Texte pour des états énumérés hors spécification) ;
- REQ_COMMON_KH_5203 : dans chaque fichier, sa base de temps dédiée.

Identifiants des nœuds : « genre:id_fichier[:nom] », par exemple
``var:3fa2b1c0:VAR_input``. Le contrôleur reçoit des références décodées
(``TreeRef``), jamais des identifiants Tk.
"""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import ttk

from ptbg.core.diagnostics import Severity
from ptbg.core.signals import SignalType
from ptbg.core.time_base import ms
from ptbg.gui.icons import Icons, bold_font
from ptbg.plotting.styles import SEVERITY_COLORS

DRAG_THRESHOLD_PX = 6


@dataclass(frozen=True)
class TreeRef:
    """Élément de l'arbre décodé : kind = package|file|time|var|group|issue|folder."""
    kind: str
    owner_id: str          # id du paquet ou du fichier
    name: str = ""


def _parse(iid: str) -> TreeRef:
    """Décode un identifiant de nœud Tk en ``TreeRef``."""
    parts = iid.split(":", 2)
    return TreeRef(parts[0], parts[1] if len(parts) > 1 else "", parts[2] if len(parts) > 2 else "")


class TreePanel(ttk.Frame):
    """Arbre Paquet > Fichier > Base de temps / Groupes / Diagnostic / Variables."""

    def __init__(self, master, controller) -> None:
        """Titre, champ de filtre et arbre avec ses liaisons souris."""
        super().__init__(master)
        self.controller = controller
        self.icons = Icons()
        self.bold = bold_font()
        self.filter_text = tk.StringVar()
        self._drag: dict | None = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Label(top, text="Arbre des données", font=self.bold).pack(side="left", padx=4)
        ttk.Button(top, text="Masquer", command=controller.toggle_tree).pack(side="right")
        search = ttk.Frame(self)
        search.pack(fill="x", pady=2)
        ttk.Label(search, text="Filtrer :").pack(side="left", padx=(4, 2))
        entry = ttk.Entry(search, textvariable=self.filter_text)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 4))
        self.filter_text.trace_add("write", lambda *_: self.refresh())

        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.tree = ttk.Treeview(body, columns=("type", "info"), selectmode="extended")
        self.tree.heading("#0", text="Élément")
        self.tree.heading("type", text="Type")
        self.tree.heading("info", text="Détail")
        self.tree.column("#0", width=230, minwidth=120, stretch=True)
        self.tree.column("type", width=70, minwidth=50, stretch=False)
        self.tree.column("info", width=260, minwidth=80, stretch=False)
        self.tree.tag_configure("active", font=self.bold)
        for severity in (Severity.WARNING, Severity.ERROR):
            self.tree.tag_configure(severity.label, foreground=SEVERITY_COLORS[severity])
        yscroll = ttk.Scrollbar(body, orient="vertical", command=self.tree.yview)
        xscroll = ttk.Scrollbar(body, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=yscroll.set, xscrollcommand=xscroll.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")
        body.rowconfigure(0, weight=1)
        body.columnconfigure(0, weight=1)

        self.tree.bind("<<TreeviewSelect>>", lambda _e: controller.on_tree_selection(self.selection()))
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Button-3>", self._on_context_menu)
        self.tree.bind("<ButtonPress-1>", self._on_press, add=True)
        self.tree.bind("<B1-Motion>", self._on_motion, add=True)
        self.tree.bind("<ButtonRelease-1>", self._on_release, add=True)

    # -------------------------------------------------------------- contenu
    def selection(self) -> list[TreeRef]:
        """Éléments sélectionnés, décodés."""
        return [_parse(iid) for iid in self.tree.selection()]

    def refresh(self) -> None:
        """Reconstruit l'arbre en conservant les nœuds ouverts et la sélection."""
        opened = {iid for iid in self._all_items() if self.tree.item(iid, "open")}
        known = set(self._all_items())
        selected = set(self.tree.selection())
        self.tree.delete(*self.tree.get_children(""))
        workspace = self.controller.workspace
        needle = self.filter_text.get().strip().lower()
        for package in workspace.packages:
            active = package is workspace.active_package
            pid = f"package:{package.id}"
            self.tree.insert("", "end", iid=pid, image=self.icons.package, open=True,
                             text=package.name + ("  (actif)" if active else ""),
                             values=("Paquet", f"{len(package.files)} fichier(s) — {package.status().label}"),
                             tags=("active",) if active else ())
            for source in package.files:
                self._insert_file(pid, source, needle, opened, known)
        for iid in selected:
            if self.tree.exists(iid):
                self.tree.selection_add(iid)

    def _all_items(self, parent: str = ""):
        """Parcourt récursivement tous les nœuds de l'arbre."""
        for iid in self.tree.get_children(parent):
            yield iid
            yield from self._all_items(iid)

    def _insert_file(self, parent, source, needle, opened, known) -> None:
        """Ajoute un fichier et ses enfants : base de temps, groupes, diagnostic, variables."""
        fid = f"file:{source.id}"
        status = source.status()
        if source.is_loaded:
            detail = f"{status.label} — {source.table.n_samples} échantillons, {source.table.size_bytes / 1048576:.2f} Mo"
        else:
            detail = f"ILLISIBLE — {source.read_issues[0].message if source.read_issues else ''}"
        self.tree.insert(parent, "end", iid=fid, text=source.name, image=self.icons.for_severity(status),
                         values=("CSV", detail), open=(fid in opened) or (fid not in known),
                         tags=(status.label,))
        if source.is_loaded:
            analysis = source.analysis
            tstatus = source.time_status()
            self.tree.insert(fid, "end", iid=f"time:{source.id}", image=self.icons.time,
                             text=f"Base de temps : {source.table.time_name}",
                             values=(source.conversion.fmt.label.split(" ")[0],
                                     f"{tstatus.label} — T = {ms(analysis.period_used_s)} ms — "
                                     f"{analysis.n_valid} horodatages valides"),
                             tags=(tstatus.label,))
            if source.groups:
                gid = f"groups:{source.id}"
                self.tree.insert(fid, "end", iid=gid, text=f"Groupes binaires ({len(source.groups)})",
                                 values=("", ""), open=gid in opened)
                for group in source.groups.values():
                    self.tree.insert(gid, "end", iid=f"group:{source.id}:{group.name}", image=self.icons.group,
                                     text=group.name, values=(f"Groupe Bool ({len(group.members)})",
                                                              ", ".join(group.members)))
        issues = source.all_issues()
        if issues:
            did = f"diag:{source.id}"
            worst_issue = max(issue.severity for issue in issues)
            self.tree.insert(fid, "end", iid=did, text=f"Diagnostic ({len(issues)})",
                             image=self.icons.for_severity(worst_issue), values=("", "Constats de lecture"),
                             open=did in opened, tags=(worst_issue.label,))
            for position, issue in enumerate(issues):
                where = f"ligne {issue.line}" if issue.line is not None else ""
                self.tree.insert(did, "end", iid=f"issue:{source.id}:{position}", image=self.icons.issue,
                                 text=issue.message, values=(issue.severity.label, where),
                                 tags=(issue.severity.label,))
        if not source.is_loaded:
            return
        for name in source.variable_names():
            if needle and needle not in name.lower():
                continue
            signal = source.signal(name)
            icon = {SignalType.BOOL: self.icons.bool, SignalType.FLOAT: self.icons.float}.get(
                signal.type, self.icons.text)
            forced = " (forcé)" if name in source.type_overrides else ""
            notes = []
            if signal.missing.any():
                notes.append(f"{int(signal.missing.sum())} vide(s)")
            if signal.invalid.any():
                notes.append(f"{int(signal.invalid.sum())} invalide(s)")
            self.tree.insert(fid, "end", iid=f"var:{source.id}:{name}", text=name, image=icon,
                             values=(signal.type.value + forced, ", ".join(notes)))

    # ---------------------------------------------------------- interactions
    def _on_double_click(self, event) -> str:
        """Double-clic : action principale de l'élément (voir le contrôleur)."""
        iid = self.tree.identify_row(event.y)
        if iid:
            self.controller.activate_tree_item(_parse(iid))
        return "break"

    def _on_context_menu(self, event) -> None:
        """Clic droit : menu contextuel de la sélection."""
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        menu = self.controller.tree_context_menu(self, self.selection())
        if menu is not None:
            menu.tk_popup(event.x_root, event.y_root)

    def _on_press(self, event) -> None:
        """Mémorise le point de départ d'un éventuel glisser-déposer."""
        iid = self.tree.identify_row(event.y)
        self._drag = {"x": event.x, "y": event.y, "iid": iid, "active": False} if iid else None

    def _on_motion(self, event) -> None:
        """Au-delà de quelques pixels, le clic devient un glisser (variables, groupes)."""
        if self._drag and not self._drag["active"]:
            if abs(event.x - self._drag["x"]) + abs(event.y - self._drag["y"]) > DRAG_THRESHOLD_PX:
                if _parse(self._drag["iid"]).kind in ("var", "group"):
                    self._drag["active"] = True
                    self.tree.configure(cursor="hand2")

    def _on_release(self, event) -> None:
        """Relâchement : dépose les variables sur l'axe situé sous la souris."""
        drag, self._drag = self._drag, None
        if drag and drag["active"]:
            self.tree.configure(cursor="")
            refs = [ref for ref in self.selection() if ref.kind in ("var", "group")] or [_parse(drag["iid"])]
            self.controller.drop_tree_items(refs, event.x_root, event.y_root)
