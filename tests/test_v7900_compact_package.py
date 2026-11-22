"""Verify compact transports reconstruct exact community package files."""
import hashlib
import pathlib
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
RELEASE=ROOT/'build/community-v7900/release'


class CompactPackageTest(unittest.TestCase):
    def test_exact_reconstruction_and_corruption_refusal(self):
        originals=sorted(p for p in RELEASE.glob('*.zip') if not p.stem.endswith('-Compact'))
        self.assertEqual(len(originals),5)
        for original in originals:
            compact=RELEASE/(original.stem+'-Compact.zip')
            self.assertTrue(compact.is_file())
            with tempfile.TemporaryDirectory() as tmp:
                tmp=pathlib.Path(tmp)
                with zipfile.ZipFile(compact) as z:
                    self.assertIsNone(z.testzip());z.extractall(tmp)
                    folder=tmp/z.namelist()[0].split('/')[0]
                target=tmp/'expanded'
                result=subprocess.run([sys.executable,str(folder/'expand.py'),str(target)],capture_output=True,text=True)
                self.assertEqual(result.returncode,0,result.stdout+result.stderr)
                with zipfile.ZipFile(original) as z:
                    for item in z.infolist():
                        relative='/'.join(item.filename.split('/')[1:])
                        self.assertEqual(hashlib.sha256((target/relative).read_bytes()).digest(),
                                         hashlib.sha256(z.read(item)).digest(),relative)
                        self.assertEqual((target/relative).stat().st_mode & 0o777,(item.external_attr>>16)&0o777,relative)
                again=subprocess.run([sys.executable,str(folder/'expand.py'),str(target)],capture_output=True,text=True)
                self.assertNotEqual(again.returncode,0)
                self.assertIn('already exists',again.stdout)
                delta=next((folder/'deltas').iterdir());data=bytearray(delta.read_bytes());data[-1]^=1;delta.write_bytes(data)
                failed=tmp/'corrupt-output'
                result=subprocess.run([sys.executable,str(folder/'expand.py'),str(failed)],capture_output=True,text=True)
                self.assertNotEqual(result.returncode,0)
                self.assertFalse(failed.exists())
                self.assertIn('checksum mismatch',result.stdout)

    def test_slim_payload_matches_full(self):
        for suffix in ('','-CFM'):
            prefix='RadeonNI-Leopard-V7900'+suffix+'-Community-'
            with zipfile.ZipFile(RELEASE/(prefix+'Experimental.zip')) as full, zipfile.ZipFile(RELEASE/(prefix+'Slim.zip')) as slim:
                def files(z):
                    return {'/'.join(i.filename.split('/')[1:]): z.read(i) for i in z.infolist()}
                original, reduced = files(full), files(slim)
                payload={k:v for k,v in original.items() if k.startswith('payload/')}
                self.assertTrue(payload)
                self.assertEqual(payload,{k:v for k,v in reduced.items() if k.startswith('payload/')})
                self.assertNotIn('SOURCE.bundle',reduced)
                self.assertFalse(any(k.startswith('build-logs/') for k in reduced))
                for k in original:
                    if 'license' in k.lower(): self.assertEqual(original[k],reduced[k],k)


if __name__=='__main__':unittest.main()
