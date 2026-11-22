#!/usr/bin/env python3
"""Isolate and rebuild the libstdc++ objects found to contain AltiVec."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'build/tiger-v7900'
SOURCE=ROOT/'third_party/build-leopard-gcc/powerpc-apple-darwin9/libstdc++-v3'
COPY=OUT/'libstdcxx-cfm-copy';DEST=OUT/'libstdcxx-cfm'
TOOLS=ROOT/'third_party/leopard-toolchain/bin'
OBJECTS=('ctype','locale-inst','cxx11-locale-inst','wlocale-inst','cxx11-wlocale-inst')


def exports(path):
    result=subprocess.check_output([str(TOOLS/'nm'),'-g',str(path)],text=True)
    return {x[-1] for line in result.splitlines() if len(x:=line.split())>=3 and x[-2].upper()!='U'}


def main():
    if COPY.exists() or DEST.exists():raise SystemExit('Refusing to overwrite prior runtime experiment')
    shutil.copytree(SOURCE,COPY,symlinks=True)
    objects=COPY/'src/c++11';original=SOURCE/'src/c++11'
    for name in OBJECTS:
        p=objects/(name+'.lo')
        if p.is_symlink() or not p.is_file():raise SystemExit('Unexpected copied object: '+str(p))
        p.unlink()
    subprocess.run(['make','-j3','-C',str(objects),*[n+'.lo' for n in OBJECTS],
                    'CXXFLAGS=-O2 -g0 -mno-altivec'],check=True)
    details={}
    for name in OBJECTS:
        old=original/(name+'.o');new=objects/(name+'.o')
        if exports(old)!=exports(new):raise SystemExit('Export set changed in '+name)
        lines=subprocess.check_output([str(TOOLS/'otool'),'-tv',str(new)],text=True)
        vec=[line for line in lines.splitlines() if re.match(r'^\s*[0-9a-fA-F]+\s+(?:v\w+|lvx|stvx)\b',line)]
        if vec:raise SystemExit('Unexpected vector instructions in '+name)
        details[name]={'original_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
                       'scalar_sha256':hashlib.sha256(new.read_bytes()).hexdigest()}
    DEST.mkdir()
    archive=DEST/'libstdc++.a'
    shutil.copy2(SOURCE/'src/.libs/libstdc++.a',archive)
    subprocess.run([str(TOOLS/'ar'),'r',str(archive),*[str(objects/(n+'.o')) for n in OBJECTS]],check=True)
    subprocess.run([str(TOOLS/'ranlib'),str(archive)],check=True)
    details['archive_sha256']=hashlib.sha256(archive.read_bytes()).hexdigest()
    (DEST/'manifest.json').write_text(json.dumps(details,indent=2)+'\n')
    print('Experimental runtime archive:',archive)
    print('Only audited objects were replaced; remaining archive code was not rebuilt.')


if __name__=='__main__':main()
