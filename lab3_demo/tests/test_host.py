"""Host checks for the demo's pure STM32 modules, using the production C sources.

Run from the repository root: python lab3_demo/tests/test_host.py (needs gcc).
"""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

DEMO = Path(__file__).resolve().parents[1]
SRC = DEMO / "stm32_zephyr" / "src"
sys.path.insert(0, str(DEMO / "pi"))
import can_protocol as p  # noqa: E402

GCC = shutil.which("gcc")


def build_and_run(test, *sources, include=()):
    with tempfile.TemporaryDirectory() as directory:
        exe = Path(directory) / "test.exe"
        flags = ["-std=c11", "-Wall", "-Wextra", "-Werror", f"-I{SRC}", *(f"-I{i}" for i in include)]
        build = subprocess.run([GCC, *flags, str(test), *map(str, sources), "-o", str(exe)],
                               capture_output=True, text=True, timeout=60)
        if build.returncode:
            raise AssertionError(build.stderr)
        run = subprocess.run([str(exe)], capture_output=True, text=True, timeout=10)
        if run.returncode:
            raise AssertionError(run.stdout + run.stderr)
        return run.stdout


@unittest.skipIf(GCC is None, "host gcc required")
class HostCTests(unittest.TestCase):
    def test_zone_state(self):
        out = build_and_run(DEMO / "tests/test_zone_state.c", SRC / "zone_state.c")
        self.assertIn("PASS", out)

    def test_frame_history(self):
        out = build_and_run(DEMO / "tests/test_frame_history.c", SRC / "frame_history.c")
        self.assertIn("PASS", out)

    def test_c_and_python_protocols_agree(self):
        out = build_and_run(DEMO / "tests/print_frames.c", SRC / "can_protocol.c",
                            include=[DEMO / "tests/fake"])
        rows = {line.split()[0]: line.split()[1:] for line in out.splitlines()}

        def c_bytes(name):
            return bytes(int(x, 16) for x in rows[name][1:9])

        self.assertEqual(c_bytes("hb"), p.seal(0, p.heartbeat_body(p.STATE_OK, True, False)))
        self.assertEqual(c_bytes("fault"), p.seal(0, p.fault_body(p.ZONE_N1, p.FAULT_ZONE_LOST, p.ZONE_N2)))
        self.assertEqual(c_bytes("force"), p.seal(0, bytes([0, 0xFD, 0, 0, 0, 0, 0])))
        self.assertTrue(all(rows[name][-1] == "valid=1" for name in ("hb", "fault", "force")))
        self.assertEqual(p.ctrl_body(-1200, 100, 0, 0x21), bytes([0x10, 0x50, 0xFB, 100, 0, 0x21, 0]))
        self.assertEqual(rows["ctrl_ok"], ["1", "-1200", "100", "0", "33"])
        self.assertEqual(rows["ctrl_bad_brake"], ["0"])
        self.assertEqual(rows["ctrl_bad_flags"], ["0"])
        self.assertEqual(rows["rtr_valid"], ["0"])
        self.assertEqual(rows["origin"], ["fault=3", "blink=1", "hb3=3"])


if __name__ == "__main__":
    unittest.main()
