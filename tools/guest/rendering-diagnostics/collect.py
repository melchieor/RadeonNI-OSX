#!/usr/bin/python
"""Leopard Python 2.5 read-only rendering report. No driver/config changes."""
import os,sys,stat,hashlib,subprocess,platform,re

def emit(line):
    sys.stdout.write(str(line)+'\n')
def command(args,show=True):
    try:
        process=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        data=process.communicate()[0]
        if not isinstance(data,str):data=data.decode('utf-8','replace')
        if show:
            emit('$ '+' '.join(args));emit(data.rstrip());emit('exit='+str(process.returncode))
        return data
    except Exception:
        emit('command-error: '+str(sys.exc_info()[1]));return ''
def metadata(path):
    try:
        info=os.lstat(path)
        emit('path='+path+' mode='+oct(stat.S_IMODE(info.st_mode))+' uid='+str(info.st_uid)+' gid='+str(info.st_gid))
    except Exception:emit('path-error '+path+': '+str(sys.exc_info()[1]))

def main():
    if platform.system()!='Darwin' or platform.machine() not in ('Power Macintosh','ppc','ppc64'):
        emit('Run this read-only collector on the Leopard Power Mac.');return 1
    emit('RadeonNI rendering report v1; no installation, reset, process termination or configuration writes')
    emit('euid='+str(os.geteuid()))
    command(['/usr/bin/sw_vers'])
    for path in ['/Library/Application Support','/Library/Application Support/RadeonNI',
                 '/Library/Application Support/RadeonNI/Backups',
                 '/Library/Application Support/RadeonNI/nocoreimage',
                 '/Library/Application Support/RadeonNI/nopbuffer','/tmp/rdngld.on','/tmp/rdngld.trace']:
        metadata(path)
    here=os.path.dirname(os.path.realpath(__file__))
    command([os.path.join(here,'qe-status')])
    emit('Installed executable fingerprints (folder names alone do not identify the loaded build):')
    modules=[('RadeonNI.kext','RadeonNI'),('RadeonNIGA.plugin','RadeonNIGA')]+[
        ('RadeonNIGLDriver'+suffix+'.bundle','RadeonNIGLDriver'+suffix) for suffix in ('','1','2','3')]
    for bundle,name in modules:
        path='/System/Library/Extensions/'+bundle+'/Contents/MacOS/'+name
        try:
            stream=open(path,'rb');digest=hashlib.sha256()
            while True:
                block=stream.read(65536)
                if not block:break
                digest.update(block)
            stream.close();emit(name+' sha256='+digest.hexdigest())
        except Exception:emit(name+' fingerprint-error: '+str(sys.exc_info()[1]))
    processes=command(['/bin/ps','-ax','-o','pid=,uid=,comm='],False)
    for line in processes.splitlines():
        fields=line.strip().split(None,2)
        if len(fields)!=3 or os.path.basename(fields[2])!='WindowServer':continue
        pid=fields[0]
        if not pid.isdigit():continue
        emit('WindowServer pid='+pid+' uid='+fields[1])
        path='/tmp/rdngld.'+pid+'.log'
        try:
            stream=open(path,'rb');head=stream.read(4096);stream.seek(0,2);size=stream.tell()
            stream.seek(max(0,size-262144));tail=stream.read(262144);stream.close()
            if not isinstance(head,str):head=head.decode('utf-8','replace');tail=tail.decode('utf-8','replace')
            emit('WindowServer driver log='+path+' bytes='+str(size)+' (head plus filtered final 256 KiB)')
            emit(head)
            matches=[entry for entry in tail.splitlines() if re.search('Core Image|fragment_program|pbuffer|backing|surface|dispatch|fail|error|unsupported|refus|missing',entry,re.I)]
            for entry in matches[-160:]:emit(entry)
        except Exception:emit('WindowServer log unavailable: '+str(sys.exc_info()[1]))
    return 0
if __name__=='__main__':sys.exit(main())
