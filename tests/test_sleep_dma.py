from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepDmaTest(unittest.TestCase):
    def test_command_preparation(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-dma-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT/'hw'),
                            str(ROOT/'tests/sleep_dma.c'), str(ROOT/'hw/rdn_sleep_dma.c'),
                            str(ROOT/'hw/rdn_cp_dma_readback.c'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
