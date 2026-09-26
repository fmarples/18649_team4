"""The batch runner never repeats a failed duty or hides an inconsistent floor."""
import unittest

from run_motor_sweep import run_category


class SweepSequenceTests(unittest.TestCase):
    def test_descend_stop_at_failure_then_confirm_only_passing_floor(self):
        calls = []
        verdicts = iter(['STARTED', 'STARTED', 'NO_START', 'STARTED', 'STARTED'])

        def trial(duty):
            calls.append(duty)
            return {'verdict': next(verdicts), 'fault': 1 if duty == 50 else 0}

        result = run_category((60, 55, 50, 45), trial)
        self.assertEqual(calls, [60, 55, 50, 55, 55])
        self.assertEqual(result['lowest_passing_duty'], 55)
        self.assertEqual(result['failed_duty'], 50)
        self.assertTrue(result['confirmed_three_times'])

    def test_failed_highest_setting_never_escalates_or_retries(self):
        calls = []

        def trial(duty):
            calls.append(duty)
            return {'verdict': 'NO_START', 'fault': 1}

        result = run_category((60, 55, 50), trial)
        self.assertEqual(calls, [60])
        self.assertIsNone(result['lowest_passing_duty'])

    def test_unexpected_failure_aborts_without_another_trial(self):
        calls = []

        def trial(duty):
            calls.append(duty)
            raise RuntimeError('Reverse-motion guard')

        with self.assertRaises(RuntimeError):
            run_category((55, 50, 45), trial)
        self.assertEqual(calls, [55])

    def test_failed_confirmation_is_not_reported_as_reliable(self):
        verdicts = iter(['HELD', 'STALLED_DURING_HOLD', 'STALLED_DURING_HOLD'])
        result = run_category((45, 40), lambda duty: {'verdict': next(verdicts)})
        self.assertEqual(result['lowest_passing_duty'], 45)
        self.assertFalse(result['confirmed_three_times'])
        self.assertEqual(len(result['trials']), 3)


if __name__ == '__main__':
    unittest.main()
