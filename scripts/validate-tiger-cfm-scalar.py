#!/usr/bin/env python3
"""Statically inspect experimental no-AltiVec PPC32 GL modules."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
from leopard_macho import read
from leopard_kext_abi import symbol_bytes

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
SDK=OUT/'sdk-audit/extracted/MacOSX10.4u.sdk';REF=OUT/'apple-reference'
OT=ROOT/'third_party/leopard-toolchain/bin/otool'


def main():
    previous=json.loads((OUT/'experimental-validation-fan.json').read_text())['modules']
    scan_cache={};report={};errors=[]
    for suffix in ('','1','2','3'):
        name='RadeonNIGLDriver'+suffix
        path=OUT/'mesa-cfm-scalar/build-tiger-native32/src/gallium/targets/rdn'/(name+'.dylib')
        old=OUT/'mesa-26.2.4/build-tiger-native32/src/gallium/targets/rdn'/(name+'.dylib')
        meta=read(path)[18];oldmeta=read(old)[18]
        if hashlib.sha256(old.read_bytes()).hexdigest()!=previous[name]['sha256']:
            raise SystemExit('Prior baseline GL binary changed: '+name)
        exports=set(meta['exports']);oldgld={x for x in oldmeta['exports'] if x.startswith('_gld')}
        missing_gld=sorted(oldgld-exports)
        helper=symbol_bytes(path,'dyld_stub_binding_helper',16)==symbol_bytes(SDK/'usr/lib/bundle1.o','dyld_stub_binding_helper',16)
        seen=set();todo=list(meta['dependencies']);resolved=set();dep_errors=[]
        while todo:
            dep=todo.pop()
            if dep in seen:continue
            seen.add(dep)
            if not dep.startswith(('/usr/lib/','/System/Library/Frameworks/','/System/Library/PrivateFrameworks/')):
                dep_errors.append('non-system '+dep);continue
            try:
                if dep not in scan_cache:
                    ref=REF/'usr/lib/libSystem.B.dylib' if dep=='/usr/lib/libSystem.B.dylib' else SDK/dep.lstrip('/')
                    scan_cache[dep]=read(ref)[18]
                lib=scan_cache[dep];resolved.update(lib['exports']);todo.extend(lib['dependencies'])
            except (OSError,ValueError,KeyError) as ex:dep_errors.append(dep+': '+str(ex))
        missing=sorted(set(meta['imports'])-resolved)
        proc=subprocess.Popen([str(OT),'-tv',str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        examples=[];count=0;by_function={};function=None
        vector_memory={'lvx','lvxl','stvx','stvxl','lvebx','lvehx','lvewx','stvebx','stvehx','stvewx','lvsl','lvsr'}
        for line in proc.stdout:
            label=re.match(r'^([^\s:]+):\s*$',line)
            if label:
                function=label.group(1)
                continue
            match=re.match(r'^\s*([0-9a-fA-F]+)\s+([a-z][a-z0-9.]*)\b',line)
            if match:
                op=match.group(2)
                if op.startswith('v') or op in vector_memory:
                    count+=1
                    by_function[function or '<unknown>']=by_function.get(function or '<unknown>',0)+1
                    if len(examples)<15:examples.append(line.strip())
        stderr=proc.stderr.read();status=proc.wait()
        item={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'kind':meta['kind'],'rpaths':meta['rpaths'],
              'missing_gl_exports':missing_gld,'missing_imports':missing,'dependency_errors':dep_errors,
              'bundle_helper_matches':helper,'vector_instruction_count':count,'vector_instructions_by_function':by_function,
              'vector_instruction_examples':examples,
              'disassembler_status':status,'disassembler_error':stderr}
        report[name]=item
        # GCC's linked exception/save-world runtime may still contain vector
        # instructions. Record that risk; reject vectors in other routines.
        unexpected=set(by_function)-{'save_world','eh_rest_world_r10'}
        item['unexpected_vector_functions']=sorted(unexpected)
        if meta['kind']!=8 or meta['rpaths'] or missing_gld or missing or dep_errors or not helper or unexpected or status:
            errors.append(name)
    output={'installable':False,'hardware_tested':False,'errors':errors,'modules':report,
            'scope':'Static PPC disassembly and referenced Apple SDK export union only. GCC save-world/exception paths can retain vectors; no execution or proof of ABI safety.'}
    (OUT/'validation-cfm-scalar.json').write_text(json.dumps(output,indent=2)+'\n')
    print(json.dumps(output,indent=2))
    if errors:raise SystemExit('Scalar static validation failed')


if __name__=='__main__':main()
