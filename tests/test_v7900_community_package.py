"""Validate payload provenance and CFM slice boundaries of forum packages."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from leopard_macho import slices

spec = importlib.util.spec_from_file_location('community', ROOT/'scripts/package-v7900-community.py')
community = importlib.util.module_from_spec(spec)
spec.loader.exec_module(community)


class CommunityPackageTest(unittest.TestCase):
    def test_packages_and_exact_slice_origins(self):
        release = ROOT/'build/community-v7900/release'
        paths = {name: release/('RadeonNI-'+name+'-V7900-Community-Experimental.zip')
                 for name in ('Tiger','Leopard')}
        candidate = release/'RadeonNI-Leopard-V7900-CFM-Community-Experimental.zip'
        if not all(p.is_file() for p in (*paths.values(),candidate)):
            self.skipTest('community artifacts not built')
        data = {}
        for osname, path in paths.items():
            _, files, _ = community.archive_files(path)
            community.verify_original(osname, files)
            _, baseline, _ = community.archive_files(community.SOURCES[osname][0])
            payload = {k:v for k,v in files.items() if k.startswith('payload/')}
            self.assertEqual(payload, {k:v for k,v in baseline.items() if k.startswith('payload/')})
            data[osname] = files
        _, proposed, _ = community.archive_files(candidate)
        community.verify_original('Leopard', proposed)
        for part in ('RadeonNI.kext/Contents/MacOS/RadeonNI', 'RadeonNI.kext/Contents/Info.plist',
                     'RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA'):
            self.assertEqual(proposed['payload/'+part], data['Leopard']['payload/'+part])
        report = json.loads(proposed['LEOPARD-CFM-VALIDATION.json'])
        self.assertEqual(report['errors'], [])
        self.assertFalse(report['hardware_tested'])
        self.assertFalse(report['unreal_tested'])
        for suffix in ('','1','2','3'):
            name='RadeonNIGLDriver'+suffix
            key='payload/'+name+'.bundle/Contents/MacOS/'+name
            new=slices(proposed[key]);old=slices(data['Leopard'][key])
            self.assertEqual(new[0x1000012], old[0x1000012])
            self.assertNotEqual(new[18], old[18])
            self.assertEqual(community.digest(new[18]),report['modules'][name]['sha256'])


if __name__ == '__main__':
    unittest.main()
