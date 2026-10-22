"""N1 copy of stm32_zephyr/src/zone_state.c: same thresholds and rules, except that
the cockpit's control input is the UDP stream instead of CTRL."""
from __future__ import annotations

from dataclasses import dataclass, field

HB_PERIOD_S = 0.020
ZONE_FAIL_S = 0.066   # R4.5: three missed heartbeats at the +10 % period, 3 x 22 ms
BUS_SILENT_S = 0.060  # R4.7: three heartbeat periods without traffic / heartbeats
UDP_FAIL_S = 0.100    # Lab 1 cockpit zone: no UDP update for 100 ms -> N1 failed
ZONES = (1, 2, 3)


@dataclass
class ZoneHealth:
    alive: dict[int, bool]
    bus_ok: tuple[bool, bool]    # traffic within BUS_SILENT_S; heartbeat health bits
    degraded: tuple[bool, bool]  # R4.7 per-bus status LED
    isolated: bool
    udp_ok: bool                 # False: N1 failed itself and stops HB_N1
    error: bool


@dataclass
class ZoneMonitor:
    """Owned by one lock holder. Times are monotonic seconds."""
    self_zone: int
    boot: float = 0.0
    hb: dict[tuple[int, int], float] = field(default_factory=dict)  # (zone, bus) -> last time
    traffic: list[float] = field(init=False)  # per bus, last frame from any other node
    udp_time: float | None = None
    latched: bool = False  # test button, bad input or received FAULT; FAULT clear releases

    def __post_init__(self):
        self.traffic = [self.boot, self.boot]

    def heartbeat(self, zone: int, bus: int, now: float) -> None:
        """Record per bus BEFORE duplicate filtering."""
        if zone in ZONES and zone != self.self_zone and bus in (0, 1):
            self.hb[(zone, bus)] = now

    def frame(self, bus: int, now: float) -> None:
        """Any frame received on this bus, valid or not."""
        if bus in (0, 1):
            self.traffic[bus] = now

    def udp(self, now: float) -> None:
        self.udp_time = now

    def evaluate(self, now: float) -> ZoneHealth:
        peers = [z for z in ZONES if z != self.self_zone]
        age = {key: now - t for key, t in self.hb.items()}
        alive = {z: any(age.get((z, bus), ZONE_FAIL_S) < ZONE_FAIL_S for bus in (0, 1)) for z in peers}
        isolated = not any(a < BUS_SILENT_S for a in age.values())
        bus_ok = tuple(now - t < BUS_SILENT_S for t in self.traffic)
        degraded = (not bus_ok[0] and bus_ok[1], not bus_ok[1] and bus_ok[0])
        udp_ok = self.udp_time is not None and now - self.udp_time < UDP_FAIL_S
        error = self.latched or not all(alive.values()) or isolated or not udp_ok
        return ZoneHealth(alive, bus_ok, degraded, isolated, udp_ok, error)

    def next_change(self, now: float) -> float | None:
        """Seconds until a bus with traffic reaches BUS_SILENT_S, so DEG_x lights on time."""
        waits = [BUS_SILENT_S - (now - t) for t in self.traffic if now - t < BUS_SILENT_S]
        return min(waits, default=None)
