import pathlib
import subprocess
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]

class PhysicalProbeTests(unittest.TestCase):
    def test_lifetime_and_failure_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            binary = pathlib.Path(directory) / 'physical_probe'
            subprocess.run(['c++', '-std=c++11', '-Wall', '-Wextra', '-Werror',
                            '-DRDN_PHYSICAL_PROBE_TEST',
                            '-I' + str(ROOT / 'tests/physical_probe_mocks'),
                            '-I' + str(ROOT / 'kext/RadeonNI'),
                            str(ROOT / 'kext/RadeonNI/RadeonNITigerPhysicalProbe.cpp'),
                            str(ROOT / 'tests/tiger_physical_probe.cpp'), '-o', str(binary)], check=True)
            subprocess.run([str(binary)], check=True)

if __name__ == '__main__':
    unittest.main()
