"""Bounded, read-only history for the laptop's current chart."""
from collections import deque
from dataclasses import dataclass

from pi.part2_protocol import STATUS_SIZE, is_newer, pop_status

STALE_SECONDS = 0.5
WINDOW_SECONDS = 30.0
CURRENT_CHANNELS = ('left', 'right', 'servo')


@dataclass(frozen=True)
class CurrentPoint:
    received_s: float
    amps: tuple[float | None, ...]
    gap: bool


# Feed complete UDP status datagrams; the chart never opens UART or sends commands.
class TelemetryHistory:
    def __init__(self, connected_channels=CURRENT_CHANNELS):
        if not set(connected_channels) <= set(CURRENT_CHANNELS):
            raise ValueError('Unknown current channel')
        self.connected_channels = tuple(name for name in CURRENT_CHANNELS if name in connected_channels)
        self.samples = deque(maxlen=3000)
        self.status = None
        self.last_received = None

    def receive(self, data, now):
        statuses = list(pop_status(bytearray(data))) if len(data) == STATUS_SIZE else []
        if not statuses:
            return False
        status = statuses[0]
        if self.status is not None:
            if (status['status_seq'], status['stm_ms']) == (
                    self.status['status_seq'], self.status['stm_ms']):
                return False
            if not self.stale(now) and not is_newer(status['status_seq'], self.status['status_seq']):
                return False
        gap = self.status is not None and (
            (status['status_seq'] - self.status['status_seq']) & 0xffffffff != 1 or
            now - self.last_received >= 0.1)
        self.status = status
        amps = tuple(self.status['current_' + name + '_mA'] / 1000
                     if name in self.connected_channels and self.status['current_valid_mask'] & (1 << i) and
                     self.status['current_' + name + '_mA'] != -2147483648 else None
                     for i, name in enumerate(CURRENT_CHANNELS))
        self.samples.append(CurrentPoint(now, amps, gap))
        while self.samples and self.samples[0].received_s < now - WINDOW_SECONDS:
            self.samples.popleft()
        self.last_received = now
        return True

    def stale(self, now):
        return self.last_received is None or now - self.last_received >= STALE_SECONDS
