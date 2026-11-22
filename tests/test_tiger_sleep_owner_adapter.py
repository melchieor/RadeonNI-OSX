from pathlib import Path
import platform
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TigerSleepOwnerAdapterTest(unittest.TestCase):
    def test_descriptor_lifetime(self):
        with tempfile.TemporaryDirectory() as tmp:
            obj = Path(tmp) / 'owner.o'
            exe = Path(tmp) / 'owner-test'
            flags = ['-fsanitize=address,undefined', '-ffunction-sections', '-fdata-sections',
                     '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1', '-I' + str(ROOT/'hw')]
            subprocess.run(['clang', '-std=c99'] + flags + ['-c', str(ROOT/'hw/rdn_sleep_owner.c'), '-o', str(obj)], check=True)
            strip = '-Wl,-dead_strip' if platform.system() == 'Darwin' else '-Wl,--gc-sections'
            sources = ['tests/tiger_sleep_owner_adapter.cpp', 'kext/RadeonNI/RadeonNITigerSleepOwner.cpp',
                       'kext/RadeonNI/RadeonNITigerSleepStage.cpp']
            subprocess.run(['clang++', '-std=c++11', '-I' + str(ROOT/'tests/tiger_owner_mocks')] + flags +
                           [str(ROOT/s) for s in sources] + [str(obj), strip, '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
