import sys
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pi'))
import timing_gpio
from part2_bridge import current_summary

class TimingTests(unittest.TestCase):
    def test_opt_in_lifetime_edges_and_cleanup(self):
        events = []
        class Request:
            def set_value(self, pin, value): events.append((pin, value))
            def set_values(self, values): events.append(values)
            def release(self): events.append('released')
        def request_lines(chip, **kwargs):
            self.assertEqual(chip, '/dev/testchip')
            self.assertEqual(set(kwargs['config']), {(17, 27)})
            return Request()
        fake = SimpleNamespace(request_lines=request_lines, LineSettings=lambda **kw: kw)
        line = SimpleNamespace(Direction=SimpleNamespace(OUTPUT='out'),
                               Value=SimpleNamespace(ACTIVE=1, INACTIVE=0))
        with patch.dict(sys.modules, {'gpiod': fake, 'gpiod.line': line}):
            with timing_gpio.create_trace(False) as disabled:
                disabled.udp_rx(); disabled.command_tx()
            self.assertEqual(events, [])
            with self.assertRaises(RuntimeError):
                with timing_gpio.create_trace(True, '/dev/testchip') as trace:
                    trace.udp_rx(); trace.udp_rx(); trace.command_tx()
                    raise RuntimeError('test cleanup during failure')
        self.assertEqual(events, [(17, 1), (17, 0), (27, 1), {17: 0, 27: 0}, 'released'])

    def test_current_display_obeys_validity_not_numeric_zero(self):
        status = dict(current_left_mA=0, current_right_mA=-12,
                      current_servo_mA=-2147483648, current_valid_mask=7)
        self.assertEqual(current_summary(status), 'left=0mA right=-12mA servo=UNAVAILABLE')
        status['current_valid_mask'] = 0
        self.assertEqual(current_summary(status),
                         'left=UNAVAILABLE right=UNAVAILABLE servo=UNAVAILABLE')

if __name__ == '__main__': unittest.main()
