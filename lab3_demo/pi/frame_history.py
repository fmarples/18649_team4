"""First-copy filter by (ID, source, seq); ported from Tianyi's lab3-relay-immediate.

Same 20 ms lifetime as stm32_zephyr/src/frame_history.h: longer than the A/B/relay
copy skew, shorter than the 320 ms reuse of a 4-bit sequence at 20 ms.
"""
import threading

WINDOW_S = 0.020
CAPACITY = 32


class FrameHistory:
    def __init__(self):
        self._seen = {}
        self._lock = threading.Lock()

    def first_copy(self, frame_id, source, seq, now):
        key = (frame_id, source, seq)
        with self._lock:
            self._seen = {k: t for k, t in self._seen.items() if now - t <= WINDOW_S}
            if key in self._seen:
                return False
            if len(self._seen) >= CAPACITY:
                raise OverflowError("CAN duplicate history full")
            self._seen[key] = now
            return True
