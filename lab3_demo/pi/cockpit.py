#!/usr/bin/env python3
"""N1 cockpit zone for the Lab 3 Part 5 demo.

Wheel UDP (Lab 2 276-byte packet, port 8000) -> CTRL on every update, BLINK and
HB_N1 every 20 ms, each written to bus A then bus B. Reads heartbeats, FAULT and
FORCE from both buses, drops duplicate copies by (ID, source, seq), and drives the
Pi's DEG_A / DEG_B / ERR LEDs and UDP_RX / CMD_TX / CAN_TX_A / CAN_TX_B markers.

    python3 cockpit.py [--fifo 1] [--bus-a can0 --bus-b can1]

Bad-input injection: `kill -USR1 <pid>` makes the next CTRL carry throttle 101
(CRC valid); `kill -USR2 <pid>` corrupts the next CTRL's CRC. N1 test button
without the wheel: SIGRTMIN latches and silences HB_N1 (single press), SIGRTMIN+1
clears (double press). lab3_demo/test_panel.py sends these from the laptop GUI.
Logs: --log-dir (default ~/.local/state/team4-lab3/demo/<start time>/) holds
events.csv and crash.log (Python tracebacks and faulthandler dumps).
"""
from __future__ import annotations

import argparse
import collections
import csv
import faulthandler
import json
import os
import queue
import select
import signal
import socket
import threading
import time
import traceback
from pathlib import Path

import can

import can_protocol as p
from blinker import Blinker
from frame_history import FrameHistory
from pi_gpio import NoGpio, PiGpio
from wheel_input import decode_wheel_packet
from zone_state import HB_PERIOD_S, ZoneMonitor

BLINK_HALF_PERIOD_S = 0.5
DOUBLE_PRESS_S = 0.5  # student clarification: double press within 500 ms
TEST_BUTTON = 1 << 0  # wheel A, as in Lab 2
UDP_RESYNC_S = 1.0    # accept a restarted proxy's lower counter after this gap
SEND_TIMEOUT_S = 0.001


class EventLog:
    """CSV rows written by a background thread so SD stalls never block control."""
    FIELDS = ("mono_s", "event", "detail", "latency_us")

    def __init__(self, path: Path | None):
        self._queue: queue.Queue = queue.Queue(maxsize=10000)
        self.dropped = 0
        self._thread = None
        if path is not None:
            self._file = open(path, "w", newline="", encoding="utf-8")
            self._writer = csv.writer(self._file)
            self._writer.writerow(self.FIELDS)
            self._thread = threading.Thread(target=self._drain, name="event-log", daemon=True)
            self._thread.start()

    def write(self, event, detail="", latency_us=""):
        if self._thread is None:
            return
        try:
            self._queue.put_nowait((f"{time.monotonic():.6f}", event, detail, latency_us))
        except queue.Full:
            self.dropped += 1

    def _drain(self):
        while (row := self._queue.get()) is not None:
            self._writer.writerow(row)
            if self._queue.empty():
                self._file.flush()

    def close(self):
        if self._thread is not None:
            self._queue.put(None)
            self._thread.join(timeout=5)
            self._file.close()


