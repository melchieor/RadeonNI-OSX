#!/usr/bin/env python3
"""Stage pinned firmware for experimental Tiger profiles, never an installer."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'third_party/linux-firmware'
DESTINATION = ROOT / 'build/tiger-v7900/firmware-staging'
REVISION = '69e51bb26f3fa3e118dd770f1962a93bed690dc1'
INPUTS = {
    'TURKS_pfp.bin': ('65d98665384252ddd627c365dbfd2f238b0538570d9e1dad6d4382bb93723089', 4480),
    'TURKS_me.bin': ('37fa5fb7cdb13df94c9a64d7ba752b63119f063f64326b67ec54656cd184363b', 5504),
    'TURKS_mc.bin': ('f88017d12951e68b8db2695350108f43b2bbac46fd4de525a1e2612540156a3d', 24096),
    'CAYMAN_pfp.bin': ('8fbe3f47f1499f6dd683245bccee38560d5d476aac488344d13aba45832ac4d9', 8704),
    'CAYMAN_me.bin': ('2cc5431d404f4d8e27eaa4f157b8c6481680dc87ecfc00b5f0f2a917c6dcf3c7', 8704),
    'CAYMAN_mc.bin': ('c98f77d106833e627c053e9c3c3fc2f5d9aa6a84ae3981161cabe9086f47fa78', 24148),
    'CAYMAN_rlc.bin': ('71aac4ac9fea69a4d9db6d58604ae8473502a49168af5629a645bacc21bc0943', 4096),
    'CAYMAN_smc.bin': ('6da39205d5121088d3b0bdea9c8b09adfde3f66eff6c1fe3e377fee174f70fed', 31212),
    'LICENSE.radeon': ('fc6223d4bfe9f2f9e2eddc44b9fe5721d0caf49f01cb08d602906add686d8c6f', None),
}


def validate(payloads, expected=INPUTS):
    if set(payloads) != set(expected):
        raise ValueError('firmware file set mismatch')
    for name, (digest, size) in expected.items():
        data = payloads[name]
        if hashlib.sha256(data).hexdigest() != digest or (size is not None and len(data) != size):
            raise ValueError('firmware checksum/size mismatch: ' + name)


def main():
    revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise SystemExit('Firmware source revision differs from the reviewed pin')
    payloads = {}
    for name in INPUTS:
        relative = ('LICENSES/' if name == 'LICENSE.radeon' else 'radeon/') + name
        payloads[name] = subprocess.check_output(['git', '-C', str(SOURCE), 'show', REVISION + ':' + relative])
    validate(payloads)
    if DESTINATION.exists():
        raise SystemExit('Refusing to overwrite existing staging directory: ' + str(DESTINATION))
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.firmware-stage-', dir=DESTINATION.parent) as temp:
        temp = Path(temp)
        for name, data in payloads.items():
            (temp / name).write_bytes(data)
        manifest = {'installable': False, 'commit': REVISION,
                    'repository': 'https://gitlab.com/kernel-firmware/linux-firmware.git',
                    'files': {n: {'sha256': hashlib.sha256(d).hexdigest(), 'bytes': len(d)} for n, d in payloads.items()}}
        (temp / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
        os.rename(temp, DESTINATION)
    print('Staged verified experimental family firmware: ' + str(DESTINATION))


if __name__ == '__main__':
    main()
