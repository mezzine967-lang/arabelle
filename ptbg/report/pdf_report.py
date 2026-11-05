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

Une dernière page « Identification et traçabilité » résume chaque fichier source,
les points à signaler et l'environnement d'exécution.

Mise en page (demandes du relecteur) : pages A4 en paysage ou en portrait,
choisies à chaque génération ; rapport épuré :

- chaque page porte l'en-tête complet (REQ 6005) et, en pied de page, qui a
  émis le rapport et quand ;
- page graphique : le titre de la capture, puis UNIQUEMENT la zone graphique
  (axes et Time Base Monitor) ;
- pages « Lectures » : le tableau des lectures de curseurs de la capture ;
- dernière page « Identification et traçabilité » : un tableau d'une ligne
  par fichier source (statut, période, Δt conformes, jitter max, anomalies),
  les seuls points à signaler (avertissements et erreurs) et l'environnement
  d'exécution. L'empreinte SHA-256 de chaque CSV n'y figure pas (non demandée,
  elle reste dans le diagnostic de chaque fichier, dans l'outil).

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
from ptbg.core.diagnostics import Severity
from ptbg.core.multi_source import compare_sources
from ptbg.core.project import ReportPage
from ptbg.core.readings import HEADER as READING_HEADER, compute_readings
from ptbg.core.time_base import ms
from ptbg.plotting.monitor import monitor_status
from ptbg.plotting.renderer import TabRenderer
from ptbg.plotting.styles import REPORT_FONT
from ptbg.system.environment import collect_environment
from ptbg.version import full_name

A4_IN = (11.69, 8.27)           # format A4 (grand côté, petit côté), en pouces
HEADER_IN = 1.5                 # hauteur de l'en-tête complet et du titre de page
FOOTER_IN = 0.35                # pied de page
ROW_IN = 0.17                   # hauteur d'une ligne du tableau des lectures (pouces)
READING_FONT = 6.5              # police du tableau des lectures
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
    sources = ", ".join(name for name, _ in header.sources) or "aucune"
    left = [("Outil", header.tool), ("Émetteur", header.issuer), ("Date", header.date),
            ("Projet", header.project_name), ("Unité", header.project_unit),
            ("Référence", header.project_reference), ("Empreinte projet", header.project_hash),
            ("Source(s)", f"{len(header.sources)} fichier(s) : {sources}")]
    width = max(len(label) for label, _ in left)
    chars = int(width_in * 0.7 / (7 * CHAR_IN)) - width - 3     # bloc de gauche : 70 % de la largeur
    fig.text(0.03, 1 - 0.2 / height_in,
             "\n".join(f"{label:<{width}} : {textwrap.shorten(value, max(chars, 30))}" for label, value in left),
             va="top", ha="left", fontsize=7, family=REPORT_FONT, linespacing=1.25)
    fig.text(0.97, 1 - 0.2 / height_in, "\n".join(summary), va="top", ha="right",
             fontsize=7, family=REPORT_FONT, linespacing=1.25)
    line = 1 - 1.18 / height_in
    fig.add_artist(Line2D([0.03, 0.97], [line, line], color="#555555", lw=0.6))


def _timeline(page: ReportPage, workspace: Workspace) -> Timeline:
    """Axe des temps de la capture (relatif ou absolu, date connue ou non)."""
    loaded = workspace.loaded_files()
    return Timeline(page.time_mode, page.ref_ns, all(s.conversion.date_known for s in loaded) if loaded else True)


def _rows_per_page(height_in: float) -> int:
    """Lignes de lecture qui tiennent sur une page « Lectures »."""
    return max(int((height_in - HEADER_IN - FOOTER_IN - 0.3) / ROW_IN) - 1, 5)


def _fit(text: str, chars: int) -> str:
    """Texte coupé à ``chars`` caractères (« … » en dernier) pour tenir dans sa colonne."""
    return text if len(text) <= chars else text[:max(chars - 1, 1)] + "…"


