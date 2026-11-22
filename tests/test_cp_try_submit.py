"""Exercise production nonblocking CP publication and gate behavior."""
from pathlib import Path
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CpTrySubmitTest(unittest.TestCase):
    def test_publication_and_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'cp-try-submit'
            strip = '-Wl,-dead_strip' if platform.system() == 'Darwin' else '-Wl,--gc-sections'
            subprocess.run(['clang', '-std=c99', '-O1', '-Wall', '-Wextra',
                            '-Wno-unused-parameter', '-fsanitize=address',
                            '-ffunction-sections', '-fdata-sections', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/cp_try_submit.c'), str(ROOT / 'hw/rdn_cp.c'),
                            strip, '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_experimental_internal_admission(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'cp-try-internal'
            strip = '-Wl,-dead_strip' if platform.system() == 'Darwin' else '-Wl,--gc-sections'
            subprocess.run(['clang', '-std=c99', '-O1', '-Wall', '-Wextra',
                            '-Wno-unused-parameter', '-fsanitize=address',
                            '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-ffunction-sections', '-fdata-sections', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/cp_try_submit.c'), str(ROOT / 'hw/rdn_cp.c'),
                            str(ROOT / 'hw/rdn_sleep_copy.c'), str(ROOT / 'hw/rdn_snapshot_transfer.c'),
                            str(ROOT / 'hw/rdn_sleep_staging.c'),
                            str(ROOT / 'hw/rdn_quiesce.c'),
                            strip, '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
