"""Paquet multi-PLC (2101-2105, 5200-5203), axe absolu (4107), projet, rendu
et rapport PDF (4102-4104, 5300, 6000-6005)."""
import json
import unittest

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure

from helpers import DEMO, EXAMPLES, TempFiles, counter_csv
from ptbg.config import Settings
from ptbg.core.arrangement import TEMPLATES, CurveRef, TabState
from ptbg.core.data_package import Workspace, configure_time, load_source
from ptbg.core.diagnostic_report import file_report
from ptbg.core.diagnostics import Severity
from ptbg.core.multi_source import compare_sources
from ptbg.core.project import ReportPage, load_project, save_project
from ptbg.core.time_parser import TimeBaseSettings
from ptbg.plotting import monitor
from ptbg.plotting.renderer import TabRenderer
from ptbg.report.pdf_report import build_header, export_pdf


def texts_of(figure):
    """Tous les textes d'une figure (sous-figures et axes compris)."""
    found = []
    for artist in figure.findobj():
        if hasattr(artist, "get_text"):
            found.append(artist.get_text())
    return "\n".join(found)


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()
        self.settings = Settings()
        self.ws = Workspace()

    def tearDown(self):
        self.files.cleanup()

    def _load(self, *paths):
        for path in paths:
            self.ws.active_package.files.append(load_source(path, self.settings))
        return self.ws.files()

    def test_multi_plc_package_and_comparison(self):
        """REQ 2101 / 2103 / 2104 : chaque PLC garde son horodatage ; comparaison."""
        a, b, c = self._load(DEMO / "PLC_A_10ms_pretrig.csv", DEMO / "PLC_B_20ms_dephase.csv",
                             DEMO / "PLC_C_heure_ns.csv")
        self.assertAlmostEqual(a.analysis.period_used_s, 0.01, places=4)
        self.assertAlmostEqual(b.analysis.period_used_s, 0.02, places=6)
        issues = compare_sources([a, b], self.ws.timeline())
        self.assertIn("fréquences différentes", " ".join(issue.message for issue in issues))
        self.assertIn("passage(s) de minuit", " ".join(i.message for i in c.time_issues()))

    def test_loss_of_data_flow_between_plcs(self):
        """REQ 2104 : un PLC qui s'arrête plus tôt est signalé."""
        a = self.files.write("a.csv", counter_csv(range(0, 2000, 20), {"x": [1] * 100}))
        b = self.files.write("b.csv", counter_csv(range(0, 1000, 20), {"y": [1] * 50}))
        sa, sb = self._load(a, b)
        issues = compare_sources([sa, sb], self.ws.timeline())
        flow = next(i for i in issues if "fin de flux" in i.message)
        self.assertIn("b.csv s'arrête plus tôt", flow.message)

    def test_phase_between_synchronised_plcs(self):
        a = self.files.write("a.csv", counter_csv(range(0, 2000, 20), {"x": [1] * 100}))
        b = self.files.write("b.csv", counter_csv(range(5, 2005, 20), {"y": [1] * 100}))
        sa, sb = self._load(a, b)
        issues = compare_sources([sa, sb], self.ws.timeline())
        phase = next(i for i in issues if "déphasage" in i.message)
        self.assertIn("5 ms", phase.message)
        self.assertIs(phase.severity, Severity.WARNING)

    def test_absolute_timeline_aligns_plcs(self):
        """REQ 4107 / 2102 : horodatage absolu depuis l'origine de chaque fichier."""
        a = self.files.write("a.csv", counter_csv([0, 20, 40], {"x": [1, 2, 3]}))
        b = self.files.write("b.csv", counter_csv([0, 20, 40], {"y": [1, 2, 3]}))
        sa, sb = self._load(a, b)
        self.assertFalse(self.ws.absolute_available())
        configure_time(sa, self.settings, TimeBaseSettings(origin="2026-10-13 12:00:00"))
        configure_time(sb, self.settings, TimeBaseSettings(origin="2026-10-13 12:00:00.010"))
        self.assertTrue(self.ws.absolute_available())
        self.ws.set_time_mode("absolute")
        timeline = self.ws.timeline()
        self.assertTrue(timeline.is_absolute)
        self.assertAlmostEqual(timeline.x(sb)[0] - timeline.x(sa)[0], 0.010)
        self.assertEqual(timeline.format(timeline.x(sb)[0], 3), "2026-10-13 12:00:00.010")

    def test_manual_offset(self):
        a = self.files.write("a.csv", counter_csv([0, 20, 40], {"x": [1, 2, 3]}))
        (source,) = self._load(a)
        configure_time(source, self.settings, TimeBaseSettings(offset_s=0.5))
        self.assertAlmostEqual(self.ws.timeline().x(source)[0], 0.5)
        self.assertIn("décalage manuel", source.conversion.description)

    def test_type_override_and_report_text(self):
        """REQ 5202 : type forcé par l'utilisateur ; diagnostic complet."""
        (source,) = self._load(EXAMPLES / "simulation10_execution1.csv")
        source.set_type("failure_plc", None)
        source.set_type("source", None)
        from ptbg.core.signals import SignalType
        source.set_type("failure_plc", SignalType.BOOL)
        self.assertIs(source.signal("failure_plc").type, SignalType.BOOL)
        report = file_report(source, self.ws.timeline())
        self.assertIn("Horodatage dupliqué", report)
        self.assertIn("| 1009 | ", report)                   # ligne du CSV de l'événement
        # Lisible d'un coup d'œil : bilan en clair, puis les points à vérifier, erreurs d'abord.
        self.assertTrue(report.splitlines()[2].startswith("**Bilan : [ERREUR]"))
        points = report.split("## Points à vérifier")[1].split("## 1.")[0]
        self.assertLess(points.index("[ERREUR] Croissance continue"), points.index("[AVERTISSEMENT]"))

    def test_project_roundtrip_with_relative_paths(self):
        """REQ 3005 : chemins relatifs portables ; état des onglets conservé."""
        csv_path = self.files.write("plc.csv", counter_csv([0, 20, 40], {"x": [1, 2, 3]}))
        (source,) = self._load(csv_path)
        configure_time(source, self.settings, TimeBaseSettings(nominal_period_s=0.02, operator_note="vu"))
        tab = TabState.from_template("2A", "Onglet")
        tab.axles[0].curves.append(CurveRef(source.id, "x"))
        page = ReportPage(tab.copy(), "relative", None)
        project = self.files.path / "essai.ptbg.json"
        save_project(project, self.ws, [tab], [page], {"project_name": "NCS"})
        document = json.loads(project.read_text(encoding="utf-8"))
        self.assertEqual(document["packages"][0]["files"][0]["relative_path"], "plc.csv")
        data = load_project(project)
        self.assertEqual(data.files[0].file_id, source.id)
        self.assertEqual(data.files[0].time_settings.operator_note, "vu")
        self.assertEqual(data.tabs[0].axles[0].curves[0].name, "x")
        self.assertEqual(data.header["project_name"], "NCS")


