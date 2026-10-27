"""Lecture de vrais échantillons et curseurs Matplotlib (requis 5400-5406).

Le clic s'accroche au timestamp enregistré le plus proche. Tous les doublons
sont indiqués ; une cellule vide/illégale n'est jamais remplacée. La position
est graphique en float mais la fenêtre de lecture utilise les textes du CSV.
"""
from bisect import bisect_left
from math import isfinite


class LecteurEchantillons:
    """Index de consultation seulement : l'ordre de la courbe n'est pas changé."""

    def __init__(self, signal):
        self.signal = signal
        self.indices = {}
        for i, temps in enumerate(signal.temps):
            self.indices.setdefault(temps, []).append(i)
        self.temps_tries = sorted(self.indices)

    def proche(self, x):
        if not self.temps_tries or not isfinite(x):
            raise ValueError("Position temporelle non représentable.")
        rang = bisect_left(self.temps_tries, x)
        candidats = self.temps_tries[max(0, rang - 1):rang + 1]
        temps = min(candidats, key=lambda t: (abs(t - x), t))
        return temps, self.indices[temps]

    def decrire(self, indices):
        s = self.signal
        lignes = []
        # Limiter seulement la fenêtre de texte, jamais les données stockées.
        for i in indices[:20]:
            temps = s.temps_bruts[i] if s.temps_bruts else str(s.temps[i])
            brut = s.valeurs_brutes[i] if s.valeurs_brutes else str(s.valeurs[i])
            valeur = brut if isfinite(s.valeurs[i]) else "ABSENTE" if i in s.indices_vides else "INVALIDE : " + brut
            lignes.append(f"Ligne {s.lignes[i]} | t={temps} | {s.colonne}={valeur}")
        if len(indices) > 20:
            lignes.append(f"{len(indices)} mesures au même temps ; 20 montrées.")
        return "\n".join(lignes)


