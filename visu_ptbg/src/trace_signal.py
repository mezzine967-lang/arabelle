# -----------------------------------------------------------------------------
# VISU PTBG — V00.07.03 — croix sur les bords des données manquantes
# Requis concernés : 4101, 4102, 4103, 3003, 3006 ; couverture partielle.
# Historique : séparation lecture, dessin et intégration dans la fenêtre.
# -----------------------------------------------------------------------------
"""Figure Matplotlib : un signal et son Time Base Monitor sur le même axe X.

Import de Matplotlib différé jusqu'au tracé. L'API Figure est utilisée sans
pyplot et sans changement du backend global de Spyder. Ce module construit
une figure aussi testable avec Agg, sans fenêtre ni serveur d'affichage.
"""
from __future__ import annotations

from pathlib import Path
from collections import Counter
from textwrap import fill
from typing import Any

from diagnostic_csv import _temps_decimal as _decimal
from signal_csv import SignalPrepare, _flottant
from _signal_draw import sample_chart


def resumer_moniteur(signal: SignalPrepare) -> str:
    """Mettre en mots les résultats préparés, sans reclasser les intervalles.

    Les nombres portent sur les intervalles affichables du fichier entier,
    même après un zoom. Une séquence de trois intervalles à fréquence modifiée
    compte donc trois intervalles, pas trois changements indépendants.
    """
    unite = signal.unite_temps or "unité inconnue"
    if signal.raster_temps is None:
        profil = "Raster indisponible — intervalles observés"
    else:
        origine = "estimé" if signal.origine_raster == "estime" else "saisi"
        profil = f"Raster {origine} : {signal.raster_temps:g} {unite}"
        if signal.tolerance_temps is not None:
            profil += f" | Tolérance : ±{signal.tolerance_temps:g} {unite}"
    comptes = Counter(signal.natures_intervalles)
    noms = {"temps_duplique": "doublon(s)", "retour_arriere": "retour(s) arrière",
            "jitter": "jitter hors tolérance", "trou_probable": "trou(s) probable(s)",
            "changement_frequence_probable": "à fréquence modifiée (probable)"}
    anomalies = [f"{comptes[nature]} {nom}" for nature, nom in noms.items() if comptes[nature]]
    bilan = " · ".join(anomalies) if anomalies else "Aucune anomalie parmi les intervalles affichés"
    return profil + "\nIntervalles — fichier entier : " + bilan


