"""Optional servo calibration console. Opening requests OFF; AUTO restores Pi control."""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import json
from pathlib import Path
import queue
import re
import threading
import time

BENCH_SERIAL = "066BFF485270535067124020"
DEFAULT_FILE = Path(__file__).resolve().parents[1] / "logs/part3_3/calibration.json"
TEAM_FILE = Path(__file__).resolve().parents[1] / "config/servo_calibration.json"
FIELDS = re.compile(r"(mode|pulse|left|center|right|marks|valid)=(\d+)")
COMMANDS = {
    "arm": "ARM", "+": "STEP 25", "-": "STEP -25",
    "+5": "STEP 5", "-5": "STEP -5", "left": "MARK LEFT",
    "center": "MARK CENTER", "right": "MARK RIGHT", "home": "CENTER",
    "live": "LIVE", "auto": "AUTO", "off": "OFF", "status": "STATUS",
}

def validate_calibration(data):
    points = [data.get(key) for key in ("left_us", "center_us", "right_us")]
    if any(type(p) is not int or not 500 <= p <= 2500 for p in points):
        raise ValueError("All three measured pulse widths must be integers within 500..2500 us.")
    l, c, r = points
    if not (l < c < r or l > c > r):
        raise ValueError("Center must lie strictly between left and right.")
    if data.get("period_us") != 20000:
        raise ValueError("This firmware uses a 20000 us (50 Hz) period.")
    return points

def read_calibration(path, team_path=TEAM_FILE, allow_fallback=True):
    """Prefer a local measurement; only a missing default file uses the team preset."""
    selected = team_path if allow_fallback and not path.exists() else path
    data = json.loads(selected.read_text(encoding="utf-8"))
    return selected, validate_calibration(data)

def parse_status(line):
    if not line.startswith("SERVO OK "):
        raise ValueError(line)
    data = {key: int(value) for key, value in FIELDS.findall(line)}
    if set(data) != {"mode", "pulse", "left", "center", "right", "marks", "valid"}:
        raise ValueError("Incomplete firmware response: " + line)
    return data

class Link:
    def __init__(self, ser, log=None):
        self.ser = ser
        self.log = log
        self.diagnostics = {}
        self.lock = threading.Lock()
        self.stop = threading.Event()
        self.responses = queue.Queue()
        self.failure = None
        self.reader = threading.Thread(target=self.read, daemon=True)
        self.keeper = threading.Thread(target=self.keepalive, daemon=True)
        self.reader.start()
        self.keeper.start()

    def send(self, command):
        with self.lock:
            self.ser.write(("SERVO " + command + "\n").encode("ascii"))

    def read(self):
        pending = bytearray()
        try:
            while not self.stop.is_set():
                pending.extend(self.ser.read(max(1, self.ser.in_waiting)))
                while b"\n" in pending:
                    line, _, pending = pending.partition(b"\n")
                    text = line.decode("ascii", errors="replace").strip()
                    if self.log:
                        self.log.write(datetime.now(timezone.utc).isoformat() + ' ' + text + '\n')
                        self.log.flush()
                    for prefix in ('STM ', 'DRIVE ', 'DIAG '):
                        if text.startswith(prefix): self.diagnostics[prefix] = text
                    # STM diagnostics may be interleaved with the response prefix.
                    position = text.find("SERVO ")
                    if position >= 0:
                        response = text[position:]
                        if response.startswith(("SERVO OK ", "SERVO ERR ", "SERVO HARDWARE_ERROR")):
                            self.responses.put(response)
                if len(pending) > 4096:
                    pending.clear()
        except Exception as exc:
            self.failure = exc
            self.stop.set()

    def keepalive(self):
        try:
            while not self.stop.wait(0.1):
                self.send("KEEPALIVE")
        except Exception as exc:
            self.failure = exc
            self.stop.set()

    def request(self, command):
        if self.failure:
            raise RuntimeError("USB connection failed: " + str(self.failure))
        self.send(command)
        try:
            response = self.responses.get(timeout=2)
        except queue.Empty:
            raise RuntimeError("No firmware reply. Check the flashed image and USB port.") from None
        return parse_status(response)

    def close(self):
        try:
            self.send("OFF")
            time.sleep(0.1)
        except Exception:
            pass
        self.stop.set()
        self.reader.join(timeout=1)
        self.keeper.join(timeout=1)

def describe(s):
    mode = {0: "OFF", 1: "MANUAL", 2: "LIVE", 3: "WAIT_CENTER"}.get(s["mode"], "UNKNOWN")
    return (f"{mode}: pulse={s['pulse']} us; "
            f"left={s['left']} center={s['center']} right={s['right']} us; "
            f"calibration={'READY' if s['valid'] else 'INCOMPLETE'}")

