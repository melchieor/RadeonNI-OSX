"""Check the target-specific PPC descriptor audit rejects altered binaries."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from leopard_kext_abi import object_data


class TargetDescriptorAbiTest(unittest.TestCase):
    def test_matching_kernel_and_wrong_slot(self):
        kernel = ROOT/'build/tiger-v7900/g5-readonly-audit/mach_kernel-8S165'
        base = ROOT/'build/tiger-v7900/sleep-link-probe-retirement-admission-20261115/kernel'
        if not kernel.exists() or not (base/'RadeonNITigerSleepBuffer.o').exists():
            self.skipTest('G5 read-only kernel and experimental build not available')
        script = ROOT/'scripts/check-tiger-target-descriptor-abi.py'
        def run(path):
            return subprocess.run([sys.executable, str(script), '--kernel', str(path),
                                   '--object', str(base/'RadeonNITigerSleepBuffer.o'),
                                   '--stage-object', str(base/'RadeonNITigerSleepStage.o')],
                                  capture_output=True, text=True)
        self.assertEqual(run(kernel).returncode, 0)
        data, sections, symbols = object_data(kernel)
        _, _, section, value = next(s for s in symbols if s[0] == '__ZTV24IOBufferMemoryDescriptor')
        address, _, offset, *_ = sections[section-1]
        modified = bytearray(data)
        modified[offset + value - address + 0xe0] ^= 1
        with tempfile.TemporaryDirectory() as tmp:
            bad = Path(tmp)/'bad-kernel'
            bad.write_bytes(modified)
            result = run(bad)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('slot 0xe0', result.stderr)


if __name__ == '__main__':
    unittest.main()
