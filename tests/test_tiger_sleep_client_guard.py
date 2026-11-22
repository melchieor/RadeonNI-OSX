"""Exercise the real experimental client-release guards with fake GPU calls."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_client_cleanup import function

ROOT = Path(__file__).resolve().parents[1]

PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstdlib>
using UInt32=uint32_t; using IOReturn=int;
enum {kIOReturnBusy=1,kIOReturnTimeout=2,kIOReturnBadArgument=3,kIOReturnSuccess=0,kIOReturnNotReady=4,RDN_GART_PAGE_SIZE=4096};
static int locks,gpu_calls,freed;
void IOLockLock(int*){assert(!locks);++locks;} void IOLockUnlock(int*){assert(locks);--locks;}
void *IOMalloc(unsigned n){return malloc(n);} void IOFree(void *p,unsigned){free(p);} void IOLog(const char*,...){}
struct Memory {void complete(){} void release(){}};
using IOMemoryDescriptor=Memory;
struct RadeonNIAccel {
 enum {kMaxGartBindings=1,kSurfaceMirrors=1};int lock=0,*fLock=&lock;
 bool fSurfaceGpuStalled=false,fRetiring=false;struct {UInt32 internal_hold=1;} fQuiesce;
 struct Binding {Memory *memory=nullptr;void *owner=nullptr;UInt32 offset=0,size=4096,vram=0;} fGartBound[1];
 struct Mirror {void *surface=nullptr;UInt32 offset=0;} fSurfaceMirrors[1];
 struct RetiredVram {UInt32 offset,fence;RetiredVram *next;};RetiredVram *fRetiredVram=nullptr;
 struct {UInt32 fence_emitted=0;} fAccel;int fGart=0,fGartSpace=0;
 void setProperty(const char*,bool){} void *heapForOffset(UInt32){return nullptr;} void reapRetiredVram();
 IOReturn gartUnbind(UInt32,void*);void freeVram(UInt32);
};
bool kOSBooleanTrue=true;
void rdn_gart_clear_page(int*,UInt32){++gpu_calls;} int rdn_gart_flush_checked(int*){++gpu_calls;return 0;}
void rdn_mem_free(void*,UInt32){++freed;} bool rdn_fence_done(void*,UInt32){++gpu_calls;return true;}
'''
SUFFIX = r'''
int main(){RadeonNIAccel a;Memory m;int owner=0;a.fGartBound[0].memory=&m;a.fGartBound[0].owner=&owner;
 a.fGartBound[0].offset=4096;a.fSurfaceMirrors[0].surface=&owner;a.fSurfaceMirrors[0].offset=4096;
 assert(a.gartUnbind(4096,&owner)==kIOReturnBusy && !gpu_calls && !freed && a.fGartBound[0].memory==&m && !a.fGartBound[0].owner);
 a.freeVram(4096);assert(!gpu_calls && !freed && a.fSurfaceMirrors[0].surface==&owner && !locks);
 RadeonNIAccel::RetiredVram retired={8192,1,nullptr};a.fRetiredVram=&retired;
 a.reapRetiredVram();assert(a.fRetiredVram==&retired && !gpu_calls && !freed);
 a.fQuiesce.internal_hold=0;a.fRetiring=true;a.fGartBound[0].owner=&owner;
 assert(a.gartUnbind(4096,&owner)==kIOReturnBusy && !gpu_calls && !freed && a.fGartBound[0].memory==&m);
 a.freeVram(4096);a.reapRetiredVram();assert(!gpu_calls && !freed && a.fRetiredVram==&retired);
}
'''


class ClientGuardTest(unittest.TestCase):
    def test_real_release_methods_retain_without_mmio(self):
        source = (ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
        methods = '\n'.join(function(source, sig) for sig in
                            ('IOReturn RadeonNIAccel::gartUnbind(', 'void RadeonNIAccel::freeVram(',
                             'void RadeonNIAccel::reapRetiredVram('))
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'test.cpp').write_text(PREFIX + methods + SUFFIX)
            subprocess.run(['clang++', '-std=c++11', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-fsanitize=address,undefined', str(path/'test.cpp'), '-o', str(path/'test')], check=True)
            subprocess.run([str(path/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
