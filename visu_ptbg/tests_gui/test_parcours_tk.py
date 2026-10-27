"""Parcours réels Tk/TkAgg. Exécuter avec un DISPLAY, séparément des tests rapides.

Ces tests exercent la fenêtre native Linux, pas la qualification Windows/SLES.
"""
from pathlib import Path
import sys
import tempfile
import time
import tkinter as tk
from tkinter import ttk
from unittest.mock import patch
import unittest

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET))
from MAIN import FenetreVISU
from vue_arrangements import MODELES


class ParcoursTkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.csv = Path(self.temp.name) / "PLC accentué.csv"
        self.csv.write_text("t,v,w,a,b\n0,10,3,true,0\n1,20,4,false,1\n"
                            "1,30,5,true,\n2,40,6,,0\n3,50,7,FAILED,1\n4,,8,true,0\n5,60,9,true,1\n", encoding="utf-8")
        self.racine = tk.Tk()
        self.addCleanup(self.racine.destroy)
        self.erreurs_callbacks = []
        self.racine.report_callback_exception = lambda typ, valeur, trace: self.erreurs_callbacks.append(valeur)
        for nom in ("showinfo", "showerror"):
            mock = patch("tkinter.messagebox." + nom, side_effect=lambda *a, **kw: self.fail(str(a)))
            mock.start()
            self.addCleanup(mock.stop)
        self.app = FenetreVISU(self.racine)
        self.racine.update()
        with patch("MAIN.filedialog.askopenfilenames", return_value=(str(self.csv),)):
            self.app._ajouter()
        self.attendre()
        self.assertEqual(len(self.app.paquet.sources), 1)

    def attendre(self, condition=None):
        condition = condition or (lambda: self.app.tache is None)
        limite = time.monotonic() + 20
        while not condition() and time.monotonic() < limite:
            self.racine.update()
            time.sleep(.01)
        self.racine.update()
        self.assertTrue(condition(), "Le parcours Tk n'a pas terminé sous 20 s")
        self.assertEqual(self.erreurs_callbacks, [])

    def widgets(self, parent=None):
        for enfant in (parent or self.racine).winfo_children():
            yield enfant
            yield from self.widgets(enfant)

    def bouton(self, texte, parent=None):
        return next(w for w in self.widgets(parent) if isinstance(w, ttk.Button) and w.cget("text") == texte)

    def test_5106_5300_panneaux_zoom_masquage_et_fermeture(self):
        self.app.arrangements.modele.set(MODELES[1])
        self.app.arrangements.nouveau()
        for colonne in ("v", "w"):
            self.app.signal_choisi.set(colonne)
            self.app._afficher_courbe()
            self.attendre()
        vues = self.app.arrangements.vues_actives()
        self.assertEqual(len(vues), 2)
        vues[0].axe_signal.set_xlim(0, 2)
        self.app.arrangements.lier()
        vues[0].curseurs.placer(1)
        self.assertEqual(vues[1].curseurs.positions[0][0], 1)
        self.assertEqual(vues[0].axe_signal.get_xlim(), (0, 2))
        self.app._basculer_arbre()
        self.racine.update()
        self.assertFalse(self.app.volet_arbre.winfo_ismapped())
        self.app._basculer_arbre()
        self.app.arrangements.fermer()
        self.racine.update()
        self.assertEqual(self.erreurs_callbacks, [])

    def test_2201_dialogue_groupe_lecture_et_capture_pdf(self):
        self.app._groupe_bool()
        liste = next(w for w in self.widgets() if isinstance(w, tk.Listbox))
        liste.selection_set(2, 3)  # colonnes a et b
        self.bouton("Appliquer").invoke()
        self.attendre()
        vue = self.app.arrangements.vues_actives()[0]
        self.assertTrue(vue.groupe)
        self.assertEqual([s.colonne for s in vue.signaux], ["a", "b"])
        vue.mode_curseur.set("Vertical")
        vue._choisir_curseur()
        vue.curseurs.placer(1)
        self.assertIn("a=true", vue.texte_lecture)
        self.assertIn("b=ABSENTE", vue.texte_lecture)
        vue.suivi.set(True)
        vue._choisir_suivi()
        vue.canvas.draw()
        px, py = vue.axe_signal.transData.transform((3, .5))
        widget = vue.canvas.get_tk_widget()
        widget.event_generate("<Motion>", x=int(px), y=int(widget.winfo_height() - py))
        self.racine.update()
        self.assertEqual(vue.curseurs.positions[0][0], 3)
        self.assertIn("INVALIDE : FAILED", vue.texte_lecture)
        self.app.rapports.ajouter()
        self.assertEqual(len(self.app.rapports.pages), 1)
        self.assertEqual(self.app.rapports.pages[0].captures[0].signal, "a, b")

    def test_5407_dialogue_condition_et_retrait(self):
        self.app.signal_choisi.set("v")
        self.app._afficher_courbe()
        self.attendre()
        self.app._condition_bool()
        liste = next(w for w in self.widgets() if isinstance(w, tk.Listbox))
        liste.selection_set(2)  # a
        self.bouton("Appliquer").invoke()
        self.attendre()
        vue = self.app.arrangements.vues_actives()[0]
        self.assertEqual(vue.curseurs.mode, "Horizontal")
        self.assertEqual(vue.curseurs.placer_horizontal(21), [2])
        self.assertIn("v=30", vue.texte_lecture)
        self.bouton("Retirer la condition Bool", vue).invoke()
        self.assertEqual(vue.curseurs.placer_horizontal(21), [1])

    def test_5202_type_par_colonne_et_affichage_arbre(self):
        self.app.signal_choisi.set("b")
        self.app.type_signal.set("Bool")
        self.app._memoriser_type()
        self.racine.update()
        self.app.signal_choisi.set("v")
        self.app._restaurer_type()
        self.assertEqual(self.app.type_signal.get(), "Auto")
        self.app.signal_choisi.set("b")
        self.app._restaurer_type()
        self.assertEqual(self.app.type_signal.get(), "Bool")
        textes = [self.app.arbre.item(i, "text") for i in self.app.arbre.get_children("f0")]
        self.assertIn("b (Bool choisi)", textes)

    def test_6000_export_interface_en_fond_et_fenetre_reactive(self):
        self.app.signal_choisi.set("v")
        self.app._afficher_courbe()
        self.attendre()
        sortie = Path(self.temp.name) / "rapport.pdf"
        self.app.rapports.exporter()
        dialogue = next(w for w in self.racine.winfo_children() if isinstance(w, tk.Toplevel))
        champs = [w for w in self.widgets(dialogue) if isinstance(w, ttk.Entry)]
        for champ in champs:
            champ.delete(0, "end")
            champ.insert(0, "Essai Tk")
        with patch("vue_rapports.filedialog.asksaveasfilename", return_value=str(sortie)):
            self.bouton("Enregistrer...", dialogue).invoke()
        battements = []
        self.racine.after(5, lambda: battements.append(True))
        self.attendre()
        self.assertTrue(battements)
        self.assertTrue(sortie.read_bytes().startswith(b"%PDF"))


if __name__ == "__main__":
    unittest.main()
