import hashlib, importlib.util, json, pathlib, re, subprocess, sys, unittest, zipfile

ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('sanitize',ROOT/'scripts/sanitize-v7900-release.py')
sanitize=importlib.util.module_from_spec(spec);spec.loader.exec_module(sanitize)
OUT=ROOT/'build/community-v7900/release'

class PrivacyReleaseTest(unittest.TestCase):
    def test_payloads_and_install_checksums(self):
        for osname,name in [('Tiger','RadeonNI-Tiger-V7900-Community-Experimental.zip'),('Leopard','RadeonNI-Leopard-V7900-Community-Slim.zip'),('Leopard','RadeonNI-Leopard-V7900-CFM-Community-Slim.zip')]:
            _,old,_=sanitize.community.archive_files(OUT/name)
            path=OUT/name.replace('.zip','-Privacy.zip')
            with zipfile.ZipFile(path) as z:self.assertIsNone(z.testzip())
            _,new,_=sanitize.community.archive_files(path)
            sanitize.community.verify_original(osname,new)
            for n in old:
                if not n.startswith('payload/'):continue
                if n!=n.replace('/Contents/MacOS/RadeonNIGLDriver',''):
                    fixed,positions=sanitize.sanitize_macho(old[n])
                    self.assertEqual(new[n],fixed);self.assertTrue(positions)
                else:self.assertEqual(old[n],new[n],n)
            if osname=='Tiger':
                script=new['manage.sh'].decode();lines=script.split("done <<'CHECKSUMS'\n",1)[1].split('\nCHECKSUMS',1)[0].splitlines()
                rows={line.split(' ',1)[1]:line.split(' ',1)[0] for line in lines}
                self.assertEqual(set(rows),{n for n in new if n.startswith('payload/')})
                for n,expected in rows.items():
                    a=subprocess.run(['cksum'],input=new[n],stdout=subprocess.PIPE,check=True).stdout.decode().split()
                    self.assertEqual(expected,a[0]+':'+a[1])
                self.assertIn(json.loads(new['manifest.json'])['package_id'],script)
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),path.with_suffix('.zip.sha256').read_text().split()[0])

if __name__=='__main__':unittest.main()
