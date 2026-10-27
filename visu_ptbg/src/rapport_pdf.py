"""Rapports de vues figées, avec provenance et moniteur (4104, 6000-6005).

Matplotlib suffit : aucune bibliothèque PDF supplémentaire dans l'application.
Les captures PNG conservent zoom et curseurs ; le texte de l'en-tête PDF reste
sélectionnable. Le rapport n'est pas une nouvelle analyse des fichiers.
"""
from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
from pathlib import Path
from textwrap import wrap

from version_visu import VERSION_VISU


@dataclass(frozen=True)
class Capture:
    image: bytes
    fichier: str
    sha256: str
    signal: str
    lecture: str
    capturee_le: str


@dataclass(frozen=True)
class PageRapport:
    captures: tuple[Capture, ...]
    disposition: str = "Un panneau"


def capturer(vue):
    """Figer une figure dans le fil Tk ; restaurer ensuite sa présentation.

    Le moniteur est systématiquement réaffiché dans le rapport même s'il est
    masqué à l'écran. Ainsi aucun rapport ne cache une anomalie temporelle.
    Le PNG est autonome : fermer ou zoomer la vue ne modifie pas la capture.
    """
    from matplotlib.backend_bases import ResizeEvent
    figure = vue.figure
    taille = figure.get_size_inches().copy()
    visible = vue.axe_temps.get_visible()
    libelle = vue.axe_signal.get_xlabel()
    xy = getattr(vue, "type_vue", "") == "XY"
    tampon = BytesIO()
    try:
        vue.axe_temps.set_visible(True)
        vue.axe_signal.set_xlabel(libelle if xy else "")
        vue.axe_signal.tick_params(labelbottom=xy)
        # Une taille d'impression stable évite une page illisible si la fenêtre
        # était petite. Les limites X/Y et les curseurs restent inchangés.
        figure.set_size_inches(9.6, 5.4, forward=False)
        figure.canvas.callbacks.process("resize_event", ResizeEvent("resize_event", figure.canvas))
        figure.savefig(tampon, format="png", dpi=180, bbox_inches="tight")
    finally:
        vue.axe_temps.set_visible(visible)
        vue.axe_signal.set_xlabel(libelle)
        vue.axe_signal.tick_params(labelbottom=xy or not visible)
        figure.set_size_inches(taille, forward=False)
        figure.canvas.callbacks.process("resize_event", ResizeEvent("resize_event", figure.canvas))
        figure.canvas.draw_idle()
    s = vue.signal
    return Capture(tampon.getvalue(), s.fichier, s.sha256, ", ".join(s.colonne for s in getattr(vue, "signaux", [s])),
                   getattr(vue, "texte_lecture", ""), datetime.now().astimezone().isoformat(timespec="seconds"))


