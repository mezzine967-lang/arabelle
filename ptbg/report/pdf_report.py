"""Rapport PDF (REQ_COMMON_KH_6000 à 6005, 4104).

- REQ_COMMON_KH_6000 : l'outil génère un rapport PDF (Matplotlib ``PdfPages``,
  aucune bibliothèque supplémentaire) ;
- REQ_COMMON_KH_6001 : chaque page = modèle avec EN-TÊTE + ZONE GRAPHIQUE ;
- REQ_COMMON_KH_6002 / 6003 : rapport AUTOMATIQUE = édition unique de l'onglet
  graphique actif ;
- REQ_COMMON_KH_6002 / 6004 : rapport PAS À PAS = suite de pages capturées
  dans l'ordre choisi par l'utilisateur, chacune figeant la vue, les curseurs,
  le nuage X/Y, la condition, le commentaire... au moment de la capture ;
- REQ_COMMON_KH_6005 : en-tête = version de l'outil, émetteur, date, fichier(s)
  source, projet et unité, référence ou empreinte du projet ;
- REQ_COMMON_KH_4104 : le Time Base Monitor figure sur chaque page, ou une
  indication confirmant la bonne construction de la base de temps.

Une dernière page « Traçabilité » donne les empreintes SHA-256 complètes, le
diagnostic de base de temps de chaque fichier et l'environnement d'exécution.

Le PDF est d'abord écrit dans un fichier temporaire du même dossier puis
renommé : un export interrompu ne laisse jamais un PDF partiel.
"""
from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from matplotlib import style
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.figure import Figure
from matplotlib.lines import Line2D

from ptbg.config import Settings
from ptbg.core.data_package import Timeline, Workspace
from ptbg.core.multi_source import compare_sources
from ptbg.core.project import ReportPage
from ptbg.core.readings import HEADER as READING_HEADER, compute_readings
from ptbg.plotting.monitor import monitor_status
from ptbg.plotting.renderer import TabRenderer
from ptbg.plotting.styles import REPORT_FONT
from ptbg.system.environment import collect_environment
from ptbg.version import SPECIFICATION, full_name

PAGE_SIZE = (11.69, 8.27)       # A4 paysage, en pouces
MAX_READING_ROWS = 14           # lignes de lecture imprimées sous le graphique
CROWDED_READING_ROWS = 8        # idem quand 3 axes ou plus se partagent la hauteur (suite en annexe)


@dataclass
class ReportHeader:
    """Contenu de l'en-tête (REQ 6005)."""
    tool: str
    issuer: str
    date: str
    project_name: str
    project_unit: str
    project_reference: str              # référence libre et/ou fichier projet
    project_hash: str                   # SHA-256 du fichier projet enregistré
    sources: list[tuple[str, str]] = field(default_factory=list)   # (nom, SHA-256)


def build_header(settings: Settings, workspace: Workspace, pages: list[ReportPage],
                 project_path: Path | None, project_hash: str) -> ReportHeader:
    """En-tête : sources = fichiers présents dans les pages (sinon tous)."""
    ids = []
    for page in pages:
        ids += [fid for fid in page.tab.file_ids() if fid not in ids]
    files = [s for s in (workspace.find(fid) for fid in ids) if s is not None] or workspace.loaded_files()
    reference = settings.project_reference.strip()
    if project_path is not None:
        reference = (reference + " — " if reference else "") + f"projet {project_path.name}"
    return ReportHeader(full_name(), settings.effective_issuer(), datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        settings.project_name or "—", settings.project_unit or "—", reference or "—",
                        project_hash or "projet non enregistré",
                        [(s.name, s.sha256 or "illisible") for s in files])


