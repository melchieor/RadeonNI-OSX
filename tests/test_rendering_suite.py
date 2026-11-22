"""Runner failure/timeout semantics and actual glyph buffer generation."""
from pathlib import Path
import importlib.util,os,subprocess,tempfile,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('suite',ROOT/'tools/guest/pixel-probe-package/run-suite.py')
suite=importlib.util.module_from_spec(spec);spec.loader.exec_module(suite)
class Suite(unittest.TestCase):
 def test_exit_and_watchdog(self):
  with tempfile.TemporaryDirectory() as d:
   before=os.getcwd()
   try:
    os.chdir(d);Path('suite-results').mkdir()
    self.assertEqual(suite.run_job('pass',['/bin/sh','-c','exit 0'],2),('PASS',False))
    self.assertEqual(suite.run_job('fail',['/bin/sh','-c','exit 1'],2),('FAIL_OR_SETUP_ERROR exit=1',False))
    self.assertEqual(suite.run_job('visual',['/bin/sh','-c','exit 0'],2,True),('VISUAL_REVIEW_REQUIRED',False))
    self.assertEqual(suite.run_job('missing',['/no/such/test'],2),('LAUNCH_ERROR',False))
    self.assertEqual(suite.run_job('timeout',['/bin/sleep','10'],0.1),('TIMEOUT_STOP',True))
    status,stop=suite.run_job('abnormal',['/bin/sh','-c','kill -TERM $$'],2)
    self.assertTrue(stop);self.assertTrue(status.startswith('ABNORMAL_STOP'))
   finally:os.chdir(before)
 def test_host_refusal(self):
  with patch.object(suite.platform,'machine',return_value='x86_64'):
   self.assertEqual(suite.main(),2)
 def test_glyph_buffers(self):
  src=(ROOT/'tools/guest/pixel-render-probe.c').read_text();start=src.index('static void glyph_formats(')
  body=src[start:src.index('\n#define RUN_FULL',start)]
  header='''
#include <assert.h>
#include <string.h>
#include "pixel-reference.h"
typedef unsigned GLenum;typedef int GLint;
#define GL_ALPHA 1
#define GL_LUMINANCE 2
#define GL_LUMINANCE_ALPHA 3
#define GL_RGB 4
#define GL_ALPHA8 5
#define GL_LUMINANCE8 6
#define GL_LUMINANCE8_ALPHA8 7
#define GL_RGB8 8
#define GL_TEXTURE_2D 9
#define GL_UNSIGNED_BYTE 10
static int damaged_readback;
static unsigned legacy_readback_kind;
static unsigned char upload[(TW+16)*(TH+4)*4+64],expected[TW*TH*4];
static unsigned calls,checks;
static void select_texture(GLenum t){assert(t==GL_TEXTURE_2D);}
static void reset_unpack(void){}
static void glTexImage2D(GLenum t,int level,GLint internal,unsigned w,unsigned h,int border,GLenum format,GLenum type,const void *p){
 assert(t==GL_TEXTURE_2D&&!level&&!border&&w==TW&&h==TH&&p==upload&&type==GL_UNSIGNED_BYTE);
 assert(format==calls+1&&internal==(int)calls+5);
 unsigned c=format==3?2:format==4?3:1;
 for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++){
  unsigned char rgba[4];pixel_source(x,y,5,rgba);unsigned char a=rgba[3],l=(x*17+y*13)&255;
  unsigned i=y*w+x;unsigned char *s=upload+i*c,*d=expected+i*4;
  if(format==1){assert(s[0]==a&&d[0]==255&&d[1]==255&&d[2]==255&&d[3]==a);}
  if(format==2){assert(s[0]==l&&d[0]==l&&d[1]==l&&d[2]==l&&d[3]==255);}
  if(format==3){assert(s[0]==l&&s[1]==a&&d[0]==l&&d[1]==l&&d[2]==l&&d[3]==a);}
  if(format==4){assert(s[0]==l&&s[1]==a&&s[2]==255-l&&d[0]==l&&d[1]==a&&d[2]==255-l&&d[3]==255);}
 }
 for(unsigned i=w*h*c;i<sizeof(upload);i++)assert(upload[i]==0xc7);
 calls++;
}
static void check_case(const char *name,int blend){assert(name&&!blend);checks++;}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'t.c').write_text(header+body+'\nint main(void){glyph_formats();assert(calls==4&&checks==4);}\n')
   for w,h in [(64,32),(257,129),(1024,256)]:
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-DTW='+str(w),'-DTH='+str(h),'-I',str(ROOT/'tools/guest'),str(p/'t.c'),'-o',str(p/'t')],check=True)
    subprocess.run([str(p/'t')],check=True)
if __name__=='__main__':unittest.main()
