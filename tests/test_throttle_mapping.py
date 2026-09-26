"""Run the production C pedal mapper's behavioral tests without hardware."""
from pathlib import Path
import shutil
import subprocess
import unittest


class ThrottleMappingTests(unittest.TestCase):
    # Compile the real mapper, then exercise its public raw-pedal interface.
    def test_c_mapping_contract(self):
        repo = Path(__file__).resolve().parents[1]
        compiler = shutil.which('gcc')
        if compiler is None:
            installed = Path('C:/msys64/mingw64/bin/gcc.exe')
            if installed.is_file():
                compiler = str(installed)
            else:
                self.skipTest('A host C compiler is required for pedal-mapping tests')
        build = repo / 'build/throttle-mapping-host'
        logs = repo / 'logs/throttle-mapping'
        build.mkdir(parents=True, exist_ok=True)
        logs.mkdir(parents=True, exist_ok=True)
        executable = build / 'test.exe'
        commands = [
            ('host-build', [compiler, '-std=c11', '-Wall', '-Wextra', '-Werror',
                            '-Istm32_zephyr/src', 'tests/test_throttle_mapping.c',
                            'stm32_zephyr/src/throttle_mapping.c', '-o', str(executable)]),
            ('host-test', [str(executable)]),
        ]
        for name, command in commands:
            result = subprocess.run(command, cwd=repo, capture_output=True, text=True, timeout=30)
            output = result.stdout + result.stderr
            (logs / (name + '.log')).write_text(output, encoding='utf-8')
            self.assertEqual(result.returncode, 0, output)


if __name__ == '__main__':
    unittest.main()
