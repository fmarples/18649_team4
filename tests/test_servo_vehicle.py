"""Compile and exercise the real servo/blinker controllers at their public APIs."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ServoVehicleTests(unittest.TestCase):
    def test_standalone_steering_contract(self):
        repo = Path(__file__).resolve().parents[1]
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host GCC required for steering controller tests')
        build = repo / 'build/servo-host'
        logs = repo / 'logs/steering-autonomous'
        build.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        executable = build / 'servo.exe'
        commands = [
            [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-Istm32_zephyr/src', 'tests/test_servo_vehicle.c',
             'stm32_zephyr/src/servo_core.c', 'stm32_zephyr/src/blinker_core.c',
             '-o', str(executable)],
            [str(executable)],
            [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-Itests/servo_fake', '-Istm32_zephyr/src',
             'tests/test_servo_service.c', 'stm32_zephyr/src/servo_bench.c',
             'stm32_zephyr/src/servo_core.c', '-o', str(build / 'service.exe')],
            [str(build / 'service.exe')],
        ]
        for stage, command in enumerate(commands):
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            (logs / f'host-{stage}.log').write_text(output, encoding='utf-8')
            self.assertEqual(result.returncode, 0, output)


if __name__ == '__main__':
    unittest.main()
