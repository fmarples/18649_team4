"""Lab 3 demo test panel, attached to the course wheel window.

Opened by `windows/start_wheel_proxy.py --lab3`, or by double-clicking
lab3_demo/test_panel.pyw. Everything a test needs from the Pi side runs from
here over the passwordless `wheelpi` SSH alias, in worker threads:

- start/stop the cockpit session through lab3_demo/start.py and stop.py; the
  sudo password comes from the gitignored lab3_demo/pi_sudo_password.txt, or
  is asked on every start and passed on stdin only when that file is absent
- live N1 state, degraded buses and FAULT/state events streamed from the
  session's stdout.log and events.csv
- bad CTRL (throttle 101 / corrupted CRC), N1 test press and clear-all, sent as
  signals to the recorded cockpit PID
- a 3 s candump of both buses with per-ID rates and recent sequence numbers
- pausing the bench sender, which stands in for "proxy stopped"
"""
import csv
import hashlib
import json
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

from PyQt5 import QtCore, QtGui, QtWidgets

HERE = Path(__file__).resolve().parent
STATE_DIR = HERE.parent / "logs/lab3-can/demo"
FLAGS = getattr(subprocess, "CREATE_NO_WINDOW", 0)
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "wheelpi"]
NAMES = {"010": "CTRL", "020": "FAULT", "100": "HB_N1", "101": "HB_N2", "102": "HB_N3",
         "200": "BLINK", "300": "FORCE"}
BLINK_MODES = ("off", "left", "right", "hazard")
CAPTURE_S = 3
# Remote one-shot: signal the cockpit only if the PID still runs the recorded script.
SIGNAL_CODE = """import os, signal, sys
pid, script, name = {pid!r}, {script!r}, {name!r}
if script.encode() not in open(f'/proc/{{pid}}/cmdline', 'rb').read().split(b'\\0'):
    sys.exit('recorded PID is not the cockpit')
os.kill(pid, {{'range': signal.SIGUSR1, 'crc': signal.SIGUSR2,
              'latch': signal.SIGRTMIN, 'clear': signal.SIGRTMIN + 1}}[name])
"""


def run(args, timeout, stdin_text=None):
    """subprocess.run without a console window; ssh never inherits stdin."""
    return subprocess.run(args, input=stdin_text, stdin=None if stdin_text else subprocess.DEVNULL,
                          capture_output=True, text=True, encoding="utf-8", errors="replace",
                          timeout=timeout, creationflags=FLAGS)


def local_cockpit_hash():
    return hashlib.sha256((HERE / "pi" / "cockpit.py").read_bytes()).hexdigest()


def session():
    path = STATE_DIR / "state.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def parse_candump(text):
    """Return {id: {iface: count}} and {id: recent sequence nibbles on the first bus seen}."""
    counts, seqs = defaultdict(Counter), defaultdict(list)
    for line in text.splitlines():
        parts = line.split()
        if len(parts) < 5 or not parts[3].startswith("["):
            continue
        iface, frame_id, data = parts[1], parts[2].upper(), parts[4:]
        counts[frame_id][iface] += 1
        if iface == "can0" and data:
            seqs[frame_id].append(int(data[0], 16) & 0x0F)
    return counts, seqs


