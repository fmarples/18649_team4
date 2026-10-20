#!/usr/bin/env python3
"""Lab 3 N1: wheel UDP -> CTRL/BLINK/HB_N1 on dual SocketCAN.

Retains the Lab 2 276-byte wheel UDP packet layout and port 8000. This demo
application emits compact Lab 3 frames; it does not drive physical actuators.
"""
from __future__ import annotations
import argparse, csv, socket, struct, time, threading
from pathlib import Path
import can
import can_protocol as p
from wheel_input import decode_wheel_packet
from timing_gpio import create_trace

UDP_PORT = 8000
UDP_FRESH_S = 0.100
PERIOD_S = 0.020
HB_IDS = {p.HB_N1: p.ZONE_N1, p.HB_N2: p.ZONE_N2, p.HB_N3: p.ZONE_N3}



class CsvLog:
    def __init__(self, path):
        self.file = open(path, "w", newline="", buffering=65536)
        self.lock = threading.Lock()
        self.writer = csv.DictWriter(self.file, fieldnames=["mono_ns","event","id_hex","seq","interface","udp_seq","latency_us","detail"])
        self.writer.writeheader()
    def write(self, **row):
        row.setdefault("mono_ns", time.monotonic_ns())
        row.setdefault("id_hex", "")
        row.setdefault("seq", "")
        row.setdefault("interface", "")
        row.setdefault("udp_seq", "")
        row.setdefault("latency_us", "")
        row.setdefault("detail", "")
        with self.lock:
            self.writer.writerow(row)
    def close(self):
        with self.lock: self.file.close()


