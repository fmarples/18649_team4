#!/usr/bin/env python3
"""Lab 5 cockpit: existing vehicle protocol plus the shared C Raft/time agent.

This is a live SocketCAN application. Running it claims CAN/GPIO and can send
vehicle commands. Host tests use fake buses; no deploy/flash is performed here.
"""

from __future__ import annotations
import argparse
import dataclasses
import json
import os
from pathlib import Path
import queue
import signal
import socket
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "lab5/host"))
sys.path.insert(0, str(ROOT / "lab5"))
import can
from vehicle import can_protocol as p
from vehicle.cockpit import Cockpit, EventLog, run, _BusListener, MIN_INTERVAL_S
from vehicle.pi_gpio import NoGpio, PiGpio, PINS
from native import Agent
from generate_config import load
from ledger import Ledger, Console

PPS, LEADER, SYNC, REF_RX = 16, 20, 21, 26
NEW_PINS = (PPS, LEADER, SYNC, REF_RX)


class Lab5NoGpio(NoGpio):
    def __init__(self):
        super().__init__()
        self.levels.update(dict.fromkeys(NEW_PINS, False))

    def consensus(self, leader, synced, pps):
        self._set(LEADER, leader)
        self._set(SYNC, synced)
        self._set(PPS, pps)

    def ref_rx(self):
        self._set(REF_RX, not self.levels[REF_RX])


class Lab5PiGpio(Lab5NoGpio):
    def __init__(self, chip="/dev/gpiochip0"):
        Lab5NoGpio.__init__(self)
        import gpiod
        from gpiod.line import Direction, Value

        self._value = Value
        self._request = gpiod.request_lines(
            chip,
            consumer="lab5-cockpit",
            config={
                PINS
                + NEW_PINS: gpiod.LineSettings(
                    direction=Direction.OUTPUT, output_value=Value.INACTIVE
                )
            },
        )

    def _write(self, pin, active):
        PiGpio._write(self, pin, active)

    def close(self):
        try:
            self._request.set_values(
                {pin: self._value.INACTIVE for pin in PINS + NEW_PINS}
            )
        finally:
            self._request.release()


