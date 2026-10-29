"""Tests de l'interface réelle (fenêtre Tk construite par MAIN.build_interface).

Requis : 5100 à 5106 (fenêtre), 5200 à 5203 (arbre), 5300, 5400 à 5408
(curseurs à la souris et au clavier), 4103 (masquage du TBM), 6002 à 6004
(rapports), 3002 (MAIN construit l'IHM). Ignorés sans écran (Linux sans
DISPLAY) : lancer sous un bureau, ou « xvfb-run python -m unittest ... ».
"""
import time
import tkinter as tk
import unittest
from pathlib import Path
from unittest import mock

from helpers import DEMO, EXAMPLES, TempFiles
from ptbg.config import Settings
from ptbg.core.data_package import configure_time
from ptbg.core.time_parser import TimeBaseSettings
from ptbg.system.activity_log import ActivityLog
from ptbg.system.compat import display_problem
from ptbg.system.environment import tkagg_problem

try:
    _root = tk.Tk()
    # Écran absent, ou Matplotlib incompatible avec ce Tcl/Tk (l'outil le refuse au démarrage).
    NO_DISPLAY = display_problem() or tkagg_problem(_root)
    _root.destroy()
except tk.TclError as exc:                      # pas d'écran ou Tk absent
    NO_DISPLAY = str(exc)


def pump(root, condition, timeout=30.0):
    """Fait tourner la boucle Tk jusqu'à ce que la condition soit vraie."""
    end = time.time() + timeout
    while time.time() < end:
        root.update()
        if condition():
            return
        time.sleep(0.01)
    raise AssertionError("délai dépassé")


class HelpViewerTests(unittest.TestCase):
    def test_markdown_tables_are_drawn_as_columns(self):
        """REQ 5101 : dans l'aide et l'historique, un tableau Markdown est dessiné en
        colonnes alignées (et non affiché en texte brut « | a | b | »)."""
        from ptbg.gui.info_windows import markdown_table
        lines = ["| Symptôme | Cause et solution |", "|---|---|",
                 "| Fichier `ILLISIBLE` | voir **Diagnostic** : " + "séparateur, encodage " * 8 + "|",
                 "| Séparateur \\| | barre échappée |"]
        rows = markdown_table(lines, width=80)
        texts = [text for text, _ in rows]
        self.assertTrue(all(len(text) == len(texts[0]) <= 80 for text in texts))   # colonnes alignées
        self.assertFalse(any("---" in text or "**" in text or "`" in text for text in texts))
        self.assertTrue(rows[1][1] and "Symptôme" in rows[1][0])                    # en-tête en gras
        self.assertGreater(sum("encodage" in text for text in texts), 1)            # cellule longue repliée
        self.assertTrue(any("Séparateur |" in text for text in texts))