HELP = """
Opening this optional calibration console requests OFF, even during vehicle operation.
Normal steering needs no USB: firmware waits for a healthy Pi link and centered wheel.
Before ARM: verify separate servo supply, common ground, D14 signal, clear linkage.
arm     Start MANUAL at saved center, or nominal 1500 us if center unmarked.
+ / -   Increase/decrease pulse by 25 us. Watch which way the CAR wheels turn.
+5 / -5 Fine adjustment by 5 us.
center  Record the current position as straight ahead.
left    Record current safe position as the CAR's left endpoint.
right   Record current safe position as the CAR's right endpoint.
home    Return to the recorded center (MANUAL only).
save    Save the three measured positions to JSON.
load    Load previously measured positions from JSON (OFF only; no movement).
live    From MANUAL, follow the centered Logitech wheel over a healthy Pi link.
auto    Return to Pi control; wait for centered wheel/healthy link, then follow it.
        LIVE/AUTO need no USB heartbeat. MANUAL still has a 500 ms USB lease.
status  Show mode, pulse, and recorded positions.
diag    Show latest STM/DRIVE/DIAG lines (no motion command).
off     Stop PWM; arm again to return to manual calibration.
quit    Stop PWM and close. Removing servo power is the physical stop.
"""

def main():
    import serial
    from serial.tools import list_ports
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", help="Optional COM port override for an intentionally selected board")
    parser.add_argument("--file", type=Path, help="Calibration JSON override; default: local saved values, then tracked team preset")
    parser.add_argument("--log", type=Path, help="New file for timestamped USB diagnostics; does not overwrite")
    args = parser.parse_args()
    explicit_file = args.file is not None
    if args.file is None:
        args.file = DEFAULT_FILE
    all_ports = list(list_ports.comports())
    ports = [p.device for p in all_ports if p.serial_number == BENCH_SERIAL]
    port = args.port or (ports[0] if len(ports) == 1 else None)
    if not port:
        parser.error("The separate LED/servo board was not found. Connect its ST-LINK USB; close miniterm.")
    print(f"Board port: {port}\nCalibration file: {args.file}\n{HELP}")
    board_serial = next((p.serial_number for p in all_ports if p.device == port), None)
    with ExitStack() as resources:
        log = None
        if args.log:
            args.log.parent.mkdir(parents=True, exist_ok=True)
            log = resources.enter_context(args.log.open('x', encoding='utf-8'))
        ser = resources.enter_context(serial.Serial(port, 115200, timeout=0.1, write_timeout=0.5))
        ser.reset_input_buffer()
        link = Link(ser, log)
        try:
            print(describe(link.request("OFF")))
            while True:
                cmd = input("servo> ").strip().lower()
                if cmd in ("quit", "exit", "q"):
                    break
                try:
                    if cmd == "help":
                        print(HELP)
                    elif cmd == "diag":
                        for prefix in ('STM ', 'DRIVE ', 'DIAG '):
                            print(link.diagnostics.get(prefix, prefix + 'not received yet'))
                    elif cmd == "save":
                        s = link.request("STATUS")
                        if not s["valid"]:
                            raise ValueError("Record safe LEFT, CENTER and RIGHT positions first.")
                        data = {"period_us": 20000, "left_us": s["left"],
                                "center_us": s["center"], "right_us": s["right"],
                                "recorded_at": datetime.now(timezone.utc).isoformat(),
                                "board_serial": board_serial,
                                "source": "Operator-saved calibration; may contain loaded or manually marked values. Verify physical limits separately."}
                        validate_calibration(data)
                        args.file.parent.mkdir(parents=True, exist_ok=True)
                        args.file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
                        print(f"Saved calibration: {args.file}")
                    elif cmd == "load":
                        selected, values = read_calibration(args.file, allow_fallback=not explicit_file)
                        print(describe(link.request("LOAD " + " ".join(map(str, values)))))
                        print(f"Loaded calibration from: {selected}")
                        print("Use this file only for the same servo/linkage. PWM is still OFF.")
                    elif cmd in COMMANDS:
                        print(describe(link.request(COMMANDS[cmd])))
                    elif cmd:
                        print("Unknown command. Type help.")
                except (ValueError, OSError, json.JSONDecodeError) as exc:
                    print(f"Not applied: {exc}")
                    print("For LIVE: mark all positions, center Logitech wheel, establish Pi link, clear self-test.")
        except (KeyboardInterrupt, EOFError):
            print("\nClosing; requesting PWM OFF.")
        finally:
            link.close()

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit(f"Servo console stopped: {exc}\nMANUAL lease expires within 500 ms. LIVE follows the Pi link; remove servo power if needed.")
