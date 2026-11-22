"""Exercise range planning under memory and undefined-behavior sanitizers."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SnapshotPlanTest(unittest.TestCase):
    def test_guarded_quiesce(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'quiesce-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/quiesce_model.c'), str(ROOT / 'hw/rdn_quiesce.c'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_range_validation_and_image_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'snapshot-plan-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/snapshot_plan.c'),
                            str(ROOT / 'hw/rdn_snapshot_plan.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_transfer_lifetime_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'snapshot-transfer-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/snapshot_transfer.c'),
                            str(ROOT / 'hw/rdn_snapshot_transfer.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_callback_copy_lifecycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'sleep-copy-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/sleep_copy.c'), str(ROOT / 'hw/rdn_sleep_copy.c'),
                            str(ROOT / 'hw/rdn_snapshot_transfer.c'),
                            str(ROOT / 'hw/rdn_sleep_staging.c'), str(ROOT / 'hw/rdn_quiesce.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_staging_mapping_lifetime(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'sleep-staging-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/sleep_staging.c'), str(ROOT / 'hw/rdn_sleep_staging.c'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_simulated_hidden_copy_pipeline(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'sleep-pipeline-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/sleep_pipeline.c'), str(ROOT / 'hw/rdn_sleep_staging.c'),
                            str(ROOT / 'hw/rdn_sleep_copy.c'), str(ROOT / 'hw/rdn_snapshot_transfer.c'),
                            str(ROOT / 'hw/rdn_sleep_dma.c'), str(ROOT / 'hw/rdn_cp_dma_readback.c'), str(ROOT / 'hw/rdn_quiesce.c'),
                            '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

    def test_private_allocations_and_rollback(self):
        with tempfile.TemporaryDirectory() as tmp:
            binary = Path(tmp) / 'sleep-private-test'
            subprocess.run(['clang', '-std=c99', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-I' + str(ROOT / 'hw'),
                            str(ROOT / 'tests/sleep_private.c'), str(ROOT / 'hw/rdn_sleep_private.c'),
                            str(ROOT / 'hw/rdn_mem.c'), str(ROOT / 'hw/rdn_sleep_dma.c'),
                            str(ROOT / 'hw/rdn_cp_dma_readback.c'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)


if __name__ == '__main__':
    unittest.main()
