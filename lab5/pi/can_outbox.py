"""Bounded, nonblocking retry of protocol frames, independently for each bus.

SocketCAN's small transmit queue can fill during a consensus burst. Keep an
ordered copy briefly instead of discarding the rest of an RPC at the first
ENOBUFS. This is not a delivery guarantee: Raft still owns acknowledgements and
retransmission. Never retain a software-queued frame beyond one 20 ms period.
"""

from collections import Counter, deque
import errno

import can
from vehicle.can_protocol import crc8


class CanOutbox:
    def __init__(self, capacity=128, lifetime_s=0.020, retry_s=0.001):
        self.capacity = capacity
        self.lifetime_s = lifetime_s
        self.retry_s = retry_s
        self.frames = deque()
        self.retry_at = 0.0
        self.counts = Counter()

    def _expire(self, now):
        while self.frames and now - self.frames[0][0] >= self.lifetime_s:
            self.frames.popleft()
            self.counts['expired'] += 1

    def enqueue(self, can_id, data, created, now):
        self._expire(now)
        if now - created >= self.lifetime_s:
            self.counts['expired'] += 1
            return
        if len(self.frames) >= self.capacity:
            self.counts['overflow'] += 1
            return
        self.frames.append((created, can_id, bytes(data)))

    def flush(self, send, clock):
        # Bounded work even if a producer is accidentally overactive. No sleep,
        # blocking socket timeout, or work on the other bus occurs here.
        for _ in range(self.capacity):
            now = clock()
            self._expire(now)
            if not self.frames or now < self.retry_at:
                return
            created, can_id, data = self.frames[0]
            if 0x81 <= can_id <= 0x83:
                # Recompute from the original every attempt; a failed attempt
                # must not accumulate the same residence time twice.
                elapsed = max(0, round((now - created) * 1_000_000))
                stamp = (int.from_bytes(data[3:7], 'little') + elapsed) & 0xffffffff
                prefix = data[:3] + stamp.to_bytes(4, 'little')
                data = prefix + bytes([crc8(prefix)])
            try:
                send(can_id, data)
            except (can.CanError, OSError) as exc:
                code = getattr(exc, 'error_code', None)
                if code is None:
                    code = getattr(exc, 'errno', None)
                if code in (errno.ENOBUFS, errno.EAGAIN, errno.EWOULDBLOCK):
                    self.counts['backpressure'] += 1
                    self.retry_at = now + self.retry_s
                    return
                self.counts['send_error'] += 1
                self.frames.popleft()
            else:
                self.frames.popleft()
                self.counts['sent'] += 1
                self.retry_at = 0.0

    def status(self):
        return dict(queued=len(self.frames), **self.counts)
