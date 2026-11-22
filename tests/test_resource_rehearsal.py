"""Production resource helpers and public wrapper ownership/cleanup boundaries."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
HELPER=r'''
#include <cassert>
#include <cstdlib>
#include <cstring>
#include <cstdint>
extern "C" {
#include "rdn_mem.h"
#include "rdn_snapshot.h"
#include "rdn_user.h"
#include "rdn_quiesce.h"
}
using UInt32=uint32_t;using UInt64=uint64_t;
static void OSSynchronizeIO(){}static void rdnStoreBarrier(){}
static void *allocate(void*,size_t n){return calloc(1,n);}static void release(void*,void *p){free(p);}
struct RadeonNIAccel {
 rdn_mem fMem{},fCommandMem{},fHidden{};UInt32 fHiddenSize=0,fGartTable=0;
 enum {kMaxGartBindings=4,kSurfaceMirrors=4};
 struct {void *memory;UInt32 offset,size,vram;} fGartBound[4]{};
 struct SurfaceMirror {UInt32 surface,offset,stride,width,height;};SurfaceMirror fSurfaceMirrors[4]{};
 struct Shape{bool used;UInt32 bufWidth,bufOffset,bufRowBytes,bufHeight;} shapes[4]{};
 Shape *fShapes=shapes;UInt32 fShapeCapacity=4;
 struct {UInt64 vram_size=16384;UInt32 aperture_size=16384;volatile uint32_t *aperture;
 UInt32 ring_offset=0,ring_words=1024,fence_offset=4,fence_emitted=7,wptr=8;} fAccel;
 rdn_quiesce fQuiesce{};UInt32 vram[4096]{};rdn_os os{};
 RadeonNIAccel(){os.alloc=allocate;os.free=release;fAccel.aperture=vram;fQuiesce.phase=RDN_QUIESCE_HELD_POWERED;
  assert(!rdn_mem_init(&fCommandMem,&os,0,4096));assert(!rdn_mem_init(&fMem,&os,4096,12288));}
 ~RadeonNIAccel(){rdn_mem_fini(&fCommandMem);rdn_mem_fini(&fMem);}
 bool resourceInventory(rdn_user_sleep_resource*);bool resourceSnapshot(rdn_user_sleep_resource*,void*);
 bool resourceAllocationValid(UInt32);
};
'''
HELPER_CASES=r'''
int main(){RadeonNIAccel a;rdn_user_sleep_resource r{};uint64_t off;uint32_t backup[1024];
 assert(!rdn_mem_alloc(&a.fMem,4096,4096,&off)&&off==4096);
 assert(a.resourceAllocationValid(off));assert(!a.resourceAllocationValid(off+4));assert(!a.resourceAllocationValid(16384));
 a.shapes[0]={true,1,4096,4,1};assert(!a.resourceAllocationValid(off));a.shapes[0].used=false;
 a.fSurfaceMirrors[0].surface=1;a.fSurfaceMirrors[0].offset=off;assert(!a.resourceAllocationValid(off));a.fSurfaceMirrors[0].surface=0;
 a.fGartBound[0].vram=off;assert(!a.resourceAllocationValid(off));a.fGartBound[0].vram=0;
 assert(a.resourceInventory(&r)&&r.visible_allocations==1&&r.visible_used==4096&&!r.hidden_used);
 for(unsigned i=0;i<4096;i++)a.vram[i]=0xab000000^i;
 r.owned_offset=off;r.owned_bytes=4096;r.private_connection=r.allocation_valid=1;
 assert(a.resourceSnapshot(&r,backup)&&r.saved_words==1024&&r.restored_words==1024&&r.metadata_unchanged&&!r.restore_mismatches&&!r.poison_mismatches);
 for(unsigned i=0;i<4096;i++)assert(a.vram[i]==(0xab000000^i));
 a.fQuiesce.phase=0;assert(!a.resourceSnapshot(&r,backup));a.fQuiesce.phase=2;
 r.allocation_valid=0;assert(!a.resourceSnapshot(&r,backup));
 a.fAccel.vram_size=1;assert(!a.resourceInventory(&r));
 static_assert(sizeof(r)==224,"fixed report ABI");
}
'''
ACCESS=r'''
#include <cassert>
#include <cstdlib>
#include <cstring>
#include "rdn_user.h"
using UInt32=uint32_t;using IOByteCount=size_t;using IOReturn=int;
enum{kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNotPrivileged=2,kIOReturnBusy=3,kIOReturnNoMemory=4};
struct Lock{bool held=false,busy=false;};
static bool IOLockTryLock(Lock *p){if(p->busy)return false;assert(!p->held);return p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
static unsigned allocations,frees;static bool fail_alloc;
static void *IOMalloc(unsigned n){if(fail_alloc)return nullptr;++allocations;return malloc(n);}
static void IOFree(void *p,unsigned){++frees;free(p);}
struct Accel{unsigned calls=0;int answer=0;
 int sleepRehearsal(UInt32 action,UInt32,rdn_user_sleep_rehearsal*,rdn_user_sleep_maintenance*,rdn_user_sleep_resource *r,void *backup=nullptr){
  ++calls;if(action){assert(backup&&r->private_connection&&r->owned_bytes==4096);}else assert(!backup);return answer;}
};
struct RadeonNIUserClient {
 bool fUvdAdministrator=false,fSurfaceGpuFailed=false,fSurfaceCompositor=false,fUvdUser=false,fWindowServerClient=false;
 Lock lock;Lock *fAllocationLock=&lock;UInt32 offsets[2]{4096,8192},*fOffsets=offsets,fCount=1;
 Accel accel,*fAccel=&accel;
 IOReturn methodSleepResource(UInt32,UInt32,UInt32,UInt32,rdn_user_sleep_resource*,IOByteCount*);
};
'''
ACCESS_CASES=r'''
int main(){RadeonNIUserClient c;rdn_user_sleep_resource r{};size_t size=sizeof(r);
 assert(!c.methodSleepResource(0,0,0,0,&r,&size)&&c.accel.calls==1&&!allocations);
 assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnNotPrivileged);
 c.fUvdAdministrator=true;
 assert(c.methodSleepResource(1,50,8192,4096,&r,&size)==kIOReturnBadArgument&&!allocations&&!c.lock.held);
 c.fCount=2;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnBadArgument);c.fCount=1;
 c.fSurfaceCompositor=true; /* Authorization is not WindowServer identity. */
 c.fWindowServerClient=true;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnBadArgument);c.fWindowServerClient=false;
 c.lock.busy=true;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnBusy);c.lock.busy=false;
 fail_alloc=true;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnNoMemory&&!c.lock.held);fail_alloc=false;
 assert(!c.methodSleepResource(1,50,4096,4096,&r,&size)&&allocations==1&&frees==1&&!c.lock.held);
 c.accel.answer=kIOReturnBusy;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnBusy&&allocations==2&&frees==2&&!c.lock.held);
 assert(c.methodSleepResource(1,50,4096,8192,&r,&size)==kIOReturnBadArgument);
 --size;assert(c.methodSleepResource(1,50,4096,4096,&r,&size)==kIOReturnBadArgument);
}
'''
class Resources(unittest.TestCase):
 def run_harness(self,prefix,functions,cases,link=False):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text();b=[]
  for declaration in functions:
   i=source.index(declaration);b.append(source[i:source.index('\n}',i)+2])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(prefix+'\n'.join(b)+cases);objects=[]
   if link:
    for module in ['rdn_mem','rdn_snapshot']:
     obj=p/(module+'.o');subprocess.run(['cc','-I',str(ROOT/'hw'),'-c',str(ROOT/'hw'/(module+'.c')),'-o',str(obj)],check=True);objects.append(str(obj))
   subprocess.run(['c++','-std=c++11','-I',str(ROOT/'hw'),str(p/'test.cpp'),*objects,'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_private_page_restore_and_inventory(self):
  self.run_harness(HELPER,['bool RadeonNIAccel::resourceInventory(', 'static void rdnSnapshotBarrier(', 'bool RadeonNIAccel::resourceSnapshot(', 'bool RadeonNIAccel::resourceAllocationValid('],HELPER_CASES,True)
 def test_ownership_privilege_and_cleanup(self):
  self.run_harness(ACCESS,['IOReturn RadeonNIUserClient::methodSleepResource('],ACCESS_CASES)
 def test_actual_root_and_windowserver_initialization(self):
  extra=r"""
