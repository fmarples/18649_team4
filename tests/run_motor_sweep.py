"""Run the complete BOTH-motor startup/holding sweep from one Windows command.

Without --run, print the plan only. --allow-stall-reset explicitly authorizes a
checked reflash after expected stall faults 1/2, never retries a failed duty.
Reverse/encoder/HAL/reset errors abort. All process, serial and crash logs persist.
"""
import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import traceback

import serial
from check_motor_hold import parse_sample
from check_motor_idle import FRAME as MOTOR

STARTUP_DUTIES = (60, 55, 50)
HOLD_DUTIES = (55, 50, 45, 40, 35)
PASS = {'STARTED', 'HELD'}
EXPECTED_FAILURE = {'NO_START', 'PARTIAL_START', 'ABORTED_AFTER_MOTION',
                    'INSUFFICIENT_MOTION', 'STALLED_DURING_HOLD'}


# Descend once per setting; confirm the lowest pass, never repeat a failed setting.
def run_category(duties, run_trial):
    result = {'lowest_passing_duty': None, 'failed_duty': None,
              'confirmed_three_times': False, 'trials': []}
    for duty in duties:
        trial = run_trial(duty)
        result['trials'].append({'duty': duty, **trial})
        if trial['verdict'] not in PASS:
            if trial['verdict'] not in EXPECTED_FAILURE:
                raise RuntimeError('Unexpected trial result: ' + trial['verdict'])
            result['failed_duty'] = duty
            break
        result['lowest_passing_duty'] = duty
    floor = result['lowest_passing_duty']
    if floor is not None:
        for _ in range(2):
            trial = run_trial(floor)
            result['trials'].append({'duty': floor, **trial})
            if trial['verdict'] not in PASS:
                return result
        result['confirmed_three_times'] = True
    return result


