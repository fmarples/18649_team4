"""Decode the existing 276-byte Lab 2 cockpit-proxy UDP packet for Lab 3."""
import struct
UDP_PACKET_BYTES = 276

def decode_wheel_packet(data: bytes):
    """Return (counter, steering int16, throttle 0..100, brake 0..100, buttons u8).

    Existing Lab 2 convention: 32767 is released for each pedal; smaller values
    represent increasing press. The Lab 3 CTRL payload uses normalized percentages.
    """
    if len(data) != UDP_PACKET_BYTES:
        raise ValueError(f"expected {UDP_PACKET_BYTES}-byte wheel datagram, got {len(data)}")
    counter = struct.unpack_from("<I", data, 0)[0]
    steer, throttle_axis = struct.unpack_from("<ii", data, 4)
    brake_axis = struct.unpack_from("<i", data, 24)[0]
    if any(v < -32768 or v > 32767 for v in (steer, throttle_axis, brake_axis)):
        raise ValueError("axis value outside signed 16-bit range")
    buttons = sum(1 << i for i in range(8) if data[52 + i] & 0x80)
    throttle = max(0, min(100, round((32767 - throttle_axis) * 100 / 65535)))
    brake = max(0, min(100, round((32767 - brake_axis) * 100 / 65535)))
    return counter, steer, throttle, brake, buttons
