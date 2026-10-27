# -*- coding: utf-8 -*-
# generate_report10.py — reads simulation9.csv / simulation10.csv

import os
import numpy as np
import pandas as pd

# ============================================================
# PARAMETERS (miroir de la simu pour fallback)
# ============================================================
HB_TIMEOUT_MS        = 50.0
STALL_LIMIT          = 2
CONSUMER_CYCLE_MS    = 20.0
# detect_delay = max(HB_TIMEOUT_MS, STALL_LIMIT * CONSUMER_CYCLE_MS)

# ============================================================
# UTILITIES
# ============================================================

def load_data():
    # auto-pick latest if both exist
    fn = "simulation10.csv" if os.path.exists("simulation10.csv") else "simulation9.csv"
    df = pd.read_csv(fn)
    df["t_ms"] = pd.to_numeric(df["t_ms"], errors="coerce")
    df.dropna(subset=["t_ms"], inplace=True)
    df.sort_values("t_ms", inplace=True)
    df.reset_index(drop=True, inplace=True)
    return df

def rising_edges_bool(series, t):
    x = series.fillna(0).astype(int).to_numpy()
    tt = t.to_numpy(dtype=float)
    idx = np.where((x[:-1] == 0) & (x[1:] == 1))[0] + 1
    return tt[idx]

def rising_edges_threshold(series, t, thr=0.5):
    x = (series > thr).astype(int).to_numpy()
    tt = t.to_numpy(dtype=float)
    idx = np.where((x[:-1] == 0) & (x[1:] == 1))[0] + 1
    return tt[idx]

def mean_delay(src_edges, dst_edges):
    delays = []
    j = 0
    for e in src_edges:
        while j < len(dst_edges) and dst_edges[j] < e:
            j += 1
        if j < len(dst_edges):
            delays.append(dst_edges[j] - e)
    return np.mean(delays) if len(delays) > 0 else np.nan

def first_time(df, col, value=1):
    rows = df[df[col] == value]
    return float(rows["t_ms"].iloc[0]) if not rows.empty else np.nan

def state_at(df, state_col, time_ms):
    rows = df[df["t_ms"] >= time_ms]
    return rows[state_col].iloc[0] if not rows.empty else "UNKNOWN"

# ============================================================
# MAIN REPORT
# ============================================================