class Cockpit5(Cockpit):
    def __init__(
        self,
        buses,
        gpio,
        log,
        now,
        store=None,
        config=None,
        ledger=None,
        console=None,
        uplink=None,
        offsets=None,
    ):
        super().__init__(buses, gpio, log, now)
        self.config = config or load()
        c = self.config
        self.agent = Agent(
            1,
            leader=1 if c["default_leader"] == "cockpit" else 0,
            seed=c["seed"],
            path=store,
            delay_us=c["can_delay_us"],
        )
        self.epoch = now
        self.rx = queue.Queue(maxsize=4096)
        self.last_second = 0
        self.pps_until = 0
        self.agent_health = {"error": 1, "hazard_hz": 2, "synced": 0}
        self._last_raft = None
        self._last_ref = None
        self.applied_events = []
        self.ledger, self.console = ledger, console
        self.pending_event = False
        self.uplink, self.offsets = uplink, offsets or {}

    def raw_us(self, now):
        return max(0, round((now - self.epoch) * 1_000_000))

    def on_frame(self, msg, bus, now):
        # Notifier threads only timestamp/enqueue; one main-loop owner runs C.
        try:
            self.rx.put_nowait((msg, bus, now))
        except queue.Full:
            self.counters["lab5_rx_dropped"] += 1

    def _write_one(self, index, frame_id, payload):
        self.gpio.can_tx(index)
        try:
            self.buses[index].send(
                can.Message(
                    arbitration_id=frame_id, is_extended_id=False, data=payload
                ),
                timeout=0,
            )
        except (can.CanError, OSError) as e:
            self.counters[f"tx_error_{index}"] += 1
            self.log.write("TX_ERROR", f"0x{frame_id:03x} bus={index} {e}")

    def _supervise(self, now):
        with self.lock:
            health = self.monitor.evaluate(now)
            error = bool(
                self.agent_health["error"]
                or self.monitor.latched
                or self.latest is None
            )
        health = dataclasses.replace(health, error=error)
        if error != self.error:
            self.log.write("STATE", "ERROR" if error else "OK")
            # Keep the existing STATE format for analyzers; record the snapshot
            # separately so an input timeout is distinguishable from other faults.
            self.log.write("STATE_CAUSE", json.dumps({
                "udp_age_ms": None if self.last_udp is None else
                    round(1000 * (now - self.last_udp[1]), 3),
                "latched": self.monitor.latched,
                "no_controls": self.latest is None,
                "agent_error": bool(self.agent_health["error"]),
                "raft": self.agent.status,
                "can_rx_queued": self.rx.qsize(),
            }))
        self.error, self.health = error, health
        self.gpio.leds(*health.degraded, error)
        return health

    def tick(self, now):
        tick_started = time.monotonic()
        raw = self.raw_us(now)
        for _ in range(1024):
            try:
                msg, bus, received = self.rx.get_nowait()
            except queue.Empty:
                break
            if msg.is_extended_id or msg.is_remote_frame or msg.dlc != 8:
                continue
            data = bytes(msg.data)
            with self.lock:
                self.monitor.frame(bus, received)
            samples = self.agent.clock_samples
            handled = self.agent.receive_can(
                bus,
                msg.arbitration_id,
                data,
                raw,
                queue_us=max(0, raw - self.raw_us(received)),
            )
            if not handled:
                super().on_frame(msg, bus, received)
            if self.agent.clock_samples != samples:
                self.gpio.ref_rx()
        received_at = time.monotonic()
        udp_ok = self.last_udp is not None and now - self.last_udp[1] < 0.100
        self.agent.update(raw, udp_ok and not self.monitor.latched, self.hb_silenced)
        if self.pending_event:
            self.pending_event = False
            if not self.agent.event():
                self.log.write(
                    "EVENT_REJECTED", "no leader, catching up, or storage full"
                )
        updated_at = time.monotonic()
        for bus, can_id, data in self.agent.outgoing():
            if 0x81 <= can_id <= 0x83:
                # Include this tick's durable writes and queue-drain time.
                # Kernel/controller arbitration still requires measurement.
                elapsed = max(0, round((time.monotonic() - tick_started) * 1_000_000))
                stamp = (int.from_bytes(data[3:7], "little") + elapsed) & 0xFFFFFFFF
                prefix = data[:3] + stamp.to_bytes(4, "little")
                data = prefix + bytes([p.crc8(prefix)])
            self._write_one(bus, can_id, data)
            if self.config["debug"]:
                self.log.write(
                    "RAFT_TX", f"bus={bus} id={can_id:03x} data={data.hex()}"
                )
        sent_at = time.monotonic()
        for index, term, event, replayed in self.agent.applied():
            row = {
                "index": index,
                "term": term,
                "event": event,
                "replayed": bool(replayed),
                "global_us": self.agent.global_us(raw),
            }
            self.log.write("COMMIT", json.dumps(row))
            if self.ledger and not self.ledger.submit(row):
                self.monitor.latched = True
                self.log.write("LEDGER_ERROR", self.ledger.error or "queue full")
            self.applied_events.append(row)
            if len(self.applied_events) > 1000:
                self.applied_events.pop(0)
        self.agent_health = self.agent.health(raw)
        state = self.agent.status
        lead = state["role"] == 2 and not state["failed"] and not self.hb_silenced
        global_us = self.agent.global_us(raw)
        if global_us // 1_000_000 != self.last_second:
            self.last_second = global_us // 1_000_000
            self.pps_until = now + 0.001
            self.log.write(
                "PPS",
                f"global_us={global_us} local_us={raw} rate={self.agent.rate:.9f} correction_us={self.agent.correction(raw)}",
            )
            if self.console:
                self.console.write(
                    f"PPS global_us={global_us} local_us={raw} rate={self.agent.rate:.9f} correction_us={self.agent.correction(raw)}"
                )
            if self.uplink:
                self.uplink.status(
                    dict(
                        wall_clock=time.time(),
                        global_us=global_us,
                        raft=self.agent.status,
                        time_master=self.agent.status["leader"],
                        held_events=self.agent_health["held_events"],
                        fl_offset_us=self.offsets.get("fl_offset_us"),
                        rl_offset_us=self.offsets.get("rl_offset_us"),
                    )
                )
        self.gpio.consensus(lead, self.agent_health["synced"], now < self.pps_until)
        changed = (state["term"], state["role"], state["leader"])
        if changed != self._last_raft:
            self.log.write("RAFT", json.dumps(state))
            if self.console:
                self.console.write("RAFT " + json.dumps(state))
            self._last_raft = changed
        super().tick(now)
        finished_at = time.monotonic()
        # Diagnostic trigger: one nominal wheel-update period. This is elapsed
        # wall time (including descheduling), not CPU execution time or WCET.
        if finished_at - tick_started >= 0.020:
            self.log.write("TICK_SLOW", json.dumps({
                "total_ms": round(1000 * (finished_at - tick_started), 3),
                "can_receive_ms": round(1000 * (received_at - tick_started), 3),
                "agent_update_ms": round(1000 * (updated_at - received_at), 3),
                "can_send_ms": round(1000 * (sent_at - updated_at), 3),
                "apply_outputs_ms": round(1000 * (finished_at - sent_at), 3),
                "can_rx_queued": self.rx.qsize(),
            }))

    def _blink(self, now):
        mode = self.blinker.mode
        raw = self.raw_us(now)
        t = self.agent.global_us(raw)
        half = (
            1_000_000 // (2 * self.agent_health["hazard_hz"]) if self.error else 500000
        )
        phase = int((t // half) % 2 == 0 and mode != p.BLINK_OFF)
        changed = (mode, phase) != (self.blink_mode, self.blink_phase)
        self.next_blink = now + max(0.0002, (half - t % half) / 1_000_000)
        if (
            changed or now - self.last_blink >= 0.5
        ) and now - self.last_blink >= MIN_INTERVAL_S:
            self.blink_mode, self.blink_phase = mode, phase
            self.last_blink = now
            self.send(p.BLINK, p.blink_body(mode, phase))

    def next_wake(self, now):
        return min(super().next_wake(now), now + 0.0002)

    def emit_status(self):
        # SSH/terminal backpressure must not block CAN, UDP or consensus work.
        if self.console is not None:
            self.console.write(self.status())

    def status(self):
        data = json.loads(super().status()[7:])
        data["raft"] = self.agent.status
        data["clock"] = self.agent_health
        # Observe evidence health without doing SQLite I/O in the control loop.
        data["evidence"] = {
            "csv_dropped": self.log.dropped,
            "console_dropped": self.console.dropped if self.console else None,
            "ledger": (
                None
                if self.ledger is None
                else {
                    "durable_index": self.ledger.durable_index,
                    "queued": self.ledger.queue.qsize(),
                    "dropped": self.ledger.dropped,
                    "error": self.ledger.error,
                }
            ),
        }
        return "STATUS " + json.dumps(data)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bus-a", default="can0")
    ap.add_argument("--bus-b", default="can1")
    ap.add_argument("--udp-port", type=int, default=8000)
    ap.add_argument("--sender")
    ap.add_argument("--no-gpio", action="store_true")
    ap.add_argument("--gpiochip", default="/dev/gpiochip0")
    ap.add_argument("--fifo", type=int)
    ap.add_argument(
        "--cloud-url", help="Optional HTTPS mirror; requires LAB5_UPLINK_TOKEN"
    )
    ap.add_argument(
        "--offsets-json",
        type=Path,
        help="Optional actual measured FL/RL offsets in microseconds",
    )
    ap.add_argument(
        "--state-dir", type=Path, default=Path.home() / ".local/state/team4-lab5"
    )
    args = ap.parse_args(argv)
    config = load()
    args.state_dir.mkdir(parents=True, exist_ok=True)
    # OS file lock prevents two processes from voting as N1 or modifying its log.
    import fcntl

    lock = open(args.state_dir / "owner.lock", "w")
    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    if args.fifo:
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(args.fifo))
    log_dir = args.state_dir / time.strftime("%Y%m%d-%H%M%S")
    log_dir.mkdir()
    log = EventLog(log_dir / "events.csv")
    console = Console()
    uplink = None
    if args.cloud_url:
        from uplink import Uplink

        uplink = Uplink(
            args.cloud_url,
            os.environ["LAB5_UPLINK_TOKEN"],
            args.state_dir / "cloud-ack.txt",
        )

    def committed(row):
        console.write("COMMIT " + json.dumps(row))
        if uplink:
            uplink.submit(row)

    ledger = Ledger(args.state_dir / "display.sqlite", committed)
    if uplink:
        for row in ledger.rows()[-1000:]:
            uplink.submit(row)
    offsets = json.loads(args.offsets_json.read_text()) if args.offsets_json else None
    gpio = Lab5NoGpio() if args.no_gpio else Lab5PiGpio(args.gpiochip)
    buses = [
        can.Bus(interface="socketcan", channel=x) for x in (args.bus_a, args.bus_b)
    ]
    app = Cockpit5(
        buses,
        gpio,
        log,
        time.monotonic(),
        args.state_dir / "raft.bin",
        config,
        ledger,
        console,
        uplink,
        offsets,
    )
    notifiers = [can.Notifier(b, [_BusListener(app, i)]) for i, b in enumerate(buses)]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setblocking(False)
    udp.bind(("0.0.0.0", args.udp_port))
    stop = threading.Event()
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGRTMIN, lambda *_: setattr(app, "pending_test", "latch"))
    signal.signal(signal.SIGRTMIN + 1, lambda *_: setattr(app, "pending_test", "clear"))
    signal.signal(signal.SIGUSR1, lambda *_: setattr(app, "pending_event", True))
    try:
        run(app, udp, stop, args.sender)
    finally:
        udp.close()
        for n in notifiers:
            n.stop()
        for b in buses:
            b.shutdown()
        gpio.close()
        app.agent.close()
        log.close()
        ledger.close()
        if uplink:
            uplink.close()
        console.close()
        lock.close()


if __name__ == "__main__":
    main()
