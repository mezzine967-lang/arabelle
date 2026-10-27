"""Modèles de disposition (templates) et état d'un onglet graphique.

- REQ_COMMON_KH_5300 : plusieurs modèles proposant des dispositions d'axes ;
- REQ_COMMON_KH_5106 : chaque onglet de la zone graphique porte sa disposition ;
- REQ_COMMON_KH_4102 : le Time Base Monitor n'est PAS un axe du modèle : il
  est ajouté automatiquement sous chaque disposition par le rendu ;
- REQ_COMMON_KH_6004 : l'état d'un onglet est une donnée pure (copiable et
  sérialisable) : une capture pour le rapport pas à pas fige zoom, curseurs,
  nuage X/Y, condition... au moment où l'utilisateur l'ajoute.

« Axle » (terminologie du document) = zone graphique = axe Matplotlib.
"""
from __future__ import annotations

import copy
from dataclasses import asdict, dataclass, field

from ptbg.core.conditional import Condition


@dataclass(frozen=True)
class AxleSlot:
    """Place d'un axe dans la grille du modèle ; ``kind`` = "time" ou "xy"."""
    row: int
    col: int
    rowspan: int = 1
    colspan: int = 1
    kind: str = "time"


@dataclass(frozen=True)
class Template:
    key: str
    name: str
    description: str
    nrows: int
    ncols: int
    slots: tuple
    row_ratios: tuple
    col_ratios: tuple = (1,)


TEMPLATES = (
    Template("1A", "1 axe", "Un axe temporel sur toute la largeur.", 1, 1,
             (AxleSlot(0, 0),), (1,)),
    Template("2A", "2 axes superposés", "Deux axes temporels synchronisés.", 2, 1,
             (AxleSlot(0, 0), AxleSlot(1, 0)), (1, 1)),
    Template("3A", "3 axes superposés", "Trois axes temporels synchronisés.", 3, 1,
             (AxleSlot(0, 0), AxleSlot(1, 0), AxleSlot(2, 0)), (1, 1, 1)),
    Template("4A", "4 axes superposés", "Quatre axes temporels synchronisés.", 4, 1,
             tuple(AxleSlot(i, 0) for i in range(4)), (1, 1, 1, 1)),
    Template("AL", "Analogique + logique", "Grand axe analogique et piste logique (Bool).", 2, 1,
             (AxleSlot(0, 0), AxleSlot(1, 0)), (3, 1)),
    Template("2x2", "Grille 2 × 2", "Quatre axes temporels en grille, temps commun.", 2, 2,
             tuple(AxleSlot(r, c) for r in range(2) for c in range(2)), (1, 1), (1, 1)),
    Template("XY", "Temporel + nuage X/Y", "Deux axes temporels et un nuage X/Y de corrélation.", 2, 2,
             (AxleSlot(0, 0), AxleSlot(1, 0), AxleSlot(0, 1, rowspan=2, kind="xy")), (1, 1), (3, 2)),
)


def template(key: str) -> Template:
    return next((t for t in TEMPLATES if t.key == key), TEMPLATES[0])


@dataclass
class CurveRef:
    """Courbe d'un axe : variable (ou groupe binaire) d'un fichier."""
    file_id: str
    name: str
    is_group: bool = False
    color: str = ""


@dataclass
class AxleState:
    """État d'un axe : courbes, curseurs, condition, nuage X/Y."""
    kind: str = "time"
    curves: list[CurveRef] = field(default_factory=list)
    selected: int = 0                     # courbe sélectionnée (REQ 5401)
    cursor_mode: str = "none"             # "none" | "single" | "double" (REQ 5400, 5403)
    t1: float | None = None
    t2: float | None = None
    h_enabled: bool = False               # curseur horizontal (REQ 5406)
    h_level: float | None = None
    h_condition: Condition | None = None  # conditionnement Bool (REQ 5407)
    xy_x: CurveRef | None = None          # nuage X/Y (REQ 5408)
    xy_y: CurveRef | None = None
    xy_mode: str = "two_cursors"          # "two_cursors" | "cross_point"
    xy_t: float | None = None             # instant du point désigné
    ylim: list | None = None              # None = échelle automatique

    def selected_curve(self) -> CurveRef | None:
        if not self.curves:
            return None
        return self.curves[min(self.selected, len(self.curves) - 1)]


@dataclass
class TabState:
    """État complet d'un onglet (disposition + axes + curseur global)."""
    title: str
    template_key: str
    axles: list[AxleState]
    global_cursor: bool = False           # REQ 5405
    t_global: float | None = None
    tracking: bool = False                # suivi souris (REQ 5402)
    xlim: list | None = None              # zoom temporel commun
    tbm_visible: bool = True              # REQ 4103
    comment: str = ""                     # commentaire de page (rapport pas à pas)

    @classmethod
    def from_template(cls, key: str, title: str) -> "TabState":
        chosen = template(key)
        return cls(title, chosen.key, [AxleState(kind=slot.kind) for slot in chosen.slots])

    @property
    def template(self) -> Template:
        return template(self.template_key)

    def file_ids(self) -> list[str]:
        """Fichiers présents dans l'onglet (pour le Time Base Monitor)."""
        ids: list[str] = []
        for axle in self.axles:
            refs = list(axle.curves) + [r for r in (axle.xy_x, axle.xy_y) if r is not None]
            for ref in refs:
                if ref.file_id not in ids:
                    ids.append(ref.file_id)
            if axle.h_condition:
                for term in axle.h_condition.terms:
                    if term.file_id not in ids:
                        ids.append(term.file_id)
        return ids

    def copy(self) -> "TabState":
        return copy.deepcopy(self)

    # -------------------------------------------------------- sérialisation
    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "TabState":
        """Reconstruit un état depuis ``to_dict`` (projet, page de rapport)."""
        axles = []
        for raw in data.get("axles", []):
            raw = dict(raw)
            raw["curves"] = [CurveRef(**c) for c in raw.get("curves", [])]
            for key in ("xy_x", "xy_y"):
                raw[key] = CurveRef(**raw[key]) if raw.get(key) else None
            raw["h_condition"] = Condition.from_dict(raw["h_condition"]) if raw.get("h_condition") else None
            axles.append(AxleState(**raw))
        fields_ = {k: v for k, v in data.items() if k != "axles"}
        return cls(axles=axles, **fields_)
