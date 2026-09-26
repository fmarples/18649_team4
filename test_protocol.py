import importlib.util
from pathlib import Path
import struct
import unittest
import zlib
import sys
from types import SimpleNamespace
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('protocol', Path(__file__).parent/'pi'/'part2_protocol.py')
p = importlib.util.module_from_spec(spec)
spec.loader.exec_module(p)


class ProtocolTests(unittest.TestCase):
    def test_crc_standard_vector(self):
        self.assertEqual(zlib.crc32(b'123456789'), 0xcbf43926)

    def test_command_wire_layout(self):
        frame = p.command(0x12345678, -32768, 32767, -32768, (1<<4)|(1<<5))
        self.assertEqual(len(frame), 28)
        self.assertEqual(frame[:8], b'L2\x01\x01\x78\x56\x34\x12')
        self.assertEqual(struct.unpack_from('<iiiI', frame, 8), (-32768,32767,-32768,48))
        self.assertEqual(struct.unpack_from('<I',frame,24)[0],zlib.crc32(frame[:24]))

    def test_wheel_offsets_and_indices(self):
        packet = bytearray(276)
        struct.pack_into('<Iii', packet, 0, 15, -32768, 32767)
        struct.pack_into('<i', packet, 24, -32768)
        packet[52] = packet[57] = packet[62] = 128
        self.assertEqual(p.wheel_packet(packet),(15,-32768,32767,-32768,1057))
        with self.assertRaises(ValueError): p.wheel_packet(packet[:-1])
        struct.pack_into('<i',packet,4,40000)
        with self.assertRaises(ValueError): p.wheel_packet(packet)

    def test_status_partial_corrupt_and_resynchronise(self):
        body = p.STATUS.pack(b'L2',1,2,8,160,7,1,-32768,32767,-32768,
                             -2147483648,-2147483648,-2147483648,0,0)
        frame = body + struct.pack('<I',zlib.crc32(body))
        self.assertEqual(len(frame),56)
        buffer=bytearray(b'junk'+frame[:17])
        self.assertEqual(list(p.pop_status(buffer)),[])
        buffer.extend(frame[17:])
        result=list(p.pop_status(buffer))
        self.assertEqual(result[0]['steer'],-32768)
        self.assertEqual(result[0]['current_valid_mask'],0)
        corrupt=frame[:-1]+bytes([frame[-1]^1])
        buffer.extend(corrupt+frame)
        self.assertEqual(len(list(p.pop_status(buffer))),1)
        self.assertEqual(len(buffer),0)

    def test_counter_wrap_duplicates_and_old_packets(self):
        self.assertTrue(p.is_newer(0,0xffffffff))
        self.assertFalse(p.is_newer(5,5))
        self.assertFalse(p.is_newer(4,5))
        self.assertTrue(p.is_newer(0,None))

    def test_self_test_status_keeps_wire_layout(self):
        body = p.STATUS.pack(b'L2',1,2,8,160,7,5,0,32767,-32768,
                             -2147483648,-2147483648,-2147483648,0,0)
        frame = body + struct.pack('<I',zlib.crc32(body))
        self.assertEqual(len(frame),56)
        status = list(p.pop_status(bytearray(frame)))[0]
        self.assertEqual(p.STATES[status['state']], 'SELF_TEST')
        self.assertEqual(struct.unpack_from('<I', p.command(9,0,32767,-32768,1),20)[0],1)

    def test_bridge_stops_refreshing_when_udp_stops(self):
        sys.modules['part2_protocol'] = p
        spec = importlib.util.spec_from_file_location('bridge', Path(__file__).parent/'pi'/'part2_bridge.py')
        bridge = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(bridge)
        clock = SimpleNamespace(now=0.0)
        writes=[]
        packet=bytearray(276)
        struct.pack_into('<Iii',packet,0,1,100,32767)
        struct.pack_into('<i',packet,24,32767)
        class FakeSocket:
            sent=False
            def bind(self,*a): pass
            def setblocking(self,*a): pass
            def close(self): pass
            def recvfrom(self,*a):
                if self.sent: raise BlockingIOError
                self.sent=True
                return bytes(packet),('127.0.0.1',9000)
        class FakeSerial:
            def __enter__(self): return self
            def __exit__(self,*a): pass
            def reset_input_buffer(self): pass
            def read(self,*a): return b''
            def write(self,data): writes.append((clock.now,data)); return len(data)
        def sleep(dt):
            clock.now += dt
            if clock.now > 0.3: raise KeyboardInterrupt
        fake_time=SimpleNamespace(monotonic=lambda:clock.now,sleep=sleep)
        with patch.object(bridge,'time',fake_time), \
             patch.object(bridge.socket,'socket',return_value=FakeSocket()), \
             patch.dict(sys.modules,{'serial':SimpleNamespace(Serial=lambda *a,**k:FakeSerial())}), \
             patch.object(sys,'argv',['part2_bridge.py','--mode','live']), \
             patch('builtins.print'):
            bridge.main()
        self.assertGreaterEqual(len(writes),4)
        self.assertLess(writes[-1][0],0.100)
        self.assertTrue(all(len(frame)==28 for _,frame in writes))


if __name__=='__main__': unittest.main()
