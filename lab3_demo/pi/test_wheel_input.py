import struct, unittest
from wheel_input import decode_wheel_packet, UDP_PACKET_BYTES

class WheelInputTests(unittest.TestCase):
    def make_packet(self, steer=0, throttle=32767, brake=32767, buttons=()):
        b=bytearray(UDP_PACKET_BYTES)
        struct.pack_into('<I',b,0,1234)
        struct.pack_into('<ii',b,4,steer,throttle)
        struct.pack_into('<i',b,24,brake)
        for i in buttons: b[52+i]=0x80
        return bytes(b)
    def test_released_pedals(self):
        self.assertEqual(decode_wheel_packet(self.make_packet())[2:4],(0,0))
    def test_pressed_pedals(self):
        self.assertEqual(decode_wheel_packet(self.make_packet(throttle=-32768,brake=-32768))[2:4],(100,100))
    def test_buttons_and_steering(self):
        counter,steer,throttle,brake,buttons=decode_wheel_packet(self.make_packet(steer=-1200,buttons=(0,3,7)))
        self.assertEqual((counter,steer,buttons),(1234,-1200,0x89))
    def test_bad_length(self):
        with self.assertRaises(ValueError): decode_wheel_packet(b'bad')

if __name__=='__main__': unittest.main()
