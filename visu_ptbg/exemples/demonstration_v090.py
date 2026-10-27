"""Créer un rapport de démonstration, sans Tk et sans modifier les CSV.

Lancer depuis la racine : python exemples/demonstration_v090.py sortie.pdf
Le PDF doit être neuf. Les deux premières pages emploient la simulation de
perte fournie dans exemples/ ; la troisième emploie deux signaux de simulation.
"""
import sys
from pathlib import Path
from types import SimpleNamespace

PROJET = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJET / "src"))
from base_temps import SourceTemps, examiner_source
from signal_csv import preparer_signal
from moniteur_temps import construire_moniteur
from trace_signal import creer_figure
from curseurs import Curseurs
from rapport_pdf import capturer, generer_pdf, PageRapport
from vue_xy import figure_xy
from matplotlib.backends.backend_agg import FigureCanvasAgg


def main(destination):
    source = SourceTemps(PROJET / "exemples/exemple_synthetique_croix.csv", unite="ms",
                         pas_attendu="10", tolerance="0")
    resultat = examiner_source(source)
    s = preparer_signal(source, resultat, "signal")
    modele = construire_moniteur(source, resultat)
    fig, axe, temps = creer_figure(s, modele)
    FigureCanvasAgg(fig)
    vue = SimpleNamespace(figure=fig, axe_signal=axe, axe_temps=temps, signal=s)
    curseurs = Curseurs(fig, axe, temps, s, lambda x: None)
    curseurs.choisir("Double vertical")
    curseurs.placer(540,0)
    curseurs.placer(770,1)
    complet = capturer(vue)
    axe.set_xlim(450,850)
    zoom = capturer(vue)
    source_xy = SourceTemps(PROJET / "donnees/simulation10_execution1.csv", unite="ms",
                            pas_attendu="1", tolerance="0")
    r = examiner_source(source_xy)
    x = preparer_signal(source_xy,r,"source")
    y = preparer_signal(source_xy,r,"pub_output")
    f, a, t, _, _ = figure_xy(x,y,construire_moniteur(source_xy,r))
    FigureCanvasAgg(f)
    xy = capturer(SimpleNamespace(figure=f, axe_signal=a, axe_temps=t, signal=x,
                                  signaux=[x,y], type_vue="XY"))
    return generer_pdf(destination, [PageRapport((complet,)),
                      PageRapport((complet,zoom), "Deux panneaux côte à côte"), PageRapport((xy,))],
                      emetteur="Démonstration logicielle", projet="VISU PTBG - données de simulation",
                      unite="Essais hors installation", reference="v0.9.0 - aucune validation métier")


if __name__ == "__main__":
    print(main(Path(sys.argv[1])))
