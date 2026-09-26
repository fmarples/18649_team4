#!/usr/bin/env python3
"""Part 2 link-only bridge: wheel UDP -> UART; STM status -> console/CSV.

This demonstrator must be extended before driving motors or a servo.
"""
import argparse
import csv
import socket
import time
from pathlib import Path
from part2_protocol import command, wheel_packet, pop_status, is_newer, STATES

TX_PERIOD = 0.020
UDP_FRESH = 0.100


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--serial', default='/dev/serial0')
    ap.add_argument('--mode', choices=('demo', 'live', 'bad-range', 'bad-crc'), default='live')
    ap.add_argument('--sender', help='Optional permitted laptop IPv4 address')
    ap.add_argument('--log', help='New CSV path for every received status frame')
    args = ap.parse_args()
    import serial
    udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    if args.mode == 'live':
        udp.bind(('0.0.0.0', 8000))
    udp.setblocking(False)
    log = None
    writer = None
    if args.log:
        p = Path(args.log)
        p.parent.mkdir(parents=True, exist_ok=True)
        log = p.open('x', newline='')  # Preserve previous measurements.
    try:
        with serial.Serial(args.serial, 115200, timeout=0, write_timeout=0.050) as uart:
            uart.reset_input_buffer()
            started = time.monotonic()
            next_tx = started
            next_display = started
            last_udp = None
            previous_counter = None
            axes = None
            seq = 0
            buffer = bytearray()
            previous_status_seq = None
            previous_stm_ms = None
            no_status_notice = started + 2
            was_streaming = False
            print('LINK-ONLY mode=%s; UART=%s 115200 8N1; Ctrl+C stops TX.' %
                  (args.mode, args.serial), flush=True)
            print('Current sensors are UNAVAILABLE in this starter. No actuator control.', flush=True)
            while True:
                now = time.monotonic()
                incoming = uart.read(4096)
                buffer.extend(incoming)
                for status in pop_status(buffer):
                    status['pi_receive_s'] = now - started
                    gap = None if previous_status_seq is None else ((status['status_seq'] - previous_status_seq) & 0xffffffff)
                    interval = None if previous_stm_ms is None else ((status['stm_ms'] - previous_stm_ms) & 0xffffffff)
                    status['stm_interval_ms'] = interval if gap == 1 else None
                    previous_status_seq = status['status_seq']
                    previous_stm_ms = status['stm_ms']
                    no_status_notice = now + 2
                    if log:
                        if writer is None:
                            writer = csv.DictWriter(log, fieldnames=list(status))
                            writer.writeheader()
                        writer.writerow(status)
                    if now >= next_display:
                        mode = status['state']
                        name = STATES[mode] if mode < len(STATES) else 'UNKNOWN'
                        print('STM %s steer=%d thr=%d brk=%d status_seq=%d dt=%sms rejected=%d currents=UNAVAILABLE' %
                              (name, status['steer'], status['throttle'], status['brake'],
                               status['status_seq'], status['stm_interval_ms'], status['rejected']), flush=True)
                        next_display = now + 0.25
                if now >= no_status_notice:
                    print('No valid STM status for 2s: check STM TX D8 -> Pi pin 10 and shared ground.', flush=True)
                    no_status_notice = now + 2
                # Flush expired input before accepting a restarted UDP sequence.
                if last_udp is not None and now - last_udp >= UDP_FRESH:
                    axes = None
                    previous_counter = None
                    last_udp = None
                    if was_streaming:
                        print('UDP stale: UART command transmission stopped.', flush=True)
                        was_streaming = False
                if args.mode == 'live':
                    # Bounded batch: still return to status handling under excess UDP load.
                    for _ in range(32):
                        try:
                            data, address = udp.recvfrom(4096)
                        except BlockingIOError:
                            break
                        if args.sender and address[0] != args.sender:
                            continue
                        try:
                            counter, *new_axes = wheel_packet(data)
                        except ValueError as err:
                            axes = None
                            last_udp = None
                            print('Rejected UDP input; TX paused: '+str(err), flush=True)
                            continue
                        if not is_newer(counter, previous_counter):
                            continue
                        previous_counter = counter
                        axes = new_axes
                        last_udp = time.monotonic()
                        # Forward every valid new UDP state immediately.
                        uart.write(command(seq, *axes))
                        seq = (seq + 1) & 0xffffffff
                        next_tx = last_udp + TX_PERIOD
                        was_streaming = True
                elif now >= next_tx:
                    steering = (-20000, 0, 20000)[int(now - started) % 3]
                    axes = [40000 if args.mode == 'bad-range' else steering, 32767, 32767, 0]
                now = time.monotonic()
                if now >= next_tx and axes is not None:
                    if args.mode != 'live' or (last_udp is not None and now - last_udp < UDP_FRESH):
                        frame = command(seq, *axes)
                        if args.mode == 'bad-crc':
                            frame = frame[:-1] + bytes([frame[-1] ^ 1])
                        uart.write(frame)
                        seq = (seq + 1) & 0xffffffff
                    next_tx = now + TX_PERIOD
                time.sleep(0.001)
    except KeyboardInterrupt:
        print('\nBridge stopped; STM should time out after the last valid command.')
    finally:
        udp.close()
        if log:
            log.close()


if __name__ == '__main__':
    main()
