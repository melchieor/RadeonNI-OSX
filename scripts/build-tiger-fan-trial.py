#!/usr/bin/env python3
"""Build a controlled Tiger V7900 fan trial with the verified baseline."""
import hashlib
import json
from pathlib import Path
import plistlib
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'
BASE_SHA = '87052c7190fc7a317dbcb90ccf7bd1729d841bea51619b0e8d9519976e49b864'


def cksum(data):
    out = subprocess.check_output(['cksum'], input=data).decode().split()
    return out[0] + ':' + out[1]


def main():
    baseline_archive = OUT/'framebuffer-test/RadeonNI-Tiger-V7900-Framebuffer-87052c71.zip'
    with zipfile.ZipFile(baseline_archive) as z:
        if z.testzip(): raise SystemExit('Bad baseline archive')
        root = 'RadeonNI-Tiger-V7900-Framebuffer/payload/RadeonNI.kext/Contents/'
        baseline_plist = z.read(root+'Info.plist')
        baseline_binary = z.read(root+'MacOS/RadeonNI')
    if hashlib.sha256(baseline_binary).hexdigest() != BASE_SHA:
        raise SystemExit('Unexpected baseline kernel')
    info = plistlib.loads(baseline_plist)
    profiles = info['IOKitPersonalities']
    if len(profiles) != 1:
        raise SystemExit('Unexpected baseline profiles')
    entry = next(iter(profiles.values()))
    if entry.get('IOPCIMatch') != '0x67041002' or entry.get('Accelerator') or entry.get('TemperatureFanControl'):
        raise SystemExit('Unexpected baseline settings')
    entry['TemperatureFanControl'] = True
    trial_plist = plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False)
    trial_binary = (OUT/'kernel-fan-experiment/RadeonNI.kext/Contents/MacOS/RadeonNI').read_bytes()
    digest = hashlib.sha256(trial_binary).hexdigest()
    audit = json.loads((OUT/'experimental-validation-fan.json').read_text())['kernel']
    if (audit['sha256'] != digest or audit['export_collisions'] or audit['unresolved_against_reference_union'] or
            audit['compatibility_alias_errors'] or any(audit['abi_comparisons'].values())):
        raise SystemExit('Fan kernel static audit failed')
    with zipfile.ZipFile(OUT/'telemetry/RadeonNI-Tiger-Fan-Telemetry.zip') as z:
        base='RadeonNI-Tiger-Fan-Telemetry/'
        manifest=json.loads(z.read(base+'manifest.json'))
        telemetry=z.read(base+'rdn_fanprobe.so')
        if z.testzip() or hashlib.sha256(telemetry).hexdigest()!=manifest['files']['rdn_fanprobe.so']:
            raise SystemExit('Telemetry archive failed integrity check')
    data = {'normal_profile_cksum': cksum(baseline_plist), 'normal_binary_cksum': cksum(baseline_binary),
            'trial_profile_cksum': cksum(trial_plist), 'trial_binary_cksum': cksum(trial_binary)}
    script=(ROOT/'g5/tiger-fan-trial-manage.sh').read_text()
    script=script.replace('__PAYLOAD_CHECKSUMS__','\n'.join(k+"='"+v+"'" for k,v in data.items()))
    script=script.replace('__TRIAL_ID__',digest[:8])
    if '__PAYLOAD_CHECKSUMS__' in script or '__TRIAL_ID__' in script: raise SystemExit('Unfilled tokens')
    readme='''EXPERIMENTAL TIGER V7900 FAN TRIAL: KEEP A RECOVERY DISPLAY\n\nThe 40% floor and fault responses are untested on Tiger. The policy starts\nat 100%, requires healthy telemetry and ramps down gradually. It requests\nfull fan after sensor, timing, or PWM errors when the controller runs. A\nkernel hang, stalled timer, misleading sensor or hardware fault may defeat\nsoftware safeguards. Do not use sleep. Stop on abnormal fan or temperature\nbehavior; shut down and use the NVIDIA card for recovery if needed.\n\nThe installer backs up the current framebuffer kext and will not replace a\ndifferent version. Keep this directory and note the printed backup path.\nRun sudo sh ./manage.sh --install, then restart. Monitor immediately with\nsudo /usr/bin/python -E ./fan-sample.py. Record the full 90 seconds.\nRestore the full-speed baseline with sudo sh ./manage.sh --restore and\nrestart; if there is no display, shut down and boot with NVIDIA first.\nThe package does not enable acceleration or remove the startup test pattern.\n'''
    files={'README.txt':readme.encode(),'manage.sh':script.encode(),
           'framebuffer-core.sh':(ROOT/'g5/tiger-framebuffer-core.sh').read_bytes(),
           'fan-core.sh':(ROOT/'g5/tiger-fan-trial-core.sh').read_bytes(),
           'fan-sample.py':b'import rdn_fanprobe\nrdn_fanprobe.sample(90)\n',
           'rdn_fanprobe.so':telemetry,
           'normal/RadeonNI.kext/Contents/Info.plist':baseline_plist,
           'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':baseline_binary,
           'trial/RadeonNI.kext/Contents/Info.plist':trial_plist,
           'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':trial_binary}
    files['manifest.json']=(json.dumps({'experimental':True,'baseline_sha256':BASE_SHA,'trial_sha256':digest,
        'files':{n:hashlib.sha256(d).hexdigest() for n,d in files.items()}},indent=2,sort_keys=True)+'\n').encode()
    dest=OUT/('fan-trial/RadeonNI-Tiger-V7900-FanTrial-'+digest[:8]+'-v2.zip')
    dest.parent.mkdir(parents=True,exist_ok=True)
    with dest.open('xb') as f:
        with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for name,content in files.items():
                item=zipfile.ZipInfo('RadeonNI-Tiger-V7900-FanTrial/'+name,(2020,1,1,0,0,0))
                item.create_system=3;item.external_attr=(0o100000 | (0o755 if name.endswith(('.sh','/MacOS/RadeonNI')) else 0o644))<<16
                item.compress_type=zipfile.ZIP_DEFLATED;z.writestr(item,content)
    print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())


if __name__=='__main__': main()
