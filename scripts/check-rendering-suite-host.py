#!/usr/bin/env python3
"""Validate synthetic GL cases using Intel Mac Apple SOFTWARE renderer only.
Never run/compile on the G5. This is not PowerPC hardware qualification.
"""
from pathlib import Path
import hashlib,platform,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
 if platform.system()!='Darwin' or platform.machine()!='x86_64':
  raise SystemExit('Intel build Mac only; never compile this on the G5')
 out=ROOT/'build/leopard-v7900/logs/masked-host-software.log'
 with out.open('w') as log,tempfile.TemporaryDirectory(prefix='rdn-host-software-') as temporary:
  for source in ('pixel-render-probe.c','pixel-reference.h','masked-render-cases.h','masked-reference.h','packed-reference.h','packed-upload-cases.h'):
   path=ROOT/'tools/guest'/source;log.write(source+' sha256='+hashlib.sha256(path.read_bytes()).hexdigest()+'\n')
  log.flush()
  for width,height in ((64,32),(257,129),(1024,256)):
   binary=Path(temporary)/'probe';pixels=Path(temporary)/('%dx%d'%(width,height))
   subprocess.run(['cc','-std=gnu99','-Wno-deprecated-declarations','-DTW='+str(width),'-DTH='+str(height),'-I'+str(ROOT/'tools/guest'),str(ROOT/'tools/guest/pixel-render-probe.c'),'-framework','OpenGL','-o',str(binary)],check=True,stdout=log,stderr=subprocess.STDOUT)
   log.write('Intel Mac software control; target_ppc_runtime_tested=false\n');log.flush()
   subprocess.run([str(binary),'software',str(pixels)],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=90)
   print('%dx%d Apple software control: PASS'%(width,height))
if __name__=='__main__':main()
