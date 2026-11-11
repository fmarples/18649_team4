"""Timing observation must neither fabricate input nor change callback behavior."""
import unittest
from windows.wheel_timing import TimedCallback


class Log:
    def __init__(self):
        self.rows = []

    def record(self, *args):
        self.rows.append(args)


class TimingTests(unittest.TestCase):
    def test_scheduler_gap_is_distinct_from_callback_work(self):
        log, calls = Log(), []
        clock = iter([0, .001, .125, .127])
        observed = TimedCallback('send', lambda x: calls.append(x) or x, log, lambda: next(clock))
        self.assertEqual(observed(1), 1)
        self.assertEqual(observed(2), 2)
        self.assertEqual(calls, [1, 2])
        self.assertEqual(len(log.rows), 1)
        self.assertIn('entry_gap_ms=125.0', log.rows[0][0])
        self.assertIn('work_ms=2.000', log.rows[0][0])

    def test_slow_call_is_logged_even_when_callback_raises(self):
        log = Log()
        def failing():
            raise ValueError('SDK error')
        clock = iter([0, .030])
        observed = TimedCallback('sample', failing, log, lambda: next(clock))
        with self.assertRaisesRegex(ValueError, 'SDK error'):
            observed()
        self.assertIn('work_ms=30.000', log.rows[0][0])

    def test_reconnect_resets_gap_and_logging_failure_is_nonfatal(self):
        log = Log()
        clock = iter([0, .001, 20, 20.001, 21, 21.001])
        observed = TimedCallback('send', lambda: 42, log, lambda: next(clock))
        observed()
        observed.reset()
        observed()
        self.assertEqual(log.rows, [])
        def failing_log(*args):
            raise RuntimeError('disk')
        log.record = failing_log
        self.assertEqual(observed(), 42)


if __name__ == '__main__':
    unittest.main()
