"""Exercise the GUI's public telemetry input with real protocol bytes, no Qt/hardware."""
from pathlib import Path
import struct
import sys
import unittest
import zlib

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from windows.current_telemetry import TelemetryHistory


# Independent wire fixture: includes negative current, real zero and a clipped reading.
def frame(seq=1, tick=20, mask=7, currents=(-1000, 0, 4320)):
    body = struct.pack('<2sBBIIIIiiiiiiII', b'L2', 1, 2, seq, tick, 0, 1,
                       0, 32767, 32767, *currents, mask, 0)
    return body + struct.pack('<I', zlib.crc32(body))


class CurrentTelemetryTests(unittest.TestCase):
    def test_forwarded_status_is_byte_identical_to_mcu_frame(self):
        from pi.part2_protocol import pop_status, status_frame
        packet = frame()
        decoded = list(pop_status(bytearray(packet)))[0]
        decoded['pi_receive_s'] = 123.4
        self.assertEqual(status_frame(decoded), packet)

    def test_valid_frame_preserves_signed_values_and_real_zero(self):
        history = TelemetryHistory()
        self.assertTrue(history.receive(frame(), 10.0))
        self.assertEqual(history.samples[-1].amps, (-1.0, 0.0, 4.32))
        self.assertFalse(history.stale(10.1))
        self.assertTrue(history.stale(10.5))

    def test_disconnected_right_never_enters_plot_data_even_with_valid_adc_bit(self):
        history = TelemetryHistory(connected_channels=('left', 'servo'))
        history.receive(frame(currents=(680, -7000, 900)), 1.0)
        self.assertEqual(history.samples[-1].amps, (0.68, None, 0.9))
        self.assertEqual(history.status['current_right_mA'], -7000)
        history.receive(frame(seq=2, tick=40, currents=(680, 4320, 900)), 1.02)
        self.assertEqual(history.samples[-1].amps, (0.68, None, 0.9))
        with self.assertRaises(ValueError):
            TelemetryHistory(connected_channels=('typo',))

    def test_bad_crc_truncation_and_duplicates_do_not_refresh_live_data(self):
        history = TelemetryHistory()
        self.assertTrue(history.receive(frame(seq=10), 1.0))
        bad = bytearray(frame(seq=11)); bad[-1] ^= 1
        for packet in (bytes(bad), frame()[:-1], frame(seq=10), frame(seq=9)):
            self.assertFalse(history.receive(packet, 1.1))
        self.assertEqual(len(history.samples), 1)
        self.assertTrue(history.stale(1.5))
        self.assertFalse(history.receive(frame(seq=10), 2.0))
        self.assertTrue(history.stale(2.0))

    def test_missing_channels_packet_gaps_wrap_and_reconnect(self):
        history = TelemetryHistory()
        history.receive(frame(seq=0xffffffff, mask=3, currents=(0, -2147483648, 99)), 1.0)
        self.assertEqual(history.samples[-1].amps, (0.0, None, None))
        history.receive(frame(seq=0), 1.02)
        self.assertFalse(history.samples[-1].gap)
        history.receive(frame(seq=2), 1.06)
        self.assertTrue(history.samples[-1].gap)
        # A reboot/reconnect may establish a new sequence baseline after silence.
        self.assertTrue(history.receive(frame(seq=0, tick=0), 2.0))
        self.assertTrue(history.samples[-1].gap)
        for seq in range(1, 4000):
            history.receive(frame(seq=seq), 2.0 + seq * .02)
        self.assertLessEqual(len(history.samples), 1501)
        self.assertGreaterEqual(history.samples[0].received_s, history.last_received - 30)


if __name__ == '__main__':
    unittest.main()
