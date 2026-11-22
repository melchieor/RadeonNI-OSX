#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class FanRecovery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.ext = self.root/'Extensions'
        self.ext.mkdir()
        self.normal = self.make_bundle(self.root/'normal', b'old')
        self.trial = self.make_bundle(self.root/'trial', b'new')
        self.installed = self.make_bundle(self.ext/'RadeonNI.kext', b'old')
        self.backup = self.root/'backup'

    def tearDown(self): self.temp.cleanup()

    def make_bundle(self, path, contents):
        (path/'Contents/MacOS').mkdir(parents=True)
        (path/'Contents/Info.plist').write_bytes(contents)
        (path/'Contents/MacOS/RadeonNI').write_bytes(contents)
        return path

    def call(self, operation):
        cmd = '. "$1"; . "$2"; '+operation+' "$3" "$4" "$5" "$6" -'
        return subprocess.run(['/bin/sh','-c',cmd,'test',str(ROOT/'g5/tiger-framebuffer-core.sh'),
            str(ROOT/'g5/tiger-fan-trial-core.sh'),str(self.normal),str(self.trial),str(self.ext),str(self.backup)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode

    def test_install_restore_and_backup_preservation(self):
        self.assertEqual(self.call('rdn_fan_install'),0)
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'new')
        self.assertEqual((self.backup/'RadeonNI.kext/Contents/Info.plist').read_bytes(),b'old')
        self.assertEqual(self.call('rdn_fan_restore'),0)
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'old')
        self.assertTrue(self.backup.exists())

    def test_changed_baseline_or_existing_backup_prevents_install(self):
        (self.installed/'Contents/Info.plist').write_bytes(b'user data')
        self.assertNotEqual(self.call('rdn_fan_install'),0)
        self.assertFalse(self.backup.exists())
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'user data')

    def test_modified_trial_not_removed_and_corrupt_backup_not_restored(self):
        self.assertEqual(self.call('rdn_fan_install'),0)
        (self.installed/'Contents/Info.plist').write_bytes(b'changed')
        self.assertNotEqual(self.call('rdn_fan_restore'),0)
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'changed')
        (self.installed/'Contents/Info.plist').write_bytes(b'new')
        (self.backup/'RadeonNI.kext/Contents/Info.plist').write_bytes(b'broken')
        self.assertNotEqual(self.call('rdn_fan_restore'),0)
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'new')

    def test_restore_when_target_absent(self):
        self.assertEqual(self.call('rdn_fan_install'),0)
        import shutil
        shutil.rmtree(self.installed)
        self.assertEqual(self.call('rdn_fan_restore'),0)
        self.assertEqual((self.installed/'Contents/Info.plist').read_bytes(),b'old')

    def test_symlink_trial_rejected(self):
        os.symlink(self.normal/'Contents/Info.plist',self.trial/'link')
        self.assertNotEqual(self.call('rdn_fan_install'),0)
        self.assertFalse(self.backup.exists())


if __name__ == '__main__': unittest.main()
