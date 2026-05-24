# server.py
# Flask HTTP server.
# Bridges the cognitive state engine and reasoning module to the visual frontend.
# Serves the instrument panel at http://localhost:5000
#
# Run from inside outer_reasoning/:
#   python server.py
#
# Endpoints:
#   GET  /           → instrument panel HTML
#   POST /analyse    → run reasoning on input, update state, return result
#   GET  /state      → current cognitive state (polled by frontend every 1s)
#   GET  /health_log → system health log (polled by frontend every 2-3s)
#   POST /reset      → reset cognitive state to initial values

import os
import time
import threading
from flask import Flask, jsonify, request, send_from_directory

from state    import CognitiveStateEngine
from decay    import DecayEngine
from logger   import SessionLogger
from reasoning import analyse
from config   import STATE_INITIAL, STATE_FLOOR, STATE_CEILING, INTERACTION_RECOVERY

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__, static_folder="static")
app.config["JSON_SORT_KEYS"] = False

# Global engine instances — one per server process
engine = CognitiveStateEngine()
logger = SessionLogger()
logger.begin()

# State history for time-series visualisation (last 120 ticks)
_HISTORY_LENGTH = 120
state_history: list = []
history_lock = threading.Lock()

def _record_history():
    snap = engine.snapshot()
    entry = {
        "ts":    time.time(),
        "LAT":   snap["LAT"],
        "ATTN":  snap["ATTN"],
        "MEM":   snap["MEM"],
        "DRIFT": snap["DRIFT"],
        "EXT":   snap["EXT"],
    }
    with history_lock:
        state_history.append(entry)
        if len(state_history) > _HISTORY_LENGTH:
            state_history.pop(0)

def _decay_tick():
    """Called by DecayEngine on each tick — records history after decay."""
    _record_history()

decay = DecayEngine(engine=engine, on_tick=_decay_tick)
decay.start()

# Seed initial history
_record_history()

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/state", methods=["GET"])
def get_state():
    """
    Returns current cognitive state + recent history.
    Polled by the frontend every 1000ms.
    """
    snap = engine.snapshot()
    with history_lock:
        hist = list(state_history)
    return jsonify({
        "state":   snap,
        "history": hist,
    })


@app.route("/health_log", methods=["GET"])
def get_health_log():
    """
    Returns system health log (diagnostic events).
    Polled by the frontend every 2-3 seconds.
    Health events appear in a dedicated panel rather than interrupting output.
    """
    health_log = engine.get_health_log()
    return jsonify({
        "health_log": health_log,
    })


@app.route("/analyse", methods=["POST"])
def post_analyse():
    """
    Receives user input, runs the reasoning pipeline, and updates cognitive state.
    Analysis costs and recovery deltas are applied before returning the result.
    """
    body = request.get_json(silent=True) or {}
    text = (body.get("text") or "").strip()

    if not text:
        return jsonify({"error": "EMPTY_INPUT"}), 400

    # Snapshot state before analysis (for delta display)
    pre_snap = engine.snapshot()

    # Run procedural analysis — pure function, no state mutation
    result = analyse(text, pre_snap)

    # Apply state costs from each analysis step
    for var, delta in result["state_deltas"].items():
        current = getattr(engine, var)
        new_val = max(STATE_FLOOR, min(STATE_CEILING, current + delta))
        setattr(engine, var, new_val)

    # Apply interaction recovery — engagement stabilises the system.
    # Net effect is positive for ATTN, MEM, DRIFT, LAT.
    # EXT is excluded: dependency accumulates regardless.
    for var, delta in INTERACTION_RECOVERY.items():
        current = getattr(engine, var)
        new_val = max(STATE_FLOOR, min(STATE_CEILING, current + delta))
        setattr(engine, var, new_val)

    # Update command timing and EXT frequency tracking
    engine.on_command("ANALYSE")
    
    post_snap = engine.snapshot()

    # Write any reasoning warnings to the health log
    if result.get("warnings"):
        for warning in result["warnings"]:
            engine.log_health_event("WARNING", warning)
    
    # Record history point immediately after analysis
    _record_history()

    return jsonify({
        "input":      text,
        "result":     result,
        "state_pre":  pre_snap,
        "state_post": post_snap,
    })


@app.route("/reset", methods=["POST"])
def reset_state():
    """Resets cognitive state to initial values. Does not affect history log."""
    for var, val in STATE_INITIAL.items():
        setattr(engine, var, val)
    engine.alerts      = []
    engine.rapid_flag  = False
    engine.health_log  = []  # Clear health log on reset
    engine.last_command_time = time.time()
    engine._command_times = []  # Clear command timestamp history
    _record_history()
    return jsonify({"status": "RESET", "state": engine.snapshot()})


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("\n  INSTRUMENT FOR OUTER REASONING — Visual Interface")
    print("  ─────────────────────────────────────────────────")
    print("  Open browser at: http://localhost:5000")
    print("  Press Ctrl+C to terminate.\n")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True)
