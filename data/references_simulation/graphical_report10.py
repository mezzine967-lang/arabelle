import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator, AutoMinorLocator

def draw():

    # ==========================================================
    # LOAD DATA
    # ==========================================================

    df = pd.read_csv("simulation10.csv")

    # ==========================================================
    # STATE MAPPING
    # ==========================================================

    STATE_MAP = {"STOP":-1,"FAILED":0,"INIT": 1, "STANDBY": 2, "ACTIVE": 3}
    df["cons1_state_val"] = df["cons1_state"].map(STATE_MAP)
    df["cons2_state_val"] = df["cons2_state"].map(STATE_MAP)

    # ==========================================================
    # START DETECTION
    # ==========================================================

    def first_change(col):
        diff = df[col].diff().fillna(0)
        idx = diff.ne(0)
        if idx.any():
            return df.loc[idx, "t_ms"].iloc[0]
        return None
    
    def first_specific_change(col, from_state, to_state):
        prev = df[col].shift(1)
        curr = df[col]
        
        mask = (prev == from_state) & (curr == to_state)
        
        if mask.any():
            return df.loc[mask, "t_ms"].iloc[0]
        return None
    
    start_prod1 = first_change("prod1")
    start_prod2 = first_change("prod2")
    start_prod3 = first_change("prod3")
    start_cons1 = first_specific_change("cons1_state","STOP","INIT")
    start_cons2 = first_specific_change("cons2_state","STOP","INIT")
    start_pub   = first_change("published")
    start_fail  = first_change("failure_plc")

    # ==========================================================
    # DELAY COMPUTATION
    # ==========================================================

    def detect_edges(df, column):
        tmp = df.copy()
        tmp["prev"] = tmp[column].shift(1)
        return tmp[tmp[column] != tmp["prev"]][["t_ms", column]]

    source_edges = detect_edges(df, "source")
    edges_c1 = detect_edges(df, "cons1_vote")
    edges_c2 = detect_edges(df, "cons2_vote")

    def compute_delay(consumer_edges, source_edges, colname):

        delays = []

        for _, row in consumer_edges.iterrows():

            t_cons = row["t_ms"]
            val = row[colname]

            src_match = source_edges[
                (source_edges["source"] == val) &
                (source_edges["t_ms"] <= t_cons)
            ]

            if not src_match.empty:
                t_src = src_match.iloc[-1]["t_ms"]
                delays.append((t_cons, t_cons - t_src))

        return pd.DataFrame(delays, columns=["t_ms", "delay_ms"])

    delay_c1 = compute_delay(edges_c1, source_edges, "cons1_vote")
    delay_c2 = compute_delay(edges_c2, source_edges, "cons2_vote")

    # ==========================================================
    # HELPER: DRAW START ARROW
    # ==========================================================

    def draw_start_arrow(ax, x, label):
        if x is None:
            return
        ymin, ymax = ax.get_ylim()
        ax.annotate(
            label,
            xy=(x, ymin),
            xycoords='data',
            xytext=(x, ymin - (ymax - ymin)*0.25),
            arrowprops=dict(arrowstyle="->"),
            ha="center",
            fontsize=8
        )

    # ==========================================================
    # FIGURE (9 plots now)
    # ==========================================================

    fig, axs = plt.subplots(
        8, 1,
        figsize=(12, 12),
        sharex=True,
        gridspec_kw={'height_ratios': [1,1,1,1,1,2,2,1]}
    )

    # ----------------------------------------------------------
    # 1) SOURCE
    # ----------------------------------------------------------

    axs[0].step(df["t_ms"], df["source"], where="post", linewidth=2, color="black")
    axs[0].set_title("Signal Source")
    axs[0].grid(True)

    # ----------------------------------------------------------
    # 2–4) PRODUCERS
    # ----------------------------------------------------------

    axs[1].step(df["t_ms"], df["prod1"], where="post", linewidth=2)
    axs[1].set_title("Producer 1")
    axs[1].grid(True)

    axs[2].step(df["t_ms"], df["prod2"], where="post", linewidth=2)
    axs[2].set_title("Producer 2")
    axs[2].grid(True)

    axs[3].step(df["t_ms"], df["prod3"], where="post", linewidth=2)
    axs[3].set_title("Producer 3")
    axs[3].grid(True)

    # Draw producer start arrows
    draw_start_arrow(axs[1], start_prod1, "Start P1")
    draw_start_arrow(axs[2], start_prod2, "Start P2")
    draw_start_arrow(axs[3], start_prod3, "Start P3")

    # ----------------------------------------------------------
    # 5) CONSUMER VOTES
    # ----------------------------------------------------------

    axs[4].step(df["t_ms"], df["cons1_vote"],where="post", linewidth=2, label="Cons1")
    axs[4].step(df["t_ms"], df["cons2_vote"],where="post", linewidth=2, label="Cons2")
    axs[4].set_title("Vote 2oo3 from consumers")
    axs[4].legend()
    axs[4].grid(True)



    # ----------------------------------------------------------
    # 6) DELAYS
    # ----------------------------------------------------------

    if not delay_c1.empty:
        axs[5].step(delay_c1["t_ms"], delay_c1["delay_ms"],where="post", linewidth=2, label="Cons1")

    if not delay_c2.empty:
        axs[5].step(delay_c2["t_ms"], delay_c2["delay_ms"],where="post", linewidth=2, label="Cons2")

    axs[5].set_title("delay consumers vs source (ms)")
    axs[5].set_ylim(0, 60)
    axs[5].legend()
    axs[5].grid(True)

    # ----------------------------------------------------------
    # 7) CONSUMER STATES
    # ----------------------------------------------------------

    axs[6].step(df["t_ms"], df["cons1_state_val"],where="post", linewidth=2, label="Cons1")
    axs[6].step(df["t_ms"], df["cons2_state_val"],where="post", linewidth=2, label="Cons2")
    axs[6].set_yticks([-1,0,1,2,3])
    axs[6].set_yticklabels(["STOP","FAILED","INIT","STANDBY","ACTIVE"])
    axs[6].set_title("Consumers Status")
    axs[6].legend()
    axs[6].grid(True)

    draw_start_arrow(axs[6], start_fail , "Failure PLC1")
    draw_start_arrow(axs[6], start_cons1, "Start C1")
    draw_start_arrow(axs[6], start_cons2, "Start C2")

    # ----------------------------------------------------------
    # 8) PUBLISHER (dedicated)
    # ----------------------------------------------------------

    axs[7].step(df["t_ms"], df["pub_output"],where="post", linewidth=2)
    axs[7].set_title("Publisher (brut)")
    axs[7].grid(True)

    for ax in axs:
        ax.xaxis.set_major_locator(MultipleLocator(1000))
        ax.xaxis.set_minor_locator(MultipleLocator(250))
        ax.grid(which='major', color='#505050', linestyle='--', linewidth=0.8)
        ax.grid(which='minor', color='#505050', linestyle=':', linewidth=0.5)

    # ----------------------------------------------------------
    # GLOBAL
    # ----------------------------------------------------------

    axs[-1].set_xlim(left=0)
    plt.tight_layout()
    plt.show()
