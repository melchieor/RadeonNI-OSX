#!/usr/bin/env python3
"""Intel Mac Apple SOFTWARE control; no target execution/compilation."""
from pathlib import Path
import hashlib,platform,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
def main():
 if platform.system()!='Darwin' or platform.machine()!='x86_64':raise SystemExit('Intel build Mac only')
 with (ROOT/'build/leopard-v7900/logs/packed-host-software.log').open('w') as log,tempfile.TemporaryDirectory(prefix='rdn-packed-control-') as temporary:
  for source in ('pixel-render-probe.c','pixel-reference.h','packed-reference.h','packed-upload-cases.h'):
   path=ROOT/'tools/guest'/source;log.write(source+' sha256='+hashlib.sha256(path.read_bytes()).hexdigest()+'\n')
  log.flush();binary=Path(temporary)/'probe'
  subprocess.run(['cc','-std=gnu99','-Wno-deprecated-declarations','-DTW=320','-DTH=320','-I'+str(ROOT/'tools/guest'),str(ROOT/'tools/guest/pixel-render-probe.c'),'-framework','OpenGL','-o',str(binary)],check=True,stdout=log,stderr=subprocess.STDOUT)
  for mode in ('--matrix-only','--glyph-batch','--glyph-program'):
   subprocess.run([str(binary),'software',str(Path(temporary)/mode[2:]),mode],check=True,stdout=log,stderr=subprocess.STDOUT,timeout=240)
 print('Intel Apple software packed control: PASS')
if __name__=='__main__':main()
