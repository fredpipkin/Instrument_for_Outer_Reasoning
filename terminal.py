# terminal.py
# Terminal I/O and stutter engine.
#
# The stutter engine is the primary observable output mechanic.
# As DRIFT rises, all printed text slows and corrupts.
#
# Degradation scale:
#   DRIFT 0.00 – 0.45  Instant, clean output
#   DRIFT 0.45 – 0.65  Per-character delay, occasional repeats
#   DRIFT 0.65 – 0.80  Noticeable slowdown, mid-word freezes
#   DRIFT 0.80 – 1.00  Severe delay, structural character corruption
#
# stutter_print() — sole output path for all cognitive-level responses
# instant_print() — system messages only (boot banner, boundary rejections)

import sys
import time
import random
from datetime import datetime
from typing import Callable

from config import (
    VERSION,
    STUTTER_MAX_CHAR_DELAY,
    STUTTER_GLITCH_THRESHOLD,
    STUTTER_MAX_GLITCH_PROB,
    STUTTER_MAX_PAUSE_PROB,
    STUTTER_PAUSE_DURATION,
)
from commands import CommandParser


# ---------------------------------------------------------------------------
# Output primitives
# ---------------------------------------------------------------------------

def instant_print(text: str) -> None:
    """Unmodified stdout. Used for boot banner and boundary messages only."""
    print(text, flush=True)


def stutter_print(text: str, drift: float) -> None:
    """
    Renders text with drift-proportional degradation.
    [STUTTER ENGINE — keyed directly to DRIFT from CognitiveStateEngine]

    Three mechanics applied per character:
    1. DELAY  — linear from 0ms at drift=0 to STUTTER_MAX_CHAR_DELAY at drift=1
    2. REPEAT — above GLITCH_THRESHOLD, chars randomly double (stutter)
    3. PAUSE  — above GLITCH_THRESHOLD, random mid-word freeze
    """
    char_delay = drift * STUTTER_MAX_CHAR_DELAY

    for char in text:
        if char_delay > 0:
            time.sleep(char_delay)

        # Repeat glitch
        if drift > STUTTER_GLITCH_THRESHOLD and char not in ("\n", " "):
            scale = (drift - STUTTER_GLITCH_THRESHOLD) / (1.0 - STUTTER_GLITCH_THRESHOLD)
            if random.random() < STUTTER_MAX_GLITCH_PROB * scale:
                sys.stdout.write(char)
                sys.stdout.flush()
                time.sleep(char_delay * 0.8)

        # Mid-word pause
        if drift > STUTTER_GLITCH_THRESHOLD and char not in ("\n", " ", "─", "│", "┌", "└"):
            scale = (drift - STUTTER_GLITCH_THRESHOLD) / (1.0 - STUTTER_GLITCH_THRESHOLD)
            if random.random() < STUTTER_MAX_PAUSE_PROB * scale:
                sys.stdout.flush()
                time.sleep(STUTTER_PAUSE_DURATION * drift)

        sys.stdout.write(char)
        sys.stdout.flush()

    if not text.endswith("\n"):
        sys.stdout.write("\n")
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# Output formatters — clinical, procedural, no freeform language
# ---------------------------------------------------------------------------

