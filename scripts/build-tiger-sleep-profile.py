#!/usr/bin/env python3
"""Package a reversible Tiger V7900 sleep-rehearsal profile, status only."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

root=Path(__file__).resolve().parents[1]
out=root/'build/tiger-v7900'
spec=importlib.util.spec_from_file_location('fan',root/'scripts/build-tiger-fan-trial.py')
fan=importlib.util.module_from_spec(spec);spec.loader.exec_module(fan)
source=out/'cursor-trial/RadeonNI-Tiger-V7900-CursorTrial-05070bba-v2.zip'
prefix='RadeonNI-Tiger-V7900-CursorTrial/'
with zipfile.ZipFile(source) as z:
    if z.testzip(): raise ValueError('Cursor archive corrupt')
    m=json.loads(z.read(prefix+'manifest.json'))
    data={n:z.read(prefix+n) for n in m['files']}
    for n,v in data.items():
        if hashlib.sha256(v).hexdigest()!=m['files'][n]: raise ValueError('Invalid input '+n)
base=data['trial/RadeonNI.kext/Contents/Info.plist']
binary=data['trial/RadeonNI.kext/Contents/MacOS/RadeonNI']
audit=json.loads((out/'experimental-validation-fan.json').read_text())['kernel']
if (hashlib.sha256(binary).hexdigest()!=audit['sha256'] or audit['export_collisions'] or
    audit['unresolved_against_reference_union'] or audit['compatibility_alias_errors'] or any(audit['abi_comparisons'].values())):
    raise ValueError('Kernel audit failed')
info=plistlib.loads(base)
if len(info['IOKitPersonalities'])!=1: raise ValueError('Unexpected personality count')
p=next(iter(info['IOKitPersonalities'].values()))
if (p.get('IOPCIMatch')!='0x67041002' or not all(p.get(k) for k in ('Accelerator','HWCursor','TemperatureFanControl','GAPlugin','Surfaces')) or p.get('AddAppleCinema1080p') or p.get('EnableSleepRehearsal')):
    raise ValueError('Unexpected baseline')
p['EnableSleepRehearsal']=True
trial=plistlib.dumps(info,fmt=plistlib.FMT_XML,sort_keys=False)
check=plistlib.loads(trial);del next(iter(check['IOKitPersonalities'].values()))['EnableSleepRehearsal']
if check != plistlib.loads(base): raise ValueError('Unexpected profile changes')
identity=hashlib.sha256(trial).hexdigest()[:8]
sums={'normal_profile_cksum':fan.cksum(base),'normal_binary_cksum':fan.cksum(binary),
      'trial_profile_cksum':fan.cksum(trial),'trial_binary_cksum':fan.cksum(binary)}
manager=(root/'g5/tiger-fan-trial-manage.sh').read_text().replace('__PAYLOAD_CHECKSUMS__','\n'.join(k+"='"+v+"'" for k,v in sums.items())).replace('TigerFanTrial-__TRIAL_ID__','TigerSleepProfile-'+identity)
if '__PAYLOAD_CHECKSUMS__' in manager or '__TRIAL_ID__' in manager: raise ValueError('Unfilled template')
status=out/'sleep-status/RadeonNI-Tiger-Sleep-Status.zip'
with zipfile.ZipFile(status) as z:
    if z.testzip(): raise ValueError('Status archive corrupt')
    s=json.loads(z.read('RadeonNI-Tiger-Sleep-Status/manifest.json'))
    stat={n:z.read('RadeonNI-Tiger-Sleep-Status/'+n) for n in s['files']}
    if any(hashlib.sha256(v).hexdigest()!=s['files'][n] for n,v in stat.items()): raise ValueError('Status archive digest mismatch')
files={'manage.sh':manager.encode(),'framebuffer-core.sh':(root/'g5/tiger-framebuffer-core.sh').read_bytes(),
       'fan-core.sh':(root/'g5/tiger-fan-trial-core.sh').read_bytes(),
       'normal/RadeonNI.kext/Contents/Info.plist':base,'normal/RadeonNI.kext/Contents/MacOS/RadeonNI':binary,
       'trial/RadeonNI.kext/Contents/Info.plist':trial,'trial/RadeonNI.kext/Contents/MacOS/RadeonNI':binary,
       'rdn_sleepstatus.so':stat['rdn_sleepstatus.so'],'status.py':stat['status.py'],
       'LICENSE.radeon':data['LICENSE.radeon'],'LICENSE.RadeonNI':data['LICENSE.RadeonNI']}
for n in ('rdn_fanprobe.so','rdn_glprobe.so','graphics-test.sh','fan-sample.py','gl-list.py','gl-draw.py'):files[n]=data[n]
files['README.txt']=b'''EXPERIMENTAL TIGER V7900 POWER-RETAINED STATUS PROFILE\n\nThis changes one profile property, enabling the EXISTING kernel rehearsal API.\nThe kernel binary, graphics plugins, fan policy and display modes are unchanged.\nIt does not implement system sleep or GPU restoration. Do not request sleep.\n\nPreserve a Tiger backup and NVIDIA recovery card. To install this profile:\n  sudo sh ./manage.sh --install\nSave the printed backup path, restart, and run ONLY:\n  /usr/bin/python -E ./status.py\nShare output and stop. No rehearsal executable is included in this package.\nRestore the exact baseline with sudo sh ./manage.sh --restore, then restart.\nIf video is lost, use SSH or boot with NVIDIA for recovery.\n'''
files['manifest.json']=(json.dumps({'experimental':True,'change':'EnableSleepRehearsal true','sleep_supported':False,
    'kernel_sha256':hashlib.sha256(binary).hexdigest(),'files':{n:hashlib.sha256(v).hexdigest() for n,v in files.items()}},indent=2,sort_keys=True)+'\n').encode()
dest=out/('sleep-profile/RadeonNI-Tiger-Sleep-Profile-'+identity+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
with dest.open('xb') as f:
    with zipfile.ZipFile(f,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for n,v in files.items():
            i=zipfile.ZipInfo('RadeonNI-Tiger-Sleep-Profile/'+n,(2020,1,1,0,0,0));i.create_system=3
            i.external_attr=(0o100000|(0o755 if n.endswith(('.sh','/MacOS/RadeonNI')) else 0o644))<<16
            i.compress_type=zipfile.ZIP_DEFLATED;z.writestr(i,v)
print(dest);print('sha256='+hashlib.sha256(dest.read_bytes()).hexdigest())
