#!/usr/bin/env python3
"""Assemble a diagnostics-only PPC ZIP; no driver payload or target access."""
import hashlib,json,subprocess,tempfile,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/leopard-v7900'
def digest(data):return hashlib.sha256(data).hexdigest()
def main():
 if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True):raise SystemExit('Commit reviewed source first')
 revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
 with (OUT/'logs/pixel-probe-build.log').open('w') as log:
  subprocess.run(['bash',str(ROOT/'scripts/build-leopard-pixel-probe.sh')],check=True,stdout=log,stderr=subprocess.STDOUT)
 with (OUT/'logs/rendering-suite-qe-build.log').open('w') as log:
  subprocess.run(['bash',str(ROOT/'scripts/build-leopard-qe-probes.sh')],check=True,stdout=log,stderr=subprocess.STDOUT)
 subprocess.run(['python3',str(ROOT/'scripts/validate-leopard-build.py')],check=True)
 validation=json.loads((OUT/'validation.json').read_text())
 assert validation['passed']
 name='RadeonNI-Rendering-Suite-20261110-'+revision[:8];files={}
 for filename in ['run-probes.sh','README.txt','environment.py','run-suite.py','capture_preferences.py']:files[filename]=(ROOT/'tools/guest/pixel-probe-package'/filename).read_bytes()
 for probe in ('pixel-render-probe','pixel-render-probe-odd','pixel-render-probe-large','pixel-render-probe-atlas'):
  files[probe]=(OUT/'pixel-probe'/probe).read_bytes()
 files['README.txt']=(ROOT/'tools/guest/pixel-probe-package/README-SUITE.txt').read_bytes()
 files['collect.py']=(ROOT/'tools/guest/rendering-diagnostics/collect.py').read_bytes()
 for probe in ('qe-status','ci-filter-test'):files[probe]=(OUT/'qe-probes'/probe).read_bytes()
 extra=('sharetest','contexthandofftest','pbufferlifetest','pbufferpublishtest','pbufferthreadtest','backingsurfacetest','rendering-suite-visual','capture-preflight')
 for probe in extra:files[probe]=(OUT/'pixel-probe'/probe).read_bytes()
 files['preferences-capture.dylib']=(OUT/'pixel-probe/preferences-capture.dylib').read_bytes()
 files['LICENSE']=(ROOT/'LICENSE').read_bytes()
 for source,destination in [('COPYING3','GPL-3.0.txt'),('COPYING.RUNTIME','GCC-RUNTIME-EXCEPTION.txt')]:
  files['licenses/'+destination]=(ROOT/'third_party/gcc-14-darwin'/source).read_bytes()
 sources=['tools/guest/pixel-render-probe.c','tools/guest/pixel-reference.h','tools/guest/packed-reference.h','tools/guest/packed-upload-cases.h','tools/guest/mixed-backing-cases.h','tools/guest/preferences-capture.c','tools/guest/masked-reference.h','tools/guest/masked-render-cases.h','scripts/build-leopard-pixel-probe.sh',
  'scripts/package-leopard-pixel-probe.py','tests/pixel_reference.c','tests/test_pixel_probe_buffers.py',
  'tests/test_pixel_probe_images.py','tests/masked_reference.c','tests/test_mixed_capture.py','tests/packed_reference.c','tests/test_packed_upload_buffers.py','scripts/check-packed-host.py','scripts/check-rendering-suite-host.py','docs/LEOPARD-V7900-PIXEL-PROBE.md']
 sources += ['tools/guest/'+name+('.m' if name=='rendering-suite-visual' else '.c') for name in extra]
 sources += ['tools/guest/rdn_probe_device.h','hw/rdn_user.h','scripts/validate-leopard-build.py','tools/guest/leopard-qe-status.c','scripts/build-leopard-qe-probes.sh','tools/guest/wsfilter.c','tests/test_rendering_suite.py']
 for source in sources:files['source/'+source]=(ROOT/source).read_bytes()
 files['SOURCE-CHANGE.patch']=subprocess.check_output(['git','show','--format=fuller','--binary',revision],cwd=ROOT)
 files['validation/binary.json']=(json.dumps({name:validation['modules'][name] for name in ('pixel-render-probe','pixel-render-probe-odd','pixel-render-probe-large','pixel-render-probe-atlas','qe-status','ci-filter-test','preferences-capture.dylib')+extra},indent=2)+'\n').encode()
 for filename in ['pixel-reference-model.log','pixel-probe-buffer-tests.log','pixel-probe-image-tests.log','pixel-probe-runner-host-guard.log','rendering-suite-tests.log','pixel-probe-build.log','rendering-suite-qe-build.log','masked-reference-model.log','masked-host-software.log','mixed-capture-host-tests.log','packed-reference-model.log','packed-upload-buffer-tests.log','packed-host-software.log']:
  files['validation/'+filename]=(OUT/'logs'/filename).read_bytes()
 files['provenance.json']=(json.dumps(dict(source_commit=revision,build_host='Intel macOS',target='Leopard PPC32',
  driver_payload_included=False,native_target_tested=False,artifact_sha256=digest(files['pixel-render-probe'])),indent=2)+'\n').encode()
 files['MANIFEST.json']=(json.dumps({k:digest(v) for k,v in sorted(files.items())},indent=2)+'\n').encode()
 assert name.startswith('RadeonNI-Rendering-Suite-'), 'Package name was overwritten'
 output=ROOT/'build'/(name+'.zip')
 with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
  for filename,data in sorted(files.items()):
   entry=zipfile.ZipInfo(name+'/'+filename,(2026,11,10,0,0,0));entry.create_system=3
   entry.external_attr=(0o100755 if filename in ('run-probes.sh','run-suite.py','qe-status','ci-filter-test')+extra or filename.startswith('pixel-render-probe') or filename=='preferences-capture.dylib' else 0o100644)<<16
   entry.compress_type=zipfile.ZIP_DEFLATED;archive.writestr(entry,data)
 with tempfile.TemporaryDirectory(prefix='rdn-pixel-verify-') as temporary:
  with zipfile.ZipFile(output) as archive:
   assert archive.testzip() is None;archive.extractall(temporary)
  stage=Path(temporary)/name;manifest=json.loads((stage/'MANIFEST.json').read_text())
  assert {str(p.relative_to(stage)) for p in stage.rglob('*') if p.is_file()}==set(manifest)|{'MANIFEST.json'}
  for filename,expected in manifest.items():assert digest((stage/filename).read_bytes())==expected
 checksum=digest(output.read_bytes());output.with_suffix('.zip.sha256').write_text(checksum+'  '+output.name+'\n')
 report=dict(zip=str(output),sha256=checksum,bytes=output.stat().st_size,source_commit=revision,
  zip_crc_passed=True,fresh_extraction_verified=True,driver_payload_included=False)
 (OUT/'pixel-probe-delivery.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