class Receiver(can.Listener):
    """python-can notifier listener: logs RX, tracks heartbeat and FORCE frames."""
    def __init__(self, log, hb_last, hb_state, force_box, fault_box):
        self.log, self.hb_last, self.hb_state, self.force_box, self.fault_box = log, hb_last, hb_state, force_box, fault_box
        self.last_seq = {}
    def on_message_received(self, msg):
        now = time.monotonic_ns()
        frame_data = bytes(msg.data)
        is_valid = p.valid(frame_data)
        duplicate = False
        if is_valid and msg.dlc == 8:
            source = frame_data[1] if msg.arbitration_id == p.FAULT else 0
            key = (msg.arbitration_id, source)
            seq = frame_data[0] & 0x0F
            duplicate = self.last_seq.get(key) == seq
            if not duplicate: self.last_seq[key] = seq
        if msg.arbitration_id in HB_IDS and is_valid:
            zone = HB_IDS[msg.arbitration_id]
            self.hb_last[(zone, msg.channel)] = now
            self.hb_state[zone] = frame_data[1]
        if msg.arbitration_id == p.FORCE and is_valid and not duplicate:
            self.force_box["counter"] = bytes(msg.data)[1] if bytes(msg.data)[1] < 128 else bytes(msg.data)[1] - 256
        if msg.arbitration_id == p.FAULT and is_valid and not duplicate:
            self.fault_box["latched"] = (frame_data[2] != 0)
        # latency_us: callback body (HB/FORCE_RX processing) before this synchronous log write.
        self.log.write(mono_ns=now, event="CAN_RX", id_hex=f"0x{msg.arbitration_id:03X}",
                       seq=(msg.data[0] & 0x0F) if msg.dlc else "", interface=str(msg.channel),
                       latency_us=f"{(time.monotonic_ns()-now)/1000.0:.3f}",
                       detail=("valid_crc_duplicate" if duplicate else "valid_crc") if is_valid else "bad_crc_or_noncatalog")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("live","demo","bad-crc","bad-range"), default="live")
    ap.add_argument("--sender", help="optional source IPv4 address allowed to send UDP")
    ap.add_argument("--log", default="lab3_pi_timing.csv")
    ap.add_argument("--trace-gpio", action="store_true")
    ap.add_argument("--gpiochip", default="/dev/gpiochip0")
    ap.add_argument("--udp-port", type=int, default=UDP_PORT)
    ap.add_argument("--force-demo", action="store_true", help="run synthetic commands instead of receiving wheel UDP")
    args = ap.parse_args()
    log = CsvLog(args.log)
    hb_last, hb_state, force_box, fault_box = {}, {}, {"counter":0}, {"latched":False}
    buses = [can.Bus(interface="socketcan", channel="can0"), can.Bus(interface="socketcan", channel="can1")]
    notifiers = [can.Notifier(bus, [Receiver(log, hb_last, hb_state, force_box, fault_box)]) for bus in buses]
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp.setblocking(False)
    if args.mode == "live" and not args.force_demo:
        udp.bind(("0.0.0.0", args.udp_port))
    seq = {frame_id:0 for frame_id in p.CATALOG_IDS}
    def next_seq(frame_id):
        value = seq[frame_id]
        seq[frame_id] = (value + 1) & 0x0F
        return value
    # Writes the frame to can0 then can1. on_sent runs right after both writes,
    # before any CSV logging, so CTRL's CMD_TX marker excludes log I/O.
    def send_both(frame_id, payload, event="CAN_TX", on_sent=None):
        rows = []
        for idx, bus in enumerate(buses):
            channel = f"can{idx}"
            t0 = time.monotonic_ns()
            trace.can_tx(channel)
            try:
                bus.send(can.Message(arbitration_id=frame_id, is_extended_id=False, data=payload), timeout=0.001)
                detail = "send_return; bus enqueue timestamp approximation"
            except (can.CanError, OSError) as exc:
                detail = f"SEND_ERROR:{type(exc).__name__}:{exc}"
            rows.append(dict(mono_ns=t0, event=event, id_hex=f"0x{frame_id:03X}", seq=payload[0]&0x0F,
                             interface=channel, detail=detail))
        if on_sent: on_sent()
        for row in rows: log.write(**row)
    started = time.monotonic()
    next_hb = started
    next_ctrl = started
    next_blink = started
    next_status = started
    last_udp_time = None
    last_udp_seq = None
    last_udp_rx_ns = None
    last_values = (0,0,0,0,0)
    next_demo = started
    blink_mode = p.BLINK_OFF
    blink_phase = 0
    n1_state = p.STATE_ERROR
    last_blink_button_state = None
    previous_buttons = 0
    last_test_press = 0.0
    ever_operational = False
    peer_failure_announced = False
    try:
        with create_trace(args.trace_gpio, args.gpiochip) as trace:
            print("Lab 3 N1 ready: dual SocketCAN, 500 kbit/s expected; Ctrl+C stops heartbeat/TX.")
            print("CSV:", Path(args.log).resolve())
            while True:
                now = time.monotonic()
                pending_ctrl = False
                batch_rx_ns = None
                if args.mode == "live" and not args.force_demo:
                    for _ in range(32):
                        rx_start_ns = time.monotonic_ns()
                        try: data, address = udp.recvfrom(4096)
                        except BlockingIOError: break
                        trace.udp_rx()
                        rx_ns = time.monotonic_ns()
                        if batch_rx_ns is None:
                            batch_rx_ns = rx_ns
                        log.write(mono_ns=rx_ns, event="UDP_RX", detail=f"peer={address[0]} bytes={len(data)}")
                        if args.sender and address[0] != args.sender: continue
                        try: counter, steer, throttle, brake, buttons = decode_wheel_packet(data)
                        except ValueError as exc:
                            log.write(event="UDP_REJECT", detail=str(exc)); continue
                        if last_udp_seq is not None and not (0 < ((counter-last_udp_seq)&0xFFFFFFFF) < 0x80000000):
                            log.write(event="UDP_OLD_SEQ", udp_seq=counter); continue
                        last_udp_seq = counter
                        last_udp_time = time.monotonic()
                        last_udp_rx_ns = rx_ns
                        last_values = (steer, throttle, brake, buttons, counter)
                        pending_ctrl = True
                        log.write(mono_ns=rx_start_ns, event="TASK_UDP_RX", udp_seq=counter,
                                  latency_us=f"{(time.monotonic_ns()-rx_start_ns)/1000.0:.3f}",
                                  detail="accepted datagram: recvfrom, marker, log, decode, freshness")
                elif (args.mode != "live" or args.force_demo) and now >= next_demo:
                    last_values = ((-20000,0,20000)[int(now-started)%3], 80, 0, 0, int(now*1000)&0xffffffff)
                    last_udp_time = now  # Synthetic demo input is fresh, but has no real UDP_RX latency sample.
                    pending_ctrl = True
                    next_demo = now + PERIOD_S
                # On stale/invalid source, output a demo-safe command (no throttle, brake 100%).
                stale = (last_udp_time is None or time.monotonic()-last_udp_time > UDP_FRESH_S) if args.mode == "live" and not args.force_demo else False
                steer, throttle, brake, buttons, counter = last_values
                if stale:
                    steer, throttle, brake = 0, 0, 100
                if args.mode == "bad-range": steer = 32767  # legal endpoint but exercises boundary
                if pending_ctrl or (now >= next_ctrl and stale):
                    ctrl_seq = next_seq(p.CTRL)
                    if args.mode == "bad-range":
                        # CRC-valid, but deliberately violates the 0..100 pedal range.
                        ctrl = p.seal(struct.pack("<BhBBBB", p.seq_byte(ctrl_seq, p.FLAG_VALID), steer, 101, brake, buttons, 0))
                    else:
                        ctrl = p.pack_ctrl(ctrl_seq, steer, throttle, brake, buttons)
                    if args.mode == "bad-crc": ctrl = ctrl[:-1] + bytes([ctrl[-1] ^ 0xFF])
                    sent = {}
                    def mark_sent():
                        sent["ns"] = time.monotonic_ns()
                        trace.cmd_tx()  # Handout: CMD_TX toggles after the writes to can0 and can1.
                    send_start_ns = time.monotonic_ns()
                    send_both(p.CTRL, ctrl, on_sent=mark_sent)
                    cmd_mark_ns = send_end_ns = sent["ns"]
                    if last_udp_rx_ns is not None and not stale:
                        log.write(mono_ns=cmd_mark_ns, event="UDP_TO_CMD_TX", id_hex="0x010", seq=ctrl_seq,
                                  udp_seq=counter, latency_us=f"{(cmd_mark_ns-last_udp_rx_ns)/1000.0:.3f}",
                                  detail="UDP userspace receive to post-write CMD_TX marker; not physical NIC arrival")
                    if args.trace_gpio and pending_ctrl and batch_rx_ns is not None:
                        log.write(mono_ns=cmd_mark_ns, event="UDP_BATCH_TO_CMD_TX", id_hex="0x010", seq=ctrl_seq,
                                  udp_seq=counter, latency_us=f"{(cmd_mark_ns-batch_rx_ns)/1000.0:.3f}",
                                  detail="first received datagram in batch to post-write CMD_TX marker; paired GPIO edges")
                    log.write(mono_ns=send_start_ns, event="CTRL_SEND_GROUP", id_hex="0x010", seq=ctrl_seq, udp_seq=counter,
                              latency_us=f"{(send_end_ns-send_start_ns)/1000.0:.3f}", detail="dual SocketCAN write calls, excluding logs; not wire latency")
                    next_ctrl = time.monotonic() + PERIOD_S
                # Wheel button bit 0 is the cockpit-zone test button in this starter.
                if (buttons & 1) and not (previous_buttons & 1):
                    press_time = time.monotonic()
                    reason = 0 if last_test_press and press_time-last_test_press <= 0.400 else 1
                    send_both(p.FAULT, p.pack_fault(next_seq(p.FAULT), p.ZONE_N1, reason))
                    fault_box["latched"] = (reason != 0)
                    log.write(event="WHEEL_TEST_BUTTON", id_hex="0x020", detail="double-press clear requested" if reason == 0 else "N1 test fault requested")
                    last_test_press = 0.0 if reason == 0 else press_time
                previous_buttons = buttons
                if now >= next_hb:
                    hb_now_ns = time.monotonic_ns()
                    bus_health = []
                    for channel in ("can0", "can1"):
                        seen = [stamp for (zone, iface), stamp in hb_last.items()
                                if zone in (p.ZONE_N2, p.ZONE_N3) and str(iface) == channel and hb_now_ns-stamp < 60_000_000]
                        bus_health.append(bool(seen))
                    peers_ready = all(hb_state.get(peer, p.STATE_ERROR) == p.STATE_OK and
                                      any(zone == peer and hb_now_ns-stamp < 60_000_000
                                          for (zone, _iface), stamp in hb_last.items())
                                      for peer in (p.ZONE_N2, p.ZONE_N3))
                    ctrl_fresh = last_udp_time is not None and (time.monotonic()-last_udp_time) < UDP_FRESH_S
                    if peers_ready and ctrl_fresh:
                        ever_operational = True
                    if ever_operational and not peers_ready and not peer_failure_announced:
                        send_both(p.FAULT, p.pack_fault(next_seq(p.FAULT), p.ZONE_N1, 4))
                        peer_failure_announced = True
                        log.write(event="PEER_TIMEOUT_FAULT", id_hex="0x020", detail="peer heartbeat missing or zone reports ERROR")
                    elif peer_failure_announced and peers_ready and ctrl_fresh:
                        send_both(p.FAULT, p.pack_fault(next_seq(p.FAULT), p.ZONE_N1, 0))
                        peer_failure_announced = False
                        log.write(event="PEER_RECOVERY_CLEAR", id_hex="0x020", detail="heartbeats recovered")
                    zone_state = p.STATE_OK if peers_ready and ctrl_fresh and not fault_box["latched"] and not peer_failure_announced else p.STATE_ERROR
                    n1_state = zone_state
                    hb_tx_ns = time.monotonic_ns()
                    send_both(p.HB_N1, p.pack_heartbeat(next_seq(p.HB_N1), zone_state, bus_health[0], bus_health[1]))
                    hb_end_ns = time.monotonic_ns()
                    log.write(mono_ns=hb_now_ns, event="TASK_HB_MON", id_hex=f"0x{p.HB_N1:03X}",
                              latency_us=f"{(hb_tx_ns-hb_now_ns)/1000.0:.3f}", detail="peer health evaluation, including any fault send")
                    log.write(mono_ns=hb_tx_ns, event="TASK_HB_TX", id_hex=f"0x{p.HB_N1:03X}",
                              latency_us=f"{(hb_end_ns-hb_tx_ns)/1000.0:.3f}", detail="dual SocketCAN heartbeat group including synchronous logs")
                    next_hb = now + PERIOD_S
                # Button convention for this starter: bit1=left, bit2=right, bit3=hazard; adjust to your wheel map.
                blink_start_ns = time.monotonic_ns()
                blink_sent = True
                requested = p.BLINK_HAZARD if n1_state == p.STATE_ERROR or fault_box["latched"] or buttons & (1<<3) else p.BLINK_LEFT if buttons & (1<<1) else p.BLINK_RIGHT if buttons & (1<<2) else p.BLINK_OFF
                if requested != blink_mode:
                    blink_mode, blink_phase = requested, 1 if requested else 0
                    next_blink = now
                if blink_mode != p.BLINK_OFF and now >= next_blink:
                    blink_phase ^= 1
                    next_blink = now + 0.5
                    send_both(p.BLINK, p.pack_blink(next_seq(p.BLINK), blink_mode, blink_phase, int(time.monotonic()*1000)))
                elif requested != p.BLINK_OFF and now >= next_blink:
                    send_both(p.BLINK, p.pack_blink(next_seq(p.BLINK), blink_mode, blink_phase, int(time.monotonic()*1000)))
                    next_blink = now + 0.5
                elif requested == p.BLINK_OFF and (last_blink_button_state is None or last_blink_button_state != requested):
                    send_both(p.BLINK, p.pack_blink(next_seq(p.BLINK), p.BLINK_OFF, 0, int(time.monotonic()*1000)))
                else:
                    blink_sent = False
                if blink_sent:
                    log.write(mono_ns=blink_start_ns, event="TASK_BLINK_TX", id_hex=f"0x{p.BLINK:03X}",
                              latency_us=f"{(time.monotonic_ns()-blink_start_ns)/1000.0:.3f}", detail="blink decision and dual SocketCAN group including synchronous logs")
                last_blink_button_state = requested
                if now >= next_status:
                    print(f"CTRL steer={steer:6d} throttle={throttle:3d}% brake={brake:3d}% stale={stale} force={force_box['counter']} heartbeat_frames={len(hb_last)}")
                    next_status = now + 1.0
                time.sleep(0.001)
    except KeyboardInterrupt:
        print("Stopping N1. The STM32 nodes should enter ERROR after heartbeat/CTRL timeout.")
    finally:
        udp.close()
        for notifier in notifiers: notifier.stop()
        for bus in buses: bus.shutdown()
        log.close()

if __name__ == "__main__": main()
