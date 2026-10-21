"""Lab 3 template-catalog wire format; stm32_zephyr/src/can_protocol.c is the other half.

Standard IDs, DLC 8. Byte 0: low nibble per-ID sequence, high nibble flags.
Byte 7: CRC-8/ATM (poly 0x07, init 0, no reflection) over bytes 0..6.
"""
from __future__ import annotations

import struct

CTRL, FAULT, HB_N1, HB_N2, HB_N3, BLINK, FORCE = 0x010, 0x020, 0x100, 0x101, 0x102, 0x200, 0x300
CATALOG_IDS = (CTRL, FAULT, HB_N1, HB_N2, HB_N3, BLINK, FORCE)
NAMES = {CTRL: "CTRL", FAULT: "FAULT", HB_N1: "HB_N1", HB_N2: "HB_N2", HB_N3: "HB_N3",
         BLINK: "BLINK", FORCE: "FORCE"}
ZONE_N1, ZONE_N2, ZONE_N3 = 1, 2, 3
HEARTBEAT_ZONE = {HB_N1: ZONE_N1, HB_N2: ZONE_N2, HB_N3: ZONE_N3}
STATE_ERROR, STATE_OK = 0, 1
BLINK_OFF, BLINK_LEFT, BLINK_RIGHT, BLINK_HAZARD = 0, 1, 2, 3
CTRL_FLAGS = 1
# FAULT byte 2. CLEAR releases every latch; ZONE_LOST is informational.
FAULT_CLEAR, FAULT_TEST_BUTTON, FAULT_BAD_CRC, FAULT_BAD_CTRL, FAULT_ZONE_LOST = range(5)
LATCHING_FAULTS = (FAULT_TEST_BUTTON, FAULT_BAD_CRC, FAULT_BAD_CTRL)


def crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def seal(seq: int, payload7: bytes) -> bytes:
    """Insert the sequence nibble into byte 0 and append the CRC."""
    if len(payload7) != 7:
        raise ValueError("payload prefix must be exactly seven bytes")
    body = bytes([(payload7[0] & 0xF0) | (seq & 0x0F)]) + payload7[1:]
    return body + bytes([crc8(body)])


def valid(data: bytes) -> bool:
    return len(data) == 8 and crc8(data[:7]) == data[7]


def ctrl_body(steer: int, throttle: int, brake: int, buttons: int) -> bytes:
    # b0 flags, b1..2 steer LE, b3 throttle %, b4 brake %, b5 buttons, b6 reserved.
    return struct.pack("<BhBBBB", CTRL_FLAGS << 4, steer, throttle, brake, buttons & 0xFF, 0)


def ctrl_in_range(data: bytes) -> bool:
    """Team-defined values table: any int16 steering; pedals 0..100 %."""
    return data[0] >> 4 == CTRL_FLAGS and data[6] == 0 and data[3] <= 100 and data[4] <= 100


def heartbeat_body(state: int, bus_a_ok: bool, bus_b_ok: bool) -> bytes:
    return bytes([0, state, int(bus_a_ok) | (int(bus_b_ok) << 1), 0, 0, 0, 0])


def fault_body(failing_zone: int, reason: int, reporter: int) -> bytes:
    return bytes([0, failing_zone, reason, reporter, 0, 0, 0])


def blink_body(mode: int, phase: int) -> bytes:
    return bytes([0, mode, phase & 1, 0, 0, 0, 0])


def origin(frame_id: int, data: bytes) -> int:
    """Zone that originated a frame (FAULT: its reporter), or 0."""
    if frame_id in (CTRL, BLINK, HB_N1):
        return ZONE_N1
    if frame_id in (HB_N2, FORCE):
        return ZONE_N2
    if frame_id == HB_N3:
        return ZONE_N3
    return data[3] if frame_id == FAULT and data[3] in (ZONE_N1, ZONE_N2, ZONE_N3) else 0


def dedup_source(frame_id: int, data: bytes) -> int:
    """FAULT has several senders with independent sequence counters."""
    return data[3] if frame_id == FAULT else 0


def signed8(value: int) -> int:
    return value - 256 if value >= 128 else value
