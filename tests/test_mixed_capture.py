"""Exercise actual mixed-test classification and helper address checks on host.
Models validate the diagnostic, not Radeon/PPC cache coherency.
"""
from pathlib import Path
import subprocess,tempfile,unittest,re,importlib.util,os,hashlib,sys,types
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
class MixedCapture(unittest.TestCase):
 def test_private_symbol_address_bounds(self):
  source=(ROOT/'tools/guest/preferences-capture.c').read_text();i=source.index('static int capture_range(');fn=source[i:source.index('\nstatic void *local_symbol',i)]
  main='''
int main(void){
 assert(capture_range(100,100,4,0,2,2));assert(!capture_range(104,100,4,0,2,2));
 assert(!capture_range(102,100,12,0,2,2));assert(!capture_range(100,100,4,0,1,2));
 assert(capture_range(100,100,4,4000,2,2));assert(capture_range(100,100,4,-100,2,2));
 assert(!capture_range(100,100,4,-101,2,2));
 assert(capture_range(0xfffffffcU,0xfffffffcU,4,0,2,2));
 assert(!capture_range(0xfffffffcU,0xfffffffcU,4,4,2,2));
 assert(!capture_range(0xfffffffffULL,100,4,0,2,2));
 assert(!capture_range(100,100,4,INT64_MAX,2,2));
 assert(!capture_range(100,100,UINT64_MAX,0,2,2));
}
'''
  self.compile_run('#include <assert.h>\n#include <stdint.h>\n'+fn+main)
 def compile_run(self,source):
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(source)
   subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
   return subprocess.check_output([str(p/'test'),d],text=True)
 def test_mixed_lock_contract_and_observation_classification(self):
  body=(ROOT/'tools/guest/mixed-backing-cases.h').read_text().replace('#include <sys/stat.h>','').replace('__asm__ volatile("sync":::"memory");','__asm__ volatile("":::"memory");')
  prefix=r'''
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
#include <sys/stat.h>
typedef int CGLContextObj;typedef int io_connect_t;typedef unsigned IOByteCount;
typedef unsigned GLenum;typedef int IOAccelSurfaceInformation;
#define GL_SCISSOR_TEST 1
#define GL_COLOR_BUFFER_BIT 2
#define GL_NO_ERROR 0
#define kIOAccelSurfaceReadLockOptions 1
#define kIOAccelSurfaceReadUnlockOptions 2
#define kIOAccelSurfaceWriteLockOptions 3
#define kIOAccelSurfaceWriteUnlockOptions 4
#define CHECK(x) do{if((x))return 1;}while(0)
static unsigned W,H,S,gx,gy,gw,gh;static int scissors,drop_write;
static unsigned char *CPU,*GPU,color[4];
static void glDisable(int cap){assert(cap==1);scissors=0;}
static void glEnable(int cap){assert(cap==1);scissors=1;}
static void glColorMask(int a,int b,int c,int d){assert(a&&b&&c&&d);}
static void glClearColor(float r,float g,float b,float a){color[0]=a*255;color[1]=r*255;color[2]=g*255;color[3]=b*255;}
static void glClear(int mask){assert(mask==2);for(unsigned y=0;y<H;y++)for(unsigned x=0;x<W;x++)if(!scissors||(x>=gx&&x<gx+gw&&H-1-y>=gy&&H-1-y<gy+gh))memcpy(GPU+y*S+x*4,color,4);}
static void glScissor(unsigned x,unsigned y,unsigned w,unsigned h){gx=x;gy=y;gw=w;gh=h;}
static void glFinish(void){}
static unsigned glGetError(void){return 0;}
static int IOConnectMethodScalarIStructureO(int conn,int selector,int count,unsigned *bytes,int zero,int *info){
 (void)conn;(void)bytes;(void)info;assert(count==1&&!zero);
 if(selector==1)memcpy(CPU,GPU,H*S);else assert(selector==3);return 0;
}
static int IOConnectMethodScalarIScalarO(int conn,int selector,int count,int output,int arg){
 (void)conn;assert(count==1&&!output&&!arg);
 if(selector==4&&!drop_write)memcpy(GPU,CPU,H*S);else assert(selector==2||selector==4);return 0;
}
static int attach(void *producer,unsigned long id){assert(!producer&&id==123);memcpy(GPU,CPU,H*S);return 1;}
'''
  main=r'''
int main(int argc,char **argv){(void)argc;
 const unsigned widths[]={65,672},heights[]={33,464};unsigned serial=0;
 for(unsigned geometry=0;geometry<2;geometry++)for(unsigned aligned=0;aligned<2;aligned++){
  W=widths[geometry];H=heights[geometry];S=aligned?((W*4+255)&~255u):W*4+28;
  CPU=calloc(H,S);GPU=calloc(H,S);assert(CPU&&GPU);
  const char *modes[]={"mixed-locked","mixed-direct","mixed-reattach","mixed-locked"};
  for(unsigned mode=0;mode<4;mode++){
   char path[1024];snprintf(path,sizeof(path),"%s/case-%u",argv[1],serial++);
   drop_write=mode==3;
   int result=mixed_backing(0,0,CPU,W,H,S,modes[mode],path,attach,NULL,123);
   assert(result==(drop_write?1:0));
  }
  free(CPU);free(GPU);
 }
}
'''
  output=self.compile_run(prefix+body+main)
  direct=re.findall(r'MIXED_RESULT mode=mixed-direct total_mismatches=(\d+)',output)
  self.assertEqual(len(direct),4);self.assertTrue(all(int(n)>0 for n in direct))
