"""Check startup failure reporting through the real CLI without opening any hardware."""
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('PyQt5'), 'Use the course proxy Python with PyQt5')
class GuiStartupTests(unittest.TestCase):
    def test_busy_monitor_port_fails_explicitly_and_persists_stack_trace(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as occupied:
            occupied.bind(('127.0.0.1', 0))
            port = occupied.getsockname()[1]
            env = dict(os.environ, QT_QPA_PLATFORM='offscreen')
            result = subprocess.run(
                [sys.executable, str(repo / 'windows/start_wheel_proxy.py'), '--monitor-only',
                 '--pi', '127.0.0.1', '--telemetry-port', str(port), '--log-dir', directory],
                cwd=repo, env=env, capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            reports = list(Path(directory).glob('*.crash.txt'))
            self.assertEqual(len(reports), 1)
            report = reports[0].read_text(encoding='utf-8')
            self.assertIn('Traceback', report)
            self.assertIn('OSError', report)
            self.assertIn('TelemetryWindows', report)
            logs = list(Path(directory).glob('*.log'))
            self.assertEqual(len(logs), 1)
            self.assertIn('ERROR', logs[0].read_text(encoding='utf-8'))
            # The failing GUI must not close the socket owned by this test.
            self.assertEqual(occupied.getsockname()[1], port)


if __name__ == '__main__':
    unittest.main()
