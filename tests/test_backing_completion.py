"""Production backing import changes only the opted-in alias shortcut."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <assert.h>
#include <stdint.h>
#include <stdbool.h>
#include <stddef.h>
#include <string.h>
#include <errno.h>
#include <stdarg.h>
#define F_OK 0
#define GL_FALSE 0
#define LOG_NOTICE 5
#define RDN_GPU_INDEX 0
static int rdn_window_server=1,marker=1,accesses,imports,fail_copy,flushes,queries,notices;
static int access(const char *p,int mode){(void)mode;assert(strstr(p,"backing-completion"));++accesses;if(marker==1)return 0;errno=marker==0?ENOENT:EACCES;return -1;}
static void syslog(int level,const char *format,...){(void)level;(void)format;++notices;}
#define rdn_log(...) ((void)0)
#define pthread_mutex_lock(p) ((void)0)
#define pthread_mutex_unlock(p) ((void)0)
static int surface_store_lock;
struct surface_store {unsigned id,unknown;struct surface_store *next;};static struct surface_store *surface_stores;
struct context{int stored,store_new;unsigned surface,store_offset,store_row_bytes;};
typedef void *OSMesaContext;
static bool alias=true,new_store;
static void surface_store(struct context *c,unsigned w,unsigned h,int publish){(void)w;(void)h;(void)publish;c->stored=1;c->store_new=new_store;c->store_offset=4096;c->store_row_bytes=64;}
static OSMesaContext OSMesaGetCurrentContext(void){return (void*)1;}
static void OSMesaFlushRender(OSMesaContext c,int wait){assert(c&&!wait);++flushes;}
static bool rdn_target_surface_query(unsigned id,uint32_t *info,bool *found){assert(id==42);++queries;*found=true;info[1]=alias?4096:8192;info[2]=64;info[3]=16;info[4]=4;return true;}
static int rdn_target_surface_gpu_copy(unsigned id,unsigned off,unsigned stride,unsigned w,unsigned h){assert(id==42&&off==4096&&stride==64&&w==16&&h==4);++imports;return fail_copy;}
static bool rdn_target_surface_buffer(unsigned id,unsigned off,unsigned stride,unsigned w,unsigned h){assert(id==42&&off==4096&&stride==64&&w==16&&h==4);return true;}
static unsigned char vram[256];static void *rdn_target_vram_map(unsigned off){assert(off==4096);return vram;}
'''
CASES=r'''
int main(int argc,char **argv){assert(argc==2);int mode=argv[1][0]-'0';
 marker=mode;rdn_window_server=mode!=3;
 struct context c={0};c.surface=42;
 assert(backing_store(&c,NULL,64,16,4,1,0));
 assert(imports==(mode==1));assert(accesses==(mode!=3));assert(flushes==1&&queries==1);
 /* Cached marker policy must not repeatedly touch configuration. */
 marker=mode==1?0:1;assert(backing_store(&c,NULL,64,16,4,1,0));assert(imports==2*(mode==1));assert(accesses==(mode!=3));
 /* Nonaliases always use the checked import, regardless of policy. */
 alias=false;assert(backing_store(&c,NULL,64,16,4,1,1));assert(imports==2*(mode==1)+1);
 /* Existing timeout handling retains/marks an unknown destination. */
 struct surface_store store={42,0,NULL};surface_stores=&store;fail_copy=2;
 assert(!backing_store(&c,NULL,64,16,4,1,0)&&!c.stored&&store.unknown);
 /* CPU path is untouched: first store copied, existing store not refreshed. */
 fail_copy=0;unsigned char bytes[256];memset(bytes,0xa5,sizeof(bytes));new_store=true;
 int before=imports;assert(backing_store(&c,bytes,64,16,4,0,1)&&!memcmp(bytes,vram,256));assert(imports==before);
}
'''
class BackingCompletion(unittest.TestCase):
 def test_existing_alias_and_failure_contract_with_each_policy(self):
  s=(ROOT/'gld/rdn_mesa.c').read_text();bodies=[]
  for result,name in [('int','ws_backing_completion'),('int','backing_store')]:
   # backing_store has an earlier prototype; require its definition.
   key='static '+result+' '+name+'(';a=s.index(key)
   if name=='backing_store':a=s.index(key,s.index('static int ws_backing_completion('))
   bodies.append(s[a:s.index('\n}',a)+2])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(PREFIX+'\n'.join(bodies)+CASES)
   subprocess.run(['cc','-std=c99','-fsanitize=address,undefined',str(p/'test.c'),'-o',str(p/'test')],check=True)
   for mode in ['0','1','2','3']:subprocess.run([str(p/'test'),mode],check=True)
if __name__=='__main__':unittest.main()
