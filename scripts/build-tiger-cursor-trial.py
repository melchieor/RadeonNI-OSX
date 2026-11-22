#!/usr/bin/env python3
"""Prepare a one-property Tiger hardware-cursor trial with rollback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
spec=importlib.util.spec_from_file_location('fan_trial',ROOT/'scripts/build-tiger-fan-trial.py')
fan=importlib.util.module_from_spec(spec);spec.loader.exec_module(fan)


def cursor_profile(data):
    info=plistlib.loads(data);profiles=info['IOKitPersonalities']
    if len(profiles)!=1: raise ValueError('Expected exactly one personality')
    entry=next(iter(profiles.values()))
    if (entry.get('IOPCIMatch')!='0x67041002' or not entry.get('Accelerator') or
            not entry.get('GAPlugin') or not entry.get('TemperatureFanControl') or entry.get('HWCursor')):
        raise ValueError('Unexpected graphics baseline')
    entry['HWCursor']=True
    return plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False)


def main():
    archive=OUT/'graphics-trial/RadeonNI-Tiger-V7900-GraphicsTrial-905f6e1c-v2.zip'
    prefix='RadeonNI-Tiger-V7900-GraphicsTrial/'
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise SystemExit('Graphics archive CRC failure')
        manifest=json.loads(z.read(prefix+'manifest.json'))
        names=('trial/RadeonNI.kext/Contents/Info.plist','trial/RadeonNI.kext/Contents/MacOS/RadeonNI',
               'rdn_fanprobe.so','rdn_glprobe.so','graphics-test.sh','fan-sample.py','gl-list.py','gl-draw.py')
        data={n:z.read(prefix+n) for n in names}
        if any(hashlib.sha256(d).hexdigest()!=manifest['files'][n] for n,d in data.items()):
            raise SystemExit('Graphics archive digest mismatch')
    baseline=data[names[0]];binary=data[names[1]]
    report=json.loads((OUT/'experimental-validation-fan.json').read_text())['kernel']
    if (hashlib.sha256(binary).hexdigest()!=report['sha256'] or report['export_collisions'] or
            report['unresolved_against_reference_union'] or report['compatibility_alias_errors'] or
            any(report['abi_comparisons'].values())):
        raise SystemExit('Baseline kernel failed static audit')
    trial=cursor_profile(baseline);identity=hashlib.sha256(trial).hexdigest()[:8]
    sums={'normal_profile_cksum':fan.cksum(baseline),'normal_binary_cksum':fan.cksum(binary),
          'trial_profile_cksum':fan.cksum(trial),'trial_binary_cksum':fan.cksum(binary)}
    script=(ROOT/'g5/tiger-fan-trial-manage.sh').read_text()
    script=script.replace('__PAYLOAD_CHECKSUMS__','\n'.join(k+"='"+v+"'" for k,v in sums.items()))
    script=script.replace('TigerFanTrial-__TRIAL_ID__','TigerCursorTrial-'+identity)
    if '__PAYLOAD_CHECKSUMS__' in script or '__TRIAL_ID__' in script:raise SystemExit('Unfilled manager tokens')
    files={'manage.sh':script.encode(),'framebuffer-core.sh':(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes(),
           'fan-core.sh':(ROOT/'g5/tiger-fan-trial-core.sh').read_bytes(),
           'LICENSE.radeon':(OUT/'firmware-staging/LICENSE.radeon').read_bytes(),
           'LICENSE.RadeonNI':(ROOT/'LICENSE').read_bytes(),
           'normal/RadeonNI.kext/Contents/Info.plist':baseline,
           'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':binary,
           'trial/RadeonNI.kext/Contents/Info.plist':trial,
           'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':binary}
    for name in names[2:]:files[name]=data[name]
    if hashlib.sha256(files['LICENSE.radeon']).hexdigest()!='fc6223d4bfe9f2f9e2eddc44b9fe5721d0caf49f01cb08d602906add686d8c6f':
        raise SystemExit('Firmware license checksum mismatch')
    files['README.txt']=b'''EXPERIMENTAL TIGER V7900 HARDWARE CURSOR TRIAL\n\nThis changes only the cursor profile flag; it preserves accelerated graphics,\nfirmware, fan policy, plugins and the kernel executable. The hardware cursor\nmay be invisible, corrupt, mispositioned or cause other display problems.\nThis is a test of one possible explanation for redraw artifacts, not a fix\nclaim. Keep a Tiger backup, the NVIDIA card, and this package for recovery.\nThe user previously observed some different corruption with the hardware\ncursor on Leopard; Tiger behavior is untested. Do not use sleep.\n\nInstall: sudo sh ./manage.sh --install (save the backup path), then restart.\nRestore: sudo sh ./manage.sh --restore, then restart. If video or pointer is\nunusable, use SSH or boot Tiger with the NVIDIA card to restore.\nThe existing graphics and fan diagnostic scripts are included.\n'''
    files['manifest.json']=(json.dumps({'experimental':True,'change':'HWCursor false -> true',
       'kernel_sha256':hashlib.sha256(binary).hexdigest(),'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}},indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('cursor-trial/RadeonNI-Tiger-V7900-CursorTrial-'+identity+'-v2.zip')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,content in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-V7900-CursorTrial/'+name,(2020,1,1,0,0,0))
                item.create_system=3;item.external_attr=(0o100000 | (0o755 if name.endswith(('.sh','/MacOS/RadeonNI')) else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,content)
    print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__':main()
