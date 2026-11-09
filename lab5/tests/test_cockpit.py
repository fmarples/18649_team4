"""Pi adapter tests without SocketCAN, GPIO, UDP sockets or a vehicle."""

import sys
import unittest
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
from cockpit5 import Cockpit5, Lab5NoGpio, LEADER, SYNC
from vehicle.cockpit import EventLog
from native import Agent
from vehicle.can_protocol import valid
import can


class Bus:
    def __init__(self):
        self.sent = []

    def send(self, msg, **kwargs):
        self.sent.append(msg)


class CockpitTests(unittest.TestCase):
    def setUp(self):
        self.buses = [Bus(), Bus()]
        self.gpio = Lab5NoGpio()
        self.app = Cockpit5(self.buses, self.gpio, EventLog(None), 0)
        self.peers = {i: Agent(i, seed=649) for i in (2, 3)}
        self.now = 0

    def tearDown(self):
        self.app.agent.close()
        for n in self.peers.values():
            n.close()

    def step(self, count):
        for _ in range(count):
            self.now += 0.001
            us = round(self.now * 1e6)
            self.app.tick(self.now)
            for n in self.peers.values():
                n.update(us)
            for b, bus in enumerate(self.buses):
                frames, bus.sent = bus.sent, []
                for msg in frames:
                    for n in self.peers.values():
                        n.receive_can(b, msg.arbitration_id, bytes(msg.data), us)
            for src, n in self.peers.items():
                for b, can_id, data in n.outgoing():
                    self.app.on_frame(
                        can.Message(
                            arbitration_id=can_id, is_extended_id=False, data=data
                        ),
                        b,
                        self.now,
                    )
                    for dst, other in self.peers.items():
                        if dst != src:
                            other.receive_can(b, can_id, data, us)

    def test_proxy_off_stays_error_but_pi_is_time_leader(self):
        self.step(500)
        self.assertTrue(self.app.error)
        self.assertTrue(self.gpio.levels[LEADER])
        self.assertTrue(self.gpio.levels[SYNC])
        self.assertGreater(self.app.agent.status["commit"], 0)

    def test_fresh_wheel_then_stale_changes_consensus_cockpit_state(self):
        self.step(400)
        self.app.latest = (0, 0, 0, 0)
        for i in range(100):
            self.app.last_udp = (i, self.now)
            self.app.monitor.udp(self.now)
            self.step(1)
        self.assertFalse(self.app.error)
        self.assertEqual(self.app.agent.status["cockpit_ok"], 1)
        self.step(250)
        self.assertTrue(self.app.error)
        self.assertEqual(self.app.agent.status["cockpit_ok"], 0)

    def test_malformed_can_does_not_crash(self):
        self.app.on_frame(
            can.Message(arbitration_id=0x410, data=b"bad", is_extended_id=False), 0, 0
        )
        self.app.tick(0.001)
        self.assertFalse(self.app.agent.status["failed"])

    def test_ref_accounts_for_work_before_send(self):
        clock = [10.0]
        update = self.app.agent.update

        def delayed_update(*args):
            update(*args)
            clock[0] += 0.005  # A modeled 5 ms durable write before send.

        with patch("cockpit5.time.monotonic", side_effect=lambda: clock[0]):
            with patch.object(self.app.agent, "update", side_effect=delayed_update):
                self.app.tick(0.001)
        for bus in self.buses:
            ref = next(m for m in bus.sent if m.arbitration_id == 0x81)
            self.assertTrue(valid(bytes(ref.data)))
            self.assertEqual(int.from_bytes(ref.data[3:7], "little"), 6000)


if __name__ == "__main__":
    unittest.main()
