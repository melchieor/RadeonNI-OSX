"""Exercise Tiger IOKit adapter with fake descriptors and GART callbacks."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TigerSleepStageTest(unittest.TestCase):
    def test_descriptor_and_mapping_lifetime(self):
        with tempfile.TemporaryDirectory() as tmp:
            objects = []
            exe = Path(tmp) / 'test'
            flags = ['-fsanitize=address,undefined', '-Wall', '-Wextra', '-Werror']
            for name in ('rdn_sleep_staging', 'rdn_sleep_copy', 'rdn_snapshot_transfer', 'rdn_quiesce'):
                obj = Path(tmp) / (name + '.o')
                subprocess.run(['clang', '-std=c99'] + flags + ['-I'+str(ROOT/'hw'), '-c',
                                str(ROOT/'hw'/f'{name}.c'), '-o', str(obj)], check=True)
                objects.append(str(obj))
            subprocess.run(['clang++', '-std=c++11'] + flags +
                           ['-I'+str(ROOT/'tests/tiger_stage_mocks'), '-I'+str(ROOT/'hw'),
                            str(ROOT/'tests/tiger_sleep_stage.cpp'),
                            str(ROOT/'kext/RadeonNI/RadeonNITigerSleepStage.cpp')] +
                           objects + ['-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
