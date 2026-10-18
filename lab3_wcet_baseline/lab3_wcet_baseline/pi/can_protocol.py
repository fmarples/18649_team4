#!/usr/bin/env python3
"""Lab 3 CAN wire format. All frames are standard CAN, DLC 8, little-endian.

Byte 0: high nibble flags, low nibble per-ID sequence counter (0..15).
Byte 7: CRC-8/ATM (poly 0x07, init 0, no reflection/xorout) over bytes 0..6.
This CRC choice is an implementation decision because the handout specifies CRC-8
but not its polynomial; confirm with the team/TA before final sign-off.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

CTRL = 0x010
FAULT = 0x020
HB_N1 = 0x100
HB_N2 = 0x101
HB_N3 = 0x102
BLINK = 0x200
FORCE = 0x300
CATALOG_IDS = (CTRL, FAULT, HB_N1, HB_N2, HB_N3, BLINK, FORCE)
ZONE_N1, ZONE_N2, ZONE_N3 = 1, 2, 3
STATE_ERROR, STATE_OK, STATE_TEST = 0, 1, 2
BLINK_OFF, BLINK_LEFT, BLINK_RIGHT, BLINK_HAZARD = 0, 1, 2, 3
FLAG_VALID = 0x1


def crc8(data: bytes) -> int:
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = ((crc << 1) ^ 0x07) & 0xFF if crc & 0x80 else (crc << 1) & 0xFF
    return crc


def seq_byte(seq: int, flags: int = 0) -> int:
    return ((flags & 0x0F) << 4) | (seq & 0x0F)


def seal(payload7: bytes) -> bytes:
    if len(payload7) != 7:
        raise ValueError("payload prefix must be exactly seven bytes")
    return payload7 + bytes([crc8(payload7)])


def valid(frame_data: bytes) -> bool:
    return len(frame_data) == 8 and crc8(frame_data[:7]) == frame_data[7]


def pack_ctrl(seq: int, steer: int, throttle: int, brake: int, buttons: int, flags: int = FLAG_VALID) -> bytes:
    if not -32768 <= int(steer) <= 32767:
        raise ValueError("steering must fit int16")
    if not 0 <= throttle <= 100 or not 0 <= brake <= 100 or not 0 <= buttons <= 255:
        raise ValueError("throttle/brake/buttons must fit uint8")
    # b0 seq/flags, b1..2 steer, b3 throttle%, b4 brake%, b5 buttons, b6 reserved.
    return seal(struct.pack("<BhBBBB", seq_byte(seq, flags), int(steer), int(throttle), int(brake), int(buttons), 0))


def unpack_ctrl(data: bytes) -> dict:
    if not valid(data):
        raise ValueError("CTRL CRC/length invalid")
    _, steer, throttle, brake, buttons, reserved = struct.unpack("<BhBBBB", data[:7])
    if reserved != 0:
        raise ValueError("CTRL reserved byte must be zero")
    if (data[0] >> 4) != FLAG_VALID:
        raise ValueError("CTRL flags are invalid")
    return {"seq": data[0] & 0x0F, "flags": data[0] >> 4, "steer": steer,
            "throttle": throttle, "brake": brake, "buttons": buttons}


def pack_heartbeat(seq: int, zone_state: int, bus_a_ok: bool, bus_b_ok: bool, flags: int = 0) -> bytes:
    health = (1 if bus_a_ok else 0) | (2 if bus_b_ok else 0)
    return seal(bytes([seq_byte(seq, flags), zone_state & 0xFF, health, 0, 0, 0, 0]))


def unpack_heartbeat(data: bytes) -> dict:
    if not valid(data): raise ValueError("heartbeat CRC/length invalid")
    return {"seq": data[0] & 0x0F, "state": data[1], "health": data[2]}


def pack_fault(seq: int, source_zone: int, reason: int, detail: int = 0) -> bytes:
    return seal(bytes([seq_byte(seq), source_zone & 0xFF, reason & 0xFF]) + struct.pack("<I", detail & 0xFFFFFFFF))


def unpack_fault(data: bytes) -> dict:
    if not valid(data): raise ValueError("FAULT CRC/length invalid")
    return {"seq": data[0] & 0x0F, "zone": data[1], "reason": data[2], "detail": struct.unpack("<I", data[3:7])[0]}


def pack_blink(seq: int, mode: int, phase: int, phase_epoch_ms: int) -> bytes:
    return seal(bytes([seq_byte(seq), mode & 0xFF, phase & 1]) + struct.pack("<I", phase_epoch_ms & 0xFFFFFFFF))


def unpack_blink(data: bytes) -> dict:
    if not valid(data): raise ValueError("BLINK CRC/length invalid")
    return {"seq": data[0] & 0x0F, "mode": data[1], "phase": data[2] & 1,
            "phase_epoch_ms": struct.unpack("<I", data[3:7])[0]}


def pack_force(seq: int, counter: int) -> bytes:
    # Dummy force feedback: signed 8-bit counter, rest reserved.
    counter = ((counter + 128) % 256) - 128
    return seal(bytes([seq_byte(seq), counter & 0xFF, 0, 0, 0, 0, 0]))


def describe(frame_id: int) -> str:
    return {CTRL:"CTRL", FAULT:"FAULT", HB_N1:"HB_N1", HB_N2:"HB_N2", HB_N3:"HB_N3", BLINK:"BLINK", FORCE:"FORCE"}.get(frame_id, "UNKNOWN")
