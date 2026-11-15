"""Stop only the recorded demo session: the laptop synthetic sender and the Pi cockpit service.

    python lab3_demo/stop.py

The sender is identified by PID and create time before it is signaled. The Pi
service is stopped and disabled, so it no longer starts at boot; start.py
enables it again. Sudo uses the same password source as start.py. Logs stay in
the remote folder named in the archived state.
"""
import json
from pathlib import Path

import psutil

from pi_ssh import STATE_DIR, UNIT, remote_python, sudo, sudo_password


def main(password=None):
    state = json.loads((STATE_DIR / "state.json").read_text(encoding="utf-8"))
    (STATE_DIR / "stop.request").touch()
    if state.get("sender_pid"):
        try:
            sender = psutil.Process(state["sender_pid"])
            if sender.create_time() != state["sender_create_time"]:
                raise SystemExit("Sender PID was reused; refusing to stop it")
            try:
                sender.wait(timeout=3)
            except psutil.TimeoutExpired:
                sender.terminate()
                sender.wait(timeout=3)
        except psutil.NoSuchProcess:
            pass
    sudo(password or sudo_password(), f"systemctl disable --now {UNIT}")
    result = remote_python(f"""
import json, socket, subprocess
active = subprocess.run(['systemctl', 'is-active', {UNIT!r}], capture_output=True, text=True).stdout.strip()
assert active != 'active', active
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(('0.0.0.0', 8000))
print(json.dumps({{'stopped': {UNIT!r}, 'state': active, 'udp8000_free': True}}))
""")
    name = Path(state["remote"]).name
    (STATE_DIR / f"stop-{name}.log").write_text(result, encoding="utf-8")
    (STATE_DIR / "state.json").replace(STATE_DIR / f"stopped-state-{name}.json")
    print(result.strip())


if __name__ == "__main__":
    main()