class Lab3Panel(QtCore.QObject):
    """Adds a "Lab 3 tests" button to the wheel window and owns the test dialog."""
    done = QtCore.pyqtSignal(str, bool, object)  # action, ok, payload; from worker threads
    streamed = QtCore.pyqtSignal(str)

    def __init__(self, window, log):
        super().__init__(window)
        self.window, self.log = window, log
        self.state = None
        self.stream = None
        self.last_status = 0.0
        self.busy = set()
        self.done.connect(self._finished)
        self.streamed.connect(self._stream_line)
        button = QtWidgets.QPushButton("Lab 3 tests")
        button.clicked.connect(self.show)
        window.centralWidget().layout().addWidget(button)
        self.dialog = self._build()
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._refresh)
        self.timer.start(500)
        self._refresh()
        self.show()

    # ---- layout ---------------------------------------------------------
    def _build(self):
        d = QtWidgets.QDialog(self.window)
        d.setWindowTitle("Lab 3 tests")
        d.setMinimumWidth(560)
        d.resize(620, 760)
        outer = QtWidgets.QVBoxLayout(d)

        box = QtWidgets.QGroupBox("Cockpit session (Pi)")
        row = QtWidgets.QHBoxLayout(box)
        self.session_label = QtWidgets.QLabel()
        self.bench = QtWidgets.QCheckBox("Bench input")
        self.bench.setToolTip("No wheel: start a laptop sender that stands in for the wheel proxy")
        self.start_button = QtWidgets.QPushButton("Start")
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.start_button.clicked.connect(self.start_session)
        self.stop_button.clicked.connect(lambda: self._work("stop", self._stop))
        row.addWidget(self.session_label, 1)
        row.addWidget(self.bench)
        row.addWidget(self.start_button)
        row.addWidget(self.stop_button)
        outer.addWidget(box)

        box = QtWidgets.QGroupBox("N1 live state")
        grid = QtWidgets.QGridLayout(box)
        self.lamps = {}
        for column, name in enumerate(("ERR", "DEG_A", "DEG_B", "N2", "N3", "LATCH")):
            lamp = QtWidgets.QLabel(name)
            lamp.setAlignment(QtCore.Qt.AlignCenter)
            lamp.setMinimumWidth(64)
            grid.addWidget(lamp, 0, column)
            self.lamps[name] = lamp
        self.inputs = QtWidgets.QLabel()
        grid.addWidget(self.inputs, 1, 0, 1, 6)
        outer.addWidget(box)

        box = QtWidgets.QGroupBox("Tests")
        grid = QtWidgets.QGridLayout(box)
        self.test_buttons = []
        tests = (("Bad CTRL: throttle 101", "range", "Checkoff 10: next CTRL out of range; N2/N3 latch and send FAULT"),
                 ("Bad CTRL: CRC", "crc", "Checkoff 10: next CTRL has a corrupted CRC"),
                 ("N1 test press", "latch", "Checkoff 9: same as one wheel A press"),
                 ("Clear all faults", "clear", "Checkoff 9: same as a double press; releases every zone"))
        for index, (label, name, tip) in enumerate(tests):
            button = QtWidgets.QPushButton(label)
            button.setToolTip(tip)
            button.clicked.connect(lambda _, n=name: self._work("signal " + n, lambda: self._signal(n)))
            grid.addWidget(button, index // 2, index % 2)
            self.test_buttons.append(button)
        self.pause = QtWidgets.QCheckBox("Pause bench input (proxy stopped)")
        self.pause.setToolTip("Checkoff 1: N1 sees no UDP, so every zone enters the error state")
        self.pause.toggled.connect(self._pause)
        grid.addWidget(self.pause, 2, 0)
        self.capture_button = QtWidgets.QPushButton(f"Bus traffic ({CAPTURE_S} s candump)")
        self.capture_button.setToolTip("Checkoff 2: every catalog ID on both buses at its rate")
        self.capture_button.clicked.connect(lambda: self._work("capture", self._capture))
        grid.addWidget(self.capture_button, 2, 1)
        outer.addWidget(box)

        self.table = QtWidgets.QTableWidget(len(NAMES), 4)
        self.table.setHorizontalHeaderLabels(["ID", "can0 (A) /s", "can1 (B) /s", "Recent seq, can0"])
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        for r, (frame_id, name) in enumerate(NAMES.items()):
            self.table.setItem(r, 0, QtWidgets.QTableWidgetItem(f"{frame_id} {name}"))
        self.table.setFixedHeight(self.table.verticalHeader().length() + self.table.horizontalHeader().height() + 4)
        outer.addWidget(self.table)

        self.events = QtWidgets.QPlainTextEdit()
        self.events.setReadOnly(True)
        self.events.setMaximumBlockCount(500)
        self.events.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.events.setMinimumHeight(160)
        self.events.setPlaceholderText("Cockpit events: state, degraded buses, FAULT, injections")
        outer.addWidget(self.events, 1)
        return d

    def show(self):
        self.dialog.show()
        self.dialog.raise_()
        self.dialog.activateWindow()

    def note(self, text, error=False):
        self.events.appendPlainText(time.strftime("%H:%M:%S ") + text)
        self.log.record("Lab 3: " + text, "Errors" if error else "Diagnostics")

    # ---- actions ----------------------------------------------------------
    def _work(self, action, fn):
        """Run fn in a thread; fn returns (ok, payload). One instance per action."""
        if action in self.busy:
            return
        self.busy.add(action)
        self._refresh()

        def worker():
            try:
                ok, payload = fn()
            except Exception as exc:  # timeouts, ssh failures: reported, never fatal
                ok, payload = False, f"{type(exc).__name__}: {exc}"
            self.done.emit(action, ok, payload)
        threading.Thread(target=worker, name="lab3-" + action, daemon=True).start()

    def start_session(self):
        """Start, or Restart a running session (deploying the current pi/ code)."""
        restart = self.state is not None
        stdin_text = None  # start.py reads the local password file itself
        if not (HERE / "pi_sudo_password.txt").exists():
            password, ok = QtWidgets.QInputDialog.getText(self.dialog, "Restart cockpit" if restart else "Start cockpit",
                                                          "Pi sudo password:", QtWidgets.QLineEdit.Password)
            if not ok or not password:
                return
            stdin_text = password + "\n"
        bench = self.state.get("synthetic", False) if restart else self.bench.isChecked()
        args = ([sys.executable, str(HERE / "start.py")] + (["--restart"] if restart else [])
                + (["--synthetic"] if bench else []))
        self.note(("Restarting" if restart else "Starting") + " cockpit"
                  + (" with bench input" if bench else " for the wheel proxy"))
        self._work("start", lambda: self._script(args, stdin_text))

    def _script(self, args, stdin_text=None):
        result = run(args, 180, stdin_text)
        return result.returncode == 0, (result.stdout + result.stderr).strip()

    def _stop(self):
        return self._script([sys.executable, str(HERE / "stop.py")])

    def _signal(self, name):
        state = session()
        if state is None:
            return False, "no cockpit session"
        code = SIGNAL_CODE.format(pid=state["pid"], script=state["script"], name=name)
        result = run(SSH + ["python3 -"], 15, code)
        return result.returncode == 0, (result.stdout + result.stderr).strip() or "sent"

    def _capture(self):
        result = run(SSH + [f"timeout {CAPTURE_S} candump -t z can0 can1"], CAPTURE_S + 15)
        if result.returncode not in (0, 124):  # 124: timeout ended candump as intended
            return False, result.stderr.strip()
        return True, parse_candump(result.stdout)

    def _pause(self, paused):
        request = STATE_DIR / "pause.request"
        if paused:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            request.touch()
        else:
            request.unlink(missing_ok=True)
        self.note("Bench input paused: N1 stops sending CTRL updates" if paused else "Bench input resumed")

    def _finished(self, action, ok, payload):
        self.busy.discard(action)
        if action == "capture" and ok:
            self._show_capture(*payload)
        elif action.startswith("signal"):
            self.note(f"{action.split()[1]}: {payload}", error=not ok)
        else:
            self.note(f"{action} {'done' if ok else 'FAILED'}: {payload}"[:2000], error=not ok)
        self._refresh()

    def _show_capture(self, counts, seqs):
        missing = []
        for r, frame_id in enumerate(NAMES):
            for c, iface in ((1, "can0"), (2, "can1")):
                count = counts[frame_id][iface]
                self.table.setItem(r, c, QtWidgets.QTableWidgetItem(f"{count / CAPTURE_S:.1f}"))
                if count == 0 and frame_id != "020":
                    missing.append(f"{NAMES[frame_id]} on {iface}")
            recent = " ".join(f"{s:x}" for s in seqs[frame_id][-12:])
            self.table.setItem(r, 3, QtWidgets.QTableWidgetItem(recent))
        self.note("Bus traffic: " + ("all periodic IDs on both buses" if not missing
                                     else "missing " + ", ".join(missing)), error=bool(missing))

    # ---- live state --------------------------------------------------------
    def _refresh(self):
        state = session()
        if (state or {}).get("pid") != (self.state or {}).get("pid"):
            self._restart_stream(state)
        self.state = state
        running = state is not None
        # An older cockpit lacks the test signal handlers; SIGRTMIN would terminate it.
        current = running and state.get("source_sha256", {}).get("cockpit.py") == local_cockpit_hash()
        if not running and self.pause.isChecked():
            self.pause.blockSignals(True)  # start.py clears pause.request for the next session
            self.pause.setChecked(False)
            self.pause.blockSignals(False)
        if running and not current:
            self.session_label.setText(f"PID {state['pid']} runs older code: press Restart")
        else:
            self.session_label.setText(f"Running, PID {state['pid']}" + (", bench" if state.get("synthetic") else ", wheel")
                                       if running else "Stopped")
        self.start_button.setText("Restart" if running else "Start")
        self.start_button.setEnabled("start" not in self.busy and "stop" not in self.busy)
        self.stop_button.setEnabled(running and "stop" not in self.busy)
        self.bench.setEnabled(not running)
        self.pause.setEnabled(running and bool(state.get("synthetic")))
        for button in self.test_buttons:
            button.setEnabled(current)
        self.capture_button.setEnabled("capture" not in self.busy)
        if not running or time.monotonic() - self.last_status > 3:
            for lamp in self.lamps.values():
                self._lamp(lamp, None)
            self.inputs.setText("No live status" if running else "Cockpit not running")

    def _restart_stream(self, state):
        if self.stream is not None:
            self.stream.kill()
            self.stream = None
        if state is None:
            return
        remote = state["remote"]
        command = (f"tail -q -n 200 -F {remote}/stdout.log {remote}/events.csv "
                   "| grep --line-buffered -v -e UDP_TO_CMD_TX -e '^mono_s'")
        self.stream = subprocess.Popen(SSH + [command], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT, text=True, encoding="utf-8",
                                       errors="replace", creationflags=FLAGS)
        stream = self.stream

        def reader():
            for line in stream.stdout:
                self.streamed.emit(line.rstrip())
        threading.Thread(target=reader, name="lab3-stream", daemon=True).start()

    def _stream_line(self, line):
        if line.startswith("STATUS "):
            try:
                self._show_status(json.loads(line[7:]))
            except ValueError:
                pass
            return
        parts = next(csv.reader([line]), [])
        if len(parts) == 4 and parts[0].replace(".", "").isdigit():  # events.csv row
            line = " ".join(parts[1:]).rstrip()
        if line:
            self.events.appendPlainText(time.strftime("%H:%M:%S ") + line)

    def _lamp(self, lamp, on, alarm=True):
        if on is None:
            style = "background:#d0d0d0; color:#505050;"
        elif on:
            style = "background:#c62828; color:white;" if alarm else "background:#2e7d32; color:white;"
        else:
            style = "background:#2e7d32; color:white;" if alarm else "background:#c62828; color:white;"
        lamp.setStyleSheet(style + " padding:4px; border-radius:3px; font-weight:bold;")

    def _show_status(self, s):
        self.last_status = time.monotonic()
        self._lamp(self.lamps["ERR"], s["error"])
        self._lamp(self.lamps["DEG_A"], s["degraded"][0])
        self._lamp(self.lamps["DEG_B"], s["degraded"][1])
        self._lamp(self.lamps["N2"], s["alive"].get("N2", False), alarm=False)
        self._lamp(self.lamps["N3"], s["alive"].get("N3", False), alarm=False)
        self._lamp(self.lamps["LATCH"], s["latched"])
        mode = BLINK_MODES[s["blink"]] if 0 <= s["blink"] < len(BLINK_MODES) else s["blink"]
        self.inputs.setText(f"steer {s['steer']}   throttle {s['throttle']} %   brake {s['brake']} %   "
                            f"blink {mode}   FORCE {s['force']}")

    def close(self):
        self.timer.stop()
        if self.stream is not None:
            self.stream.kill()
