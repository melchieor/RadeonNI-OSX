#!/usr/bin/env python3
"""Fail closed on static audit regressions for the inert Tiger link probe."""
import argparse
import hashlib
import json
from pathlib import Path
from leopard_macho import read

root = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument('--probe-dir', type=Path, default=root/'build/tiger-v7900/sleep-link-probe')
parser.add_argument('--require-owner', action='store_true')
parser.add_argument('--require-tiger-owner', action='store_true')
args = parser.parse_args()
out = args.probe_dir
kernel = out / 'kernel/RadeonNI.kext/Contents/MacOS/RadeonNI'
report = json.loads((out/'validation.json').read_text())
audit = report['kernel']
architectures = read(kernel)
if set(architectures) != {18} or architectures[18]['kind'] != 1:
    raise SystemExit('Unexpected architecture or Mach-O type')
if hashlib.sha256(kernel.read_bytes()).hexdigest() != audit['sha256']:
    raise SystemExit('Audit does not describe this binary')
for name in ('unresolved_against_reference_union', 'compatibility_alias_errors', 'export_collisions'):
    if audit[name]: raise SystemExit(name + ': ' + repr(audit[name]))
if any(audit['abi_comparisons'].values()): raise SystemExit('Tiger vtable mismatch')
required = {'_rdn_sleep_sequence_bridge_begin', '_rdn_sleep_sequence_bridge_start',
            '_rdn_sleep_sequence_bridge_poll', '_rdn_sleep_sequence_bridge_unstage',
            '_rdn_sleep_sequence_bridge_finish'}
if args.require_owner:
    required.update({'_rdn_sleep_owner_arm', '_rdn_sleep_owner_client_closed',
                     '_rdn_sleep_owner_observe', '_rdn_sleep_owner_may_retire', '_rdn_sleep_owner_release'})
missing = required - set(architectures[18]['exports'])
if missing: raise SystemExit('Missing experimental objects: ' + repr(sorted(missing)))
if args.require_tiger_owner:
    exports = set(architectures[18]['exports'])
    if not any(s.startswith('__Z25rdn_tiger_sleep_owner_arm') for s in exports):
        raise SystemExit('Missing typed Tiger owner adapter')
print('Tiger PPC link probe: symbols, reference-union imports and vtable checks pass.')
print('This is not a kextload, runtime, sleep or hardware test.')
