"""Small ctypes boundary to the C implementation, shared by simulation and Pi."""

import ctypes as C
from pathlib import Path
import os

ROOT = Path(__file__).resolve().parents[1]
LIB = ROOT / "build" / ("lab5.dll" if os.name == "nt" else "liblab5.so")
lib = C.CDLL(str(LIB))
P, U, U64, B = C.c_void_p, C.c_uint, C.c_uint64, C.POINTER(C.c_uint8)
signatures = {
    "new": ([U, U, U, U, C.c_char_p], P),
    "free": ([P], None),
    "tick": ([P, U64], None),
    "request": ([P, U], C.c_int),
    "receive": ([P, B, U64], None),
    "drain": ([P, B], C.c_int),
    "applied": ([P, C.POINTER(C.c_uint16)], C.c_int),
    "status": ([P, U], U),
    "entry": ([P, U, C.POINTER(C.c_uint16)], C.c_int),
    "heartbeat": ([P, U, U, U64], C.c_int),
    "fail_write": ([P, C.c_int], None),
    "reopen": ([P], C.c_int),
    "truncate": ([P, U], C.c_int),
    "store_length": ([P], U),
    "held_events": ([P], U),
    "store_append": ([P, U, U], C.c_int),
    "store_prepare_boot": ([P], C.c_int),
    "store_hardstate": ([P, U, U], C.c_int),
    "store_state": ([P, U], U),
    "fragment": ([P, B, B], None),
    "packet": ([P, U, U, B, U64, B], C.c_int),
    "global": ([P, U64], U64),
    "ref": ([P, U, U, C.c_uint32, U64, U], C.c_int),
    "lead": ([P, U, U, U64], None),
    "rate": ([P], C.c_double),
    "clock_samples": ([P], U),
    "correction": ([P, U64], C.c_int64),
    "queue_delay": ([P, U], None),
    "route": ([P, U, U, C.POINTER(U)], C.c_int),
    "agent_enable": ([P, U], None),
    "agent_tick": ([P, U64, U, U], None),
    "agent_receive": ([P, U, U, B, U64], C.c_int),
    "agent_drain": ([P, C.POINTER(C.c_uint16), B], C.c_int),
    "agent_status": ([P, U, U64], U),
    "user_event": ([P], C.c_int),
}
for name, (args, result) in signatures.items():
    f = getattr(lib, "l5_host_" + name)
    f.argtypes = args
    f.restype = result


def buf(data):
    return (C.c_uint8 * len(data)).from_buffer_copy(data)


class Node:
    def __init__(self, node_id, leader=1, seed=1, capacity=30000, path=None):
        self.id = node_id
        self.ptr = lib.l5_host_new(
            node_id, leader, seed, capacity, os.fsencode(path) if path else None
        )
        if not self.ptr:
            raise RuntimeError(
                "Cannot initialize Raft: invalid configuration or durable store"
            )

    def close(self):
        if self.ptr:
            lib.l5_host_free(self.ptr)
            self.ptr = None

    def __del__(self):
        self.close()

    @property
    def status(self):
        names = (
            "role",
            "term",
            "leader",
            "length",
            "commit",
            "applied",
            "nodes",
            "links",
            "cockpit_ok",
            "failed",
            "dropped",
            "vote",
            "entry_reads",
        )
        return {n: int(lib.l5_host_status(self.ptr, i)) for i, n in enumerate(names)}

    def tick(self, ms):
        lib.l5_host_tick(self.ptr, ms)

    def request(self, event):
        return bool(lib.l5_host_request(self.ptr, event))

    def event(self):
        return bool(lib.l5_host_user_event(self.ptr))

    def receive(self, data, ms):
        if len(data) != 24:
            raise ValueError("RPC must have 24 bytes")
        lib.l5_host_receive(self.ptr, buf(data), ms)

    def drain(self):
        p = (C.c_uint8 * 24)()
        while lib.l5_host_drain(self.ptr, p):
            yield bytes(p)

    def applied(self, limit=None):
        if limit is not None and limit < 0:
            raise ValueError("Applied notification limit must be nonnegative")
        p = (C.c_uint16 * 4)()
        count = 0
        while (limit is None or count < limit) and lib.l5_host_applied(self.ptr, p):
            count += 1
            yield tuple(p)

    def log(self):
        p = (C.c_uint16 * 2)()
        for i in range(1, self.status["length"] + 1):
            if not lib.l5_host_entry(self.ptr, i, p):
                raise RuntimeError("store read failed")
            yield i, int(p[0]), int(p[1])

    def heartbeat(self, src, term, ms):
        return bool(lib.l5_host_heartbeat(self.ptr, src, term, ms))

    def fragment(self, data):
        p = (C.c_uint8 * 40)()
        lib.l5_host_fragment(self.ptr, buf(data), p)
        b = bytes(p)
        return [
            (int.from_bytes(b[i : i + 2], "little"), b[i + 2 : i + 10])
            for i in range(0, 40, 10)
        ]

    def packet(self, can_id, data, ms, bus=0):
        if len(data) != 8:
            return None
        p = (C.c_uint8 * 24)()
        if lib.l5_host_packet(self.ptr, bus, can_id, buf(data), ms, p):
            return bytes(p)
        return None

    def global_us(self, raw):
        return int(lib.l5_host_global(self.ptr, raw))

    def ref(self, src, term, low, raw, delay=0):
        return bool(lib.l5_host_ref(self.ptr, src, term, low, raw, delay))

    def lead(self, src, term, raw):
        lib.l5_host_lead(self.ptr, src, term, raw)

    @property
    def rate(self):
        return float(lib.l5_host_rate(self.ptr))

    def route(self, dst):
        b = U()
        bus = lib.l5_host_route(self.ptr, self.id, dst, C.byref(b))
        return bus, b.value

    @property
    def clock_samples(self):
        return int(lib.l5_host_clock_samples(self.ptr))

    def correction(self, raw_us):
        return int(lib.l5_host_correction(self.ptr, raw_us))


class Agent(Node):
    def __init__(self, *args, delay_us=240, **kwargs):
        super().__init__(*args, **kwargs)
        self.delay_us = delay_us
        lib.l5_host_agent_enable(self.ptr, delay_us)

    def update(self, raw_us, upstream_ok=True, paused=False):
        lib.l5_host_agent_tick(self.ptr, raw_us, upstream_ok, paused)

    def receive_can(self, bus, can_id, data, raw_us, queue_us=0):
        if len(data) != 8:
            return True
        lib.l5_host_queue_delay(self.ptr, self.delay_us + queue_us)
        result = bool(
            lib.l5_host_agent_receive(self.ptr, bus, can_id, buf(data), raw_us)
        )
        lib.l5_host_queue_delay(self.ptr, self.delay_us)
        return result

    def outgoing(self):
        meta = (C.c_uint16 * 2)()
        p = (C.c_uint8 * 8)()
        while lib.l5_host_agent_drain(self.ptr, meta, p):
            yield int(meta[0]), int(meta[1]), bytes(p)

    def health(self, raw_us):
        return {
            name: int(lib.l5_host_agent_status(self.ptr, i, raw_us))
            for i, name in enumerate(
                ("error", "hazard_hz", "synced", "relays", "held_events",
                 "reason_mask", "pi_report_age_ms", "n2_report_age_ms", "n3_report_age_ms")
            )
        }
