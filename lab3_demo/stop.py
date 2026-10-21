"""Stop only the recorded demo session: the laptop synthetic sender and the Pi cockpit.

    python lab3_demo/stop.py

Identity is checked (sender create time and script path; cockpit command line)
before signaling. Logs stay in the remote folder named in the archived state.
"""
import json
import subprocess
from pathlib import Path

import psutil

STATE_DIR = Path(__file__).resolve().parent.parent / "logs/lab3-can/demo"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def main():
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
    code = f"""
import json, os, signal, socket, time
from pathlib import Path
pid, script = {state['pid']!r}, {state['script']!r}
proc = Path('/proc') / str(pid)
if proc.exists() and script.encode() in (proc / 'cmdline').read_bytes().split(b'\\0'):
    os.kill(pid, signal.SIGTERM)
    end = time.monotonic() + 10
    while proc.exists() and (proc / 'stat').read_text().split(') ', 1)[1].split()[0] != 'Z':
        if time.monotonic() > end:
            raise RuntimeError('cockpit did not stop')
        time.sleep(0.1)
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind(('0.0.0.0', 8000))
print(json.dumps({{'stopped': pid, 'udp8000_free': True}}))
"""
    result = subprocess.run(["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "wheelpi", "python3 -"],
                            input=code.encode(), capture_output=True, creationflags=FLAGS, timeout=20)
    (STATE_DIR / f"stop-{state['pid']}.log").write_bytes(result.stdout + result.stderr)
    result.check_returncode()
    (STATE_DIR / "state.json").rename(STATE_DIR / f"stopped-state-{state['pid']}.json")
    print(result.stdout.decode().strip())


if __name__ == "__main__":
    main()
