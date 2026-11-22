#!/usr/bin/env python3
"""Consolidate the user's tested Tiger PPC artifacts into an experimental ZIP."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import zipfile
from leopard_macho import read

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
NAMES=['RadeonNIGLDriver'+s for s in ('','1','2','3')]


def digest(data):return hashlib.sha256(data).hexdigest()
def cksum(data):
    p=subprocess.check_output(['cksum'],input=data).decode().split()
    return p[0]+':'+p[1]
def read_archive(path,prefix):
    with zipfile.ZipFile(path) as z:
        if z.testzip():raise ValueError('Archive CRC failure: '+str(path))
        m=json.loads(z.read(prefix+'manifest.json'))
        files={n:z.read(prefix+n) for n in m['files']}
        for n,d in files.items():
            if digest(d)!=m['files'][n]:raise ValueError('Archive SHA-256 mismatch: '+n)
    return files


def main():
    cursor=read_archive(OUT/'cursor-trial/RadeonNI-Tiger-V7900-CursorTrial-05070bba-v2.zip','RadeonNI-Tiger-V7900-CursorTrial/')
    graphics=read_archive(OUT/'graphics-trial/RadeonNI-Tiger-V7900-GraphicsTrial-905f6e1c-v2.zip','RadeonNI-Tiger-V7900-GraphicsTrial/')
    cfm=read_archive(OUT/'cfm-gl-trial/RadeonNI-Tiger-CFM-GLTrial-19a123ec.zip','RadeonNI-Tiger-CFM-GLTrial/')
    kernel=cursor['trial/RadeonNI.kext/Contents/MacOS/RadeonNI']
    profile=cursor['trial/RadeonNI.kext/Contents/Info.plist']
    entry=next(iter(plistlib.loads(profile)['IOKitPersonalities'].values()))
    if (entry.get('IOPCIMatch')!='0x67041002' or not entry.get('Accelerator') or not entry.get('HWCursor') or
            not entry.get('TemperatureFanControl') or not entry.get('GAPlugin') or not entry.get('Surfaces') or
            entry.get('AddAppleCinema1080p')):
        raise ValueError('Unexpected active baseline profile')
    scalar_audit=json.loads(cfm['validation.json'])
    if scalar_audit['errors']:raise ValueError('Scalar GL validation failed')
    files={'payload/RadeonNI.kext/Contents/Info.plist':profile,
           'payload/RadeonNI.kext/Contents/MacOS/RadeonNI':kernel}
    for part in ('Info.plist','MacOS/RadeonNIGA'):
        files['payload/RadeonNIGA.plugin/Contents/'+part]=graphics['trial/RadeonNIGA.plugin/Contents/'+part]
    for n in NAMES:
        info='trial/'+n+'.bundle/Contents/Info.plist'; exe='trial/'+n+'.bundle/Contents/MacOS/'+n
        if digest(cfm['normal/'+n])!=digest(graphics[exe]):raise ValueError('CFM baseline mismatch: '+n)
        if digest(cfm['trial/'+n])!=scalar_audit['modules'][n]['sha256']:raise ValueError('CFM candidate mismatch: '+n)
        files['payload/'+n+'.bundle/Contents/Info.plist']=graphics[info]
        files['payload/'+n+'.bundle/Contents/MacOS/'+n]=cfm['trial/'+n]
    for name in ('rdn_fanprobe.so','rdn_glprobe.so','fan-sample.py','gl-list.py','gl-draw.py','graphics-test.sh'):
        files[name]=cursor[name]
    files['framebuffer-core.sh']=(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes()
    files['graphics-core.sh']=(ROOT/'g5/tiger-graphics-core.sh').read_bytes()
    files['complete-core.sh']=(ROOT/'g5/tiger-complete-core.sh').read_bytes()
    for name in ('LICENSE.radeon','LICENSE.RadeonNI'):
        files[name]=cursor[name]
    for name in graphics:
        if name.startswith('LICENSE.') or name.startswith('licenses/'):
            files.setdefault(name,graphics[name])
    files['validation-cfm-scalar.json']=cfm['validation.json']
    checks='\n'.join(cksum(d)+' '+n for n,d in files.items() if n.startswith('payload/'))
    # ID is based on the exact payload only, not timestamps or documentation.
    identity=hashlib.sha256(''.join(n+':'+digest(files[n])+'\n' for n in sorted(files) if n.startswith('payload/')).encode()).hexdigest()[:12]
    manager=(ROOT/'g5/tiger-complete-manage.sh').read_text()
    manager=manager.replace('__PAYLOAD_CHECKSUMS__',checks).replace('__PACKAGE_ID__',identity)
    if '__PAYLOAD_CHECKSUMS__' in manager or '__PACKAGE_ID__' in manager:raise ValueError('Unfilled manager token')
    files['manage.sh']=manager.encode()
    files['README.txt']=('''EXPERIMENTAL TIGER 10.4.11 V7900 DRIVER -- NOT A STABLE RELEASE\n\nThis package combines the user's previously tested Tiger V7900 framebuffer,\naccelerator, 2D plugin, hardware cursor, automatic fan and scalar OpenGL\ntrial. Basic desktop and green-pixel OpenGL tests passed; two CFM games were\nreported to launch and play. Long-duration GPU load, Core Image correctness,\nother boards, fault responses on hardware, and sleep are not qualified.\nThe GCC exception/save-world runtime still contains vector instructions.\nUnreal 1 produced a separate audio-path crash on exit.\n\nEDID-reported modes and the driver’s existing fallbacks are used; the failed\nopt-in 1080p experiment is NOT in this package. Startup\ncolor bars remain. 256 MB reported by System Profiler is the PCI aperture,\nnot necessarily physical VRAM. Do not use sleep during this experiment.\n\nIf an existing RadeonNI installation is present, do NOT reinstall over it.\nRun sh ./manage.sh --verify-installed to compare its six bundles. This does\nnot create an uninstall backup and does not validate running memory. Continue\nto preserve the backups and packages from the earlier trials.\n\nFor a fresh Tiger 10.4.11 PowerPC installation, with NVIDIA installed and a\nTiger disk backup: sudo sh ./manage.sh --install. It refuses any pre-existing\nRadeonNI bundle. Save the fresh-install state path; shut down and unplug\nbefore swapping cards. No Apple logo or video is guaranteed. If needed, boot\nusing NVIDIA, then sudo sh ./manage.sh --remove and restart. Removal is only\nfor this package's own recorded fresh install and refuses modified bundles.\nPreserve this directory and all earlier recovery media.\n\nDiagnostics: sh ./graphics-test.sh from the desktop, and sudo /usr/bin/python\n-E ./fan-sample.py for a 90-second sensor capture. Checksums are for accidental\ncorruption, not signatures; compare the ZIP SHA-256 on the build host.\n''').encode()
    manifest={'package_id':identity,'experimental':True,'os':'10.4.11','architecture':'ppc32','pci_id':'1002:6704',
              'gl_legacy_cfm_tested':True,'sustained_load_tested':False,'sleep_supported':False,
              'inputs':{'kernel_source_commit':'4ea57fa','cursor_profile_commit':'cfb3db0',
                        'scalar_gl_source_commit':'60ecd49','firmware_revision':'69e51bb26f3fa3e118dd770f1962a93bed690dc1'},
              'files':{n:digest(d) for n,d in files.items()}}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('complete-package/RadeonNI-Tiger-V7900-Experimental-'+identity+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for n,d in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-V7900-Experimental/'+n,(2020,1,1,0,0,0));item.create_system=3
                item.external_attr=(0o100000|(0o755 if n.endswith('.sh') or '/Contents/MacOS/' in n else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,d)
    print(dest);print('sha256='+digest(dest.read_bytes()));print('EXPERIMENTAL: not yet load-qualified under sustained graphics use')


if __name__=='__main__':main()
