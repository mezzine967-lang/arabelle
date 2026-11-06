import numpy as np
import csv
import random
import heapq

from scipy.signal       import square
from graphical_report10 import draw
from generate_report10  import report

# ============================================================
# PARAMETERS
# ============================================================

SQW_F           = 1
SQW_MN          = 0
SQW_MX          = 1
SQW_CR          = 50
SOURCE_CYCLE    = 0.001

DT              = 0.001
T_SIM           = 10
HB_TIMEOUT      = 0.050
STALL_LIMIT     = 2
TIME_FAULT      = 8

PRODUCER_CYCLE        = 0.010
PRODUCER_WORK_DELAY   = 0.004
PRODUCER_JITTER_MAX   = 0.001

CONSUMER_CYCLE        = 0.020
CONSUMER_WORK_DELAY   = 0.010
CONSUMER_JITTER_MAX   = 0.001

PUBLISHER_CYCLE       = 0.010
PUBLISHER_WORK_DELAY  = 0.004    
PUBLISHER_JITTER_MAX  = 0.001

# ============================================================
# SIGNAL
# ============================================================

def square_signal(t):
    return ((SQW_MX - SQW_MN) / 2) * (square(2 * np.pi * SQW_F * t, duty=SQW_CR / 100) + 1)

# ============================================================
# VOTER Logic
# ============================================================

def voter(a, b, c):
    return (a + b + c) >= 2

# ============================================================
# SCHEDULER (original + internal event queue)
# ============================================================

class Task:
    def __init__(self, period, phase, callback):
        self.period = period
        self.next_run = phase
        self.callback = callback

    def tick(self, sim_time):
        if sim_time >= self.next_run:
            self.callback(self.next_run)
            self.next_run += self.period

# ---- Internal event queue (for intra-cycle delays) ----

event_queue = []
event_counter = 0

def schedule_event(time, callback):
    global event_counter
    event_counter += 1
    heapq.heappush(event_queue, (time, event_counter, callback))

def run_events(sim_time):
    while event_queue and event_queue[0][0] <= sim_time:
        _, _, cb = heapq.heappop(event_queue)
        cb(sim_time)

# ============================================================
# SHARED STATE
# ============================================================

source_value     = 0
shared_prod      = {1: 0, 2: 0, 3: 0}
plc_image        = {1: {}, 2: {}}
failure_plc      = 0
consumer_state   = {1: "STOP", 2: "STOP"}
consumer_vote    = {1: 0, 2: 0}
consumer_hb      = {1: {"value": 0, "time": None},2: {"value": 0, "time": None}}
last_seen_hb     = {1: None, 2: None}
hb_stall_cnt     = {1: 0, 2: 0}

seed_init        = 123
random.seed(seed_init)
INIT_TIME        = {1: random.uniform(0.6, 0.7),2: random.uniform(0.6, 0.7)}

published_value  = 0

overrun_prod     = {1: False, 2: False, 3: False}
overrun_cons     = {1: False, 2: False}
overrun_pub      = False

start_flags      = {"prod1": False, "prod2": False, "prod3": False,"cons1": False, "cons2": False, "pub": False}
start_pulse      = {"prod1": 0, "prod2": 0, "prod3": 0,"cons1": 0, "cons2": 0, "pub": 0}

publisher_output = []
log_all          = []

prod_slot        = {1: 0, 2: 0, 3: 0}   # tampon producteur (valeur capturée dans le slot)
cons_slot_vote   = {1: 0, 2: 0}         # tampon consommateur (vote calculé dans le slot)
cons_slot_active = {1: False, 2: False} # tampon consommateur (état ACTIVE dans le slot)
pub_slot_value   = None                 # tampon publisher (snapshot à émettre en fin de slot)

# ============================================================
# TASKS
# ============================================================

def source_task(t):
    global source_value
    source_value = square_signal(t)

# ------------------------------------------------------------
# PRODUCER (work in slot, publish at end of period)
# ------------------------------------------------------------

def producer_task(pid):
    def task(t0):
        global start_flags, start_pulse, overrun_prod, prod_slot, shared_prod

        key = f"prod{pid}"
        if not start_flags[key]:
            start_flags[key] = True
            start_pulse[key] = 1

        def work_phase(t):
            prod_slot[pid] = source_value

        def publish_phase(t):
            shared_prod[pid] = prod_slot[pid]

        jitter = random.uniform(-PRODUCER_JITTER_MAX, PRODUCER_JITTER_MAX)
        schedule_event(t0 + PRODUCER_WORK_DELAY + jitter, work_phase)
        schedule_event(t0 + PRODUCER_CYCLE, publish_phase)

    return task

# ------------------------------------------------------------
# CONSUMER (work in slot, publish at end of period)
# ------------------------------------------------------------

