"""Read-only Qt telemetry windows attached by the team wheel-proxy launcher."""
from collections import deque
from datetime import datetime, timezone
import faulthandler
import math
import json
import os
from pathlib import Path
import socket
import sys
import threading
import time
import traceback

from PyQt5 import QtCore, QtGui, QtWidgets
from pi.part2_protocol import CURRENT_REPORT_MAX_MA, STATES
from windows.current_telemetry import TelemetryHistory, WINDOW_SECONDS, CURRENT_CHANNELS
from windows.telemetry_events import CATEGORIES, LogEvent, TelemetryEvents
from pi.background_io import BackgroundIO

COLORS = ('#005a9e', '#946200', '#8e327b')
NAMES = ('Left motor', 'Right motor', 'Servo')


# Preserve ordinary proxy output while also recording complete lines to file and GUI.
class LogStream:
    def __init__(self, original, log, category='Diagnostics'):
        self.original, self.log, self.pending = original, log, ''
        self.category = category
        self.encoding = getattr(original, 'encoding', 'utf-8')
        self.lock = threading.RLock()

    def write(self, text):
        with self.lock:
            self.pending += text
            while '\n' in self.pending:
                line, self.pending = self.pending.split('\n', 1)
                self.emit_line(line.rstrip('\r'))
        return len(text)

    def emit_line(self, line):
        # The course proxy prints this on every empty force-feedback read.
        if self.category != 'Errors' and line.strip() == 'No data':
            return
        if self.original is not None:
            self.log.io.submit(('echo', (self.original, line + '\n')))
        category = self.category
        if line.startswith(('connected to a steering wheel', 'initialized successfully', 'disconnecting')):
            category = 'Connection'
        if line.strip():
            self.log.record(line, category)

    def flush(self):
        if self.pending:
            self.emit_line(self.pending)
            self.pending = ''
        if self.original is not None:
            self.log.io.submit(('flush', self.original))

    def isatty(self):
        return False


# The session owns persistent logs and Python/native crash reports, independent of view state.
class SessionLog(QtCore.QObject):
    line = QtCore.pyqtSignal(object)

    def __init__(self, directory):
        super().__init__()
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        stem = datetime.now().strftime('%Y%m%d-%H%M%S-%f') + '-' + str(os.getpid())
        self.path = directory / (stem + '.log')
        self.crash_path = directory / (stem + '.crash.txt')
        self.file = self.path.open('x', encoding='utf-8')
        self.crash = self.crash_path.open('x', encoding='utf-8')
        self.frames_path = directory / (stem + '.frames.jsonl')
        self.frames = self.frames_path.open('x', encoding='utf-8')
        self.lines = deque(maxlen=3000)
        self.lock = threading.RLock()
        self.io = BackgroundIO(self._write, self._finish)
        self.original = sys.stdout, sys.stderr, sys.excepthook
        self.stdout = LogStream(sys.stdout, self)
        self.stderr = LogStream(sys.stderr, self, 'Errors')
        sys.stdout, sys.stderr, sys.excepthook = self.stdout, self.stderr, self.exception
        faulthandler.enable(file=self.crash, all_threads=True)

    def record(self, text, category='Diagnostics'):
        if category not in CATEGORIES:
            raise ValueError('Unknown log category: ' + category)
        line = datetime.now(timezone.utc).isoformat(timespec='milliseconds') + f'  {category}  ' + text
        event = LogEvent(category, line)
        with self.lock:
            self.lines.append(event)
        self.io.submit(('event', line))
        self.line.emit(event)

    def capture_frame(self, data, status):
        row = {'received': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
               'hex': data.hex(), 'status': status}
        self.io.submit(('frame', row))

    def _write(self, item):
        kind, value = item
        if kind == 'echo':
            value[0].write(value[1])
        elif kind == 'flush':
            value.flush()
        elif kind == 'event':
            self.file.write(value + '\n')
            self.file.flush()
        elif kind == 'frame':
            self.frames.write(json.dumps(value) + '\n')
            self.frames.flush()

    def _finish(self):
        self.file.close()
        self.frames.close()

    def exception(self, kind, error, tb):
        traceback.print_exception(kind, error, tb, file=self.crash)
        self.crash.flush()
        self.record('ERROR ' + ''.join(traceback.format_exception(kind, error, tb)).rstrip(), 'Errors')
        self.original[2](kind, error, tb)
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.exit(1)

    def close(self):
        for stream in (self.stdout, self.stderr):
            if stream.pending:
                stream.emit_line(stream.pending)
                stream.pending = ''
        sys.stdout, sys.stderr, sys.excepthook = self.original
        faulthandler.disable()
        self.io.close()
        self.crash.close()


