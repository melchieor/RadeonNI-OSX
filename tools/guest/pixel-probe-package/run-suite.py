#!/usr/bin/python
"""Python2.5-compatible own-process rendering suite; no root/config writes."""
import os,sys,subprocess,time,signal,platform

def run_job(label,args,timeout,visual=False,env=None):
    print('Running '+label);sys.stdout.flush()
    log=open(os.path.join('suite-results',label+'.log'),'wb')
    try:
        child=subprocess.Popen(args,stdout=log,stderr=subprocess.STDOUT,env=env)
    except OSError:
        log.write(('LAUNCH_ERROR '+str(sys.exc_info()[1])+'\n').encode('utf-8'));log.close()
        return 'LAUNCH_ERROR',False
    deadline=time.time()+timeout
    while child.poll() is None and time.time()<deadline:time.sleep(0.1)
    if child.poll() is None:
        # Only signal the test process we created, never WindowServer or apps.
        try:os.kill(child.pid,signal.SIGTERM)
        except OSError:pass
        end=time.time()+2
        while child.poll() is None and time.time()<end:time.sleep(0.1)
        if child.poll() is None:
            try:os.kill(child.pid,signal.SIGKILL)
            except OSError:pass
        log.close();return 'TIMEOUT_STOP',True
    code=child.returncode;log.close()
    if code<0 or code>=128:return 'ABNORMAL_STOP exit='+str(code),True
    if code:return 'FAIL_OR_SETUP_ERROR exit='+str(code),False
    return ('VISUAL_REVIEW_REQUIRED' if visual else 'PASS'),False

