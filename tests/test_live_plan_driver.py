"""Run the actual live-plan driver method against fake locked allocators."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <cassert>
#include <cstdlib>
#include <cstring>
#include "rdn_user.h"
extern "C" {
#include "rdn_live_plan.h"
}
using UInt32=uint32_t;using UInt64=uint64_t;using IOReturn=int;
enum{kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,kIOReturnNoMemory=3,kIOReturnNotReady=4,RDN_QUIESCE_RUNNING=0};
#define bzero(p,n) memset((p),0,(n))
struct Lock{bool held=false;};static void IOLockLock(Lock *p){assert(!p->held);p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
static int yes;static void *kOSBooleanTrue=&yes;static bool failalloc=false;static unsigned allocations=0,frees=0;
static void *IOMalloc(size_t n){if(failalloc)return nullptr;++allocations;return malloc(n);}
static void IOFree(void *p,size_t){++frees;free(p);}
static void *mem_alloc(void*,size_t n){return calloc(1,n);}static void mem_free(void*,void *p){free(p);}
struct FB{bool enabled=true;void *getProperty(const char*){return enabled?kOSBooleanTrue:nullptr;}};
struct RadeonNIAccel{
 Lock lock,*fLock=&lock;FB fb,*fFramebuffer=&fb;bool fEngineUp=true,fRetiring=false;
 struct{int phase=RDN_QUIESCE_RUNNING;}fQuiesce;
 rdn_mem fMem{},fCommandMem{},fHidden{};UInt32 fHiddenSize=0x8000;
 struct{uint64_t vram_size=0x10000;uint32_t aperture_size=0x8000;}fAccel;rdn_os os{};
 RadeonNIAccel(){os.alloc=mem_alloc;os.free=mem_free;assert(!rdn_mem_init(&fCommandMem,&os,0x2000,0x2000));
  assert(!rdn_mem_init(&fMem,&os,0x4000,0x4000));assert(!rdn_mem_init(&fHidden,&os,0x8000,0x8000));}
 ~RadeonNIAccel(){rdn_mem_fini(&fHidden);rdn_mem_fini(&fMem);rdn_mem_fini(&fCommandMem);}
 IOReturn sleepLivePlan(rdn_user_live_plan*);
};
'''
CASES=r'''
int main(){RadeonNIAccel a;rdn_user_live_plan out{};uint64_t off;
 assert(!rdn_mem_alloc(&a.fHidden,4096,4096,&off));
 assert(!a.sleepLivePlan(&out));assert(!a.lock.held&&allocations==2&&frees==2);
 assert(out.version==1&&out.range_count==2&&out.hidden_allocations==1);
 assert(out.reserved_lo==0x2000&&out.hidden_lo==4096&&out.image_lo==0x3000);
 assert(out.missing_mask==15&&!out.content_saved);
 a.fRetiring=true;assert(a.sleepLivePlan(&out)==kIOReturnNotReady&&!a.lock.held);a.fRetiring=false;
 a.fb.enabled=false;assert(a.sleepLivePlan(&out)==kIOReturnUnsupported);a.fb.enabled=true;
 failalloc=true;assert(a.sleepLivePlan(&out)==kIOReturnNoMemory&&!a.lock.held);
}
'''
class DriverPlan(unittest.TestCase):
 def test_actual_method(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIAccel::sleepLivePlan(')
  fn=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(PREFIX+fn+CASES);objects=[]
   for name in ('rdn_mem','rdn_snapshot_plan','rdn_live_plan'):
    obj=p/(name+'.o');subprocess.run(['cc','-I'+str(ROOT/'hw'),'-c',str(ROOT/'hw'/(name+'.c')),'-o',str(obj)],check=True);objects.append(str(obj))
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1','-I'+str(ROOT/'hw'),str(p/'test.cpp'),*objects,'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
