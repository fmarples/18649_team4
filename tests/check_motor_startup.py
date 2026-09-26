"""One explicitly requested 200 ms startup trial at a verified fixed firmware duty.

Never sweeps, retries, resets, or clears faults. Each invocation requires --pulse.
Captures serial evidence and exception tracebacks under logs/motor-bench/.
"""
import argparse
import json
from pathlib import Path
import time
import traceback

import serial
from check_encoder_serial import FRAME as ENCODER
from check_motor_idle import FRAME as MOTOR


# Classify only encoder samples paired with active telemetry, excluding coast-down.
def classify_start(baseline, powered_counts, fault, side):
    if not powered_counts:
        raise RuntimeError('No powered encoder samples; startup result unknown')
    selected = (0, 1) if side == 'BOTH' else (0 if side == 'LEFT' else 1,)
    if fault not in (0, *(i + 1 for i in selected)):
        raise RuntimeError(f'Unexpected firmware fault {fault}')
    movements = []
    for wheel in selected:
        forward = []
        for counts in powered_counts:
            if side != 'BOTH' and counts[1 - wheel] != baseline[1 - wheel]:
                raise RuntimeError('Unselected wheel moved')
            delta = counts[wheel] - baseline[wheel]
            delta = -delta if wheel == 0 else delta
            if delta <= -4:
                raise RuntimeError('Reverse motion detected')
            forward.append(delta)
        movements.append(max(forward))
    if fault:
        if max(movements) < 4:
            return 'NO_START'
        return 'PARTIAL_START' if min(movements) < 4 else 'ABORTED_AFTER_MOTION'
    return 'STARTED' if min(movements) >= 8 else 'INSUFFICIENT_MOTION'


