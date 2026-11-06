"""Génère les CSV de démonstration de data/demo/ (reproductibles, graine fixe).

Usage : python tools/generer_donnees_demo.py

Chaque fichier illustre des requis précis :

- PLC_A_10ms_pretrig.csv : compteur « t_ms » à 10 ms (REQ 2100, 2307) avec
  pré-déclenchement en temps négatif (remarque sur REQ 2305), jitter de
  ± 0,4 ms toléré (REQ 4107), un trou de 3 échantillons (REQ 4101), des
  cellules vides, un groupe binaire indexé DI[0..3] (REQ 2201) ;
- PLC_B_20ms_dephase.csv : second PLC à 20 ms, décalé de 5 ms par rapport à
  A (déphasage inter-sources, REQ 2104), un échantillon déphasé et un
  changement de fréquence 20 -> 40 ms en fin de fichier (REQ 2104) ;
- PLC_C_heure_ns.csv : horodatage absolu « hh:mm:ss.nnnnnnnnn » (REQ 2306)
  qui passe minuit, et un horodatage dupliqué (REQ 4100, croissance continue) ;
- non_conforme_point_virgule.csv : séparateur « ; » refusé (REQ 2301).

Les signaux simulent une montée en pression avec déclenchement d'alarme et
une régulation : ils servent uniquement à démontrer l'outil.
"""
from __future__ import annotations

import csv
import math
import random
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "data" / "demo"


def _write(name: str, header: list[str], rows: list[list]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    with (OUT / name).open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)
    print(f"{name} : {len(rows)} lignes")


def _process(t: float) -> tuple[float, float]:
    """Pression et débit simulés ; échelon de consigne à t = 0 (déclenchement)."""
    pressure = 50.0 + (0.0 if t < 0 else 30.0 * (1 - math.exp(-t / 1.5)))
    flow = 12.0 + 2.0 * math.sin(2 * math.pi * 0.4 * t)
    return pressure, flow


def plc_a(rng: random.Random) -> None:
    """PLC A : 10 ms, pré-déclenchement, jitter toléré, trou, cellules vides, groupe DI[0..3]."""
    rows = []
    k_values = [k for k in range(-200, 800) if k not in (412, 413, 414)]   # trou de 3 échantillons
    for k in k_values:
        t_ms = k * 10 + rng.uniform(-0.4, 0.4)                              # jitter ± 0,4 ms
        t = t_ms / 1000
        pressure, flow = _process(t)
        pressure += rng.gauss(0, 0.15)
        alarm = pressure > 75.0
        pump = t >= 0.2
        valve = 1.0 <= t <= 5.5
        bits = [int(pump), int(valve), int(alarm), int(t > 3.0)]
        flow_cell = "" if 250 <= k < 262 else f"{flow:.4f}"                # cellules vides
        rows.append([f"{t_ms:.3f}", f"{pressure:.4f}", flow_cell, str(pump), str(valve),
                     str(alarm)] + bits)
    _write("PLC_A_10ms_pretrig.csv",
           ["t_ms", "P_circuit_bar", "Debit_m3h", "Pompe_ON", "Vanne_ouverte", "Alarme_P_haute",
            "DI[0]", "DI[1]", "DI[2]", "DI[3]"], rows)


def plc_b(rng: random.Random) -> None:
    """PLC B : 20 ms décalé de 5 ms, un échantillon déphasé, passage à 40 ms en fin de fichier."""
    rows = []
    t_ms = -1995.0                                       # décalé de +5 ms par rapport à A
    k = 0
    while t_ms <= 7995:
        t = t_ms / 1000
        pressure, _flow = _process(t - 0.05)
        temperature = 40.0 + (0.0 if t < 0 else 8.0 * (1 - math.exp(-t / 3.0)))
        command = 0.0 if t < 0 else min(100.0, 20.0 * t)
        rows.append([f"{t_ms:.1f}", f"{pressure + rng.gauss(0, 0.2):.4f}", f"{temperature:.3f}",
                     f"{command:.2f}", "1" if t >= 0 else "0"])
        k += 1
        step = 40.0 if t_ms >= 6000 else 20.0            # changement de fréquence en fin de fichier
        if k == 150:
            step = 27.0                                  # un échantillon déphasé
        t_ms += step
    _write("PLC_B_20ms_dephase.csv", ["Temps_ms", "P_mesure_B", "T_fluide_C", "Commande_pct", "Mode_auto"],
           rows)


def plc_c(rng: random.Random) -> None:
    """PLC C : horodatage hh:mm:ss.nnnnnnnnn passant minuit, avec un doublon."""
    rows = []
    start_ns = ((23 * 60 + 59) * 60 + 55) * 1_000_000_000         # 23:59:55, passe minuit
    previous = start_ns
    for k in range(1000):
        ns = start_ns + k * 10_000_000 + rng.randint(-200_000, 200_000)
        if k == 600:
            ns = previous                                          # horodatage dupliqué
        previous = ns
        ns %= 86_400 * 1_000_000_000
        hours, rest = divmod(ns, 3_600_000_000_000)
        minutes, rest = divmod(rest, 60_000_000_000)
        seconds, fraction = divmod(rest, 1_000_000_000)
        stamp = f"{hours:02d}:{minutes:02d}:{seconds:02d}.{fraction:09d}"
        level = 2.0 + 0.5 * math.sin(k / 40)
        rows.append([stamp, f"{level:.4f}", "true" if level > 2.3 else "false"])
    _write("PLC_C_heure_ns.csv", ["Horodatage", "Niveau_m", "Seuil_niveau"], rows)


def non_conforme() -> None:
    """Fichier au séparateur « ; » : doit être refusé (REQ 2301) sans bloquer les autres."""
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "non_conforme_point_virgule.csv").write_text("t_ms;A;B\n0;1,5;0\n10;1,6;1\n", encoding="utf-8")
    print("non_conforme_point_virgule.csv : séparateur « ; »")


if __name__ == "__main__":
    generator = random.Random(20261027)
    plc_a(generator)
    plc_b(generator)
    plc_c(generator)
    non_conforme()
