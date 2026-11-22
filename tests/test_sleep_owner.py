from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepOwnerTest(unittest.TestCase):
    def test_client_close_retirement_and_quarantine(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-owner'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-I'+str(ROOT/'hw'), str(ROOT/'tests/sleep_owner.c'),
                            str(ROOT/'hw/rdn_sleep_owner.c'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
