"""Exercise real persistent GUI logs without starting Qt windows or hardware."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest


@unittest.skipUnless(importlib.util.find_spec('PyQt5'), 'Requires course PyQt5 environment')
class EventLoggingTests(unittest.TestCase):
    def test_no_data_polling_noise_is_not_an_event_or_console_output(self):
        from windows.telemetry_gui import SessionLog
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                log = SessionLog(directory)
                try:
                    for _ in range(10):
                        print('No data')
                    print('connected to a steering wheel at index 0')
                finally:
                    log.close()
            text = log.path.read_text(encoding='utf-8')
            self.assertNotIn('No data', text)
            self.assertNotIn('No data', output.getvalue())
            self.assertIn('Connection', text)
            self.assertIn('connected to a steering wheel', text)

    def test_continuous_frames_are_separate_from_categorized_events(self):
        import json
        from windows.telemetry_gui import SessionLog
        with tempfile.TemporaryDirectory() as directory:
            log = SessionLog(directory)
            try:
                log.record('ADC unavailable', 'Sensor status')
                log.capture_frame(b'abc', {'current_valid_mask': 0})
                self.assertEqual(len(log.lines), 1)
                self.assertEqual(log.lines[0].category, 'Sensor status')
            finally:
                log.close()
            event_text = log.path.read_text(encoding='utf-8')
            self.assertIn('Sensor status  ADC unavailable', event_text)
            self.assertNotIn('616263', event_text)
            frame = json.loads(log.frames_path.read_text(encoding='utf-8'))
            self.assertEqual(frame['hex'], '616263')
            self.assertEqual(frame['status'], {'current_valid_mask': 0})


if __name__ == '__main__':
    unittest.main()
