#!/usr/bin/env python3
"""Package the private, power-retained indexed VRAM diagnostic for this G5."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

root = Path(__file__).resolve().parents[1]
base = root / 'build/tiger-v7900/index-baseline-20261117/RadeonNI.kext/Contents'
probe = root / 'build/tiger-v7900/sleep-index-probe-20261117'
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
if 'EnableIndexedVramRehearsal' in personality:
    raise SystemExit('Diagnostic is already enabled')
personality['EnableIndexedVramRehearsal'] = True
trial_profile = plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False)
spec = importlib.util.spec_from_file_location('fan', root / 'scripts/build-tiger-fan-trial.py')
fan = importlib.util.module_from_spec(spec)
spec.loader.exec_module(fan)
checks = {'normal_profile_cksum': fan.cksum(original), 'normal_binary_cksum': fan.cksum(original_binary),
          'trial_profile_cksum': fan.cksum(trial_profile), 'trial_binary_cksum': fan.cksum(binary)}
manager = (root / 'g5/tiger-fan-trial-manage.sh').read_text().replace(
    '__PAYLOAD_CHECKSUMS__', '\n'.join(k + "='" + v + "'" for k, v in checks.items())).replace(
    'TigerFanTrial-__TRIAL_ID__', 'TigerIndexProbe-20261117')
files = {'manage.sh': manager.encode(),
         'framebuffer-core.sh': (root / 'g5/tiger-framebuffer-core.sh').read_bytes(),
         'fan-core.sh': (root / 'g5/tiger-fan-trial-core.sh').read_bytes(),
         'normal/RadeonNI.kext/Contents/Info.plist': original,
         'normal/RadeonNI.kext/Contents/MacOS/RadeonNI': original_binary,
         'trial/RadeonNI.kext/Contents/Info.plist': trial_profile,
         'trial/RadeonNI.kext/Contents/MacOS/RadeonNI': binary}
archive = root / 'build/tiger-v7900/index-rehearsal-20261117-v2/RadeonNI-Tiger-Index-Rehearsal.zip'
with zipfile.ZipFile(archive) as z:
    if z.testzip(): raise SystemExit('Diagnostic archive failed CRC check')
    for name in ('rdn_index_rehearsal.so', 'rehearse.py', 'rdn_fanprobe.so', 'fan-sample.py', 'rdn_sleepstatus.so', 'status.py'):
        files[name] = z.read('RadeonNI-Tiger-Index-Rehearsal/' + name)
files['README.txt'] = b'''EXPERIMENTAL TIGER V7900 INDEXED VRAM TEST\n\nOnly for the G5 whose current kext was captured as this package's baseline.\nThe diagnostic changes the kernel binary. It does not support system sleep.\nSave work. A GPU hang, panic, or lost display is possible. Keep SSH and the\noriginal graphics card available. Install: sudo sh ./manage.sh --install\nRestart only after saving work. Then run sudo sh ./run-test.sh once.\nIt writes and copies data inside a private page and briefly increases the fan.\nRestore: sudo sh ./manage.sh --restore, then restart. The exact previous kext\nis saved in /Library/Application Support/RadeonNI/TigerIndexProbe-20261117.\nA pass tests only a small powered VRAM comparison, not sleep or hidden VRAM.\n'''
files['run-test.sh'] = b'''#!/bin/sh\nset -u\n[ "$(id -u)" = 0 ] || { echo 'Run as root.' >&2; exit 1; }\ncd "$(dirname "$0")" || exit 1\nbefore=$(dmesg | grep -c 'indexed VRAM rehearsal aperture comparison' || :)\n[ "$before" = 0 ] || { echo 'Existing diagnostic log: restart before testing.' >&2; exit 1; }\nout=$(mktemp /tmp/radeon-index-test.XXXXXXXX) || exit 1\n/usr/bin/python -E ./rehearse.py > "$out" 2>&1\nresult=$?\ncat "$out"\nrm -f "$out"\n[ "$result" = 0 ] || { echo 'Rehearsal failed; stop.' >&2; exit 1; }\nline=$(dmesg | grep 'indexed VRAM rehearsal aperture comparison' | tail -1)\necho "$line"\ncase "$line" in *'0 mismatched bytes of 16'*) echo 'INDEX_COMPARISON_PASS' ;; *) echo 'Indexed comparison missing or failed; stop.' >&2; exit 1 ;; esac\n'''
files['manifest.json'] = (json.dumps({'experimental': True, 'sleep_supported': False,
    'scope': 'private visible 16-byte GPU copy and indexed read; power retained',
    'files': {n: hashlib.sha256(v).hexdigest() for n, v in files.items()}}, indent=2, sort_keys=True)+'\n').encode()
dest = root / 'build/tiger-v7900/RadeonNI-Tiger-Index-Probe-20261117.zip'
with dest.open('xb') as f:
    with zipfile.ZipFile(f, 'w', compression=zipfile.ZIP_DEFLATED) as z:
        for name, data in files.items():
            entry = zipfile.ZipInfo('RadeonNI-Tiger-Index-Probe/' + name, (2020, 1, 1, 0, 0, 0))
            entry.create_system = 3
            entry.external_attr = (0o100000 | (0o755 if name.endswith(('.sh', '/MacOS/RadeonNI')) else 0o644)) << 16
            entry.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(entry, data)
print(dest, hashlib.sha256(dest.read_bytes()).hexdigest())
