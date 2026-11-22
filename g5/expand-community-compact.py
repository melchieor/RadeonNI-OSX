#!/usr/bin/python
"""Expand a RadeonNI compact transport without changing system files.

Designed for the built-in Tiger/Leopard Python; target execution is untested.
"""
import os
import plistlib
import shutil
import struct
import sys
import tempfile
try:
    import hashlib
    def new_hash(): return hashlib.sha256()
    HASH_KEY = 'sha256'
except ImportError:
    import sha
    def new_hash(): return sha.new()
    HASH_KEY = 'sha1'

def fail(message):
    raise ValueError(message)

def safe_relative(name):
    if not name or name.startswith('/') or '\\' in name:
        fail('Invalid path: '+name)
    for part in name.split('/'):
        if not part or part == '.' or part == '..': fail('Invalid path: '+name)
    return name

def file_hash(path):
    stream=open(path,'rb'); result=new_hash()
    try:
        while True:
            block=stream.read(1048576)
            if not block: break
            result.update(block)
    finally: stream.close()
    return result.hexdigest()

def read_exact(stream, amount):
    data=stream.read(amount)
    if len(data)!=amount: fail('Truncated delta')
    return data

def reconstruct(base, delta, destination, record):
    source=open(base,'rb'); patch=open(delta,'rb'); out=open(destination,'wb')
    digest=new_hash(); total=0
    try:
        if read_exact(patch,7)!='RDND01\n'.encode('ascii'): fail('Invalid delta header')
        size=struct.unpack('>Q',read_exact(patch,8))[0]
        if size!=record['size']: fail('Unexpected output size')
        source.seek(0,2); base_size=source.tell()
        while total<size:
            kind=read_exact(patch,1)
            if kind=='C'.encode('ascii'):
                offset,length=struct.unpack('>QI',read_exact(patch,12))
                if not length or length>4096 or offset>base_size or length>base_size-offset:
                    fail('Invalid copy range')
                source.seek(offset); block=read_exact(source,length)
            elif kind=='L'.encode('ascii'):
                length=struct.unpack('>I',read_exact(patch,4))[0]
                if not length or length>4096: fail('Invalid literal range')
                block=read_exact(patch,length)
            else: fail('Invalid delta instruction')
            if length>size-total: fail('Delta exceeds expected output')
            out.write(block); digest.update(block); total+=length
        if patch.read(1): fail('Trailing delta data')
        if digest.hexdigest()!=record[HASH_KEY]: fail('Reconstructed file checksum mismatch')
    finally:
        source.close();patch.close();out.close()

def main():
    if len(sys.argv)>2: fail('Usage: /usr/bin/python -E ./expand.py [new-output-directory]')
    here=os.path.dirname(os.path.abspath(__file__))
    meta_path=os.path.join(here,'COMPACT-MANIFEST.plist')
    if hasattr(plistlib,'readPlist'): manifest=plistlib.readPlist(meta_path)
    else:
        stream=open(meta_path,'rb')
        try: manifest=plistlib.load(stream)
        finally: stream.close()
    if manifest.get('format')!=1: fail('Unsupported compact format')
    if len(sys.argv)==2: dest=os.path.abspath(sys.argv[1])
    else:
        output_name=safe_relative(manifest['output_name'])
        if '/' in output_name: fail('Invalid default output directory')
        dest=os.path.join(os.path.dirname(here),output_name)
    if os.path.exists(dest) or os.path.islink(dest): fail('Output already exists: '+dest)
    parent=os.path.dirname(dest)
    if not os.path.isdir(parent): fail('Output parent does not exist')
    original=os.path.join(here,'package');delta_dir=os.path.join(here,'deltas')
    for tree in (original,delta_dir):
        if os.path.islink(tree) or not os.path.isdir(tree): fail('Missing or unsafe package directory')
        for directory,dirs,names in os.walk(tree):
            for name in dirs+names:
                if os.path.islink(os.path.join(directory,name)): fail('Symbolic links are not allowed')
    files=manifest['files'];base_rel=safe_relative(manifest['base'])
    if base_rel not in files or files[base_rel].get('delta'): fail('Invalid base file')
    base=os.path.join(original,base_rel)
    if not os.path.isfile(base) or file_hash(base)!=files[base_rel][HASH_KEY]: fail('Base checksum mismatch')
    temp=tempfile.mkdtemp(prefix='.radeonni-expand-',dir=parent)
    try:
        names=list(files.keys());names.sort()
        for name in names:
            safe_relative(name);record=files[name];target=os.path.join(temp,name)
            if not isinstance(record['mode'],int) or record['mode']<0 or record['mode']>511:
                fail('Invalid file mode: '+name)
            directory=os.path.dirname(target)
            if not os.path.isdir(directory): os.makedirs(directory)
            delta=record.get('delta')
            if delta:
                safe_relative(delta);patch=os.path.join(delta_dir,delta)
                if os.path.islink(patch) or file_hash(patch)!=record['delta_'+HASH_KEY]: fail('Delta checksum mismatch: '+name)
                reconstruct(base,patch,target,record)
                if file_hash(target)!=record[HASH_KEY]: fail('Written file checksum mismatch: '+name)
            else:
                src=os.path.join(original,name)
                if os.path.islink(src) or not os.path.isfile(src) or file_hash(src)!=record[HASH_KEY]: fail('Source checksum mismatch: '+name)
                shutil.copyfile(src,target)
                if file_hash(target)!=record[HASH_KEY]: fail('Copied file checksum mismatch: '+name)
            os.chmod(target,record['mode'])
        os.rename(temp,dest);temp=None
    finally:
        if temp: shutil.rmtree(temp)
    print('Expanded and verified package: '+dest)
    print('Read 00-COMMUNITY-NOTES.txt and the original installer instructions before continuing.')

if __name__=='__main__':
    try: main()
    except Exception:
        print('ERROR: '+str(sys.exc_info()[1]))
        sys.exit(1)
