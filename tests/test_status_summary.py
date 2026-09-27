from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from summarize_status import summarize

def row(seq, tick, state=1, valid=0):
    return dict(status_seq=seq, stm_ms=tick, state=state, current_valid_mask=valid,
                current_left_mA=0, current_right_mA=-10, current_servo_mA=-2147483648)

class SummaryTests(unittest.TestCase):
    def test_wrap_gaps_and_invalid_current(self):
        result = summarize([row(0xfffffffe, 0xfffffff0), row(0xffffffff, 4, valid=7),
                            row(0, 24), row(2, 64), row(3, 100), row(0, 0)])
        self.assertEqual(result['frames'], 6)
        self.assertEqual(result['missing_sequence_numbers'], 1)
        self.assertEqual(result['sequence_discontinuities'], 1)
        self.assertEqual(result['consecutive_mcu_intervals'], 3)
        self.assertEqual(result['mcu_intervals_outside_18_22_ms'], 1)
        self.assertEqual(result['valid_current_frames'], dict(left=1, right=1, servo=0))
    def test_empty_and_single_capture(self):
        with self.assertRaises(ValueError): summarize([])
        self.assertIsNone(summarize([row(0, 0)])['mcu_interval_mean_ms'])

if __name__ == '__main__': unittest.main()
