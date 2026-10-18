"""Exercise the measurement console parser through its CLI, using synthetic firmware records."""
import csv
import json
from pathlib import Path
import subprocess
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PARSER = ROOT / 'lab3_wcet_baseline/lab3_wcet_baseline/measurements/parse_stm32_console.py'


class MeasurementCliTests(unittest.TestCase):
    def test_named_task_records_keep_counts_raw_cycles_and_zone(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'console.log'
            out = Path(directory) / 'tasks.csv'
            log.write_text('Booting\nOBS_TASK zone=N2 uptime_ms=5000 name=hb_tx max_cycles=85 max_us=2 count=250\n'
                           'OBS_TASK zone=N2 uptime_ms=5000 name=pid max_cycles=0 max_us=0 count=0\n', encoding='utf-8')
            run = subprocess.run([sys.executable, str(PARSER), str(log), '--tasks', '--out', str(out)],
                                 capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            with out.open(encoding='utf-8', newline='') as file:
                rows = list(csv.DictReader(file))
            self.assertEqual(rows, [
                dict(zone='N2', uptime_ms='5000', task='hb_tx', max_cycles='85', max_us='2', count='250'),
                dict(zone='N2', uptime_ms='5000', task='pid', max_cycles='0', max_us='0', count='0'),
            ])

    def test_firmware_accumulator_to_csv(self):
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host gcc is required for the real C accumulator test')
        source = ROOT / 'lab3_wcet_baseline/lab3_wcet_baseline/stm32_zephyr/src'
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'timing_test.exe'
            build = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                                    '-I'+str(ROOT/'tests/lab3_timing_fake'), '-I'+str(source),
                                    str(ROOT/'tests/test_lab3_timing.c'), str(source/'timing_stats.c'),
                                    '-o', str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)
            log = Path(directory) / 'console.log'
            log.write_text(run.stdout, encoding='utf-8')
            out = Path(directory) / 'out.csv'
            parse = subprocess.run([sys.executable, str(PARSER), str(log), '--tasks', '--out', str(out)],
                                   capture_output=True, text=True, timeout=10)
            self.assertEqual(parse.returncode, 0, parse.stderr)
            with out.open(encoding='utf-8', newline='') as file:
                self.assertEqual(list(csv.DictReader(file)), [dict(zone='N2', uptime_ms='5000',
                    task='force_tx', max_cycles='84', max_us='1', count='1')])

    def test_probe_command_selects_only_available_task_and_preserves_counters(self):
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host gcc is required for the probe command test')
        source = ROOT / 'lab3_wcet_baseline/lab3_wcet_baseline/stm32_zephyr/src'
        for zone in ('N2', 'N3'):
            with self.subTest(zone=zone), tempfile.TemporaryDirectory() as directory:
                executable = Path(directory) / 'probe_test.exe'
                build = subprocess.run([compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                    '-DCONFIG_LAB3_ZONE_'+zone, '-I'+str(ROOT/'tests/lab3_timing_fake'), '-I'+str(source),
                    str(ROOT/'tests/test_lab3_probe.c'), str(source/'timing_stats.c'), str(source/'timing_probe.c'),
                    '-o', str(executable)], capture_output=True, text=True, timeout=30)
                self.assertEqual(build.returncode, 0, build.stderr)
                run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
                self.assertEqual(run.returncode, 0, run.stderr)

    def test_pid_workload_runs_real_lab2_calculation_and_publishes_changing_output(self):
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host gcc is required for the PID workload test')
        source = ROOT / 'lab3_wcet_baseline/lab3_wcet_baseline/stm32_zephyr/src'
        lab2 = ROOT / 'bringup/motor_test/src'
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'pid_test.exe'
            build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-I'+str(source), '-I'+str(lab2), str(ROOT/'tests/test_lab3_pid.c'),
                str(source/'pid_measurement.c'), str(lab2/'velocity_control.c'), '-lm',
                '-o', str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_steering_uses_lab2_mapping_and_tracked_calibration(self):
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host gcc is required for the steering workload test')
        source = ROOT / 'lab3_wcet_baseline/lab3_wcet_baseline/stm32_zephyr/src'
        lab2 = ROOT / 'stm32_zephyr/src'
        calibration = json.loads((ROOT/'config/servo_calibration.json').read_text(encoding='utf-8'))
        with tempfile.TemporaryDirectory() as directory:
            generated = Path(directory) / 'servo_calibration.h'
            generated.write_text('\n'.join(f'#define SERVO_DEFAULT_{point.upper()}_US {calibration[point+"_us"]}'
                                           for point in ('left', 'center', 'right')), encoding='utf-8')
            executable = Path(directory) / 'steering_test.exe'
            build = subprocess.run([compiler, '-std=c11', '-O2', '-Wall', '-Wextra', '-Werror',
                '-I'+directory, '-I'+str(source), '-I'+str(lab2),
                str(ROOT/'tests/test_lab3_steering.c'), str(source/'steering_measurement.c'),
                str(lab2/'servo_core.c'), '-o', str(executable)], capture_output=True, text=True, timeout=30)
            self.assertEqual(build.returncode, 0, build.stderr)
            run = subprocess.run([str(executable)], capture_output=True, text=True, timeout=10)
            self.assertEqual(run.returncode, 0, run.stderr)

    def test_truncated_task_record_is_an_error_not_a_silent_gap(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / 'console.log'
            log.write_text('OBS_TASK zone=N3 uptime_ms=5000 name=drive max_cycles=85 max_us=2 count=250\n'
                           'OBS_TASK zone=N3 uptime_ms=10000 name=drive max_cycles=\n', encoding='utf-8')
            run = subprocess.run([sys.executable, str(PARSER), str(log), '--tasks', '--out', str(Path(directory)/'out.csv')],
                                 capture_output=True, text=True, timeout=10)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn('Malformed OBS_TASK at line 2', run.stderr)


if __name__ == '__main__':
    unittest.main()