# A bounded view over the persistent session log. Closing the dialog only hides it.
class RawLogWindow(QtWidgets.QDialog):
    def __init__(self, parent, log):
        super().__init__(parent)
        self.setWindowTitle('Raw log')
        self.resize(1000, 440)
        self.lines = deque(log.lines, maxlen=3000)
        self.paused = False
        self.frozen = None
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        self.pause = QtWidgets.QPushButton('Pause view')
        self.pause.setCheckable(True)
        self.pause.toggled.connect(self.set_paused)
        clear = QtWidgets.QPushButton('Clear view')
        clear.clicked.connect(self.clear_view)
        toolbar.addWidget(self.pause)
        toolbar.addWidget(clear)
        toolbar.addStretch()
        layout.addLayout(toolbar)
        filters = QtWidgets.QHBoxLayout()
        filters.addWidget(QtWidgets.QLabel('Show:'))
        self.filters = {}
        for category in CATEGORIES:
            checkbox = QtWidgets.QCheckBox(category)
            checkbox.setChecked(category != 'Diagnostics')
            checkbox.toggled.connect(self.refresh_view)
            self.filters[category] = checkbox
            filters.addWidget(checkbox)
        filters.addStretch()
        layout.addLayout(filters)
        self.text = QtWidgets.QPlainTextEdit()
        self.text.setReadOnly(True)
        self.text.setLineWrapMode(QtWidgets.QPlainTextEdit.NoWrap)
        self.text.setMaximumBlockCount(3000)
        self.text.setFont(QtGui.QFontDatabase.systemFont(QtGui.QFontDatabase.FixedFont))
        self.refresh_view()
        layout.addWidget(self.text)
        path = QtWidgets.QLabel('Events: ' + str(log.path) + '\nSamples: ' + str(log.frames_path))
        path.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        path.setWordWrap(True)
        layout.addWidget(path)
        log.line.connect(self.append)

    def append(self, event):
        self.lines.append(event)
        if not self.paused and self.filters[event.category].isChecked():
            scroll = self.text.verticalScrollBar()
            follow = scroll.value() == scroll.maximum()
            self.text.appendPlainText(event.text)
            if follow:
                scroll.setValue(scroll.maximum())

    def refresh_view(self):
        events = self.frozen if self.paused else self.lines
        self.text.setPlainText('\n'.join(event.text for event in events
                                        if self.filters[event.category].isChecked()))
        self.text.verticalScrollBar().setValue(self.text.verticalScrollBar().maximum())

    def set_paused(self, paused):
        self.frozen = tuple(self.lines) if paused else None
        self.paused = paused
        self.pause.setText('Resume view' if paused else 'Pause view')
        self.refresh_view()

    def clear_view(self):
        self.lines.clear()
        if self.paused:
            self.frozen = ()
        self.text.clear()


# Paint signed currents with explicit breaks at missing/invalid samples, never invented zeros.
class CurrentPlot(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.points, self.now = (), 0.0
        self.setMinimumSize(520, 260)
        self.setAccessibleName('Current in amps over the last thirty seconds')

    def paintEvent(self, event):
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor('white'))
        bounds = QtCore.QRectF(66, 24, self.width() - 86, self.height() - 62)
        points = [p for p in self.points if p.received_s >= self.now - WINDOW_SECONDS]
        values = [a for p in points for a in p.amps if a is not None]
        low = math.floor(min([-0.25, *values]) * 2) / 2
        high = math.ceil(max([1.0, *values]) * 2) / 2
        def y(value):
            return bounds.bottom() - (value - low) / (high - low) * bounds.height()
        def x(stamp):
            return bounds.right() - (self.now - stamp) / WINDOW_SECONDS * bounds.width()
        painter.setFont(QtGui.QFont('Segoe UI', 9))
        for i in range(5):
            value = low + (high - low) * i / 4
            pos = y(value)
            painter.setPen(QtGui.QColor('#dddddd'))
            painter.drawLine(QtCore.QPointF(bounds.left(), pos), QtCore.QPointF(bounds.right(), pos))
            painter.setPen(QtGui.QColor('#303030'))
            painter.drawText(QtCore.QRectF(0, pos - 9, 58, 18), QtCore.Qt.AlignRight, f'{value:.2f}')
        painter.drawText(12, 16, 'Amps')
        for age in (30, 20, 10, 0):
            pos = x(self.now - age)
            painter.setPen(QtGui.QColor('#dddddd'))
            painter.drawLine(QtCore.QPointF(pos, bounds.top()), QtCore.QPointF(pos, bounds.bottom()))
            painter.setPen(QtGui.QColor('#303030'))
            label = f'-{age} s' if age else 'Now'
            painter.drawText(QtCore.QRectF(pos - 24, bounds.bottom() + 8, 48, 20), QtCore.Qt.AlignCenter, label)
        painter.save()
        painter.setClipRect(bounds.adjusted(-2, -2, 2, 2))
        ceiling = CURRENT_REPORT_MAX_MA / 1000
        if low <= ceiling <= high:
            painter.setPen(QtGui.QPen(QtGui.QColor('#666666'), 1, QtCore.Qt.DashLine))
            painter.drawLine(QtCore.QPointF(bounds.left(), y(ceiling)), QtCore.QPointF(bounds.right(), y(ceiling)))
        for channel, color in enumerate(COLORS):
            path = QtGui.QPainterPath()
            connected = False
            painter.setPen(QtGui.QPen(QtGui.QColor(color), 2))
            for point in points:
                value = point.amps[channel]
                if value is None:
                    connected = False
                    continue
                pos = QtCore.QPointF(x(point.received_s), y(value))
                if connected and not point.gap:
                    path.lineTo(pos)
                else:
                    path.moveTo(pos)
                    painter.drawEllipse(pos, 2, 2)
                connected = True
            painter.drawPath(path)
        painter.restore()
        if not values:
            painter.setPen(QtGui.QColor('#555555'))
            painter.drawText(bounds, QtCore.Qt.AlignCenter, 'No valid current samples in this time window')