# The real CLI owns the serial/build resources and restores idle on every exit.
def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', required=True)
    parser.add_argument('--drive', required=True, help='Rediscovered NOD_F401RE drive letter')
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--allow-stall-reset', action='store_true')
    args = parser.parse_args()
    drive = args.drive.rstrip(':').upper()
    if not re.fullmatch('[A-Z]', drive):
        parser.error('--drive must be a single drive letter')
    plan = {'side': 'BOTH', 'pwm_hz': 10000, 'startup_ms': 200,
            'startup_duties': STARTUP_DUTIES, 'holding_duties': HOLD_DUTIES,
            'hold_kick_percent': 60, 'hold_limit_ms': 4000,
            'confirmation_trials_at_lowest_pass': 2,
            'expected_stall_reset_authorized': args.allow_stall_reset}
    print(json.dumps(plan, indent=2), flush=True)
    if not args.run:
        print('PLAN ONLY: no hardware opened, flashed or actuated. Add --run to execute.')
        return
    repo = Path(__file__).resolve().parents[1]
    ws = Path.home() / 'zephyrproject'
    directory = repo / 'logs/motor-bench' / ('sweep-' + time.strftime('%Y%m%d-%H%M%S'))
    directory.mkdir(parents=True, exist_ok=False)
    (repo / 'build/motor-host-test').mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env['PATH'] = str(ws / '.venv/Scripts') + os.pathsep + env['PATH']
    env['PYTHONUNBUFFERED'] = '1'
    summary = {'plan': plan, 'status': 'RUNNING', 'completed_trials': []}
    current_profile = None
    sequence = 0

    def persist():
        (directory / 'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')

    def command(cmd, name, timeout, cwd=repo):
        with (directory / (name + '.log')).open('w', encoding='utf-8') as log:
            proc = subprocess.run([str(x) for x in cmd], cwd=cwd, env=env, text=True,
                                  stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
        text = (directory / (name + '.log')).read_text(encoding='utf-8')
        if proc.returncode:
            raise RuntimeError(f'{name} exited {proc.returncode}; log {directory / (name + ".log")}\n{text}')
        return text

    def stop_and_verify(name, allowed_faults):
        lines = []
        try:
            with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
                port.reset_input_buffer()
                port.write(b'STOP\n')
                end = time.monotonic() + 8
                previous = None
                still_since = None
                motor_off = False
                while time.monotonic() < end:
                    line = port.readline().decode('utf-8', errors='replace').strip()
                    if not line:
                        continue
                    lines.append(line)
                    motor = MOTOR.fullmatch(line)
                    if motor:
                        values = motor.groups()
                        if values[:5] != ('IDLE', '0', '0', '0000', '00'):
                            raise RuntimeError('STOP did not produce disabled outputs')
                        motor_off = True
                    sample = parse_sample(line)
                    if sample is None:
                        continue
                    if sample.stage != 'OFF' or sample.phase != 'IDLE' or sample.left_pct or sample.right_pct:
                        raise RuntimeError('Outputs active during stop check')
                    if sample.invalid_left or sample.invalid_right or sample.errors or sample.fault not in allowed_faults:
                        raise RuntimeError('Unexpected fault; no automatic reset: ' + line)
                    pair = (sample.left, sample.right)
                    if pair != previous:
                        previous, still_since = pair, sample.t_ms
                    elif sample.t_ms - still_since >= 1000 and motor_off:
                        return sample
                raise TimeoutError('Unable to verify disabled, stationary motors')
        finally:
            (directory / (name + '.json')).write_text(json.dumps(lines, indent=2), encoding='utf-8')

    def prepare(startup, hold, name, fault):
        nonlocal current_profile
        profile = (startup, hold)
        if profile == current_profile and not fault:
            return
        print(f'Preparing fixed image: startup {startup}%, hold 60% kick -> {hold}% / 4s', flush=True)
        if profile != current_profile:
            compiler = Path('C:/msys64/mingw64/bin/gcc.exe')
            command([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror', '-Ibringup/motor_test/src',
                     f'-DBENCH_DUTY_PERCENT={startup}', f'-DEXPECTED_DUTY={startup}',
                     f'-DBENCH_HOLD_PERCENT={hold}', f'-DEXPECTED_HOLD={hold}',
                     '-DBENCH_HOLD_MS=4000', '-DEXPECTED_HOLD_MS=4000',
                     'tests/test_motor_bench.c', 'bringup/motor_test/src/bench_control.c',
                     '-o', 'build/motor-host-test/test.exe'], name + '-host-build', 30)
            command([repo / 'build/motor-host-test/test.exe'], name + '-host-test', 20)
            command([ws / '.venv/Scripts/west.exe', 'build', '-b', 'nucleo_f401re',
                     '-d', repo / 'build/motor-test', repo / 'bringup/motor_test', '-o=-j4', '--',
                     f'-DMOTOR_TEST_DUTY={startup}', f'-DMOTOR_HOLD_DUTY={hold}', '-DMOTOR_HOLD_MS=4000'],
                    name + '-zephyr-build', 300, ws / 'zephyr')
        label = subprocess.check_output(['powershell.exe', '-NoProfile', '-Command',
                                         f'(Get-Volume -DriveLetter {drive}).FileSystemLabel'],
                                        text=True, timeout=15).strip()
        if label != 'NOD_F401RE':
            raise RuntimeError(f'Refusing to flash drive {drive}: label is {label!r}')
        lines = []
        try:
            with serial.Serial(args.port, 115200, timeout=0.1, write_timeout=1) as port:
                port.reset_input_buffer()
                shutil.copyfile(repo / 'build/motor-test/zephyr/zephyr.bin', Path(f'{drive}:/motor.bin'))
                expected = {f'MOTOR BENCH: idle at boot; 10kHz; one-shot {startup}% / 200ms.',
                            f'HOLD BENCH: 10kHz; kick=60%/200ms hold={hold}%/4000ms; LEFT/RIGHT/BOTH.'}
                end = time.monotonic() + 10
                while time.monotonic() < end:
                    line = port.readline().decode('utf-8', errors='replace').strip()
                    if line:
                        lines.append(line)
                        expected.discard(line)
                    if not expected and any('SCHED control=2 console=5' in x for x in lines):
                        break
                if expected or Path(f'{drive}:/FAIL.TXT').exists():
                    raise RuntimeError('Flash failure or missing runtime profile')
                port.write(b'STOP\n')
        finally:
            (directory / (name + '-flash.json')).write_text(json.dumps(lines, indent=2), encoding='utf-8')
        stop_and_verify(name + '-post-flash-idle', (0,))
        current_profile = profile

    def trial(kind, duty):
        nonlocal sequence
        sequence += 1
        name = f'{sequence:02d}-{kind}-{duty}'
        allowed = (0, 1, 2) if args.allow_stall_reset else (0,)
        state = stop_and_verify(name + '-preflight', allowed)
        prepare(duty if kind == 'startup' else 60, 55 if kind == 'startup' else duty, name, state.fault)
        print(f'POWERED TRIAL {sequence}: BOTH {kind} {duty}% (3-second warning inside check)', flush=True)
        if kind == 'startup':
            cmd = [sys.executable, 'tests/check_motor_startup.py', '--port', args.port,
                   '--side', 'BOTH', '--duty', str(duty), '--pulse']
        else:
            cmd = [sys.executable, 'tests/check_motor_hold.py', '--port', args.port,
                   '--side', 'BOTH', '--hold-duty', str(duty), '--hold-ms', '4000', '--run']
        output = command(cmd, name + '-trial', 25)
        print(output, flush=True)
        match = re.search(r'^Capture: (.+)$', output, re.MULTILINE)
        if not match:
            raise RuntimeError('Trial did not return a persistent capture path')
        path = Path(match.group(1).strip())
        data = json.loads(path.read_text(encoding='utf-8'))
        result = {**data['result'], 'capture': str(path)}
        if not result.get('outputs_disabled') or result.get('error'):
            raise RuntimeError('Trial did not finish disabled without a host error')
        summary['completed_trials'].append({'kind': kind, **result})
        persist()
        if result.get('fault') and not args.allow_stall_reset:
            raise RuntimeError('Motion fault: continuation/reset not authorized')
        if result['verdict'] not in PASS | EXPECTED_FAILURE:
            raise RuntimeError('Unexpected trial outcome; refusing to continue')
        return result

    persist()
    try:
        summary['startup'] = run_category(STARTUP_DUTIES, lambda duty: trial('startup', duty))
        persist()
        if not summary['startup']['confirmed_three_times']:
            raise RuntimeError('No repeatable BOTH startup floor; holding sweep aborted')
        summary['holding'] = run_category(HOLD_DUTIES, lambda duty: trial('holding', duty))
        persist()
        if not summary['holding']['confirmed_three_times']:
            raise RuntimeError('Holding floor not repeatable; no automatic escalation')
        state = stop_and_verify('before-final-profile', (0, 1, 2))
        prepare(60, 55, 'final-default', state.fault)
        summary['status'] = 'COMPLETE'
    except BaseException:
        summary['status'] = 'ABORTED'
        summary['error'] = traceback.format_exc()
        (directory / 'crash.txt').write_text(summary['error'], encoding='utf-8')
        raise
    finally:
        try:
            summary['final_idle'] = asdict(stop_and_verify('final-stop', (0, 1, 2, 3, 4)))
        except BaseException:
            summary['cleanup_error'] = traceback.format_exc()
            (directory / 'cleanup-crash.txt').write_text(summary['cleanup_error'], encoding='utf-8')
            summary['status'] = 'ABORTED'
        persist()
        print('Sweep summary:', directory / 'summary.json', flush=True)
    if summary['status'] != 'COMPLETE':
        raise RuntimeError('Final idle verification failed; inspect sweep summary and cleanup-crash.txt')
    print('Holding duty | Left RPM | Right RPM | Mean RPM | Verdict', flush=True)
    for trial_result in summary['holding']['trials']:
        wheels = trial_result.get('wheels')
        if wheels:
            print(f"{trial_result['duty']:>3}% | {wheels['LEFT']['late_rpm']:.1f} | "
                  f"{wheels['RIGHT']['late_rpm']:.1f} | {trial_result['late_rpm']:.1f} | {trial_result['verdict']}")
        else:
            print(f"{trial_result['duty']:>3}% | -- | -- | -- | {trial_result['verdict']}")
    print(json.dumps({key: {k: v for k, v in summary[key].items() if k != 'trials'}
                      for key in ('startup', 'holding')}, indent=2), flush=True)


if __name__ == '__main__':
    main()
