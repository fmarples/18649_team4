"""Process-local Windows timing policy and wheel callback diagnostics.

This is a scheduling request, not a real-time guarantee. It does not extend
the Pi freshness deadline, replay packets, or initialize the Logitech SDK.
"""
import ctypes
import sys
import time
from ctypes import wintypes


class PowerThrottling(ctypes.Structure):
    _fields_ = [('Version', wintypes.DWORD), ('ControlMask', wintypes.DWORD),
                ('StateMask', wintypes.DWORD)]


class WheelTimingPolicy:
    """Restore the process's original policy on exit; no system setting edits."""
    def __init__(self, log):
        self.log = log
        self.kernel = self.winmm = None
        self.priority = self.power = None
        self.period = False

    def _record(self, text):
        self.log.record(text, 'Diagnostics')

    def start(self):
        if sys.platform != 'win32' or self.kernel is not None:
            return
        self.kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        self.kernel.GetCurrentProcess.restype = wintypes.HANDLE
        self.handle = self.kernel.GetCurrentProcess()
        signatures = {
            'GetPriorityClass': ([wintypes.HANDLE], wintypes.DWORD),
            'SetPriorityClass': ([wintypes.HANDLE, wintypes.DWORD], wintypes.BOOL),
            'GetProcessInformation': ([wintypes.HANDLE, ctypes.c_int,
                                       ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
            'SetProcessInformation': ([wintypes.HANDLE, ctypes.c_int,
                                       ctypes.c_void_p, wintypes.DWORD], wintypes.BOOL),
        }
        for name, (args, result) in signatures.items():
            function = getattr(self.kernel, name)
            function.argtypes, function.restype = args, result
        # ProcessPowerThrottling=4. Version=1. Flags: execution speed=1,
        # ignore timer resolution=4. ControlMask owns the policy; StateMask=0
        # explicitly disables those two forms of throttling for this process.
        old = PowerThrottling(1, 0, 0)
        if self.kernel.GetProcessInformation(self.handle, 4, ctypes.byref(old), ctypes.sizeof(old)):
            requested = PowerThrottling(1, old.ControlMask | 5, old.StateMask & ~5)
            if self.kernel.SetProcessInformation(self.handle, 4, ctypes.byref(requested), ctypes.sizeof(requested)):
                self.power = old
                self._record('Wheel process: execution/timer throttling disabled')
            else:
                self._record(f'Wheel power policy unavailable: Windows error {ctypes.get_last_error()}')
        else:
            self._record(f'Wheel power policy query unavailable: Windows error {ctypes.get_last_error()}')
        old_priority = self.kernel.GetPriorityClass(self.handle)
        # Only raise NORMAL priority; never lower an existing higher priority.
        if old_priority == 0x20 and self.kernel.SetPriorityClass(self.handle, 0x8000):
            self.priority = old_priority
            self._record('Wheel process: AboveNormal priority (not real-time)')
        self.winmm = ctypes.WinDLL('winmm')
        for name in ('timeBeginPeriod', 'timeEndPeriod'):
            function = getattr(self.winmm, name)
            function.argtypes, function.restype = [wintypes.UINT], wintypes.UINT
        self.period = self.winmm.timeBeginPeriod(1) == 0
        self._record(f'Wheel process: 1 ms timer resolution requested={self.period}')

    def close(self):
        if self.period:
            self.winmm.timeEndPeriod(1)
            self.period = False
        if self.power is not None:
            self.kernel.SetProcessInformation(self.handle, 4, ctypes.byref(self.power), ctypes.sizeof(self.power))
            self.power = None
        if self.priority is not None:
            self.kernel.SetPriorityClass(self.handle, self.priority)
            self.priority = None


class TimedCallback:
    """Observe a callback without changing its arguments, result or failures."""
    def __init__(self, name, callback, log, clock=time.perf_counter):
        self.name, self.callback, self.log, self.clock = name, callback, log, clock
        self.previous = None

    def reset(self):
        self.previous = None

    def __call__(self, *args, **kwargs):
        start = self.clock()
        gap_ms = None if self.previous is None else (start - self.previous) * 1000
        self.previous = start
        try:
            return self.callback(*args, **kwargs)
        finally:
            elapsed_ms = (self.clock() - start) * 1000
            if elapsed_ms >= 20 or (gap_ms is not None and gap_ms >= 60):
                try:
                    self.log.record(f'Wheel callback {self.name}: entry_gap_ms={gap_ms!r}, '
                                    f'work_ms={elapsed_ms:.3f}', 'Diagnostics')
                except Exception:
                    pass  # A diagnostic failure must not alter wheel behavior.


def instrument_callbacks(window, log):
    callbacks = []
    for name, timer, callback in (
        ('sample/feedback', window.update_timer, window._update_sw),
        ('transmit', window.transmit_timer, window._transmit),
    ):
        observed = TimedCallback(name, callback, log)
        timer.timeout.disconnect(callback)
        timer.timeout.connect(observed)
        window.connect_button.clicked.connect(observed.reset)
        window.stop_button.clicked.connect(observed.reset)
        callbacks.append(observed)
    return callbacks
