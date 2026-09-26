"""Startup verdicts use powered encoder samples, never coast-down totals."""
import unittest

from check_motor_startup import classify_start


class StartupVerdictTests(unittest.TestCase):
    def test_both_requires_both_to_start_and_rejects_either_stall(self):
        self.assertEqual(classify_start((100, 200), [(80, 224)], 0, 'BOTH'), 'STARTED')
        self.assertEqual(classify_start((0, 0), [(-2, 1)], 1, 'BOTH'), 'NO_START')
        self.assertEqual(classify_start((0, 0), [(-20, 2)], 2, 'BOTH'), 'PARTIAL_START')
        self.assertEqual(classify_start((0, 0), [(-20, 2)], 0, 'BOTH'), 'INSUFFICIENT_MOTION')
        with self.assertRaises(RuntimeError):
            classify_start((0, 0), [(-20, -5)], 4, 'BOTH')

    def test_forward_motion_during_power(self):
        self.assertEqual(classify_start((100, 200), [(90, 200), (60, 200)], 0, 'LEFT'), 'STARTED')
        self.assertEqual(classify_start((100, 200), [(100, 212)], 0, 'RIGHT'), 'STARTED')

    def test_no_progress_cutoff_is_not_success(self):
        self.assertEqual(classify_start((100, 200), [(100, 200)], 1, 'LEFT'), 'NO_START')
        self.assertEqual(classify_start((100, 200), [(100, 200)], 2, 'RIGHT'), 'NO_START')

    def test_motion_followed_by_stall_is_inconclusive(self):
        self.assertEqual(classify_start((0, 0), [(-20, 0)], 1, 'LEFT'), 'ABORTED_AFTER_MOTION')

    def test_insufficient_motion_is_not_a_success(self):
        self.assertEqual(classify_start((0, 0), [(-3, 0)], 0, 'LEFT'), 'INSUFFICIENT_MOTION')

    def test_faults_wrong_direction_and_other_wheel_abort(self):
        for counts, fault in [([(10, 0)], 0), ([(-20, 1)], 0), ([(-20, 0)], -5), ([(-20, 0)], 2)]:
            with self.assertRaises(RuntimeError):
                classify_start((0, 0), counts, fault, 'LEFT')

    def test_missing_powered_encoder_data_is_not_no_start(self):
        with self.assertRaises(RuntimeError):
            classify_start((0, 0), [], 1, 'LEFT')


if __name__ == '__main__':
    unittest.main()