class Cockpit:
    """N1 logic. main() owns sockets and the clock; tests call these methods directly.

    on_frame runs on python-can notifier threads; everything else on the main loop.
    `lock` guards the zone monitor, which both sides touch.
    """

    def __init__(self, buses, gpio, log, now):
        self.buses = buses  # [bus A, bus B]
        self.gpio = gpio
        self.log = log
        self.lock = threading.Lock()
        self.monitor = ZoneMonitor(p.ZONE_N1)
        self.history = FrameHistory()
        self.blinker = Blinker()
        self.seq = dict.fromkeys(p.CATALOG_IDS, 0)
        self.latest = (0, 0, 0, 0)  # steer, throttle %, brake %, buttons
        self.last_udp = None        # (counter, time)
        self.error = True
        self.health = None
        self.was_alive = {p.ZONE_N2: False, p.ZONE_N3: False}
        self.test_armed = False
        self.last_test_press = 0.0
        self.hb_silenced = False    # own test press stops HB_N1 until any FAULT clear
        self.previous_buttons = 0
        self.blink_mode, self.blink_phase = p.BLINK_OFF, 0
        self.next_blink = now
        self.next_hb = now
        self.inject = None          # "range" or "crc" for the next CTRL
        self.pending_test = None    # "latch" or "clear" from a signal, run by the main loop
        self.force = 0
        self.counters = collections.Counter()
        gpio.leds(False, False, True)  # power-up in error

    # ---- transmit -------------------------------------------------------
    def _write(self, frame_id, payload):
        """Queue one frame on A then B."""
        for index in range(len(self.buses)):
            self._write_one(index, frame_id, payload)

    def _write_one(self, index, frame_id, payload):
        """Queue one frame on one bus, toggling that bus's CAN_TX marker."""
        self.gpio.can_tx(index)
        try:
            self.buses[index].send(can.Message(arbitration_id=frame_id, is_extended_id=False, data=payload),
                                   timeout=SEND_TIMEOUT_S)
        except (can.CanError, OSError) as exc:
            self.counters[f"tx_error_{'AB'[index]}"] += 1
            self.log.write("TX_ERROR", f"{p.NAMES[frame_id]} bus={'AB'[index]} {exc}")

    def send(self, frame_id, body):
        """The send helper: one sequence number per logical message, then both buses."""
        seq = self.seq[frame_id]
        self.seq[frame_id] = (seq + 1) & 0x0F
        self._write(frame_id, p.seal(seq, body))

    def send_fault(self, failing_zone, reason):
        self.send(p.FAULT, p.fault_body(failing_zone, reason, p.ZONE_N1))
        self.log.write("FAULT_TX", f"zone={failing_zone} reason={reason}")

    def send_ctrl(self, udp_time, clock=time.monotonic):
        steer, throttle, brake, buttons = self.latest
        body = p.ctrl_body(steer, throttle, brake, buttons)
        inject, self.inject = self.inject, None
        if inject == "range":
            body = body[:3] + bytes([101]) + body[4:]
        seq = self.seq[p.CTRL]
        self.seq[p.CTRL] = (seq + 1) & 0x0F
        payload = p.seal(seq, body)
        if inject == "crc":
            payload = payload[:7] + bytes([payload[7] ^ 0xFF])
        self._write_one(0, p.CTRL, payload)
        self.gpio.cmd_tx()  # clarification #1: CMD_TX right after the first CAN write returns
        latency_us = (clock() - udp_time) * 1e6
        self._write_one(1, p.CTRL, payload)
        self.log.write("UDP_TO_CMD_TX", f"seq={seq}", f"{latency_us:.1f}")
        if inject:
            self.log.write("INJECT", f"{inject} seq={seq}")

    # ---- receive --------------------------------------------------------
    def on_udp(self, data, now):
        """Accept one wheel datagram; returns True when a CTRL should follow."""
        try:
            counter, steer, throttle, brake, buttons = decode_wheel_packet(data)
        except ValueError as exc:
            self.counters["udp_reject"] += 1
            self.log.write("UDP_REJECT", str(exc))
            return False
        if self.last_udp is not None:
            last_counter, last_time = self.last_udp
            newer = 0 < ((counter - last_counter) & 0xFFFFFFFF) < 0x80000000
            if not newer and now - last_time < UDP_RESYNC_S:
                self.counters["udp_old"] += 1
                return False
        self.last_udp = (counter, now)
        self.latest = (steer, throttle, brake, buttons)
        with self.lock:
            self.monitor.ctrl(now)
        self._test_button(buttons, now)
        self.blinker.update(self.error, buttons, steer)
        return True

    def _test_button(self, buttons, now):
        pressed = buttons & TEST_BUTTON and not self.previous_buttons & TEST_BUTTON
        self.previous_buttons = buttons
        if not pressed:
            return
        clear = self.test_armed and now - self.last_test_press <= DOUBLE_PRESS_S
        self.test_fault(clear, now)

    def test_fault(self, clear, now):
        """N1 test button: latch, send FAULT and stop HB_N1, or release every zone with
        FAULT clear and resume HB_N1."""
        with self.lock:
            self.monitor.latched = not clear
            self.hb_silenced = not clear
        self.send_fault(p.ZONE_N1, p.FAULT_CLEAR if clear else p.FAULT_TEST_BUTTON)
        self.test_armed = not clear
        self.last_test_press = now
        self._supervise(now)

    def on_frame(self, msg, bus, now):
        """Dispatch path: validate, drop our own frames relayed back by N2,
        per-bus heartbeat, dedup, then FAULT/FORCE."""
        data = bytes(msg.data)
        if msg.is_extended_id or msg.is_remote_frame or msg.dlc != 8 or not p.valid(data):
            self.counters["bad_frame"] += 1
            return
        frame_id = msg.arbitration_id
        if frame_id not in p.NAMES or p.origin(frame_id, data) == p.ZONE_N1:
            return
        with self.lock:
            zone = p.HEARTBEAT_ZONE.get(frame_id)
            if zone:
                self.monitor.heartbeat(zone, bus, now)
            try:
                first = self.history.first_copy(frame_id, p.dedup_source(frame_id, data), data[0] & 0x0F, now)
            except OverflowError:
                self.counters["history_full"] += 1
                return
            if not first:
                self.counters["duplicate"] += 1
                return
            self.counters[f"rx_{p.NAMES[frame_id]}"] += 1
            if frame_id == p.FAULT:
                reason = data[2]
                if reason == p.FAULT_CLEAR:
                    self.monitor.latched = False
                    self.hb_silenced = False
                elif reason in p.LATCHING_FAULTS:
                    self.monitor.latched = True
            elif frame_id == p.FORCE:
                self.force = p.signed8(data[1])
        if frame_id == p.FAULT:
            self.log.write("FAULT_RX", f"zone={data[1]} reason={data[2]} reporter={data[3]} bus={'AB'[bus]}")

    # ---- periodic -------------------------------------------------------
    def _supervise(self, now):
        """HB_MON: error state and LEDs; returns the health snapshot."""
        with self.lock:
            health = self.monitor.evaluate(now)
        if health.error != self.error:
            self.log.write("STATE", "ERROR" if health.error else "OK",
                           f"latched={self.monitor.latched} alive={health.alive} ctrl_fresh={health.ctrl_fresh}")
        if self.health is None or health.degraded != self.health.degraded:
            self.log.write("DEGRADED", f"A={health.degraded[0]} B={health.degraded[1]}")
        self.error, self.health = health.error, health
        self.gpio.leds(health.degraded[0], health.degraded[1], health.error)
        return health

    def tick(self, now):
        if now >= self.next_hb:
            self.next_hb += HB_PERIOD_S
            if self.next_hb <= now:
                self.next_hb = now + HB_PERIOD_S
            health = self._supervise(now)
            for zone in self.was_alive:
                if self.was_alive[zone] and not health.alive[zone]:
                    self.send_fault(zone, p.FAULT_ZONE_LOST)
                self.was_alive[zone] = health.alive[zone]
            with self.lock:
                silenced = self.hb_silenced
            if not silenced:
                self.send(p.HB_N1, p.heartbeat_body(p.STATE_ERROR if health.error else p.STATE_OK,
                                                    *health.bus_alive))
            steer, _, _, buttons = self.latest
            self.blinker.update(self.error, buttons, steer)
        self._blink(now)

    def _blink(self, now):
        """BLINK_TX: immediately on a mode change, then every 500 ms toggle."""
        mode = self.blinker.mode
        if mode != self.blink_mode:
            self.blink_mode, self.blink_phase = mode, int(mode != p.BLINK_OFF)
            self.next_blink = now + BLINK_HALF_PERIOD_S
        elif now >= self.next_blink:
            if mode != p.BLINK_OFF:
                self.blink_phase ^= 1
            self.next_blink += BLINK_HALF_PERIOD_S
            if self.next_blink <= now:
                self.next_blink = now + BLINK_HALF_PERIOD_S
        else:
            return
        self.send(p.BLINK, p.blink_body(self.blink_mode, self.blink_phase))

    def status(self):
        """One `STATUS {json}` line per second; test_panel.py parses it."""
        h = self.health
        steer, throttle, brake, _ = self.latest
        return "STATUS " + json.dumps({
            "error": self.error, "latched": self.monitor.latched,
            "alive": {} if h is None else {f"N{z}": v for z, v in h.alive.items()},
            "degraded": [False, False] if h is None else list(h.degraded),
            "blink": self.blink_mode, "steer": steer, "throttle": throttle, "brake": brake,
            "force": self.force, "counters": dict(self.counters)})


