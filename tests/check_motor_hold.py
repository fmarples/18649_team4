"""One 60%/200ms kick followed by a fixed-duty, bounded hold on the selected raised wheels.

No automatic sweep, retry or fault reset. MCU timestamps exclude USB latency from
speed estimates. Captures and exception stack traces persist in logs/motor-bench.
"""
import argparse
from dataclasses import dataclass
import json
import math
from pathlib import Path
import re
import time
import traceback

import serial
from check_motor_idle import FRAME as MOTOR

FRAME = re.compile(
    r'SAMPLE t_ms=(\d+) stage=(OFF|PULSE|KICK|HOLD|PID) phase=(IDLE|ARMED|LEFT|RIGHT|BOTH) '
    r'left_pct=(\d+) right_pct=(\d+) left=(-?\d+) right=(-?\d+) '
    r'invalid_left=(\d+) invalid_right=(\d+) errors=(\d+) fault=(-?\d+)'
)
COUNTS_PER_REV = 1320
WHEEL_DIAMETER_M = 0.075


@dataclass(frozen=True)
class Sample:
    t_ms: int
    stage: str
    phase: str
    left_pct: int
    right_pct: int
    left: int
    right: int
    invalid_left: int
    invalid_right: int
    errors: int
    fault: int


# Parse only complete, versioned bench sample lines; unrelated serial stays in logs.
def parse_sample(line):
    match = FRAME.fullmatch(line)
    if not match:
        return None
    t, stage, phase, *numbers = match.groups()
    return Sample(int(t), stage, phase, *(int(x) for x in numbers))


# Both live capture and offline analysis reject wrong outputs and encoder faults.
def validate_sample(sample, side, duty):
    if sample.invalid_left or sample.invalid_right or sample.errors:
        raise RuntimeError('Encoder invalid transitions or GPIO errors')
    expected_faults = (0, 1, 2) if side == 'BOTH' else (0, 1 if side == 'LEFT' else 2)
    if sample.fault not in expected_faults:
        raise RuntimeError(f'Unexpected firmware fault {sample.fault}')
    if sample.stage == 'OFF':
        if sample.phase not in ('IDLE', 'ARMED') or sample.left_pct or sample.right_pct:
            raise RuntimeError('OFF sample has enabled outputs')
    else:
        percent = 60 if sample.stage == 'KICK' else duty
        expected = {'LEFT': (percent, 0), 'RIGHT': (0, percent), 'BOTH': (percent, percent)}[side]
        if sample.stage not in ('KICK', 'HOLD') or sample.phase != side or (sample.left_pct, sample.right_pct) != expected:
            raise RuntimeError('Unexpected active stage, duty or side')


