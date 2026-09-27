"""Run the built Zephyr controller tests without hardware; stop QEMU after summary."""
import argparse
import os
from pathlib import Path
import queue
import subprocess
import threading
import time

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--qemu', required=True, type=Path)
    parser.add_argument('--elf', type=Path, default=Path('build/integration-tests/zephyr/zephyr.elf'))
    parser.add_argument('--log', required=True, type=Path)
    args = parser.parse_args()
    args.log.parent.mkdir(parents=True, exist_ok=True)
    events = queue.Queue()
    env = os.environ.copy()
    if os.name == 'nt':
        env['PATH'] = r'C:\Program Files\Git\mingw64\bin;' + env.get('PATH', '')
    with args.log.open('x', encoding='utf-8') as log:
        process = subprocess.Popen([str(args.qemu), '-cpu', 'cortex-m3', '-machine',
            'lm3s6965evb', '-nographic', '-no-reboot', '-net', 'none',
            '-icount', 'shift=6,align=off,sleep=off', '-rtc', 'clock=vm',
            '-kernel', str(args.elf.resolve())], stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, env=env)
        def read():
            for line in process.stdout: events.put(line)
            events.put(None)
        reader = threading.Thread(target=read, daemon=True); reader.start()
        passed = False
        deadline = time.monotonic() + 60
        try:
            while time.monotonic() < deadline:
                try: line = events.get(timeout=.5)
                except queue.Empty: continue
                if line is None: break
                log.write(line); log.flush()
                if 'SUITE PASS' in line or 'FAIL' in line: print(line.rstrip())
                if 'PROJECT EXECUTION SUCCESSFUL' in line:
                    passed = True; break
                if 'PROJECT EXECUTION FAILED' in line or 'FATAL ERROR' in line: break
        finally:
            if process.poll() is None:
                process.terminate()
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: process.kill(); process.wait()
            reader.join(timeout=2)
            process.stdout.close()
        if not passed: raise SystemExit('QEMU did not report success. Read ' + str(args.log))
        print('QEMU reported PROJECT EXECUTION SUCCESSFUL. Log: ' + str(args.log))

if __name__ == '__main__': main()