# Execute a single trial through the real console, with profile and rest interlocks.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--side', choices=('LEFT', 'RIGHT', 'BOTH'), required=True)
    parser.add_argument('--duty', type=int, choices=range(1, 101), required=True)
    parser.add_argument('--pulse', action='store_true')
    args = parser.parse_args()
    if not args.pulse:
        parser.error('--pulse is required; this physically actuates the selected motors')
    stem = Path('logs/motor-bench') / f'startup-{args.side.lower()}-{args.duty}-{time.strftime("%Y%m%d-%H%M%S")}'
    stem.parent.mkdir(parents=True, exist_ok=True)
    records = []
    result = {'side': args.side, 'duty_percent': args.duty, 'pwm_hz': 10000, 'pulse_limit_ms': 200}
    started = time.monotonic()
    phase = None
    fault = 0
    counts = None
    profile_seen = False
    pulse_sent = None
    powered_counts = []
    baseline = None
    active_seen = False
    expected_faults = (1, 2) if args.side == 'BOTH' else (1 if args.side == 'LEFT' else 2,)
    banner = f'MOTOR BENCH: idle at boot; 10kHz; one-shot {args.duty}% / 200ms.'
    try:
        with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
            def read_frame(deadline):
                nonlocal phase, fault, counts, profile_seen, active_seen
                while time.monotonic() < deadline:
                    line = port.readline().decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    now = time.monotonic()
                    records.append({'elapsed_s': round(now - started, 4), 'line': line})
                    if line.startswith('ERROR') or 'Booting Zephyr' in line:
                        raise RuntimeError('Firmware error/reset during measurement')
                    if line.startswith('MOTOR BENCH:'):
                        if line != banner or pulse_sent is not None:
                            raise RuntimeError('Unexpected firmware profile or restart: ' + line)
                        profile_seen = True
                    motor = MOTOR.fullmatch(line)
                    if motor:
                        new_phase, left, right, pins, en, fault_text, _, _ = motor.groups()
                        fault = int(fault_text)
                        if fault and (pulse_sent is None or fault not in expected_faults):
                            raise RuntimeError('Unexpected fault: ' + line)
                        if new_phase in ('IDLE', 'ARMED'):
                            if (left, right, pins, en) != ('0', '0', '0000', '00'):
                                raise RuntimeError('Outputs not disabled: ' + line)
                        elif new_phase == args.side and pulse_sent is not None:
                            expected = {'LEFT': (str(args.duty), '0', '0100'),
                                        'RIGHT': ('0', str(args.duty), '0010'),
                                        'BOTH': (str(args.duty), str(args.duty), '0110')}[args.side]
                            # Selected EN readbacks can be either level during partial-duty PWM.
                            inactive_en = '0' if args.side == 'BOTH' else en[1 if args.side == 'LEFT' else 0]
                            if (left, right, pins) != expected or inactive_en != '0':
                                raise RuntimeError('Unexpected active outputs: ' + line)
                            active_seen = True
                        else:
                            raise RuntimeError('Unrequested motor phase: ' + line)
                        if new_phase != phase:
                            print(f'{now - started:.3f}s {line}', flush=True)
                        phase = new_phase
                        return 'motor'
                    encoder = ENCODER.fullmatch(line)
                    if encoder:
                        values = tuple(int(v) for v in encoder.groups())
                        if any(values[i] for i in (4, 5, 6)):
                            raise RuntimeError('Encoder error: ' + line)
                        counts = values[:2]
                        if pulse_sent is not None and phase == args.side:
                            powered_counts.append(counts)
                        return 'encoder'
                raise TimeoutError('No complete telemetry frame before deadline')

            def stationary(seconds, timeout):
                end = time.monotonic() + timeout
                last_counts = None
                still_since = None
                while time.monotonic() < end:
                    kind = read_frame(min(end, time.monotonic() + 1))
                    if kind == 'motor' and phase != 'IDLE':
                        raise RuntimeError('Expected disabled IDLE while waiting for rest')
                    if kind == 'encoder':
                        now = time.monotonic()
                        if counts != last_counts:
                            last_counts, still_since = counts, now
                        elif still_since is not None and now - still_since >= seconds:
                            return
                raise TimeoutError('Wheels did not become stationary')

            try:
                port.reset_input_buffer()
                port.write(b'STOP\n')
                stationary(1.0, 6)
                # Drain opening USB fragments before requesting a fresh profile.
                port.write(b'STATUS\n')
                end = time.monotonic() + 1
                while not profile_seen:
                    read_frame(end)
                if phase != 'IDLE' or fault:
                    raise RuntimeError('Profile/idle interlock not satisfied')
                baseline = counts
                print(f'One {args.side} {args.duty}% / max 200 ms trial in 3 seconds...', flush=True)
                # Keep checking the encoders throughout the warning interval.
                end = time.monotonic() + 3
                while time.monotonic() < end:
                    read_frame(end + 0.2)
                    if phase != 'IDLE' or counts != baseline:
                        raise RuntimeError('Wheel moved before arming')
                port.write(b'ARM\n')
                end = time.monotonic() + 1
                while phase != 'ARMED':
                    read_frame(end)
                if counts != baseline:
                    raise RuntimeError('Wheel moved while arming')
                print(f'{args.side} {args.duty}% STARTUP PULSE NOW', flush=True)
                pulse_sent = time.monotonic()
                port.write((args.side + '\n').encode('ascii'))
                end = pulse_sent + 0.8
                while not (active_seen and phase == 'IDLE'):
                    read_frame(end)
                result['command_to_idle_s'] = round(time.monotonic() - pulse_sent, 4)
                result['fault'] = fault
                result['baseline_counts'] = baseline
                result['powered_counts'] = powered_counts
                verdict = classify_start(baseline, powered_counts, fault, args.side)
                result['verdict'] = verdict
                stationary(1.0, 8)
                result['final_stationary_counts'] = counts
                result['outputs_disabled'] = True
                print(json.dumps(result, indent=2), flush=True)
                # A completed measurement may be a failed/partial start. The batch
                # runner uses this explicit verdict; it never treats exit code as motion.
            finally:
                port.write(b'STOP\n')
    except BaseException:
        result['error'] = traceback.format_exc()
        stem.with_suffix('.crash.txt').write_text(result['error'], encoding='utf-8')
        raise
    finally:
        stem.with_suffix('.json').write_text(json.dumps({'result': result, 'records': records}, indent=2), encoding='utf-8')
        print('Capture:', stem.with_suffix('.json').resolve(), flush=True)


if __name__ == '__main__':
    main()