# Report the last approximately one second of HOLD only, never kick/coast counts.
def summarize_hold(samples, side, duty, hold_ms=2000):
    if not samples:
        raise RuntimeError('No timestamped samples')
    for sample in samples:
        validate_sample(sample, side, duty)
    if any(b.t_ms <= a.t_ms for a, b in zip(samples, samples[1:])):
        raise RuntimeError('MCU time did not increase; reset or duplicate samples')
    other = 'right' if side == 'LEFT' else 'left'
    if side != 'BOTH' and any(getattr(s, other) != getattr(samples[0], other) for s in samples):
        raise RuntimeError('Unselected wheel moved')
    hold = [s for s in samples if s.stage == 'HOLD']
    kick = [s for s in samples if s.stage == 'KICK']
    result = {'verdict': None, 'late_rpm': None, 'hold_samples': len(hold),
              'counts_per_rev': COUNTS_PER_REV, 'wheel_diameter_m': WHEEL_DIAMETER_M}
    if not kick or samples[-1].stage != 'OFF':
        raise RuntimeError('Missing kick or final disabled sample')
    fault = next((s.fault for s in samples if s.fault), 0)
    result['fault'] = fault
    if fault:
        result['verdict'] = 'STALLED_DURING_HOLD' if hold else 'KICK_FAILED'
        return result
    if not hold or hold[-1].t_ms - hold[0].t_ms < hold_ms - 200:
        raise RuntimeError('Holding interval ended early without reported fault')
    late = [s for s in hold if s.t_ms >= hold[0].t_ms + hold_ms - 1000]
    if len(late) < 3 or late[-1].t_ms - late[0].t_ms < 700:
        raise RuntimeError('Insufficient late powered speed samples')
    middle = late[len(late) // 2]
    wheels = {}
    for wheel in (('LEFT', 'RIGHT') if side == 'BOTH' else (side,)):
        selected = 'left' if wheel == 'LEFT' else 'right'
        sign = -1 if wheel == 'LEFT' else 1

        def rpm(a, b):
            delta = sign * (getattr(b, selected) - getattr(a, selected))
            if delta <= 0:
                raise RuntimeError('No forward progress in powered speed window')
            return delta * 60000 / (COUNTS_PER_REV * (b.t_ms - a.t_ms))

        first_rpm = rpm(late[0], middle)
        last_rpm = rpm(middle, late[-1])
        mean_rpm = rpm(late[0], late[-1])
        wheels[wheel] = dict(late_rpm=mean_rpm,
                            late_m_per_s=mean_rpm / 60 * math.pi * WHEEL_DIAMETER_M,
                            late_first_half_rpm=first_rpm, late_second_half_rpm=last_rpm,
                            settled_in_late_window=abs(last_rpm - first_rpm) <= max(1, mean_rpm * 0.1))
    result.update(verdict='HELD', wheels=wheels,
                  late_window_ms=late[-1].t_ms - late[0].t_ms,
                  settled_in_late_window=all(w['settled_in_late_window'] for w in wheels.values()))
    # Correct each encoder's forward sign before averaging wheel speeds.
    for key in ('late_rpm', 'late_m_per_s', 'late_first_half_rpm', 'late_second_half_rpm'):
        result[key] = sum(w[key] for w in wheels.values()) / len(wheels)
    return result


# Execute one authorized trial with profile, idle/rest and output checks before ARM.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--side', choices=('LEFT', 'RIGHT', 'BOTH'), required=True)
    parser.add_argument('--hold-duty', type=int, required=True)
    parser.add_argument('--hold-ms', type=int, choices=(2000, 4000), default=2000)
    parser.add_argument('--run', action='store_true')
    args = parser.parse_args()
    if not args.run or not 1 <= args.hold_duty <= 60:
        parser.error('--run and --hold-duty 1..60 are required; this actuates a motor')
    stem = Path('logs/motor-bench') / f'hold-{args.side.lower()}-{args.hold_duty}-{time.strftime("%Y%m%d-%H%M%S")}'
    stem.parent.mkdir(parents=True, exist_ok=True)
    records, samples = [], []
    result = {'side': args.side, 'hold_duty': args.hold_duty, 'kick_duty': 60,
              'kick_ms': 200, 'hold_limit_ms': args.hold_ms, 'pwm_hz': 10000}
    start = time.monotonic()
    sent = False
    profile_seen = False
    last = None
    last_state = None
    baseline = None
    banner = f'HOLD BENCH: 10kHz; kick=60%/200ms hold={args.hold_duty}%/{args.hold_ms}ms; LEFT/RIGHT/BOTH.'
    try:
        with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
            def read_sample(deadline):
                nonlocal last, profile_seen, last_state
                while time.monotonic() < deadline:
                    line = port.readline().decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    records.append({'host_elapsed_s': round(time.monotonic() - start, 4), 'line': line})
                    if line.startswith('ERROR') or 'Booting Zephyr' in line or (sent and 'BENCH:' in line):
                        raise RuntimeError('Firmware error or reset')
                    if line.startswith('HOLD BENCH:'):
                        if line != banner:
                            raise RuntimeError('Wrong compiled holding profile: ' + line)
                        profile_seen = True
                    motor = MOTOR.fullmatch(line)
                    if motor:
                        phase, left, right, pins, en, fault, _, _ = motor.groups()
                        if phase in ('IDLE', 'ARMED'):
                            if (left, right, pins, en) != ('0', '0', '0000', '00'):
                                raise RuntimeError('Idle control pins not low')
                        else:
                            expected_pins = {'LEFT': '0100', 'RIGHT': '0010', 'BOTH': '0110'}[args.side]
                            other_enabled = args.side != 'BOTH' and en[1 if args.side == 'LEFT' else 0] != '0'
                            if phase != args.side or not sent or pins != expected_pins or other_enabled:
                                raise RuntimeError('Unexpected bridge outputs')
                    sample = parse_sample(line)
                    if sample is None:
                        continue
                    validate_sample(sample, args.side, args.hold_duty)
                    if not sent and (sample.fault or sample.stage != 'OFF'):
                        raise RuntimeError('Preflight requires disabled fault-free outputs')
                    if last is not None:
                        dt = sample.t_ms - last.t_ms
                        if dt <= 0 or dt > 200:
                            raise RuntimeError('Timestamp reset or telemetry gap >200 ms')
                    if sent and baseline is not None and args.side != 'BOTH':
                        other = 'right' if args.side == 'LEFT' else 'left'
                        if getattr(sample, other) != getattr(baseline, other):
                            raise RuntimeError('Unselected wheel moved')
                    last = sample
                    samples.append(sample)
                    state = (sample.phase, sample.stage, sample.fault)
                    if state != last_state:
                        print(line, flush=True)
                        last_state = state
                    return sample
                raise TimeoutError('No complete timestamped sample')

            def stationary(timeout=8):
                end = time.monotonic() + timeout
                still_since = None
                previous = None
                while time.monotonic() < end:
                    sample = read_sample(min(end, time.monotonic() + 1))
                    if sample.phase != 'IDLE' or sample.stage != 'OFF':
                        raise RuntimeError('Not disabled during rest check')
                    pair = (sample.left, sample.right)
                    if pair != previous:
                        still_since, previous = sample.t_ms, pair
                    elif sample.t_ms - still_since >= 1000:
                        return sample
                raise TimeoutError('Wheels did not become stationary')

            try:
                port.reset_input_buffer()
                port.write(b'STOP\n')
                baseline = stationary()
                port.write(b'STATUS\n')
                end = time.monotonic() + 1
                while not profile_seen:
                    read_sample(end)
                print(f'One {args.side}: 60%/200ms then {args.hold_duty}%/max {args.hold_ms}ms in 3 seconds...', flush=True)
                end = time.monotonic() + 3
                while time.monotonic() < end:
                    sample = read_sample(end + 0.2)
                    if sample.phase != 'IDLE' or (sample.left, sample.right) != (baseline.left, baseline.right):
                        raise RuntimeError('Wheel moved before ARM')
                port.write(b'ARM\n')
                end = time.monotonic() + 1
                while last.phase != 'ARMED':
                    read_sample(end)
                print(f'{args.side} KICK/HOLD NOW', flush=True)
                trial_index = len(samples)
                sent = True
                port.write(('HOLD' + args.side + '\n').encode('ascii'))
                end = time.monotonic() + args.hold_ms / 1000 + 1
                active_seen = False
                while True:
                    sample = read_sample(min(end, time.monotonic() + 1))
                    active_seen |= sample.stage == 'KICK'
                    if active_seen and sample.phase == 'IDLE':
                        break
                result.update(summarize_hold(samples[trial_index:], args.side, args.hold_duty, args.hold_ms))
                final = stationary()
                result.update(outputs_disabled=True, final_counts=[final.left, final.right])
                print(json.dumps(result, indent=2), flush=True)
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
