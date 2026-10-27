"""Independent numerical checks for the analytical CCM and divider screens.

Run: python -m unittest test_power_margins.py (from lab4).
These verify arithmetic, not the physical assumptions or a fabrication release.
"""
import cmath
import math
import unittest

from check_power_margins import buck_scenario, feedback_network


class PowerMarginChecks(unittest.TestCase):
    def test_ccm_against_sampled_waveforms(self):
        # Integrate piecewise-linear inductor current and the actual switch
        # states. Input capacitor current is pulsed switch current minus its
        # cycle average; output capacitor current is inductor minus load.
        vin, vout, load, inductance, frequency = 12, 5, 3, 4.7e-6, 600000
        case = buck_scenario(vin, vout, load, inductance, frequency, 1, 20)
        period, duty, samples = 1/frequency, vout/vin, 120000
        rise = (vin-vout)/inductance
        fall = -vout/inductance
        valley = load-rise*duty*period/2
        inputs, outputs, losses = [], [], []
        for n in range(samples):
            t = (n+.5)*period/samples
            on = t < duty*period
            current = (valley+rise*t if on else
                       valley+rise*duty*period+fall*(t-duty*period))
            inputs.append(current if on else 0)
            outputs.append(current-load)
            losses.append(current*current*(.055 if on else .0243))
        average_input = sum(inputs)/samples
        input_rms = math.sqrt(sum((i-average_input)**2 for i in inputs)/samples)
        output_rms = math.sqrt(sum(i*i for i in outputs)/samples)
        self.assertAlmostEqual(input_rms, case["input_cap_ripple_A_rms_ideal"], places=8)
        self.assertAlmostEqual(output_rms, case["output_cap_ripple_A_rms_ideal"], places=8)
        self.assertAlmostEqual(sum(losses)/samples, case["conduction_W"], places=8)
        self.assertAlmostEqual(average_input*vin, load*vout, places=8)
        self.assertAlmostEqual(case["switch_overlap_W_assumed"], .216, places=10)

    def test_passive_divider_against_complex_impedances(self):
        for c in (22, 30, 82, 91):
            top, bottom, frequency = 75000, 10000, 66000
            zc = 1/(2j*math.pi*frequency*c*1e-12)
            ztop = 1/(1/top+1/zc)
            transfer = bottom/(bottom+ztop)
            _, _, phase = feedback_network(top, bottom, c, frequency)
            self.assertAlmostEqual(math.degrees(cmath.phase(transfer)), phase, places=10)

    def test_eco_mode_invalidates_negative_ccm_valley(self):
        case = buck_scenario(15, 3.318, .8, 3.76e-6, 400000, 1, 20)
        self.assertFalse(case["ccm_assumption_valid"])
        self.assertNotIn("conduction_W", case)
        self.assertNotIn("output_cap_ripple_A_rms_ideal", case)

    def test_invalid_buck_voltage_rejected(self):
        with self.assertRaises(ValueError):
            buck_scenario(5, 6, 1, 4.7e-6, 600000, 1, 20)


if __name__ == "__main__":
    unittest.main()
