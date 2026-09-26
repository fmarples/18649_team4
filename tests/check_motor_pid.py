"""Continuous BOTH-wheel PID until B1 or STOP; no timer, retry, tuning or fault reset.

Without --run, display the plan without opening hardware. Logs and exception
stack traces persist under logs/motor-bench/pid-<rpm>-<timestamp>.*.
"""
import argparse
import json
from pathlib import Path
import re
import time
import traceback

import serial
from check_motor_hold import COUNTS_PER_REV, parse_sample
from check_motor_idle import FRAME as MOTOR

PID_KEYS = ('t_ms', 'target', 'left_mrpm', 'right_mrpm', 'avg_mrpm',
            'left_mduty', 'right_mduty', 'p', 'i', 'd', 'trim')
PID_FRAME = re.compile('PID ' + ' '.join(key + r'=(-?\d+)' for key in PID_KEYS))
PROFILE = ('PID_PROFILE min_duty=40 max_duty=100 run_ms=0 sample_ms=20 cpr=1320 '
           'kp_milli=120 ki_milli=350 kd_milli=3 filter_ms=60 stop=B1 motion_guard=0')


# Retain fractional duty and controller terms without trusting them as speed proof.
def parse_pid(line):
    match = PID_FRAME.fullmatch(line)
    return dict(zip(PID_KEYS, map(int, match.groups()))) if match else None


# A mismatched target or an output above the compiled cap aborts the live trial.
def validate_pid(frame, target):
    if frame['target'] != target or any(not 40000 <= frame[key] <= 100000
                                      for key in ('left_mduty', 'right_mduty')):
        raise RuntimeError('Wrong PID target or running duty outside user-selected 40..100%')


# Use the coherent SAMPLE record for mode, raw-count and fault checks.
def validate_sample(sample):
    if sample.fault not in (0, 6) or sample.errors or sample.invalid_left or sample.invalid_right:
        raise RuntimeError(f'Firmware/encoder fault in PID trial: {sample}')
    if sample.stage == 'OFF':
        if sample.phase not in ('IDLE', 'ARMED') or sample.left_pct or sample.right_pct:
            raise RuntimeError('OFF sample has enabled outputs')
    elif (sample.fault or sample.stage not in ('KICK', 'PID') or sample.phase != 'BOTH' or
          not 40 <= sample.left_pct <= 100 or not 40 <= sample.right_pct <= 100):
        raise RuntimeError('Unexpected powered PID stage, side or duty')
    elif sample.stage == 'KICK' and (sample.left_pct, sample.right_pct) != (60, 60):
        raise RuntimeError('Wrong startup kick')


