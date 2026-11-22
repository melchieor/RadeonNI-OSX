"""Compile the actual hidden-index user-client guard with a fake accelerator."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PREFIX = r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
using UInt32=uint32_t;using UInt8=uint8_t;using IOByteCount=size_t;using IOReturn=int;
#define RDN_SLEEP_INDEX_WRITE 0x80000000u
enum {kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,
      kIOReturnNotPrivileged=3,kIOReturnBusy=4,kIOReturnNotReady=5};
struct Lock {bool held=false,busy=false;};
static bool IOLockTryLock(Lock *p){if(p->busy)return false;assert(!p->held);return p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
struct Accel {unsigned calls=0;bool wrote=false;int result=0;unsigned char data[16]{};
 int sleepIndexHidden(UInt32 off,void *out,bool wr,const unsigned char *restore=nullptr){assert(off>=0x10000000&&off<0x10001000&&out);++calls;wrote=wr||restore;if(restore)for(unsigned i=0;i<16;i++)data[i]=restore[i];return result;}};
struct RadeonNIUserClient {
 Lock lock,*fAllocationLock=&lock;bool fUvdAdministrator=false,fSurfaceGpuFailed=false;
 bool fWindowServerClient=false,fUvdUser=false;
 UInt32 offsets[2]={4096,0x10000000},*fOffsets=offsets,fCount=2;
 Accel accel,*fAccel=&accel;
 int methodSleepIndexHidden(UInt32,void *,IOByteCount *);
 int methodSleepIndexRestore(UInt32,UInt32,UInt32,UInt32,UInt32);
};
'''
CASES = r'''
int main(){RadeonNIUserClient c;char data[16];size_t n=16;
 assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnNotPrivileged);
 c.fUvdAdministrator=true;
 assert(c.methodSleepIndexHidden(0x10000004,data,&n)==kIOReturnBadArgument);
 assert(c.methodSleepIndexHidden(0x20000000,data,&n)==kIOReturnBadArgument);
 assert(c.accel.calls==0&&!c.lock.held);
 c.lock.busy=true;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnBusy);c.lock.busy=false;
 c.fWindowServerClient=true;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnBadArgument);c.fWindowServerClient=false;
 c.fUvdUser=true;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnBadArgument);c.fUvdUser=false;
 c.fSurfaceGpuFailed=true;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnBadArgument);c.fSurfaceGpuFailed=false;
 n=15;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnBadArgument);n=16;
 assert(!c.methodSleepIndexHidden(0x10000000,data,&n)&&n==16&&c.accel.calls==1&&!c.lock.held);
 assert(!c.accel.wrote);
 assert(!c.methodSleepIndexHidden(0x90000000,data,&n)&&c.accel.wrote&&c.accel.calls==2&&!c.lock.held);
 assert(!c.methodSleepIndexHidden(0x90000ff0,data,&n)&&c.accel.calls==3);
 assert(c.methodSleepIndexHidden(0x90001000,data,&n)==kIOReturnBadArgument&&c.accel.calls==3);
 c.accel.result=kIOReturnNotReady;assert(c.methodSleepIndexHidden(0x10000000,data,&n)==kIOReturnNotReady&&!c.lock.held);
}
'''
KERNEL = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
using UInt32=uint32_t;using UInt64=uint64_t;using IOReturn=int;
enum {kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,
 kIOReturnNotPrivileged=3,kIOReturnBusy=4,kIOReturnNotReady=5,kIOReturnIOError=6,
 RDN_FAMILY_CAYMAN=7,RDN_QUIESCE_RUNNING=0};
static int yes;static void *kOSBooleanTrue=&yes;
struct Lock{bool held=false,busy=false;};
static bool IOLockTryLock(Lock *p){if(p->busy)return false;assert(!p->held);return p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
struct Framebuffer {bool enabled=true,locked=false,busy=false;
 void *getProperty(const char*){return enabled?kOSBooleanTrue:nullptr;}
 bool tryPowerLock(){if(busy)return false;return locked=true;}
 void unlockPower(){assert(locked);locked=false;}};
struct Card{int family=RDN_FAMILY_CAYMAN;bool crtc_on=true;};
struct rdn_hang_regs{UInt32 cp_rptr;};
struct Mem{};
struct Accel {Card *card;UInt32 wptr=5,fence_emitted=9;};
static int isbusy=0,done=1,reads=0,readerror=0,writes=0,writeerror=0;static UInt32 size=4096;
static unsigned char stored[16];
static uint64_t rdn_mem_allocation_size(Mem*,UInt32){return size;}
static int rdn_cayman_hang_mask(Accel *a,rdn_hang_regs *r){r->cp_rptr=a->wptr;return isbusy;}
static bool rdn_fence_done(Accel*,UInt32){return done;}
static int rdn_vram_get(Card*,UInt32 off,void *out,UInt32 n){assert(off>=0x10000000&&off<0x10001000&&n==16);++reads;memcpy(out,stored,n);return readerror;}
static int rdn_vram_put(Card*,UInt32 off,const void *in,UInt32 n){assert(off>=0x10000000&&off<0x10001000&&n==16&&in);++writes;if(!writeerror)memcpy(stored,in,n);return writeerror;}
static void OSSynchronizeIO(){}
using UInt8=uint8_t;
struct RadeonNIAccel {
 Lock uvd,lock,*fUvdLock=&uvd,*fLock=&lock;Framebuffer fb,*fFramebuffer=&fb;
 bool fEngineUp=true,fRetiring=false,fSurfaceGpuStalled=false,fPowerFault=false;
 bool fFenceIRQEnabled=false,fHardwarePower=false,fIdleGovernor=false,fClockTuning=false;
 bool fVideoBusy=false,fUvdUp=false;struct{bool prepared=false;}fUvd;
 UInt32 fUvdUsers=0,fUvdLive=0,fHiddenSize=0x10000000,fHiddenOffset=0x10000000;
 struct{int phase=RDN_QUIESCE_RUNNING;}fQuiesce;
 Card card;Accel fAccel;Mem fHidden;
 RadeonNIAccel(){fAccel.card=&card;}
 int sleepIndexHidden(UInt32,void*,bool,const UInt8 * = nullptr);
 void clean(){assert(!uvd.held&&!lock.held&&!fb.locked);}
};
'''
KERNEL_CASES = r'''
int main(){RadeonNIAccel a;char bytes[16];
 assert(!a.sleepIndexHidden(0x10000000,bytes,false)&&reads==1);a.clean();
 assert(a.sleepIndexHidden(0x0ffff000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();
 size=0;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();size=4096;
 a.fb.enabled=false;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();a.fb.enabled=true;
 a.fVideoBusy=true;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();a.fVideoBusy=false;
 a.fFenceIRQEnabled=true;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();a.fFenceIRQEnabled=false;
 isbusy=1;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();isbusy=0;
 done=0;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnNotReady&&reads==1&&!writes);a.clean();done=1;
 a.fb.busy=true;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnBusy&&reads==1&&!writes);a.clean();a.fb.busy=false;
 assert(!a.sleepIndexHidden(0x10000000,bytes,true)&&reads==2&&writes==1);a.clean();
 assert(!a.sleepIndexHidden(0x10000ff0,bytes,true)&&reads==3&&writes==2);a.clean();
 writeerror=1;assert(a.sleepIndexHidden(0x10000000,bytes,true)==kIOReturnIOError&&reads==3&&writes==3);a.clean();writeerror=0;
 readerror=1;assert(a.sleepIndexHidden(0x10000000,bytes,false)==kIOReturnIOError&&reads==4);a.clean();
 readerror=0;UInt8 arbitrary[16]={0,1,2,3,4,5,6,7,8,9,10,11,12,13,14,255};
 assert(!a.sleepIndexHidden(0x10000000,bytes,false,arbitrary)&&!memcmp(bytes,arbitrary,16));a.clean();
}
'''
RESTORE_CASES = r'''
int main(){RadeonNIUserClient c;
 assert(c.methodSleepIndexRestore(0x10000000,0x00112233,0x44556677,0x8899aabb,0xccddeeff)==kIOReturnNotPrivileged);
 c.fUvdAdministrator=true;
 assert(c.methodSleepIndexRestore(0x90000000,0,0,0,0)==kIOReturnBadArgument);
 assert(c.methodSleepIndexRestore(0x10000001,0,0,0,0)==kIOReturnBadArgument);
 assert(c.methodSleepIndexRestore(0x20000000,0,0,0,0)==kIOReturnBadArgument);
 c.fUvdUser=true;assert(c.methodSleepIndexRestore(0x10000000,0,0,0,0)==kIOReturnBadArgument);c.fUvdUser=false;
 assert(!c.methodSleepIndexRestore(0x10000000,0x00112233,0x44556677,0x8899aabb,0xccddeeff));
 for(unsigned i=0;i<16;i++)assert(c.accel.data[i]==i*17);
 assert(!c.lock.held);
}
'''
class AccessTest(unittest.TestCase):
 def test_private_owned_page_and_privilege(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIUserClient::methodSleepIndexHidden(')
  function=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);(path/'probe.cpp').write_text(PREFIX+function+CASES)
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1',str(path/'probe.cpp'),'-o',str(path/'probe')],check=True)
   subprocess.run([str(path/'probe')],check=True)

 def test_gpu_idle_power_locks_and_hidden_bounds(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIAccel::sleepIndexHidden(')
  function=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);(path/'probe.cpp').write_text(KERNEL+function+KERNEL_CASES)
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1',str(path/'probe.cpp'),'-o',str(path/'probe')],check=True)
   subprocess.run([str(path/'probe')],check=True)

 def test_restore_ownership_and_byte_order(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIUserClient::methodSleepIndexRestore(')
  function=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   path=Path(d);(path/'probe.cpp').write_text(PREFIX+function+RESTORE_CASES)
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1',str(path/'probe.cpp'),'-o',str(path/'probe')],check=True)
   subprocess.run([str(path/'probe')],check=True)

if __name__=='__main__': unittest.main()
