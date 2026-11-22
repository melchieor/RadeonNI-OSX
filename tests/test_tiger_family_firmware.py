#!/usr/bin/env python3
import hashlib
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/stage-tiger-family-firmware.py'
spec = importlib.util.spec_from_file_location('tiger_firmware', path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FirmwareValidation(unittest.TestCase):
    def setUp(self):
        self.files = {'CAYMAN_me.bin': b'one', 'TURKS_me.bin': b'two'}
        self.expected = {k: (hashlib.sha256(v).hexdigest(), len(v)) for k, v in self.files.items()}

    def test_good(self):
        module.validate(self.files, self.expected)

    def test_reject_missing_and_extra(self):
        for files in ({'CAYMAN_me.bin': b'one'}, dict(self.files, extra=b'x')):
            with self.assertRaises(ValueError):
                module.validate(files, self.expected)

    def test_reject_corruption_and_swapped_families(self):
        for files in ({'CAYMAN_me.bin': b'bad', 'TURKS_me.bin': b'two'},
                      {'CAYMAN_me.bin': b'two', 'TURKS_me.bin': b'one'}):
            with self.assertRaises(ValueError):
                module.validate(files, self.expected)


if __name__ == '__main__':
    unittest.main()
