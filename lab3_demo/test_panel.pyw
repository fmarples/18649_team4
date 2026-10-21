"""Double-click launcher: course wheel window plus the Lab 3 test panel, no console.

Whatever Python opens this file, the GUI runs under the course checkout's
.venv pythonw, which has PyQt5 and the wheel SDK wrapper. Session logs and
crash reports: logs/wheel-gui/.
"""
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
from windows.start_wheel_proxy import course_repository, main  # noqa: E402

pythonw = course_repository() / ".venv" / "Scripts" / "pythonw.exe"
same_python = os.path.normcase(Path(sys.executable).parent) == os.path.normcase(pythonw.parent)
if not same_python and not os.environ.get("LAB3_PANEL_CHILD"):
    subprocess.Popen([str(pythonw), __file__], cwd=REPO, env=dict(os.environ, LAB3_PANEL_CHILD="1"),
                     creationflags=getattr(subprocess, "DETACHED_PROCESS", 0))
    sys.exit(0)
sys.argv = [sys.argv[0], "--lab3"]
sys.exit(main())
