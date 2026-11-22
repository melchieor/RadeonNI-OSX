#!/usr/bin/env python3
"""Package the private, power-retained indexed VRAM diagnostic for this G5."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

root = Path(__file__).resolve().parents[1]
base = root / 'build/tiger-v7900/hidden-write-current-20261117/RadeonNI.kext/Contents'
probe = root / 'build/tiger-v7900/sleep-index-probe-hidden-range2-20261117'
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
    'TigerFanTrial-__TRIAL_ID__', 'TigerHiddenRangeProbe-20261117')
files = {'manage.sh': manager.encode(),
         'framebuffer-core.sh': (root / 'g5/tiger-framebuffer-core.sh').read_bytes(),
         'fan-core.sh': (root / 'g5/tiger-fan-trial-core.sh').read_bytes(),
         'normal/RadeonNI.kext/Contents/Info.plist': original,
         'normal/RadeonNI.kext/Contents/MacOS/RadeonNI': original_binary,
         'trial/RadeonNI.kext/Contents/Info.plist': trial_profile,
         'trial/RadeonNI.kext/Contents/MacOS/RadeonNI': binary}
archive = root / 'build/tiger-v7900/hidden-index-range-rehearsal-20261117/RadeonNI-Tiger-Hidden-Index-Range-Rehearsal.zip'
with zipfile.ZipFile(archive) as z:
    if z.testzip(): raise SystemExit('Diagnostic archive failed CRC check')
    for name in ('rdn_hidden_index_rehearsal.so', 'rehearse.py', 'rdn_fanprobe.so', 'fan-sample.py', 'rdn_sleepstatus.so', 'status.py'):
        files[name] = z.read('RadeonNI-Tiger-Hidden-Index-Range-Rehearsal/' + name)
files['README.txt'] = b"""EXPERIMENTAL TIGER V7900 HIDDEN-VRAM TEST\n\nFor the G5 with the previous indexed diagnostic installed only. The test\nwrites 16 bytes to a new private hidden VRAM page using the GPU, reads that\npage through the indexed register window, then copies it back with the GPU.\nIt also writes a 1024-byte pattern using the indexed window and tests GPU readback.\nIt retains power, does not request sleep, and can hang or panic. Save work.\nA timed-out transfer leaves the test process holding its allocations and\nrequires a restart; do not kill that process. Process/device failure can still\ndefeat retention. Install with sudo sh ./manage.sh --install, restart, then\nrun sudo sh ./run-test.sh once. Restore with sudo sh ./manage.sh --restore\nand restart. The backup is at /Library/Application Support/RadeonNI/\nTigerHiddenRangeProbe-20261117/RadeonNI.kext.\nA pass is not proof of sleep, provider removal safety or complete restoration.\n"""
files['run-test.sh'] = b"""#!/bin/sh\nset -u\n[ \"$(id -u)\" = 0 ] || { echo 'Run as root.' >&2; exit 1; }\ncd \"$(dirname \"$0\")\" || exit 1\nexec /usr/bin/python -E ./rehearse.py\n"""
files['manifest.json'] = (json.dumps({'experimental': True, 'sleep_supported': False,
    'scope': 'private hidden 1024-byte indexed write and GPU copy; power retained',
    'files': {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}}, indent=2, sort_keys=True)+'\n').encode()
dest = root / 'build/tiger-v7900/RadeonNI-Tiger-Hidden-Range-Probe-20261117.zip'
with dest.open('xb') as f:
    with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            entry = zipfile.ZipInfo('RadeonNI-Tiger-Hidden-Range-Probe/' + name, (2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100000 | (0o755 if name.endswith(('.sh', '/MacOS/RadeonNI')) else 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
print(dest, hashlib.sha256(dest.read_bytes()).hexdigest())