#define RDN_LEOPARD 1
#define super IOUserClient
using task_t=void*;
static bool administrator=true;static unsigned uid=0;static const char *process_name="resource-rehearsal";
enum{kIOClientPrivilegeAdministrator=1};
static Lock *IOLockAlloc(){return new Lock;}static void IOLockFree(Lock *p){delete p;}
static void proc_selfname(char *p,size_t n){strncpy(p,process_name,n-1);}
static void *kauth_cred_get(){return nullptr;}static unsigned kauth_cred_getuid(void*){return uid;}
struct IOUserClient {
 bool initWithTask(task_t,void*,UInt32){return true;}
 int clientHasPrivilege(void*,unsigned){return administrator?kIOReturnSuccess:kIOReturnNotPrivileged;}
};
"""
  prefix=ACCESS.replace('struct RadeonNIUserClient {',extra+"struct RadeonNIUserClient : IOUserClient {\n enum {kMaxAllocations=65536};task_t fTask;bool fProtocolV2;UInt32 fUvdHandleCount;\n bool initWithTask(task_t,void*,UInt32);\n")
  cases=r"""
int main(){
 {RadeonNIUserClient c;assert(c.initWithTask(nullptr,nullptr,RDN_UC_TYPE_V2));
  assert(c.fUvdAdministrator&&c.fSurfaceCompositor&&!c.fWindowServerClient);
  c.fCount=1;c.fOffsets[0]=4096;rdn_user_sleep_resource r{};size_t n=sizeof(r);
  assert(!c.methodSleepResource(1,50,4096,4096,&r,&n));
  IOFree(c.fOffsets,65536*4);IOLockFree(c.fAllocationLock);}
 {RadeonNIUserClient c;administrator=false;uid=88;process_name="WindowServer";
  assert(c.initWithTask(nullptr,nullptr,RDN_UC_TYPE_V2));assert(c.fWindowServerClient&&c.fSurfaceCompositor&&!c.fUvdAdministrator);
  c.fCount=1;c.fOffsets[0]=4096;rdn_user_sleep_resource r{};size_t n=sizeof(r);
  assert(c.methodSleepResource(1,50,4096,4096,&r,&n)==kIOReturnNotPrivileged);
  c.fUvdAdministrator=true;assert(c.methodSleepResource(1,50,4096,4096,&r,&n)==kIOReturnBadArgument);
  IOFree(c.fOffsets,65536*4);IOLockFree(c.fAllocationLock);}
}
"""
  self.run_harness(prefix,['bool RadeonNIUserClient::initWithTask(', 'IOReturn RadeonNIUserClient::methodSleepResource('],cases)
if __name__=='__main__':unittest.main()