@unittest.skipIf(NO_DISPLAY, f"pas d'affichage : {NO_DISPLAY}")
class InterfaceTests(unittest.TestCase):
    def setUp(self):
        import MAIN
        self.files = TempFiles()
        self.root = tk.Tk()
        self.root.geometry("1500x950+0+0")
        self.ctl = MAIN.build_interface(self.root, Settings(), ActivityLog(write_to_disk=False))
        self.root.update()

    def tearDown(self):
        self.ctl.shutdown()
        self.files.cleanup()

    def load(self, *paths):
        self.ctl._load([Path(p) for p in paths])
        pump(self.root, lambda: self.ctl.task is None)
        return self.ctl.workspace.files()

    def test_main_window_layout(self):
        """REQ 5100, 5102, 5103, 5104, 5106, 3002 : menus, arbre à gauche, graphique à droite, barre d'état."""
        menu = self.root.nametowidget(self.root["menu"])
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)]
        self.assertEqual(labels, ["Fichier", "Affichage", "Base de temps", "Outils", "Rapport", "Information"])
        panes = [str(p) for p in self.ctl.paned.panes()]
        self.assertEqual(panes, [str(self.ctl.tree), str(self.ctl.graph)])
        self.assertGreater(self.ctl.graph.winfo_width(), self.ctl.tree.winfo_width())
        self.assertEqual(len(self.ctl.graph.tabs), 1)
        status_texts = [w.cget("text") for w in self.ctl.status.winfo_children() if isinstance(w, tk.Widget)
                        and "text" in w.keys()]
        self.assertTrue(any(t.startswith("Utilisateur") for t in status_texts))
        self.assertTrue(any(t.startswith("VISU PTBG") for t in status_texts))

    def test_tree_levels_and_types(self):
        """REQ 5200, 5201, 5202, 5203 : paquet > fichiers > base de temps + variables typées."""
        a, b = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv", DEMO / "PLC_A_10ms_pretrig.csv")
        tree = self.ctl.tree.tree
        package = tree.get_children("")[0]
        self.assertEqual(len(tree.get_children(package)), 2)
        self.assertTrue(tree.exists(f"time:{a.id}"))
        self.assertEqual(tree.item(f"var:{a.id}:init", "values")[0], "Bool")
        self.assertEqual(tree.item(f"var:{a.id}:output", "values")[0], "Float")
        self.assertTrue(tree.exists(f"group:{b.id}:DI"))
        self.ctl.tree.filter_text.set("PID")
        self.assertFalse(tree.exists(f"var:{a.id}:init"))
        self.assertTrue(tree.exists(f"var:{a.id}:PID_P"))

    def test_curves_cursors_mouse_and_keyboard(self):
        """REQ 5400, 5401, 5403, 5404, 5405 : curseurs par axe, double, global, flèches clavier."""
        from matplotlib.backend_bases import KeyEvent, MouseEvent
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, "output", False), (source.id, "pv", False)], 0)
        tab.add_curves([(source.id, "init", False)], 0)                 # Bool -> axe logique
        self.assertEqual(len(tab.state.axles[1].curves), 1)
        tab.set_cursor_mode("double")
        axle = tab.axle()
        self.assertIsNotNone(axle.t1)
        self.assertIsNotNone(axle.t2)                                   # REQ 5403 : posés d'office
        self.root.update()
        ax = tab.renderer.axes[0]
        x_px, y_px = ax.transData.transform((5.0, 5.0))
        x1_px = ax.transData.transform((axle.t1, 0))[0]
        press = MouseEvent("button_press_event", tab.canvas, x1_px, y_px, button=1)
        tab.canvas.callbacks.process("button_press_event", press)
        move = MouseEvent("motion_notify_event", tab.canvas, x_px, y_px, button=1)
        tab.canvas.callbacks.process("motion_notify_event", move)
        self.root.update()
        tab.canvas.callbacks.process("button_release_event",
                                     MouseEvent("button_release_event", tab.canvas, x_px, y_px, button=1))
        self.assertAlmostEqual(axle.t1, 5.0, delta=0.1)                 # C1 glissé à 5 s
        tab.set_cursor_mode("single")
        tab.canvas.callbacks.process("key_press_event", KeyEvent("key_press_event", tab.canvas, "right"))
        cycles = axle.t1 / 0.02
        self.assertAlmostEqual(cycles, round(cycles), places=6)         # échantillon réel suivant
        rows = tab.panel.table.get_children()
        self.assertGreaterEqual(len(rows), 2)                           # REQ 5402 : toutes les courbes
        tab.global_cursor.set(True)
        tab._toggle_global()
        global_lines = [line for a in tab.renderer.axes + [tab.renderer.tbm_plot] for line in a.lines
                        if line.get_linestyle() == "--" and line.get_color() == "#2e7d32"]
        self.assertGreaterEqual(len(global_lines), 3)                   # REQ 5405 : sur tous les axes

    def test_tracking_mode(self):
        """REQ 5402 : le curseur suit la souris sans clic."""
        from matplotlib.backend_bases import MouseEvent
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, "output", False)], 0)
        tab.tracking.set(True)
        tab._toggle_tracking()
        self.root.update()
        ax = tab.renderer.axes[0]
        x_px, y_px = ax.transData.transform((12.0, 1.0))
        tab.canvas.callbacks.process("motion_notify_event",
                                     MouseEvent("motion_notify_event", tab.canvas, x_px, y_px))
        self.root.update()
        self.assertAlmostEqual(tab.axle().t1, 12.0, delta=0.1)
        # REQ 4105 : seuls les curseurs sont redessinés, sur le rendu figé du reste.
        self.assertIsNotNone(tab._background)
        ax = tab.renderer.axes[0]            # un redimensionnement a pu redessiner l'onglet
        x_px, y_px = ax.transData.transform((14.0, 1.0))
        tab.canvas.callbacks.process("motion_notify_event",
                                     MouseEvent("motion_notify_event", tab.canvas, x_px, y_px))
        self.root.update()
        self.assertAlmostEqual(tab.axle().t1, 14.0, delta=0.1)
        self.assertIn("14.", tab.panel.table.item(tab.panel.table.get_children()[0], "values")[3])

    def test_drag_and_drop_to_axle(self):
        from ptbg.gui.tree_panel import TreeRef
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        self.root.update()
        ax = tab.renderer.axes[1]
        widget = tab.canvas.get_tk_widget()
        x_px, y_px = ax.bbox.x0 + 50, ax.bbox.y0 + 10
        self.ctl.drop_tree_items([TreeRef("var", source.id, "ula")],
                                 int(widget.winfo_rootx() + x_px),
                                 int(widget.winfo_rooty() + widget.winfo_height() - y_px))
        self.assertEqual(tab.state.axles[1].curves[0].name, "ula")

    def test_monitor_hide_rules(self):
        """REQ 4103 : refus si alerte, accepté si base de temps conforme."""
        good, bad = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv", EXAMPLES / "simulation10_execution1.csv")
        configure_time(good, self.ctl.settings, TimeBaseSettings(unit="ms"))   # unité confirmée (REQ 2307)
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(good.id, "output", False)], 0)
        tab.toggle_monitor()
        self.assertFalse(tab.state.tbm_visible)
        tab.toggle_monitor()
        tab.add_curves([(bad.id, "published", False)], 1)
        with mock.patch("ptbg.gui.analysis_tab.messagebox.showwarning") as warning:
            tab.toggle_monitor()
        warning.assert_called_once()
        self.assertTrue(tab.state.tbm_visible)

    def test_unit_confirmed_for_several_files(self):
        """REQ 2307 : unité supposée = avertissement ; confirmée d'un coup pour plusieurs PLC."""
        first, second = self.load(EXAMPLES / "scenari0002.csv", EXAMPLES / "scenari0045.csv")
        self.assertTrue(first.conversion.unit_assumed and second.conversion.unit_assumed)
        self.assertEqual(first.time_status().label, "AVERTISSEMENT")
        answer = mock.Mock(result=TimeBaseSettings(unit="ms"), share_unit=True)
        with mock.patch("ptbg.gui.app.TimeBaseDialog", return_value=answer):
            self.ctl.configure_time_base(first)
        pump(self.root, lambda: self.ctl.task is None)
        for source in (first, second):
            self.assertFalse(source.conversion.unit_assumed)
            self.assertEqual(source.time_settings.unit, "ms")

    def test_horizontal_cursor_only_on_float(self):
        """REQ 5406 : refusé sur un axe logique."""
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, "init", False)], 1)
        with mock.patch("ptbg.gui.app.messagebox.showwarning") as warning:
            self.ctl.horizontal_cursor()
        warning.assert_called_once()
        tab.add_curves([(source.id, "output", False)], 0)
        self.assertTrue(tab.float_curve_selected())

    def test_reset_view_returns_to_full_duration(self):
        """REQ 5106 / 5405 : après un zoom et un déplacement vertical, « Vue d'origine »
        réaffiche toute la durée avec les échelles automatiques ; les courbes restent."""
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, "output", False)], 0)
        self.root.update()
        full = tab.renderer.axes_time_master().get_xlim()
        tab.renderer.axes_time_master().set_xlim(5.0, 6.0)          # zoom mémorisé dans l'onglet
        tab.state.axles[0].ylim = [1000.0, 2000.0]                   # vue déplacée verticalement
        tab.redraw()
        self.assertEqual(tuple(tab.renderer.axes_time_master().get_xlim()), (5.0, 6.0))
        self.ctl.reset_view()
        self.root.update()
        self.assertEqual(tuple(tab.renderer.axes_time_master().get_xlim()), tuple(full))
        self.assertIsNone(tab.state.axles[0].ylim)
        self.assertEqual(len(tab.state.axles[0].curves), 1)

    def test_diagnostic_window_is_readable(self):
        """REQ 4101 / 2300 : la fenêtre Diagnostic se lit sans balisage : gravités en
        couleur, sous-points en retrait, tableaux en colonnes à chasse fixe."""
        from ptbg.gui.info_windows import TextWindow
        (source,) = self.load(EXAMPLES / "simulation10_execution1.csv")
        self.ctl.show_diagnostic(source)
        window = [w for w in self.root.winfo_children() if isinstance(w, TextWindow)][-1]
        text = window.text
        content = text.get("1.0", "end")
        self.assertNotIn("**", content)
        self.assertNotIn("|---", content)
        self.assertIn("┌", content)
        for tag_name in ("sev_ERREUR", "sev_AVERTISSEMENT", "sev_OK", "fg_ERREUR", "li1", "strong"):
            self.assertTrue(text.tag_ranges(tag_name), tag_name)
        start = text.tag_ranges("fg_ERREUR")[0]
        self.assertIn("table", text.tag_names(start))         # couleur sans changer la police du tableau
        window.destroy()

    def test_legend_can_be_moved_hidden_and_picks_curves(self):
        """REQ 5106 / 6001 : la légende se glisse à la souris et garde sa place (redessin,
        projet, rapport) ; un clic sur un nom sélectionne la courbe ; elle se masque
        par le menu de l'axe ; « Vue d'origine » la remet à sa place automatique."""
        from matplotlib.backend_bases import MouseEvent
        from ptbg.core.arrangement import TabState
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, name, False) for name in source.float_names()[:2]], 0)
        self.root.update()
        tab.canvas.draw()
        axle = tab.state.axles[0]

        def mouse(kind, x, y):
            """Événement souris envoyé à la figure comme par Tk."""
            tab.canvas.callbacks.process(kind, MouseEvent(kind, tab.canvas, x, y, button=1))

        box = tab.renderer.axes[0].get_legend().get_window_extent()
        x0, y0 = (box.x0 + box.x1) / 2, (box.y0 + box.y1) / 2
        mouse("button_press_event", x0, y0)
        mouse("motion_notify_event", x0 - 120, y0 - 70)
        mouse("button_release_event", x0 - 120, y0 - 70)
        self.assertEqual(axle.legend, "free")
        self.assertIsNone(axle.t1, "le clic sur la légende ne doit pas poser de curseur")
        tab.redraw()
        tab.canvas.draw()
        moved = tab.renderer.axes[0].get_legend().get_window_extent()
        self.assertAlmostEqual(moved.x0, box.x0 - 120, delta=3)
        self.assertAlmostEqual(moved.y0, box.y0 - 70, delta=3)
        self.assertEqual(TabState.from_dict(tab.state.to_dict()).axles[0].legend_xy, axle.legend_xy)
        # Clic simple sur le 2e nom : la 2e courbe devient la courbe sélectionnée.
        name = tab.renderer.axes[0].get_legend().get_texts()[1].get_window_extent()
        x1, y1 = (name.x0 + name.x1) / 2, (name.y0 + name.y1) / 2
        mouse("button_press_event", x1, y1)
        mouse("button_release_event", x1, y1)
        self.assertEqual(axle.selected, 1)
        self.assertEqual(axle.legend_xy, TabState.from_dict(tab.state.to_dict()).axles[0].legend_xy)
        menu = self.ctl.axle_context_menu(tab, 0)
        labels = [menu.entrycget(i, "label") for i in range(menu.index("end") + 1)
                  if menu.type(i) == "command"]
        self.assertIn("Masquer la légende", labels)
        self.assertIn("Légende à sa place automatique", labels)
        tab.set_legend(0, "hidden")
        self.assertIsNone(tab.renderer.axes[0].get_legend())
        tab.set_legend(0, "auto")
        mouse("button_press_event", x0, y0)       # replacée puis déplacée à nouveau
        tab.state.axles[0].legend, tab.state.axles[0].legend_xy = "free", [0.1, 0.1]
        self.ctl.reset_view()
        self.assertEqual((axle.legend, axle.legend_xy), ("auto", None))
        self.assertIsNotNone(tab.renderer.axes[0].get_legend())

    def test_tabs_close_with_their_cross(self):
        """REQ 5106 : chaque onglet se ferme par la croix de son titre (ou clic molette,
        clic droit, Ctrl+W) ; il reste toujours au moins un onglet."""
        from types import SimpleNamespace
        graph = self.ctl.graph
        first = graph.tabs[0]
        self.ctl.new_tab("2A")
        self.root.update()
        notebook = graph.notebook
        crosses = [(x, y) for y in range(2, 34, 2) for x in range(0, notebook.winfo_width(), 2)
                   if "close" in notebook.identify(x, y) and notebook.index(f"@{x},{y}") == 1]
        self.assertTrue(crosses, "croix de fermeture absente du 2e onglet")
        event = SimpleNamespace(x=crosses[0][0], y=crosses[0][1])
        graph._on_press(event)
        graph._on_release(event)
        self.assertEqual(graph.tabs, [first])
        self.ctl.close_tab(first)
        self.assertEqual(len(graph.tabs), 1)                  # un onglet vide est recréé
        self.assertIsNot(graph.tabs[0], first)

    def test_xy_tab_and_point_pick(self):
        """REQ 5408 : nuage X/Y et désignation d'un point."""
        from matplotlib.backend_bases import MouseEvent
        from ptbg.core.arrangement import CurveRef
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.new_tab("XY")
        axle = tab.state.axles[2]
        axle.xy_x, axle.xy_y = CurveRef(source.id, "pv"), CurveRef(source.id, "output")
        tab.redraw()
        self.root.update()
        ax = tab.renderer.axes[2]
        x_px, y_px = ax.transData.transform((5.0, 10.0))
        tab.canvas.callbacks.process("button_press_event",
                                     MouseEvent("button_press_event", tab.canvas, x_px, y_px, button=1))
        self.assertIsNotNone(axle.xy_t)

    def test_reports_and_project(self):
        """REQ 6003 / 6004 et projet : rapport auto, pas à pas, enregistrement, réouverture."""
        (source,) = self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        tab = self.ctl.graph.active_tab()
        tab.add_curves([(source.id, "output", False)], 0)
        auto_pdf = self.files.path / "auto.pdf"
        with mock.patch("ptbg.gui.app.filedialog.asksaveasfilename", return_value=str(auto_pdf)), \
                mock.patch("ptbg.gui.app.messagebox.askyesno", return_value=False):
            self.ctl.automatic_report()
        self.assertTrue(auto_pdf.read_bytes().startswith(b"%PDF"))
        with mock.patch("ptbg.gui.app.simpledialog.askstring", return_value="Vue 1"):
            self.ctl.add_report_page()
            tab.set_cursor_mode("single")
            self.ctl.add_report_page()
        self.assertEqual([p.tab.comment for p in self.ctl.report_pages], ["Vue 1", "Vue 1"])
        self.assertEqual(self.ctl.report_pages[0].tab.axles[0].cursor_mode, "none")   # capture figée
        project = self.files.path / "essai.ptbg.json"
        with mock.patch("ptbg.gui.app.filedialog.asksaveasfilename", return_value=str(project)):
            self.ctl.save_project()
        self.assertEqual(len(self.ctl.project_hash), 64)
        with mock.patch("ptbg.gui.app.filedialog.askopenfilename", return_value=str(project)), \
                mock.patch("ptbg.gui.app.messagebox.askyesno", return_value=True):
            self.ctl.open_project()
            pump(self.root, lambda: self.ctl.task is None and self.ctl.graph.tabs)
        self.assertEqual(len(self.ctl.report_pages), 2)
        self.assertEqual(self.ctl.graph.tabs[0].state.axles[0].curves[0].name, "output")

    def test_information_windows_and_tree_toggle(self):
        """REQ 5105 (arbre masquable) ; REQ 5101 (version, historique, sources, aide)."""
        for action in (self.ctl.show_version, self.ctl.show_history, self.ctl.show_sources,
                       self.ctl.show_help, self.ctl.show_log, self.ctl.show_traceability):
            action()
        windows = [w for w in self.root.winfo_children() if isinstance(w, tk.Toplevel)]
        self.assertEqual(len(windows), 6)
        self.ctl.toggle_tree()
        self.assertEqual([str(p) for p in self.ctl.paned.panes()], [str(self.ctl.graph)])
        self.ctl.toggle_tree()
        self.assertEqual(len(self.ctl.paned.panes()), 2)

    def test_absolute_time_mode(self):
        """REQ 4107 : axe absolu refusé sans origine, accepté pour l'horodatage hh:mm:ss."""
        self.load(EXAMPLES / "Test_PID_P_AS_scenari0045.csv")
        with mock.patch("ptbg.gui.app.messagebox.showwarning") as warning:
            self.ctl.set_time_mode("absolute")
        warning.assert_called_once()
        self.ctl.workspace.remove_file(self.ctl.workspace.files()[0])
        self.load(DEMO / "PLC_C_heure_ns.csv")
        self.ctl.set_time_mode("absolute")
        self.assertTrue(self.ctl.workspace.timeline().is_absolute)


if __name__ == "__main__":
    unittest.main()
