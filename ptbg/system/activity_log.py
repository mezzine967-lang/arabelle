"""Journal d'activité de la session (REQ_COMMON_KH_5102 « Activity log »).

Chaque action notable (ouverture, analyse, rapport, erreur) est :
- conservée en mémoire pour la fenêtre « Journal d'activité » ;
- transmise aux écouteurs (la barre d'état affiche le dernier message) ;
- écrite dans un fichier journal du dossier utilisateur (traçabilité), par
  exemple ~/.local/state/visu_ptbg/journal_20261027.log sous SLES.

L'écriture disque est facultative : si le dossier est en lecture seule, le
journal continue en mémoire, sans interrompre l'outil.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable

from ptbg.system.compat import ensure_dir, user_state_dir

LEVELS = ("INFO", "AVERTISSEMENT", "ERREUR")


@dataclass(frozen=True)
class LogEntry:
    """Une ligne du journal."""
    when: datetime
    level: str
    message: str

    def as_line(self) -> str:
        return f"{self.when:%Y-%m-%d %H:%M:%S}  {self.level:<13} {self.message}"


class ActivityLog:
    """Journal thread-safe avec écouteurs (la barre d'état en est un)."""

    def __init__(self, log_dir: Path | None = None, write_to_disk: bool = True) -> None:
        self._entries: list[LogEntry] = []
        self._listeners: list[Callable[[LogEntry], None]] = []
        self._lock = threading.Lock()
        self.file_path: Path | None = None
        if write_to_disk:
            folder = ensure_dir(log_dir or user_state_dir())
            if folder is not None:
                self.file_path = folder / f"journal_{datetime.now():%Y%m%d}.log"

    def add_listener(self, callback: Callable[[LogEntry], None]) -> None:
        self._listeners.append(callback)

    def log(self, message: str, level: str = "INFO") -> LogEntry:
        """Ajoute une entrée ; ``level`` vaut INFO, AVERTISSEMENT ou ERREUR."""
        entry = LogEntry(datetime.now(), level if level in LEVELS else "INFO", message)
        with self._lock:
            self._entries.append(entry)
        self._write(entry)
        for callback in list(self._listeners):
            callback(entry)
        return entry

    def entries(self) -> list[LogEntry]:
        with self._lock:
            return list(self._entries)

    def as_text(self) -> str:
        return "\n".join(entry.as_line() for entry in self.entries())

    def _write(self, entry: LogEntry) -> None:
        if self.file_path is None:
            return
        try:
            with self.file_path.open("a", encoding="utf-8") as handle:
                handle.write(entry.as_line() + "\n")
        except OSError:
            self.file_path = None  # dossier devenu inaccessible : mémoire seule
