"""Exercise the MCU bus LEDs with actual Lab 5 packets and legacy Pi traffic.

The production zone monitor is compiled for the host. This checks the traffic
semantics, not physical CAN delivery, MCU scheduling, or GPIO wiring.
"""

import ctypes
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pi"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_network import Network
from vehicle.cockpit import Cockpit, EventLog
from vehicle.pi_gpio import NoGpio
from vehicle import can_protocol as p


class Bus:
    def __init__(self):
        self.sent = []

    def send(self, message, **kwargs):
        self.sent.append(message)


class BusIndicatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        directory = Path(cls.temp.name)
        wrapper = directory / "monitor.c"
        wrapper.write_text('''
#include "zone_state.h"
static struct zone_monitor monitors[4];
void reset_monitors(void) {
    for (unsigned n = 1; n <= 3; ++n)
        zone_monitor_init(&monitors[n], n, 0);
}
void receive(unsigned node, unsigned bus, uint32_t ms) {
    zone_monitor_traffic(&monitors[node], bus, ms);
}
unsigned degraded(unsigned node, uint32_t ms) {
    struct zone_health h = zone_monitor_evaluate(&monitors[node], ms);
    return h.degraded[0] | (h.degraded[1] << 1);
}
''')
        compiler = shlex.split(os.environ.get("CC", "gcc"))
        if not shutil.which(compiler[0]):
            compiler = [sys.executable, "-m", "ziglang", "cc"]
        src = ROOT / "stm32_zephyr/src"
        library = directory / ("monitor.dll" if os.name == "nt" else "monitor.so")
        flags = [] if os.name == "nt" else ["-fPIC"]
        subprocess.run(
            compiler + ["-std=c11", "-Wall", "-Wextra", "-Werror", "-shared"]
            + flags + [f"-I{src}", str(wrapper), str(src / "zone_state.c"),
                       "-o", str(library)],
            check=True, capture_output=True, text=True,
        )
        cls.monitor = ctypes.CDLL(str(library))
        cls.monitor.reset_monitors.argtypes = []
        cls.monitor.reset_monitors.restype = None
        cls.monitor.receive.argtypes = [ctypes.c_uint] * 3
        cls.monitor.receive.restype = None
        cls.monitor.degraded.argtypes = [ctypes.c_uint] * 2
        cls.monitor.degraded.restype = ctypes.c_uint
        if os.name == "nt":
            import _ctypes
            cls.addClassCleanup(_ctypes.FreeLibrary, cls.monitor._handle)

    def setUp(self):
        self.monitor.reset_monitors()

    def test_matching_lab5_without_wheel_only_disconnected_node_lights(self):
        monitor = self.monitor

        class ObservedNetwork(Network):
            def deliver(self, dst, bus, can_id, data, at):
                # MCU dispatch records every bus's traffic before handling or
                # duplicate-filtering the protocol packet.
                monitor.receive(dst, bus, at // 1000)
                super().deliver(dst, bus, can_id, data, at)

        for cut_node in (2, 3):
            for cut_bus in (0, 1):
                with self.subTest(node=cut_node, bus=cut_bus):
                    monitor.reset_monitors()
                    net = ObservedNetwork()
                    try:
                        net.upstream = False  # Pi present, wheel input absent.
                        net.run(500)
                        net.links.remove((cut_node, cut_bus))
                        net.run(150)
                        for node in (2, 3):
                            self.assertEqual(
                                monitor.degraded(node, net.now // 1000),
                                1 << cut_bus if node == cut_node else 0,
                            )
                            self.assertTrue(net.nodes[node].health(net.now)["error"])
                        net.links.add((cut_node, cut_bus))
                        net.run(100)
                        self.assertEqual(monitor.degraded(2, net.now // 1000), 0)
                        self.assertEqual(monitor.degraded(3, net.now // 1000), 0)
                    finally:
                        net.close()

    def test_legacy_pi_without_wheel_reproduces_other_node_flicker(self):
        # N3 is off A; N2 still hears N3 on B. A legacy Pi without any wheel
        # command sends sparse BLINK frames, not periodic Lab 5 HELLO/REPORT.
        buses = [Bus(), Bus()]
        pi = Cockpit(buses, NoGpio(), EventLog(None), 0)
        masks, ids = {}, []
        for ms in range(1, 1001):
            pi.tick(ms / 1000)
            if ms % 20 == 0:
                self.monitor.receive(2, 1, ms)
            for bus, queue in enumerate(buses):
                for frame in queue.sent:
                    ids.append(frame.arbitration_id)
                    self.monitor.receive(2, bus, ms)
                queue.sent.clear()
            masks[ms] = self.monitor.degraded(2, ms)
        self.assertNotIn(p.HB_N1, ids)
        self.assertNotIn(p.CTRL, ids)
        self.assertIn(p.BLINK, ids)
        self.assertEqual(masks[50], 0)
        self.assertEqual(masks[100], 1)
        self.assertEqual(masks[490], 1)
        self.assertEqual(masks[525], 0)
        self.assertEqual(masks[600], 1)


if __name__ == "__main__":
    unittest.main()
