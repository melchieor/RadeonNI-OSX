#!/usr/bin/env python3
"""Package the private, power-retained indexed VRAM diagnostic for this G5."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

root = Path(__file__).resolve().parents[1]
base = root / 'build/tiger-v7900/hidden-snapshot-current-20261117/RadeonNI.kext/Contents'
probe = root / 'build/tiger-v7900/sleep-index-probe-live-plan-v2-20261117'
report = json.loads((probe / 'validation.json').read_text())['kernel']
binary = (probe / 'kernel/RadeonNI.kext/Contents/MacOS/RadeonNI').read_bytes()
if hashlib.sha256(binary).hexdigest() != report['sha256'] or any(
        report[k] for k in ('unresolved_against_reference_union', 'compatibility_alias_errors', 'export_collisions')) or any(report['abi_comparisons'].values()):
    raise SystemExit('Diagnostic kext static audit failed')
original = (base / 'Info.plist').read_bytes()
original_binary = (base / 'MacOS/RadeonNI').read_bytes()
info = plistlib.loads(original)
personalities = info['IOKitPersonalities']
if len(personalities) != 1:
    raise SystemExit('Unexpected personality count')
personality = next(iter(personalities.values()))
if personality.get('IOPCIMatch') != '0x67041002' or not all(personality.get(k) for k in ('EnableSleepRehearsal', 'TemperatureFanControl', 'Accelerator', 'HWCursor')):
    raise SystemExit('Unexpected installed profile')
if personality.get('EnableIndexedVramRehearsal') is not True:
    raise SystemExit('Indexed diagnostic is not enabled')
trial_profile = original
spec = importlib.util.spec_from_file_location('fan', root / 'scripts/build-tiger-fan-trial.py')
fan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fan)
checks = {'normal_profile_cksum': fan.cksum(original), 'normal_binary_cksum': fan.cksum(original_binary),
          'trial_profile_cksum': fan.cksum(trial_profile), 'trial_binary_cksum': fan.cksum(binary)}
manager = (root / 'g5/tiger-fan-trial-manage.sh').read_text().replace(
    '__PAYLOAD_CHECKSUMS__', '\n'.join(k + "='" + v + "'" for k, v in checks.items())).replace(
    'TigerFanTrial-__TRIAL_ID__', 'TigerLivePlanProbe-20261117')
files = {'manage.sh': manager.encode(),
         'framebuffer-core.sh': (root / 'g5/tiger-framebuffer-core.sh').read_bytes(),
         'fan-core.sh': (root / 'g5/tiger-fan-trial-core.sh').read_bytes(),
         'normal/RadeonNI.kext/Contents/Info.plist': original,
         'normal/RadeonNI.kext/Contents/MacOS/RadeonNI': original_binary,
         'trial/RadeonNI.kext/Contents/Info.plist': trial_profile,
         'trial/RadeonNI.kext/Contents/MacOS/RadeonNI': binary}
archive = root / 'build/tiger-v7900/hidden-snapshot-batch-20261117/RadeonNI-Tiger-Hidden-Snapshot-Batch.zip'
with zipfile.ZipFile(archive) as z:
    if z.testzip(): raise SystemExit('Diagnostic archive failed CRC check')
    for name in ('rdn_hidden_batch.so', 'rehearse.py', 'run-batch.sh', 'rdn_fanprobe.so', 'fan-sample.py', 'rdn_sleepstatus.so', 'status.py'):
        files[name] = z.read('RadeonNI-Tiger-Hidden-Snapshot-Batch/' + name)
with zipfile.ZipFile(root/'build/tiger-v7900/live-plan-check-20261117-v2/RadeonNI-Tiger-Live-Plan-Check-v2.zip') as z:
    if z.testzip(): raise SystemExit('Live plan archive failed CRC check')
    prefix='RadeonNI-Tiger-Live-Plan-Check-v2/'
    manifest=json.loads(z.read(prefix+'manifest.json'))
    for name in ('rdn_live_plan.so','rehearse.py'):
        data=z.read(prefix+name)
        if hashlib.sha256(data).hexdigest()!=manifest['files'][name]: raise SystemExit('Live plan diagnostic hash mismatch')
        files['rdn_live_plan.so' if name.endswith('.so') else 'live-plan.py']=data
files['full-batch.sh']=b'''#!/bin/sh\nset -u\n[ "$(id -u)" = 0 ] || exit 1\ncd "$(dirname "$0")" || exit 1\necho LIVE_PLAN_BEFORE\n/usr/bin/python -E ./live-plan.py || exit 1\nsh ./run-batch.sh || exit 1\necho LIVE_PLAN_AFTER\n/usr/bin/python -E ./live-plan.py || exit 1\necho COMPLETE\n'''
files['README.txt'] = b"""EXPERIMENTAL TIGER V7900 HIDDEN-VRAM TEST\n\nFor the G5 with the previous indexed diagnostic installed only. The test\nwrites 16 bytes to a new private hidden VRAM page using the GPU, reads that\npage through the indexed register window, then copies it back with the GPU.\nIt also captures live allocator metadata and restores three private pages.\nIt retains power, does not request sleep, and can hang or panic. Save work.\nA timed-out transfer leaves the test process holding its allocations and\nrequires a restart; do not kill that process. Process/device failure can still\ndefeat retention. Install with sudo sh ./manage.sh --install, restart, then\nrun sudo sh ./run-test.sh once. Restore with sudo sh ./manage.sh --restore\nand restart. The backup is at /Library/Application Support/RadeonNI/\nTigerLivePlanProbe-20261117/RadeonNI.kext.\nA pass is not proof of sleep, provider removal safety or complete restoration.\n"""
files['run-test.sh'] = b"""#!/bin/sh\nset -u\n[ \"$(id -u)\" = 0 ] || { echo 'Run as root.' >&2; exit 1; }\ncd \"$(dirname \"$0\")\" || exit 1\nexec sh ./full-batch.sh\n"""
files['manifest.json'] = (json.dumps({'experimental': True, 'sleep_supported': False,
    'scope': 'live VRAM metadata plan plus private hidden snapshot batch; power retained',
    'files': {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}}, indent=2, sort_keys=True)+'\n').encode()
dest = root / 'build/tiger-v7900/RadeonNI-Tiger-Live-Plan-Probe-20261117.zip'
with dest.open('xb') as f:
    with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            entry = zipfile.ZipInfo('RadeonNI-Tiger-Live-Plan-Probe/' + name, (2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100000 | (0o755 if name.endswith(('.sh', '/MacOS/RadeonNI')) else 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
print(dest, hashlib.sha256(dest.read_bytes()).hexdigest())
