#!/usr/bin/env python3
"""Build read-only Tiger PPC telemetry as a Python 2.3 extension."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'
SDK = OUT / 'sdk-audit/extracted/MacOSX10.4u.sdk'
REF = OUT / 'apple-reference'


def main():
    output = OUT / 'telemetry/rdn_fanprobe.so'
    archive_path = OUT / 'telemetry/RadeonNI-Tiger-Fan-Telemetry.zip'
    if output.exists() or archive_path.exists():
        raise SystemExit('Refusing to overwrite telemetry build; move the old outputs first')
    output.parent.mkdir(parents=True, exist_ok=True)
    cc = ROOT / 'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc'
    args = [str(cc), '-m32', '-Os', '-std=gnu99', '-mmacosx-version-min=10.4',
            '-nodefaultrpaths', '-isysroot', str(SDK), '-I' + str(ROOT/'hw'), '-bundle',
            str(ROOT/'tools/guest/tiger_fanprobe.c'), '-framework', 'Python', '-framework', 'IOKit',
            '-framework', 'CoreFoundation', '-Wl,-undefined,error', '-o', str(output)]
    subprocess.run(args, check=True)
    macho = read(output)[18]
    if macho['kind'] != 8 or macho['rpaths'] or '_initrdn_fanprobe' not in macho['exports']:
        raise SystemExit('Unexpected architecture, Mach-O kind, exports or rpaths')
    if symbol_bytes(output, 'dyld_stub_binding_helper', 16) != symbol_bytes(SDK/'usr/lib/bundle1.o', 'dyld_stub_binding_helper', 16):
        raise SystemExit('Bundle dyld helper does not match Tiger SDK')
    exports, seen, todo = set(), set(), list(macho['dependencies'])
    while todo:
        name = todo.pop()
        if name in seen:
            continue
        seen.add(name)
        if not name.startswith(('/usr/lib/', '/System/Library/Frameworks/', '/System/Library/PrivateFrameworks/')):
            raise SystemExit('Unexpected non-system dependency: ' + name)
        path = REF/'usr/lib/libSystem.B.dylib' if name == '/usr/lib/libSystem.B.dylib' else SDK/name.lstrip('/')
        lib = read(path)[18]
        exports.update(lib['exports'])
        todo.extend(lib['dependencies'])
    missing = sorted(set(macho['imports']) - exports)
    if missing:
        raise SystemExit('Unresolved Tiger SDK/reference imports: ' + repr(missing))
    sample = b'import rdn_fanprobe\nrdn_fanprobe.sample(10)\n'
    readme = b'''Tiger 10.4.11 PowerPC: experimental read-only V7900 fan telemetry.\nRun: sudo /usr/bin/python -E ./sample.py\nThis reads the active RadeonNI framebuffer telemetry; it does not set fan speed.\nA bad or missing sample is not a safe temperature reading. Stop on errors.\n'''
    files = {'README.txt': readme, 'sample.py': sample, 'rdn_fanprobe.so': output.read_bytes()}
    manifest = {'architecture': 'ppc32', 'runtime_tested': False, 'imports_missing': missing,
                'dependencies': macho['dependencies'], 'files': {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}}
    files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    with archive_path.open('xb') as f:
        with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                item = zipfile.ZipInfo('RadeonNI-Tiger-Fan-Telemetry/' + name, (2020, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = 0o100644 << 16
                item.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(item, data)
    print('Archive:', archive_path)
    print('SHA-256:', hashlib.sha256(archive_path.read_bytes()).hexdigest())
    print('Statically validated only; not yet tested on Tiger')


if __name__ == '__main__':
    main()
