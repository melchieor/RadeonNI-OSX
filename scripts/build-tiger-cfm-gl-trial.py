#!/usr/bin/env python3
"""Package an experimental CFM-alignment GL-only trial and rollback."""
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
NAMES=['RadeonNIGLDriver'+x for x in ('','1','2','3')]


def digest(data):return hashlib.sha256(data).hexdigest()
def cksum(data):
    bits=subprocess.check_output(['cksum'],input=data).decode().split()
    return bits[0]+':'+bits[1]


def main():
    archive=OUT/'graphics-trial/RadeonNI-Tiger-V7900-GraphicsTrial-905f6e1c-v2.zip'
    audit=json.loads((OUT/'validation-cfm-scalar.json').read_text())
    if audit['errors']:raise SystemExit('Candidate static validation has errors')
    prefix='RadeonNI-Tiger-V7900-GraphicsTrial/'
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise SystemExit('Baseline archive CRC failure')
        old_manifest=json.loads(z.read(prefix+'manifest.json'))
        old={}
        for n in NAMES:
            key='trial/'+n+'.bundle/Contents/MacOS/'+n
            old[n]=z.read(prefix+key)
            if digest(old[n])!=old_manifest['files'][key]:raise SystemExit('Baseline GL checksum mismatch: '+n)
        tools={n:z.read(prefix+n) for n in ('rdn_fanprobe.so','fan-sample.py','rdn_glprobe.so','gl-list.py','gl-draw.py','graphics-test.sh')}
        if any(digest(d)!=old_manifest['files'][n] for n,d in tools.items()):raise SystemExit('Diagnostic checksum mismatch')
    candidates={}
    for n in NAMES:
        path=OUT/'mesa-cfm-scalar/build-tiger-native32/src/gallium/targets/rdn'/(n+'.dylib')
        candidates[n]=path.read_bytes();entry=audit['modules'][n]
        if digest(candidates[n])!=entry['sha256'] or entry['unexpected_vector_functions']:
            raise SystemExit('Candidate does not match scoped audit: '+n)
    identity=digest(candidates[NAMES[0]])[:8]
    files={}
    for n in NAMES:files['normal/'+n]=old[n];files['trial/'+n]=candidates[n]
    files.update(tools)
    checks='\n'.join(cksum(d)+' '+n for n,d in files.items() if n.startswith(('normal/','trial/')))
    manager=(ROOT/'g5/tiger-gl-swap-manage.sh').read_text().replace('__PAYLOAD_CHECKSUMS__',checks).replace('__TRIAL_ID__',identity)
    if '__PAYLOAD_CHECKSUMS__' in manager or '__TRIAL_ID__' in manager:raise SystemExit('Unfilled manager token')
    files['manage.sh']=manager.encode()
    files['swap-core.sh']=(ROOT/'g5/tiger-gl-swap-core.sh').read_bytes()
    files['cfm-game-test.sh']=(ROOT/'g5/tiger-cfm-game-test.sh').read_bytes()
    files['LICENSE.RadeonNI']=(ROOT/'LICENSE').read_bytes()
    files['LICENSE.gcc-runtime']=(ROOT/'third_party/gcc-14-darwin/COPYING.RUNTIME').read_bytes()
    files['LICENSE.gcc']=(ROOT/'third_party/gcc-14-darwin/COPYING3').read_bytes()
    files['LICENSE.mesa']=(ROOT/'third_party/mesa-26.2.4/docs/license.rst').read_bytes()
    for p in sorted((ROOT/'third_party/mesa-26.2.4/licenses').rglob('*')):
        if p.is_file():files['licenses/mesa/'+str(p.relative_to(ROOT/'third_party/mesa-26.2.4/licenses'))]=p.read_bytes()
    files['README.txt']=b'''EXPERIMENTAL TIGER CFM OPENGL TRIAL\n\nThis build addresses a suspected AltiVec stack-alignment failure in two\nlegacy Unreal games. It is not a general ABI fix, and may crash, corrupt\nrendering, reduce performance or destabilize the GPU. The GCC save-world\nand exception runtime still contains vector instructions, so full CFM stack\nsafety is not proven. Use only with a backup, SSH and an NVIDIA recovery card.\n\nClose both games first. sudo sh ./manage.sh --install saves all four current\nOpenGL executables and atomically replaces each on disk. No kernel, fan,\nframebuffer, or GA plugin is changed. Existing processes may retain the old\nbinary; newly launched applications use the trial. No reboot is required.\nTo test from the Tiger desktop: sh ./cfm-game-test.sh tournament serial\nAfter recording the result, sh ./cfm-game-test.sh unreal serial tests the\nother game. The script reports the paths of its driver and output logs.\nTo restore: close games, sudo sh ./manage.sh --restore. Keep this package\nand the printed backup. No cache, boot-argument, firmware or NVRAM changes.\nKeep tests brief and monitor the GPU fan; do not sleep the machine.\n'''
    files['validation.json']=(json.dumps(audit,indent=2,sort_keys=True)+'\n').encode()
    files['manifest.json']=(json.dumps({'experimental':True,'hardware_tested':False,'candidate_id':identity,
        'residual_vector_functions':['save_world','eh_rest_world_r10'],
        'files':{n:digest(d) for n,d in files.items()}},indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('cfm-gl-trial/RadeonNI-Tiger-CFM-GLTrial-'+identity+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for n,d in files.items():
                i=zipfile.ZipInfo('RadeonNI-Tiger-CFM-GLTrial/'+n,(2020,1,1,0,0,0));i.create_system=3
                i.external_attr=(0o100000|(0o755 if n.endswith('.sh') else 0o644))<<16;i.compress_type=zipfile.ZIP_DEFLATED
                z.writestr(i,d)
    print(dest);print('sha256='+digest(dest.read_bytes()))


if __name__=='__main__':main()
