"""Hardware checks for the encoder-only firmware (requires pyserial).

Run from the Zephyr virtualenv. Keep the 12 V supply OFF.
--expect streaming checks telemetry; --expect left/right checks that only the
named wheel counts, in BOTH directions, while a human turns it during the run.
"""

import argparse
import re
import time

import serial

FRAME = re.compile(
    r"ENC left=(-?\d+) right=(-?\d+) left_ab=([01]{2}) right_ab=([01]{2}) "
    r"invalid_left=(\d+) invalid_right=(\d+) errors=(\d+)"
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--seconds", type=float, default=5)
    parser.add_argument("--expect", choices=("streaming", "left", "right"), default="streaming")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")

    frames = []
    with serial.Serial(args.port, 115200, timeout=0.5) as port:
        port.reset_input_buffer()
        end = time.monotonic() + args.seconds
        while time.monotonic() < end:
            line = port.readline().decode("utf-8", errors="replace").strip()
            if line:
                print(line, flush=True)
            match = FRAME.fullmatch(line)
            if match:
                frames.append(tuple(int(value) for value in match.groups()))

    if len(frames) < 2:
        raise SystemExit("FAIL: expected at least two encoder telemetry frames")
    if any(frame[6] for frame in frames):
        raise SystemExit("FAIL: firmware reported GPIO read errors")
    if any(frames[-1][i] != frames[0][i] for i in (4, 5)):
        raise SystemExit("FAIL: invalid quadrature transitions occurred during capture")

    if args.expect != "streaming":
        moving = 0 if args.expect == "left" else 1
        stationary = 1 - moving
        deltas = [b[moving] - a[moving] for a, b in zip(frames, frames[1:])]
        if not (any(d > 0 for d in deltas) and any(d < 0 for d in deltas)):
            raise SystemExit("FAIL: expected counts to increase AND decrease on the selected wheel")
        if any(frame[stationary] != frames[0][stationary] for frame in frames):
            raise SystemExit("FAIL: the other wheel's count changed; keep it still/check wiring")

    print(f"PASS: {args.expect} ({len(frames)} frames)")
    if args.expect == "streaming":
        print("Streaming alone does NOT verify wheel motion, direction, or calibration.")


if __name__ == "__main__":
    main()
