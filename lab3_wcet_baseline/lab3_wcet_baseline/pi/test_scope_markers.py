"""Keep scope edge pairs aligned when the bridge combines queued UDP updates."""
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('lab3_scope_markers', Path(__file__).with_name('timing_gpio.py'))
timing = importlib.util.module_from_spec(spec)
spec.loader.exec_module(timing)


class ScopeMarkerTests(unittest.TestCase):
    def test_coalesced_receives_and_stale_commands_keep_matching_edges(self):
        events = []
        class Request:
            def set_value(self, pin, value): events.append((pin, value))
            def set_values(self, values): events.append(values)
            def release(self): events.append('released')
        fake = SimpleNamespace(request_lines=lambda *a, **kw: Request(), LineSettings=lambda **kw: kw)
        line = SimpleNamespace(Direction=SimpleNamespace(OUTPUT='out'), Value=SimpleNamespace(ACTIVE=1, INACTIVE=0))
        with patch.dict(sys.modules, {'gpiod': fake, 'gpiod.line': line}):
            with timing.create_trace(True) as trace:
                trace.cmd_tx()  # No UDP yet: no unmatched command edge.
                trace.udp_rx()
                trace.udp_rx()  # Same drained batch: no second start edge.
                trace.cmd_tx()
                trace.cmd_tx()  # Stale re-send: no extra edge.
                trace.udp_rx()
                trace.cmd_tx()
            self.assertEqual(events, [(17, 1), (27, 1), (17, 0), (27, 0),
                {17: 0, 27: 0, 22: 0, 23: 0}, 'released'])


if __name__ == '__main__':
    unittest.main()
