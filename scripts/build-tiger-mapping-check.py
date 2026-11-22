#!/usr/bin/env python3
"""Build Tiger's experimental powered resource probe as a Python bundle."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

root=Path(__file__).resolve().parents[1]
out=root/'build/tiger-v7900/mapping-check-20261118'
sdk=root/'build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk'
ref=root/'build/tiger-v7900/apple-reference'
out.mkdir(parents=True,exist_ok=True)
binary=out/'rdn_mapping_probe.so'; archive=out/'RadeonNI-Tiger-Mapping-Check.zip'
if binary.exists() or archive.exists(): raise SystemExit('Refusing to overwrite existing output')
cc=root/'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc'
subprocess.run([str(cc),'-m32','-Os','-std=gnu99','-DRDN_INDEX_WRITE_PROBE=1','-DRDN_INDEX_RANGE_PROBE=1','-DRDN_INDEX_FULLPAGE_PROBE=1','-DRDN_INDEX_RESTORE_PROBE=1','-mmacosx-version-min=10.4',
 '-nodefaultrpaths','-isysroot',str(sdk),'-I'+str(root/'hw'),'-I'+str(root/'tools/guest'),
 '-bundle',str(root/'tools/guest/tiger_mapping_probe.c'),'-framework','Python',
 '-framework','IOKit','-framework','CoreFoundation','-Wl,-undefined,error','-o',str(binary)],check=True)
m=read(binary)[18]
if m['kind']!=8 or m['rpaths'] or '_initrdn_mapping_probe' not in m['exports']: raise ValueError('Unexpected Mach-O')
if symbol_bytes(binary,'dyld_stub_binding_helper',16)!=symbol_bytes(sdk/'usr/lib/bundle1.o','dyld_stub_binding_helper',16): raise ValueError('Unexpected dyld helper')
exports,seen,todo=set(),set(),list(m['dependencies'])
while todo:
 name=todo.pop()
 if name in seen: continue
 seen.add(name)
 if not name.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')): raise ValueError('Unexpected dependency '+name)
 path=ref/'usr/lib/libSystem.B.dylib' if name=='/usr/lib/libSystem.B.dylib' else sdk/name.lstrip('/')
 lib=read(path)[18];exports.update(lib['exports']);todo.extend(lib['dependencies'])
missing=sorted(set(m['imports'])-exports)
if missing: raise ValueError('Unresolved Tiger imports: '+repr(missing))
files={'rdn_mapping_probe.so':binary.read_bytes(),
 'rehearse.py':b'import rdn_mapping_probe\nrdn_mapping_probe.check()\n',
 'README.txt':b'''EXPERIMENTAL TIGER PRIVATE MAPPING GATE TEST\n\nUses a dedicated system RAM buffer and may block this test process. It does\nnot redirect framebuffer mappings, change GPU power, or test system sleep.\nRequires the matching test kext and administrator privilege.\n  sudo sh ./run-batch.sh\n'''}
files['run-batch.sh']=b'''#!/bin/sh\nset -u\n[ "$(id -u)" = 0 ] || exit 1\ncd "$(dirname "$0")" || exit 1\necho BEFORE_STATUS\n/usr/bin/python -E ./status.py || exit 1\necho BEFORE_FAN\nioreg -c RadeonNI -w 0 | grep -E "FanTemperatureMilliC|FanRequestedPercent|FanControlReady|TemperatureFanControlActive"\necho TEST_START\n/usr/bin/python -E ./rehearse.py || exit 1\necho AFTER_STATUS\n/usr/bin/python -E ./status.py || exit 1\necho AFTER_FAN\nioreg -c RadeonNI -w 0 | grep -E "FanTemperatureMilliC|FanRequestedPercent|FanControlReady|TemperatureFanControlActive"\necho BATCH_FINISHED\n'''
with zipfile.ZipFile(root/'build/tiger-v7900/sleep-profile/RadeonNI-Tiger-Sleep-Profile-5e901ad5.zip') as z:
 prefix='RadeonNI-Tiger-Sleep-Profile/'
 if z.testzip(): raise ValueError('Profile archive failed CRC')
 source=json.loads(z.read(prefix+'manifest.json'))
 for n in ('rdn_sleepstatus.so','status.py','rdn_fanprobe.so','fan-sample.py','rdn_glprobe.so','graphics-test.sh','gl-list.py','gl-draw.py'):
  v=z.read(prefix+n)
  if hashlib.sha256(v).hexdigest()!=source['files'][n]: raise ValueError('Diagnostic mismatch '+n)
  files[n]=v
files['manifest.json']=(json.dumps({'runtime_tested':False,'architecture':'ppc32','imports_missing':missing,'dependencies':m['dependencies'],
 'files':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}},indent=2,sort_keys=True)+'\n').encode()
with archive.open('xb') as f:
 with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
  for n,v in files.items():
   i=zipfile.ZipInfo('RadeonNI-Tiger-Mapping-Check/'+n,(2020,1,1,0,0,0));i.create_system=3;i.external_attr=0o100644<<16;i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,v)
print(archive);print('sha256='+hashlib.sha256(archive.read_bytes()).hexdigest())