class RenderAndReportTests(unittest.TestCase):
    def setUp(self):
        self.files = TempFiles()
        self.settings = Settings(project_name="NPI-NCS", project_unit="Tranche 1")
        self.ws = Workspace()
        for name in ("Test_PID_P_AS_scenari0045.csv", "simulation10_execution1.csv"):
            self.ws.active_package.files.append(load_source(EXAMPLES / name, self.settings))
        self.ok, self.bad = self.ws.files()
        # Colonne « index » sans unité : l'opérateur confirme les millisecondes.
        configure_time(self.ok, self.settings, TimeBaseSettings(unit="ms"))

    def tearDown(self):
        self.files.cleanup()

    def _render(self, tab, for_print=False):
        figure = Figure(figsize=(12, 8))
        FigureCanvasAgg(figure)
        renderer = TabRenderer(figure, tab, self.ws, self.ws.timeline(), 2000, for_print)
        renderer.draw()
        figure.canvas.draw()
        return figure, renderer

    def test_every_template_has_time_base_monitor(self):
        """REQ 5300 / 4102 : chaque modèle reçoit automatiquement le TBM."""
        for item in TEMPLATES:
            with self.subTest(template=item.key):
                tab = TabState.from_template(item.key, item.name)
                tab.axles[0].curves.append(CurveRef(self.ok.id, "output"))
                figure, renderer = self._render(tab)
                self.assertEqual(len(renderer.axes), len(item.slots))
                self.assertIsNotNone(renderer.tbm_plot)
                self.assertIn(monitor.TITLE, texts_of(figure))

    def test_monitor_hiding_rules(self):
        """REQ 4103 : masquage refusé en cas d'erreur, permis sinon."""
        self.assertTrue(monitor.can_hide([self.ok])[0])
        configure_time(self.ok, self.settings, TimeBaseSettings())       # unité de nouveau supposée
        allowed, reason = monitor.can_hide([self.ok])
        self.assertFalse(allowed)                                        # REQ 2307 : à confirmer
        configure_time(self.ok, self.settings, TimeBaseSettings(unit="ms"))
        allowed, reason = monitor.can_hide([self.ok, self.bad])
        self.assertFalse(allowed)
        self.assertIn(self.bad.name, reason)

    def test_report_note_when_monitor_hidden(self):
        """REQ 4104 : TBM retiré -> indication de bonne construction dans le rapport."""
        tab = TabState.from_template("1A", "Sans TBM")
        tab.axles[0].curves.append(CurveRef(self.ok.id, "output"))
        tab.tbm_visible = False
        figure, renderer = self._render(tab, for_print=True)
        self.assertIsNone(renderer.tbm_plot)
        self.assertIn("construction de la base de temps vérifiée : CONFORME", texts_of(figure))

    def test_cursor_labels_show_time_and_value(self):
        """REQ 5401 / 5403 : instants automatiques et valeur de la courbe sélectionnée."""
        tab = TabState.from_template("1A", "Curseurs")
        axle = tab.axles[0]
        axle.curves.append(CurveRef(self.ok.id, "output"))
        axle.cursor_mode, axle.t1, axle.t2 = "double", 1.0, 3.0
        text = texts_of(self._render(tab)[0])
        self.assertIn("C1  1.000000 s", text)
        self.assertIn("C2  3.000000 s", text)
        self.assertIn("Δt = 2 s", text)
        self.assertIn("output = 15", text)

    def test_axes_are_gridded_and_lane_names_stay_inside(self):
        """REQ 5104 / 2200 : axes quadrillés (grille principale et sous-graduations en
        pointillés) ; les noms des pistes logiques restent dans le cadre de l'axe quand
        on déplace la vue (ils ne débordent plus sur l'axe voisin)."""
        from matplotlib.ticker import AutoMinorLocator
        tab = TabState.from_template("AL", "Grille")
        tab.axles[0].curves.append(CurveRef(self.ok.id, "output"))
        tab.axles[1].curves.append(CurveRef(self.ok.id, "init"))
        figure, renderer = self._render(tab)
        for ax in renderer.axes:
            self.assertIsInstance(ax.xaxis.get_minor_locator(), AutoMinorLocator)
            self.assertTrue(any(tick.gridline.get_visible() for tick in ax.xaxis.get_minor_ticks()))
        lanes = [text for text in renderer.axes[1].texts if "init" in text.get_text()]
        self.assertTrue(lanes and all(text.get_clip_on() for text in lanes))

    def test_report_page_layout_like_project_test_reports(self):
        """REQ 6001 / 6005 : en-tête à chasse fixe, identification à gauche avec tous les
        champs de REQ 6005, bilan de la page à droite ; légende des courbes à droite,
        hors du graphique, comme les rapports de test du projet."""
        from ptbg.report.pdf_report import _draw_header
        tab = TabState.from_template("1A", "Rapport")
        tab.axles[0].curves.append(CurveRef(self.ok.id, "output"))
        _, renderer = self._render(tab, for_print=True)
        ax = renderer.axes[0]
        self.assertGreater(ax.get_legend().get_window_extent().x0, ax.get_window_extent().x1)
        self.assertEqual(ax.title.get_text(), "Axe 1")                       # titre centré
        page = Figure()
        FigureCanvasAgg(page)
        header = build_header(self.settings, self.ws, [ReportPage(tab, "relative", None)], None, "")
        _draw_header(page, header, ["Page 1/2", "Base de temps : OK"])
        text = texts_of(page)
        for label in ("Outil", "Émetteur", "Date", "Projet", "Unité", "Référence", "Empreinte projet",
                      "Source(s)", "NPI-NCS", "Tranche 1", self.ok.name, "Page 1/2"):
            self.assertIn(label, text)
        self.assertTrue(all(item.get_fontfamily()[0] == "DejaVu Sans Mono" for item in page.texts))

    def test_pdf_automatic_and_step_by_step(self):
        """REQ 6000, 6001, 6002, 6005 : PDF, en-tête complet, pages dans l'ordre + traçabilité."""
        tab = TabState.from_template("AL", "Vue")
        tab.axles[0].curves.append(CurveRef(self.ok.id, "output"))
        tab.axles[1].curves.append(CurveRef(self.bad.id, "published"))
        pages = [ReportPage(tab.copy(), "relative", None), ReportPage(tab.copy(), "relative", None)]
        header = build_header(self.settings, self.ws, pages, None, "")
        self.assertEqual(header.project_name, "NPI-NCS")
        self.assertEqual(header.project_unit, "Tranche 1")
        self.assertEqual({name for name, _ in header.sources}, {self.ok.name, self.bad.name})
        self.assertTrue(header.tool.startswith("VISU PTBG"))
        target = self.files.path / "rapport.pdf"
        progress = []
        export_pdf(target, pages, header, self.ws, self.settings, lambda i, n: progress.append((i, n)))
        data = target.read_bytes()
        self.assertTrue(data.startswith(b"%PDF"))
        self.assertEqual(data.count(b"/Type /Page\n") + data.count(b"/Type /Page "), 3)
        self.assertEqual(progress, [(1, 3), (2, 3)])
        self.assertFalse((self.files.path / "rapport.pdf.partiel").exists())


if __name__ == "__main__":
    unittest.main()
