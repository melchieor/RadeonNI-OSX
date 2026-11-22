#!/usr/bin/env python3
"""Check the mapping redirect PPC vtable slot against the exact G5 kernel."""
import argparse
import hashlib
import struct
from pathlib import Path
from leopard_kext_abi import object_data,symbol_bytes
from leopard_macho import read
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser()
p.add_argument('--kernel',type=Path,required=True)
p.add_argument('--object',type=Path,required=True)
a=p.parse_args()
if set(read(a.kernel))!={18} or read(a.kernel)[18]['kind']!=2:raise SystemExit('Expected PPC32 kernel')
_,_,symbols=object_data(a.kernel)
name='__ZN12_IOMemoryMap8redirectEP18IOMemoryDescriptormm'
target=[v for n,t,s,v in symbols if n==name and not t&0xe0 and t&0x0e==0x0e]
vtable=symbol_bytes(a.kernel,'__ZTV12_IOMemoryMap',0xf4)
if len(target)!=1 or struct.unpack_from('>I',vtable,0xf0)[0]!=target[0]:
 raise SystemExit('Exact G5 IOMemoryMap redirect slot mismatch')
fn='__ZN18RadeonNIUserClient29methodSleepMappingUniqueProbeEmPm'
code=symbol_bytes(a.object,fn,0x180)
if code.count(struct.pack('>I',0x800200f0))!=2:
 raise SystemExit('Expected two redirect calls through PPC vtable slot 0xf0')
print('PPC mapping redirect slot=0xf0 target='+hex(target[0]))
print('kernel_sha256='+hashlib.sha256(a.kernel.read_bytes()).hexdigest())
print('Static ABI check only; mapping behavior and cleanup still require testing.')
