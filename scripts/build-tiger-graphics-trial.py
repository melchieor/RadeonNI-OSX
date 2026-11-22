#!/usr/bin/env python3
"""Prepare an experimental Tiger graphics trial and recovery bundle."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import zipfile
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

ROOT=Path(__file__).resolve().parents[1]; OUT=ROOT/'build/tiger-v7900'
SDK=OUT/'sdk-audit/extracted/MacOSX10.4u.sdk';REF=OUT/'apple-reference'


def cksum(data):
    bits=subprocess.check_output(['cksum'],input=data).decode().split()
    return bits[0]+':'+bits[1]


def verified_archive(path,prefix):
    with zipfile.ZipFile(path) as z:
        if z.testzip(): raise ValueError('Archive CRC failure: '+str(path))
        manifest=json.loads(z.read(prefix+'manifest.json'))
        files={n:z.read(prefix+n) for n in manifest['files']}
        for n,d in files.items():
            if hashlib.sha256(d).hexdigest()!=manifest['files'][n]:
                raise ValueError('Archive digest mismatch: '+n)
    return files


def validate_tool(path):
    meta=read(path)[18]
    if meta['kind']!=8 or meta['rpaths'] or '_initrdn_glprobe' not in meta['exports']:
        raise ValueError('Invalid Tiger GL probe')
    if symbol_bytes(path,'dyld_stub_binding_helper',16)!=symbol_bytes(SDK/'usr/lib/bundle1.o','dyld_stub_binding_helper',16):
        raise ValueError('Wrong dyld bundle helper')
    seen=set();todo=list(meta['dependencies']);exports=set()
    while todo:
        name=todo.pop()
        if name in seen:continue
        seen.add(name)
        if not name.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')):
            raise ValueError('Non-system dependency: '+name)
        ref=REF/'usr/lib/libSystem.B.dylib' if name=='/usr/lib/libSystem.B.dylib' else SDK/name.lstrip('/')
        library=read(ref)[18];exports.update(library['exports']);todo.extend(library['dependencies'])
    missing=sorted(set(meta['imports'])-exports)
    if missing:raise ValueError('Missing probe imports: '+repr(missing))


def graphics_profile(data):
    info=plistlib.loads(data);profiles=info['IOKitPersonalities']
    if len(profiles)!=1:raise ValueError('Expected one V7900 personality')
    p=next(iter(profiles.values()))
    if (p.get('IOPCIMatch')!='0x67041002' or not p.get('Accelerator') or
            not p.get('TemperatureFanControl') or p.get('GAPlugin') or p.get('Surfaces')):
        raise ValueError('Unexpected engine baseline profile')
    p.update(AccelCaps=3,AGPShim=3,Surfaces=True,SurfaceGate=False,GAPlugin=True)
    return plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False)


def main():
    engine=verified_archive(OUT/'accelerator-trial/RadeonNI-Tiger-V7900-EngineTrial-e1886551.zip',
                            'RadeonNI-Tiger-V7900-EngineTrial/')
    modules=verified_archive(OUT/'userspace-probe/RadeonNI-Tiger-Userspace-Probe.zip',
                             'RadeonNI-Tiger-Userspace-Probe/')
    baseline=engine['trial/RadeonNI.kext/Contents/Info.plist']
    kernel=engine['trial/RadeonNI.kext/Contents/MacOS/RadeonNI']
    audit=json.loads((OUT/'experimental-validation-fan.json').read_text())
    if hashlib.sha256(kernel).hexdigest()!=audit['kernel']['sha256']:
        raise ValueError('Engine kernel changed since audit')
    profile=graphics_profile(baseline)
    output=OUT/'graphics-tests/rdn_glprobe.so'
    if output.exists():raise SystemExit('Move existing GL probe output aside before rebuilding')
    output.parent.mkdir(parents=True,exist_ok=True)
    subprocess.run([str(ROOT/'third_party/leopard-toolchain/bin/powerpc-apple-darwin9-gcc'),
        '-m32','-Os','-std=gnu99','-mmacosx-version-min=10.4','-nodefaultrpaths','-isysroot',str(SDK),
        '-bundle',str(ROOT/'tools/guest/tiger_glprobe.c'),'-framework','Python','-framework','OpenGL',
        '-framework','ApplicationServices','-Wl,-undefined,error','-o',str(output)],check=True)
    validate_tool(output)
    files={'normal/RadeonNI.kext/Contents/Info.plist':baseline,
           'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':kernel,
           'trial/RadeonNI.kext/Contents/Info.plist':profile,
           'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':kernel,
           'framebuffer-core.sh':(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes(),
           'graphics-core.sh':(ROOT/'g5/tiger-graphics-core.sh').read_bytes(),
           'rdn_glprobe.so':output.read_bytes(),'rdn_fanprobe.so':engine['rdn_fanprobe.so'],
           'fan-sample.py':b'import rdn_fanprobe\nrdn_fanprobe.sample(90)\n',
           'gl-list.py':b'import rdn_glprobe\nresult = rdn_glprobe.probe(0)\nprint "probe_status", result\n',
           'gl-draw.py':b'import rdn_glprobe\nresult = rdn_glprobe.probe(1)\nprint "probe_status", result\n'}
    files['graphics-test.sh']=b'''#!/bin/sh\n# Run in a logged-in Tiger desktop session, as the desktop user.\nPATH=/bin:/sbin:/usr/bin:/usr/sbin\nexport PATH\nRDN_SOFTWARE=0\nRDN_GLD_LOG="$HOME/Desktop/radeon-tiger-gld.log"\nexport RDN_SOFTWARE RDN_GLD_LOG\necho '=== CGL renderers ==='\n/usr/bin/python -E ./gl-list.py\necho "list_exit_status=$?"\necho '=== Offscreen draw ==='\n/usr/bin/python -E ./gl-draw.py\necho "draw_exit_status=$?"\necho '=== Display information ==='\nsystem_profiler SPDisplaysDataType\necho '=== GPU service properties ==='\nioreg -c RadeonNIAccel -w 0 | grep -E 'RadeonNIEngine|IOGLBundleName|AccelCaps|IOAccelRevision'\necho 'GL driver log, if produced:' "$RDN_GLD_LOG"\n'''
    for suffix in ('','1','2','3'):
        name='RadeonNIGLDriver'+suffix
        meta=plistlib.loads((ROOT/'gld/Info.plist').read_bytes())
        meta.update(CFBundleExecutable=name,CFBundleName=name,
                    CFBundleIdentifier='org.osxgpu.RadeonNIGLDriver'+suffix)
        files['trial/'+name+'.bundle/Contents/Info.plist']=plistlib.dumps(meta,fmt=plistlib.FMT_XML,sort_keys=False)
        files['trial/'+name+'.bundle/Contents/MacOS/'+name]=modules['modules/'+name+'.dylib']
    files['trial/RadeonNIGA.plugin/Contents/Info.plist']=(ROOT/'ga/Info.plist').read_bytes()
    files['trial/RadeonNIGA.plugin/Contents/MacOS/RadeonNIGA']=modules['modules/RadeonNIGA']
    identity=hashlib.sha256(profile).hexdigest()[:8]
    checks='\n'.join(cksum(d)+' '+n for n,d in files.items() if n.startswith(('normal/','trial/')))
    manager=(ROOT/'g5/tiger-graphics-manage.sh').read_text()
    manager=manager.replace('__PAYLOAD_CHECKSUMS__',checks).replace('__TRIAL_ID__',identity)
    if '__PAYLOAD_CHECKSUMS__' in manager or '__TRIAL_ID__' in manager:raise ValueError('Unfilled installer template')
    files['manage.sh']=manager.encode()
    files['LICENSE.radeon']=engine['LICENSE.radeon']
    files['LICENSE.mesa']=(ROOT/'third_party/mesa-26.2.4/docs/license.rst').read_bytes()
    files['LICENSE.gcc-runtime']=(ROOT/'third_party/gcc-14-darwin/COPYING.RUNTIME').read_bytes()
    files['LICENSE.gcc']=(ROOT/'third_party/gcc-14-darwin/COPYING3').read_bytes()
    files['LICENSE.RadeonNI']=(ROOT/'LICENSE').read_bytes()
    for p in sorted((ROOT/'third_party/mesa-26.2.4/licenses').rglob('*')):
        if p.is_file():files['licenses/mesa/'+str(p.relative_to(ROOT/'third_party/mesa-26.2.4/licenses'))]=p.read_bytes()
    readme='''EXPERIMENTAL TIGER V7900 GRAPHICS TRIAL\n\nThis trial enables surfaces, the GA plugin and OpenGL driver. It may cause\nvisual corruption, hangs, or kernel panics. Save work, back up Tiger and\nretain the NVIDIA card and power cable for recovery. Keep this package; it\ncontains the exact engine-only baseline needed for restore. Automatic fan\ncontrol is retained but not qualified for sustained GPU load. Do not use sleep.\n\nThe installer refuses existing plugin names and a changed engine baseline.\nRun sudo sh ./manage.sh --install and save its backup path. After restart,\nrun /usr/bin/python -E ./gl-list.py and /usr/bin/python -E ./gl-draw.py\nfrom a Tiger desktop terminal; output can indicate software fallback. The\n90-second fan-sample.py is included. Restore with sudo sh ./manage.sh\n--restore, then restart; use NVIDIA if necessary. Never force a failed restore.\n'''
    files['README.txt']=readme.encode()
    manifest={'experimental':True,'graphics_runtime_tested':False,'baseline_engine_sha256':hashlib.sha256(kernel).hexdigest(),
              'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('graphics-trial/RadeonNI-Tiger-V7900-GraphicsTrial-'+identity+'-v2.zip')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-V7900-GraphicsTrial/'+name,(2020,1,1,0,0,0))
                item.create_system=3;item.external_attr=(0o100000 | (0o755 if name.endswith(('.sh','/MacOS/RadeonNI','/MacOS/RadeonNIGA')) or '/MacOS/RadeonNIGLDriver' in name else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
    print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__':main()
