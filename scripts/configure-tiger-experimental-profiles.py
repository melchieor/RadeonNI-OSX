#!/usr/bin/env python3
"""Create non-installable Tiger profile experiments for two known PCI IDs."""
import argparse
import copy
import importlib.util
from pathlib import Path
import plistlib

ROOT = Path(__file__).resolve().parents[1]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


firmware = load_script('stage-tiger-family-firmware')
families = load_script('configure-device-families')


def profiles(template, payloads, fan=False):
    firmware.validate(payloads)
    result = copy.deepcopy(template)
    base = template['IOKitPersonalities']['RadeonNI']
    keep = ('CFBundleIdentifier', 'IOClass', 'IOMatchCategory', 'IOProbeScore', 'IOProviderClass')
    output = {}
    for family, pci in [('TURKS', '0x675d1002'), ('CAYMAN', '0x67041002')]:
        entry = {key: copy.deepcopy(base[key]) for key in keep}
        entry.update(IOPCIMatch=pci, FirmwareFamily=family, Accelerator=True,
                     AccelCaps=3, AGPShim=3, Surfaces=True, SurfaceGate=False,
                     GAPlugin=True, HWCursor=False)
        for kind, expected in zip(('PFP', 'ME'), families.CP_BYTES[family]):
            data = payloads[family + '_' + kind.lower() + '.bin']
            if len(data) != expected:
                raise ValueError('microcode size disagrees with family capabilities: ' + family + ' ' + kind)
            entry['FW_' + kind] = data
        for kind in ('MC', 'RLC', 'SMC'):
            name = family + '_' + kind.lower() + '.bin'
            if name in payloads:
                entry['FW_' + kind] = payloads[name]
        if fan and family == 'CAYMAN':
            entry['TemperatureFanControl'] = True
        output['RadeonNI-' + family] = entry
    result['IOKitPersonalities'] = output
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fan-experiment', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    safe_root = (ROOT / 'build/tiger-v7900').resolve()
    if safe_root not in output.parents or output.exists():
        parser.error('output must be a new file inside build/tiger-v7900')
    staged = firmware.DESTINATION
    payloads = {name: (staged / name).read_bytes() for name in firmware.INPUTS}
    with (ROOT / 'kext/RadeonNI/Info.plist').open('rb') as stream:
        template = plistlib.load(stream)
    result = profiles(template, payloads, args.fan_experiment)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('xb') as stream:
        plistlib.dump(result, stream, sort_keys=False)
    print('EXPERIMENT ONLY: profile is not qualified for installation:', output)


if __name__ == '__main__':
    main()
