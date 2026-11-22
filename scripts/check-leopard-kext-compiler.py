#!/usr/bin/env python3
"""Compile-only check of the PPC32 IOKit kernel ABI, not a runtime test."""
import json
from pathlib import Path
import subprocess
import sys
from leopard_kext_abi import vtables, symbol_bytes

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'build/leopard-v7900'


def check(compiler=None, report_name='compiler-abi-validation'):
    compiler = compiler or ROOT/'third_party/apple-kext-toolchain/bin/powerpc-apple-darwin9-g++'
    output = OUT/(report_name+'.o')
    subprocess.run([str(compiler),'-m32','-mkernel','-fapple-kext','-fno-exceptions',
                    '-fno-rtti','-g0','-c',str(ROOT/'tests/leopard_kext_abi_probe.cpp'),
                    '-o',str(output)],check=True)
    table = vtables(output)['__ZTV11RDNABIProbe']
    errors = []
    if not table['terminated'] or len(table['entries']) != 2 or not table['entries'][0][0].endswith('D0Ev'):
        errors.append('kernel vtable must have D0, reserved, zero terminator')
    plain = symbol_bytes(output,'_rdn_abi_plain',8)
    virtual = symbol_bytes(output,'_rdn_abi_virtual',8)
    if plain[:4] != bytes.fromhex('0000ffff'):
        errors.append('nonvirtual member pointer lacks legacy delta/index -1 fields')
    if virtual != bytes.fromhex('0000000400000000'):
        errors.append('virtual member pointer lacks legacy vtable index 4')
    result = dict(passed=not errors,errors=errors,compiler=str(compiler),
                  version=subprocess.check_output([str(compiler),'--version'],text=True).splitlines()[0],
                  vtable=table, nonvirtual_member_bytes=plain.hex(),virtual_member_bytes=virtual.hex(),
                  runtime_executed=False)
    (OUT/(report_name+'.json')).write_text(json.dumps(result,indent=2)+'\n')
    return result


if __name__ == '__main__':
    result = check(Path(sys.argv[1]) if len(sys.argv)>1 else None)
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)
