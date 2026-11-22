"""Production client pixel state survives nesting, failures, and context switches."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <assert.h>
#include <stddef.h>
#define MAX_CONTEXTS 2
struct context{void *gld_ctx,*rend;int unpack_row_bytes;
 struct{int bytes,client_storage;unsigned pixel;}unpack_stack[16];};
static struct context contexts[2];
'''
CASES=r'''
int main(void){int token[4];void *a=&token[0],*b=&token[1];
 contexts[0].gld_ctx=&token[2];contexts[0].rend=a;
 contexts[1].gld_ctx=&token[3];contexts[1].rend=b;
 rdn_mesa_unpack_row_bytes(a,640);rdn_mesa_unpack_row_bytes(b,128);
 assert(rdn_mesa_unpack_client_attrib(a,1,0,1,1,1)==-1);
 rdn_mesa_unpack_row_bytes(a,1024);
 assert(rdn_mesa_unpack_client_attrib(a,1,1,2,1,0)==-1);
 rdn_mesa_unpack_row_bytes(a,2048);
 assert(rdn_mesa_unpack_client_attrib(a,0,2,1,0,1)==0);
 assert(rdn_mesa_unpack_row_bytes(a,-1)==1024);
 assert(rdn_mesa_unpack_client_attrib(a,0,1,0,0,0)==1);
 assert(rdn_mesa_unpack_row_bytes(a,-1)==640&&rdn_mesa_unpack_row_bytes(b,-1)==128);
 /* Non-pixel entries count for depth but must not restore pixel state. */
 assert(rdn_mesa_unpack_client_attrib(a,2,0,1,1,0)==-1);
 rdn_mesa_unpack_row_bytes(a,300);
 assert(rdn_mesa_unpack_client_attrib(a,0,1,0,0,1)==-1&&rdn_mesa_unpack_row_bytes(a,-1)==300);
 /* Failed Mesa stack operations must not consume/reset saved entries. */
 assert(rdn_mesa_unpack_client_attrib(a,1,0,1,1,1)==-1);
 rdn_mesa_unpack_row_bytes(a,999);
 assert(rdn_mesa_unpack_client_attrib(a,1,16,16,1,0)==-1);
 assert(rdn_mesa_unpack_client_attrib(a,0,0,0,0,0)==-1);
 assert(rdn_mesa_unpack_client_attrib(a,0,1,0,0,0)==1&&rdn_mesa_unpack_row_bytes(a,-1)==300);
 for(int n=0;n<1000;n++){
  rdn_mesa_unpack_row_bytes(a,64+n);
  for(int i=0;i<16;i++)assert(rdn_mesa_unpack_client_attrib(a,1,i,i+1,1,i&1)==-1);
  rdn_mesa_unpack_row_bytes(a,1);
  for(int i=15;i>=0;i--)assert(rdn_mesa_unpack_client_attrib(a,0,i+1,i,0,0)==(i&1));
  assert(rdn_mesa_unpack_row_bytes(a,-1)==64+n);
 }
 assert(rdn_mesa_unpack_client_attrib(NULL,1,0,1,1,1)==-1);
}
'''
class PixelState(unittest.TestCase):
 def test_production_stack_restores_extension_state(self):
  text=(ROOT/'gld/rdn_mesa.c').read_text();parts=[]
  for name in ['rdn_mesa_unpack_row_bytes','rdn_mesa_unpack_client_attrib']:
   a=text.index('int '+name+'(');parts.append(text[a:text.index('\n}',a)+2])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(PREFIX+'\n'.join(parts)+CASES)
   subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_generated_dispatch_reproduces_old_failure_and_restores_new_state(self):
  text=(ROOT/'gld/rdn_mesa.c').read_text();helpers=[]
  for name in ['rdn_mesa_unpack_row_bytes','rdn_mesa_unpack_client_attrib']:
   a=text.index('int '+name+'(');helpers.append(text[a:text.index('\n}',a)+2])
  prefix=PREFIX+r"""
typedef void *GLIContext;typedef int GLint;typedef unsigned GLbitfield;
static struct{unsigned count;}rowrun;
static int call_stats,lazy_pending,rdn_trace,depth,error,client_storage;
static struct{int client_storage;}apple;
static void *current;
#define RDN_ENTER(c) (current=(c))
#define rowrun_flush_for(c) ((void)0)
#define rdn_list_recording() 0
#define rdn_list_record(...) ((void)0)
#define call_note(n) ((void)0)
#define lazy_flush(c) ((void)0)
#define rdn_trace_wanted(n) 0
#define rdn_log(...) ((void)0)
#define elide_arrays_unknown(c,n) ((void)0)
#define apple_ctx(c) (&apple)
struct list_args_push_client_attrib{unsigned mask;};
struct list_args_pop_client_attrib{unsigned char unused;};
static void m_get_integerv(unsigned pname,int *out){assert(pname==0x0BB1);*out=depth;}
static void m_push_client_attrib(unsigned mask){(void)mask;if(depth==16)error=0x503;else depth++;}
static void m_pop_client_attrib(void){if(!depth)error=0x504;else depth--;}
"""
  cases=r"""
int main(void){int token;void *a=&token;contexts[0].gld_ctx=&token;contexts[0].rend=a;
 rdn_mesa_unpack_row_bytes(a,64);apple.client_storage=1;error=123;
 t_push_client_attrib(a,1);rdn_mesa_unpack_row_bytes(a,128);apple.client_storage=0;
 t_pop_client_attrib(a);
 if(rdn_mesa_unpack_row_bytes(a,-1)!=64 || apple.client_storage!=1)return 17;
 assert(!depth && error==123);
 t_push_client_attrib(a,2);rdn_mesa_unpack_row_bytes(a,300);t_pop_client_attrib(a);
 assert(rdn_mesa_unpack_row_bytes(a,-1)==300);
 depth=16;t_push_client_attrib(a,1);assert(depth==16&&error==0x503);
 depth=0;t_pop_client_attrib(a);assert(!depth&&error==0x504&&rdn_mesa_unpack_row_bytes(a,-1)==300);
 return 0;
}
"""
  header=ROOT/'third_party/sdk-audit/extracted/MacOSX10.5.sdk/System/Library/Frameworks/OpenGL.framework/Headers/gliDispatch.h'
  with tempfile.TemporaryDirectory() as d:
   p=Path(d)
   old=subprocess.check_output(['git','show','7527fc44:gld/gen_dispatch.py'],cwd=ROOT)
   (p/'old.py').write_bytes(old)
   for generator,expected,label in [(p/'old.py',17,'old'),(ROOT/'gld/gen_dispatch.py',0,'fixed')]:
    subprocess.run(['python3',str(generator),str(header),str(p/'dispatch.c')],check=True)
    generated=(p/'dispatch.c').read_text();bodies=[]
    for name in ['push_client_attrib','pop_client_attrib']:
     a=generated.index('static void t_'+name+'(');bodies.append(generated[a:generated.index('\n}',a)+2])
    (p/'test.c').write_text(prefix+'\n'.join(helpers+bodies)+cases)
    subprocess.run(['cc','-std=c99',str(p/'test.c'),'-o',str(p/'test')],check=True)
    result=subprocess.run([str(p/'test')])
    self.assertEqual(result.returncode,expected,label)
if __name__=='__main__':unittest.main()
