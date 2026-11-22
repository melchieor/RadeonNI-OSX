from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class TigerSleepBufferTest(unittest.TestCase):
    def test_buffer_guards_and_private_readback(self):
        with tempfile.TemporaryDirectory() as tmp:
            exe = Path(tmp) / 'tiger-sleep-buffer'
            subprocess.run(['clang++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-fsanitize=address,undefined', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-I'+str(ROOT/'tests/tiger_stage_mocks'), '-I'+str(ROOT/'hw'),
                            str(ROOT/'tests/tiger_sleep_buffer.cpp'),
                            str(ROOT/'kext/RadeonNI/RadeonNITigerSleepBuffer.cpp'), '-o', str(exe)], check=True)
            subprocess.run([str(exe)], check=True)


if __name__ == '__main__':
    unittest.main()
