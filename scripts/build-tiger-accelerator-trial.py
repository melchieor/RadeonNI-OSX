#!/usr/bin/env python3
"""Stage an experimental Tiger V7900 engine-only trial with rollback."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/tiger-v7900'


def load(name):
    spec=importlib.util.spec_from_file_location(name.replace('-','_'),ROOT/'scripts'/(name+'.py'))
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


firmware=load('stage-tiger-family-firmware')
fan=load('build-tiger-fan-trial')


def create_profile(baseline,payloads):
    firmware.validate(payloads)
    result=plistlib.loads(baseline)
    profiles=result['IOKitPersonalities']
    if len(profiles)!=1: raise ValueError('Expected exactly one V7900 profile')
    p=next(iter(profiles.values()))
    if p.get('IOPCIMatch')!='0x67041002' or p.get('Accelerator') or not p.get('TemperatureFanControl'):
        raise ValueError('Baseline is not the V7900 automatic fan framebuffer')
    if p.get('GAPlugin') or p.get('Surfaces'): raise ValueError('Unexpected baseline graphics settings')
    p['Accelerator']=True
    for kind in ('PFP','ME','MC'):
        p['FW_'+kind]=payloads['CAYMAN_'+kind.lower()+'.bin']
    # Keep GA, surfaces, capability advertising and cursor unchanged.
    return plistlib.dumps(result,fmt=plistlib.FMT_XML,sort_keys=False)


def main():
    archive=OUT/'fan-trial/RadeonNI-Tiger-V7900-FanTrial-c0a7f468-v2.zip'
    prefix='RadeonNI-Tiger-V7900-FanTrial/'
    with zipfile.ZipFile(archive) as z:
        manifest=json.loads(z.read(prefix+'manifest.json'))
        items=('trial/RadeonNI.kext/Contents/Info.plist','trial/RadeonNI.kext/Contents/MacOS/RadeonNI','rdn_fanprobe.so')
        base={name:z.read(prefix+name) for name in items}
        if z.testzip() or any(hashlib.sha256(v).hexdigest()!=manifest['files'][k] for k,v in base.items()):
            raise SystemExit('Fan trial archive integrity failed')
    base_plist=base[items[0]];binary=base[items[1]];digest=hashlib.sha256(binary).hexdigest()
    audit=json.loads((OUT/'experimental-validation-fan.json').read_text())['kernel']
    if (digest!=audit['sha256'] or audit['export_collisions'] or audit['unresolved_against_reference_union'] or
            audit['compatibility_alias_errors'] or any(audit['abi_comparisons'].values())):
        raise SystemExit('Kernel audit or baseline mismatch')
    payloads={name:(firmware.DESTINATION/name).read_bytes() for name in firmware.INPUTS}
    trial_plist=create_profile(base_plist,payloads)
    checks={'normal_profile_cksum':fan.cksum(base_plist),'normal_binary_cksum':fan.cksum(binary),
            'trial_profile_cksum':fan.cksum(trial_plist),'trial_binary_cksum':fan.cksum(binary)}
    script=(ROOT/'g5/tiger-fan-trial-manage.sh').read_text()
    script=script.replace('__PAYLOAD_CHECKSUMS__','\n'.join(k+"='"+v+"'" for k,v in checks.items()))
    script=script.replace('TigerFanTrial-__TRIAL_ID__','TigerEngineTrial-'+hashlib.sha256(trial_plist).hexdigest()[:8])
    if '__TRIAL_ID__' in script or '__PAYLOAD_CHECKSUMS__' in script: raise SystemExit('Unfilled template')
    readme='''EXPERIMENTAL TIGER V7900 ENGINE TEST; NOT FULL GRAPHICS ACCELERATION\n\nThe trial initializes the V7900 command processor and its firmware, which has\nnot been tested on Tiger. It can corrupt the display, hang or panic the G5.\nIt keeps the current automatic fan policy, and backs up that exact baseline.\nThe 2D plugin, surfaces, and OpenGL bundles are not installed or enabled.\nKeep a Tiger disk backup and NVIDIA card available. Do not use sleep.\n\nWhile in Tiger, run sudo sh ./manage.sh --install and retain the backup path;\nrestart only after the result is reviewed. After reboot run the included\nsudo sh ./collect.sh and share its output. Restore with\nsudo sh ./manage.sh --restore followed by restart. If necessary, shut down\nand boot with the NVIDIA card first. This package must be retained.\n'''
    collect=b'''#!/bin/sh\nPATH=/bin:/sbin:/usr/bin:/usr/sbin\nexport PATH\necho '=== RadeonNI and engine status ==='\nkextstat | grep -i RadeonNI\nioreg -c RadeonNIAccel -w 0\necho '=== RadeonNI recent log ==='\ngrep -i RadeonNI /var/log/system.log | tail -100\necho '=== Fan telemetry (90 seconds) ==='\n/usr/bin/python -E ./fan-sample.py\n'''
    files={'README.txt':readme.encode(),'manage.sh':script.encode(),
           'framebuffer-core.sh':(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes(),
           'fan-core.sh':(ROOT/'g5/tiger-fan-trial-core.sh').read_bytes(),
           'collect.sh':collect,'fan-sample.py':b'import rdn_fanprobe\nrdn_fanprobe.sample(90)\n',
           'rdn_fanprobe.so':base['rdn_fanprobe.so'],'LICENSE.radeon':payloads['LICENSE.radeon'],
           'normal/RadeonNI.kext/Contents/Info.plist':base_plist,
           'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':binary,
           'trial/RadeonNI.kext/Contents/Info.plist':trial_plist,
           'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':binary}
    files['manifest.json']=(json.dumps({'experimental':True,'engine_test_only':True,'kernel_sha256':digest,
       'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}},indent=2,sort_keys=True)+'\n').encode()
    identity=hashlib.sha256(trial_plist).hexdigest()[:8]
    dest=OUT/('accelerator-trial/RadeonNI-Tiger-V7900-EngineTrial-'+identity+'.zip')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,data in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-V7900-EngineTrial/'+name,(2020,1,1,0,0,0))
                item.create_system=3;item.external_attr=(0o100000 | (0o755 if name.endswith(('.sh','/MacOS/RadeonNI')) else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,data)
    print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__': main()
