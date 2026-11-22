#!/usr/bin/env python3
"""Check one PPC virtual-call slot against the exact, copied G5 kernel.

This is a static check, not a kext load or a hardware coherency test.
"""
import argparse
import hashlib
import struct
from pathlib import Path
from leopard_kext_abi import object_data, symbol_bytes
from leopard_macho import read

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--kernel', type=Path, required=True)
parser.add_argument('--object', type=Path, required=True)
parser.add_argument('--stage-object', type=Path, required=True)
args = parser.parse_args()
kernel = read(args.kernel)
if set(kernel) != {18} or kernel[18]['kind'] != 2:
    raise SystemExit('Expected a PPC32 Mach-O kernel executable')
_, _, symbols = object_data(args.kernel)
vtable_addresses = [v for n, t, s, v in symbols if n == '__ZTV24IOBufferMemoryDescriptor'
                    and not t & 0xe0 and t & 0x0e == 0x0e]
if len(vtable_addresses) != 1:
    raise SystemExit('Expected one IOBufferMemoryDescriptor vtable')
vtable_address = vtable_addresses[0]
constructor = symbol_bytes(args.kernel, '__ZN24IOBufferMemoryDescriptorC2EPK11OSMetaClass', 0x3c)
load = struct.pack('>II', 0x3c400000 | ((vtable_address + 0x8000) >> 16),
                   0x38420000 | (vtable_address & 0xffff))
where = constructor.find(load)
if where < 0 or struct.pack('>I', 0x905d0000) not in constructor[where + 8:where + 20]:
    raise SystemExit('Cannot verify constructor installs the expected vtable address')
vtable = symbol_bytes(args.kernel, '__ZTV24IOBufferMemoryDescriptor', 0x14c)
checks = [
    (0xe0, '__ZN18IOMemoryDescriptor16performOperationEmmm', args.object,
     '__ZL10sync_stageP21rdn_tiger_sleep_stagem', 0x94),
    (0x13c, '__ZN25IOGeneralMemoryDescriptor18getPhysicalSegmentEmPm', args.stage_object,
     '__ZL9stage_busPvjPy', 0x74),
    (0x144, '__ZN25IOGeneralMemoryDescriptor7prepareE11IODirection', args.stage_object,
     '__Z29rdn_tiger_sleep_stage_prepareP21rdn_tiger_sleep_stagem', 0xf4),
    (0x148, '__ZN25IOGeneralMemoryDescriptor8completeE11IODirection', args.stage_object,
     '__Z28rdn_tiger_sleep_stage_finishP21rdn_tiger_sleep_stage', 0xa0),
]
for slot, name, obj, function, length in checks:
    target = [v for n, t, s, v in symbols if n == name and not t & 0xe0 and t & 0x0e == 0x0e]
    actual = struct.unpack_from('>I', vtable, slot)[0]
    if len(target) != 1 or actual != target[0]:
        raise SystemExit('IOBufferMemoryDescriptor slot %#x does not match %s' % (slot, name))
    code = symbol_bytes(obj, function, length)
    if code.count(struct.pack('>I', 0x80020000 | slot)) != 1:
        raise SystemExit('Expected one PPC load from vtable offset %#x in %s' % (slot, function))
    print('slot=%#x target=%s address=%#x' % (slot, name, actual))
print('kernel_sha256=' + hashlib.sha256(args.kernel.read_bytes()).hexdigest())
print('Static slot check only: no runtime, memory-ordering, mapper or GPU behavior verified.')
