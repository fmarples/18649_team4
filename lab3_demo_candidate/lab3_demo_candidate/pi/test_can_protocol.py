import unittest
import can_protocol as p

class ProtocolTests(unittest.TestCase):
    def test_ctrl_round_trip(self):
        raw = p.pack_ctrl(14, -1234, 45, 7, 0xA5)
        got = p.unpack_ctrl(raw)
        self.assertEqual((got['seq'], got['steer'], got['throttle'], got['brake'], got['buttons']), (14,-1234,45,7,0xA5))
    def test_crc_detects_corruption(self):
        raw = bytearray(p.pack_ctrl(1,0,0,0,0)); raw[3] ^= 1
        self.assertFalse(p.valid(bytes(raw)))
    def test_heartbeat_round_trip(self):
        got = p.unpack_heartbeat(p.pack_heartbeat(3, p.STATE_OK, True, False))
        self.assertEqual((got['seq'], got['state'], got['health']), (3,p.STATE_OK,1))
    def test_fault_round_trip(self):
        got = p.unpack_fault(p.pack_fault(7, p.ZONE_N2, 1, 123))
        self.assertEqual((got['zone'], got['reason'], got['detail']), (p.ZONE_N2,1,123))
    def test_blink_round_trip(self):
        got = p.unpack_blink(p.pack_blink(4,p.BLINK_HAZARD,1,123456))
        self.assertEqual((got['mode'],got['phase'],got['phase_epoch_ms']), (p.BLINK_HAZARD,1,123456))

if __name__ == '__main__': unittest.main()
