"""Deploy and start the N1 cockpit on the Pi (SSH alias `wheelpi`).

    python lab3_demo/start.py [--synthetic] [--no-fifo] [--restart]

Copies lab3_demo/pi to a fresh remote folder, runs its unit tests there, brings
can0/can1 up at 500 kbit/s with restart-ms 100 when they are down, starts
cockpit.py detached and applies SCHED_FIFO 1 to all its threads with chrt.
Sudo is needed only for the CAN links and FIFO. The password comes from the
gitignored lab3_demo/pi_sudo_password.txt when it exists, otherwise once from
the terminal (or one stdin line). --synthetic also starts a
laptop wheel-format UDP sender for bench checks without the course proxy.
Ownership state: logs/lab3-can/demo/state.json; stop with lab3_demo/stop.py.
A recorded session whose cockpit has died is cleaned up automatically; a live
one is replaced only with --restart (the test panel's Restart button).
"""
import argparse
import getpass
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
STATE_DIR = ROOT / "logs/lab3-can/demo"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "wheelpi"]
PI_PINS = (5, 6, 12, 17, 22, 23, 27)
# Local only (gitignored): the repository is public on GitHub.
PASSWORD_FILE = HERE / "pi_sudo_password.txt"


def call(args, **kwargs):
    # ssh forwards inherited stdin to the remote command, which would eat the password line.
    if "input" not in kwargs:
        kwargs.setdefault("stdin", subprocess.DEVNULL)
    return subprocess.run(args, creationflags=FLAGS, **kwargs)


def remote_python(code, timeout=15):
    result = call(SSH + ["python3 -"], input=code.encode(), capture_output=True, timeout=timeout)
    if result.returncode:
        raise RuntimeError(result.stdout.decode() + result.stderr.decode())
    return result.stdout.decode()


