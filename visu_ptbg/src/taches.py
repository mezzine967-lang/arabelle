"""Exécuter un calcul sans Tkinter ; publier son résultat au seul fil graphique.

Requis 4105. Une annulation invalide le résultat, elle ne tue pas un thread
au milieu d'une lecture. Le calcul en cours finit proprement ; aucun deuxième
calcul ne démarre avant sa fin. Cela borne le nombre de tâches et leur mémoire.
"""
from queue import Queue, Empty
from threading import Event, Thread


class TacheFond:
    """Une tâche à la fois, sans widget ni modification de l'état partagé."""

    def __init__(self, calcul):
        self.annulation = Event()
        self.messages = Queue()
        self.terminee = Event()
        self.thread = Thread(target=self._executer, args=(calcul,), daemon=True)
        self.thread.start()

    def _executer(self, calcul):
        try:
            valeur = calcul(self.annulation, self.messages.put)
            self.messages.put(("annule" if self.annulation.is_set() else "resultat", valeur))
        except Exception as exc:
            self.messages.put(("annule" if self.annulation.is_set() else "erreur", str(exc)))
        finally:
            self.terminee.set()

    def annuler(self):
        self.annulation.set()

    def lire(self):
        """Vider la file sans attendre : à appeler depuis after() dans Tk."""
        messages = []
        while True:
            try:
                messages.append(self.messages.get_nowait())
            except Empty:
                return messages


def importer_copie(paquet, chemins, annulation, publier):
    """Préparer un nouveau paquet ; les listes de l'IHM restent inchangées.

    Les résultats existants ne sont pas modifiés : les deux listes sont copiées
    avant l'ajout. Si l'utilisateur annule, la copie est simplement abandonnée.
    """
    from paquet_csv import PaquetCSV
    nouveau = PaquetCSV()
    nouveau.sources = list(paquet.sources)
    nouveau.resultats = list(paquet.resultats)
    for indice, chemin in enumerate(chemins):
        if annulation.is_set():
            break
        publier(("progression", f"Lecture {indice + 1}/{len(chemins)} : {chemin}"))
        nouveau.ajouter([chemin])
    return nouveau
