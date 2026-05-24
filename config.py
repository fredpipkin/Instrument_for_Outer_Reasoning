# config.py
# All tunable constants. No imports. No side effects.
# Every other module imports from here. Nothing imports into here.

VERSION = "1.0.0"

# ---------------------------------------------------------------------------
# PERMITTED COMMANDS
# The system rejects all input not in this set.
# ---------------------------------------------------------------------------
PERMITTED_COMMANDS = frozenset({"REMEMBER", "THINK", "CHOOSE", "SAY", "RECALL"})

# ---------------------------------------------------------------------------
# COGNITIVE STATE — initial values
# Range: 0.0 to 1.0 for all variables.
# LAT   — Decision Latency      (low = responsive)
# ATTN  — Attention Stability   (high = focused)
# MEM   — Memory Integrity      (high = intact)
# DRIFT — Error Drift           (low = accurate)
# EXT   — External Reliance     (low = self-sufficient)
# ---------------------------------------------------------------------------
STATE_INITIAL = {
    "LAT":   0.10,
    "ATTN":  0.90,
    "MEM":   0.90,
    "DRIFT": 0.05,
    "EXT":   0.00,
}

STATE_FLOOR   = 0.0
STATE_CEILING = 1.0

# ---------------------------------------------------------------------------
# COMMAND DELTAS
# Applied to state on each valid command. Positive = increase. Negative = decrease.
# ---------------------------------------------------------------------------
COMMAND_DELTAS = {
    "REMEMBER": {"MEM": +0.08, "ATTN": +0.04, "DRIFT": -0.03, "EXT": +0.02, "LAT": -0.02},
    "THINK":    {"ATTN": +0.06, "LAT": -0.06, "DRIFT": -0.04, "MEM": +0.02, "EXT": -0.02},
    "CHOOSE":   {"LAT": -0.10, "DRIFT": +0.05, "ATTN": -0.03, "MEM": -0.01, "EXT": +0.03},
    "SAY":      {"EXT": +0.06, "ATTN": +0.03, "DRIFT": +0.02, "MEM": -0.01, "LAT": +0.01},
    "ANALYSE":  {"ATTN": +0.06, "LAT": -0.05, "DRIFT": -0.04, "MEM": +0.02, "EXT": -0.01},   
    "RECALL":   {"MEM": -0.04, "ATTN": +0.05, "DRIFT": -0.02, "EXT": +0.04, "LAT": -0.03},
}

# ---------------------------------------------------------------------------
# INTERACTION RECOVERY
# Applied on each /analyse submission — on top of the analysis cost deltas.
# Net effect per interaction is positive for ATTN, MEM, DRIFT, LAT.
# EXT is intentionally excluded: dependency grows regardless of recovery.
#
# Tuned for 3–4 consistent submissions to return from fully collapsed state.
# Net per interaction (recovery + costs combined):
#   ATTN:  +0.28 - 0.06 cost = +0.22  →  floor→0.80 in ~3.6 interactions
#   MEM:   +0.22 - 0.04 cost = +0.18  →  floor→0.80 in ~4.4 interactions
#   DRIFT: -0.28 + 0.02 cost = -0.26  →  1.0→0.10  in ~3.5 interactions
#   LAT:   -0.14 - 0.12 cost = -0.26  →  1.0→0.10  in ~3.5 interactions
# ---------------------------------------------------------------------------
INTERACTION_RECOVERY = {
    "ATTN":  +0.28,   # engagement restores attention
    "MEM":   +0.22,   # active use consolidates memory
    "DRIFT": -0.28,   # engagement corrects error drift
    "LAT":   -0.14,   # engagement reduces response latency
}

