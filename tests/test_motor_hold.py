"""Independent encoder/time examples for the powered holding-speed report."""
import unittest
from dataclasses import replace

from check_motor_hold import parse_sample, summarize_hold


# Fixtures use 1320 counts/rev; 660 counts/second is exactly 30 wheel RPM.
def sample(t, stage, left, duty=55, fault=0, invalid=0):
    phase = 'LEFT' if stage != 'OFF' else 'IDLE'
    pct = duty if stage == 'HOLD' else 60 if stage == 'KICK' else 0
    return parse_sample(f'SAMPLE t_ms={t} stage={stage} phase={phase} left_pct={pct} right_pct=0 left={left} right=12 invalid_left={invalid} invalid_right=0 errors=0 fault={fault}')


class HoldingSpeedTests(unittest.TestCase):
    def test_both_reports_each_wheel_and_average_not_cancelling_raw_signs(self):
        original = [sample(0, 'KICK', 0), sample(200, 'HOLD', -100),
                    sample(1200, 'HOLD', -760), sample(1450, 'HOLD', -925),
                    sample(1700, 'HOLD', -1090), sample(1950, 'HOLD', -1255),
                    sample(2150, 'HOLD', -1387), sample(2200, 'OFF', -1600)]
        both = [replace(s, phase='BOTH' if s.stage != 'OFF' else 'IDLE',
                        right_pct=s.left_pct, right=-2 * s.left) for s in original]
        result = summarize_hold(both, 'BOTH', 55)
        self.assertAlmostEqual(result['wheels']['LEFT']['late_rpm'], 30)
        self.assertAlmostEqual(result['wheels']['RIGHT']['late_rpm'], 60)
        self.assertAlmostEqual(result['late_rpm'], 45)
        for fault in (1, 2):
            failed = both[:2] + [replace(both[-1], fault=fault)]
            self.assertEqual(summarize_hold(failed, 'BOTH', 55)['verdict'], 'STALLED_DURING_HOLD')

    def test_timestamped_powered_window_excludes_kick_and_coast(self):
        samples = [sample(0, 'KICK', 0), sample(200, 'HOLD', -100),
                   sample(1200, 'HOLD', -760), sample(1450, 'HOLD', -925),
                   sample(1700, 'HOLD', -1090), sample(1950, 'HOLD', -1255),
                   sample(2150, 'HOLD', -1387), sample(2200, 'OFF', -1600),
                   sample(3000, 'OFF', -2000)]
        result = summarize_hold(samples, 'LEFT', 55)
        self.assertEqual(result['verdict'], 'HELD')
        self.assertEqual(result['late_window_ms'], 950)
        self.assertAlmostEqual(result['late_rpm'], 30)
        self.assertAlmostEqual(result['late_m_per_s'], 0.1178097245)
        self.assertTrue(result['settled_in_late_window'])

    def test_four_second_hold_uses_final_second_and_flags_deceleration(self):
        samples = [sample(0, 'KICK', 0), sample(200, 'HOLD', -100),
                   sample(3200, 'HOLD', -1000), sample(3450, 'HOLD', -1100),
                   sample(3700, 'HOLD', -1200), sample(3950, 'HOLD', -1250),
                   sample(4150, 'HOLD', -1290), sample(4200, 'OFF', -1350)]
        result = summarize_hold(samples, 'LEFT', 55, 4000)
        self.assertEqual(result['late_window_ms'], 950)
        self.assertAlmostEqual(result['late_rpm'], 13.8755980861)
        self.assertFalse(result['settled_in_late_window'])

    def test_fault_never_becomes_a_successful_holding_speed(self):
        samples = [sample(0, 'KICK', 0), sample(200, 'HOLD', -100, 45),
                   sample(300, 'HOLD', -120, 45), sample(450, 'OFF', -120, fault=1)]
        result = summarize_hold(samples, 'LEFT', 45)
        self.assertEqual(result['verdict'], 'STALLED_DURING_HOLD')
        self.assertIsNone(result['late_rpm'])

    def test_reset_wrong_duty_encoder_errors_and_short_run_rejected(self):
        good = [sample(0, 'KICK', 0), sample(200, 'HOLD', -100)]
        for samples in [good + [sample(100, 'OFF', -110)],
                        [sample(0, 'KICK', 0), sample(200, 'HOLD', -100, 50)],
                        good + [sample(300, 'HOLD', -110, invalid=1)],
                        good + [sample(300, 'OFF', -110)]]:
            with self.assertRaises(RuntimeError):
                summarize_hold(samples, 'LEFT', 55)


if __name__ == '__main__':
    unittest.main()
