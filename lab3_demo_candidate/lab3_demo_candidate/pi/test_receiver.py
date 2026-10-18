import sys
import types
import unittest
from unittest.mock import patch
try:
    import can
except ImportError:
    # Transport is not called by these real Receiver tests.
    sys.modules['can'] = types.ModuleType('can')
import can_protocol as p
from cockpit_bridge import Receiver

class Log:
    def __init__(self): self.rows = []
    def write(self, **row): self.rows.append(row)

def message(frame_id, data, bus='can0'):
    return types.SimpleNamespace(arbitration_id=frame_id, data=data, dlc=len(data),
        channel=bus, is_extended_id=False, is_remote_frame=False, is_error_frame=False)

class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.log = Log()
        self.hb, self.states = {}, {}
        self.force, self.fault = {'counter':0}, {'latched':False}
        self.rx = Receiver(self.log, self.hb, self.states, self.force, self.fault)

    @patch('cockpit_bridge.time.monotonic_ns', return_value=100)
    def test_late_fault_duplicate_cannot_undo_clear(self, _clock):
        fault = p.pack_fault(1, p.ZONE_N3, 1)
        clear = p.pack_fault(2, p.ZONE_N3, 0)
        self.rx.on_message_received(message(p.FAULT, fault))
        self.rx.on_message_received(message(p.FAULT, clear))
        self.rx.on_message_received(message(p.FAULT, fault, 'can1'))
        self.assertFalse(self.fault['latched'])
        self.assertEqual(self.log.rows[-1]['detail'], 'valid_crc_duplicate')

    @patch('cockpit_bridge.time.monotonic_ns', return_value=100)
    def test_duplicate_heartbeat_still_updates_both_bus_times(self, _clock):
        data = p.pack_heartbeat(1, p.STATE_OK, True, True)
        for bus in ('can0', 'can1'):
            self.rx.on_message_received(message(p.HB_N3, data, bus))
        self.assertEqual(len(self.hb), 2)
        self.assertEqual(self.log.rows[-1]['detail'], 'valid_crc_duplicate')

    def test_invalid_frames_do_not_poison_history(self):
        data = p.pack_force(1, 25)
        bad = message(p.FORCE, data[:-1] + bytes([data[-1] ^ 1]))
        self.rx.on_message_received(bad)
        extended = message(p.FORCE, data); extended.is_extended_id = True
        self.rx.on_message_received(extended)
        self.assertEqual(self.force['counter'], 0)
        self.rx.on_message_received(message(p.FORCE, data))
        self.assertEqual(self.force['counter'], 25)

if __name__ == '__main__': unittest.main()