def report():

    DF = load_data()
    T = DF["t_ms"]

    # ========== SOURCE (pour stats seulement) ==========
    SRC_EDGES = rising_edges_threshold(DF["source"], T)
    SRC_EDGES = SRC_EDGES[SRC_EDGES >= 1000]
    if len(SRC_EDGES) > 1:
        periods = np.diff(SRC_EDGES)
        freq = 1000.0 / np.mean(periods)
        cycle_rate = np.mean(DF["source"]) * 100
    else:
        freq = np.nan
        cycle_rate = np.nan

    # ========== PRODUCERS ==========
    producers = {}
    for pid in [1, 2, 3]:
        start = first_time(DF, f"start_p{pid}")
        edges = rising_edges_threshold(DF[f"prod{pid}"], T)
        delay = mean_delay(SRC_EDGES, edges)
        overruns = int(DF[f"ov_p{pid}"].sum())
        producers[pid] = {"start": start, "delay": delay, "overruns": overruns}

    # ========== CONSUMERS ==========
    consumers = {}
    for cid in [1, 2]:
        start = first_time(DF, f"start_c{cid}")
        vote_edges = rising_edges_bool(DF[f"cons{cid}_vote"], T)
        delay = mean_delay(SRC_EDGES, vote_edges)
        overruns = int(DF[f"ov_c{cid}"].sum())
        status_1s = state_at(DF, f"cons{cid}_state", 1000)
        fail_rows = DF[DF[f"cons{cid}_state"] == "FAILED"]
        if not fail_rows.empty:
            fail_time = float(fail_rows["t_ms"].iloc[0])
            new_status = "FAILED"
        else:
            fail_time = np.nan
            new_status = "N/A"
        consumers[cid] = {
            "start": start,
            "delay": delay,
            "overruns": overruns,
            "status_1s": status_1s,
            "fail_time": fail_time,
            "new_status": new_status
        }

    # ========== PUBLISHER ==========
    pub_start = first_time(DF, "start_pub")
    # fronts logiques (diagnostic): dépend de changements de valeur
    PUB_EDGES = rising_edges_bool(DF["pub_output"], T)
    # liste de TOUS les instants de publication (plus robuste)
    PUB_TIMES = DF.loc[DF["pub_output"].notna(), "t_ms"].to_numpy(dtype=float)
    pub_delay = mean_delay(SRC_EDGES, PUB_EDGES)
    pub_overruns = int(DF["ov_pub"].sum())

    # ========== FAILURE / SWITCH / RECOVERY ==========
    # 1) fault_time direct si disponible
    fault_time_raw = first_time(DF, "failure_plc")  # peut être NaN
    # 2) switch_time = 1er instant où C2 devient ACTIVE
    c2_rows = DF[DF["cons2_state"] == "ACTIVE"]
    switch_time = float(c2_rows["t_ms"].iloc[0]) if not c2_rows.empty else np.nan

    # 3) fallback si fault_time absent: estimer par la détection HB + stall
    detect_delay = max(HB_TIMEOUT_MS, STALL_LIMIT * CONSUMER_CYCLE_MS)
    fault_time = fault_time_raw if not np.isnan(fault_time_raw) else (
        switch_time - detect_delay if not np.isnan(switch_time) else np.nan
    )

    # 4) délais
    switch_delay = (
        switch_time - fault_time
        if (not np.isnan(fault_time) and not np.isnan(switch_time))
        else np.nan
    )

    # publication la plus proche APRES le switch (indépendant d'un front)
    first_pub_after_switch = np.nan
    if not np.isnan(switch_time) and len(PUB_TIMES) > 0:
        after = PUB_TIMES[PUB_TIMES >= switch_time]
        if len(after) > 0:
            first_pub_after_switch = after[0]

    # recovery pure pipeline (switch -> publish)
    recovery_switch_to_pub = (
        first_pub_after_switch - switch_time
        if (not np.isnan(first_pub_after_switch) and not np.isnan(switch_time))
        else np.nan
    )
    # recovery end-to-end (fault -> publish)
    recovery_fault_to_pub = (
        first_pub_after_switch - fault_time
        if (not np.isnan(first_pub_after_switch) and not np.isnan(fault_time))
        else np.nan
    )

    # (optionnel) edge-to-edge purement diagnostique
    complete_delay_edge2edge = np.nan
    if not np.isnan(fault_time) and not np.isnan(switch_time):
        src_edge = SRC_EDGES[SRC_EDGES <= fault_time]
        last_src = src_edge[-1] if len(src_edge) > 0 else np.nan
        pub_edge = PUB_EDGES[PUB_EDGES >= switch_time]
        first_pub_edge = pub_edge[0] if len(pub_edge) > 0 else np.nan
        if not np.isnan(last_src) and not np.isnan(first_pub_edge):
            complete_delay_edge2edge = first_pub_edge - last_src

    # ========== MARKDOWN ==========
    with open("report.md", "w", encoding="utf-8") as f:

        f.write("# REDUNDANCY8 REPORT\n\n")

        f.write("## Source\n")
        f.write(f">Frequency calculated: {freq:.3f} Hz\n")
        f.write(f">Cycle rate calculated: {cycle_rate:.2f} %\n\n")

        for pid in [1, 2, 3]:
            p = producers[pid]
            f.write(f"## Producer {pid}\n")
            f.write(f">start time: {p['start']:.3f} ms\n")
            f.write(f">mean delay edges / source: {p['delay']:.3f} ms\n")
            f.write(f">overruns: {p['overruns']}\n\n")

        for cid in [1, 2]:
            c = consumers[cid]
            f.write(f"## Consumer {cid}\n")
            f.write(f">start time: {c['start']:.3f} ms\n")
            f.write(f">mean delay 2oo3 edges / source: {c['delay']:.3f} ms\n")
            f.write(f">overruns: {c['overruns']}\n")
            f.write(f">status @ 1s: {c['status_1s']}\n")
            f.write(f">Moment of failure: {c['fail_time']:.3f} ms\n")
            f.write(f">New status: {c['new_status']}\n\n")

        f.write("## Publisher 1\n")
        f.write(f">start time: {pub_start:.3f} ms\n")
        f.write(f">mean delay edges / source (publisher output): {pub_delay:.3f} ms\n")
        f.write(f">overruns: {pub_overruns}\n\n")

        f.write("## PLC Failure / Recovery\n")
        f.write(f">fault time (raw/fallback): {fault_time:.3f} ms\n")
        f.write(f">switch time (C2 ACTIVE): {switch_time:.3f} ms\n")
        f.write(f">switch delay (fault -> switch): {switch_delay:.3f} ms\n")
        f.write(f">recovery (switch -> first publish): {recovery_switch_to_pub:.3f} ms\n")
        f.write(f">recovery (fault -> first publish): {recovery_fault_to_pub:.3f} ms\n")
        f.write(f">diagnostic edge-to-edge (src edge -> pub edge): {complete_delay_edge2edge:.3f} ms\n")

    # ========== SUMMARY CSV ==========
    summary = {
        "freq": freq,
        "cycle_rate": cycle_rate,
        "p1_start": producers[1]["start"],
        "p2_start": producers[2]["start"],
        "p3_start": producers[3]["start"],
        "c1_start": consumers[1]["start"],
        "c2_start": consumers[2]["start"],
        "p1_delay": producers[1]["delay"],
        "p2_delay": producers[2]["delay"],
        "p3_delay": producers[3]["delay"],
        "c1_delay": consumers[1]["delay"],
        "c2_delay": consumers[2]["delay"],
        "pub_delay": pub_delay,
        "fault_time": fault_time,
        "switch_time": switch_time,
        "switch_delay": switch_delay,
        "recovery_switch_to_pub": recovery_switch_to_pub,
        "recovery_fault_to_pub": recovery_fault_to_pub,
        "edge2edge_delay": complete_delay_edge2edge
    }

    file = "reports.csv"
    df_res = pd.read_csv(file) if os.path.exists(file) else pd.DataFrame()
    df_res = pd.concat([df_res, pd.DataFrame([summary])], ignore_index=True)
    df_res.to_csv(file, index=False)

    print("REDUNDANCY10 report generated.")