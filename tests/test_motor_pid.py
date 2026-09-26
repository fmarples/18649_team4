"""PID verdicts use powered raw encoder counts, not filtered self-reported RPM."""
from dataclasses import replace
import unittest
from pathlib import Path
import subprocess
import sys
from collections import deque
from contextlib import chdir, redirect_stdout
import io
import importlib.util
import tempfile
from unittest.mock import patch
import check_motor_pid

from check_motor_hold import parse_sample
from check_motor_pid import parse_pid, summarize_pid, validate_pid


def trial():
    samples = []
    for t in range(1000, 5201, 100):
        stage = 'KICK' if t < 1200 else 'PID' if t < 5200 else 'OFF'
        phase = 'IDLE' if stage == 'OFF' else 'BOTH'
        duty = 0 if stage == 'OFF' else 60 if stage == 'KICK' else 45
        counts = (t - 1000) * 99 // 100  # Independently worked: 990 counts/s = 45 RPM.
        samples.append(parse_sample(
            f'SAMPLE t_ms={t} stage={stage} phase={phase} left_pct={duty} right_pct={duty} '
            f'left={-counts} right={counts} invalid_left=0 invalid_right=0 errors=0 fault=0'))
    return samples


# Serial is the external hardware boundary. MCU/host clocks advance independently
# and faults can first appear after the firmware's final powered sample.
class SerialTranscript:
    def __init__(self, coast_fault=False):
        self.lines = deque()
        self.t = 1000
        self.host = 0.0
        self.phase = 'IDLE'
        self.start = None
        self.coast_fault = coast_fault
        self.fault = 0
        self.count = 0

    def __enter__(self):
        return self

    def __exit__(self, *_):
        pass

    def reset_input_buffer(self):
        self.lines.clear()

    def write(self, command):
        if command == b'STATUS\n':
            self.lines.append(check_motor_pid.PROFILE)
        elif command == b'ARM\n':
            self.phase = 'ARMED'
        elif command == b'PID 45\n':
            self.phase = 'BOTH'
            self.start = self.t
        elif command == b'STOP\n':
            self.phase = 'IDLE'
            if self.start is not None and self.coast_fault:
                self.fault = 1
        else:
            raise AssertionError(command)
        return len(command)

    def readline(self):
        self.host += 0.02
        if not self.lines:
            self.t += 50
            stage, duty = 'OFF', 0
            if self.phase == 'BOTH':
                elapsed = self.t - self.start
                self.count = elapsed * 99 // 100
                if elapsed >= 30000:
                    self.phase = 'IDLE'
                    self.fault = 6  # Physical B1 event well past the former 4-second cap.
                else:
                    stage = 'KICK' if elapsed < 200 else 'PID'
                    duty = 60 if stage == 'KICK' else 45
            pins, en = ('0110', '11') if duty else ('0000', '00')
            self.lines.append(f'MOTOR phase={self.phase} left={duty} right={duty} in={pins} en={en} '
                              f'fault={self.fault} accepted=2 rejected=0')
            self.lines.append(f'SAMPLE t_ms={self.t} stage={stage} phase={self.phase} '
                              f'left_pct={duty} right_pct={duty} left={-self.count} right={self.count} '
                              f'invalid_left=0 invalid_right=0 errors=0 fault={self.fault}')
            if duty:
                self.lines.append(f'PID t_ms={self.t} target=45 left_mrpm=45000 right_mrpm=45000 avg_mrpm=45000 '
                                  f'left_mduty={duty * 1000} right_mduty={duty * 1000} p=0 i=0 d=0 trim=0')
        return (self.lines.popleft() + '\n').encode('ascii')


