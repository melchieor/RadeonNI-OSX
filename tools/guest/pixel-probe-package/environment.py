#!/usr/bin/python
"""Read-only installed binary fingerprints; Leopard Python 2.5 compatible."""
import hashlib,os,sys
names=[('RadeonNI.kext','RadeonNI'),('RadeonNIGA.plugin','RadeonNIGA')]+[
    ('RadeonNIGLDriver'+s+'.bundle','RadeonNIGLDriver'+s) for s in ('','1','2','3')]
for bundle,name in names:
    path='/System/Library/Extensions/'+bundle+'/Contents/MacOS/'+name
    try:
        stream=open(path,'rb');digest=hashlib.sha256()
        while True:
            block=stream.read(65536)
            if not block:break
            digest.update(block)
        stream.close();sys.stdout.write(name+' sha256='+digest.hexdigest()+'\n')
    except Exception:sys.stdout.write(name+' fingerprint-error: '+str(sys.exc_info()[1])+'\n')