class MainRunner(unittest.TestCase):
 def test_packed_default_and_one_archive(self):
  spec=importlib.util.spec_from_file_location('suite',ROOT/'tools/guest/pixel-probe-package/run-suite.py')
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);mod.__file__=str(p/'run-suite.py');seen=[];commands=[]
   fake=types.SimpleNamespace(DRIVER='fixture',EXPECTED='pinned',fingerprint=lambda path:'pinned')
   class Version:
    def __init__(self,*a,**kw):pass
    def communicate(self):return ('10.5.9',None)
   def job(label,args,timeout,visual=False,env=None):
    seen.append(label)
    if label=='capture-preflight':
     self.assertEqual(env['RDN_CAPTURE_SECONDS'],'2')
     self.assertEqual(env['DYLD_INSERT_LIBRARIES'],os.path.realpath(p/'preferences-capture.dylib'))
    return ('VISUAL_REVIEW_REQUIRED' if visual else 'PASS'),False
   before=os.getcwd()
   try:
    with patch.object(mod.platform,'system',return_value='Darwin'),patch.object(mod.platform,'machine',return_value='ppc'),patch.object(mod.os,'geteuid',return_value=501),patch.object(mod.subprocess,'Popen',Version),patch.object(mod,'run_job',job),patch.object(mod.subprocess,'call',side_effect=lambda a:commands.append(a) or 0),patch.dict(sys.modules,{'capture_preferences':fake}),patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['run-suite.py']):
     self.assertEqual(mod.main(),0)
    self.assertEqual(sum(x.startswith('mixed-') for x in seen),0)
    self.assertNotIn('gpu',seen);self.assertNotIn('capture-preflight',seen);self.assertIn('gpu-packed',seen);self.assertIn('software-packed',seen)
    self.assertEqual(len(commands),1);self.assertEqual(commands[0][0],'/usr/bin/zip')
    self.assertIn('gpu-packed: PASS',(p/'suite-results/summary.txt').read_text())
    self.assertIn('preferences-capture: NOT_REQUESTED_PACKED_MODE',(p/'suite-results/summary.txt').read_text())
   finally:os.chdir(before)

