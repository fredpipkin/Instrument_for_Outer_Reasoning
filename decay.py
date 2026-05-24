# decay.py
# Background daemon thread.
# Checks inactivity on each tick. Applies decay rates to state engine.
# Dies automatically when the main process exits (daemon=True).
#
# [ALL PASSIVE STATE DEGRADATION ORIGINATES HERE]
#
# NEURAL MODEL INTEGRATION POINT:
#   _get_rates() currently returns static config values.
#   Replace with inference_stub.InferenceStub.infer() output
#   to apply learned, personalised decay rates.

import time
import threading
from typing import Callable, Optional

from config import DECAY_TICK_SECONDS, DECAY_INACTIVE_AFTER, DECAY_RATES


class DecayEngine:

    def __init__(
        self,
        engine,                                  # CognitiveStateEngine
        on_tick: Optional[Callable] = None,      # Called after each decay application
    ) -> None:
        self._engine   = engine
        self._on_tick  = on_tick
        self._stop     = threading.Event()
        self._thread   = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()

    def _run(self) -> None:
        while not self._stop.is_set():
            time.sleep(DECAY_TICK_SECONDS)

            # Only decay when user has been inactive long enough
            # [DECAY TRIGGER: inactivity check]
            inactive = time.time() - self._engine.last_command_time
            if inactive < DECAY_INACTIVE_AFTER:
                continue

            # [DECAY APPLIED TO STATE HERE]
            self._engine.on_decay(self._get_rates())

            if self._on_tick:
                try:
                    self._on_tick()
                except Exception:
                    pass  # Decay thread must never crash

    # [NEURAL MODEL INTEGRATION POINT: replace return value with model output]
    def _get_rates(self) -> dict:
        return dict(DECAY_RATES)
