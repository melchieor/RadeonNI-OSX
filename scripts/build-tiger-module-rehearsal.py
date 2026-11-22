#!/usr/bin/env python3
"""Package a nonpersistent kernel module registration experiment for Tiger."""
import hashlib
import json
from pathlib import Path
import plistlib
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'


def main():
    build = OUT / 'kernel-experiment/RadeonNI.kext/Contents'
    kernel = (build / 'MacOS/RadeonNI').read_bytes()
    report = json.loads((OUT / 'experimental-validation.json').read_text())['kernel']
    if (report['sha256'] != hashlib.sha256(kernel).hexdigest() or
            report['unresolved_against_reference_union'] or report['compatibility_alias_errors'] or report['export_collisions'] or
            any(report['abi_comparisons'].values())):
        raise SystemExit('Kernel differs from or failed its static audit')
    with (build / 'Info.plist').open('rb') as stream:
        info = plistlib.load(stream)
    info.pop('IOKitPersonalities', None)
    if info['CFBundleIdentifier'] != 'org.osxgpu.driver.RadeonNI':
        raise SystemExit('Unexpected bundle identifier')
    readme = '''EXPERIMENTAL TIGER MODULE TEST: KERNEL PANIC POSSIBLE

This is a nonpersistent experiment, not a driver installer. Save work and
ensure your Tiger disk is backed up. Boot Tiger 10.4.11 with the NVIDIA card.
The module is loaded into the kernel; kernel incompatibility can crash the
machine even without an AMD card. If it crashes, restart; do not repeat it.
The temporary module is not copied into /System/Library/Extensions and is
not configured to load at boot. Keep the existing graphics card installed.

The test profile has NO device-matching IOKit personalities. The test uses
kextload -l; the loader may send an internal module-demand record even with
no device profile. The test loads and starts the module. It does not
test display output, acceleration, AMD hardware, fans, sleep or unloading.
It refuses to run if RadeonNI is already loaded or installed at its standard
location. It leaves a root-owned temporary copy in /tmp, since the module may
still be loaded, and does not automatically unload it. Restart after testing.

From this extracted directory:
  sudo sh ./run-module-test.sh --i-understand-runtime-risk > ~/Desktop/radeon-tiger-module-report.txt 2>&1
  cat ~/Desktop/radeon-tiger-module-report.txt

If the computer panics or freezes, restart Tiger. The report, the new panic
log in /Library/Logs/panic.log or /Library/Logs/PanicReporter, and relevant
RadeonNI lines from /var/log/system.log may help diagnose it. Review logs
before sharing. Do not repeat after a panic or force the module to load.
'''
    files = {'README.txt': readme.encode(),
             'run-module-test.sh': (ROOT / 'g5/tiger-module-rehearsal.sh').read_bytes(),
             'RadeonNI.kext/Contents/Info.plist': plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False),
             'RadeonNI.kext/Contents/MacOS/RadeonNI': kernel}
    manifest = {'purpose': 'nonpersistent kernel registration experiment', 'installable': False,
                'device_personalities': 0, 'fan_control': False,
                'files': {n: hashlib.sha256(d).hexdigest() for n, d in files.items()}}
    files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    destination = OUT / ('module-rehearsal/RadeonNI-Tiger-Module-Rehearsal-' + report['sha256'][:8] + '.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                item = zipfile.ZipInfo('RadeonNI-Tiger-Module-Rehearsal/' + name, (2020, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = (0o100000 | (0o755 if name in ('run-module-test.sh', 'RadeonNI.kext/Contents/MacOS/RadeonNI') else 0o644)) << 16
                item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, data)
    print(destination)
    print('sha256=' + hashlib.sha256(destination.read_bytes()).hexdigest())
    print('EXPERIMENTAL KERNEL MODULE; CAN PANIC; NOT INSTALLABLE')


if __name__ == '__main__':
    main()
