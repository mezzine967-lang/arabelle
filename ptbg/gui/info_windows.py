"""Section « Information » (REQ_COMMON_KH_5101) et fenêtres de texte.

- Version de l'outil ;
- Historique des modifications (CHANGELOG.md) ;
- Sources : emplacement et empreinte de chaque module du code, environnement
  Python et bibliothèques (REQ 3004), fichiers de données chargés ;
- Fichier d'aide (docs/GUIDE_UTILISATEUR.md).

Les documents Markdown sont affichés par un rendu simple dans un widget Text
(titres, listes, blocs de code, tableaux dessinés en colonnes alignées) :
aucune bibliothèque ni navigateur requis, identique sous Windows et SLES.
"""
from __future__ import annotations

import hashlib
import re
import textwrap
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, ttk
from tkinter import font as tkfont

from ptbg.gui.icons import bold_font
from ptbg.system.compat import project_root
from ptbg.system.environment import collect_environment
from ptbg.version import MIN_PYTHON, SPECIFICATION, TOOL_DATE, full_name

TABLE_WIDTH = 118        # largeur maximale d'un tableau (caractères à chasse fixe)
MIN_COLUMN = 8           # largeur minimale d'une colonne avant retour à la ligne


def _inline(text: str) -> str:
    """Texte Markdown d'une ligne rendu lisible : gras, code et liens sans balisage."""
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text).replace("`", "")
    return re.sub(r"\[(.+?)\]\((.+?)\)", r"\1 (\2)", text)


def markdown_table(lines: list[str], width: int = TABLE_WIDTH) -> list[tuple[str, bool]]:
    """Tableau Markdown (lignes « | a | b | ») dessiné en colonnes alignées.

    Renvoie les lignes à afficher et, pour chacune, si elle appartient à
    l'en-tête. Les cellules trop longues passent à la ligne dans leur colonne ;
    la ligne de séparation « |---| » est remplacée par un trait."""
    rows = []
    for line in lines:
        cells = [_inline(cell.strip().replace("\x00", "|"))
                 for cell in line.strip().replace("\\|", "\x00").strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells if cell):
            continue                                   # ligne de séparation de l'en-tête
        rows.append(cells)
    if not rows:
        return []
    count = max(len(row) for row in rows)
    rows = [row + [""] * (count - len(row)) for row in rows]
    widths = [max(max(len(row[col]) for row in rows), 1) for col in range(count)]
    budget = width - 3 * count - 1                     # bordures et marges des cellules
    while sum(widths) > budget and max(widths) > MIN_COLUMN:
        widths[widths.index(max(widths))] -= 1         # on rétrécit la colonne la plus large
    rule = "─"
    out = [("┌" + "┬".join(rule * (w + 2) for w in widths) + "┐", True)]
    for number, row in enumerate(rows):
        wrapped = [textwrap.wrap(cell, w) or [""] for cell, w in zip(row, widths)]
        for depth in range(max(len(cell) for cell in wrapped)):
            parts = [(cell[depth] if depth < len(cell) else "").ljust(w) for cell, w in zip(wrapped, widths)]
            out.append(("│ " + " │ ".join(parts) + " │", number == 0))
        joint = ("├", "┼", "┤") if number < len(rows) - 1 else ("└", "┴", "┘")
        out.append((joint[0] + joint[1].join(rule * (w + 2) for w in widths) + joint[2], number == 0))
    return out