def _draw_header(fig: Figure, header: ReportHeader, summary: list[str]) -> None:
    """En-tête en deux blocs de texte à chasse fixe (texte sélectionnable dans le PDF),
    sur le modèle des rapports de test du projet : identification à gauche (REQ 6005),
    bilan de la page à droite."""
    sources = [f"{name} (SHA-256 {digest[:16]}…)" for name, digest in header.sources] or ["aucune"]
    left = [("Outil", header.tool), ("Émetteur", header.issuer), ("Date", header.date),
            ("Projet", header.project_name), ("Unité", header.project_unit),
            ("Référence", header.project_reference), ("Empreinte projet", header.project_hash),
            ("Source(s)", textwrap.shorten(" ; ".join(sources), 150))]
    width = max(len(label) for label, _ in left)
    fig.text(0.03, 0.975, "\n".join(f"{label:<{width}} : {value}" for label, value in left),
             va="top", ha="left", fontsize=7, family=REPORT_FONT, linespacing=1.25)
    fig.text(0.97, 0.975, "\n".join(summary), va="top", ha="right",
             fontsize=7, family=REPORT_FONT, linespacing=1.25)
    fig.add_artist(Line2D([0.03, 0.97], [0.858, 0.858], color="#555555", lw=0.6))


def _draw_readings(fig: Figure, rows, bottom: float, height: float, limit: int) -> None:
    """Tableau des lectures de curseurs sous le graphique (``limit`` lignes, suite en annexe)."""
    ax = fig.add_axes([0.03, bottom, 0.94, height])
    ax.set_axis_off()
    shown = [row.as_tuple() for row in rows[:limit]]
    if len(rows) > limit:
        shown.append(("…", "", f"{len(rows) - limit} lecture(s) supplémentaire(s) en annexe",
                      "", "", ""))
    table = ax.table(cellText=[[textwrap.shorten(str(c), 60) for c in r] for r in shown],
                     colLabels=READING_HEADER, loc="upper center", cellLoc="left",
                     colWidths=[0.06, 0.07, 0.33, 0.2, 0.26, 0.08])
    table.auto_set_font_size(False)
    table.set_fontsize(6.5)
    table.scale(1, 0.95)


def _render_page(pdf: PdfPages, page: ReportPage, header: ReportHeader, workspace: Workspace,
                 settings: Settings, number: int, count: int) -> list:
    """Une page : en-tête, titre, zone graphique, lectures, pied de page."""
    fig = Figure(figsize=PAGE_SIZE, dpi=100)
    loaded = workspace.loaded_files()
    timeline = Timeline(page.time_mode, page.ref_ns,
                        all(s.conversion.date_known for s in loaded) if loaded else True)
    rows = compute_readings(page.tab, workspace, timeline)
    files = [s for s in (workspace.find(fid) for fid in page.tab.file_ids()) if s is not None]
    # Courbes tracées : celles des axes temporels, plus un nuage par axe X/Y renseigné.
    curves = sum(len(axle.curves) + (axle.xy_x is not None and axle.xy_y is not None) for axle in page.tab.axles)
    _draw_header(fig, header, [f"Page {number}/{count}", f"Fichiers sources : {len(files)}",
                               f"Courbes : {curves}", f"Lectures de curseurs : {len(rows)}",
                               f"Base de temps : {monitor_status(files).label if files else '—'}"])
    title = f"{page.tab.title} — capture du {page.captured_at}"
    fig.text(0.5, 0.835, title, fontsize=10, fontweight="bold", ha="center", family=REPORT_FONT)
    if page.tab.comment:
        fig.text(0.5, 0.815, textwrap.shorten(page.tab.comment, 220), fontsize=7.5, style="italic",
                 ha="center", family=REPORT_FONT)
    # Disposition chargée (3 axes ou plus) : moins de lignes sous le graphique, qui garde
    # assez de hauteur pour rester lisible ; les autres lectures vont en annexe.
    limit = CROWDED_READING_ROWS if page.tab.template.nrows >= 3 else MAX_READING_ROWS
    table_height = 0.0 if not rows else min(0.035 + 0.018 * min(len(rows), limit + 1), 0.30)
    graph_bottom = 0.04 + table_height
    # Une sous-figure n'utilise que les RATIOS de sa grille (pas top/bottom) :
    # 3 bandes = en-tête (masqué ici), zone graphique, tableau des lectures.
    bands = fig.add_gridspec(3, 1, height_ratios=[0.20, 0.80 - graph_bottom, graph_bottom])
    area = fig.add_subfigure(bands[1])
    TabRenderer(area, page.tab, workspace, timeline, settings.max_points_per_curve * 2, for_print=True,
                height_in=PAGE_SIZE[1] * (0.80 - graph_bottom)).draw()
    if rows:
        _draw_readings(fig, rows, 0.035, table_height, limit)
    fig.text(0.5, 0.012, f"{header.tool} — {SPECIFICATION}", ha="center", fontsize=6.5, color="#555555",
             family=REPORT_FONT)
    pdf.savefig(fig)
    return rows[limit:]


