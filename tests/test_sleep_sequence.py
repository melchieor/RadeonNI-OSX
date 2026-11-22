from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepSequenceTest(unittest.TestCase):
    def test_ordered_guarded_test_sequence(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-sequence'
            sources = ['tests/sleep_sequence.c', 'hw/rdn_sleep_sequence.c', 'hw/rdn_sleep_guarded.c',
                       'hw/rdn_sleep_dma.c', 'hw/rdn_cp_dma_readback.c', 'hw/rdn_mem.c']
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I'+str(ROOT/'hw')] +
                           [str(ROOT/s) for s in sources] + ['-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