# Pausing freezes a copy of the view; acquisition and file logging continue independently.
class CurrentChartWindow(QtWidgets.QDialog):
    def __init__(self, parent, history):
        super().__init__(parent)
        self.history = history
        self.frozen = None
        self.setWindowTitle('Current chart')
        self.resize(800, 440)
        layout = QtWidgets.QVBoxLayout(self)
        toolbar = QtWidgets.QHBoxLayout()
        self.pause = QtWidgets.QPushButton('Pause view')
        self.pause.setCheckable(True)
        self.pause.toggled.connect(self.set_paused)
        toolbar.addWidget(self.pause)
        toolbar.addWidget(QtWidgets.QLabel('Last 30 seconds; laptop receive time'))
        toolbar.addStretch()
        layout.addLayout(toolbar)
        legends = QtWidgets.QHBoxLayout()
        self.labels = {}
        for i, (name, color) in enumerate(zip(NAMES, COLORS)):
            if CURRENT_CHANNELS[i] not in history.connected_channels:
                continue
            label = QtWidgets.QLabel(name + ': unavailable')
            label.setStyleSheet(f'color: {color}; font-weight: 600')
            legends.addWidget(label)
            self.labels[i] = label
        layout.addLayout(legends)
        self.plot = CurrentPlot()
        layout.addWidget(self.plot)
        self.state = QtWidgets.QLabel()
        layout.addWidget(self.state)
        note = QtWidgets.QLabel('Gaps mean missing or invalid data. +4.320 A is the reporting ceiling.\n'
                               'Nominal sensor calibration; unexpected negative readings are not hidden.')
        note.setWordWrap(True)
        layout.addWidget(note)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(100)
        self.refresh()

    def set_paused(self, paused):
        self.frozen = (tuple(self.history.samples), time.monotonic()) if paused else None
        self.pause.setText('Resume view' if paused else 'Pause view')
        self.refresh()

    def refresh(self):
        points, now = self.frozen or (tuple(self.history.samples), time.monotonic())
        stale = not points or now - points[-1].received_s >= 0.5
        for i, label in self.labels.items():
            value = points[-1].amps[i] if points and not stale else None
            text = 'unavailable' if value is None else f'{value:.3f} A'
            if value == CURRENT_REPORT_MAX_MA / 1000:
                text += ' [ceiling]'
            label.setText(NAMES[i] + ': ' + text)
        self.state.setText('View paused; recording continues' if self.frozen else
                           'Waiting for fresh telemetry' if stale else 'Receiving telemetry')
        self.plot.points, self.plot.now = points, now
        self.plot.update()


