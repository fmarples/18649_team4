"""Pi adapter tests without SocketCAN, GPIO, UDP sockets or a vehicle."""

import sys
import json
import struct
import unittest
from unittest.mock import patch, Mock
from types import SimpleNamespace
from queue import Queue
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pi"))
from cockpit5 import Cockpit5, Lab5NoGpio, LEADER, SYNC
from vehicle.cockpit import EventLog, run
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

    def test_full_display_queue_leaves_commits_pending_until_space_exists(self):
        pending = [(2, 1, 22, 1)]
        queue = Queue(maxsize=1)
        queue.put({"index": 1})

        def applied(limit=None):
            for _ in range(min(limit, len(pending))):
                yield pending.pop(0)

        def submit(row):
            queue.put_nowait(row)
            return True

        self.app.ledger = SimpleNamespace(queue=queue, submit=submit)
        with patch.object(self.app.agent, "applied", side_effect=applied):
            self.app.tick(0.001)
            self.assertEqual(len(pending), 1)
            self.assertFalse(self.app.monitor.latched)
            queue.get_nowait()
            self.app.tick(0.002)
            self.assertEqual(pending, [])
            self.assertEqual(queue.get_nowait()["index"], 2)

    def test_large_replay_is_interleaved_with_control_ticks(self):
        pending = [(i, 1, 22, 1) for i in range(1, 131)]

        def applied(limit=None):
            for _ in range(min(limit, len(pending))):
                yield pending.pop(0)

        with patch.object(self.app.agent, "applied", side_effect=applied):
            self.app.tick(0.001)
            self.assertEqual(len(self.app.applied_events), 64)
            self.app.tick(0.002)
            self.assertEqual(len(self.app.applied_events), 128)
            self.app.tick(0.003)
        self.assertEqual([r["index"] for r in self.app.applied_events], list(range(1, 131)))

    def test_status_exposes_evidence_drops_and_ledger_lag(self):
        self.assertIsNone(json.loads(self.app.status()[7:])["evidence"]["ledger"])
        pending = Queue()
        pending.put("one pending row")
        self.app.ledger = SimpleNamespace(
            durable_index=3, queue=pending, dropped=2, error="disk error"
        )
        self.app.console = SimpleNamespace(dropped=4)
        self.app.log.dropped = 5
        data = json.loads(self.app.status()[7:])["evidence"]
        self.assertEqual(
            data,
            {
                "csv_dropped": 5,
                "console_dropped": 4,
                "ledger": {
                    "durable_index": 3,
                    "queued": 1,
                    "dropped": 2,
                    "error": "disk error",
                },
            },
        )

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

    def test_periodic_status_uses_background_console(self):
        self.app.console = SimpleNamespace(write=Mock(), dropped=0)
        stop = Mock()
        stop.is_set.side_effect = [False, True]
        with patch("vehicle.cockpit.select.select", return_value=([], [], [])):
            with patch("builtins.print", side_effect=AssertionError("control-loop print")):
                run(self.app, Mock(), stop, clock=lambda: 0.001)
        rows = [c.args[0] for c in self.app.console.write.call_args_list]
        self.assertEqual(sum(row.startswith("STATUS ") for row in rows), 1)

    def test_slow_tick_reports_elapsed_stage_without_changing_deadline(self):
        clock = [10.0]
        update = self.app.agent.update
        self.app.log.write = Mock()

        def delayed_update(*args):
            update(*args)
            clock[0] += 0.125

        with patch("cockpit5.time.monotonic", side_effect=lambda: clock[0]):
            with patch.object(self.app.agent, "update", side_effect=delayed_update):
                self.app.tick(0.001)
        rows = [json.loads(c.args[1]) for c in self.app.log.write.call_args_list
                if c.args[0] == "TICK_SLOW"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["total_ms"], 125.0)
        self.assertEqual(rows[0]["agent_update_ms"], 125.0)
        self.assertEqual(rows[0]["can_receive_ms"], 0.0)

    def test_error_transition_records_cause_snapshot(self):
        self.step(400)
        self.app.latest = (0, 0, 0, 0)
        for i in range(100):
            self.app.last_udp = (i, self.now)
            self.app.monitor.udp(self.now)
            self.step(1)
        self.assertFalse(self.app.error)
        self.app.log.write = Mock()
        self.step(250)
        rows = [c for c in self.app.log.write.call_args_list if c.args[0] == "STATE_CAUSE"]
        self.assertTrue(rows)
        cause = json.loads(rows[0].args[1])
        self.assertGreaterEqual(cause["udp_age_ms"], 100)
        self.assertFalse(cause["latched"])
        self.assertFalse(cause["no_controls"])
        self.assertTrue(cause["agent_error"])

    def test_udp_gap_records_counter_and_keeps_duplicate_from_refreshing_input(self):
        def packet(counter):
            data = bytearray(276)
            struct.pack_into('<Iii', data, 0, counter, 0, 32767)
            struct.pack_into('<i', data, 24, 32767)
            return data
        self.app.log.write = Mock()
        self.assertTrue(self.app.on_udp(packet(10), 1.0))
        self.assertFalse(self.app.on_udp(packet(10), 1.08))
        self.assertEqual(self.app.last_udp, (10, 1.0))
        self.assertTrue(self.app.on_udp(packet(17), 1.14))
        rows = [json.loads(c.args[1]) for c in self.app.log.write.call_args_list
                if c.args[0] == 'UDP_GAP']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['gap_ms'], 140.0)
        self.assertEqual(rows[0]['counter_advance'], 7)

    def test_select_delay_is_logged_even_when_tick_is_fast(self):
        clock = [0.0]
        self.app.log.write = Mock()
        stop = Mock()
        stop.is_set.side_effect = [False, True]
        def delayed_select(*args):
            clock[0] += .125
            return [], [], []
        with patch('vehicle.cockpit.select.select', side_effect=delayed_select):
            run(self.app, Mock(), stop, clock=lambda: clock[0], status_period=0)
        rows = [json.loads(c.args[1]) for c in self.app.log.write.call_args_list
                if c.args[0] == 'LOOP_SLOW']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['select_ms'], 125.0)
        self.assertEqual(rows[0]['tick_ms'], 0.0)

    def test_local_ctrl_is_not_queued_behind_blocked_protocol(self):
        import errno
        self.buses[1].send = Mock(side_effect=OSError(errno.ENOBUFS, 'full'))
        with patch('cockpit5.time.monotonic', return_value=.001):
            self.app.tick(.001)
        self.assertTrue(self.app.protocol_tx[1].frames)
        self.app.latest = (123, 0, 0, 0)
        self.app.send_ctrl(.002, clock=lambda: .002)
        self.assertTrue(any(m.arbitration_id == 0x010 for m in self.buses[0].sent))
        self.assertTrue(all(ident != 0x010 for _, ident, _ in self.app.protocol_tx[1].frames))


if __name__ == "__main__":
    unittest.main()
