#!/usr/bin/env python3
"""Stage only checksum-pinned Cayman microcode from an upstream checkout."""
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'third_party/linux-firmware'
REVISION = '69e51bb26f3fa3e118dd770f1962a93bed690dc1'
INPUTS = {
    'CAYMAN_pfp.bin': ('8fbe3f47f1499f6dd683245bccee38560d5d476aac488344d13aba45832ac4d9', 8704),
    'CAYMAN_me.bin': ('2cc5431d404f4d8e27eaa4f157b8c6481680dc87ecfc00b5f0f2a917c6dcf3c7', 8704),
    'CAYMAN_mc.bin': ('c98f77d106833e627c053e9c3c3fc2f5d9aa6a84ae3981161cabe9086f47fa78', 24148),
    'CAYMAN_rlc.bin': ('71aac4ac9fea69a4d9db6d58604ae8473502a49168af5629a645bacc21bc0943', 4096),
    'CAYMAN_smc.bin': ('6da39205d5121088d3b0bdea9c8b09adfde3f66eff6c1fe3e377fee174f70fed', 31212),
    'LICENSE.radeon': ('fc6223d4bfe9f2f9e2eddc44b9fe5721d0caf49f01cb08d602906add686d8c6f', None),
}


def main():
    revision = subprocess.check_output(['git', '-C', str(SOURCE), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise SystemExit('Firmware source revision differs from the reviewed pin')
    payloads, manifest = {}, {}
    for name, (expected, size) in INPUTS.items():
        relative = ('LICENSES/' if name == 'LICENSE.radeon' else 'radeon/') + name
        data = (SOURCE / relative).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        if digest != expected or (size is not None and len(data) != size):
            raise SystemExit('Firmware checksum/size mismatch: ' + name)
        payloads[name] = data
        manifest[name] = dict(sha256=digest, bytes=len(data), source=relative)
    destination = ROOT / 'firmware'
    destination.mkdir(exist_ok=True)
    for name, data in payloads.items():
        (destination / name).write_bytes(data)
    (destination / 'cayman-manifest.json').write_text(json.dumps(dict(
        repository='https://gitlab.com/kernel-firmware/linux-firmware.git',
        commit=REVISION, files=manifest), indent=2) + '\n')
    print('Staged five unchanged Cayman microcode files and LICENSE.radeon in ' + str(destination))


if __name__ == '__main__':
    main()
