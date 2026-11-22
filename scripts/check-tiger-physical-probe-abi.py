#!/usr/bin/env python3
"""Fail closed if experimental physical-probe PPC slots differ on this kernel."""
import argparse
import hashlib
import struct
from pathlib import Path
from leopard_kext_abi import object_data, symbol_bytes

p = argparse.ArgumentParser()
p.add_argument('--kernel', type=Path, required=True)
p.add_argument('--object', type=Path, required=True)
a = p.parse_args()
_, _, symbols = object_data(a.kernel)
checks = [
 ('__ZTV24IOBufferMemoryDescriptor', 0xd8, '__ZN18IOMemoryDescriptor20getPhysicalSegment64EmPm', '__Z26rdn_physical_probe_prepareP24rdn_tiger_physical_probe', 0x1c0),
 ('__ZTV24IOBufferMemoryDescriptor', 0x144, '__ZN25IOGeneralMemoryDescriptor7prepareE11IODirection', '__Z26rdn_physical_probe_prepareP24rdn_tiger_physical_probe', 0x1c0),
 ('__ZTV24IOBufferMemoryDescriptor', 0x148, '__ZN25IOGeneralMemoryDescriptor8completeE11IODirection', '__Z25rdn_physical_probe_finishP24rdn_tiger_physical_probe', 0x140),
 ('__ZTV25IOGeneralMemoryDescriptor', 0x14c, '__ZN18IOMemoryDescriptor3mapEP4taskjmmm', '__Z22rdn_physical_probe_mapP24rdn_tiger_physical_probeP4taskmj', 0xc8),
 ('__ZTV12_IOMemoryMap', 0xe0, '__ZN12_IOMemoryMap19getMemoryDescriptorEv', '__Z27rdn_physical_probe_redirectP24rdn_tiger_physical_probeb', 0xe8),
 ('__ZTV12_IOMemoryMap', 0xe8, '__ZN12_IOMemoryMap5unmapEv', '__Z25rdn_physical_probe_finishP24rdn_tiger_physical_probe', 0x140),
 ('__ZTV12_IOMemoryMap', 0xf0, '__ZN12_IOMemoryMap8redirectEP18IOMemoryDescriptormm', '__Z27rdn_physical_probe_redirectP24rdn_tiger_physical_probeb', 0xe8),
]
for vtable, slot, target, caller, length in checks:
    values = [v for n,t,s,v in symbols if n == target and not t & 0xe0 and t & 0x0e == 0x0e]
    actual = struct.unpack_from('>I', symbol_bytes(a.kernel, vtable, slot+4), slot)[0]
    if len(values) != 1 or actual != values[0]:
        raise SystemExit('Unexpected kernel vtable target: ' + target)
    code = symbol_bytes(a.object, caller, length)
    if struct.pack('>I', 0x80020000 | slot) not in code:
        raise SystemExit('Expected virtual slot not called: ' + caller)
    print('%s %#x -> %s' % (vtable, slot, target))
print('kernel_sha256=' + hashlib.sha256(a.kernel.read_bytes()).hexdigest())
print('ABI only: does not validate physical addresses, mapping, or lifetime behavior.')
