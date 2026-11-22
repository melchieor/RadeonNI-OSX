#!/usr/bin/env python3
"""Build the read-only Tiger sleep resource status bundle on the build Mac."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

root = Path(__file__).resolve().parents[1]
out = root / 'build/tiger-v7900/sleep-status'
sdk = root / 'build/tiger-v7900/sdk-audit/extracted/MacOSX10.4u.sdk'
ref = root / 'build/tiger-v7900/apple-reference'
out.mkdir(parents=True, exist_ok=True)
binary = out / 'rdn_sleepstatus.so'
archive = out / 'RadeonNI-Tiger-Sleep-Status.zip'
if binary.exists() or archive.exists():
    raise SystemExit('Refusing to overwrite earlier diagnostic')
cc = root / 'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc'
subprocess.run([str(cc), '-m32', '-Os', '-std=gnu99', '-mmacosx-version-min=10.4',
    '-nodefaultrpaths', '-isysroot', str(sdk), '-I'+str(root/'hw'),
    '-I'+str(root/'tools/guest'), '-bundle', str(root/'tools/guest/tiger_sleep_status.c'),
    '-framework', 'Python', '-framework', 'IOKit', '-framework', 'CoreFoundation',
    '-Wl,-undefined,error', '-o', str(binary)], check=True)
macho = read(binary)[18]
if macho['kind'] != 8 or macho['rpaths'] or '_initrdn_sleepstatus' not in macho['exports']:
    raise SystemExit('Unexpected Mach-O bundle')
if symbol_bytes(binary, 'dyld_stub_binding_helper', 16) != symbol_bytes(sdk/'usr/lib/bundle1.o', 'dyld_stub_binding_helper', 16):
    raise SystemExit('Unexpected bundle startup helper')
exports, seen, todo = set(), set(), list(macho['dependencies'])
while todo:
    name = todo.pop()
    if name in seen: continue
    seen.add(name)
    if not name.startswith(('/usr/lib/', '/System/Library/Frameworks/', '/System/Library/PrivateFrameworks/')):
        raise SystemExit('Unexpected non-system dependency: '+name)
    path = ref/'usr/lib/libSystem.B.dylib' if name == '/usr/lib/libSystem.B.dylib' else sdk/name.lstrip('/')
    lib = read(path)[18]
    exports.update(lib['exports']); todo.extend(lib['dependencies'])
missing = sorted(set(macho['imports']) - exports)
if missing: raise SystemExit('Unresolved Tiger imports: '+repr(missing))
files = {'rdn_sleepstatus.so': binary.read_bytes(),
         'status.py': b'import rdn_sleepstatus\nrdn_sleepstatus.status()\n',
         'README.txt': b'Tiger 10.4.11 PPC V7900: experimental read-only resource status.\nRun: /usr/bin/python -E ./status.py\nNo sleep or rehearsal is requested. The accelerator is opened to query status.\nAn error or enabled=0 is a valid diagnostic result; do not force sleep.\nThis diagnostic has not yet run on the target.\n'}
manifest = {'architecture':'ppc32', 'runtime_tested':False, 'imports_missing':missing,
            'dependencies':macho['dependencies'], 'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}}
files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True)+'\n').encode()
with archive.open('xb') as f:
    with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items():
            entry=zipfile.ZipInfo('RadeonNI-Tiger-Sleep-Status/'+name,(2020,1,1,0,0,0))
            entry.create_system=3;entry.external_attr=0o100644<<16;entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry,data)
print(archive)
print('sha256='+hashlib.sha256(archive.read_bytes()).hexdigest())
