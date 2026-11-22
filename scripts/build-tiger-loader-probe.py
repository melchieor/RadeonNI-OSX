#!/usr/bin/env python3
"""Build a non-installing Tiger kernel-extension diagnostic archive."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'
spec = importlib.util.spec_from_file_location('tiger_profiles', ROOT / 'scripts/configure-tiger-experimental-profiles.py')
profiles = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profiles)


def main():
    destination = OUT / 'loader-probe/RadeonNI-Tiger-Loader-Probe.zip'
    kernel = (OUT / 'kernel-experiment/RadeonNI.kext/Contents/MacOS/RadeonNI').read_bytes()
    report = json.loads((OUT / 'experimental-validation.json').read_text())
    audit = report['kernel']
    if (audit['sha256'] != hashlib.sha256(kernel).hexdigest() or
            audit['unresolved_against_reference_union'] or audit['compatibility_alias_errors'] or audit['export_collisions'] or
            any(audit['abi_comparisons'].values())):
        raise SystemExit('Baseline kernel differs from or failed its static audit')
    payloads = {name: (profiles.firmware.DESTINATION / name).read_bytes() for name in profiles.firmware.INPUTS}
    with (ROOT / 'kext/RadeonNI/Info.plist').open('rb') as stream:
        profile = profiles.profiles(plistlib.load(stream), payloads, fan=False)
    if any(p.get('TemperatureFanControl', False) for p in profile['IOKitPersonalities'].values()):
        raise SystemExit('Fan control must not be enabled in this diagnostic')
    readme = '''Tiger 10.4.11 PowerPC loader diagnostic; NOT A DRIVER INSTALLER

This bundle tests the experimental RadeonNI kernel extension without loading
it, matching the device, or installing a driver. It does not test the fan,
OpenGL, display output, GPU behavior, or sleep. Do not install this kext.
The script creates and deletes a root-owned copy in /tmp. The -c option tells
kextload to scan extensions rather than create or use its repository cache.
Output may contain machine details; review it before sharing.

On the Tiger desktop, in Terminal, from this extracted directory:
  sudo sh ./check-tiger-loader.sh > ~/Desktop/radeon-tiger-loader-report.txt 2>&1
  cat ~/Desktop/radeon-tiger-loader-report.txt

A successful check is preliminary and is not evidence of runtime safety.
The extension can still fail or panic when actually loaded. Nothing in this
archive installs or loads the extension. Firmware is embedded only as data in
the experimental profile; LICENSE.radeon is included for that firmware.
'''
    files = {
        'README.txt': readme.encode(),
        'check-tiger-loader.sh': (ROOT / 'g5/tiger-loader-probe.sh').read_bytes(),
        'RadeonNI.kext/Contents/Info.plist': plistlib.dumps(profile, fmt=plistlib.FMT_XML, sort_keys=False),
        'RadeonNI.kext/Contents/MacOS/RadeonNI': kernel,
        'LICENSE.radeon': payloads['LICENSE.radeon'],
    }
    manifest = {'purpose': 'non-loading validation only', 'installable': False,
                'firmware_commit': profiles.firmware.REVISION,
                'kernel_sha256': audit['sha256'],
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                info = zipfile.ZipInfo('RadeonNI-Tiger-Loader-Probe/' + name, (2020, 1, 1, 0, 0, 0))
                info.create_system = 3
                mode = 0o755 if name in ('check-tiger-loader.sh', 'RadeonNI.kext/Contents/MacOS/RadeonNI') else 0o644
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
    print(destination)
    print('sha256=' + hashlib.sha256(destination.read_bytes()).hexdigest())
    print('NON-LOADING DIAGNOSTIC ONLY; NOT INSTALLABLE')


if __name__ == '__main__':
    main()
