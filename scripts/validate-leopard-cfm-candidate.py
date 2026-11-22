#!/usr/bin/env python3
"""Static, non-runtime audit of isolated Leopard PPC32 CFM GL candidates."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'build/community-v7900'
SDK=ROOT/'third_party/sdk-audit/extracted/MacOSX10.5.sdk'
REFERENCE=ROOT/'third_party/apple-leopard-update/reference'
OT=ROOT/'third_party/leopard-toolchain/bin/otool'
MODULES=['RadeonNIGLDriver'+s for s in ('','1','2','3')]
EXPECTED={x.strip() for x in (ROOT/'gld/rdn_gld.exports').read_text().splitlines() if x.strip().startswith('_')}

def exports(name,cache):
    if name in cache:return cache[name]
    if not name.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')):
        raise ValueError('non-system dependency: '+name)
    path=REFERENCE/'usr/lib/libSystem.B.dylib' if name=='/usr/lib/libSystem.B.dylib' else SDK/name.lstrip('/')
    meta=read(path)[18]; result=set(meta['exports']);cache[name]=result
    for dep in meta['dependencies']:result.update(exports(dep,cache))
    return result

def main():
    output={};errors=[];cache={}
    for name in MODULES:
        path=OUT/'mesa-leopard-cfm/build-leopard-native32/src/gallium/targets/rdn'/(name+'.dylib')
        arch=read(path)
        if set(arch)!={18}:raise ValueError('not thin PPC32: '+name)
        meta=arch[18];provided=set()
        helper=(symbol_bytes(path,'dyld_stub_binding_helper',16)==
                symbol_bytes(SDK/'usr/lib/bundle1.o','dyld_stub_binding_helper',16))
        for dep in meta['dependencies']:provided.update(exports(dep,cache))
        missing=sorted(set(meta['imports'])-provided)
        scan=subprocess.Popen([str(OT),'-tv',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        functions={};current=None
        vector_memory={'lvx','lvxl','stvx','stvxl','lvebx','lvehx','lvewx','stvebx','stvehx','stvewx','lvsl','lvsr'}
        for line in scan.stdout:
            label=re.match(r'^([^\s:]+):\s*$',line)
            if label:current=label.group(1);continue
            op=re.match(r'^\s*[0-9a-fA-F]+\s+([a-z][a-z0-9.]*)\b',line)
            if op and (op.group(1).startswith('v') or op.group(1) in vector_memory):
                functions[current or '<unknown>']=functions.get(current or '<unknown>',0)+1
        stderr=scan.stderr.read();status=scan.wait()
        unexpected=sorted(set(functions)-{'save_world','eh_rest_world_r10'})
        output[name]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'kind':meta['kind'],
                      'dependencies':meta['dependencies'],'rpaths':meta['rpaths'],
                      'missing_imports':missing,'exports_match':set(meta['exports'])==EXPECTED,
                      'bundle_helper_matches_leopard_sdk':helper,
                      'vector_instructions_by_function':functions,'unexpected_vector_functions':unexpected,
                      'disassembler_status':status,'disassembler_error':stderr}
        if meta['kind']!=8 or meta['rpaths'] or missing or set(meta['exports'])!=EXPECTED or not helper or unexpected or status:
            errors.append(name)
    report={'errors':errors,'hardware_tested':False,'unreal_tested':False,'modules':output,
            'scope':'Static PPC32 checks only; save-world/exception vector paths may remain; no CFM ABI guarantee.'}
    (OUT/'leopard-cfm32-validation.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report,indent=2,sort_keys=True))
    if errors:raise SystemExit('Leopard CFM candidate static audit failed')

if __name__=='__main__':main()
