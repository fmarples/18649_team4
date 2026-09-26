"""Real-board smoke check. Sends only STOP and STATUS; NEVER arms a motor."""
import argparse
import re
import time

import serial

FRAME = re.compile(
    r"MOTOR phase=(IDLE|ARMED|LEFT|RIGHT|BOTH) left=(\d+) right=(\d+) "
    r"in=([01]{4}) en=([01]{2}) fault=(-?\d+) accepted=(\d+) rejected=(\d+)"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=4)
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    seen = 0
    with serial.Serial(args.port, 115200, timeout=0.5, write_timeout=1) as port:
        port.reset_input_buffer()
        port.write(b"STOP\nSTATUS\n")
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            line = port.readline().decode("utf-8", errors="replace").strip()
            if line:
                print(line, flush=True)
            if line.startswith("ERROR"):
                raise SystemExit("FAIL: firmware reported an error")
            match = FRAME.fullmatch(line)
            if match:
                phase, left, right, direction, enable, fault, _, _ = match.groups()
                if (phase, left, right, direction, enable, fault) != (
                    "IDLE", "0", "0", "0000", "00", "0"
                ):
                    raise SystemExit("FAIL: expected idle, zero duty and low control pin readbacks")
                seen += 1
    if seen < 4:
        raise SystemExit("FAIL: no sustained MOTOR idle telemetry")
    print(f"PASS: {seen} idle frames; MCU reads IN1-4 and ENA/ENB low; no pulses requested")
    print("This is not an oscilloscope measurement or a powered motor/stop-time test.")


if __name__ == "__main__":
    main()
