"""Compile the production current backend with an ADC hardware boundary double."""
from pathlib import Path
import shutil
import subprocess
import unittest


class CurrentBackendTests(unittest.TestCase):
    def test_acquired_current_contract(self):
        repo = Path(__file__).resolve().parents[1]
        compiler = shutil.which('gcc')
        if compiler is None:
            self.skipTest('Host GCC required for current ADC boundary tests')
        build = repo / 'build/current-host'
        logs = repo / 'logs/current-sense'
        build.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        executable = build / 'current.exe'
        calibration = []
        for channel in ('LEFT', 'RIGHT', 'SERVO'):
            calibration += [f'-DCONFIG_LAB_CURRENT_{channel}_ZERO_MV=2500',
                            f'-DCONFIG_LAB_CURRENT_{channel}_SENSITIVITY=185']
        commands = [
            [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
             '-Itests/current_adc_fake', '-Istm32_zephyr/src', *calibration,
             'tests/test_current_backend.c', 'stm32_zephyr/src/current_backend.c',
             'stm32_zephyr/src/current_cache.c', '-o', str(executable)],
            [str(executable)],
        ]
        for stage, command in enumerate(commands):
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            (logs / f'host-{stage}.log').write_text(output, encoding='utf-8')
            self.assertEqual(result.returncode, 0, output)


if __name__ == '__main__':
    unittest.main()
