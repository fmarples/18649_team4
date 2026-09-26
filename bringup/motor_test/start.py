"""Start continuous PID capture in the background without opening a terminal.

Requires --run to actuate. B1 stops both motors; stop.py requests serial STOP.
No duration limit, automatic retry, reflash or fault reset.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time


# Own one background serial session; publish its PID and persistent artifact paths.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--rpm', type=int, default=45)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not 1 <= args.rpm <= 0xFFFFFFFF:
        parser.error('--rpm must be a positive unsigned 32-bit integer')
    if not args.run:
        print(f'PLAN ONLY: BOTH at {args.rpm} RPM continuously until B1/STOP. Add --run to actuate.')
        return
    repo = Path(__file__).resolve().parents[2]
    logs = repo / 'logs/motor-bench'
    logs.mkdir(parents=True, exist_ok=True)
    pointer = logs / 'continuous-session.json'
    if pointer.exists():
        previous = json.loads(pointer.read_text(encoding='utf-8'))
        state_path = Path(previous['state_file'])
        if not state_path.exists() or json.loads(state_path.read_text(encoding='utf-8'))['status'] not in ('STOPPED', 'FAILED'):
            raise RuntimeError('A session is already active or unverified; use B1/stop.py first')
    folder = logs / ('continuous-' + time.strftime('%Y%m%d-%H%M%S'))
    folder.mkdir(exist_ok=False)
    state = folder / 'state.json'
    stop = folder / 'stop.request'
    command = [sys.executable, str(repo / 'tests/check_motor_pid.py'), '--port', args.port,
               '--rpm', str(args.rpm), '--run', '--state-file', str(state), '--stop-file', str(stop)]
    options = {'creationflags': subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP} if os.name == 'nt' else {'start_new_session': True}
    ownership = dict(pid=None, port=args.port, state_file=str(state), stop_file=str(stop),
                     process_log=str(folder / 'process.log'))
    # Publish the stop route BEFORE a child can arm anything.
    pointer.write_text(json.dumps(ownership, indent=2), encoding='utf-8')
    process = None
    try:
        with (folder / 'process.log').open('w', encoding='utf-8') as output:
            process = subprocess.Popen(command, cwd=repo, stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=subprocess.STDOUT, close_fds=True, **options)
        ownership['pid'] = process.pid
        pointer.write_text(json.dumps(ownership, indent=2), encoding='utf-8')
        end = time.monotonic() + 20
        while time.monotonic() < end:
            if state.exists():
                status = json.loads(state.read_text(encoding='utf-8'))
                if status['status'] == 'RUNNING':
                    print(json.dumps(status, indent=2))
                    print('Running with no time cap. B1 stops BOTH and latches off until reset.')
                    return
                if status['status'] in ('FAILED', 'STOPPED'):
                    raise RuntimeError(f'Session ended: {status}; log {folder / "process.log"}')
            if process.poll() is not None:
                raise RuntimeError(f'Capture exited {process.returncode}; log {folder / "process.log"}')
            time.sleep(0.1)
        raise TimeoutError(f'Start not verified. Log: {folder / "process.log"}')
    except BaseException:
        stop.write_text('Launcher failed; STOP requested\n', encoding='utf-8')
        if process is not None:
            try:
                process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                print('Capture did not exit: press B1 or use the motor-power cutoff.', file=sys.stderr)
        raise


if __name__ == '__main__':
    main()
