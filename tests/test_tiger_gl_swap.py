#!/usr/bin/env python3
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
NAMES=['RadeonNIGLDriver'+x for x in ('','1','2','3')]


class GLSwap(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.pkg=self.root/'package';self.ext=self.root/'Extensions';self.ext.mkdir();self.backup=self.root/'Backup'
        for n in NAMES:
            for kind in ('normal','trial'):
                p=self.pkg/kind/n;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((kind+n).encode())
            p=self.ext/(n+'.bundle')/'Contents/MacOS'/n;p.parent.mkdir(parents=True);p.write_bytes(('normal'+n).encode())
    def tearDown(self):self.tmp.cleanup()
    def call(self,op):
        code='. "$1"; '+op+' "$2" "$3" "$4" -'
        return subprocess.run(['/bin/sh','-c',code,'test',str(ROOT/'g5/tiger-gl-swap-core.sh'),str(self.pkg),str(self.ext),str(self.backup)],stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode
    def target(self,n):return self.ext/(n+'.bundle')/'Contents/MacOS'/n
    def test_install_restore(self):
        self.assertEqual(self.call('rdn_gl_install'),0)
        self.assertTrue(all(self.target(n).read_bytes()==('trial'+n).encode() for n in NAMES))
        self.assertEqual(self.call('rdn_gl_restore'),0)
        self.assertTrue(all(self.target(n).read_bytes()==('normal'+n).encode() for n in NAMES))
        self.assertTrue(self.backup.exists())
    def test_preexisting_change_refuses_install(self):
        self.target(NAMES[1]).write_bytes(b'other')
        self.assertNotEqual(self.call('rdn_gl_install'),0)
        self.assertFalse(self.backup.exists())
        self.assertEqual(self.target(NAMES[1]).read_bytes(),b'other')
    def test_changed_file_refuses_restore_without_modification(self):
        self.assertEqual(self.call('rdn_gl_install'),0)
        self.target(NAMES[2]).write_bytes(b'other')
        self.assertNotEqual(self.call('rdn_gl_restore'),0)
        self.assertEqual(self.target(NAMES[0]).read_bytes(),('trial'+NAMES[0]).encode())
    def test_partial_install_and_missing_file_restore(self):
        self.assertEqual(self.call('rdn_gl_install'),0)
        self.target(NAMES[0]).write_bytes(('normal'+NAMES[0]).encode())
        self.target(NAMES[1]).unlink()
        self.assertEqual(self.call('rdn_gl_restore'),0)
        self.assertTrue(all(self.target(n).read_bytes()==('normal'+n).encode() for n in NAMES))
    def test_symlink_rejected(self):
        p=self.target(NAMES[0]);p.unlink();os.symlink(self.pkg/'normal'/NAMES[0],p)
        self.assertNotEqual(self.call('rdn_gl_install'),0)
        self.assertFalse(self.backup.exists())

if __name__=='__main__':unittest.main()
