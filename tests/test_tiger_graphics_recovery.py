#!/usr/bin/env python3
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
NAMES=['RadeonNIGA.plugin']+['RadeonNIGLDriver'+x+'.bundle' for x in ('','1','2','3')]

class GraphicsRecovery(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.payload=self.root/'package';self.ext=self.root/'Extensions';self.ext.mkdir()
        self.bundle(self.payload/'normal/RadeonNI.kext',b'engine')
        self.bundle(self.payload/'trial/RadeonNI.kext',b'graphics')
        self.bundle(self.ext/'RadeonNI.kext',b'engine')
        for n in NAMES:self.bundle(self.payload/'trial'/n,n.encode())
        self.backup=self.root/'backup'

    def tearDown(self):self.temp.cleanup()

    def bundle(self,p,data):
        (p/'Contents/MacOS').mkdir(parents=True)
        (p/'Contents/Info.plist').write_bytes(data)
        (p/'Contents/MacOS'/('RadeonNI' if p.name=='RadeonNI.kext' else 'binary')).write_bytes(data)

    def call(self,op):
        cmd='. "$1"; . "$2"; '+op+' "$3" "$4" "$5" -'
        return subprocess.run(['/bin/sh','-c',cmd,'test',str(ROOT/'g5/tiger-framebuffer-core.sh'),
            str(ROOT/'g5/tiger-graphics-core.sh'),str(self.payload),str(self.ext),str(self.backup)],
            stdout=subprocess.PIPE,stderr=subprocess.PIPE).returncode

    def test_install_restore(self):
        self.assertEqual(self.call('rdn_graphics_install'),0)
        self.assertTrue(all((self.ext/n).is_dir() for n in NAMES))
        self.assertEqual(self.call('rdn_graphics_restore'),0)
        self.assertTrue(all(not (self.ext/n).exists() for n in NAMES))
        self.assertEqual((self.ext/'RadeonNI.kext/Contents/Info.plist').read_bytes(),b'engine')
        self.assertTrue(self.backup.exists())

    def test_existing_plugin_refuses_install(self):
        (self.ext/NAMES[0]).mkdir()
        self.assertNotEqual(self.call('rdn_graphics_install'),0)
        self.assertFalse(self.backup.exists())
        self.assertEqual((self.ext/'RadeonNI.kext/Contents/Info.plist').read_bytes(),b'engine')

    def test_modified_plugin_refuses_all_restore_changes(self):
        self.assertEqual(self.call('rdn_graphics_install'),0)
        (self.ext/NAMES[1]/'Contents/Info.plist').write_bytes(b'modified')
        self.assertNotEqual(self.call('rdn_graphics_restore'),0)
        self.assertEqual((self.ext/'RadeonNI.kext/Contents/Info.plist').read_bytes(),b'graphics')
        self.assertTrue((self.ext/NAMES[0]).exists())

    def test_partial_install_recovers(self):
        self.assertEqual(self.call('rdn_graphics_install'),0)
        shutil.rmtree(self.ext/NAMES[0]);shutil.rmtree(self.ext/'RadeonNI.kext')
        self.assertEqual(self.call('rdn_graphics_restore'),0)
        self.assertEqual((self.ext/'RadeonNI.kext/Contents/Info.plist').read_bytes(),b'engine')

    def test_corrupt_backup_refuses_restore(self):
        self.assertEqual(self.call('rdn_graphics_install'),0)
        (self.backup/'RadeonNI.kext/Contents/Info.plist').write_bytes(b'broken')
        self.assertNotEqual(self.call('rdn_graphics_restore'),0)
        self.assertTrue((self.ext/NAMES[0]).exists())

if __name__=='__main__': unittest.main()
