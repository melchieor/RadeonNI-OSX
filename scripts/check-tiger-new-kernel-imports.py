#!/usr/bin/env python3
"""Conservative new-import gate for a Tiger diagnostic versus a tested kext.

An entry in kernel.6.0 is NOT proof of runtime visibility. The inverse is a
reason to stop and review when the new symbol comes from the raw kernel only.
"""
import argparse
from pathlib import Path
from leopard_macho import read

p=argparse.ArgumentParser()
p.add_argument('--baseline',type=Path,required=True)
p.add_argument('--candidate',type=Path,required=True)
p.add_argument('--kernel6',type=Path,required=True)
p.add_argument('--kernel',type=Path,required=True)
a=p.parse_args()
base=read(a.baseline)[18]
test=read(a.candidate)[18]
compat=read(a.kernel6)[18]
kernel=read(a.kernel)[18]
added=set(test['imports'])-set(base['imports'])
compat_names=set(compat['imports'])|set(compat['exports'])
raw_kernel=set(kernel['exports'])
missing=sorted((added&raw_kernel)-compat_names)
for name in sorted(added):
 print(name, 'kernel6_reference='+str(name in compat_names))
if missing:
 raise SystemExit('REJECT: new raw-kernel imports absent from kernel.6.0: '+', '.join(missing))
print('No newly introduced raw-kernel-only imports; this does not establish loadability.')
