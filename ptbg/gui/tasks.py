"""Exécution des traitements longs hors du fil de l'interface (REQ_COMMON_KH_4105).

Un ``BackgroundTask`` lance une fonction dans un ``threading.Thread`` (et non
un processus : ``multiprocessing`` est peu fiable dans la console de Spyder
sous Windows). Le résultat revient par une file ``queue.Queue`` lue toutes
les 100 ms par ``after`` : l'interface reste réactive et l'utilisateur peut
annuler. Les fonctions exécutées ne doivent jamais toucher à Tkinter.
"""
from __future__ import annotations

import queue
import threading
import traceback
from typing import Callable

POLL_MS = 100


class BackgroundTask:
    """Fonction exécutée en arrière-plan avec avancement et annulation."""

    def __init__(self, root, work: Callable, on_done: Callable, on_error: Callable,
                 on_progress: Callable[[float, str], None] | None = None) -> None:
        self.root = root
        self.cancel_event = threading.Event()
        self._queue: queue.Queue = queue.Queue()
        self._on_done, self._on_error, self._on_progress = on_done, on_error, on_progress
        self._thread = threading.Thread(target=self._run, args=(work,), daemon=True)

    def start(self) -> "BackgroundTask":
        self._thread.start()
        self.root.after(POLL_MS, self._poll)
        return self

    def cancel(self) -> None:
        self.cancel_event.set()

    def progress(self, fraction: float, text: str = "") -> None:
        """Appelé depuis le fil de travail : transmis à l'interface par la file."""
        self._queue.put(("progress", (fraction, text)))

    def _run(self, work: Callable) -> None:
        try:
            self._queue.put(("done", work(self)))
        except Exception as exc:  # noqa: BLE001 - toute erreur est rapportée à l'IHM
            self._queue.put(("error", (exc, traceback.format_exc())))

    def _poll(self) -> None:
        try:
            while True:
                kind, payload = self._queue.get_nowait()
                if kind == "progress" and self._on_progress:
                    self._on_progress(*payload)
                elif kind == "done":
                    self._on_done(payload)
                    return
                elif kind == "error":
                    self._on_error(*payload)
                    return
        except queue.Empty:
            pass
        try:
            self.root.after(POLL_MS, self._poll)
        except Exception:  # noqa: BLE001 - fenêtre fermée pendant le calcul
            pass
