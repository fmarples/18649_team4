"""Teaching link protocol v1. Little-endian integers; CRC-32/IEEE."""
import struct
import zlib

HEADER = b'L2\x01'
COMMAND = struct.Struct('<2sBBIiiiI')
STATUS = struct.Struct('<2sBBIIIIiiiiiiII')
STATUS_SIZE = STATUS.size + 4
STATES = ('WAITING', 'LINK_OK', 'ERROR_TIMEOUT', 'ERROR_BAD_INPUT', 'ERROR_RX_OVERFLOW',
          'ERROR_MOTOR', 'SELF_TEST', 'ERROR_ACTUATOR')


def command(seq, steer, throttle, brake, buttons=0):
    payload = COMMAND.pack(b'L2', 1, 1, seq & 0xffffffff, steer, throttle, brake, buttons)
    return payload + struct.pack('<I', zlib.crc32(payload))


def wheel_packet(data):
    if len(data) != 276:
        raise ValueError('Expected a 276-byte Windows wheel packet')
    seq = struct.unpack_from('<I', data, 0)[0]
    steer, throttle = struct.unpack_from('<ii', data, 4)
    brake = struct.unpack_from('<i', data, 24)[0]
    if any(v < -32768 or v > 32767 for v in (steer, throttle, brake)):
        raise ValueError('Wheel axis is outside the calibrated signed raw range')
    buttons = sum(1 << i for i in range(11) if data[52 + i] & 0x80)
    return seq, steer, throttle, brake, buttons


def pop_status(buffer):
    """Yield complete valid frames; resynchronise after junk or corruption."""
    magic = HEADER + b'\x02'
    while len(buffer) >= 4:
        start = buffer.find(magic)
        if start < 0:
            del buffer[:-3]
            return
        del buffer[:start]
        if len(buffer) < STATUS_SIZE:
            return
        frame = bytes(buffer[:STATUS_SIZE])
        if zlib.crc32(frame[:-4]) != struct.unpack('<I', frame[-4:])[0]:
            del buffer[0]
            continue
        fields = STATUS.unpack(frame[:-4])
        del buffer[:STATUS_SIZE]
        names = ('status_seq', 'stm_ms', 'command_seq', 'state', 'steer', 'throttle',
                 'brake', 'current_left_mA', 'current_right_mA', 'current_servo_mA',
                 'current_valid_mask', 'rejected')
        yield dict(zip(names, fields[3:]))


def is_newer(seq, previous):
    return previous is None or 0 < ((seq - previous) & 0xffffffff) < 0x80000000