def _draw_readings(fig: Figure, rows, bottom: float, height: float, font: float) -> None:
    """Tableau des lectures de curseurs, remplissant le cadre donné (fractions de page)."""
    ax = fig.add_axes([0.03, bottom, 0.94, height])
    ax.set_axis_off()
    shown = [row.as_tuple() for row in rows]
    # Texte de chaque cellule raccourci à la largeur de sa colonne.
    table_in = fig.get_size_inches()[0] * 0.94
    chars = [max(int(share * table_in / (font * CHAR_IN)) - 1, 6) for share in TABLE_COLUMNS]
    table = ax.table(cellText=[[_fit(str(c), n) for c, n in zip(r, chars)] for r in shown],
                     colLabels=READING_HEADER, loc="upper center", cellLoc="left", colWidths=list(TABLE_COLUMNS))
    table.auto_set_font_size(False)
    table.set_fontsize(font)
    for cell in table.get_celld().values():
        cell.set_height(1.0 / (len(shown) + 1))


def _render_page(pdf: PdfPages, page: ReportPage, header: ReportHeader, workspace: Workspace,
                 settings: Settings, number: int, count: int) -> None:
    """Page graphique : en-tête, titre, puis uniquement la zone graphique."""
    width_in, height_in = page_size(settings.report_orientation)
    fig = Figure(figsize=(width_in, height_in), dpi=100)
    files = [s for s in (workspace.find(fid) for fid in page.tab.file_ids()) if s is not None]
    # Courbes tracées : celles des axes temporels, plus un nuage par axe X/Y renseigné.
    curves = sum(len(axle.curves) + (axle.xy_x is not None and axle.xy_y is not None) for axle in page.tab.axles)
    _draw_header(fig, header, [f"Page {number}/{count}", f"Fichiers sources : {len(files)}",
                               f"Courbes : {curves}",
                               f"Base de temps : {monitor_status(files).label if files else '—'}"])
    _draw_title(fig, page)
    top_in = HEADER_IN + (0.15 if page.tab.comment else 0.0)
    graph_in = height_in - top_in - FOOTER_IN
    # Une sous-figure n'utilise que les RATIOS de sa grille (pas top/bottom) :
    # 3 bandes = bandeau et titre (masqués ici), zone graphique, pied de page.
    bands = fig.add_gridspec(3, 1, height_ratios=[top_in, graph_in, FOOTER_IN], hspace=0)
    area = fig.add_subfigure(bands[1])
    TabRenderer(area, page.tab, workspace, _timeline(page, workspace), settings.max_points_per_curve * 2,
                for_print=True, height_in=graph_in).draw()
    _draw_footer(fig, header)
    pdf.savefig(fig)


def _render_readings(pdf: PdfPages, page: ReportPage, header: ReportHeader, settings: Settings,
                     rows: list, number: int, count: int) -> int:
    """Pages « Lectures » d'une capture, à la suite de sa page graphique ; renvoie le
    nombre de pages écrites."""
    width_in, height_in = page_size(settings.report_orientation)
    per_page = _rows_per_page(height_in)
    chunks = [rows[i:i + per_page] for i in range(0, len(rows), per_page)]
    for part, chunk in enumerate(chunks, 1):
        fig = Figure(figsize=(width_in, height_in), dpi=100)
        _draw_header(fig, header, [f"Page {number + part - 1}/{count}", "Lectures de curseurs",
                                   f"Lectures : {len(rows)}"])
        suite = f" (suite {part}/{len(chunks)})" if part > 1 else ""
        _draw_title(fig, page, "Lectures de curseurs — ", suite)
        table_in = (len(chunk) + 1) * ROW_IN
        top = 1 - (HEADER_IN + 0.2) / height_in
        _draw_readings(fig, chunk, top - table_in / height_in, table_in / height_in, READING_FONT)
        _draw_footer(fig, header)
        pdf.savefig(fig)
    return len(chunks)