def main():
    if platform.system()!='Darwin' or platform.machine() not in ('Power Macintosh','ppc','ppc64'):
        print('Run on the Leopard Power Mac G5, not the build Mac.');return 2
    version=subprocess.Popen(['/usr/bin/sw_vers','-productVersion'],stdout=subprocess.PIPE).communicate()[0].strip()
    if version not in ('10.5.8','10.5.9') or os.geteuid()==0:
        print('Leopard 10.5.8/Sorbet10.5.9 normal user only; do not use sudo.');return 2
    here=os.path.dirname(os.path.realpath(__file__));os.chdir(here)
    if os.path.exists('suite-results') or os.path.exists('rendering-results.zip'):
        print('Existing results: use a fresh extracted directory.');return 2
    os.mkdir('suite-results')
    print('Save work and close games. Default: offscreen packed-upload condition tests; no test window.')
    print('Allow2GB disk space and several minutes. No install/settings/sleep/firmware changes.')
    env=os.environ.copy();env['RDN_SOFTWARE']='0'
    jobs=[('environment',['/usr/bin/python','-E','-S','environment.py'],30,False),
          ('qe-status',['./qe-status'],30,False),
          ('rendering-report',['/usr/bin/python','-E','-S','collect.py'],30,False)]
    for suffix in ('','-odd','-large'):
        for backend in ('gpu','software'):
            jobs.append((backend+suffix,['./pixel-render-probe'+suffix,backend,'suite-results/'+backend+suffix],90,False))
    for width,height in ((672,464),(672,468),(768,512)):
        for mode in ('linear','quartz'):
            jobs.append(('backing-%dx%d-%s'%(width,height,mode),['./backingsurfacetest','6704','21a00','1',mode,str(width),str(height)],60,False))
    jobs.extend([
        ('shared-contexts',['./sharetest','0x21a00'],60,False),
        ('thread-handoff',['./contexthandofftest','legacy','20'],60,False),
        ('pbuffer-lifetime',['./pbufferlifetest'],60,False),
        ('pbuffer-publication',['./pbufferpublishtest'],60,False),
        ('pbuffer-threads',['./pbufferthreadtest','32'],60,False),
        ('backing-import',['./backingsurfacetest','6704','21a00','1'],60,False),
        ('backing-quartz',['./backingsurfacetest','6704','21a00','1','quartz'],60,False),
        ('visual',['./rendering-suite-visual'],45,True),
        ('core-image-visual',['./ci-filter-test','CIColorInvert','8'],20,True)])
    for width,height in ((65,33),(672,464)):
        for layout in ('linear','quartz'):
            for mode in ('mixed-locked','mixed-direct','mixed-reattach'):
                label='%s-%dx%d-%s'%(mode,width,height,layout)
                jobs.append((label,['./backingsurfacetest','6704','21a00','1',layout,str(width),str(height),mode,'suite-results/'+label],60,False))
    for backend in ('gpu','software'):
        label=backend+'-packed'
        jobs.append((label,['./pixel-render-probe-atlas',backend,'suite-results/'+label,'--matrix-only'],300,False))
        label=backend+'-glyph'
        jobs.append((label,['./pixel-render-probe-atlas',backend,'suite-results/'+label,'--glyph-batch'],300,False))
        label=backend+'-program'
        jobs.append((label,['./pixel-render-probe-atlas',backend,'suite-results/'+label,'--glyph-program'],300,False))
    # Full previously qualified suite remains available; default targets new gaps.
    if '--all' not in sys.argv:
        jobs=[job for job in jobs if job[0]=='environment' or job[0].endswith(('-packed','-glyph','-program'))]
    capture_requested=('--all' in sys.argv or '--capture' in sys.argv);pin_ok=False
    if '--all' in sys.argv:
        for backend in ('gpu','software'):
            label=backend+'-previous-packed'
            jobs.append((label,['./pixel-render-probe-atlas',backend,'suite-results/'+label,'--packed-only'],300,False))
    if capture_requested:
        import capture_preferences as capture_module
        try:pin_ok=capture_module.fingerprint(capture_module.DRIVER)==capture_module.EXPECTED and not os.environ.get('DYLD_INSERT_LIBRARIES')
        except Exception:pin_ok=False
    pin=open('suite-results/capture-pin.txt','w');pin.write('capture_requested='+str(capture_requested)+'\ndriver_pinned_and_no_prior_injection='+str(pin_ok if capture_requested else 'not-checked')+'\n');pin.close()
    if pin_ok:jobs.append(('capture-preflight',['./capture-preflight'],15,False))
    elif capture_requested:print('Private capture refused: driver fingerprint differs or prior injected libraries exist.')
    summary=open('suite-results/summary.txt','w');stopped=False;issues=capture_requested and not pin_ok;preflight_ok=False
    try:
        for label,args,timeout,visual in jobs:
            if stopped:status='NOT_RUN_AFTER_STOP'
            else:
                job_env=env.copy()
                if label=='capture-preflight':
                    job_env['RDN_CAPTURE_ENABLE']='1';job_env['RDN_CAPTURE_SECONDS']='2'
                    job_env['DYLD_INSERT_LIBRARIES']=os.path.join(os.getcwd(),'preferences-capture.dylib')
                    job_env['RDN_CAPTURE_STATUS']=os.path.join(os.getcwd(),'suite-results/preflight-capture-status.log')
                if label=='core-image-visual':job_env['WSF_PLAIN']='1'
                if label.startswith('software'):job_env['RDN_SOFTWARE']='1'
                job_env['RDN_GLD_LOG']=os.path.join(os.getcwd(),'suite-results',label+'-driver.log')
                status,stopped=run_job(label,args,timeout,visual,job_env)
            if label=='capture-preflight':preflight_ok=status=='PASS'
            if label.startswith(('mixed-direct','mixed-reattach')) and status=='PASS':status='OBSERVATION_REVIEW_REQUIRED'
            if label in ('environment','rendering-report') and status=='PASS':status='COLLECTED_REVIEW_REQUIRED'
            if status not in ('PASS','VISUAL_REVIEW_REQUIRED','COLLECTED_REVIEW_REQUIRED','OBSERVATION_REVIEW_REQUIRED'):issues=True
            line=label+': '+status
            print(line);sys.stdout.flush();summary.write(line+'\n');summary.flush()
    finally:summary.close()
    if not stopped and preflight_ok:
        capture=subprocess.call(['/usr/bin/python','-E','-S','./capture_preferences.py'])
        with_status=open('suite-results/summary.txt','a')
        with_status.write('preferences-capture: '+('COLLECTED_REVIEW_REQUIRED' if capture==0 else 'INCOMPLETE_REVIEW_LOGS')+'\n');with_status.close()
        if capture:issues=True
    else:
        skipped=open('suite-results/summary.txt','a');skipped.write('preferences-capture: '+('NOT_RUN_PREFLIGHT_OR_STOP' if capture_requested else 'NOT_REQUESTED_PACKED_MODE')+'\n');skipped.close()
    notes=open('suite-results/visual-checklist.txt','w')
    if not capture_requested:notes.write('Focused offscreen packed uploads only. No visual exercise or Preferences capture requested.\n')
    else:notes.write('Please report: selected text legible? popup text intact? red/green GL panels correct?\n'
                'Core Image: did the temporary rectangle invert the desktop behind it for8 seconds?\n'
                'Any holes, stale pixels or corruption during overlap/resize? Apple menu/fonts still broken afterward?\n'
                'VISUAL_REVIEW_REQUIRED is not an automatic pass. No sleep, power loss, UVD, full VRAM,\n'
                'all-app, all-format, multi-display or full inter-process WindowServer qualification.\n')
    notes.close()
    code=subprocess.call(['/usr/bin/zip','-qr','rendering-results.zip','suite-results'])
    if code:return 2
    print('Share '+os.path.join(os.getcwd(),'rendering-results.zip')+'.')
    print('No automatic claim of GUI correctness. Do not force/retry a stopped test.')
    return 1 if issues else 0
if __name__=='__main__':
    try:sys.exit(main())
    except KeyboardInterrupt:
        print('Interrupted. Quit any launched Preferences window normally; it was not terminated by the runner.')
        if os.path.isdir('suite-results'):
            subprocess.call(['/usr/bin/zip','-qr','rendering-results.zip','suite-results'])
            print('Partial results retained in rendering-results.zip.')
        sys.exit(130)