def _bar(value: float, width: int = 12) -> str:
    filled = round(value * width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


def format_response(command: str, argument: str, snap: dict) -> str:
    ts     = datetime.now().strftime("%H:%M:%S")
    alerts = snap["alerts"]
    rapid  = snap["rapid_flag"]

    lines = [
        "",
        f"  ┌─ {command} ─── {ts}",
        f"  │  {argument[:72] if argument else '(no argument)'}",
        "  │",
        f"  │  LAT   {_bar(snap['LAT'])}  {snap['LAT']:.3f}  Decision Latency",
        f"  │  ATTN  {_bar(snap['ATTN'])}  {snap['ATTN']:.3f}  Attention Stability",
        f"  │  MEM   {_bar(snap['MEM'])}  {snap['MEM']:.3f}  Memory Integrity",
        f"  │  DRIFT {_bar(snap['DRIFT'])}  {snap['DRIFT']:.3f}  Error Drift",
        f"  │  EXT   {_bar(snap['EXT'])}  {snap['EXT']:.3f}  External Reliance",
        "  │",
    ]

    if rapid:
        lines.append("  │  [FLAG] RAPID_RESPONSE")
    for alert in alerts:
        lines.append(f"  │  [ALERT] {alert}")

    lines.append("  └" + "─" * 48)
    return "\n".join(lines)


def format_summary(snap: dict) -> str:
    mins, secs = divmod(int(snap["uptime"]), 60)
    alerts     = snap["alerts"]
    return "\n".join([
        "\n  SESSION SUMMARY",
        "  ───────────────",
        f"  UPTIME   : {mins}m {secs}s",
        f"  COMMANDS : {snap['command_count']}",
        f"  LAT      : {snap['LAT']:.3f}",
        f"  ATTN     : {snap['ATTN']:.3f}",
        f"  MEM      : {snap['MEM']:.3f}",
        f"  DRIFT    : {snap['DRIFT']:.3f}",
        f"  EXT      : {snap['EXT']:.3f}",
        f"  ALERTS   : {', '.join(alerts) if alerts else 'NONE'}",
    ])


BOOT_BANNER = f"""\
╔══════════════════════════════════════════════════════╗
║  INSTRUMENT FOR OUTER REASONING  v{VERSION}          ║
║  Cognitive Stabilisation Interface                  ║
╚══════════════════════════════════════════════════════╝
  STATE      : LAT · ATTN · MEM · DRIFT · EXT
  COMMANDS   : REMEMBER · THINK · CHOOSE · SAY · RECALL
  META       : STATUS · HELP · EXIT
──────────────────────────────────────────────────────"""

HELP_TEXT = """
  REMEMBER [text]   Register information into memory scaffold
  THINK    [text]   Submit reasoning fragment
  CHOOSE   [text]   Commit to a decision branch
  SAY      [text]   Externalise output
  RECALL   [query]  Retrieve memory fragment

  STATUS            Print current state vector
  HELP              Print this reference
  EXIT              Terminate session
"""


# ---------------------------------------------------------------------------
# Terminal
# ---------------------------------------------------------------------------

class Terminal:

    def __init__(self, engine, on_command: Callable, on_quit: Callable) -> None:
        self._engine  = engine
        self._on_cmd  = on_command
        self._on_quit = on_quit
        self._parser  = CommandParser()

    def boot(self) -> None:
        instant_print(BOOT_BANNER)

    def run(self) -> None:
        while True:
            try:
                raw = input("\n  › ")
            except (EOFError, KeyboardInterrupt):
                break

            if not raw.strip():
                continue

            upper = raw.strip().upper()

            if upper in ("EXIT", "QUIT", "Q"):
                break

            if upper == "STATUS":
                snap  = self._engine.snapshot()
                drift = snap["DRIFT"]
                stutter_print(format_summary(snap), drift)
                continue

            if upper in ("HELP", "?"):
                stutter_print(HELP_TEXT, self._engine.DRIFT)
                continue

            valid, record = self._parser.parse(raw)

            if not valid:
                # Rejections bypass stutter — they are system boundary events
                instant_print(self._parser.format_rejection(record))
                continue

            snap  = self._on_cmd(record.name, record.argument)
            text  = format_response(record.name, record.argument, snap)

            # [STUTTER ENGINE: all cognitive output rendered here, keyed to DRIFT]
            stutter_print(text, snap["DRIFT"])

        self._shutdown()

    def _shutdown(self) -> None:
        instant_print("\n──────────────────────────────────────────────────────")
        instant_print("  STATUS : SESSION TERMINATED")
        instant_print(format_summary(self._engine.snapshot()))
        self._on_quit()
