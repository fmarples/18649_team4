"""Exercise real bridge parsing/state logic with external UART/UDP/clock adapters."""
from collections import deque
from pathlib import Path
import struct
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'pi'))
import part2_bridge as bridge
import part2_protocol as protocol


# Make a real course packet; only the external transports and clock are replaced.
def wheel(seq, throttle):
    packet = bytearray(276)
    struct.pack_into('<Iii', packet, 0, seq, 0, throttle)
    struct.pack_into('<i', packet, 24, 32767)
    return bytes(packet)


# Run the real bridge until an external KeyboardInterrupt, recording its UART frames.
def capture(events, stop_at, pause_after_first_sleep=0, trace_events=None):
    queue = deque(events)
    clock = SimpleNamespace(now=0.0, slept=False)
    writes = []
    class Trace:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def udp_rx(self):
            if trace_events is not None: trace_events.append('udp')
        def command_tx(self):
            if trace_events is not None: trace_events.append('tx')

    class Udp:
        def bind(self, address): pass
        def setblocking(self, value): pass
        def close(self): pass
        def recvfrom(self, size):
            if not queue or queue[0][0] > clock.now:
                raise BlockingIOError
            return queue.popleft()[1], ('127.0.0.1', 9000)

    class Uart:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def reset_input_buffer(self): pass
        def read(self, size): return b''
        def write(self, data):
            if trace_events is not None: trace_events.append('write')
            writes.append((clock.now, struct.unpack_from('<IiiiI', data, 4)))
            return len(data)

    def sleep(dt):
        clock.now += pause_after_first_sleep if not clock.slept and pause_after_first_sleep else dt
        clock.slept = True
        if clock.now > stop_at:
            raise KeyboardInterrupt

    with patch.object(bridge, 'time', SimpleNamespace(monotonic=lambda: clock.now, sleep=sleep)), \
         patch.object(bridge.socket, 'socket', return_value=Udp()), \
         patch.object(bridge, 'create_trace', return_value=Trace()), \
         patch.dict(sys.modules, {'serial': SimpleNamespace(Serial=lambda *a, **kw: Uart())}), \
         patch.object(sys, 'argv', ['part2_bridge.py', '--mode', 'live']), \
         patch('builtins.print'):
        bridge.main()
    return writes


class BridgeFreshnessTests(unittest.TestCase):
    def test_trace_includes_invalid_udp_and_stop_frames(self):
        edges = []
        writes = capture([(0, wheel(1, 32767)), (0.001, b'bad')], .090, trace_events=edges)
        self.assertEqual(edges.count('udp'), 2)
        self.assertEqual(edges.count('tx'), len(writes))
        for i, event in enumerate(edges):
            if event == 'write': self.assertEqual(edges[i - 1], 'tx')
        self.assertTrue(any(fields[3] == -32768 for _, fields in writes))

    def test_timeout_discards_queued_throttle_instead_of_restarting(self):
        # The producer stops at 2 ms. A bridge scheduling pause ends at 120 ms.
        writes = capture([(0, wheel(100, -32768)), (0.001, wheel(101, -32768)),
                          (0.002, wheel(102, -32768))], 0.2, pause_after_first_sleep=0.12)
        after_pause = [fields for t, fields in writes if t >= 0.12]
        self.assertEqual(len(after_pause), 1)
        self.assertEqual(after_pause[0][1:4], (0, 32767, -32768))

    def test_invalid_input_does_not_accept_older_or_duplicate_pedals(self):
        writes = capture([(0, wheel(100, 32767)), (0.001, b'bad'),
                          (0.002, wheel(99, -32768)), (0.003, wheel(100, -32768)),
                          (0.004, wheel(101, -32768))], 0.015)
        drives = [(t, fields) for t, fields in writes if fields[2] == -32768]
        self.assertEqual(len(drives), 1)
        self.assertGreaterEqual(drives[0][0], 0.004)
        self.assertTrue(any(fields[3] == -32768 for _, fields in writes))

    def test_actual_timeout_allows_a_new_counter_baseline_after_invalid_input(self):
        writes = capture([(0, wheel(100, 32767)), (0.001, b'bad'),
                          (0.100, wheel(1, -32768))], 0.110)
        self.assertTrue(any(t >= 0.100 and fields[2] == -32768 for t, fields in writes))


if __name__ == '__main__':
    unittest.main()
