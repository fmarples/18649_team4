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

    def returning_pi(self):
        """Replace the default-leader Pi with one that has to join as a follower."""
        self.app.agent.close()
        self.app = Cockpit5(self.buses, self.gpio, EventLog(None), 0,
                            config={**self.app.config, "default_leader": "none"})
        self.heard = set()
        send = [bus.send for bus in self.buses]
        for bus, real in zip(self.buses, send):
            bus.send = lambda msg, real=real, **kw: (self.heard.add(msg.arbitration_id), real(msg, **kw))

    def test_returning_pi_announces_only_after_it_has_caught_up_and_run_on_time(self):
        self.returning_pi()
        self.step(900)  # peers elect a leader and the Pi learns the commit index
        state = self.app.agent.status
        self.assertEqual(state["role"], 0)
        self.assertGreater(state["commit"], 0)
        # Still inside its first steady second: no presence frame has left,
        # so the leader has not recorded NODE_1 UP.
        self.assertNotIn(0x111, self.heard)
        self.assertEqual(self.peers[state["leader"]].status["nodes"] & 1, 0)
        self.assertFalse(self.app.announced)
        self.step(1200)
        self.assertTrue(self.app.announced)
        self.assertIn(0x111, self.heard)
        leader = self.peers[self.app.agent.status["leader"]]
        self.assertEqual(leader.status["nodes"] & 1, 1)  # NODE_1 committed UP

    def test_no_announcement_while_the_system_is_still_booting(self):
        self.returning_pi()
        self.app.announce_not_before = 3.0
        self.step(2900)
        self.assertFalse(self.app.announced)
        self.step(1200)
        self.assertTrue(self.app.announced)

    def test_a_late_tick_restarts_the_wait_before_announcing(self):
        self.returning_pi()
        self.step(900)
        for _ in range(6):  # a 50 ms stall every 0.5 s never gives one steady second
            self.now += 0.050
            self.step(500)
        self.assertFalse(self.app.announced)
        self.assertNotIn(0x111, self.heard)
        self.step(1200)
        self.assertTrue(self.app.announced)

    def drop_pi(self, index):
        # A committed NODE_1_DOWN reaches the cockpit, as when peers stop hearing it.
        rows = [(index, 1, 4, 0)]
        with patch.object(self.app.agent, "applied",
                          side_effect=lambda limit=None: [rows.pop()] if rows else []):
            self.step(1)

    def test_pi_dropped_by_its_peers_goes_quiet_and_waits_longer_each_time(self):
        self.returning_pi()
        self.step(2100)
        self.assertTrue(self.app.announced)
        self.drop_pi(9001)
        self.assertFalse(self.app.announced)       # quiet again: no REPORT, so no flapping
        self.step(1500)
        self.assertFalse(self.app.announced)       # first repeat within 30 s waits 2 s, not 1 s
        self.step(700)
        self.assertTrue(self.app.announced)
        self.drop_pi(9002)
        self.step(3500)
        self.assertFalse(self.app.announced)       # second repeat waits 4 s
        self.step(700)
        self.assertTrue(self.app.announced)

    def test_drop_after_own_test_button_silence_does_not_hold_the_announcement(self):
        self.returning_pi()
        self.step(2100)
        self.app.hb_silenced = True                # wheel test press
        self.step(300)
        self.app.hb_silenced = False               # double press clears it
        self.step(5)
        self.drop_pi(9001)                         # the NODE_1_DOWN committed while silent
        self.assertTrue(self.app.announced)

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
        self.step(500)
        self.assertTrue(self.app.error)
        self.assertEqual(self.app.agent.status["cockpit_ok"], 0)

    def test_wheel_input_gap_of_200_ms_is_tolerated_and_300_ms_is_not(self):
        # Wi-Fi delivers wheel packets in bursts 100-150 ms apart on this bench.
        def feed(count):
            for i in range(count):
                self.app.last_udp = (i, self.now)
                self.app.monitor.udp(self.now)
                self.step(1)

        self.step(400)
        self.app.latest = (0, 0, 0, 0)
        feed(100)
        self.step(200)
        self.assertFalse(self.app.error)
        self.assertEqual(self.app.agent.status["cockpit_ok"], 1)
        feed(50)
        self.step(300)
        self.assertTrue(self.app.error)

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
            # 1 ms of global time, the 5 ms of work, and the Pi send allowance.
            self.assertEqual(int.from_bytes(ref.data[3:7], "little"),
                             6000 + self.app.config["pi_ref_send_us"])

    def test_frame_age_uses_kernel_receive_time_not_delivery_time(self):
        # The receive thread can deliver a frame milliseconds after the kernel
        # stamped it; a relayed REF must be corrected for that whole wait.
        def frame(stamp):
            return can.Message(arbitration_id=0x82, is_extended_id=False,
                               data=bytes(8), timestamp=stamp)

        with patch("cockpit5.time.time", return_value=1000.0), \
                patch("cockpit5.time.monotonic", return_value=50.0):
            self.app.on_frame(frame(999.997), 0, 50.0)   # stamped 3 ms before delivery
            self.app.on_frame(frame(0.0), 0, 50.0)       # no kernel stamp (fake bus)
            self.app.on_frame(frame(1000.5), 0, 50.0)    # stamp ahead of the clock
        received = [self.app.rx.get_nowait()[2] for _ in range(3)]
        self.assertAlmostEqual(received[0], 49.997, places=6)
        self.assertEqual(received[1:], [50.0, 50.0])

    def test_ref_leaves_on_the_priority_sockets_only(self):
        frames = [[], []]
        self.app.ref_tx = [SimpleNamespace(send=frames[b].append) for b in range(2)]
        for _ in range(60):
            self.now += 0.001
            self.app.tick(self.now)
        urgent = {0x81, 0x111, 0x410, 0x411, 0x412, 0x413}  # REF, HELLO, REPORT
        for b, bus in enumerate(self.buses):
            self.assertFalse([m for m in bus.sent if m.arbitration_id in urgent])
            self.assertTrue(bus.sent)  # everything else still uses the ordinary bus
            sent = [struct.unpack("=IB3x8s", raw) for raw in frames[b]]
            self.assertEqual({can_id for can_id, _, _ in sent}, urgent)
            self.assertTrue(all(dlc == 8 and valid(data) for _, dlc, data in sent))

    def test_local_echo_of_a_ref_is_not_treated_as_bus_traffic(self):
        def frame(can_id, is_rx):
            return can.Message(arbitration_id=can_id, is_extended_id=False,
                               data=bytes(8), is_rx=is_rx)

        self.app.on_frame(frame(0x82, False), 1, 1.0)  # our own relayed REF, looped back
        self.app.on_frame(frame(0x111, False), 1, 1.0)  # our own HELLO, looped back
        self.app.on_frame(frame(0x411, False), 1, 1.0)  # our own REPORT fragment
        self.assertTrue(self.app.rx.empty())
        self.app.on_frame(frame(0x82, True), 1, 1.0)   # the same ID arriving from the wire
        self.app.on_frame(frame(0x100, False), 1, 1.0)  # other local frames are unchanged
        self.assertEqual(self.app.rx.qsize(), 2)

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
        self.step(400)
        rows = [c for c in self.app.log.write.call_args_list if c.args[0] == "STATE_CAUSE"]
        self.assertTrue(rows)
        cause = json.loads(rows[0].args[1])
        self.assertGreaterEqual(cause["udp_age_ms"], 250)
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
