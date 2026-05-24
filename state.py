# state.py
# Cognitive state engine.
# Owns LAT, ATTN, MEM, DRIFT, EXT.
# No other module mutates these directly.
#
# EXT responds dynamically to interaction frequency over a rolling time window.
# Command timestamps are tracked to calculate this frequency.
# Diagnostic events are written to a health log and surfaced in the UI.
#
# get_feature_vector() is reserved for a future model integration.
# A trained model would receive this dict and return delta overrides.

import time
from typing import Dict, List

from config import (
    STATE_INITIAL,
    STATE_FLOOR,
    STATE_CEILING,
    COMMAND_DELTAS,
    ALERT_THRESHOLDS,
    RAPID_THRESHOLD,
    EXT_INTERACTION_BASE,
    EXT_INTERACTION_SCALE,
    EXT_FREQUENCY_WINDOW,
    HEALTH_LOG_MAX_ENTRIES,
    HEALTH_LOG_ENTRY_TTL,
)


class HealthLogEntry:
    """Single diagnostic entry in the health log."""
    def __init__(self, level: str, message: str):
        self.timestamp = time.time()
        self.level = level  # "NOTICE", "WARNING", "ALERT", "ERROR"
        self.message = message
    
    def to_dict(self) -> dict:
        return {
            "ts": round(self.timestamp, 1),
            "level": self.level,
            "message": self.message,
        }
    
    def is_expired(self, now: float) -> bool:
        return (now - self.timestamp) > HEALTH_LOG_ENTRY_TTL


class CognitiveStateEngine:

    def __init__(self) -> None:
        self.LAT:   float = STATE_INITIAL["LAT"]
        self.ATTN:  float = STATE_INITIAL["ATTN"]
        self.MEM:   float = STATE_INITIAL["MEM"]
        self.DRIFT: float = STATE_INITIAL["DRIFT"]
        self.EXT:   float = STATE_INITIAL["EXT"]

        self.session_start:     float     = time.time()
        self.last_command_time: float     = time.time()
        self.command_count:     int       = 0
        self.alerts:            List[str] = []
        self.rapid_flag:        bool      = False
        
        self.health_log:        List[HealthLogEntry] = []
        self._command_times:    List[float] = []

    # ------------------------------------------------------------------
    # Called on every validated command.
    # Applies command deltas, updates EXT based on interaction frequency,
    # and checks for threshold violations.
    # ------------------------------------------------------------------
    def on_command(self, command: str) -> dict:
        now     = time.time()
        elapsed = now - self.last_command_time

        self.rapid_flag = (elapsed < RAPID_THRESHOLD and self.command_count > 0)

        # Track timestamp for rolling frequency calculation
        self._command_times.append(now)

        # Calculate how many commands occurred in the last window
        cutoff = now - EXT_FREQUENCY_WINDOW
        recent_commands = sum(1 for ts in self._command_times if ts > cutoff)
        frequency = recent_commands / EXT_FREQUENCY_WINDOW  # commands per second

        # EXT grows with base rate plus a boost proportional to interaction speed
        ext_increase = EXT_INTERACTION_BASE + (frequency * EXT_INTERACTION_SCALE)
        self._set("EXT", self._get("EXT") + ext_increase)
        
        # Apply standard command deltas
        for var, delta in COMMAND_DELTAS.get(command, {}).items():
            self._set(var, self._get(var) + delta)

        self.command_count     += 1
        self.last_command_time  = now
        self.alerts             = self._evaluate_alerts()

        return self.snapshot()

    # ------------------------------------------------------------------
    # Called by the decay thread on each tick (driven by decay.py)
    # ------------------------------------------------------------------
    def on_decay(self, rates: Dict[str, float]) -> None:
        for var, delta in rates.items():
            self._set(var, self._get(var) + delta)
        self.alerts = self._evaluate_alerts()

    # ------------------------------------------------------------------
    # Health log management
    # ------------------------------------------------------------------
    def log_health_event(self, level: str, message: str) -> None:
        """Record a diagnostic event in the health log."""
        entry = HealthLogEntry(level=level, message=message)
        self.health_log.append(entry)
        
        # Trim old entries
        now = time.time()
        self.health_log = [e for e in self.health_log if not e.is_expired(now)]
        
        # Keep only most recent N entries
        if len(self.health_log) > HEALTH_LOG_MAX_ENTRIES:
            self.health_log = self.health_log[-HEALTH_LOG_MAX_ENTRIES:]
    
    def get_health_log(self) -> List[dict]:
        """Return health log as list of dicts (for JSON serialization)."""
        now = time.time()
        # Clean expired entries
        self.health_log = [e for e in self.health_log if not e.is_expired(now)]
        return [e.to_dict() for e in self.health_log]

    # ------------------------------------------------------------------
    # Read-only snapshot — safe to call from any thread
    # ------------------------------------------------------------------
    def snapshot(self) -> dict:
        return {
            "LAT":           round(self.LAT,   4),
            "ATTN":          round(self.ATTN,  4),
            "MEM":           round(self.MEM,   4),
            "DRIFT":         round(self.DRIFT, 4),
            "EXT":           round(self.EXT,   4),
            "alerts":        list(self.alerts),
            "rapid_flag":    self.rapid_flag,
            "command_count": self.command_count,
            "uptime":        round(time.time() - self.session_start, 1),
        }

    # Returns a flat feature dict for potential future model inference
    def get_feature_vector(self) -> dict:
        now = time.time()
        return {
            "LAT":                     round(self.LAT,   4),
            "ATTN":                    round(self.ATTN,  4),
            "MEM":                     round(self.MEM,   4),
            "DRIFT":                   round(self.DRIFT, 4),
            "EXT":                     round(self.EXT,   4),
            "time_since_last_command": round(now - self.last_command_time, 2),
            "session_uptime":          round(now - self.session_start, 2),
            "command_count":           self.command_count,
            "rapid_flag":              int(self.rapid_flag),
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------
    def _get(self, var: str) -> float:
        return getattr(self, var)

    def _set(self, var: str, value: float) -> None:
        setattr(self, var, max(STATE_FLOOR, min(STATE_CEILING, value)))

    def _evaluate_alerts(self) -> List[str]:
        """Check each parameter against its threshold and write violations to the health log."""
        t = ALERT_THRESHOLDS
        out: List[str] = []
        
        if self.DRIFT >= t["DRIFT_HIGH"]:
            out.append("DRIFT_HIGH")
            self.log_health_event("ALERT", f"Cognitive drift critical: {self.DRIFT:.3f}")
        if self.ATTN  <= t["ATTN_LOW"]:
            out.append("ATTN_DEGRADED")
            self.log_health_event("WARNING", f"Attention stability below threshold: {self.ATTN:.3f}")
        if self.MEM   <= t["MEM_LOW"]:
            out.append("MEM_DEGRADED")
            self.log_health_event("WARNING", f"Memory integrity compromised: {self.MEM:.3f}")
        if self.EXT   >= t["EXT_HIGH"]:
            out.append("EXT_OVERRELIANCE")
            self.log_health_event("NOTICE", f"External reliance elevated: {self.EXT:.3f}")
        if self.LAT   >= t["LAT_HIGH"]:
            out.append("LAT_CRITICAL")
            self.log_health_event("ALERT", f"Decision latency critical: {self.LAT:.3f}")
        
        return out
