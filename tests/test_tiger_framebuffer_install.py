#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / 'g5/tiger-framebuffer-core.sh'


class InstallRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.source = base / 'payload/RadeonNI.kext'
        self.extensions = base / 'Extensions'
        (self.source / 'Contents/MacOS').mkdir(parents=True)
        (self.source / 'Contents/Info.plist').write_bytes(b'profile')
        (self.source / 'Contents/MacOS/RadeonNI').write_bytes(b'kernel')
        self.extensions.mkdir()
        self.target = self.extensions / 'RadeonNI.kext'
        self.keep = self.extensions / 'Other.kext'
        self.keep.write_bytes(b'unrelated')

    def tearDown(self):
        self.temp.cleanup()

    def call(self, operation):
        cmd = '. "$1"; ' + operation + ' "$2" "$3" -'
        return subprocess.run(['/bin/sh', '-c', cmd, 'test', str(CORE), str(self.source), str(self.extensions)],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode

    def test_install_and_remove_preserve_unrelated(self):
        self.assertEqual(self.call('rdn_install'), 0)
        self.assertEqual((self.target / 'Contents/MacOS/RadeonNI').read_bytes(), b'kernel')
        self.assertEqual(self.call('rdn_remove'), 0)
        self.assertFalse(self.target.exists())
        self.assertEqual(self.keep.read_bytes(), b'unrelated')

    def test_refuses_to_overwrite_existing(self):
        self.target.mkdir()
        (self.target / 'valuable').write_bytes(b'old')
        self.assertNotEqual(self.call('rdn_install'), 0)
        self.assertEqual((self.target / 'valuable').read_bytes(), b'old')

    def test_refuses_modified_install(self):
        self.assertEqual(self.call('rdn_install'), 0)
        (self.target / 'Contents/Info.plist').write_bytes(b'changed')
        self.assertNotEqual(self.call('rdn_remove'), 0)
        self.assertEqual((self.target / 'Contents/Info.plist').read_bytes(), b'changed')

    def test_rejects_symlinks_and_extra_files(self):
        os.symlink(self.keep, self.source / 'link')
        self.assertNotEqual(self.call('rdn_install'), 0)
        (self.source / 'link').unlink()
        (self.source / 'extra').write_bytes(b'extra')
        self.assertNotEqual(self.call('rdn_install'), 0)
        self.assertFalse(self.target.exists())


if __name__ == '__main__':
    unittest.main()
