"""Bench stand-in for the course wheel proxy: 276-byte wheel UDP to the Pi every 20 ms.

Started by start.py --synthetic; exits when logs/lab3-can/demo/stop.request appears
and sends nothing while pause.request exists (the test panel's "proxy stopped").
Steering steps left/center/right every 0.5 s, throttle near 50 %, brake released,
no buttons, so SRV, PWM_OUT and DIR_A all show activity on the scope.
"""
import json
import socket
import struct
import subprocess
import time
from pathlib import Path

STATE_DIR = Path(__file__).resolve().parent.parent / "logs/lab3-can/demo"
STEER = (-32768, 0, 32767, 0)


def main():
    packet = bytearray(276)
    struct.pack_into("<i", packet, 8, 0)       # throttle axis 0 -> ~50 %
    struct.pack_into("<i", packet, 24, 32767)  # brake released
    count = 0
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as udp:
        udp.connect((pi_address(), 8000))
        deadline = time.monotonic()
        while not (STATE_DIR / "stop.request").exists():
            if not (STATE_DIR / "pause.request").exists():
                struct.pack_into("<Ii", packet, 0, count, STEER[(count // 25) % len(STEER)])
                udp.send(packet)
                count += 1
                if count % 500 == 0:
                    print(json.dumps({"packets": count}), flush=True)
            deadline = max(deadline + 0.02, time.monotonic())
            time.sleep(max(0.0, deadline - time.monotonic()))
    print(json.dumps({"stopped": count}), flush=True)


def pi_address():
    """Resolve the wheelpi SSH alias through ssh's own config."""
    out = subprocess.run(["ssh", "-G", "wheelpi"], capture_output=True, text=True, check=True,
                         creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stdout
    return next(line.split()[1] for line in out.splitlines() if line.startswith("hostname "))


if __name__ == "__main__":
    main()
