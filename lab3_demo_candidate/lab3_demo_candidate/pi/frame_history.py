"""Bounded first-copy filtering, including direct/relayed copies on one bus."""
import threading

WINDOW_NS = 5_000_000
CAPACITY = 32

class FrameHistory:
    def __init__(self):
        self._seen = {}
        self._lock = threading.Lock()

    def first_copy(self, frame_id, source, seq, now_ns):
        key = (frame_id, source, seq)
        with self._lock:
            self._seen = {k: t for k, t in self._seen.items() if now_ns - t <= WINDOW_NS}
            if key in self._seen:
                return False
            if len(self._seen) >= CAPACITY:
                raise OverflowError("CAN duplicate history full")
            self._seen[key] = now_ns
            return True
