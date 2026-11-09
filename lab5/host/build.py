"""Compile the shared production C core for host tests or Raspberry Pi.

Uses CC (e.g. 'gcc', 'clang', or 'python -m ziglang cc'); never deploys hardware.
"""

import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build" / ("lab5.dll" if os.name == "nt" else "liblab5.so")


def build():
    cc = shlex.split(os.environ.get("CC", "gcc"))
    if not shutil.which(cc[0]):
        try:
            import ziglang  # noqa: F401
        except ImportError:
            raise SystemExit(
                "Install a C compiler, or set CC to its command. Host build needs gcc/clang/zig cc."
            )
        cc = [sys.executable, "-m", "ziglang", "cc"]
    OUT.parent.mkdir(exist_ok=True)
    cmd = cc + [
        "-std=c11",
        "-D_POSIX_C_SOURCE=200809L",
        "-Wall",
        "-Wextra",
        "-Werror",
        "-O2",
        "-shared",
        f"-I{ROOT / 'core'}",
    ]
    if os.name != "nt":
        cmd += ["-fPIC"]
    cmd += [
        str(ROOT / "core" / x)
        for x in ("lab5.c", "clock.c", "store.c", "wire.c", "agent.c")
    ]
    cmd += [str(ROOT / "host/bridge.c"), "-o", str(OUT)]
    subprocess.run(cmd, check=True)
    print(OUT)
    return OUT


if __name__ == "__main__":
    build()
