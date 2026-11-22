from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepRuntimeTest(unittest.TestCase):
    def test_fence_and_cpu_visibility_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-runtime'
            files = ['tests/sleep_runtime.c', 'hw/rdn_sleep_runtime.c',
                     'hw/rdn_sleep_copy.c', 'hw/rdn_sleep_staging.c',
                     'hw/rdn_snapshot_transfer.c', 'hw/rdn_quiesce.c']
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-I'+str(ROOT/'hw')] + [str(ROOT/f) for f in files] + ['-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
