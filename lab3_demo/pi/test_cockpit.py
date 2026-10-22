"""Cockpit behavior through python-can's virtual bus; no hardware or sockets."""
import json
import socket
import struct
import threading
import time
import unittest
import uuid
from unittest import mock

import can

import can_protocol as p
from cockpit import Cockpit, EventLog, run
from pi_gpio import CMD_TX, DEG_A, DEG_B, ERR, UDP_RX, NoGpio
from wheel_input import UDP_PACKET_BYTES


def wheel(counter, steer=0, throttle_axis=32767, brake_axis=32767, buttons=()):
    data = bytearray(UDP_PACKET_BYTES)
    struct.pack_into("<Iii", data, 0, counter, steer, throttle_axis)
    struct.pack_into("<i", data, 24, brake_axis)
    for index in buttons:
        data[52 + index] = 0x80
    return bytes(data)


class CockpitTests(unittest.TestCase):
    def setUp(self):
        prefix = uuid.uuid4().hex
        self.buses = [can.Bus(interface="virtual", channel=prefix + name) for name in "AB"]
        self.peers = [can.Bus(interface="virtual", channel=prefix + name) for name in "AB"]
        for bus in self.buses + self.peers:
            self.addCleanup(bus.shutdown)
        self.gpio = NoGpio()
        self.cockpit = Cockpit(self.buses, self.gpio, EventLog(None), 0.0)

    def drain(self, bus):
        frames = []
        while (msg := bus.recv(0)) is not None:
            frames.append(msg)
        return frames

    def frames(self, frame_id):
        """Frames of one ID seen on each bus since the last call: (A list, B list)."""
        return tuple([m for m in self.drain(peer) if m.arbitration_id == frame_id] for peer in self.peers)

    def heartbeat(self, frame_id, bus, now, seq=0, state=p.STATE_OK):
        data = p.seal(seq, p.heartbeat_body(state, True, True))
        self.cockpit.on_frame(can.Message(arbitration_id=frame_id, is_extended_id=False, data=data), bus, now)

    def frame(self, frame_id, body, bus, now, seq=0):
        msg = can.Message(arbitration_id=frame_id, is_extended_id=False, data=p.seal(seq, body))
        self.cockpit.on_frame(msg, bus, now)

    def healthy(self, now, buses=(0, 1)):
        """Peers alive and a fresh wheel update at `now`, then one HB_MON tick."""
        for bus in buses:
            self.heartbeat(p.HB_N2, bus, now, seq=int(now * 50) & 15)
            self.heartbeat(p.HB_N3, bus, now, seq=int(now * 50) & 15)
        self.assertTrue(self.cockpit.on_udp(wheel(int(now * 1000) + 1), now))
        self.cockpit.tick(now)

    def test_ctrl_goes_to_both_buses_with_one_sequence_number(self):
        self.assertTrue(self.cockpit.on_udp(wheel(1, steer=-1200, throttle_axis=-32768), 0.0))
        self.cockpit.send_ctrl(0.0)
        self.cockpit.on_udp(wheel(2), 0.02)
        self.cockpit.send_ctrl(0.02)
        a, b = self.frames(p.CTRL)
        self.assertEqual([bytes(m.data) for m in a], [bytes(m.data) for m in b])
        self.assertEqual([m.data[0] & 15 for m in a], [0, 1])
        first = bytes(a[0].data)
        self.assertTrue(p.valid(first) and p.ctrl_in_range(first))
        self.assertEqual(struct.unpack_from("<hBB", first, 1), (-1200, 100, 0))
        self.assertTrue(self.gpio.levels[CMD_TX] == self.gpio.levels[UDP_RX])

    def test_cmd_tx_marks_the_return_of_the_first_ctrl_write(self):
        order = mock.Mock()
        targets = [("A", self.buses[0], "send"), ("B", self.buses[1], "send"), ("CMD_TX", self.gpio, "cmd_tx")]
        for name, owner, method in targets:
            patcher = mock.patch.object(owner, method, wraps=getattr(owner, method))
            order.attach_mock(patcher.start(), name)
            self.addCleanup(patcher.stop)
        self.cockpit.on_udp(wheel(1), 0.0)
        self.cockpit.send_ctrl(0.0)
        self.assertEqual([call[0] for call in order.mock_calls], ["A", "CMD_TX", "B"])

    def test_power_up_in_error_until_both_peers_and_ctrl(self):
        self.cockpit.tick(0.0)
        self.assertTrue(self.gpio.levels[ERR])
        self.heartbeat(p.HB_N2, 0, 0.01)
        self.heartbeat(p.HB_N3, 0, 0.01)
        self.cockpit.tick(0.02)
        self.assertTrue(self.cockpit.error)  # heartbeats without UDP/CTRL
        self.healthy(0.04)
        self.assertFalse(self.cockpit.error)
        self.assertFalse(self.gpio.levels[ERR])
        hb = self.frames(p.HB_N1)[0][-1]
        self.assertEqual((hb.data[1], hb.data[2]), (p.STATE_OK, 3))

    def test_lost_zone_enters_error_reports_fault_and_recovers_without_reset(self):
        self.healthy(0.0)
        self.drain(self.peers[0]); self.drain(self.peers[1])
        t = 0.02
        while t < 0.1:  # N3 silent on both buses, N2 and UDP continue
            self.heartbeat(p.HB_N2, 0, t, seq=int(t * 50) & 15)
            self.cockpit.on_udp(wheel(int(t * 1000) + 1), t)
            self.cockpit.tick(t)
            t = round(t + 0.02, 3)
        self.assertTrue(self.cockpit.error)
        faults = self.frames(p.FAULT)[0]
        self.assertEqual([(m.data[1], m.data[2], m.data[3]) for m in faults], [(3, p.FAULT_ZONE_LOST, 1)])
        self.healthy(0.12)
        self.assertFalse(self.cockpit.error)

    def test_bus_silent_on_one_side_lights_only_that_degraded_led(self):
        self.healthy(0.0)
        self.healthy(0.06, buses=(0,))
        self.healthy(0.07, buses=(0,))
        self.assertEqual((self.gpio.levels[DEG_A], self.gpio.levels[DEG_B]), (False, True))
        self.assertFalse(self.cockpit.error)  # degraded is not a zone failure
        self.healthy(0.08, buses=(1,))
        self.assertFalse(self.gpio.levels[DEG_B])

    def test_duplicate_copies_from_either_bus_count_once(self):
        body = p.fault_body(p.ZONE_N2, p.FAULT_TEST_BUTTON, p.ZONE_N2)
        self.frame(p.FAULT, body, 0, 1.0, seq=4)
        self.frame(p.FAULT, body, 1, 1.001, seq=4)  # other bus
        self.frame(p.FAULT, body, 0, 1.002, seq=4)  # relayed copy on the same bus
        self.assertEqual(self.cockpit.counters["rx_FAULT"], 1)
        self.assertEqual(self.cockpit.counters["duplicate"], 2)
        # Same reporter's next FAULT, and another reporter's equal sequence, are new.
        self.frame(p.FAULT, p.fault_body(p.ZONE_N3, p.FAULT_ZONE_LOST, p.ZONE_N3), 0, 1.003, seq=4)
        self.assertEqual(self.cockpit.counters["rx_FAULT"], 2)

    def test_remote_test_fault_latches_and_clear_releases(self):
        self.healthy(0.0)
        self.frame(p.FAULT, p.fault_body(2, p.FAULT_TEST_BUTTON, 2), 0, 0.01, seq=0)
        self.healthy(0.02)
        self.assertTrue(self.cockpit.error)
        self.frame(p.FAULT, p.fault_body(2, p.FAULT_ZONE_LOST, 2), 0, 0.03, seq=1)
        self.frame(p.FAULT, p.fault_body(2, p.FAULT_CLEAR, 2), 0, 0.03, seq=2)
        self.healthy(0.04)
        self.assertFalse(self.cockpit.error)

    def test_wheel_test_button_single_then_double_press(self):
        self.healthy(0.0)
        self.drain(self.peers[0])
        self.cockpit.on_udp(wheel(100, buttons=(0,)), 0.01)
        self.assertTrue(self.cockpit.error and self.gpio.levels[ERR])
        self.cockpit.on_udp(wheel(101), 0.1)
        self.cockpit.on_udp(wheel(102, buttons=(0,)), 0.2)
        self.healthy(0.21)
        self.assertFalse(self.cockpit.error)
        faults = self.frames(p.FAULT)[0]
        self.assertEqual([m.data[2] for m in faults], [p.FAULT_TEST_BUTTON, p.FAULT_CLEAR])

    def test_signal_test_fault_latches_then_clears_without_the_wheel(self):
        self.healthy(0.0)
        self.frames(p.FAULT)
        self.cockpit.test_fault(False, 0.01)
        self.assertTrue(self.cockpit.error)
        self.cockpit.test_fault(True, 5.0)  # clear needs no second press inside 500 ms
        self.healthy(5.01)
        self.assertFalse(self.cockpit.error)
        self.assertEqual([m.data[2] for m in self.frames(p.FAULT)[0]], [p.FAULT_TEST_BUTTON, p.FAULT_CLEAR])

    def test_test_press_stops_heartbeats_until_a_double_press_within_500_ms(self):
        self.healthy(0.0)
        self.frames(p.HB_N1)
        self.cockpit.on_udp(wheel(11, buttons=(0,)), 0.01)
        self.healthy(0.02)
        self.healthy(0.04)
        self.assertEqual(self.frames(p.HB_N1), ([], []))
        self.cockpit.on_udp(wheel(300), 0.3)
        self.cockpit.on_udp(wheel(460, buttons=(0,)), 0.46)  # 450 ms after the first press
        self.healthy(0.47)
        self.assertFalse(self.cockpit.error)
        a, b = self.frames(p.HB_N1)
        self.assertEqual((len(a), len(b)), (1, 1))

    def test_any_zones_fault_clear_resumes_silenced_heartbeats(self):
        self.healthy(0.0)
        self.cockpit.test_fault(False, 0.01)
        self.healthy(0.02)
        self.frames(p.HB_N1)
        self.frame(p.FAULT, p.fault_body(2, p.FAULT_CLEAR, 2), 0, 0.03, seq=0)
        self.healthy(0.04)
        self.assertEqual(len(self.frames(p.HB_N1)[0]), 1)

    def test_status_line_is_parseable_json(self):
        self.healthy(0.0)
        line = self.cockpit.status()
        self.assertTrue(line.startswith("STATUS "))
        status = json.loads(line[7:])
        self.assertEqual((status["error"], status["degraded"], status["alive"]), (False, [False, False], {"N2": True, "N3": True}))

    def test_own_frames_relayed_back_by_n2_are_ignored(self):
        self.healthy(0.0)
        self.cockpit.on_udp(wheel(15, buttons=(0,)), 0.01)  # N1 latches
        self.frame(p.FAULT, p.fault_body(1, p.FAULT_CLEAR, 1), 1, 0.011, seq=9)  # stray own echo
        self.frame(p.HB_N1, p.heartbeat_body(p.STATE_OK, True, True), 1, 0.011)
        self.healthy(0.02)
        self.assertTrue(self.cockpit.error)
        self.assertNotIn((1, 1), self.cockpit.monitor.hb)

    def test_injected_bad_ctrl_is_one_shot(self):
        self.cockpit.on_udp(wheel(1), 0.0)
        self.cockpit.inject = "range"
        self.cockpit.send_ctrl(0.0)
        self.cockpit.inject = "crc"
        self.cockpit.send_ctrl(0.0)
        self.cockpit.send_ctrl(0.0)
        a, _ = self.frames(p.CTRL)
        data = [bytes(m.data) for m in a]
        self.assertTrue(p.valid(data[0]) and data[0][3] == 101 and not p.ctrl_in_range(data[0]))
        self.assertFalse(p.valid(data[1]))
        self.assertTrue(p.valid(data[2]) and p.ctrl_in_range(data[2]))

    def test_blink_starts_on_paddle_and_toggles_every_500_ms(self):
        self.healthy(0.0)
        self.frames(p.BLINK)
        self.cockpit.on_udp(wheel(500, buttons=(5,)), 0.03)  # left paddle
        self.cockpit.tick(0.03)
        self.healthy(0.531)
        self.healthy(1.032)
        a, b = self.frames(p.BLINK)
        self.assertEqual([(m.data[1], m.data[2]) for m in a],
                         [(p.BLINK_LEFT, 1), (p.BLINK_LEFT, 0), (p.BLINK_LEFT, 1)])
        self.assertEqual(len(b), 3)

    def test_error_forces_hazard_blink(self):
        self.cockpit.tick(0.0)
        a, _ = self.frames(p.BLINK)
        self.assertEqual(a[-1].data[1], p.BLINK_HAZARD)

    def test_blink_change_within_20_ms_of_the_last_blink_waits(self):
        self.healthy(0.0)  # sends BLINK off at 0.0
        self.frames(p.BLINK)
        self.cockpit.on_udp(wheel(10, buttons=(5,)), 0.01)
        self.cockpit.tick(0.01)
        self.assertEqual(self.frames(p.BLINK), ([], []))
        self.assertAlmostEqual(self.cockpit.next_wake(0.01), 0.02)
        self.cockpit.tick(0.02)
        self.assertEqual([m.data[1] for m in self.frames(p.BLINK)[0]], [p.BLINK_LEFT])

    def test_udp_silence_of_100_ms_fails_n1_and_stops_heartbeats(self):
        self.healthy(0.0)
        t = 0.02
        while t <= 0.081:  # peers keep beating; UDP stops after 0.0
            for zone in (p.HB_N2, p.HB_N3):
                self.heartbeat(zone, 0, t, seq=int(t * 50) & 15)
            self.cockpit.tick(t)
            t = round(t + 0.02, 3)
        self.assertFalse(self.cockpit.error)  # 80 ms: no 60 ms CTRL rule any more
        self.frames(p.HB_N1)
        for zone in (p.HB_N2, p.HB_N3):
            self.heartbeat(zone, 0, 0.1, seq=5)
        self.cockpit.tick(0.1)
        self.assertTrue(self.cockpit.error and self.gpio.levels[ERR])
        self.assertEqual(self.frames(p.HB_N1), ([], []))
        self.healthy(0.121)  # stream resumes
        self.assertFalse(self.cockpit.error)
        self.assertEqual(len(self.frames(p.HB_N1)[0]), 1)

    def test_ctrl_refreshes_at_least_every_50_ms_without_cmd_tx(self):
        self.cockpit.tick(0.0)
        self.assertEqual(self.frames(p.CTRL), ([], []))  # nothing to send before the first update
        self.cockpit.on_udp(wheel(1, steer=300), 0.0)
        self.cockpit.send_ctrl(0.0)
        marker = self.gpio.levels[CMD_TX]
        for t in (0.02, 0.039, 0.04, 0.06, 0.08):
            self.cockpit.tick(t)
        a, b = self.frames(p.CTRL)
        self.assertEqual(len(a), 3)  # 0.0, then refreshes at 0.04 and 0.08
        self.assertEqual([m.data[0] & 15 for m in a], [0, 1, 2])
        self.assertEqual({struct.unpack_from("<h", m.data, 1)[0] for m in a}, {300})
        self.assertEqual(len(b), 3)
        self.assertEqual(self.gpio.levels[CMD_TX], marker)

    def test_every_udp_update_gets_its_own_ctrl(self):
        udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.addCleanup(udp.close)
        udp.bind(("127.0.0.1", 0))
        udp.setblocking(False)
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
            for counter in (1, 2, 3):
                sender.sendto(wheel(counter), udp.getsockname())
        time.sleep(0.05)
        stop = threading.Event()
        threading.Timer(0.05, stop.set).start()
        with mock.patch.object(self.cockpit, "send_ctrl", wraps=self.cockpit.send_ctrl) as send_ctrl:
            run(self.cockpit, udp, stop, status_period=0)
        updates = [c for c in send_ctrl.call_args_list if c.kwargs.get("update", True)]
        self.assertEqual(len(updates), 3)  # refreshes, if the loop reaches 40 ms, are not updates

    def test_malformed_udp_enters_error_and_sends_fault(self):
        self.healthy(0.0)
        self.frames(p.FAULT)
        self.assertFalse(self.cockpit.on_udp(b"\x00" * 10, 0.01))
        self.cockpit.tick(0.01)
        self.assertTrue(self.cockpit.error)
        self.assertEqual([(m.data[1], m.data[2]) for m in self.frames(p.FAULT)[0]], [(1, p.FAULT_BAD_CTRL)])

    def test_test_presses_less_than_50_ms_apart_are_one_press(self):
        self.healthy(0.0)
        self.frames(p.FAULT)
        self.cockpit.on_udp(wheel(20, buttons=(0,)), 0.01)
        self.cockpit.on_udp(wheel(30), 0.02)
        self.cockpit.on_udp(wheel(40, buttons=(0,)), 0.04)  # 30 ms later: same press
        self.cockpit.on_udp(wheel(45), 0.05)
        self.cockpit.on_udp(wheel(50, buttons=(0,)), 0.07)  # chatter: 30 ms after the last raw press
        self.healthy(0.09)
        self.assertTrue(self.cockpit.error)
        self.assertEqual([m.data[2] for m in self.frames(p.FAULT)[0]], [p.FAULT_TEST_BUTTON])

    def test_fault_keeps_20_ms_minimum_interval(self):
        self.healthy(0.0)
        self.frames(p.FAULT)
        self.cockpit.test_fault(False, 0.01)
        self.cockpit.test_fault(True, 0.015)  # clear waits for its slot
        self.assertEqual(len(self.frames(p.FAULT)[0]), 1)
        self.cockpit.tick(0.029)
        self.assertEqual(self.frames(p.FAULT), ([], []))
        self.cockpit.tick(0.03)
        self.assertEqual([m.data[2] for m in self.frames(p.FAULT)[0]], [p.FAULT_CLEAR])

    def test_restarted_proxy_counter_resyncs_after_a_gap(self):
        self.assertTrue(self.cockpit.on_udp(wheel(5000), 0.0))
        self.assertFalse(self.cockpit.on_udp(wheel(10), 0.02))
        self.assertTrue(self.cockpit.on_udp(wheel(10), 2.0))


if __name__ == "__main__":
    unittest.main()
