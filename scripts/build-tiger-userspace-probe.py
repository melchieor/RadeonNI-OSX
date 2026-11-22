#!/usr/bin/env python3
"""Package isolated Tiger user-space bundle load checks and fan monitoring."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/tiger-v7900'
SDK=OUT/'sdk-audit/extracted/MacOSX10.4u.sdk'
REF=OUT/'apple-reference'


def main():
    output=OUT/'userspace-probe/rdn_dlopen_probe.so'
    destination=OUT/'userspace-probe/RadeonNI-Tiger-Userspace-Probe.zip'
    if output.exists() or destination.exists(): raise SystemExit('Refusing to overwrite existing outputs')
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(ROOT/'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc'),
        '-m32','-Os','-mmacosx-version-min=10.4','-nodefaultrpaths','-isysroot',str(SDK),
        '-bundle',str(ROOT/'tools/guest/tiger_dlopen_probe.c'),'-framework','Python',
        '-Wl,-undefined,error','-o',str(output)],check=True)
    meta=read(output)[18]
    if meta['kind']!=8 or meta['rpaths'] or '_initrdn_dlopen_probe' not in meta['exports']:
        raise SystemExit('Unexpected probe architecture, type or exports')
    if symbol_bytes(output,'dyld_stub_binding_helper',16)!=symbol_bytes(SDK/'usr/lib/bundle1.o','dyld_stub_binding_helper',16):
        raise SystemExit('Unexpected Tiger dyld helper')
    exports=set();seen=set();todo=list(meta['dependencies'])
    while todo:
        name=todo.pop()
        if name in seen: continue
        seen.add(name)
        if not name.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')):
            raise SystemExit('Non-system dependency: '+name)
        p=REF/'usr/lib/libSystem.B.dylib' if name=='/usr/lib/libSystem.B.dylib' else SDK/name.lstrip('/')
        lib=read(p)[18];exports.update(lib['exports']);todo.extend(lib['dependencies'])
    missing=sorted(set(meta['imports'])-exports)
    if missing: raise SystemExit('Missing probe imports: '+repr(missing))
    audit=json.loads((OUT/'experimental-validation-fan.json').read_text())['modules']
    files={'rdn_dlopen_probe.so':output.read_bytes()}
    glroot=OUT/'mesa-26.2.4/build-tiger-native32/src/gallium/targets/rdn'
    for suffix in ('','1','2','3'):
        key='RadeonNIGLDriver'+suffix; path=glroot/(key+'.dylib'); content=path.read_bytes(); entry=audit[key]
        if (hashlib.sha256(content).hexdigest()!=entry['sha256'] or entry['unresolved'] or
                entry['dependency_errors'] or entry['rpaths'] or not entry['sdk_bundle_helper_prefix_matches']):
            raise SystemExit('GL module differs from audit: '+key)
        files['modules/'+key+'.dylib']=content
    ga=(OUT/'ga-experiment/RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA').read_bytes(); entry=audit['RadeonNIGA']
    if hashlib.sha256(ga).hexdigest()!=entry['sha256'] or entry['unresolved'] or entry['dependency_errors'] or entry['rpaths']:
        raise SystemExit('GA module differs from audit')
    files['modules/RadeonNIGA']=ga
    with zipfile.ZipFile(OUT/'telemetry/RadeonNI-Tiger-Fan-Telemetry.zip') as z:
        telemetry=z.read('RadeonNI-Tiger-Fan-Telemetry/rdn_fanprobe.so')
        manifest=json.loads(z.read('RadeonNI-Tiger-Fan-Telemetry/manifest.json'))
        if hashlib.sha256(telemetry).hexdigest()!=manifest['files']['rdn_fanprobe.so']:
            raise SystemExit('Telemetry checksum mismatch')
        files['rdn_fanprobe.so']=telemetry
    files['fan-sample.py']=b'import rdn_fanprobe\nrdn_fanprobe.sample(90)\n'
    files['probe-case.py']=b'import sys\nimport rdn_dlopen_probe\nrdn_dlopen_probe.probe(sys.argv[1],sys.argv[2])\nprint "LOAD_OK", sys.argv[1], sys.argv[2]\n'
    files['run.py']=b'''import os, sys\ncases = [("modules/RadeonNIGA", "RadeonNIGAFactory")]\nfor suffix in ("", "1", "2", "3"):\n    cases.append(("modules/RadeonNIGLDriver" + suffix + ".dylib", "gldGetRendererInfo"))\nfailures = 0\nfor path, symbol in cases:\n    print "BEGIN", path\n    sys.stdout.flush()\n    child = os.fork()\n    if child == 0:\n        os.execv("/usr/bin/python", ["/usr/bin/python", "-E", "./probe-case.py", path, symbol])\n        os._exit(127)\n    pid, status = os.waitpid(child, 0)\n    if not os.WIFEXITED(status) or os.WEXITSTATUS(status) != 0:\n        failures += 1\n        print "FAILED", path, "wait_status", status\n    else:\n        print "PASSED", path\n    sys.stdout.flush()\nprint "FAILED_CASES", failures\nif failures:\n    sys.exit(1)\nsys.exit(0)\n'''
    files['README.txt']=b'''EXPERIMENTAL TIGER USER-SPACE LOAD CHECK; NO INSTALLATION\n\nRun from this directory: /usr/bin/python -E ./run.py\nEach separate process loads one user-space plugin and checks an export.\nIt does not call driver entry points or enable graphics acceleration.\nInitializers may execute; this is not a proof of runtime safety.\nThe fan tool is included: sudo /usr/bin/python -E ./fan-sample.py\n'''
    manifest={'runtime_tested':False,'probe_imports_missing':missing,
              'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    with destination.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-Userspace-Probe/'+name,(2020,1,1,0,0,0))
                item.create_system=3;item.external_attr=0o100644<<16;item.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(item,data)
    print('Archive:',destination)
    print('SHA-256:',hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__=='__main__': main()
