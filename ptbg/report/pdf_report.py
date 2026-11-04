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

Mise en page (remarques du relecteur) : pages A4 en paysage ou en portrait
(Rapport > Pages en paysage / portrait) ; chaque onglet tient sur SA page,
graphique et tableau des lectures compris : le tableau prend la place qu'il
lui faut (jusqu'à ``TABLE_SHARE`` de la hauteur, police réduite si besoin).
Seul un nombre de lectures qui ne tiendrait pas même ainsi renvoie la suite
en annexe, ce qui est signalé sur la page.

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

A4_IN = (11.69, 8.27)           # format A4 (grand côté, petit côté), en pouces
HEADER_IN = 1.5                 # hauteur de l'en-tête et du titre de page
FOOTER_IN = 0.35                # pied de page
TABLE_SHARE = 0.34              # part maximale de la hauteur laissée au tableau des lectures
CHAR_IN = 0.6 / 72              # largeur d'un caractère à chasse fixe, par point de police (pouces)
TABLE_COLUMNS = (0.06, 0.07, 0.33, 0.2, 0.26, 0.08)   # largeur des colonnes des lectures (fraction)


def page_size(orientation: str) -> tuple[float, float]:
    """(largeur, hauteur) en pouces d'une page A4 « landscape » ou « portrait »."""
    return A4_IN if orientation != "portrait" else (A4_IN[1], A4_IN[0])


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
    bilan de la page à droite ; les lignes longues sont raccourcies à la largeur de la page."""
    width_in, height_in = fig.get_size_inches()
    sources = [f"{name} (SHA-256 {digest[:16]}…)" for name, digest in header.sources] or ["aucune"]
    left = [("Outil", header.tool), ("Émetteur", header.issuer), ("Date", header.date),
            ("Projet", header.project_name), ("Unité", header.project_unit),
            ("Référence", header.project_reference), ("Empreinte projet", header.project_hash),
            ("Source(s)", " ; ".join(sources))]
    width = max(len(label) for label, _ in left)
    chars = int(width_in * 0.7 / (7 * CHAR_IN)) - width - 3     # bloc de gauche : 70 % de la largeur
    fig.text(0.03, 1 - 0.2 / height_in,
             "\n".join(f"{label:<{width}} : {textwrap.shorten(value, max(chars, 30))}" for label, value in left),
             va="top", ha="left", fontsize=7, family=REPORT_FONT, linespacing=1.25)
    fig.text(0.97, 1 - 0.2 / height_in, "\n".join(summary), va="top", ha="right",
             fontsize=7, family=REPORT_FONT, linespacing=1.25)
    line = 1 - 1.18 / height_in
    fig.add_artist(Line2D([0.03, 0.97], [line, line], color="#555555", lw=0.6))


def _reading_layout(count: int, height_in: float) -> tuple[int, float, float]:
    """(lignes imprimées, taille de police, hauteur d'une ligne en pouces) pour ``count``
    lectures : police normale si elles tiennent dans ``TABLE_SHARE`` de la page, sinon
    réduite, sinon le maximum de lignes à la police réduite (suite en annexe)."""
    room = TABLE_SHARE * height_in - 0.1
    for font, row_in in ((6.5, 0.15), (5.5, 0.125)):
        if (count + 1) * row_in <= room:
            return count, font, row_in
    return max(int(room / 0.125) - 2, 4), 5.5, 0.125


def _draw_readings(fig: Figure, rows, bottom: float, height: float, limit: int, font: float) -> None:
    """Tableau des lectures de curseurs sous le graphique (``limit`` lignes, suite en annexe)."""
    ax = fig.add_axes([0.03, bottom, 0.94, height])
    ax.set_axis_off()
    shown = [row.as_tuple() for row in rows[:limit]]
    if len(rows) > limit:
        shown.append(("…", "", f"{len(rows) - limit} lecture(s) supplémentaire(s) en annexe",
                      "", "", ""))
    # Texte de chaque cellule raccourci à la largeur de sa colonne.
    table_in = fig.get_size_inches()[0] * 0.94
    chars = [max(int(share * table_in / (font * CHAR_IN)) - 1, 6) for share in TABLE_COLUMNS]
    table = ax.table(cellText=[[textwrap.shorten(str(c), n) for c, n in zip(r, chars)] for r in shown],
                     colLabels=READING_HEADER, loc="upper center", cellLoc="left", colWidths=list(TABLE_COLUMNS))
    table.auto_set_font_size(False)
    table.set_fontsize(font)
    for cell in table.get_celld().values():
        cell.set_height(1.0 / (len(shown) + 1))


def _render_page(pdf: PdfPages, page: ReportPage, header: ReportHeader, workspace: Workspace,
                 settings: Settings, number: int, count: int) -> list:
    """Une page : en-tête, titre, zone graphique, lectures, pied de page ; tout l'onglet
    tient sur la page (voir l'en-tête du module)."""
    width_in, height_in = page_size(settings.report_orientation)
    fig = Figure(figsize=(width_in, height_in), dpi=100)
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
    title_chars = int(width_in * 0.94 / (10 * CHAR_IN))
    fig.text(0.5, 1 - 1.36 / height_in, textwrap.shorten(title, title_chars), fontsize=10, fontweight="bold",
             ha="center", family=REPORT_FONT)
    if page.tab.comment:
        fig.text(0.5, 1 - 1.52 / height_in, textwrap.shorten(page.tab.comment, int(title_chars * 1.3)),
                 fontsize=7.5, style="italic", ha="center", family=REPORT_FONT)
    limit, font, row_in = _reading_layout(len(rows), height_in)
    table_in = 0.0 if not rows else (min(len(rows), limit + 1) + 1) * row_in + 0.1
    top_in = HEADER_IN + (0.15 if page.tab.comment else 0.0)
    graph_in = height_in - top_in - FOOTER_IN - table_in
    # Une sous-figure n'utilise que les RATIOS de sa grille (pas top/bottom) :
    # 3 bandes = en-tête (masqué ici), zone graphique, tableau des lectures et pied de page.
    bands = fig.add_gridspec(3, 1, height_ratios=[top_in, graph_in, FOOTER_IN + table_in], hspace=0)
    area = fig.add_subfigure(bands[1])
    TabRenderer(area, page.tab, workspace, timeline, settings.max_points_per_curve * 2, for_print=True,
                height_in=graph_in).draw()
    if rows:
        _draw_readings(fig, rows, (FOOTER_IN - 0.05) / height_in, table_in / height_in, limit, font)
    fig.text(0.5, 0.1 / height_in, f"{header.tool} — {SPECIFICATION}", ha="center", fontsize=6.5,
             color="#555555", family=REPORT_FONT)
    pdf.savefig(fig)
    return rows[limit:]


def _render_annex(pdf: PdfPages, header: ReportHeader, workspace: Workspace, settings: Settings,
                  pages: list[ReportPage], extra_rows: list, number: int, count: int) -> None:
    """Page de traçabilité : empreintes, diagnostics de base de temps, environnement."""
    width_in, height_in = page_size(settings.report_orientation)
    fig = Figure(figsize=(width_in, height_in), dpi=100)
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
        wrapped += textwrap.wrap(line, int(width_in * 0.94 / (6.5 * CHAR_IN)), subsequent_indent="      ") or [""]
    room = int((height_in - HEADER_IN - FOOTER_IN) * 72 / (6.5 * 1.2))       # lignes qui tiennent
    fig.text(0.03, 1 - (HEADER_IN - 0.1) / height_in, "\n".join(wrapped[:room]), fontsize=6.5, va="top",
             family="DejaVu Sans Mono")
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
            _render_annex(pdf, header, workspace, settings, pages, extra, count, count)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