def _draw_title(fig: Figure, page: ReportPage, prefix: str = "", suffix: str = "") -> None:
    """Titre de la capture (et son commentaire) sous l'en-tête."""
    width_in, height_in = fig.get_size_inches()
    chars = int(width_in * 0.94 / (10 * CHAR_IN))
    title = f"{prefix}{page.tab.title} — capture du {page.captured_at}{suffix}"
    fig.text(0.5, 1 - 1.36 / height_in, textwrap.shorten(title, chars), fontsize=10, fontweight="bold",
             ha="center", family=REPORT_FONT)
    if page.tab.comment:
        fig.text(0.5, 1 - 1.52 / height_in, textwrap.shorten(page.tab.comment, int(chars * 1.3)),
                 fontsize=7.5, style="italic", ha="center", family=REPORT_FONT)


def _draw_footer(fig: Figure, header: ReportHeader) -> None:
    """Pied de page : émetteur et date du rapport."""
    fig.text(0.5, 0.12 / fig.get_size_inches()[1], f"Émis par {header.issuer} le {header.date}", ha="center",
             fontsize=6.5, color="#777777", family=REPORT_FONT)


FILE_COLUMNS = (("Fichier", 0.32), ("Statut", 0.13), ("Période", 0.1), ("Δt conformes", 0.12),
                ("Jitter max", 0.1), ("Anomalies", 0.23))


def _file_row(source) -> list[str]:
    """Ligne du tableau des fichiers sources de la page de traçabilité."""
    if not source.is_loaded:
        return [source.name, source.status().label, "—", "—", "—", "fichier non lu"]
    analysis = source.analysis
    events = ", ".join(f"{count} {kind.short}" for kind, count in analysis.event_counts.items()) or "aucune"
    return [source.name, source.status().label, f"{ms(analysis.period_used_s)} ms",
            f"{analysis.normal_ratio * 100:.1f} %", f"{ms(analysis.jitter_max_s)} ms", events]


