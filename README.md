# Instrument for Outer Reasoning

A real-time cognitive state interface built with Python, Flask, and vanilla JavaScript. The system models five cognitive parameters that degrade passively over time and recover through user interaction. It was developed as an interactive installation piece examining the relationship between human reasoning and computational dependency.

---

## Overview

The user submits a problem, decision, or scenario into a text input. The system processes it through a four-stage reasoning pipeline — tokenisation, complexity scoring, scenario classification, and recommendation generation — and returns a structured analysis. Every submission applies costs to the cognitive state and recovery deltas that partially restore it. Leaving the system idle causes the parameters to decay, which degrades the visual output, audio output, and recommendation quality until interaction resumes.

---

## Cognitive Parameters

| Parameter | ID | Healthy | Description |
|---|---|---|---|
| Decision Latency | LAT | Low | Speed of committing to an output. High values indicate stalling. |
| Attention Stability | ATTN | High | Coherence of processing. Low values produce fragmented analysis. |
| Memory Integrity | MEM | High | Contextual continuity across interactions. Low values lose prior context. |
| Error Drift | DRIFT | Low | Accumulated deviation from reliable reasoning. High values corrupt output. |
| External Reliance | EXT | Low | Dependency on user input. Grows with interaction frequency. |

All parameters operate between 0.0 and 1.0. A composite health score is computed as a weighted average and drives output quality, audio integrity, and visual degradation across the interface.

---

## Stack

- **Backend** — Python 3, Flask
- **Frontend** — Vanilla JavaScript, Canvas API, Web Audio API
- **Rendering** — CSS Grid layout, Canvas 2D for gauges, time-series traces, and 3D brain render
- **Audio** — Procedural phrase generation via Web Audio API. Phrase coherence reflects system health.
- **State** — Five float variables managed by a central engine. Updated on interaction and via a background decay thread.
- **Persistence** — Session log written to SQLite via `session.db`

---

## File Structure

```
outer_reasoning/
├── server.py        # Flask server, route handlers, state update logic
├── state.py         # Cognitive state engine, health log, alert thresholds
├── reasoning.py     # Four-stage reasoning pipeline, cost model, recommendations
├── decay.py         # Background decay thread, per-tick state updates
├── config.py        # All tunable constants — decay rates, thresholds, recovery values
├── logger.py        # Session logging to SQLite
├── inference_stub.py# Reserved for future model integration
├── flowchart.html   # User flow diagram (standalone, open in browser)
└── static/
    └── index.html   # Entire frontend — markup, styles, and scripts in one file
```

---

## Installation

**Requirements**
- Python 3.7+
- pip

**Install dependencies**
```bash
pip install flask
```

**Run**
```bash
cd outer_reasoning
python server.py
```

Open a browser and go to `http://localhost:5000`

---

## Running on Raspberry Pi

```bash
# Copy files from USB
cp -r /media/pi/YOUR_DRIVE/outer_reasoning ~/outer_reasoning

# Install Flask
sudo apt install python3-flask

# Run
cd ~/outer_reasoning
python3 server.py
```

To access from another device on the same network, change the host in `server.py`:
```python
app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
```
Then navigate to `http://[PI_IP_ADDRESS]:5000` from any device on the same network. Find the Pi's IP with `hostname -I`.

---

## Configuration

All system behaviour is controlled through `config.py`. No other file needs to be edited to adjust timing, thresholds, or recovery rates.

| Constant | Description |
|---|---|
| `STATE_INITIAL` | Starting values for all five parameters |
| `DECAY_RATES` | Per-second passive degradation rates during inactivity |
| `DECAY_INACTIVE_AFTER` | Seconds of silence before decay activates (default 8s) |
| `INTERACTION_RECOVERY` | Recovery deltas applied on each submission |
| `ALERT_THRESHOLDS` | Values at which health log warnings are triggered |
| `EXT_INTERACTION_BASE` | Base EXT increase per submission |
| `EXT_FREQUENCY_WINDOW` | Rolling window in seconds for frequency calculation |

---

## Reasoning Pipeline

Each submission is processed in four sequential stages:

1. **Tokenise** — input is split into lowercase tokens and matched against keyword lexicons
2. **Score** — six complexity dimensions are scored between 0.0 and 1.0
3. **Classify** — the dominant dimension determines the scenario type
4. **Recommend** — between one and three ranked recommendations are generated, gated by current health

Each stage applies a fixed cost to the cognitive parameters. Recovery deltas are applied after costs, tuned so that three to four consistent submissions restore a fully degraded system.

---

## License

MIT
