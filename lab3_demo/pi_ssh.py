"""SSH and sudo helpers shared by start.py and stop.py (SSH alias `wheelpi`)."""
import getpass
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE.parent / "logs/lab3-can/demo"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "wheelpi"]
# Boot-enabled system service: start.py installs and enables it, stop.py disables it.
UNIT = "team4-lab3-cockpit.service"
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


def sudo_password():
    """The local password file, else the terminal, else one stdin line (the test panel)."""
    if PASSWORD_FILE.exists():
        password = PASSWORD_FILE.read_text(encoding="utf-8").strip()
    elif sys.stdin and sys.stdin.isatty():
        password = getpass.getpass("Pi sudo password: ")
    else:
        password = sys.stdin.readline().rstrip("\r\n") if sys.stdin else ""
    if not password:
        raise SystemExit("Pi sudo password required")
    return password


def sudo(password, command, timeout=30):
    """Run one root command on the Pi; output is appended to setup.log."""
    result = call(SSH + ["sudo -S -p '' " + command], input=(password + "\n").encode(),
                  capture_output=True, timeout=timeout)
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with (STATE_DIR / "setup.log").open("ab") as log:
        log.write(f"$ sudo {command}\n".encode() + result.stdout + result.stderr)
    result.check_returncode()
    return result.stdout.decode()
