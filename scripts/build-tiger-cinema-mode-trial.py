#!/usr/bin/env python3
"""Prepare an opt-in Apple Cinema 1080p Tiger mode trial with rollback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
spec=importlib.util.spec_from_file_location('fan_trial',ROOT/'scripts/build-tiger-fan-trial.py')
fan=importlib.util.module_from_spec(spec);spec.loader.exec_module(fan)


def trial_profile(data):
    info=plistlib.loads(data);profiles=info['IOKitPersonalities']
    if len(profiles)!=1:raise ValueError('Expected exactly one V7900 profile')
    p=next(iter(profiles.values()))
    if (p.get('IOPCIMatch')!='0x67041002' or not p.get('Accelerator') or not p.get('GAPlugin') or
            not p.get('HWCursor') or not p.get('TemperatureFanControl') or p.get('AddAppleCinema1080p')):
        raise ValueError('Unexpected cursor/fan graphics baseline')
    p['AddAppleCinema1080p']=True
    return plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False)


def main():
    archive=OUT/'cursor-trial/RadeonNI-Tiger-V7900-CursorTrial-05070bba-v2.zip'
    prefix='RadeonNI-Tiger-V7900-CursorTrial/'
    with zipfile.ZipFile(archive) as z:
        if z.testzip():raise SystemExit('Cursor baseline archive CRC failure')
        manifest=json.loads(z.read(prefix+'manifest.json'))
        names=('trial/RadeonNI.kext/Contents/Info.plist','trial/RadeonNI.kext/Contents/MacOS/RadeonNI',
               'rdn_fanprobe.so','rdn_glprobe.so','graphics-test.sh','fan-sample.py','gl-list.py','gl-draw.py',
               'LICENSE.radeon','LICENSE.RadeonNI')
        data={n:z.read(prefix+n) for n in names}
        if any(hashlib.sha256(d).hexdigest()!=manifest['files'][n] for n,d in data.items()):
            raise SystemExit('Cursor baseline archive digest mismatch')
    old_profile=data[names[0]];old_kernel=data[names[1]]
    candidate=(OUT/'kernel-cinema-experiment/RadeonNI.kext/Contents/MacOS/RadeonNI').read_bytes()
    audit=json.loads((OUT/'experimental-validation-cinema.json').read_text())['kernel']
    if (hashlib.sha256(candidate).hexdigest()!=audit['sha256'] or audit['export_collisions'] or
            audit['unresolved_against_reference_union'] or audit['compatibility_alias_errors'] or
            any(audit['abi_comparisons'].values())):
        raise SystemExit('Cinema kernel static audit failed')
    new_profile=trial_profile(old_profile)
    identity=hashlib.sha256(candidate+new_profile).hexdigest()[:8]
    values={'normal_profile_cksum':fan.cksum(old_profile),'normal_binary_cksum':fan.cksum(old_kernel),
            'trial_profile_cksum':fan.cksum(new_profile),'trial_binary_cksum':fan.cksum(candidate)}
    manager=(ROOT/'g5/tiger-fan-trial-manage.sh').read_text()
    manager=manager.replace('__PAYLOAD_CHECKSUMS__','\n'.join(k+"='"+v+"'" for k,v in values.items()))
    manager=manager.replace('TigerFanTrial-__TRIAL_ID__','TigerCinemaTrial-'+identity)
    if '__PAYLOAD_CHECKSUMS__' in manager or '__TRIAL_ID__' in manager:raise SystemExit('Unfilled template')
    files={'manage.sh':manager.encode(),'framebuffer-core.sh':(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes(),
           'fan-core.sh':(ROOT/'g5/tiger-fan-trial-core.sh').read_bytes(),
           'normal/RadeonNI.kext/Contents/Info.plist':old_profile,
           'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':old_kernel,
           'trial/RadeonNI.kext/Contents/Info.plist':new_profile,
           'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':candidate}
    for n in names[2:]:files[n]=data[n]
    files['mode-check.sh']=b'''#!/bin/sh\nPATH=/bin:/sbin:/usr/bin:/usr/sbin\nexport PATH\necho '=== Driver modes in current kernel buffer ==='\ndmesg | grep 'RadeonNI: mode' || :\necho '=== Current display ==='\nsystem_profiler SPDisplaysDataType\n'''
    files['README.txt']=b'''EXPERIMENTAL TIGER APPLE CINEMA 1080P MODE\n\nThis V7900 trial offers one additional 1920x1080p60 CTA timing only when\nthe EDID matches Apple vendor 0610, product 9226, a 2560x1440 preferred\ntiming and a valid base checksum. The EDID need not advertise that mode.\nApple lists 1080p as supported, but this exact signal path and timing have\nnot been tested. It also corrects CTA VIC 16 sync polarity generally.\n\nThe preferred 2560x1440 mode is unchanged. Changing modes can lose video;\nit may persist across reboot. Keep a Tiger backup, SSH and the NVIDIA card\navailable. Full-screen scaling is not guaranteed. Do not use sleep.\n\nRun sudo sh ./manage.sh --install and save the backup path. Restart after\nreview. Run sh ./mode-check.sh before selecting another mode. To restore:\nsudo sh ./manage.sh --restore followed by restart; use the NVIDIA card if\nnecessary. Preserve this extracted directory and the printed backup.\n'''
    manifest={'experimental':True,'hardware_tested':False,'extra_mode':'1920x1080p60 CTA',
              'kernel_sha256':hashlib.sha256(candidate).hexdigest(),
              'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}}
    files['manifest.json']=(json.dumps(manifest,indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('cinema-trial/RadeonNI-Tiger-Cinema1080-Trial-'+identity+'.zip')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for n,d in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-Cinema1080-Trial/'+n,(2020,1,1,0,0,0));item.create_system=3
                item.external_attr=(0o100000|(0o755 if n.endswith(('.sh','/MacOS/RadeonNI')) else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,d)
    print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__':main()
