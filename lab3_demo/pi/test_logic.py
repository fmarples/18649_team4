"""Protocol, zone-state, blinker and history units shared with the STM32 design."""
import unittest

import can_protocol as p
from blinker import LEFT_BUTTON, RIGHT_BUTTON, Blinker
from frame_history import CAPACITY, WINDOW_S, FrameHistory
from zone_state import ZoneMonitor


class ProtocolTests(unittest.TestCase):
    def test_crc_matches_handout_example_layout(self):
        # Known CRC-8/ATM check value for "123456789".
        self.assertEqual(p.crc8(b"123456789"), 0xF4)

    def test_seal_inserts_sequence_and_keeps_flags(self):
        data = p.seal(18, p.ctrl_body(-1, 50, 0, 0x21))
        self.assertEqual(data[0], 0x12)
        self.assertTrue(p.valid(data) and p.ctrl_in_range(data))

    def test_out_of_range_ctrl_fields(self):
        good = p.seal(0, p.ctrl_body(0, 0, 0, 0))
        for index, value in ((3, 101), (4, 101), (6, 1), (0, 0x00)):
            bad = bytearray(good)
            bad[index] = value
            self.assertFalse(p.ctrl_in_range(bytes(bad)), index)

    def test_fault_layout_and_dedup_source(self):
        data = p.seal(3, p.fault_body(p.ZONE_N3, p.FAULT_ZONE_LOST, p.ZONE_N2))
        self.assertEqual(tuple(data[1:4]), (3, 4, 2))
        self.assertEqual(p.dedup_source(p.FAULT, data), 2)
        self.assertEqual(p.dedup_source(p.CTRL, data), 0)


def beat(m, zones, buses, t):
    for bus in buses:
        m.frame(bus, t)
        for zone in zones:
            m.heartbeat(zone, bus, t)


class ZoneStateTests(unittest.TestCase):
    """Same rules as tests/test_zone_state.c, plus N1's 100 ms UDP rule."""

    def healthy_monitor(self):
        m = ZoneMonitor(1, 0.0)
        beat(m, (2, 3), (0, 1), 0.0)
        m.udp(0.0)
        return m

    def test_power_up_in_error_isolated_without_degraded_leds(self):
        h = ZoneMonitor(1, 0.0).evaluate(0.0)
        self.assertTrue(h.error and h.isolated)
        self.assertEqual(h.degraded, (False, False))
        self.assertFalse(self.healthy_monitor().evaluate(0.01).error)

    def test_zone_fails_after_three_missed_heartbeats_66_ms(self):
        m = self.healthy_monitor()
        for t in (0.02, 0.04, 0.06):
            beat(m, (2,), (0,), t)
        self.assertFalse(m.evaluate(0.0655).error)
        h = m.evaluate(0.066)
        self.assertTrue(h.error and not h.alive[3] and h.alive[2])

    def test_bus_degraded_at_60_ms_only_while_other_bus_has_traffic(self):
        m = self.healthy_monitor()
        self.assertAlmostEqual(m.next_change(0.0), 0.06)
        for t in (0.02, 0.04, 0.06):
            beat(m, (2, 3), (1,), t)
        self.assertEqual(m.evaluate(0.0599).degraded, (False, False))
        h = m.evaluate(0.06)
        self.assertEqual((h.degraded, h.bus_ok, h.error), ((True, False), (False, True), False))
        m.frame(0, 0.07)  # any frame clears it
        self.assertEqual(m.evaluate(0.07).degraded, (False, False))

    def test_isolation_is_not_degraded(self):
        h = self.healthy_monitor().evaluate(0.06)
        self.assertTrue(h.isolated and h.error)
        self.assertEqual(h.degraded, (False, False))

    def test_udp_silence_fails_n1_at_100_ms(self):
        m = self.healthy_monitor()
        for t in (0.02, 0.04, 0.06, 0.08, 0.1):
            beat(m, (2, 3), (0, 1), t)
        self.assertTrue(m.evaluate(0.0999).udp_ok)
        h = m.evaluate(0.1)
        self.assertTrue(not h.udp_ok and h.error)

    def test_own_heartbeat_id_ignored(self):
        m = ZoneMonitor(1, 0.0)
        m.heartbeat(1, 0, 0.0)
        self.assertNotIn((1, 0), m.hb)


class BlinkerTests(unittest.TestCase):
    def test_paddles_toggle_cancel_and_auto_cancel(self):
        b = Blinker()
        self.assertEqual(b.update(False, LEFT_BUTTON, 0), p.BLINK_LEFT)
        self.assertEqual(b.update(False, 0, 0), p.BLINK_LEFT)
        self.assertEqual(b.update(False, LEFT_BUTTON, 0), p.BLINK_OFF)
        b.update(False, 0, 0)
        self.assertEqual(b.update(False, RIGHT_BUTTON, 0), p.BLINK_RIGHT)
        b.update(False, 0, 9000)
        self.assertEqual(b.update(False, 0, 5000), p.BLINK_OFF)
        b.update(False, LEFT_BUTTON | RIGHT_BUTTON, 0)
        self.assertEqual(b.mode, p.BLINK_OFF)

    def test_error_forces_hazard_and_recovery_ignores_held_paddle(self):
        b = Blinker()
        self.assertEqual(b.update(True, LEFT_BUTTON, 0), p.BLINK_HAZARD)
        self.assertEqual(b.update(False, LEFT_BUTTON, 0), p.BLINK_OFF)
        self.assertEqual(b.update(False, LEFT_BUTTON, 0), p.BLINK_OFF)


class HistoryTests(unittest.TestCase):
    def test_same_bus_or_opposite_copy_is_suppressed(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x010, 0, 7, 0))
        self.assertFalse(h.first_copy(0x010, 0, 7, 0.0026))

    def test_expiry_not_extended_by_duplicates(self):
        h = FrameHistory()
        self.assertTrue(h.first_copy(0x010, 0, 0, 0))
        self.assertFalse(h.first_copy(0x010, 0, 0, WINDOW_S))
        self.assertTrue(h.first_copy(0x010, 0, 0, WINDOW_S + 0.001))

    def test_full_history_does_not_evict_live_entries(self):
        h = FrameHistory()
        for n in range(CAPACITY):
            self.assertTrue(h.first_copy(n, 0, 0, 0))
        with self.assertRaises(OverflowError):
            h.first_copy(100, 0, 0, 0)
        self.assertFalse(h.first_copy(0, 0, 0, 0.001))


if __name__ == "__main__":
    unittest.main()
