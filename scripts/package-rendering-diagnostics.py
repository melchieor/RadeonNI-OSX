#!/usr/bin/env python3
"""Build a diagnostics-only archive; never install drivers or access the G5."""
import hashlib,json,shutil,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/leopard-v7900'
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):
  raise SystemExit('Commit reviewed source before packaging')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 with (OUT/'logs/rendering-diagnostics-build.log').open('w') as log:
  subprocess.run(['bash',str(ROOT/'scripts/build-leopard-qe-probes.sh')],check=True,stdout=log,stderr=subprocess.STDOUT)
 subprocess.run(['python3',str(ROOT/'scripts/validate-leopard-build.py')],check=True)
 name='RadeonNI-Rendering-Diagnostics-'+revision[:8]
 files={}
 for filename in ('collect.py','README.txt'):
  files[filename]=(ROOT/'tools/guest/rendering-diagnostics'/filename).read_bytes()
 files['qe-status']=(OUT/'qe-probes/qe-status').read_bytes()
 sources=['tools/guest/leopard-qe-status.c','scripts/build-leopard-qe-probes.sh',
          'scripts/package-rendering-diagnostics.py','g5/leopard-v7900-manage.py',
          'tests/test_qe_marker_status.py','tests/test_leopard_installer.py',
          'docs/LEOPARD-V7900-RENDERING-INVESTIGATION.md','docs/LEOPARD-V7900-REPRODUCE.md']
 for source in sources:files['source/'+source]=(ROOT/source).read_bytes()
 files['SOURCE-CHANGE.patch']=subprocess.check_output(['git','show','--format=fuller','--binary',revision],cwd=ROOT)
 files['provenance.json']=(json.dumps(dict(source_commit=revision,build_host='Intel macOS',
  target='Leopard PPC32',driver_payload_included=False,target_tested=False),indent=2)+'\n').encode()
 for filename in ('rendering-installer-tests.log','rendering-marker-tests.log'):
  files['validation/'+filename]=(OUT/'logs'/filename).read_bytes()
 files['validation/static.json']=(OUT/'validation.json').read_bytes()
 files['MANIFEST.json']=(json.dumps({k:digest(v) for k,v in sorted(files.items())},indent=2)+'\n').encode()
 output=ROOT/'build'/(name+'.zip')
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
  for filename,data in sorted(files.items()):
   entry=zipfile.ZipInfo(name+'/'+filename,(2026,11,9,0,0,0));entry.create_system=3
   entry.external_attr=(0o100755 if filename=='qe-status' else 0o100644)<<16
   entry.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(entry,data)
 with tempfile.TemporaryDirectory(prefix='rdn-diagnostics-verify-') as temporary:
  with zipfile.ZipFile(output) as archive:
   assert archive.testzip() is None;archive.extractall(temporary)
  stage=Path(temporary)/name
  manifest=json.loads((stage/'MANIFEST.json').read_text())
  assert {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}==set(manifest)|{'MANIFEST.json'}
  for filename,expected in manifest.items():assert digest((stage/filename).read_bytes())==expected
 checksum=digest(output.read_bytes());output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n')
 result=dict(zip=str(output),sha256=checksum,bytes=output.stat().st_size,source_commit=revision,
             zip_crc_passed=True,fresh_extraction_verified=True,driver_payload_included=False)
 (OUT/'rendering-diagnostics-delivery.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