class Curseurs:
    """Dessiner sans recalculer le raster ni changer les données du signal."""

    MODES = ("Aucun", "Vertical", "Double vertical", "Horizontal")

    def __init__(self, figure, axe, moniteur, signal, afficher):
        self.figure, self.axe, self.moniteur = figure, axe, moniteur
        self.signal, self.afficher = signal, afficher
        self.signaux = [signal]
        self.lecteurs = [LecteurEchantillons(signal)]
        self.sur_position = None
        self.lecteur = LecteurEchantillons(signal)
        self.mode = "Aucun"
        self.suivi = False
        self.condition = None
        self.cible = 0
        self.positions = [None, None]
        limites = (axe.get_xlim(), axe.get_ylim(), moniteur.get_xlim(), moniteur.get_ylim())
        self.lignes = [axe.axvline(0, color=c, visible=False, linewidth=1)
                       for c in ("#a1266d", "#805900")]
        self.guides = [moniteur.axvline(0, color=c, visible=False, linewidth=1)
                       for c in ("#a1266d", "#805900")]
        self.horizontale = axe.axhline(0, color="#a1266d", visible=False)
        self.annotation = axe.text(.99, .02, "", transform=axe.transAxes,
                                   ha="right", va="bottom", fontsize=8, zorder=10,
                                   bbox=dict(facecolor="white", alpha=.85, edgecolor="none"))
        self.connexions = [figure.canvas.mpl_connect("button_press_event", self._clic),
                           figure.canvas.mpl_connect("motion_notify_event", self._mouvement)]
        # Un artiste invisible à x=0 ne doit pas agrandir le domaine temporel.
        axe.set_xlim(limites[0]); axe.set_ylim(limites[1])
        moniteur.set_xlim(limites[2]); moniteur.set_ylim(limites[3])

    def choisir(self, mode):
        if mode not in self.MODES:
            raise ValueError("Mode de curseur inconnu.")
        if mode == "Horizontal" and self.signal.type_signal != "Float":
            raise ValueError("Le curseur horizontal est réservé aux signaux Float.")
        self.mode = mode
        self.sur_position = None
        self.positions = [None, None]
        for ligne in self.lignes + self.guides + [self.horizontale]:
            ligne.set_visible(False)
        self.annotation.set_text("")
        self.afficher("Cliquer sur le graphique. Lecture d'échantillons réels, sans interpolation.")
        self.figure.canvas.draw_idle()

    def _clic(self, evenement):
        # Ne pas intercepter le zoom ou le déplacement de la barre Matplotlib.
        barre = getattr(self.figure.canvas, "toolbar", None)
        if barre and barre.mode or evenement.inaxes is not self.axe or evenement.button != 1:
            return
        if self.mode == "Horizontal" and evenement.ydata is not None:
            self.placer_horizontal(evenement.ydata)
        elif self.mode in ("Vertical", "Double vertical") and evenement.xdata is not None:
            self.placer(evenement.xdata, self.cible if self.mode == "Double vertical" else 0)
        self.figure.canvas.draw_idle()

    def definir_condition(self, condition):
        """Même CSV et même ligne physique ; jamais d'alignement par proximité."""
        if condition is not None:
            if condition.type_signal != "Bool" or not meme_horloge(self.signal, condition):
                raise ValueError("La condition doit être un Bool de la même lecture du CSV.")
        self.condition = condition
        self.horizontale.set_visible(False)
        self.annotation.set_text("")
        self.afficher("Condition : " + (condition.colonne + " = vrai ; absences et invalides exclues."
                                      if condition else "aucune"))
        self.figure.canvas.draw_idle()

    def placer_horizontal(self, y):
        """Lire la valeur analogique mesurée la plus proche de l'ordonnée visée.

        Le Bool vrai autorise uniquement la mesure sur sa propre ligne. On ne
        prolonge pas un état à travers un champ vide ni un autre timestamp.
        """
        if self.signal.type_signal != "Float" or not isfinite(y):
            raise ValueError("Choisir une ordonnée finie sur un signal Float.")
        autorisees = None
        if self.condition is not None:
            autorisees = {ligne for ligne, valeur in zip(self.condition.lignes, self.condition.valeurs)
                          if valeur == 1}
        candidats = [i for i, valeur in enumerate(self.signal.valeurs)
                     if isfinite(valeur) and (autorisees is None or self.signal.lignes[i] in autorisees)]
        if not candidats:
            self.horizontale.set_visible(False)
            self.annotation.set_text("Aucune mesure autorisée")
            self.afficher("Aucune mesure analogique présente avec un Bool vrai sur la même ligne.")
            return []
        meilleur = min(candidats, key=lambda i: (abs(self.signal.valeurs[i] - y), i))
        valeur = self.signal.valeurs[meilleur]
        indices = [i for i in candidats if self.signal.valeurs[i] == valeur]
        self.horizontale.set_ydata([valeur] * 2)
        self.horizontale.set_visible(True)
        condition = "" if self.condition is None else f" | {self.condition.colonne} = vrai"
        self.annotation.set_text(f"Y mesuré = {valeur:.9g}" + condition)
        self.afficher(self.annotation.get_text() + "\n" + self.lecteur.decrire(indices))
        return indices

    def _mouvement(self, evenement):
        """REQ 5402 : suivre la souris seulement en mode demandé, hors zoom/pan.

        Ne redessiner que lorsque l'échantillon change : le suivi ne doit pas
        déclencher un rendu coûteux pour chaque pixel parcouru.
        """
        barre = getattr(self.figure.canvas, "toolbar", None)
        if (not self.suivi or self.mode not in ("Vertical", "Double vertical")
                or evenement.inaxes is not self.axe or evenement.xdata is None
                or (barre and barre.mode)):
            return
        cible = self.cible if self.mode == "Double vertical" else 0
        temps, _ = self.lecteur.proche(evenement.xdata)
        if self.positions[cible] is not None and self.positions[cible][0] == temps:
            return
        self.placer(evenement.xdata, cible)
        self.figure.canvas.draw_idle()

    def placer(self, x, cible=0, notifier=True):
        temps, indices = self.lecteur.proche(x)
        self.positions[cible] = (temps, indices)
        for ligne in (self.lignes[cible], self.guides[cible]):
            ligne.set_xdata([temps, temps])
            ligne.set_visible(True)
        textes, etiquettes = [], []
        for i, position in enumerate(self.positions):
            if position is not None:
                lecture = []
                for lecteur in self.lecteurs:
                    # Les courbes superposées partagent le même fichier/hash.
                    # Lire au même timestamp, sans chercher un point voisin
                    # dans une autre horloge.
                    indices_signal = lecteur.indices.get(position[0], [])
                    lecture.append(lecteur.decrire(indices_signal) if indices_signal else "Aucune mesure à cet instant.")
                textes.append(f"C{i + 1} — échantillon le plus proche\n" + "\n".join(lecture))
                j = position[1][0]
                brut = self.signal.temps_bruts[j] if self.signal.temps_bruts else str(position[0])
                etiquettes.append(f"C{i + 1}: t={brut}")
        self.annotation.set_text("\n".join(etiquettes))
        self.afficher("\n\n".join(textes))
        if notifier and self.sur_position is not None:
            self.sur_position(temps, cible)
        return temps

    def ajouter(self, signal):
        if not meme_horloge(self.signal, signal):
            raise ValueError("Superposition limitée au même fichier et à la même lecture.")
        self.signaux.append(signal)
        self.lecteurs.append(LecteurEchantillons(signal))

    def detruire(self):
        for connexion in self.connexions:
            self.figure.canvas.mpl_disconnect(connexion)


def meme_horloge(a, b):
    """L'identité du CSV, son contenu et l'unité prouvent ici le repère commun."""
    return (a.fichier, a.sha256, a.unite_temps, a.format_temps) == (b.fichier, b.sha256, b.unite_temps, b.format_temps)
