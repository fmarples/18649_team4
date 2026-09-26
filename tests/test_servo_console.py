import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location("servo_console", Path(__file__).parents[1] / "windows/servo_console.py")
console = importlib.util.module_from_spec(spec)
spec.loader.exec_module(console)

class CalibrationFileTests(unittest.TestCase):
    def test_accept_both_directions_and_reject_bad_geometry(self):
        for points in ((1100, 1510, 1850), (1850, 1510, 1100)):
            data = dict(zip(("left_us", "center_us", "right_us"), points), period_us=20000)
            self.assertEqual(console.validate_calibration(data), list(points))
        for points in ((1500, 1500, 1800), (500, 2500, 1500), (499, 1500, 1800), (1100, True, 1850)):
            with self.assertRaises(ValueError):
                console.validate_calibration(dict(zip(("left_us", "center_us", "right_us"), points), period_us=20000))

    def test_wrong_period_missing_fields_and_error_responses(self):
        with self.assertRaises(ValueError):
            console.validate_calibration(dict(left_us=1100, center_us=1500, right_us=1850, period_us=1000))
        with self.assertRaises(ValueError):
            console.parse_status("SERVO OK mode=0")
        with self.assertRaises(ValueError):
            console.parse_status("SERVO ERR mode=0 pulse=0 left=0 center=0 right=0 marks=0 valid=0")
        self.assertEqual(console.parse_status("SERVO OK mode=0 pulse=0 left=0 center=0 right=0 marks=0 valid=0")["pulse"], 0)

if __name__ == "__main__":
    unittest.main()
