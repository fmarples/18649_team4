"""USB command reception regression. Only arms/disarms; never starts a motor."""
import argparse
import time

import serial
from check_motor_idle import FRAME


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--paced", action="store_true", help="Diagnostic: 30 ms between bytes")
    args = parser.parse_args()
    with serial.Serial(args.port, 115200, timeout=0.2, write_timeout=1) as port:
        def send(text):
            data = (text + "\n").encode("ascii")
            if args.paced:
                for byte in data:
                    port.write(bytes([byte]))
                    time.sleep(0.03)
            else:
                port.write(data)

        def wait_phase(expected):
            end = time.monotonic() + 2
            while time.monotonic() < end:
                line = port.readline().decode("utf-8", errors="replace").strip()
                if line:
                    print(line, flush=True)
                m = FRAME.fullmatch(line)
                if not m:
                    continue
                phase, left, right, pins, en, fault, _, _ = m.groups()
                if (left, right, pins, en, fault) != ("0", "0", "0000", "00", "0"):
                    raise SystemExit("FAIL: expected no actuation or fault during command-only check")
                if phase == expected:
                    return
            raise SystemExit(f"FAIL: {expected} was not acknowledged")

        port.reset_input_buffer()
        try:
            send("STOP")
            wait_phase("IDLE")
            send("ARM")
            wait_phase("ARMED")
            send("STOP")
            wait_phase("IDLE")
            print("PASS: ARM acknowledged and STOP disarmed, without any motor output")
        finally:
            send("STOP")


if __name__ == "__main__":
    main()