# === 1. Afficher la courbe avec ses interruptions, sur les temps du CSV ===
def creer_figure(signal: SignalPrepare, moniteur: dict[str, Any], decimale: str = ".", *, note_signal=None):
    """Retourner la figure et ses deux axes partageant exactement le même temps."""
    from matplotlib.figure import Figure

    figure = Figure(figsize=(9.6, 5.4), dpi=100, facecolor="white")
    grille = figure.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.85)
    courbe = figure.add_subplot(grille[0])
    temps = figure.add_subplot(grille[1], sharex=courbe)
    sample_chart(courbe, signal.temps, signal.valeurs, "", signal.colonne,
                 f"{Path(signal.fichier).name} — {signal.colonne}",
                 relier_points=signal.relier_points, indices_coupures=signal.indices_coupures)
    courbe.tick_params(labelbottom=False)
    if signal.type_signal == "Bool":
        # Les ronds sont les états réellement lus. Aucun maintien à 0/1 entre
        # deux mesures n'est présumé par un escalier ou une interpolation.
        courbe.lines[0].set_linestyle("None")
        courbe.set_yticks([0, 1], ["0 / False", "1 / True"])
        courbe.set_ylim(-0.15, 1.15)
    figure.subplots_adjust(left=0.11, right=0.97, top=0.89, bottom=0.24)

    # === 1a. Croix SUR les mesures qui encadrent des cellules vides du signal ===
    # La mesure absente conserve son NaN : on ne lui invente jamais d'ordonnée.
    # Les croix utilisent les coordonnées réelles du dernier/premier point connu.
    # Ni un saut temporel, ni un texte invalide ne déclenche de croix à lui seul.
    if signal.indices_croix:
        courbe.plot([signal.temps[i] for i in signal.indices_croix],
                    [signal.valeurs[i] for i in signal.indices_croix],
                    linestyle="None", marker="x", color="#dc6a00", markersize=8,
                    markeredgewidth=2, zorder=4, label="Bords des données manquantes")
        courbe.legend(loc="upper right", fontsize=8)

    # === 2. Δt quantitatifs sur la même base X que le signal ===
    # Le point placé au temps t représente t - temps précédent. Les couleurs
    # qualifient seulement l'intervalle observé ; elles n'affirment jamais une
    # perte de donnée. Les lignes rejetées ne sont pas franchies.
    temps.set_title("Time Base Monitor", loc="left", fontsize=10)
    couleur = {"ok": "#17823b", "avertissement": "#b05a00", "erreur": "#b42318"}[moniteur["niveau"]]
    couleurs_intervalles = {
        "observe": "#37759b",
        "conforme": "#23745a", "jitter": "#7b2cbf",
        "trou_probable": "#a33b74", "changement_frequence_probable": "#2455a4",
        "temps_duplique": "#d88500", "retour_arriere": "#c00000",
    }
    libelles_intervalles = {
        "observe": "Δt observés",
        "conforme": "Dans la tolérance", "jitter": "Jitter hors tolérance",
        "trou_probable": "Trou probable",
        "changement_frequence_probable": "Changement de fréquence probable",
        "temps_duplique": "Doublon", "retour_arriere": "Retour arrière",
    }
    # Formes distinctes : les catégories restent reconnaissables sans se fier
    # uniquement à la couleur. Aucune croix ici : elles restent réservées aux
    # cellules vides sur la courbe du signal.
    symboles = {"observe": ".", "conforme": ".", "jitter": "D",
                "trou_probable": "^", "changement_frequence_probable": "s",
                "temps_duplique": "o", "retour_arriere": "v"}
    for nature in ("observe", "conforme", "jitter", "trou_probable",
                   "changement_frequence_probable", "temps_duplique", "retour_arriere"):
        points = [(x, y) for x, y, type_intervalle in zip(
            signal.temps_intervalles, signal.deltas_temps, signal.natures_intervalles
        ) if type_intervalle == nature]
        if points:
            discret = nature in ("observe", "conforme")
            temps.plot([p[0] for p in points], [p[1] for p in points],
                       linestyle="None", marker=symboles[nature],
                       markersize=0.8 if discret else 7,
                       alpha=0.3 if discret else 1, zorder=2 if discret else 5,
                       color=couleurs_intervalles[nature], label=libelles_intervalles[nature])
    if signal.raster_temps is not None:
        libelle_raster = "Raster estimé" if signal.origine_raster == "estime" else "Raster saisi"
        temps.axhline(signal.raster_temps, color="#2f6f4e", linestyle="--",
                      linewidth=0.9, label=libelle_raster)
        if signal.tolerance_temps is not None:
            bas = signal.raster_temps - signal.tolerance_temps
            haut = signal.raster_temps + signal.tolerance_temps
            temps.axhspan(bas, haut, color="#2f8b65", alpha=0.07,
                          label="Tolérance")
    styles = {"temps_duplique": "#d88500", "retour_arriere": "#c00000",
              "pas_hors_tolerance": "#7b2cbf"}
    types_traces: set[str] = set()
    for marqueur in moniteur["marqueurs"]:
        x = _flottant(_decimal(marqueur["temps"], decimale))
        if x is None:
            continue
        teinte = styles[marqueur["type"]]
        # La catégorie figure déjà dans la série quantitative. Le trait sert
        # seulement à localiser précisément l'événement sur l'axe partagé.
        # Le guide vertical reste en arrière-plan : il ne doit pas masquer
        # le symbole placé à la vraie valeur de Δt.
        temps.axvline(x, color=teinte, linewidth=0.7, alpha=0.35,
                      zorder=1, label="_nolegend_")
        types_traces.add(marqueur["type"])
        if marqueur["type"] == "pas_hors_tolerance":
            avant = _flottant(_decimal(marqueur.get("temps_avant", ""), decimale))
            if avant is not None and avant < x:
                courbe.axvspan(avant, x, color="#7b2cbf", alpha=0.14,
                               label="_nolegend_")
    if signal.deltas_temps or types_traces or signal.raster_temps is not None:
        temps.legend(loc="lower right", bbox_to_anchor=(1, 1.25), ncol=3,
                     fontsize=7, framealpha=0.9)
    temps.set_xlabel(f"{signal.colonne_temps} [{signal.unite_temps or 'unité inconnue'}]")
    if signal.format_temps == "heure":
        temps.set_xlabel(f"{signal.colonne_temps} [s depuis minuit, date non définie]")
    temps.set_ylabel(f"Δt [{signal.unite_temps or 'unité inconnue'}]")
    temps.ticklabel_format(axis="x", style="plain", useOffset=False)
    temps.ticklabel_format(axis="y", style="plain", useOffset=False)
    temps.grid(alpha=0.2)
    # Laisser de l'air autour des symboles à Δt=0 et aux extrema ; pas de
    # bornes métier ajoutées, seulement une marge de dessin Matplotlib.
    temps.margins(y=0.2)
    statut = figure.text(0.11, 0, moniteur["message"], color=couleur, fontsize=9, va="bottom")
    note = (f"{signal.colonne} : {len(signal.indices_vides)} cellule(s) vide(s) | "
            f"{len(signal.indices_invalides)} valeur(s) invalide(s) | {signal.lignes_rejetees} ligne(s) rejetée(s)")
    if not signal.lecture_complete:
        note += " | lecture partielle"
    if moniteur.get("marqueurs_tronques"):
        note += " | liste des repères limitée"
    if "pas_hors_tolerance" in types_traces:
        note += "\nBande violette : intervalle hors tolérance ; perte de données non prouvée."
    else:
        note += "\nCroix : mesures réelles de part et d’autre d’un manque dans le CSV."
    if signal.raster_temps is not None:
        note += "\nMoniteur : chaque point est un Δt ; son écart vertical au raster est l'écart temporel."
    else:
        note += "\nMoniteur : Δt observés ; aucun raster fiable n'est imposé."
    if not signal.relier_points:
        note += "\nPas irréguliers ou lecture partielle sans profil : points seuls. Renseigner le pas et sa tolérance."
    note = resumer_moniteur(signal) + "\n" + note
    if note_signal is not None:
        note = resumer_moniteur(signal) + "\n" + note_signal
    legende = figure.text(0.11, 0, note, fontsize=8, color="#4a5568", va="bottom")

    def ajuster_marges(_evenement=None):
        """Réserver la hauteur du texte lors du redimensionnement de la VISU."""
        hauteur = figure.get_figheight() * figure.dpi
        # Retour à la ligne en fonction de la largeur disponible : les noms
        # longs et les bilans d'anomalies ne doivent pas sortir de la figure.
        largeur = figure.get_figwidth() * figure.dpi * 0.86
        caracteres = max(25, int(largeur / (8 * 0.65 * figure.dpi / 72)))
        texte = "\n".join(fill(ligne, width=caracteres) for ligne in note.splitlines())
        legende.set_text(texte)
        hauteur_note = (texte.count("\n") + 1) * 8 * 1.3 * figure.dpi / 72
        legende.set_position((0.11, 8 / hauteur))
        statut.set_position((0.11, (16 + hauteur_note) / hauteur))
        # 60 pixels supplémentaires accueillent le statut et le libellé X.
        figure.subplots_adjust(bottom=min(0.55, (76 + hauteur_note) / hauteur))

    figure.canvas.mpl_connect("resize_event", ajuster_marges)
    ajuster_marges()
    return figure, courbe, temps
