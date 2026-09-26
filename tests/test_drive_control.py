"""Host regressions for the production pedal/PID/stop policy and shared PID."""
from pathlib import Path
import shutil
import subprocess
import unittest


class DriveControlTests(unittest.TestCase):
    # Build the actual C implementation, not a Python model of the controller.
    def test_controller_contracts(self):
        repo = Path(__file__).resolve().parents[1]
        compiler = shutil.which('gcc')
        if compiler is None:
            installed = Path('C:/msys64/mingw64/bin/gcc.exe')
            if not installed.is_file():
                self.skipTest('Host GCC required for motor-controller tests')
            compiler = str(installed)
        build = repo / 'build/motor-integration-host'
        logs = repo / 'logs/motor-integration'
        build.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        cases = {
            'drive': ['tests/test_drive_control.c', 'stm32_zephyr/src/drive_control.c',
                      'stm32_zephyr/src/throttle_mapping.c'],
            'velocity': ['tests/test_velocity_control.c'],
            'bench': ['tests/test_motor_bench.c', 'bringup/motor_test/src/bench_control.c'],
        }
        for name, sources in cases.items():
            with self.subTest(name=name):
                executable = build / (name + '.exe')
                commands = [
                    [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                     '-Istm32_zephyr/src', '-Ibringup/motor_test/src', *sources,
                     'bringup/motor_test/src/velocity_control.c', '-o', str(executable)],
                    [str(executable)],
                ]
                for stage, command in enumerate(commands):
                    result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
                    output = result.stdout + result.stderr
                    (logs / f'{name}-{stage}.log').write_text(output, encoding='utf-8')
                    self.assertEqual(result.returncode, 0, output)


if __name__ == '__main__':
    unittest.main()