class _BusListener(can.Listener):
    def __init__(self, cockpit, bus):
        self.cockpit, self.bus = cockpit, bus

    def on_message_received(self, msg):
        self.cockpit.on_frame(msg, self.bus, time.monotonic())


def run(cockpit, udp, stop, sender=None, clock=time.monotonic, status_period=1.0):
    """Main loop: block on UDP until the next periodic deadline, never busy-poll."""
    next_status = clock()
    while not stop.is_set():
        timeout = max(0.0, min(cockpit.next_hb, cockpit.next_blink) - clock())
        readable, _, _ = select.select([udp], [], [], timeout)
        if cockpit.pending_test is not None:
            request, cockpit.pending_test = cockpit.pending_test, None
            cockpit.test_fault(request == "clear", clock())
        if readable:
            first_rx, accepted = None, False
            for _ in range(32):
                try:
                    data, address = udp.recvfrom(4096)
                except BlockingIOError:
                    break
                if sender and address[0] != sender:
                    continue
                cockpit.gpio.udp_rx()
                now = clock()
                first_rx = first_rx or now
                accepted |= cockpit.on_udp(data, now)
            if accepted:
                cockpit.send_ctrl(first_rx, clock)
        now = clock()
        cockpit.tick(now)
        if status_period and now >= next_status:
            print(cockpit.status(), flush=True)
            next_status = now + status_period


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bus-a", default="can0", help="SocketCAN interface on physical bus A")
    ap.add_argument("--bus-b", default="can1", help="SocketCAN interface on physical bus B")
    ap.add_argument("--udp-port", type=int, default=8000)
    ap.add_argument("--sender", help="only accept UDP from this IPv4 address")
    ap.add_argument("--fifo", type=int, metavar="PRIO", help="run under SCHED_FIFO at this priority (needs root)")
    ap.add_argument("--no-gpio", action="store_true", help="run without LEDs/markers (no libgpiod)")
    ap.add_argument("--gpiochip", default="/dev/gpiochip0")
    ap.add_argument("--log-dir", type=Path)
    args = ap.parse_args(argv)

    log_dir = args.log_dir or Path.home() / ".local/state/team4-lab3/demo" / time.strftime("%Y%m%d-%H%M%S")
    log_dir.mkdir(parents=True, exist_ok=True)
    crash = open(log_dir / "crash.log", "a", encoding="utf-8")
    faulthandler.enable(file=crash)
    if args.fifo:
        # Before any thread starts, so the notifier threads inherit the policy.
        os.sched_setscheduler(0, os.SCHED_FIFO, os.sched_param(args.fifo))
    log = EventLog(log_dir / "events.csv")
    gpio = NoGpio() if args.no_gpio else PiGpio(args.gpiochip)
    buses = [can.Bus(interface="socketcan", channel=name) for name in (args.bus_a, args.bus_b)]
    cockpit = Cockpit(buses, gpio, log, time.monotonic())
    notifiers = [can.Notifier(bus, [_BusListener(cockpit, index)]) for index, bus in enumerate(buses)]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setblocking(False)
    udp.bind(("0.0.0.0", args.udp_port))
    stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    signal.signal(signal.SIGINT, lambda *_: stop.set())
    if hasattr(signal, "SIGUSR1"):
        signal.signal(signal.SIGUSR1, lambda *_: setattr(cockpit, "inject", "range"))
        signal.signal(signal.SIGUSR2, lambda *_: setattr(cockpit, "inject", "crc"))
        signal.signal(signal.SIGRTMIN, lambda *_: setattr(cockpit, "pending_test", "latch"))
        signal.signal(signal.SIGRTMIN + 1, lambda *_: setattr(cockpit, "pending_test", "clear"))
    print(f"N1 cockpit pid={os.getpid()} A={args.bus_a} B={args.bus_b} udp={args.udp_port} "
          f"fifo={args.fifo or 'off'} logs={log_dir}", flush=True)
    try:
        run(cockpit, udp, stop, args.sender)
    except BaseException:
        crash.write(time.strftime("%Y-%m-%d %H:%M:%S ") + traceback.format_exc())
        crash.flush()
        raise
    finally:
        udp.close()
        for notifier in notifiers:
            notifier.stop()
        for bus in buses:
            bus.shutdown()
        gpio.close()
        log.close()
        crash.close()


if __name__ == "__main__":
    main()
