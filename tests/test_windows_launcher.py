"""Check the relocated CMD entry point without starting a wheel or GUI."""

import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


@unittest.skipUnless(sys.platform == "win32", "requires Windows CMD")
class WindowsLauncherTests(unittest.TestCase):
    def test_finds_course_proxy_beside_team_checkout(self):
        with tempfile.TemporaryDirectory(prefix="wheel launcher ") as directory:
            workspace = Path(directory)
            launcher_dir = workspace / "team" / "windows"
            launcher_dir.mkdir(parents=True)
            launcher = launcher_dir / "start_wheel_proxy.cmd"
            shutil.copyfile(
                Path(__file__).resolve().parents[1] / "windows" / launcher.name,
                launcher,
            )
            course = workspace / "logitech-wheel-dev-updated-f26"
            course.mkdir()
            (course / "proxy_gui.py").write_text("", encoding="utf-8")
            # Stand in for the GUI entry point; exercise the real CMD discovery.
            (launcher_dir / "start_wheel_proxy.py").write_text(
                "import os\nprint(os.environ['LOGITECH_WHEEL_REPO'])\n",
                encoding="utf-8",
            )
            env = {k: v for k, v in os.environ.items() if k.upper() != "LOGITECH_WHEEL_REPO"}
            env["PATH"] = str(Path(sys.executable).parent) + os.pathsep + env.get("PATH", "")
            result = subprocess.run(
                [os.environ.get("COMSPEC", "cmd.exe"), "/d", "/c", str(launcher)],
                input="",
                capture_output=True,
                text=True,
                cwd=workspace,
                env=env,
                timeout=15,
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn(str(course), result.stdout)
            self.assertNotIn("Enter the course", result.stdout)


if __name__ == "__main__":
    unittest.main()
