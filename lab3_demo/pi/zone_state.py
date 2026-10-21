"""N1 copy of stm32_zephyr/src/zone_state.c: same thresholds, same error rule."""
from __future__ import annotations

from dataclasses import dataclass, field

HB_PERIOD_S = 0.020
HB_TIMEOUT_S = 0.060    # R4.5: three missed heartbeats
CTRL_TIMEOUT_S = 0.060  # three missed 20 ms UDP updates
ZONES = (1, 2, 3)


@dataclass
class ZoneHealth:
    alive: dict[int, bool]
    bus_alive: tuple[bool, bool]
    degraded: tuple[bool, bool]
    ctrl_fresh: bool
    error: bool


@dataclass
class ZoneMonitor:
    """Owned by one lock holder. Times are monotonic seconds."""
    self_zone: int
    hb: dict[tuple[int, int], float] = field(default_factory=dict)  # (zone, bus) -> last time
    ctrl_time: float | None = None
    latched: bool = False  # test button, bad input or received FAULT; FAULT clear releases

    def heartbeat(self, zone: int, bus: int, now: float) -> None:
        """Record per bus BEFORE duplicate filtering."""
        if zone in ZONES and zone != self.self_zone and bus in (0, 1):
            self.hb[(zone, bus)] = now

    def ctrl(self, now: float) -> None:
        self.ctrl_time = now

    def evaluate(self, now: float) -> ZoneHealth:
        peers = [z for z in ZONES if z != self.self_zone]
        fresh = {key: now - t < HB_TIMEOUT_S for key, t in self.hb.items()}
        alive = {z: fresh.get((z, 0), False) or fresh.get((z, 1), False) for z in peers}
        bus_alive = tuple(any(fresh.get((z, bus), False) for z in peers) for bus in (0, 1))
        ever_seen = bool(self.hb)
        degraded = tuple(ever_seen and not ok for ok in bus_alive)
        ctrl_fresh = self.ctrl_time is not None and now - self.ctrl_time < CTRL_TIMEOUT_S
        error = self.latched or not all(alive.values()) or not ctrl_fresh
        return ZoneHealth(alive, bus_alive, degraded, ctrl_fresh, error)