def cockpit_alive(state):
    """True when the recorded PID on the Pi still runs the recorded cockpit script."""
    code = (f"from pathlib import Path\n"
            f"p = Path('/proc/{int(state['pid'])}/cmdline')\n"
            f"print(p.exists() and {state['script']!r}.encode() in p.read_bytes().split(bytes(1)))\n")
    return remote_python(code).strip() == "True"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true", help="also start the laptop synthetic UDP sender")
    ap.add_argument("--no-fifo", action="store_true", help="skip SCHED_FIFO (no sudo if CAN is already up)")
    ap.add_argument("--restart", action="store_true", help="stop a running recorded session first")
    args = ap.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    if (STATE_DIR / "state.json").exists():
        state = json.loads((STATE_DIR / "state.json").read_text(encoding="utf-8"))
        alive = cockpit_alive(state)
        if alive and not args.restart:
            raise SystemExit(f"Cockpit PID {state['pid']} is already running; use --restart "
                             "(Restart in the test panel) to replace it")
        print(f"Stopping {'running' if alive else 'stale'} session, cockpit PID {state['pid']}")
        import stop  # sibling script: stops the recorded sender and cockpit, archives the state
        stop.main()
    for request in ("stop.request", "pause.request"):
        (STATE_DIR / request).unlink(missing_ok=True)

    # can0=spi0.1 (CE1) and can1=spi0.0 (CE0) is the verified Pi mapping; can0 is bus A.
    print(remote_python(
        "from pathlib import Path; import gpiod\n"
        "names=tuple(Path(f'/sys/class/net/{n}/device').resolve().name for n in ('can0','can1'))\n"
        "assert names==('spi0.1','spi0.0'), names\n"
        f"c=gpiod.Chip('/dev/gpiochip0'); used=[p for p in {PI_PINS!r} if c.get_line_info(p).used]; c.close()\n"
        "assert not used, f'GPIO lines already claimed: {used}'\n"
        "print('Pi preflight: SPI mapping and GPIO ownership verified')\n").strip())
    links = json.loads(call(SSH + ["ip -json -details link show"], capture_output=True, check=True, timeout=10).stdout)
    setup = []
    for name in ("can0", "can1"):
        link = next(item for item in links if item["ifname"] == name)
        if "UP" in link.get("flags", []):
            bitrate = link.get("linkinfo", {}).get("info_data", {}).get("bittiming", {}).get("bitrate")
            if bitrate != 500000:
                raise SystemExit(f"{name} is up at an unexpected bitrate: {bitrate}")
        else:
            setup += [f"ip link set {name} type can bitrate 500000 restart-ms 100", f"ip link set {name} up"]

    password = None
    if setup or not args.no_fifo:
        if PASSWORD_FILE.exists():
            password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
        elif sys.stdin.isatty():
            password = getpass.getpass("Pi sudo password: ")
        else:
            password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise SystemExit("Sudo password required for CAN setup / FIFO")

    def sudo(command):
        result = call(SSH + ["sudo -S -p '' " + command], input=(password + "\n").encode(),
                      capture_output=True, timeout=15)
        with (STATE_DIR / "setup.log").open("ab") as log:
            log.write(f"$ sudo {command}\n".encode() + result.stdout + result.stderr)
        result.check_returncode()

    if setup:
        sudo("sh -c '" + "; ".join(setup) + "'")

    remote = "/home/labuser/.local/state/team4-lab3/demo-" + uuid.uuid4().hex
    sources = sorted((HERE / "pi").glob("*.py"))
    call(SSH + [f"mkdir -p {remote}/src"], check=True, timeout=10)
    call(["scp", "-q", *map(str, sources), f"wheelpi:{remote}/src/"], check=True, timeout=30)
    tests = call(SSH + [f"cd {remote}/src && python3 -m unittest discover -p 'test_*.py'"],
                 capture_output=True, timeout=60)
    (STATE_DIR / "pi-tests.log").write_bytes(tests.stdout + tests.stderr)
    if tests.returncode:
        raise SystemExit("Pi unit tests failed; see logs/lab3-can/demo/pi-tests.log")

    launched = json.loads(remote_python(f"""
import json, subprocess, sys, time
from pathlib import Path
folder = Path({remote!r})
out = (folder / 'stdout.log').open('ab', buffering=0)
p = subprocess.Popen([sys.executable, '-u', str(folder / 'src/cockpit.py'), '--log-dir', str(folder)],
                     cwd=folder / 'src', stdin=subprocess.DEVNULL, stdout=out, stderr=subprocess.STDOUT,
                     start_new_session=True)
deadline = time.monotonic() + 10
while 'N1 cockpit pid=' not in (folder / 'stdout.log').read_text(errors='replace'):
    if p.poll() is not None or time.monotonic() > deadline:
        p.kill()
        raise RuntimeError((folder / 'stdout.log').read_text(errors='replace'))
    time.sleep(0.1)
print(json.dumps({{'pid': p.pid, 'script': str(folder / 'src/cockpit.py'), 'remote': str(folder)}}))
"""))
    state = dict(launched, status="running", fifo_priority=None, synthetic=False,
                 source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (STATE_DIR / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    if not args.no_fifo:
        sudo(f"chrt -a -f -p 1 {state['pid']}")
        policies = remote_python(
            f"import os, json; from pathlib import Path; pid={state['pid']}\n"
            "tids=[int(t.name) for t in (Path('/proc')/str(pid)/'task').iterdir()]\n"
            "rows=[(t, os.sched_getscheduler(t), os.sched_getparam(t).sched_priority) for t in tids]\n"
            "assert all(s == os.SCHED_FIFO and r == 1 for _, s, r in rows), rows\nprint(json.dumps(rows))\n")
        (STATE_DIR / "verified-rt-policy.json").write_text(policies, encoding="utf-8")
        state["fifo_priority"] = 1
    password = None
    if args.synthetic:
        with (STATE_DIR / "sender.log").open("ab", buffering=0) as log:
            sender = subprocess.Popen([sys.executable, "-u", str(HERE / "synthetic_sender.py")],
                                      stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                      creationflags=FLAGS)
        state.update(synthetic=True, sender_pid=sender.pid, sender_create_time=psutil.Process(sender.pid).create_time())
        time.sleep(1)
        if sender.poll() is not None:
            raise SystemExit((STATE_DIR / "sender.log").read_text())
    (STATE_DIR / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