def generer_pdf(chemin, pages, *, emetteur, projet, unite, reference=""):
    """Créer un PDF neuf ; aucune source ni sortie existante n'est écrasée."""
    from matplotlib.backends.backend_pdf import PdfPages
    from matplotlib.figure import Figure
    from matplotlib.image import imread

    destination = Path(chemin)
    if destination.suffix.lower() != ".pdf":
        raise ValueError("Choisir un nom terminé par .pdf.")
    if not pages or any(not page.captures for page in pages):
        raise ValueError("Le rapport doit contenir au moins une vue.")
    if not all(str(v).strip() for v in (emetteur, projet, unite)):
        raise ValueError("Renseigner l'émetteur, le projet et l'unité d'installation.")
    if any(len(str(v)) > 120 or '\n' in str(v) or '\r' in str(v)
           for v in (emetteur, projet, unite, reference)):
        raise ValueError("Chaque champ d'en-tête est limité à 120 caractères sur une ligne.")
    tampon = BytesIO()
    date = datetime.now().astimezone().isoformat(timespec="seconds")
    with PdfPages(tampon, metadata={"Title": f"VISU PTBG - {projet}", "Author": emetteur,
                                   "Creator": f"VISU PTBG {VERSION_VISU}"}) as pdf:
        for numero, page in enumerate(pages, 1):
            n = len(page.captures)
            if n > 2:
                raise ValueError("Un arrangement de rapport comporte au plus deux panneaux.")
            superposes = "superposés" in page.disposition and n == 2
            taille = (11.7, 16.5) if superposes else (16.5, 8.3) if n == 2 else (11.7, 8.3)
            figure = Figure(figsize=taille)
            titre = f"VISU PTBG {VERSION_VISU} | {projet} | Unité : {unite}"
            lignes = [titre, f"Émetteur : {emetteur} | Édité le : {date}",
                      f"Référence projet : {reference or 'non fournie ; empreintes des sources ci-dessous'}"]
            for c in page.captures:
                lignes.extend([f"Source : {c.fichier} | Signal : {c.signal}",
                               f"SHA-256 source : {c.sha256} | Capture : {c.capturee_le}"])
            largeur = int(taille[0] * 12)
            texte = "\n".join("\n".join(wrap(ligne, largeur)) for ligne in lignes)
            hauteur_entete = (texte.count("\n") + 1) * 11 / (taille[1] * 72)
            if hauteur_entete > .32:
                raise ValueError("En-tête trop long pour cette page ; raccourcir les champs de projet.")
            figure.text(.04, .97, texte, va="top", fontsize=8)
            haut = .94 - hauteur_entete
            for i, c in enumerate(page.captures):
                if superposes:
                    hauteur = (haut - .07) / 2
                    rectangle = [.035, .06 + (1 - i) * hauteur, .93, hauteur - .02]
                else:
                    rectangle = [.035 + i * .93 / n, .07, .91 / n, haut - .07]
                axe = figure.add_axes(rectangle)
                axe.imshow(imread(BytesIO(c.image), format="png"))
                axe.set_axis_off()
            figure.text(.04, .025, "Temps natifs conservés ; aucune synchronisation ni interpolation. "
                        "Time Base Monitor inclus.", fontsize=8)
            figure.text(.96, .025, f"{numero}/{len(pages)}", ha="right", fontsize=8)
            pdf.savefig(figure)
            figure.clear()
    # L'exclusivité protège aussi d'un fichier créé entre le dialogue et ici.
    with destination.open("xb") as sortie:
        sortie.write(tampon.getvalue())
    return destination


def _rendre_pdf_isole(pages, valeurs):
    """Processus séparé : aucune figure ou instance Tk partagée avec l'IHM."""
    from tempfile import TemporaryDirectory
    with TemporaryDirectory() as dossier:
        fichier = generer_pdf(Path(dossier) / "rapport.pdf", pages, **valeurs)
        return fichier.read_bytes()


def exporter_pdf_en_fond(chemin, pages, annulation, publier, **valeurs):
    """REQ 4105 : rendu isolé et publication seulement si non annulé.

    La capture des figures vivantes reste sur le fil Tk ; les images figées
    sont ensuite rendues par un autre processus Matplotlib. Annuler écarte le
    résultat et ne crée pas le PDF demandé, même si le rendu a déjà commencé.
    """
    from concurrent.futures import ProcessPoolExecutor
    from multiprocessing import get_context
    destination = Path(chemin)
    if destination.suffix.lower() != ".pdf" or destination.exists():
        raise ValueError("Choisir un nouveau fichier .pdf pour préserver les fichiers existants.")
    if annulation.is_set():
        return None
    publier(("progression", "Génération PDF en arrière-plan…"))
    with ProcessPoolExecutor(max_workers=1, mp_context=get_context("spawn")) as executeur:
        contenu = executeur.submit(_rendre_pdf_isole, pages, valeurs).result()
    if annulation.is_set():
        return None
    with destination.open("xb") as sortie:
        sortie.write(contenu)
    return destination
