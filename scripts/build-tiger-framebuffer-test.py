#!/usr/bin/env python3
"""Build the V7900 framebuffer-only Tiger controlled test archive."""
import hashlib
import importlib.util
import json
from pathlib import Path
import plistlib
import subprocess
import zipfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'
TESTED_KERNEL = '87052c7190fc7a317dbcb90ccf7bd1729d841bea51619b0e8d9519976e49b864'
spec = importlib.util.spec_from_file_location('tiger_framebuffer_profile', ROOT / 'scripts/configure-tiger-v7900-framebuffer.py')
profile_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(profile_module)


def posix_cksum(data):
    parts = subprocess.check_output(['cksum'], input=data).decode().split()
    return parts[0] + ':' + parts[1]


def main():
    kernel = (OUT / 'kernel-experiment/RadeonNI.kext/Contents/MacOS/RadeonNI').read_bytes()
    digest = hashlib.sha256(kernel).hexdigest()
    report = json.loads((OUT / 'experimental-validation.json').read_text())['kernel']
    if (digest != TESTED_KERNEL or digest != report['sha256'] or report['export_collisions'] or
            report['unresolved_against_reference_union'] or report['compatibility_alias_errors'] or
            any(report['abi_comparisons'].values())):
        raise SystemExit('Kernel is not the audited build successfully registered on the Tiger G5')
    with (ROOT / 'kext/RadeonNI/Info.plist').open('rb') as f:
        info = profile_module.profile(plistlib.load(f))
    encoded = plistlib.dumps(info, fmt=plistlib.FMT_XML, sort_keys=False)
    manage = (ROOT / 'g5/tiger-framebuffer-manage.sh').read_text()
    for token, value in (('__EXPECTED_PLIST_CKSUM__', posix_cksum(encoded)),
                         ('__EXPECTED_BINARY_CKSUM__', posix_cksum(kernel))):
        if manage.count(token) != 1:
            raise SystemExit('Missing or repeated checksum token')
        manage = manage.replace(token, value)
    readme = '''EXPERIMENTAL Tiger 10.4.11 V7900 framebuffer-only test

This is the first Tiger attachment test on this V7900. It may show no video,
freeze, or panic, and the fan may run at full speed. Automatic fan control,
OpenGL acceleration, Quartz Extreme, and sleep are not tested or provided.
Use only after backing up Tiger and ensuring the NVIDIA card and its original
power cable are available for recovery. Do not flash the GPU or change its ROM.

While running Tiger with the NVIDIA card installed, and after reviewing this
archive and keeping it available on the Tiger disk, run:
  sudo sh ./manage.sh --install
Save the output. Shut down and unplug the G5 before swapping the card and
transferring its PCIe power cable. On V7900 there may be no boot screen or
desktop at all. Wait for boot before assessing video. If it fails, power down,
reinstall the NVIDIA card and cable, boot Tiger, return to this directory and:
  sudo sh ./manage.sh --remove
  sudo shutdown -r now

The installer refuses to overwrite an existing RadeonNI.kext. Removal refuses
to remove a bundle that differs from this package. No other graphics bundles
are replaced. Keep the archive so recovery has the matching payload. The
script invalidates the system's rebuildable extension caches; installation
and removal do not unload the driver. The package is experimental; loading
the kernel module on NVIDIA did not test actual V7900 device attachment.
'''
    files = {'README.txt': readme.encode(), 'manage.sh': manage.encode(),
             'core.sh': (ROOT / 'g5/tiger-framebuffer-core.sh').read_bytes(),
             'payload/RadeonNI.kext/Contents/Info.plist': encoded,
             'payload/RadeonNI.kext/Contents/MacOS/RadeonNI': kernel}
    manifest = {'experimental': True, 'installable_for_controlled_test_only': True,
                'tested_kernel_sha256': digest, 'pci_id': '1002:6704',
                'files': {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
    files['manifest.json'] = (json.dumps(manifest, indent=2, sort_keys=True) + '\n').encode()
    destination = OUT / ('framebuffer-test/RadeonNI-Tiger-V7900-Framebuffer-' + digest[:8] + '.zip')
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open('xb') as stream:
        with zipfile.ZipFile(stream, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in files.items():
                item = zipfile.ZipInfo('RadeonNI-Tiger-V7900-Framebuffer/' + name, (2020, 1, 1, 0, 0, 0))
                item.create_system = 3
                item.external_attr = (0o100000 | (0o755 if name in ('manage.sh', 'core.sh', 'payload/RadeonNI.kext/Contents/MacOS/RadeonNI') else 0o644)) << 16
                item.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(item, data)
    print(destination)
    print('sha256=' + hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()