# Judge the last powered second from raw counts and MCU time, excluding coast.
# +/-5 RPM per wheel and <=5 RPM half-window drift are provisional bench criteria.
def summarize_pid(samples, target):
    for sample in samples:
        validate_sample(sample)
        if sample.fault:
            raise RuntimeError('Fault in historical bounded trial')
    if not samples or any(b.t_ms <= a.t_ms or b.t_ms - a.t_ms > 200
                          for a, b in zip(samples, samples[1:])):
        raise RuntimeError('Missing samples, timestamp reset or telemetry gap')
    kick = [s for s in samples if s.stage == 'KICK']
    powered = [s for s in samples if s.stage == 'PID']
    if (not kick or samples[-1].stage != 'OFF' or not powered or
            powered[-1].t_ms - powered[0].t_ms < 3800):
        raise RuntimeError('Missing kick, full 4-second PID interval or final disabled sample')
    # Allow 100 ms for telemetry boundary uncertainty, not a longer command.
    if (powered[0].t_ms - kick[0].t_ms > 300 or
            samples[-1].t_ms - powered[0].t_ms > 4100 or
            samples[-1].t_ms - kick[0].t_ms > 4300):
        raise RuntimeError('Kick or PID powered interval exceeded its bounded duration')
    late = [s for s in powered if s.t_ms >= powered[-1].t_ms - 1000]
    if len(late) < 3 or late[-1].t_ms - late[0].t_ms < 700:
        raise RuntimeError('Insufficient late powered samples')
    result = {'target_rpm': target, 'counts_per_rev': COUNTS_PER_REV,
              'late_window_ms': late[-1].t_ms - late[0].t_ms}
    stable = True
    for name, sign in (('left', -1), ('right', 1)):
        def rpm(a, b):
            return sign * (getattr(b, name) - getattr(a, name)) * 60000 / (COUNTS_PER_REV * (b.t_ms - a.t_ms))
        speed = rpm(late[0], late[-1])
        middle = late[len(late) // 2]
        drift = rpm(middle, late[-1]) - rpm(late[0], middle)
        result[name + '_rpm'] = speed
        result[name + '_drift_rpm'] = drift
        stable &= abs(speed - target) <= 5 and abs(drift) <= 5
    result['average_rpm'] = (result['left_rpm'] + result['right_rpm']) / 2
    result['verdict'] = 'AT_TARGET' if stable else 'OFF_TARGET'
    return result


# The CLI logs continuously, with constant memory, until B1/STOP or a fault.
# --run authorizes motor actuation; there is deliberately no duration/heartbeat cap.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--rpm', type=int, default=45)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--state-file', type=Path)
    parser.add_argument('--stop-file', type=Path)
    args = parser.parse_args()
    if not 1 <= args.rpm <= 0xFFFFFFFF:
        parser.error('--rpm must be a positive unsigned 32-bit integer')
    result = {'target_rpm': args.rpm, 'side': 'BOTH', 'kick_percent': 60,
              'kick_ms': 200, 'run_ms': 0, 'stop': 'B1', 'min_running_duty_percent': 40, 'max_duty_percent': 100, 'pwm_hz': 10000}
    print(json.dumps(result, indent=2), flush=True)
    if not args.run:
        print('PLAN ONLY: no hardware opened or actuated. Add --run after bench readiness confirmation.')
        return 0
    stem = Path('logs/motor-bench') / f'pid-{args.rpm}-{time.strftime("%Y%m%d-%H%M%S")}'
    stem.parent.mkdir(parents=True, exist_ok=True)
    result['pid_frames'] = 0
    sent = profile_seen = cleaning_up = False
    last = last_pid = None
    motor_off = False
    motor_seen_at = 0.0
    cleanup_fault = None
    start = time.monotonic()

    last_state = (None, 0.0)

    def state(status, **extra):
        nonlocal last_state
        now = time.monotonic()
        if status == last_state[0] and now - last_state[1] < 0.5:
            return
        if args.state_file:
            payload = dict(status=status, log=str(stem.with_suffix('.serial.log').resolve()),
                           target_rpm=args.rpm, **extra)
            temporary = args.state_file.with_suffix('.tmp')
            temporary.write_text(json.dumps(payload), encoding='utf-8')
            # Windows readers may briefly hold a handle without delete sharing.
            # Retry that specific transient error; persistent errors still abort.
            for attempt in range(25):
                try:
                    temporary.replace(args.state_file)
                    break
                except PermissionError:
                    if attempt == 24:
                        raise
                    time.sleep(0.01)
        last_state = (status, now)

    state('PREPARING')
    try:
        with stem.with_suffix('.serial.log').open('w', encoding='utf-8', buffering=1) as live_log, \
                serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
            def read_sample(deadline):
                nonlocal profile_seen, last, last_pid, motor_off, motor_seen_at, cleanup_fault
                while time.monotonic() < deadline:
                    line = port.readline().decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    elapsed = round(time.monotonic() - start, 4)
                    live_log.write(f'{elapsed:.4f} {line}\n')
                    # The flushed serial log is the complete record; never retain
                    # an unbounded in-memory list for continuous operation.
                    if (line.startswith('ERROR') or 'FATAL ERROR' in line or 'Booting Zephyr' in line or
                            (sent and ('BENCH:' in line or line.startswith('PID_PROFILE')))):
                        raise RuntimeError('Firmware error or unexpected reset')
                    if line.startswith('PID_PROFILE'):
                        if line != PROFILE:
                            raise RuntimeError('Wrong compiled PID profile: ' + line)
                        profile_seen = True
                    motor = MOTOR.fullmatch(line)
                    if motor:
                        motor_off = motor.groups()[:5] == ('IDLE', '0', '0', '0000', '00')
                        motor_seen_at = time.monotonic()
                        if cleaning_up and int(motor.group(6)) not in (0, 6):
                            cleanup_fault = cleanup_fault or line
                    if motor and not cleaning_up:
                        phase, left, right, pins, en, fault, _, _ = motor.groups()
                        if int(fault) not in (0, 6) or pins[0] != '0' or pins[3] != '0':
                            raise RuntimeError('Firmware fault or reverse bridge polarity')
                        if not sent and (left, right, pins, en) != ('0', '0', '0000', '00'):
                            raise RuntimeError('Preflight outputs not disabled')
                    frame = parse_pid(line)
                    if frame and not cleaning_up:
                        if not sent:
                            raise RuntimeError('Unexpected PID operation before ARM')
                        validate_pid(frame, args.rpm)
                        if last_pid and frame['t_ms'] <= last_pid['t_ms']:
                            raise RuntimeError('PID estimator time reset')
                        last_pid = frame
                        result['pid_frames'] += 1
                    sample = parse_sample(line)
                    if sample is None:
                        continue
                    if cleaning_up and (sample.fault not in (0, 6) or sample.errors or sample.invalid_left or sample.invalid_right):
                        cleanup_fault = cleanup_fault or line
                    if not cleaning_up:
                        validate_sample(sample)
                        if not sent and (sample.stage != 'OFF' or sample.fault):
                            raise RuntimeError('Unexpected actuation before PID command')
                    if last and sample.t_ms <= last.t_ms:
                        raise RuntimeError('MCU time reset')
                    last = sample
                    state('RUNNING' if sent and sample.stage in ('KICK', 'PID') else 'STOPPING' if sent else 'PREPARING',
                          t_ms=sample.t_ms, fault=sample.fault, pid=last_pid)
                    return sample
                raise TimeoutError('No complete timestamped sample')

            def stationary():
                end = time.monotonic() + 8
                off_deadline = time.monotonic() + 0.5
                previous = None
                still_since = None
                while time.monotonic() < end:
                    sample = read_sample(min(end, time.monotonic() + 1))
                    if (sample.stage != 'OFF' or sample.phase != 'IDLE' or
                            sample.left_pct or sample.right_pct):
                        if time.monotonic() < off_deadline:
                            continue
                        raise RuntimeError('STOP did not disable both outputs')
                    pair = (sample.left, sample.right)
                    if pair != previous:
                        previous, still_since = pair, sample.t_ms
                    elif sample.t_ms - still_since >= 1000 and motor_off and time.monotonic() - motor_seen_at <= 0.2:
                        return sample
                raise TimeoutError('Wheels did not report stationary counts')

            try:
                port.reset_input_buffer()
                port.write(b'STOP\n')
                baseline = stationary()
                port.write(b'STATUS\n')
                end = time.monotonic() + 1
                while not profile_seen:
                    read_sample(end)
                print(f'BOTH motors: PID {args.rpm} RPM continuously in 3 seconds. B1 stops both.', flush=True)
                end = time.monotonic() + 3
                while time.monotonic() < end:
                    sample = read_sample(end + 0.2)
                    if sample.phase != 'IDLE' or (sample.left, sample.right) != (baseline.left, baseline.right):
                        raise RuntimeError('Wheel moved before ARM')
                if args.stop_file and args.stop_file.exists():
                    result['verdict'] = 'REQUESTED_STOP'
                    return 0
                port.write(b'ARM\n')
                end = time.monotonic() + 1
                while last.phase != 'ARMED':
                    read_sample(end)
                sent = True
                port.write(f'PID {args.rpm}\n'.encode('ascii'))
                active_seen = False
                requested_stop = False
                stop_deadline = None
                arm_deadline = time.monotonic() + 1
                while True:
                    if args.stop_file and args.stop_file.exists() and not requested_stop:
                        port.write(b'STOP\n')
                        requested_stop = True
                        stop_deadline = time.monotonic() + 0.5
                    if stop_deadline is not None and time.monotonic() >= stop_deadline:
                        raise RuntimeError('STOP not acknowledged; retrying in cleanup')
                    if not active_seen and time.monotonic() >= arm_deadline:
                        raise RuntimeError('PID command did not start')
                    try:
                        sample = read_sample(time.monotonic() + 1)
                    except TimeoutError:
                        # Missing host telemetry is not a motor run-time limit.
                        # Continue polling STOP; B1 remains local to the MCU.
                        continue
                    active_seen |= sample.stage in ('KICK', 'PID')
                    if sample.phase == 'IDLE' and (sample.fault == 6 or requested_stop):
                        result['verdict'] = 'B1_STOP' if sample.fault == 6 else 'REQUESTED_STOP'
                        break
                    if active_seen and sample.phase == 'IDLE':
                        raise RuntimeError('Unexpected stop without B1 or STOP request')
                    if not active_seen and time.monotonic() >= arm_deadline:
                        raise RuntimeError('PID command did not start')
            finally:
                cleaning_up = True
                try:
                    port.write(b'STOP\n')
                    final = stationary()
                    result.update(outputs_disabled=True, final_counts=[final.left, final.right], final_fault=final.fault)
                    if cleanup_fault:
                        result.update(verdict='FAULT_DURING_STOP', cleanup_fault=cleanup_fault)
                        raise RuntimeError('Firmware or encoder fault during stop/coast-down: ' + cleanup_fault)
                except BaseException:
                    result['cleanup_error'] = traceback.format_exc()
                    stem.with_suffix('.cleanup-crash.txt').write_text(result['cleanup_error'], encoding='utf-8')
                    raise
    except BaseException:
        result['error'] = traceback.format_exc()
        stem.with_suffix('.crash.txt').write_text(result['error'], encoding='utf-8')
        raise
    finally:
        stem.with_suffix('.json').write_text(json.dumps({'result': result}, indent=2), encoding='utf-8')
        state('FAILED' if 'error' in result else 'STOPPED', result=result)
        print('Capture:', stem.with_suffix('.json').resolve(), flush=True)
    print(json.dumps(result, indent=2), flush=True)
    return 0 if result['verdict'] in ('B1_STOP', 'REQUESTED_STOP') else 1


if __name__ == '__main__':
    raise SystemExit(main())
