"""Physical-input events observe the unchanged course proxy packet, not MCU echoes."""
import struct
import unittest
from windows.wheel_input_log import WheelInputEvents


def packet(steer=0, throttle=32767, brake=32767, buttons=(), pov=0xffffffff, slider=32767):
    data = bytearray(276)
    struct.pack_into('<8i4I', data, 4, steer, throttle, 0, 0, 0, brake, slider, 0,
                     pov, 0xffffffff, 0xffffffff, 0xffffffff)
    for index in buttons:
        data[52 + index] = 128
    return bytes(data)


class WheelInputTests(unittest.TestCase):
    def test_buttons_paddles_and_high_indices_are_edges_not_polling_lines(self):
        events = WheelInputEvents()
        events.receive(packet())
        changed = events.receive(packet(buttons=(0, 5, 127)))
        self.assertEqual([e.category for e in changed], ['Buttons'] * 3)
        self.assertIn('A / self-test (button 0) pressed', changed[0].text)
        self.assertIn('left turn-signal request', changed[1].text)
        self.assertIn('button 5) pressed', changed[1].text)
        self.assertEqual(changed[2].text, 'Button 127 pressed')
        self.assertEqual(events.receive(packet(buttons=(0, 5, 127))), [])
        released = events.receive(packet())
        self.assertEqual(len(released), 3)
        self.assertTrue(all(e.text.endswith('released') for e in released))

    def test_wheel_and_pedals_include_position_change_and_raw_without_duplicates(self):
        events = WheelInputEvents()
        initial = events.receive(packet())
        self.assertTrue(any('Wheel: centered' in e.text for e in initial))
        self.assertEqual(events.receive(packet()), [])
        changed = events.receive(packet(steer=-32768, throttle=-32768, brake=0))
        self.assertEqual([e.category for e in changed], ['Steering', 'Pedals', 'Pedals'])
        self.assertIn('left 100.000%', changed[0].text)
        self.assertIn('change -100.000 percentage points', changed[0].text)
        self.assertIn('raw=-32768', changed[0].text)
        self.assertIn('Accelerator: pressed 100.000%', changed[1].text)
        self.assertIn('Brake: pressed 49.999%', changed[2].text)
        released = events.receive(packet())
        self.assertIn('Accelerator: released 0.000%', released[1].text)
        self.assertIn('change -100.000', released[1].text)
        # Do not hide small physical changes behind a display deadband.
        tiny = events.receive(packet(steer=1))
        self.assertEqual(len(tiny), 1)
        self.assertIn('raw=1', tiny[0].text)

    def test_dpad_and_auxiliary_axis_changes_and_initial_held_button(self):
        events = WheelInputEvents()
        initial = events.receive(packet(buttons=(4,)))
        self.assertTrue(any('button 4) held on first sample' in e.text for e in initial))
        changed = events.receive(packet(buttons=(4,), pov=9000, slider=1000))
        self.assertTrue(any('D-pad / POV 0: right' in e.text for e in changed))
        self.assertTrue(any('Slider 0' in e.text and 'raw=1000' in e.text for e in changed))
        self.assertEqual(events.receive(packet(buttons=(4,), pov=9000, slider=1000)), [])
        self.assertTrue(any('centered' in e.text for e in events.receive(packet(buttons=(4,), slider=1000))))
        with self.assertRaises(ValueError):
            events.receive(b'bad')

    def test_socket_observer_preserves_bytes_destination_return_and_close(self):
        from windows.wheel_input_log import InputLoggingSocket
        from unittest.mock import Mock
        transport = Mock()
        transport.sendto.return_value = 276
        log = Mock()
        observed = InputLoggingSocket(transport, log)
        data, target = packet(buttons=(4,)), ('172.26.166.33', 8000)
        self.assertEqual(observed.sendto(data, target), 276)
        transport.sendto.assert_called_once_with(data, target)
        self.assertTrue(any('right turn-signal request' in call.args[0] for call in log.record.call_args_list))
        before = log.record.call_count
        observed.sendto(data, target)
        self.assertEqual(log.record.call_count, before)
        observed.reset()
        observed.sendto(data, target)
        self.assertGreater(log.record.call_count, before)
        observed.close()
        transport.close.assert_called_once()
        transport.sendto.side_effect = OSError('network unavailable')
        log.reset_mock()
        with self.assertRaises(OSError):
            observed.sendto(packet(throttle=-32768), target)
        self.assertTrue(any('Accelerator: pressed 100.000%' in call.args[0]
                            for call in log.record.call_args_list))


if __name__ == '__main__':
    unittest.main()