def consumer_task(cid):
    def task(t0):
        global start_flags, start_pulse
        global plc_image, consumer_hb, last_seen_hb, hb_stall_cnt
        global consumer_state, cons_slot_vote, cons_slot_active, published_value, failure_plc

        key = f"cons{cid}"
        if not start_flags[key]:
            start_flags[key] = True
            start_pulse[key] = 1
        # ---------------------------------------------------------------------
        def work_phase(t):

            if t >= TIME_FAULT:
                if cid == 1:
                    failure_plc = 1
                    cons_slot_active[cid] = False
                    return

            plc_image[cid] = shared_prod.copy()

            consumer_hb[cid]["value"] += 1
            consumer_hb[cid]["time"] = t

            if t < INIT_TIME[cid]:
                consumer_state[cid] = "INIT"
                cons_slot_active[cid] = False
                return

            other = 2 if cid == 1 else 1
            hb_other = consumer_hb[other]
            
            if hb_other["time"] is not None:
                if last_seen_hb[other] == hb_other["value"]:
                    hb_stall_cnt[other] += 1
                else:
                    hb_stall_cnt[other] = 0
                    last_seen_hb[other] = hb_other["value"]
                    
            # -----------------------------------------------------------------
            def unhealthy(c):
                hb = consumer_hb[c]
                if hb["time"] is None:
                    return True
                timeout = (t - hb["time"]) > HB_TIMEOUT
                stall = hb_stall_cnt[c] >= STALL_LIMIT
                return timeout and stall
            # -----------------------------------------------------------------

            if t <= max(INIT_TIME.values()):
                consumer_state[1] = "INIT"
                consumer_state[2] = "INIT"
                cons_slot_active[cid] = False
                return
            else:
                if not unhealthy(1):
                    consumer_state[1] = "ACTIVE"
                    consumer_state[2] = "STANDBY"
                else:
                    consumer_state[1] = "FAILED"
                    consumer_state[2] = "ACTIVE"

            v = voter(plc_image[cid][1], plc_image[cid][2], plc_image[cid][3])
            cons_slot_vote[cid] = int(v)
            consumer_vote[cid] = int(v)  
            cons_slot_active[cid] = (consumer_state[cid] == "ACTIVE")
        # ---------------------------------------------------------------------
        def publish_phase(t):
            global published_value
            if cons_slot_active[cid]:
                published_value = cons_slot_vote[cid]
        # ---------------------------------------------------------------------
        jitter = random.uniform(-CONSUMER_JITTER_MAX, CONSUMER_JITTER_MAX)
        schedule_event(t0 + CONSUMER_WORK_DELAY + jitter, work_phase)
        schedule_event(t0 + CONSUMER_CYCLE, publish_phase)

    return task


# ------------------------------------------------------------
# PUBLISHER (work in slot, publish at end of period)
# ------------------------------------------------------------

def publisher_task(t0):
    global start_flags, start_pulse
    global pub_slot_value, publisher_output, published_value

    if not start_flags["pub"]:
        start_flags["pub"] = True
        start_pulse["pub"] = 1

    def work_phase(t):
        global pub_slot_value, published_value
        pub_slot_value = published_value

    def publish_phase(t):
        global publisher_output, pub_slot_value
        plc_value = pub_slot_value
        publisher_output.append((t, plc_value))

    jitter = random.uniform(-PUBLISHER_JITTER_MAX, PUBLISHER_JITTER_MAX)
    schedule_event(t0 + PUBLISHER_WORK_DELAY + jitter, work_phase)
    schedule_event(t0 + PUBLISHER_CYCLE, publish_phase)


# ------------------------------------------------------------
# LOGGER
# ------------------------------------------------------------

def logger_task(t):
    pub_val = publisher_output[-1][1] if publisher_output else None
    log_all.append((
        int(t*1000),
        source_value,
        shared_prod[1],
        shared_prod[2],
        shared_prod[3],
        consumer_state[1],
        consumer_state[2],
        consumer_vote[1],
        consumer_vote[2],
        published_value,
        failure_plc,
        pub_val,
        start_pulse["prod1"],
        start_pulse["prod2"],
        start_pulse["prod3"],
        start_pulse["cons1"],
        start_pulse["cons2"],
        start_pulse["pub"]
    ))
    for k in start_pulse:
        start_pulse[k] = 0


# ============================================================
# PHASES
# ============================================================
random.seed()
phase_prod = {i: random.uniform(0, 0.5) for i in [1, 2, 3]}
phase_cons = {i: random.uniform(0, 0.5) for i in [1, 2]}
phase_pub  = random.uniform(0, 0.5)

# ============================================================
# BUILD TASK LIST
# ============================================================

tasks = []

tasks.append(Task(SOURCE_CYCLE, 0, source_task))

for i in [1, 2, 3]:
    tasks.append(Task(PRODUCER_CYCLE, phase_prod[i], producer_task(i)))

for i in [1, 2]:
    tasks.append(Task(CONSUMER_CYCLE, phase_cons[i], consumer_task(i)))

tasks.append(Task(PRODUCER_CYCLE, phase_pub, publisher_task))

tasks.append(Task(DT, 0, logger_task))

# ============================================================
# RUN SIMULATION
# ============================================================

sim_time = 0.0
while sim_time < T_SIM:

    for task in tasks:
        task.tick(sim_time)

    run_events(sim_time)

    sim_time += DT

# ============================================================
# WRITE CSV
# ============================================================

with open("simulation10.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow([
        "t_ms",
        "source",
        "prod1","prod2","prod3",
        "cons1_state","cons2_state",
        "cons1_vote","cons2_vote",
        "published",
        "failure_plc",
        "pub_output",
        "start_p1","start_p2","start_p3",
        "start_c1","start_c2",
        "start_pub"
    ])
    w.writerows(log_all)

print("Simulation complete. Single deterministic log generated.")
#report()
draw()