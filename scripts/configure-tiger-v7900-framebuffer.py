#!/usr/bin/env python3
"""Build a narrow, unqualified Tiger V7900 framebuffer-only profile."""
import argparse
import copy
from pathlib import Path
import plistlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'build/tiger-v7900'


def profile(template):
    result = copy.deepcopy(template)
    base = template['IOKitPersonalities']['RadeonNI']
    keys = ('CFBundleIdentifier', 'IOClass', 'IOMatchCategory', 'IOProbeScore', 'IOProviderClass')
    entry = {key: copy.deepcopy(base[key]) for key in keys}
    entry.update(IOPCIMatch='0x67041002', FirmwareFamily='CAYMAN',
                 Accelerator=False, Surfaces=False, GAPlugin=False,
                 HWCursor=False, TemperatureFanControl=False, MultiHead=False)
    result['IOKitPersonalities'] = {'RadeonNI-V7900-Framebuffer': entry}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output = args.output.resolve()
    if OUT.resolve() not in output.parents or output.exists():
        parser.error('output must be a new file inside build/tiger-v7900')
    with (ROOT / 'kext/RadeonNI/Info.plist').open('rb') as f:
        result = profile(plistlib.load(f))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as f:
        plistlib.dump(result, f, fmt=plistlib.FMT_XML, sort_keys=False)
    print('Experimental framebuffer-only profile; not yet qualified for installation:', output)


if __name__ == '__main__':
    main()
