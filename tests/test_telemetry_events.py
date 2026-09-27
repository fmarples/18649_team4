"""Event output is driven by changes in received MCU status, not sample cadence."""
import unittest
from windows.telemetry_events import TelemetryEvents


def status(**changes):
    return dict(state=1, current_valid_mask=7, current_left_mA=10,
                current_right_mA=20, current_servo_mA=30, **changes)


class TelemetryEventTests(unittest.TestCase):
    def test_samples_log_initial_state_but_not_continuous_current_changes(self):
        events = TelemetryEvents()
        first = events.receive(status())
        self.assertEqual([event.category for event in first], ['Connection', 'Connection', 'Sensor status'])
        for value in range(100):
            sample = status()
            sample.update(current_left_mA=value, status_seq=value, stm_ms=value * 20)
            self.assertEqual(events.receive(sample), [])

    def test_disconnected_sensor_never_generates_sample_driven_events(self):
        events = TelemetryEvents(connected_channels=('left', 'servo'))
        first = events.receive(status())
        sensor = [e for e in first if e.category == 'Sensor status'][0]
        self.assertEqual(sensor.text, 'left: available; servo: available')
        sample = status()
        for raw in (-7000, 4320, -2147483648):
            sample['current_right_mA'] = raw
            self.assertEqual(events.receive(sample), [])

    def test_loss_and_recovery_each_emit_once_and_refresh_sensor_state(self):
        events = TelemetryEvents()
        self.assertEqual(events.stale(), [])
        events.receive(status())
        self.assertEqual([(e.category, e.text) for e in events.stale()],
                         [('Errors', 'Telemetry stale: no fresh status for 500 ms')])
        self.assertEqual(events.stale(), [])
        self.assertEqual([e.category for e in events.receive(status())],
                         ['Connection', 'Connection', 'Sensor status'])

    def test_invalid_and_ceiling_transitions_not_numeric_changes(self):
        events = TelemetryEvents()
        sample = status()
        events.receive(sample)
        sample['current_left_mA'] = -2147483648
        changed = events.receive(sample)
        self.assertEqual(len(changed), 1)
        self.assertIn('left: unavailable', changed[0].text)
        self.assertEqual(events.receive(sample), [])
        sample['current_left_mA'] = 4320
        self.assertIn('left: ceiling', events.receive(sample)[0].text)
        sample['current_left_mA'] = -250
        self.assertIn('left: available', events.receive(sample)[0].text)
        sample['state'] = 2
        self.assertEqual([(e.category, e.text) for e in events.receive(sample)],
                         [('Errors', 'MCU state: ERROR_TIMEOUT')])


if __name__ == '__main__':
    unittest.main()