def _render_annex(pdf: PdfPages, header: ReportHeader, workspace: Workspace, pages: list[ReportPage],
                  extra_rows: list, number: int, count: int) -> None:
    """Page de traçabilité : empreintes, diagnostics de base de temps, environnement."""
    fig = Figure(figsize=PAGE_SIZE, dpi=100)
    lines = ["TRAÇABILITÉ DES SOURCES ET DE LA BASE DE TEMPS", ""]
    names = {name for name, _ in header.sources}
    files = [s for s in workspace.files() if s.name in names]
    _draw_header(fig, header, [f"Page {number}/{count}", "Annexe de traçabilité",
                               f"Fichiers sources : {len(files)}",
                               f"Base de temps : {monitor_status(files).label if files else '—'}"])
    for source in files:
        lines.append(f"■ {source.name} — {source.path}")
        lines.append(f"   SHA-256 : {source.sha256} ; taille : {source.table.size_bytes if source.table else 0} octets ; "
                     f"statut : {source.status().label}")
        if source.is_loaded:
            lines.append(f"   Conversion : {source.conversion.description}")
            for check in source.analysis.checks:
                lines.append(f"   {check.name} [{check.severity.label}] : {check.text}")
        for issue in source.all_issues()[:6]:
            lines.append(f"   {issue.as_text()}")
    timelines = {(p.time_mode, p.ref_ns) for p in pages}
    for mode, ref in sorted(timelines, key=str):
        for issue in compare_sources(files, Timeline(mode, ref)):
            lines.append(f"Inter-sources : {issue.as_text()}")
    for row in extra_rows:
        lines.append("Lecture : " + " | ".join(row.as_tuple()))
    environment = collect_environment()
    lines += ["", f"Environnement : Python {environment.python_version} ({environment.python_bits} bits), "
              f"{environment.os_description}, {environment.tk_version}"]
    lines.append("Bibliothèques : " + ", ".join(f"{p.name} {p.installed}" for p in environment.packages if p.installed))
    wrapped = []
    for line in lines:
        wrapped += textwrap.wrap(line, 175, subsequent_indent="      ") or [""]
    fig.text(0.03, 0.83, "\n".join(wrapped[:62]), fontsize=6.5, va="top", family="DejaVu Sans Mono")
    pdf.savefig(fig)


def export_pdf(path: Path, pages: list[ReportPage], header: ReportHeader, workspace: Workspace,
               settings: Settings, progress=None) -> None:
    """Écrit le rapport : une page par capture + annexe de traçabilité.

    ``progress(i, n)`` est appelé après chaque page (barre d'avancement).
    """
    path = Path(path)
    temporary = path.with_name(path.name + ".partiel")
    count = len(pages) + 1
    metadata = {"Title": f"Rapport {full_name()}", "Author": header.issuer,
                "Subject": f"Projet {header.project_name} — unité {header.project_unit}",
                "Keywords": "perturbographie PTBG " + " ".join(n for n, _ in header.sources),
                "Creator": full_name()}
    try:
        # Style par défaut : un réglage global (ex. savefig.bbox = "tight" dans
        # Spyder) recadrerait les pages A4.
        with style.context("default"), PdfPages(temporary, metadata=metadata) as pdf:
            extra = []
            for number, page in enumerate(pages, start=1):
                extra += _render_page(pdf, page, header, workspace, settings, number, count)
                if progress:
                    progress(number, count)
            _render_annex(pdf, header, workspace, pages, extra, count, count)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