# Add the two chosen buttons without replacing the course proxy or touching its force socket.
class TelemetryWindows(QtCore.QObject):
    def __init__(self, window, pi_address, local_address, port, log,
                 connected_channels=('left', 'servo')):
        super().__init__(window)
        self.window, self.pi_address, self.log = window, pi_address, log
        self.history = TelemetryHistory(connected_channels)
        self.events = TelemetryEvents(self.history.connected_channels)
        self.raw_window = self.chart_window = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind((local_address, port))
            self.socket.setblocking(False)
        except BaseException:
            self.socket.close()
            raise
        self.address = self.socket.getsockname()
        layout = window.centralWidget().layout()
        row = QtWidgets.QHBoxLayout()
        self.log_button = QtWidgets.QPushButton('Raw log')
        self.chart_button = QtWidgets.QPushButton('Current chart')
        self.log_button.clicked.connect(self.show_log)
        self.chart_button.clicked.connect(self.show_chart)
        row.addWidget(self.log_button)
        row.addWidget(self.chart_button)
        layout.addLayout(row)
        self.status = QtWidgets.QLabel(f'Waiting for Pi telemetry\nUDP {self.address[1]}')
        self.status.setWordWrap(True)
        self.status.setMinimumHeight(self.status.fontMetrics().height() * 2 + 4)
        window.setMinimumWidth(max(window.minimumWidth(), 300))
        layout.addWidget(self.status)
        self.rejected = 0
        self.rejecting = False
        self.closed = False
        window.installEventFilter(self)
        self.receiver = QtCore.QSocketNotifier(self.socket.fileno(), QtCore.QSocketNotifier.Read, self)
        self.receiver.activated.connect(self.receive_ready)
        # Only freshness/display age needs a clock. UDP reception and log delivery are event-driven.
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.refresh_status)
        self.timer.start(100)
        log.record(f'Telemetry listening on {self.address[0]}:{self.address[1]}; expected Pi {pi_address}',
                   'Connection')
        log.record('Current ADC calibration is nominal. Telemetry never sends wheel force or actuator commands.')
        log.record('Crash reports: ' + str(log.crash_path))
        for i, pin in enumerate(('A0', 'A1', 'A3')):
            if CURRENT_CHANNELS[i] not in self.history.connected_channels:
                log.record(f'{NAMES[i]} current sensor is not connected ({pin}); excluded from chart.', 'Errors')

    def show_log(self):
        if self.raw_window is None:
            self.raw_window = RawLogWindow(self.window, self.log)
        self.raw_window.show()
        self.raw_window.raise_()
        self.raw_window.activateWindow()

    def show_chart(self):
        if self.chart_window is None:
            self.chart_window = CurrentChartWindow(self.window, self.history)
        self.chart_window.show()
        self.chart_window.raise_()
        self.chart_window.activateWindow()

    def receive_ready(self):
        for _ in range(8):
            try:
                data, address = self.socket.recvfrom(4096)
            except BlockingIOError:
                break
            # Do not accept telemetry from another host on the local network.
            if address[0] != self.pi_address:
                self.rejected += 1
                continue
            now = time.monotonic()
            accepted = self.history.receive(data, now)
            if accepted:
                status = self.history.status
                self.log.capture_frame(data, status)
                for event in self.events.receive(status):
                    self.log.record(event.text, event.category)
                if self.rejecting:
                    self.log.record('Valid telemetry resumed after rejected packets', 'Diagnostics')
                    self.rejecting = False
            else:
                self.rejected += 1
                if not self.rejecting:
                    self.log.record(f'Rejected telemetry: bytes={len(data)} prefix={data[:56].hex()}',
                                    'Diagnostics')
                    self.rejecting = True
        self.refresh_status()

    def refresh_status(self):
        now = time.monotonic()
        if self.history.last_received is None:
            text = f'Waiting for Pi telemetry\nUDP {self.address[1]}'
        elif self.history.stale(now):
            for event in self.events.stale():
                self.log.record(event.text, event.category)
            text = f'Telemetry stale\nLast sample {now - self.history.last_received:.1f} s ago'
        else:
            state = self.history.status['state']
            name = STATES[state] if state < len(STATES) else 'UNKNOWN'
            text = f'Pi telemetry: {name}\nReceived {(now - self.history.last_received) * 1000:.0f} ms ago'
        if self.log.io.error:
            text += '\nLogging failed: ' + self.log.io.error
        elif self.log.io.dropped:
            text += f'\nLog records dropped: {self.log.io.dropped} (slow storage)'
        self.status.setText(text)

    def eventFilter(self, watched, event):
        if watched is self.window and event.type() == QtCore.QEvent.Close:
            self.close()
        return False

    def close(self):
        if self.closed:
            return
        self.closed = True
        self.timer.stop()
        self.receiver.setEnabled(False)
        self.socket.close()
        self.log.record('Telemetry receiver closed', 'Connection')
        for dialog in (self.raw_window, self.chart_window):
            if dialog is not None:
                dialog.close()
        if self.chart_window is not None:
            self.chart_window.timer.stop()
