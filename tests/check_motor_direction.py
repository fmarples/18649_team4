"""Actuate ONE selected forward trial at 100% for at most 5 seconds.

Requires the current motor_test firmware with per-wheel 150 ms motion cutoff,
raised wheels, and an explicit --pulse flag. No automatic retry. Logs all serial
frames. Forward encoder signs come from the independent hand-turn calibration.
"""
import argparse
import json
import time
from pathlib import Path

import serial
from check_encoder_serial import FRAME as ENCODER
from check_motor_idle import FRAME as MOTOR


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", required=True)
    parser.add_argument("--pulse", action="store_true")
    parser.add_argument("--side", choices=("LEFT", "RIGHT", "BOTH"), default="LEFT")
    args = parser.parse_args()
    if not args.pulse:
        parser.error("--pulse is required: this check physically actuates the motor")
    records = []
    start = time.monotonic()
    samples = []
    last_phase = None
    last_encoder_print = -1.0
    path = Path("logs/motor-bench") / ("encoder-direction-" + args.side.lower() + "-" + time.strftime("%Y%m%d-%H%M%S") + ".json")

    try:
        with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
            def read_frame(deadline):
                nonlocal last_phase, last_encoder_print
                while time.monotonic() < deadline:
                    line = port.readline().decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    elapsed = round(time.monotonic() - start, 3)
                    records.append({"elapsed_s": elapsed, "line": line})
                    if line.startswith("ERROR") or "Booting Zephyr" in line:
                        raise RuntimeError("Firmware error/reset during measurement")
                    motor = MOTOR.fullmatch(line)
                    if motor:
                        phase, left, right, pins, en, fault, _, _ = motor.groups()
                        if phase != last_phase or fault != "0":
                            print(f"{elapsed:.3f}s {line}", flush=True)
                            last_phase = phase
                        if fault != "0":
                            raise RuntimeError("Trial aborted by firmware: " + line)
                        active = {"LEFT": ("100", "0", "0100", "10"),
                                  "RIGHT": ("0", "100", "0010", "01"),
                                  "BOTH": ("100", "100", "0110", "11")}[args.side]
                        expected = {"IDLE": ("0", "0", "0000", "00"),
                                    "ARMED": ("0", "0", "0000", "00"),
                                    args.side: active}
                        if expected.get(phase) != (left, right, pins, en):
                            raise RuntimeError("Unexpected output: " + line)
                        return "motor", phase
                    encoder = ENCODER.fullmatch(line)
                    if encoder:
                        sample = tuple(int(value) for value in encoder.groups())
                        if any(sample[i] for i in (4, 5, 6)):
                            raise RuntimeError("Encoder invalid transitions or GPIO errors: " + line)
                        samples.append(sample)
                        if elapsed - last_encoder_print >= 0.5:
                            print(f"{elapsed:.3f}s {line}", flush=True)
                            last_encoder_print = elapsed
                        return "encoder", sample
                raise TimeoutError("No valid serial frame before deadline")

            def wait_phase(phase, seconds=1):
                deadline = time.monotonic() + seconds
                while time.monotonic() < deadline:
                    if read_frame(deadline) == ("motor", phase):
                        return
                raise TimeoutError("Expected phase " + phase)

            try:
                port.reset_input_buffer()
                port.write(b"STOP\n")
                wait_phase("IDLE")
                print(f"One {args.side} forward 100% / max 5 s trial in 3 seconds...", flush=True)
                time.sleep(3)
                port.reset_input_buffer()
                port.write(b"ARM\n")
                wait_phase("ARMED")
                deadline = time.monotonic() + 1
                while True:
                    kind, value = read_frame(deadline)
                    if kind == "encoder":
                        baseline = value
                        break
                print(args.side + " FORWARD TRIAL NOW", flush=True)
                pulse_sent = time.monotonic()
                port.write((args.side + "\n").encode("ascii"))
                wait_phase(args.side)
                wait_phase("IDLE", seconds=6)
                elapsed_run = time.monotonic() - pulse_sent
                if not 4.8 <= elapsed_run <= 5.5:
                    raise RuntimeError(f"Unexpected run/acknowledgment duration: {elapsed_run:.3f}s")
                print(f"Output automatically disabled; host-observed run/ack interval {elapsed_run:.3f}s")
                # Observe coast-down with outputs disabled; do not extend/retrigger.
                end = time.monotonic() + 1
                while time.monotonic() < end:
                    kind, value = read_frame(end + 0.2)
                    if kind == "motor" and value != "IDLE":
                        raise RuntimeError("Output did not remain idle during coast-down")
                left = samples[-1][0] - baseline[0]
                right = samples[-1][1] - baseline[1]
                print(f"RESULT: raw encoder deltas left={left:+d}, right={right:+d}")
                if abs(left) < 8 and abs(right) < 8:
                    raise RuntimeError("No substantial encoder motion detected; no automatic retry")
                if args.side in ("LEFT", "BOTH") and left > -8:
                    raise RuntimeError("Left wheel did not show sufficient FORWARD motion")
                if args.side in ("RIGHT", "BOTH") and right < 8:
                    raise RuntimeError("Right wheel did not show sufficient FORWARD motion")
                if (args.side == "LEFT" and right != 0) or (args.side == "RIGHT" and left != 0):
                    raise RuntimeError("Unselected wheel counts changed: check motor-channel mapping/cross-motion")
                print(f"PASS: {args.side} forward trial completed; outputs disabled; no encoder faults")
            finally:
                port.write(b"STOP\n")
    finally:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(records, indent=2), encoding="utf-8")
        print("Capture:", path)


if __name__ == "__main__":
    main()