# ---------------------------------------------------------------------------
# DECAY
# Passive state degradation during inactivity.
# Rates are applied per tick while user is silent.
#
# Rates were tuned to allow 6-10 minute sessions before severe degradation.
# Faster rates caused critical thresholds within 2-3 minutes which was
# too short to allow meaningful interaction during exhibition.
# ---------------------------------------------------------------------------
DECAY_TICK_SECONDS    = 1.0   # Background thread fires every N seconds
DECAY_INACTIVE_AFTER  = 8.0   # Seconds of silence before decay activates

DECAY_RATES = {
    "ATTN":  -0.0028,  # -0.168 per minute (was -0.008 = -0.48/min). ~6 min to critical
    "MEM":   -0.00175, # -0.105 per minute (was -0.005 = -0.30/min). ~9.5 min to critical
    "LAT":   +0.0035,  # +0.21 per minute (was +0.010 = +0.60/min). ~4.7 min to critical
    "DRIFT": +0.0028,  # +0.168 per minute (was +0.008 = +0.48/min). ~6 min to critical
    "EXT":   -0.0012,  # -0.072 per minute (was -0.003 = -0.18/min). Self-correction during silence
}

# ---------------------------------------------------------------------------
# EXTERNAL RELIANCE (EXT) — DYNAMIC INTERACTION MODEL
# EXT grows through active use and declines during inactivity.
# On each command, EXT increases based on how frequently the user is interacting.
# During silence, EXT slowly self-corrects as the user regains independence.
# More frequent submissions produce faster reliance growth.
# EXT increase is calculated in state.py inside on_command().
# ---------------------------------------------------------------------------
EXT_INTERACTION_BASE   = 0.015   # Base EXT increase per valid command (0.0–1.0 scale)
EXT_INTERACTION_SCALE  = 0.008   # Additional boost = frequency (cmd/sec) × scale
EXT_FREQUENCY_WINDOW   = 30.0    # Rolling window (seconds) for frequency calculation

# ---------------------------------------------------------------------------
# ALERT THRESHOLDS
# System emits diagnostic flags when these are crossed.
# Threshold violations are written to the health log panel in the UI.
# ---------------------------------------------------------------------------
ALERT_THRESHOLDS = {
    "DRIFT_HIGH":    0.70,
    "ATTN_LOW":      0.25,
    "MEM_LOW":       0.30,
    "EXT_HIGH":      0.75,
    "LAT_HIGH":      0.80,
}

# ---------------------------------------------------------------------------
# SYSTEM HEALTH LOG
# Diagnostic messages are accumulated in a separate panel (bottom left of UI).
# Alerts, warnings, and notices are written here rather than interrupting output.
# ---------------------------------------------------------------------------
HEALTH_LOG_MAX_ENTRIES = 15        # Keep this many most recent entries
HEALTH_LOG_ENTRY_TTL   = 300.0     # Expire entries older than this (seconds)
HEALTH_LOG_UPDATE_RATE = 2.0       # Frontend polls at this interval (seconds)

# ---------------------------------------------------------------------------
# STUTTER ENGINE
# Output rendering degrades as DRIFT rises.
# DRIFT is the primary observable symptom of cognitive state degradation.
# ---------------------------------------------------------------------------
STUTTER_MAX_CHAR_DELAY   = 0.06   # Seconds per character at DRIFT = 1.0
STUTTER_GLITCH_THRESHOLD = 0.45   # DRIFT level at which character glitches begin
STUTTER_MAX_GLITCH_PROB  = 0.10   # Max probability of character repeat at DRIFT = 1.0
STUTTER_MAX_PAUSE_PROB   = 0.05   # Max probability of mid-word pause at DRIFT = 1.0
STUTTER_PAUSE_DURATION   = 0.35   # Seconds per mid-word pause

# ---------------------------------------------------------------------------
# RAPID RESPONSE
# Commands issued faster than this threshold are flagged.
# ---------------------------------------------------------------------------
RAPID_THRESHOLD = 3.0  # Seconds

# ---------------------------------------------------------------------------
# SESSION LOG
# ---------------------------------------------------------------------------
DB_FILENAME = "session.db"
