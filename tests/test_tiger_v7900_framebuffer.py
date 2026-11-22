#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import plistlib
import unittest

root = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('profile', root / 'scripts/configure-tiger-v7900-framebuffer.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class FramebufferProfile(unittest.TestCase):
    def test_scope_and_features(self):
        with (root / 'kext/RadeonNI/Info.plist').open('rb') as f:
            template = plistlib.load(f)
        personalities = module.profile(template)['IOKitPersonalities']
        self.assertEqual(list(personalities), ['RadeonNI-V7900-Framebuffer'])
        entry = personalities['RadeonNI-V7900-Framebuffer']
        self.assertEqual(entry['IOPCIMatch'], '0x67041002')
        for key in ('Accelerator', 'Surfaces', 'GAPlugin', 'HWCursor', 'TemperatureFanControl', 'MultiHead'):
            self.assertIs(entry[key], False)
        self.assertFalse(any(key.startswith('FW_') for key in entry))


if __name__ == '__main__':
    unittest.main()
