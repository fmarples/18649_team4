"""Request STOP from the background PID session and verify its recorded shutdown.

B1 is the independent local stop; this command needs the host capture process.
"""
import json
from pathlib import Path
import time


# Do not kill the logger or reset the MCU; let it send STOP and verify coast-down.
def main():
    pointer = Path(__file__).resolve().parents[2] / 'logs/motor-bench/continuous-session.json'
    session = json.loads(pointer.read_text(encoding='utf-8'))
    Path(session['stop_file']).write_text('User requested STOP\n', encoding='utf-8')
    state_path = Path(session['state_file'])
    end = time.monotonic() + 12
    while time.monotonic() < end:
        if state_path.exists():
            state = json.loads(state_path.read_text(encoding='utf-8'))
            if state['status'] in ('STOPPED', 'FAILED'):
                print(json.dumps(state, indent=2))
                if not state.get('result', {}).get('outputs_disabled'):
                    raise RuntimeError('Stop not verified. Press B1 or use the motor-power cutoff.')
                return
        time.sleep(0.1)
    raise TimeoutError('Host stop not verified. Press B1 or use the motor-power cutoff.')


if __name__ == '__main__':
    main()
