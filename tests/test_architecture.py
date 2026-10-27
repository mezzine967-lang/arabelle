"""Contraintes d'architecture vérifiées automatiquement (section « Architecture »).

- REQ_COMMON_KH_3002 : MAIN.py ne fait que construire l'interface ;
- REQ_COMMON_KH_3003 : les traitements sont dans des modules dédiés, sans IHM ;
- REQ_COMMON_KH_3004 : toute bibliothèque importée est documentée et figée ;
- REQ_COMMON_KH_3005 : les particularités d'OS sont centralisées et documentées ;
- REQ_COMMON_KH_3006 : le code source est commenté ;
- REQ_COMMON_KH_3007 : aucune fonction inutile ;
- REQ_COMMON_KH_3000 / 3001 : syntaxe compatible avec la version minimale de Python ;
- REQ_COMMON_KH_5300 : modèles de disposition cohérents ;
- traçabilité : chaque requis du Word est cité dans la matrice, le code et les tests.
"""
import ast
import io
import sys
import tokenize
import unittest

from helpers import ROOT
from ptbg.core.arrangement import TEMPLATES
from ptbg.version import MIN_PYTHON

PRODUCTION = sorted((ROOT / "ptbg").rglob("*.py")) + [ROOT / "MAIN.py"]
TOOLS = sorted((ROOT / "tools").glob("*.py"))


def tree_of(path):
    return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))


def imported_modules(path) -> set[str]:
    modules = set()
    for node in ast.walk(tree_of(path)):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
    return modules


class ArchitectureTests(unittest.TestCase):
    def test_main_only_builds_the_gui(self):
        """REQ_COMMON_KH_3002."""
        modules = imported_modules(ROOT / "MAIN.py")
        forbidden = {m for m in modules if m.startswith(("ptbg.core", "ptbg.report", "ptbg.plotting",
                                                         "numpy", "matplotlib"))}
        self.assertEqual(forbidden, set(), "MAIN.py ne doit pas traiter de données")
        functions = {n.name for n in ast.walk(tree_of(ROOT / "MAIN.py")) if isinstance(n, ast.FunctionDef)}
        self.assertEqual(functions, {"_environment_problem", "build_interface", "main"})

    def test_processing_is_externalized_and_gui_free(self):
        """REQ_COMMON_KH_3003 : core sans Tk ni Matplotlib ; dessin et rapport sans Tk."""
        for path in PRODUCTION:
            modules = imported_modules(path)
            relative = path.relative_to(ROOT).as_posix()
            if relative.startswith("ptbg/core/"):
                self.assertFalse({m for m in modules if m.split(".")[0] in ("tkinter", "matplotlib")}, relative)
            if relative.startswith(("ptbg/plotting/", "ptbg/report/")):
                self.assertNotIn("tkinter", {m.split(".")[0] for m in modules}, relative)

    def test_third_party_libraries_are_documented_and_pinned(self):
        """REQ_COMMON_KH_3004 : bibliothèques tierces figées et documentées, stdlib listée."""
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
        documentation = (ROOT / "docs" / "DEPENDANCES.md").read_text(encoding="utf-8")
        stdlib = getattr(sys, "stdlib_module_names", set())
        for path in PRODUCTION:
            for module in imported_modules(path):
                top = module.split(".")[0]
                if top in ("ptbg", "__future__"):
                    continue
                if top in stdlib:
                    self.assertIn(f"`{top}`", documentation, f"module standard {top} non documenté")
                else:
                    self.assertIn(f"{top}==", requirements, f"{top} non figé dans requirements.txt")
                    self.assertIn(top, documentation)

    def test_os_specific_code_is_centralized(self):
        """REQ_COMMON_KH_3005 : seuls system/compat.py et environment.py testent l'OS."""
        allowed = {"ptbg/system/compat.py", "ptbg/system/environment.py"}
        for path in PRODUCTION:
            text = path.read_text(encoding="utf-8")
            relative = path.relative_to(ROOT).as_posix()
            if relative not in allowed:
                for marker in ("sys.platform", "os.name", "startfile", "platform.system"):
                    self.assertNotIn(marker, text, f"{marker} hors de system/ dans {relative}")
        self.assertTrue((ROOT / "docs" / "COMPATIBILITE_OS.md").exists())

    def test_sources_are_commented(self):
        """REQ_COMMON_KH_3006 : docstring par module et par fonction/classe publique non triviale."""
        missing = []
        comment_lines = code_lines = 0
        for path in PRODUCTION + TOOLS:
            text = path.read_text(encoding="utf-8")
            tree = tree_of(path)
            if not ast.get_docstring(tree):
                missing.append(f"{path.name} (module)")
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and not node.name.startswith("_"):
                    if node.end_lineno - node.lineno > 8 and not ast.get_docstring(node):
                        missing.append(f"{path.name}:{node.lineno} {node.name}")
            tokens = tokenize.generate_tokens(io.StringIO(text).readline)
            comment_lines += sum(1 for token in tokens if token.type == tokenize.COMMENT)
            code_lines += sum(1 for line in text.splitlines() if line.strip())
            comment_lines += sum(len((ast.get_docstring(n) or "").splitlines()) for n in ast.walk(tree)
                                 if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)))
        self.assertEqual(missing, [])
        self.assertGreater(comment_lines / code_lines, 0.20, "densité de commentaires insuffisante")

    def test_no_unused_functions(self):
        """REQ_COMMON_KH_3007 : toute fonction définie est appelée quelque part."""
        hooks = {"body", "validate", "apply", "main"}       # appelées par Tkinter / le point d'entrée
        defined, used = {}, set()
        for path in PRODUCTION + TOOLS:
            for node in ast.walk(tree_of(path)):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    defined.setdefault(node.name, path.name)
                elif isinstance(node, ast.Name):
                    used.add(node.id)
                elif isinstance(node, ast.Attribute):
                    used.add(node.attr)
        unused = {name: where for name, where in defined.items()
                  if name not in used and name not in hooks and not name.startswith("__")}
        self.assertEqual(unused, {})

    def test_minimal_python_syntax(self):
        """REQ_COMMON_KH_3000 / 3001 : le code se compile avec la grammaire de la version minimale."""
        for path in PRODUCTION + TOOLS:
            ast.parse(path.read_text(encoding="utf-8"), feature_version=MIN_PYTHON)

    def test_templates_fit_their_grid(self):
        """REQ_COMMON_KH_5300 : plusieurs modèles, axes dans la grille, au moins un axe temporel."""
        self.assertGreaterEqual(len(TEMPLATES), 5)
        for item in TEMPLATES:
            self.assertEqual(len(item.row_ratios), item.nrows)
            self.assertEqual(len(item.col_ratios), item.ncols)
            self.assertTrue(any(slot.kind == "time" for slot in item.slots))
            for slot in item.slots:
                self.assertLessEqual(slot.row + slot.rowspan, item.nrows)
                self.assertLessEqual(slot.col + slot.colspan, item.ncols)

    def test_every_requirement_is_traced(self):
        """Aucun requis du Word laissé de côté : matrice + code + test."""
        sys.path.insert(0, str(ROOT / "tools"))
        import verifier_tracabilite
        self.assertEqual(len(verifier_tracabilite.spec_requirements()), 63)
        self.assertEqual(verifier_tracabilite.check(), [])


if __name__ == "__main__":
    unittest.main()
