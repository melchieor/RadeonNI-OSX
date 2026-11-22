from pathlib import Path
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SleepGartIntegrationTest(unittest.TestCase):
    def test_checked_gart_flush(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'gart-flush-model'
            strip = '-Wl,-dead_strip' if platform.system() == 'Darwin' else '-Wl,--gc-sections'
            sources = ['tests/cp_dma_readback_model.c', 'hw/rdn_cp_dma_readback.c', 'hw/rdn_gart.c']
            subprocess.run(['clang', '-std=c99', '-O1', '-include', 'errno.h',
                            '-fsanitize=address,undefined', '-ffunction-sections', '-fdata-sections',
                            '-I'+str(ROOT/'hw')] + [str(ROOT/s) for s in sources] +
                           [strip, '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)

    def test_guarded_copy_with_simulated_device(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'sleep-gart-integration'
            strip = '-Wl,-dead_strip' if platform.system() == 'Darwin' else '-Wl,--gc-sections'
            sources = ['tests/sleep_gart_integration.c', 'hw/rdn_cp.c', 'hw/rdn_sleep_transaction.c',
                       'hw/rdn_sleep_private.c', 'hw/rdn_sleep_dma.c', 'hw/rdn_mem.c',
                       'hw/rdn_cp_dma_readback.c', 'hw/rdn_sleep_runtime.c', 'hw/rdn_sleep_copy.c',
                       'hw/rdn_sleep_staging.c', 'hw/rdn_snapshot_transfer.c', 'hw/rdn_quiesce.c']
            subprocess.run(['clang', '-std=c99', '-O1', '-Wall', '-Wextra', '-Wno-unused-parameter',
                            '-fsanitize=address', '-ffunction-sections', '-fdata-sections',
                            '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1', '-I'+str(ROOT/'hw')] +
                           [str(ROOT/s) for s in sources] + [strip, '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
