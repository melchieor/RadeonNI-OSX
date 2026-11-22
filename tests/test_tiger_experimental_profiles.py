#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import plistlib
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('tiger_profiles', root / 'scripts/configure-tiger-experimental-profiles.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


@unittest.skipUnless(module.firmware.DESTINATION.is_dir(), 'verified firmware staging is not present')
class ProfileChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.payloads = {n: (module.firmware.DESTINATION / n).read_bytes() for n in module.firmware.INPUTS}
        with (root / 'kext/RadeonNI/Info.plist').open('rb') as stream:
            cls.template = plistlib.load(stream)

    def test_profiles_are_exactly_scoped_and_family_specific(self):
        for fan in (False, True):
            profiles = module.profiles(self.template, self.payloads, fan)['IOKitPersonalities']
            self.assertEqual(set(profiles), {'RadeonNI-TURKS', 'RadeonNI-CAYMAN'})
            for family, pci in (('TURKS', '0x675d1002'), ('CAYMAN', '0x67041002')):
                profile = profiles['RadeonNI-' + family]
                self.assertEqual(profile['IOPCIMatch'], pci)
                self.assertEqual(profile['FirmwareFamily'], family)
                for kind in ('PFP', 'ME', 'MC', 'RLC', 'SMC'):
                    name = family + '_' + kind.lower() + '.bin'
                    if name in self.payloads:
                        self.assertEqual(profile['FW_' + kind], self.payloads[name])
                    else:
                        self.assertNotIn('FW_' + kind, profile)
                self.assertEqual(profile.get('TemperatureFanControl', False), fan and family == 'CAYMAN')

    def test_profiles_reject_bad_firmware_before_use(self):
        for changed in ('CAYMAN_pfp.bin', 'TURKS_mc.bin'):
            corrupt = dict(self.payloads)
            corrupt[changed] = b'bad'
            with self.assertRaises(ValueError):
                module.profiles(self.template, corrupt)


if __name__ == '__main__':
    unittest.main()