class TextWindow(tk.Toplevel):
    """Fenêtre de lecture avec recherche, copie et enregistrement."""

    def __init__(self, parent, title: str, text: str, markdown: bool = False) -> None:
        """Barre de recherche et de copie, texte en lecture seule (Markdown ou brut)."""
        super().__init__(parent)
        self.title(title)
        self.geometry("980x680")
        bar = ttk.Frame(self, padding=4)
        bar.pack(fill="x")
        self.needle = tk.StringVar()
        ttk.Label(bar, text="Rechercher :").pack(side="left")
        search = ttk.Entry(bar, textvariable=self.needle, width=30)
        search.pack(side="left", padx=4)
        search.bind("<Return>", lambda _e: self.find_next())
        ttk.Button(bar, text="Suivant", command=self.find_next).pack(side="left")
        ttk.Button(bar, text="Enregistrer sous…", command=self.save).pack(side="right")
        ttk.Button(bar, text="Copier tout", command=self.copy).pack(side="right", padx=4)
        body = ttk.Frame(self)
        body.pack(fill="both", expand=True)
        self.text = tk.Text(body, wrap="word", padx=10, pady=8)
        scroll = ttk.Scrollbar(body, orient="vertical", command=self.text.yview)
        self.text.configure(yscrollcommand=scroll.set)
        self.text.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.fonts = (bold_font(6), bold_font(3), bold_font(1))     # conservées : sinon libérées
        self.text.tag_configure("h1", font=self.fonts[0], spacing3=6, foreground="#0d47a1")
        self.text.tag_configure("h2", font=self.fonts[1], spacing1=8, spacing3=4, foreground="#1565c0")
        self.text.tag_configure("h3", font=self.fonts[2], spacing1=6)
        self.text.tag_configure("mono", font="TkFixedFont", background="#f5f5f5")
        self.table_font = tkfont.nametofont("TkFixedFont").copy()
        self.table_bold = tkfont.nametofont("TkFixedFont").copy()
        self.table_bold.configure(weight="bold")
        self.text.tag_configure("table", font=self.table_font, wrap="none")
        self.text.tag_configure("table_head", font=self.table_bold, wrap="none")
        self.text.tag_configure("found", background="#ffeb3b")
        self._raw = text
        if markdown:
            self._render_markdown(text)
        else:
            self.text.insert("1.0", text, "mono")
        self.text.configure(state="disabled")

    def _render_markdown(self, text: str) -> None:
        """Rendu simple : titres, listes, blocs de code et tableaux en colonnes."""
        in_code, table = False, []
        for line in text.splitlines() + [""]:
            if not in_code and line.lstrip().startswith("|"):
                table.append(line)                     # tableau : rendu quand il se termine
                continue
            if table:
                for row, header in markdown_table(table):
                    self.text.insert("end", row + "\n", "table_head" if header else "table")
                table = []
            if line.strip().startswith("```"):
                in_code = not in_code
                continue
            if in_code or line.startswith("    "):
                self.text.insert("end", line + "\n", "mono")
                continue
            clean = _inline(line)
            for prefix, tag in (("### ", "h3"), ("## ", "h2"), ("# ", "h1")):
                if clean.startswith(prefix):
                    self.text.insert("end", clean[len(prefix):] + "\n", tag)
                    break
            else:
                if re.match(r"^\s*[-*] ", clean):
                    clean = re.sub(r"^(\s*)[-*] ", r"\1• ", clean)
                self.text.insert("end", clean + "\n")

    def find_next(self) -> None:
        """Surligne l'occurrence suivante du texte recherché."""
        needle = self.needle.get()
        if not needle:
            return
        start = self.text.index("found.last") if self.text.tag_ranges("found") else "1.0"
        self.text.tag_remove("found", "1.0", "end")
        position = self.text.search(needle, start, nocase=True, stopindex="end") or \
            self.text.search(needle, "1.0", nocase=True, stopindex="end")
        if position:
            end = f"{position}+{len(needle)}c"
            self.text.tag_add("found", position, end)
            self.text.see(position)

    def copy(self) -> None:
        """Copie le texte brut dans le presse-papiers."""
        self.clipboard_clear()
        self.clipboard_append(self._raw)

    def save(self) -> None:
        """Enregistre le texte brut dans un fichier choisi."""
        path = filedialog.asksaveasfilename(parent=self, defaultextension=".txt",
                                            filetypes=[("Texte", "*.txt"), ("Markdown", "*.md")])
        if path:
            Path(path).write_text(self._raw, encoding="utf-8")


def read_document(relative: str) -> str:
    """Contenu d'un document du projet (ou message clair s'il manque)."""
    path = project_root() / relative
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return f"# Document introuvable\n\n{path}"


def version_text() -> str:
    """Texte de la fenêtre « Version de l'outil »."""
    return "\n".join([
        f"# {full_name()}",
        "",
        f"- Date de version : {TOOL_DATE}",
        f"- Spécification : {SPECIFICATION}",
        "- Objet : analyseur graphique des fichiers CSV de perturbographie (PTBG), TXS Compact, NPI-NCS",
        f"- Python minimal vérifié : {MIN_PYTHON[0]}.{MIN_PYTHON[1]} (référence de développement : 3.11)",
        "- Cibles : Windows 11 64 bits (Spyder 6) et SUSE Linux Enterprise Server 15 SP7",
        f"- Emplacement des sources : {project_root()}",
        "",
        "Voir Information > Historique des modifications et Information > Sources.",
    ])


def sources_text(workspace) -> str:
    """Sources du code (empreintes), environnement et fichiers chargés."""
    root = project_root()
    lines = [f"# Sources de {full_name()}", "", f"Dossier : {root}", "", "## Code source (SHA-256 tronqué)", ""]
    for path in sorted((root / "ptbg").rglob("*.py")) + [root / "MAIN.py"]:
        if path.exists():
            data = path.read_bytes()
            count = data.count(b"\n")      # hors f-string : antislash interdit avant Python 3.12
            lines.append(f"    {str(path.relative_to(root)):<46} {count:>5} lignes  "
                         f"{hashlib.sha256(data).hexdigest()[:16]}")
    lines += ["", "## Environnement d'exécution et bibliothèques (REQ 3004)", ""]
    lines += ["    " + line for line in collect_environment().as_text().splitlines()]
    lines += ["", "Détail des dépendances, licences et impacts de montée de version : docs/DEPENDANCES.md",
              "", "## Fichiers de données chargés", ""]
    for source in workspace.files():
        lines.append(f"    {source.path}")
        lines.append(f"        SHA-256 {source.sha256 or 'illisible'} — statut {source.status().label}")
    if not workspace.files():
        lines.append("    (aucun)")
    return "\n".join(lines)
