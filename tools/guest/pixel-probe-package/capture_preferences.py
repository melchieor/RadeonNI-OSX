#!/usr/bin/python
"""User-operated Preferences reproduction; normal quit, no process termination."""
import os,sys,subprocess,hashlib,time,platform
DRIVER='/System/Library/Extensions/RadeonNIGLDriver.bundle/Contents/MacOS/RadeonNIGLDriver'
EXPECTED='6ce6d4cb87d4c389c20fbd38d168b5333cd069fd89a9350f7051a62f5175384a'
APP='/Applications/System Preferences.app/Contents/MacOS/System Preferences'
def fingerprint(path):
    stream=open(path,'rb');digest=hashlib.sha256()
    while True:
        data=stream.read(65536)
        if not data:break
        digest.update(data)
    stream.close();return digest.hexdigest()
def main():
    if platform.system()!='Darwin' or platform.machine() not in ('Power Macintosh','ppc','ppc64') or os.geteuid()==0:
        print('Normal-user Leopard G5 only; launch through run-suite.py.');return 2
    here=os.path.dirname(os.path.realpath(__file__));os.chdir(here)
    out=os.path.join(here,'suite-results')
    if not os.path.isdir(out):print('Run through run-suite.py first.');return 2
    if os.path.exists('/tmp/rdngld.trace'):
        print('A global trace marker exists; comparison refused to avoid mixing debug modes.');return 2
    if os.environ.get('DYLD_INSERT_LIBRARIES'):
        print('Prior injected libraries detected; capture refused to avoid changing that setup.');return 2
    if fingerprint(DRIVER)!=EXPECTED:
        print('Driver fingerprint differs: private-symbol capture refused. Share existing results.');return 2
    processes=subprocess.Popen(['/bin/ps','-ax','-o','comm='],stdout=subprocess.PIPE).communicate()[0]
    if any(os.path.basename(line.strip())=='System Preferences' for line in processes.splitlines()):
        print('Quit System Preferences normally before starting the suite. No application was terminated.');return 2
    try:read_input=raw_input
    except NameError:read_input=input
    print('Two comparisons: baseline logging, then temporary process-local tracing.')
    print('No installation, global markers, theme change, or software override.')
    complete=True
    for tag in ('baseline','trace'):
        read_input('Press Return to launch the '+tag+' Preferences comparison: ')
        env=os.environ.copy();env['RDN_SOFTWARE']='0'
        env['RDN_GLD_LOG']=os.path.join(out,tag+'-preferences-driver.log')
        if tag=='trace':
            env['RDN_CAPTURE_ENABLE']='1';env['RDN_CAPTURE_SECONDS']='90'
            env['DYLD_INSERT_LIBRARIES']=os.path.join(here,'preferences-capture.dylib')
            env['RDN_CAPTURE_STATUS']=os.path.join(out,'preferences-state.log')
            env['RDN_GLD_TRACE_ONLY']=','.join(['glBindBuffer','glBindBufferARB','glDeleteBuffers','glDeleteBuffersARB','glBufferData','glBufferDataARB','glMapBuffer','glMapBufferARB','glUnmapBuffer','glUnmapBufferARB','glTexImage2D','glTexSubImage2D','glPixelStorei','glBindTexture','glActiveTexture','glBlendFunc','glBlendFuncSeparate','glScissor','glViewport','glColorMask','glEnable','glDisable','glProgramStringARB','glBindProgramARB','glProgramLocalParameter4fARB','glCopyTexSubImage2D','glCopyTexImage2D','glPushAttrib','glPopAttrib','glPushClientAttrib','glPopClientAttrib','glDrawArrays','glDrawElements','glBegin','glEnd','glMultiTexCoord2f','glMultiTexCoord4f','glTexCoord2f','glColor4ub','glColor4f','glVertex2f'])
            print('Tracing lasts up to90 seconds/32MiB and may change timing/cache behavior.')
        console=open(os.path.join(out,tag+'-preferences-console.log'),'wb')
        child=subprocess.Popen([APP],stdout=console,stderr=subprocess.STDOUT,env=env,preexec_fn=os.setpgrp)
        notes=open(os.path.join(out,tag+'-preferences-observations.txt'),'w')
        try:
            for pane in ('Sound','Security'):
                print(tag+': open '+pane+', reproduce the glitch, return to this Terminal.')
                answer=read_input(pane+' appearance (describe briefly, then Return): ')
                notes.write(pane+': '+answer+'\n');notes.flush()
                answer=read_input('Capture ONLY the Preferences window? y/N: ')
                if answer.lower()=='y':
                    print('Click the Preferences window when the selector appears. Escape cancels.')
                    result=subprocess.call(['/usr/sbin/screencapture','-i','-w','-x',os.path.join(out,tag+'-'+pane.lower()+'.png')])
                    notes.write(pane+' screenshot_exit='+str(result)+'\n');notes.flush()
            print('Quit System Preferences normally now (Command-Q). Waiting for that quit.')
            code=child.wait();notes.write('application_exit='+str(code)+'\n')
            if code:complete=False
        finally:notes.close();console.close()
    path=os.path.join(out,'preferences-state.log');state=''
    if os.path.isfile(path):
        stream=open(path);state=stream.read();stream.close()
    enabled='ENABLED pid-local flags' in state
    print('Tracing enabled='+str(enabled)+'. Idle samples may be absent if no Mesa context is current.')
    return 0 if enabled and complete else 1
if __name__=='__main__':sys.exit(main())