class FocusedCaptureRunner(unittest.TestCase):
 def test_capture_option_keeps_focused_jobs_and_runs_preflight(self):
  spec=importlib.util.spec_from_file_location('focused_suite',ROOT/'tools/guest/pixel-probe-package/run-suite.py')
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);mod.__file__=str(p/'run-suite.py');seen=[];commands=[]
   fake=types.SimpleNamespace(DRIVER='fixture',EXPECTED='pinned',fingerprint=lambda path:'pinned')
   class Version:
    def __init__(self,*a,**kw):pass
    def communicate(self):return ('10.5.9',None)
   def job(label,args,timeout,visual=False,env=None):
    seen.append(label);return ('PASS',False)
   before=os.getcwd()
   try:
    with patch.object(mod.platform,'system',return_value='Darwin'),patch.object(mod.platform,'machine',return_value='ppc'),patch.object(mod.os,'geteuid',return_value=501),patch.object(mod.subprocess,'Popen',Version),patch.object(mod,'run_job',job),patch.object(mod.subprocess,'call',side_effect=lambda a:commands.append(a) or 0),patch.dict(sys.modules,{'capture_preferences':fake}),patch.dict(os.environ,{},clear=True),patch.object(sys,'argv',['run-suite.py','--capture']):
     self.assertEqual(mod.main(),0)
    self.assertEqual(seen,['environment','gpu-packed','gpu-glyph','gpu-program','software-packed','software-glyph','software-program','capture-preflight'])
    self.assertTrue(any('capture_preferences.py' in str(x) for x in commands))
    self.assertIn('preferences-capture: COLLECTED_REVIEW_REQUIRED',(p/'suite-results/summary.txt').read_text())
   finally:os.chdir(before)
 def test_capture_filter_includes_buffer_binding(self):
  source=(ROOT/'tools/guest/pixel-probe-package/capture_preferences.py').read_text()
  for entry in ('glBindBuffer','glBindBufferARB','glBufferData','glTexSubImage2D'):
   self.assertIn("'"+entry+"'",source)

class CaptureRunner(unittest.TestCase):
 def test_pinned_app_capture_flow_and_process_local_environment(self):
  spec=importlib.util.spec_from_file_location('capture',ROOT/'tools/guest/pixel-probe-package/capture_preferences.py')
  mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'suite-results').mkdir();driver=p/'driver';driver.write_bytes(b'qualified test fixture')
   mod.__file__=str(p/'capture_preferences.py');mod.DRIVER=str(driver);mod.EXPECTED=hashlib.sha256(driver.read_bytes()).hexdigest()
   launches=[]
   class Child:
    def __init__(self,args,**kw):
     self.args=args
     if args[0]!='/bin/ps':
      launches.append((args,kw))
      if 'RDN_CAPTURE_STATUS' in kw['env']:Path(kw['env']['RDN_CAPTURE_STATUS']).write_text('ENABLED pid-local flags\nSTOP reason=process-exit\n')
    def communicate(self):return ('',None)
    def wait(self):return 0
   before=os.getcwd();prior=dict(os.environ)
   try:
    with patch.object(mod.platform,'system',return_value='Darwin'),patch.object(mod.platform,'machine',return_value='ppc'),patch.object(mod.os,'geteuid',return_value=501),patch.object(mod.subprocess,'Popen',Child),patch('builtins.input',side_effect=['','Sound text corruption','n','Security text corruption','n']*2),patch.dict(os.environ,{},clear=True):
     self.assertEqual(mod.main(),0)
     self.assertNotIn('DYLD_INSERT_LIBRARIES',os.environ)
    self.assertEqual(len(launches),2);self.assertNotIn('DYLD_INSERT_LIBRARIES',launches[0][1]['env']);env=launches[1][1]['env']
    self.assertEqual(env['RDN_SOFTWARE'],'0');self.assertEqual(env['RDN_CAPTURE_SECONDS'],'90')
    self.assertEqual(launches[0][1]['preexec_fn'],os.setpgrp)
    self.assertIn('Sound text corruption',(p/'suite-results/baseline-preferences-observations.txt').read_text())
   finally:os.chdir(before)
   self.assertEqual(dict(os.environ),prior)

if __name__=='__main__':unittest.main()
