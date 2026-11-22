#!/usr/bin/env python3
"""Create compact, reconstructible ZIP transports from the verified packages."""
import hashlib
import argparse
import importlib.util
import io
from pathlib import Path
import plistlib
import struct
import zipfile

ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'build/community-v7900/release'
spec=importlib.util.spec_from_file_location('community',ROOT/'scripts/package-v7900-community.py')
community=importlib.util.module_from_spec(spec);spec.loader.exec_module(community)

def hashes(data):
    return {'sha256':hashlib.sha256(data).hexdigest(),'sha1':hashlib.sha1(data).hexdigest()}

def make_delta(base,target):
    # Aligned matches preserve cross-slice shifts without ever changing bytes.
    index={}
    for off in range(0,len(base),4096):
        chunk=base[off:off+4096]
        index.setdefault(hashlib.sha256(chunk).digest(),[]).append(off)
    out=io.BytesIO();out.write(b'RDND01\n');out.write(struct.pack('>Q',len(target)))
    for off in range(0,len(target),4096):
        chunk=target[off:off+4096];key=hashlib.sha256(chunk).digest();match=None
        for candidate in index.get(key,[]):
            if base[candidate:candidate+len(chunk)]==chunk:match=candidate;break
        if match is None:out.write(b'L'+struct.pack('>I',len(chunk))+chunk)
        else:out.write(b'C'+struct.pack('>QI',match,len(chunk)))
    return out.getvalue()

def add(z,name,data,mode=0o644):
    info=zipfile.ZipInfo(name,(2020,1,1,0,0,0));info.create_system=3
    info.external_attr=(0o100000|mode)<<16;info.compress_type=zipfile.ZIP_DEFLATED
    z.writestr(info,data)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archives',nargs='*',type=Path)
    args=parser.parse_args()
    archives=args.archives or [RELEASE/'RadeonNI-Tiger-V7900-Community-Experimental.zip',
              RELEASE/'RadeonNI-Leopard-V7900-Community-Experimental.zip',
              RELEASE/'RadeonNI-Leopard-V7900-CFM-Community-Experimental.zip']
    for source in archives:
        original,files,modes=community.archive_files(source)
        community.verify_original('Tiger' if 'Tiger' in source.name else 'Leopard',files)
        base='payload/RadeonNIGLDriver.bundle/Contents/MacOS/RadeonNIGLDriver'
        if base not in files:raise ValueError('missing GL base')
        replacements={}
        for suffix in ('1','2','3'):
            name='payload/RadeonNIGLDriver'+suffix+'.bundle/Contents/MacOS/RadeonNIGLDriver'+suffix
            replacements[name]=('driver'+suffix+'.delta',make_delta(files[base],files[name]))
        records={}
        for name,data in files.items():
            record=dict(hashes(data),size=len(data),mode=(modes[name]>>16)&0o777)
            if name in replacements:
                delta_name,delta=replacements[name];record['delta']=delta_name
                for key,value in hashes(delta).items():record['delta_'+key]=value
            records[name]=record
        folder=source.stem+'-Compact'
        manifest={'format':1,'base':base,'output_name':original.rstrip('/')+'-expanded','files':records}
        instructions=('COMPACT TRANSPORT: no installation occurs when expanding.\n\n'
            'Extract this ZIP completely, open Terminal, and cd into this folder.\n'
            'Run: /usr/bin/python -E ./expand.py\n'
            'It creates a new verified sibling folder and will not overwrite an existing one.\n'
            'Open that expanded folder and read 00-COMMUNITY-NOTES.txt and the original\n'
            'installer instructions. Expansion needs enough disk space for the full driver.\n'
            'The extractor is host-tested but not yet run on Tiger or Leopard. If it fails,\n'
            'use the original full-size ZIP; never run a partially expanded installer.\n'
            'Checksums detect corruption, not authenticity. Hardware and sleep warnings\n'
            'from the original package still apply. The expanded files are byte-for-byte\n'
            'the original community package, including all license and recovery files.\n').encode('ascii')
        destination=RELEASE/(folder+'.zip')
        with destination.open('xb') as stream,zipfile.ZipFile(stream,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
            add(z,folder+'/READ-ME-FIRST.txt',instructions)
            add(z,folder+'/expand.py',(ROOT/'g5/expand-community-compact.py').read_bytes(),0o755)
            add(z,folder+'/COMPACT-MANIFEST.plist',plistlib.dumps(manifest))
            for name,data in sorted(files.items()):
                if name not in replacements:add(z,folder+'/package/'+name,data,(modes[name]>>16)&0o777)
            for name,data in sorted(replacements.values()):add(z,folder+'/deltas/'+name,data)
        with zipfile.ZipFile(destination) as z:
            if z.testzip():raise ValueError('compact ZIP CRC failure')
        digest=hashlib.sha256(destination.read_bytes()).hexdigest()
        destination.with_suffix('.zip.sha256').write_text(digest+'  '+destination.name+'\n')
        print(destination.name,round(destination.stat().st_size/1048576,2),'MiB',digest,flush=True)

if __name__=='__main__':main()