def _render_annex(pdf: PdfPages, header: ReportHeader, workspace: Workspace, settings: Settings,
                  pages: list[ReportPage], number: int, count: int) -> None:
    """Page « Identification et traçabilité » (voir l'en-tête du module)."""
    width_in, height_in = page_size(settings.report_orientation)
    fig = Figure(figsize=(width_in, height_in), dpi=100)
    names = {name for name, _ in header.sources}
    files = [s for s in workspace.files() if s.name in names]
    _draw_header(fig, header, [f"Page {number}/{count}", "Identification et traçabilité",
                               f"Base de temps : {monitor_status(files).label if files else '—'}"])
    y_in = HEADER_IN

    def heading(text: str) -> None:
        """Titre de section, puis descente sous lui."""
        nonlocal y_in
        fig.text(0.03, 1 - y_in / height_in, text, fontsize=9, fontweight="bold", va="top", family=REPORT_FONT)
        y_in += 0.3

    heading("Fichiers sources")
    if files:
        rows = [_file_row(source) for source in files]
        table_in = (len(rows) + 1) * ROW_IN
        ax = fig.add_axes([0.03, 1 - (y_in + table_in) / height_in, 0.94, table_in / height_in])
        ax.set_axis_off()
        font = 6 if width_in > 9 else 5
        table_width = width_in * 0.94
        chars = [max(int(share * table_width / (font * CHAR_IN)) - 2, 6) for _, share in FILE_COLUMNS]
        table = ax.table(cellText=[[_fit(str(c), n) for c, n in zip(row, chars)] for row in rows],
                         colLabels=[label for label, _ in FILE_COLUMNS], loc="upper center", cellLoc="left",
                         colWidths=[share for _, share in FILE_COLUMNS])
        table.auto_set_font_size(False)
        table.set_fontsize(font)
        for cell in table.get_celld().values():
            cell.set_height(1.0 / (len(rows) + 1))
        y_in += table_in + 0.35
    # Points à signaler : avertissements et erreurs seulement (les constats « OK » et
    # les informations sont dans le diagnostic de chaque fichier, dans l'outil).
    notes = []
    for source in files:
        notes += [f"{source.name} : {issue.as_text()}" for issue in source.all_issues()
                  if issue.severity >= Severity.WARNING][:6]
        if source.is_loaded:
            notes += [f"{source.name} : {check.name} [{check.severity.label}] — {check.text}"
                      for check in source.analysis.checks if check.severity >= Severity.WARNING]
            if source.time_settings.operator_note:
                notes.append(f"{source.name} : diagnostic de l'opérateur — {source.time_settings.operator_note}")
    for mode, ref in sorted({(p.time_mode, p.ref_ns) for p in pages}, key=str):
        notes += [f"Entre sources : {issue.as_text()}" for issue in compare_sources(files, Timeline(mode, ref))
                  if issue.severity >= Severity.WARNING]
    heading("Points à signaler")
    chars = int(width_in * 0.92 / (6.5 * CHAR_IN))
    wrapped = []
    for note in notes or ["Aucun avertissement ni erreur."]:
        wrapped += textwrap.wrap("• " + note, chars, subsequent_indent="  ")
    room = max(int((height_in - y_in - FOOTER_IN - 0.9) * 72 / (6.5 * 1.35)), 3)
    if len(wrapped) > room:
        wrapped = wrapped[:room - 1] + [f"… ({len(wrapped) - room + 1} ligne(s) de plus : voir le diagnostic "
                                        "de chaque fichier dans l'outil)"]
    fig.text(0.03, 1 - y_in / height_in, "\n".join(wrapped), fontsize=6.5, va="top", family=REPORT_FONT,
             linespacing=1.35)
    y_in += len(wrapped) * 6.5 * 1.35 / 72 + 0.3
    environment = collect_environment()
    heading("Environnement")
    text = (f"Python {environment.python_version} ({environment.python_bits} bits), {environment.os_description}, "
            f"{environment.tk_version} ; " + ", ".join(f"{p.name} {p.installed}" for p in environment.packages
                                                         if p.installed))
    fig.text(0.03, 1 - y_in / height_in, "\n".join(textwrap.wrap(text, chars)), fontsize=6.5, va="top",
             family=REPORT_FONT, linespacing=1.35)
    _draw_footer(fig, header)
    pdf.savefig(fig)


def export_pdf(path: Path, pages: list[ReportPage], header: ReportHeader, workspace: Workspace,
               settings: Settings, progress=None) -> None:
    """Écrit le rapport : pour chaque capture, sa page graphique puis ses pages de
    lectures ; enfin la page d'identification et de traçabilité.

    ``progress(i, n)`` est appelé après chaque capture (i = dernière page écrite).
    """
    path = Path(path)
    temporary = path.with_name(path.name + ".partiel")
    height_in = page_size(settings.report_orientation)[1]
    readings = [compute_readings(page.tab, workspace, _timeline(page, workspace)) for page in pages]
    per_page = _rows_per_page(height_in)
    count = sum(1 + -(-len(rows) // per_page) for rows in readings) + 1
    metadata = {"Title": f"Rapport {full_name()}", "Author": header.issuer,
                "Subject": f"Projet {header.project_name} — unité {header.project_unit}",
                "Keywords": "perturbographie PTBG " + " ".join(n for n, _ in header.sources),
                "Creator": full_name()}
    try:
        # Style par défaut : un réglage global (ex. savefig.bbox = "tight" dans
        # Spyder) recadrerait les pages A4.
        with style.context("default"), PdfPages(temporary, metadata=metadata) as pdf:
            number = 1
            for page, rows in zip(pages, readings):
                _render_page(pdf, page, header, workspace, settings, number, count)
                number += 1 + _render_readings(pdf, page, header, settings, rows, number + 1, count)
                if progress:
                    progress(number - 1, count)
            _render_annex(pdf, header, workspace, settings, pages, count, count)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()
