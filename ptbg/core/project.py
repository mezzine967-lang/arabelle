"""Fichier projet « .ptbg.json » : sauvegarde et réouverture d'une analyse.

Il mémorise paquets, fichiers (chemin + SHA-256), réglages de base de temps,
types forcés, groupes binaires, onglets et pages du rapport pas à pas. Son
nom et son SHA-256 alimentent l'en-tête des rapports (REQ_COMMON_KH_6005
« Project file reference or Hash »).

Compatibilité Windows / SLES (REQ_COMMON_KH_3005) : les chemins sont stockés
RELATIFS au fichier projet, avec « / » comme séparateur, en plus du chemin
absolu d'origine. Un projet créé sous Windows se rouvre ainsi sous SLES si
le dossier (projet + CSV) a été copié tel quel.

Les CSV ne sont jamais modifiés ni copiés dans le projet ; à la réouverture,
une empreinte différente est signalée (fichier source modifié entre-temps).
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path, PurePosixPath

from ptbg.core.arrangement import TabState
from ptbg.core.data_package import Workspace
from ptbg.core.signals import BinaryGroup, SignalType
from ptbg.core.time_parser import TimeBaseSettings
from ptbg.version import TOOL_VERSION

PROJECT_FORMAT = 1
PROJECT_SUFFIX = ".ptbg.json"


@dataclass
class ReportPage:
    """Page du rapport pas à pas : capture figée d'un onglet (REQ 6004)."""
    tab: TabState
    time_mode: str
    ref_ns: int | None
    captured_at: str = field(default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    def to_dict(self) -> dict:
        """Forme sérialisable en JSON."""
        return {"tab": self.tab.to_dict(), "time_mode": self.time_mode, "ref_ns": self.ref_ns,
                "captured_at": self.captured_at}

    @classmethod
    def from_dict(cls, data: dict) -> "ReportPage":
        """Reconstruit une page depuis ``to_dict``."""
        return cls(TabState.from_dict(data["tab"]), data.get("time_mode", "relative"),
                   data.get("ref_ns"), data.get("captured_at", ""))


@dataclass
class FileEntry:
    """Fichier à recharger à l'ouverture d'un projet."""
    package: str
    path: Path
    file_id: str
    sha256: str
    time_settings: TimeBaseSettings
    type_overrides: dict
    groups: list[BinaryGroup]


@dataclass
class ProjectData:
    packages: list[str]
    files: list[FileEntry]
    time_mode: str
    tabs: list[TabState]
    pages: list[ReportPage]
    header: dict


def _portable(path: Path, base: Path) -> str:
    """Chemin relatif au projet avec « / », ou vide si impossible (autre lecteur)."""
    try:
        return PurePosixPath(Path(os.path.relpath(path, base)).as_posix()).as_posix()
    except ValueError:          # autre lecteur sous Windows : pas de chemin relatif
        return ""


def save_project(path: Path, workspace: Workspace, tabs: list[TabState],
                 pages: list[ReportPage], header: dict) -> None:
    """Écrit le projet en JSON UTF-8 (lisible et comparable entre versions)."""
    base = path.resolve().parent
    packages = []
    for package in workspace.packages:
        files = []
        for source in package.files:
            files.append({
                "relative_path": _portable(source.path.resolve(), base),
                "absolute_path": str(source.path.resolve()),
                "file_id": source.id,
                "sha256": source.sha256,
                "time_settings": source.time_settings.to_dict(),
                "type_overrides": {k: v.value for k, v in source.type_overrides.items()},
                "groups": [{"name": g.name, "members": g.members, "automatic": g.automatic}
                           for g in source.groups.values()],
            })
        packages.append({"name": package.name, "files": files})
    document = {
        "format": PROJECT_FORMAT, "tool_version": TOOL_VERSION,
        "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "time_mode": workspace.time_mode, "packages": packages,
        "tabs": [tab.to_dict() for tab in tabs],
        "report_pages": [page.to_dict() for page in pages],
        "report_header": header,
    }
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False), encoding="utf-8")


def load_project(path: Path) -> ProjectData:
    """Lit un projet ; lève ValueError si le format est inconnu."""
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("format") != PROJECT_FORMAT:
        raise ValueError(f"Format de projet non pris en charge : {document.get('format')}")
    base = path.resolve().parent
    entries, names = [], []
    for package in document.get("packages", []):
        names.append(package["name"])
        for item in package.get("files", []):
            relative = item.get("relative_path")
            candidate = base / relative if relative else None
            file_path = candidate if candidate and candidate.exists() else Path(item["absolute_path"])
            entries.append(FileEntry(
                package["name"], file_path, item["file_id"], item.get("sha256", ""),
                TimeBaseSettings.from_dict(item.get("time_settings", {})),
                {k: SignalType(v) for k, v in item.get("type_overrides", {}).items()},
                [BinaryGroup(g["name"], list(g["members"]), g.get("automatic", False))
                 for g in item.get("groups", [])]))
    return ProjectData(names, entries, document.get("time_mode", "relative"),
                       [TabState.from_dict(t) for t in document.get("tabs", [])],
                       [ReportPage.from_dict(p) for p in document.get("report_pages", [])],
                       document.get("report_header", {}))
