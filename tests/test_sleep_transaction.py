from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepTransactionTest(unittest.TestCase):
    def test_private_transaction_with_simulated_callbacks(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-transaction'
            sources = ['tests/sleep_transaction.c', 'hw/rdn_sleep_transaction.c',
                       'hw/rdn_sleep_private.c', 'hw/rdn_sleep_dma.c', 'hw/rdn_mem.c',
                       'hw/rdn_cp_dma_readback.c', 'hw/rdn_sleep_runtime.c',
                       'hw/rdn_sleep_copy.c', 'hw/rdn_sleep_staging.c',
                       'hw/rdn_snapshot_transfer.c', 'hw/rdn_quiesce.c']
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-I'+str(ROOT/'hw')] + [str(ROOT/s) for s in sources] + ['-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
