#!/usr/bin/env python3
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
NAMES=['RadeonNI.kext','RadeonNIGA.plugin']+['RadeonNIGLDriver'+s+'.bundle' for s in ('','1','2','3')]


class PackageRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.payload=self.root/'payload';self.ext=self.root/'Extensions';self.ext.mkdir();self.backup=self.root/'backup'
        for n in NAMES:
            p=self.payload/n/'Contents/MacOS';p.mkdir(parents=True)
            (p/'RadeonNI' if n=='RadeonNI.kext' else p/'binary').write_bytes(n.encode())
            (p.parent/'Info.plist').write_bytes(n.encode())
        (self.ext/'Unrelated.kext').write_bytes(b'keep')
    def tearDown(self):self.tmp.cleanup()
    def call(self,action):
        sources='. "$1"; . "$2"; . "$3"; '
        args=['/bin/sh','-c',sources+action,'fixture',str(ROOT/'g5/tiger-framebuffer-core.sh'),
              str(ROOT/'g5/tiger-graphics-core.sh'),str(ROOT/'g5/tiger-complete-core.sh'),str(self.payload),
              str(self.ext),str(self.backup)]
        return subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode
    def install(self):return self.call('rdn_complete_install "$4" "$5" "$6" - test-id')
    def remove(self):return self.call('rdn_complete_remove "$4" "$5" "$6" test-id')
    def verify(self):return self.call('rdn_complete_verify_installed "$4" "$5"')
    def test_fresh_install_verify_remove(self):
        self.assertEqual(self.install(),0);self.assertEqual(self.verify(),0);self.assertEqual(self.remove(),0)
        self.assertTrue(all(not (self.ext/n).exists() for n in NAMES))
        self.assertEqual((self.ext/'Unrelated.kext').read_bytes(),b'keep')
    def test_existing_bundle_refuses_all_changes(self):
        (self.ext/NAMES[-1]).mkdir();self.assertNotEqual(self.install(),0)
        self.assertFalse(self.backup.exists());self.assertFalse((self.ext/NAMES[0]).exists())
    def test_changed_bundle_refuses_all_removal(self):
        self.assertEqual(self.install(),0)
        (self.ext/NAMES[-1]/'Contents/Info.plist').write_bytes(b'changed')
        self.assertNotEqual(self.remove(),0);self.assertTrue((self.ext/NAMES[0]).exists())
    def test_partial_install_recovery(self):
        self.assertEqual(self.install(),0);shutil.rmtree(self.ext/NAMES[2])
        self.assertEqual(self.remove(),0);self.assertFalse((self.ext/NAMES[0]).exists())
    def test_wrong_marker_and_symlink_refuse_removal(self):
        self.assertEqual(self.install(),0)
        (self.backup/'fresh-install-id').write_text('wrong\n');self.assertNotEqual(self.remove(),0)
        (self.backup/'fresh-install-id').write_text('test-id\n')
        (self.ext/NAMES[0]/'link').symlink_to(self.root/'Unrelated')
        self.assertNotEqual(self.remove(),0);self.assertTrue((self.ext/NAMES[0]).exists())

if __name__=='__main__':unittest.main()
