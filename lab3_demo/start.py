"""Deploy and start the N1 cockpit on the Pi (SSH alias `wheelpi`).

    python lab3_demo/start.py [--synthetic] [--no-fifo] [--restart]

Copies lab3_demo/pi to a fresh remote folder, runs its unit tests there, then
installs and enables the system service team4-lab3-cockpit.service pointing at
that folder. On every start, including each Pi boot, the service brings
can0/can1 up at 500 kbit/s with restart-ms 50 and runs cockpit.py as labuser
under SCHED_FIFO 1, inherited by all its threads. The service starts again
after a reboot until lab3_demo/stop.py disables it.
Sudo comes from the gitignored lab3_demo/pi_sudo_password.txt when it exists,
otherwise once from the terminal (or one stdin line). --synthetic also starts a
laptop wheel-format UDP sender for bench checks without the course proxy; that
sender does not survive a laptop restart.
Ownership state: logs/lab3-can/demo/state.json. A recorded session whose
service has stopped is cleaned up automatically; a live one is replaced only
with --restart (the test panel's Restart button).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import time
import uuid
from pathlib import Path

import psutil

from pi_ssh import FLAGS, HERE, SSH, STATE_DIR, UNIT, call, remote_python, sudo, sudo_password

PI_PINS = (5, 6, 12, 17, 22, 23, 27)
# R4.8: bus-off recovery within 100 ms of the bus being restored. The kernel
# restarts a bus-off controller after restart-ms; 50 ms leaves margin for the
# MCP2515 to resynchronize after the restart.
RESTART_MS = 50


# The Pi recreates can0/can1 down at boot, so the service configures them before each start.
# systemd expands $$ to $ and runs ExecStartPre=+ as root; the cockpit itself runs as labuser.
def unit_text(remote, fifo):
    links = ("for n in can0 can1; do ip link set $$n down && ip link set $$n type can bitrate 500000 "
             f"restart-ms {RESTART_MS} && ip link set $$n up || exit 1; done")
    scheduling = "CPUSchedulingPolicy=fifo\nCPUSchedulingPriority=1\n" if fifo else ""
    return ("[Unit]\nDescription=Team 4 Lab 3 N1 cockpit (installed by lab3_demo/start.py)\n"
            "Requires=sys-subsystem-net-devices-can0.device sys-subsystem-net-devices-can1.device\n"
            "After=sys-subsystem-net-devices-can0.device sys-subsystem-net-devices-can1.device\n\n"
            f"[Service]\nUser=labuser\nWorkingDirectory={remote}/src\n"
            f"ExecStartPre=+/bin/sh -c '{links}'\n"
            f"ExecStart=/usr/bin/python3 -u {remote}/src/cockpit.py --log-dir {remote}\n"
            f"StandardOutput=append:{remote}/stdout.log\nStandardError=append:{remote}/stdout.log\n"
            f"{scheduling}\n[Install]\nWantedBy=multi-user.target\n")


def service_active():
    result = call(SSH + [f"systemctl is-active {UNIT}"], capture_output=True, timeout=15)
    return result.stdout.decode().strip() == "active"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--synthetic", action="store_true", help="also start the laptop synthetic UDP sender")
    ap.add_argument("--no-fifo", action="store_true", help="run the cockpit without SCHED_FIFO")
    ap.add_argument("--restart", action="store_true", help="stop a running recorded session first")
    args = ap.parse_args()
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    password = sudo_password()
    if (STATE_DIR / "state.json").exists():
        alive = service_active()
        if alive and not args.restart:
            raise SystemExit(f"{UNIT} is already running; use --restart "
                             "(Restart in the test panel) to replace it")
        print(f"Stopping {'running' if alive else 'stopped'} session")
        import stop  # sibling script: stops the recorded sender, disables the service, archives the state
        stop.main(password)
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

    remote = "/home/labuser/.local/state/team4-lab3/demo-" + uuid.uuid4().hex
    sources = sorted((HERE / "pi").glob("*.py"))
    call(SSH + [f"mkdir -p {remote}/src"], check=True, timeout=10)
    call(["scp", "-q", *map(str, sources), f"wheelpi:{remote}/src/"], check=True, timeout=30)
    tests = call(SSH + [f"cd {remote}/src && python3 -m unittest discover -p 'test_*.py'"],
                 capture_output=True, timeout=60)
    (STATE_DIR / "pi-tests.log").write_bytes(tests.stdout + tests.stderr)
    if tests.returncode:
        raise SystemExit("Pi unit tests failed; see logs/lab3-can/demo/pi-tests.log")

    (STATE_DIR / UNIT).write_text(unit_text(remote, not args.no_fifo), encoding="utf-8", newline="\n")
    call(["scp", "-q", str(STATE_DIR / UNIT), f"wheelpi:{remote}/{UNIT}"], check=True, timeout=30)
    sudo(password, f"sh -c 'install -m 644 {remote}/{UNIT} /etc/systemd/system/{UNIT} && "
                   f"systemctl daemon-reload && systemctl enable {UNIT} && systemctl restart {UNIT}'")
    state = dict(unit=UNIT, script=f"{remote}/src/cockpit.py", remote=remote, status="running",
                 fifo_priority=None, synthetic=False,
                 source_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    (STATE_DIR / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    pid = int(remote_python(f"""
import subprocess, time
from pathlib import Path
log = Path({remote!r}) / 'stdout.log'
deadline = time.monotonic() + 15
while True:
    show = subprocess.run(['systemctl', 'show', '-p', 'MainPID', '-p', 'ActiveState', '--value', {UNIT!r}],
                          capture_output=True, text=True).stdout.split()
    pid, active = int(show[0]), show[1]
    if active == 'active' and log.exists() and f'N1 cockpit pid={{pid}} ' in log.read_text(errors='replace'):
        print(pid)
        break
    if active == 'failed' or time.monotonic() > deadline:
        journal = subprocess.run(['journalctl', '-u', {UNIT!r}, '-n', '30', '--no-pager'],
                                 capture_output=True, text=True).stdout
        raise RuntimeError(journal + (log.read_text(errors='replace') if log.exists() else ''))
    time.sleep(0.2)
""", timeout=30))
    if not args.no_fifo:
        policies = remote_python(
            f"import os, json; from pathlib import Path; pid={pid}\n"
            "tids=[int(t.name) for t in (Path('/proc')/str(pid)/'task').iterdir()]\n"
            "rows=[(t, os.sched_getscheduler(t), os.sched_getparam(t).sched_priority) for t in tids]\n"
            "assert all(s == os.SCHED_FIFO and r == 1 for _, s, r in rows), rows\nprint(json.dumps(rows))\n")
        (STATE_DIR / "verified-rt-policy.json").write_text(policies, encoding="utf-8")
        state["fifo_priority"] = 1
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