class MotorPidTests(unittest.TestCase):
    def test_overlong_kick_or_run_cannot_pass(self):
        samples = trial()
        overlong = [replace(s, t_ms=round(1000 + (s.t_ms - 1000) * 1.1)) for s in samples]
        long_kick = [replace(s, stage='KICK', left_pct=60, right_pct=60)
                     if s.stage == 'PID' and s.t_ms < 1600 else s for s in samples]
        for trace in (overlong, long_kick):
            with self.assertRaises(RuntimeError):
                summarize_pid(trace, 45)

    def test_fault_first_appearing_during_coast_fails_real_cli_flow(self):
        for fault in (False, True):
            fake = SerialTranscript(coast_fault=fault)
            with self.subTest(coast_fault=fault), tempfile.TemporaryDirectory() as directory, chdir(directory), \
                    patch.object(sys, 'argv', ['check_motor_pid', '--port', 'FAKE', '--rpm', '45', '--run']), \
                    patch.object(check_motor_pid.serial, 'Serial', return_value=fake), \
                    patch.object(check_motor_pid.time, 'monotonic', side_effect=lambda: fake.host), \
                    redirect_stdout(io.StringIO()):
                if fault:
                    with self.assertRaisesRegex(RuntimeError, 'coast'):
                        check_motor_pid.main()
                    self.assertEqual(len(list(Path('logs/motor-bench').glob('*.crash.txt'))), 1)
                else:
                    self.assertEqual(check_motor_pid.main(), 0)
                    self.assertGreaterEqual(fake.t - fake.start, 30000)

    def test_ignored_host_stop_has_shutdown_deadline_not_a_run_cap(self):
        fake = SerialTranscript()
        with tempfile.TemporaryDirectory() as directory, chdir(directory):
            stop = Path(directory) / 'stop.request'
            original_write = fake.write

            def write(command):
                if command == b'STOP\n' and fake.phase == 'BOTH':
                    return len(command)  # Transport accepted it, firmware ignored it.
                result = original_write(command)
                if command == b'PID 45\n':
                    stop.touch()
                return result

            with patch.object(fake, 'write', side_effect=write), \
                    patch.object(sys, 'argv', ['check_motor_pid', '--port', 'FAKE', '--run', '--stop-file', str(stop)]), \
                    patch.object(check_motor_pid.serial, 'Serial', return_value=fake), \
                    patch.object(check_motor_pid.time, 'monotonic', side_effect=lambda: fake.host), \
                    redirect_stdout(io.StringIO()):
                with self.assertRaisesRegex(RuntimeError, 'STOP'):
                    check_motor_pid.main()
                self.assertLess(fake.t - fake.start, 30000)

    def test_background_launcher_failure_requests_stop(self):
        source = Path(__file__).resolve().parents[1] / 'bringup/motor_test/start.py'
        spec = importlib.util.spec_from_file_location('motor_start', source)
        launcher = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(launcher)
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(launcher, '__file__', str(Path(directory) / 'bringup/motor_test/start.py')), \
                patch.object(sys, 'argv', ['start', '--port', 'FAKE', '--run']), \
                patch.object(launcher.subprocess, 'Popen') as spawn:
            spawn.return_value.pid = 1234
            spawn.return_value.poll.side_effect = RuntimeError('monitor failed')
            with self.assertRaisesRegex(RuntimeError, 'monitor failed'):
                launcher.main()
            self.assertEqual(len(list(Path(directory).glob('logs/motor-bench/continuous-*/stop.request'))), 1)
            spawn.return_value.wait.assert_called_once_with(timeout=12)

    def test_windows_state_file_reader_lock_is_retried(self):
        fake = SerialTranscript()
        replace = Path.replace
        failures = 2

        def locked(path, target):
            nonlocal failures
            if failures:
                failures -= 1
                raise PermissionError('Windows reader temporarily denies delete sharing')
            return replace(path, target)

        with tempfile.TemporaryDirectory() as directory, chdir(directory), \
                patch.object(sys, 'argv', ['check_motor_pid', '--port', 'FAKE', '--run', '--state-file', 'state.json']), \
                patch.object(check_motor_pid.serial, 'Serial', return_value=fake), \
                patch.object(check_motor_pid.time, 'monotonic', side_effect=lambda: fake.host), \
                patch.object(Path, 'replace', locked), redirect_stdout(io.StringIO()):
            self.assertEqual(check_motor_pid.main(), 0)
            self.assertEqual(failures, 0)

    def test_cli_without_run_does_not_open_hardware(self):
        proc = subprocess.run([sys.executable, str(Path(__file__).with_name('check_motor_pid.py')),
                               '--port', 'NOT_A_REAL_PORT', '--rpm', '45'],
                              capture_output=True, text=True, timeout=10)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn('PLAN ONLY', proc.stdout)

    def test_both_wheels_at_target_with_1320_count_calibration(self):
        result = summarize_pid(trial(), 45)
        self.assertEqual(result['verdict'], 'AT_TARGET')
        self.assertEqual(result['average_rpm'], 45)
        self.assertEqual(result['left_rpm'], 45)
        self.assertEqual(result['right_rpm'], 45)

    def test_target_miss_is_a_failed_verdict(self):
        samples = [replace(s, left=s.left * 2, right=s.right * 2) for s in trial()]
        self.assertEqual(summarize_pid(samples, 45)['verdict'], 'OFF_TARGET')

    def test_early_stop_fault_time_reset_and_wrong_stage_are_errors(self):
        for samples in (trial()[:-11] + trial()[-1:],
                        trial()[:-1] + [replace(trial()[-1], fault=1)],
                        trial()[:10] + trial()[9:],
                        [replace(s, stage='HOLD') if s.stage == 'PID' else s for s in trial()]):
            with self.subTest(samples=samples[-1]):
                with self.assertRaises(RuntimeError):
                    summarize_pid(samples, 45)

    def test_one_wheel_cannot_hide_behind_correct_average(self):
        samples = [replace(s, left=s.left // 2, right=s.right * 3 // 2) for s in trial()]
        self.assertEqual(summarize_pid(samples, 45)['verdict'], 'OFF_TARGET')

    def test_fractional_duty_telemetry_and_cap(self):
        frame = parse_pid('PID t_ms=2000 target=45 left_mrpm=43000 right_mrpm=47000 avg_mrpm=45000 '
                          'left_mduty=45500 right_mduty=44200 p=0 i=350 d=-100 trim=650')
        self.assertEqual(frame['left_mduty'], 45500)
        validate_pid(frame, 45)
        validate_pid({**frame, 'right_mduty': 100000}, 45)
        with self.assertRaises(RuntimeError):
            validate_pid({**frame, 'right_mduty': 39999}, 45)
        with self.assertRaises(RuntimeError):
            validate_pid({**frame, 'right_mduty': 100001}, 45)
        with self.assertRaises(RuntimeError):
            validate_pid(frame, 60)
        self.assertIsNone(parse_pid('PID t_ms=2000 target=45'))


if __name__ == '__main__':
    unittest.main()
