"""Exercise the production power-retained routine with fake locks and GPU state."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include "rdn_user.h"
#include "rdn_quiesce.h"
using UInt32=uint32_t;using UInt64=uint64_t;using IOReturn=int;
enum {kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNotReady=2,kIOReturnBusy=3,kIOReturnUnsupported=4,EBUSY=16,RDN_FAMILY_CAYMAN=1};
static int truth;static void *kOSBooleanTrue=&truth;
struct Lock{bool held=false,busy=false;};
static bool IOLockTryLock(Lock *p){if(p->busy)return false;assert(!p->held);return p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
static unsigned tick_ms=1;static bool frozen_clock;static UInt64 clock_ms;static bool busy_gpu,mutate,backwards,broken_gate;
static UInt64 now(void*){return backwards?--clock_ms:clock_ms;}
static void IOSleep(unsigned n){if(!frozen_clock)clock_ms+=n*tick_ms;}
static void rdnStoreBarrier(){}
struct os{void *cookie=nullptr;UInt64(*time_ms)(void*)=now;};
struct card{int family=RDN_FAMILY_CAYMAN;os *os;bool crtc_on=true;};
struct rdn_accel{card *card;UInt32 fence_emitted=7,wptr=32;const volatile UInt32 *submission_gate;};
struct rdn_hang_regs{UInt32 cp_rptr;};
static unsigned rdn_cayman_hang_mask(rdn_accel *a,rdn_hang_regs *r){r->cp_rptr=a->wptr;if(mutate)++a->fence_emitted;return busy_gpu?1:0;}
static bool rdn_fence_done(rdn_accel*,UInt32){return !busy_gpu;}
static int rdn_ring_begin(rdn_accel *a,unsigned){return broken_gate?0:((a->submission_gate&&*a->submission_gate)?-EBUSY:0);}
struct Framebuffer{
 Lock lock;bool enabled=true,fan_fail=false,pause_fail=false,paused=false,probe_fail=false;
 unsigned fan_calls=0,resumes=0;
 bool beginMaintenanceRehearsal(){assert(lock.held);return pause_fail?false:(paused=true);}
 void probeMaintenanceExclusion(rdn_user_sleep_maintenance *r){assert(lock.held&&paused);r->cursor_excluded=r->fan_excluded=r->hotplug_excluded=r->telemetry_excluded=!probe_fail;}
 void endMaintenanceRehearsal(rdn_user_sleep_maintenance *r){assert(lock.held&&paused);paused=false;++resumes;r->cursor_resumed=1;}

 void *getProperty(const char*){return enabled?kOSBooleanTrue:nullptr;}
 bool tryPowerLock(){return IOLockTryLock(&lock);}void unlockPower(){IOLockUnlock(&lock);}
 int prepareRehearsalFan(){++fan_calls;return fan_fail?1:0;}
};
struct RadeonNIAccel{
 Lock lock,uvd;Lock *fLock=&lock,*fUvdLock=&uvd;Framebuffer fb,*fFramebuffer=&fb;
 os platform;card device;rdn_accel fAccel;rdn_quiesce fQuiesce;rdn_user_sleep_rehearsal fSleepReport{};rdn_user_sleep_maintenance fMaintenanceReport{};rdn_user_sleep_resource fResourceReport{};
 bool inventory_ok=true,allocation_ok=true,snapshot_ok=true;unsigned snapshots=0;
 bool resourceInventory(rdn_user_sleep_resource *r){r->inventory_valid=inventory_ok;return inventory_ok;}
 bool resourceAllocationValid(UInt32){return allocation_ok;}
 bool resourceSnapshot(rdn_user_sleep_resource *,void*){++snapshots;return snapshot_ok;}
 bool fEngineUp=true,fRetiring=false,fSurfaceGpuStalled=false,fPowerFault=false;
 void *fHardwarePower=nullptr;bool fIdleGovernor=false,fClockTuning=false,fFenceIRQEnabled=false,fVideoBusy=false;
 bool fUvdUp=false;struct{bool prepared=false;}fUvd;unsigned fUvdUsers=0,fUvdLive=0;
 RadeonNIAccel(){clock_ms=100;tick_ms=1;frozen_clock=busy_gpu=mutate=backwards=broken_gate=false;device.os=&platform;fAccel.card=&device;rdn_quiesce_init(&fQuiesce);fAccel.submission_gate=&fQuiesce.phase;}
 IOReturn sleepRehearsal(UInt32,UInt32,rdn_user_sleep_rehearsal*,rdn_user_sleep_maintenance* = nullptr,rdn_user_sleep_resource* = nullptr,void* = nullptr);
 void clean(){assert(!lock.held&&!uvd.held&&!fb.lock.held&&!fb.paused&&!fQuiesce.phase);}
};
'''
CASES=r'''
int main(){rdn_user_sleep_rehearsal r{};rdn_user_sleep_maintenance m{};
 {RadeonNIAccel a;assert(!a.sleepRehearsal(0,0,&r));assert(!a.fb.fan_calls&&!r.sleep_supported&&!r.full_mmio_gated);a.clean();}
 {RadeonNIAccel a;assert(!a.sleepRehearsal(1,50,&r));assert(!r.result&&r.held_witness&&r.gate_verified&&r.queue_state_unchanged&&r.fan_full_requested);a.clean();}
 {RadeonNIAccel a;a.uvd.busy=true;assert(a.sleepRehearsal(1,50,&r)==kIOReturnBusy);a.clean();}
 {RadeonNIAccel a;a.lock.busy=true;assert(a.sleepRehearsal(1,50,&r)==kIOReturnBusy);a.clean();}
 {RadeonNIAccel a;a.fb.lock.busy=true;assert(a.sleepRehearsal(1,50,&r)==kIOReturnBusy);a.clean();}
 {RadeonNIAccel a;a.fb.enabled=false;assert(a.sleepRehearsal(1,50,&r)==kIOReturnUnsupported);a.clean();}
 {RadeonNIAccel a;a.fVideoBusy=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_UNSAFE&&!a.fb.fan_calls);a.clean();}
 {RadeonNIAccel a;a.fb.fan_fail=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_UNSAFE&&!r.fan_full_requested);a.clean();}
 {RadeonNIAccel a;busy_gpu=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_TIMEOUT&&!r.held_witness);a.clean();}
 {RadeonNIAccel a;backwards=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_CLOCK);a.clean();}
 {RadeonNIAccel a;mutate=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_INVARIANT&&!r.queue_state_unchanged);a.clean();}
 {RadeonNIAccel a;broken_gate=true;assert(!a.sleepRehearsal(1,50,&r)&&r.result==RDN_QUIESCE_INVARIANT);a.clean();}

 {RadeonNIAccel a;assert(!a.sleepRehearsal(0,0,&m.base,&m));assert(m.version==1&&m.size==128&&!a.fb.fan_calls&&!a.fb.paused);a.clean();}
 {RadeonNIAccel a;assert(!a.sleepRehearsal(1,50,&m.base,&m));assert(!m.base.result&&m.base.held_witness&&m.cursor_excluded&&m.cursor_resumed&&m.fan_excluded&&m.hotplug_excluded&&m.telemetry_excluded&&m.hold_ms==20&&a.fb.resumes==1);a.clean();}
 {RadeonNIAccel a;a.fb.pause_fail=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_UNSAFE&&!a.fb.fan_calls&&!a.fb.resumes);a.clean();}
 {RadeonNIAccel a;a.fb.fan_fail=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_UNSAFE&&a.fb.resumes==1);a.clean();}
 {RadeonNIAccel a;busy_gpu=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_TIMEOUT&&a.fb.resumes==1);a.clean();}
 {RadeonNIAccel a;a.fb.probe_fail=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_INVARIANT&&!m.hold_ms&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;assert(!a.sleepRehearsal(1,5,&m.base,&m)&&m.base.result==RDN_QUIESCE_TIMEOUT&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;backwards=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_CLOCK&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;frozen_clock=true;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_CLOCK&&!m.hold_ms&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;tick_ms=10;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&!m.base.result&&m.hold_ms==20&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;tick_ms=100;assert(!a.sleepRehearsal(1,50,&m.base,&m)&&m.base.result==RDN_QUIESCE_TIMEOUT&&m.cursor_resumed);a.clean();}
 {RadeonNIAccel a;rdn_user_sleep_resource z{};z.owned_bytes=4096;z.private_connection=1;
  assert(!a.sleepRehearsal(1,50,&z.maintenance.base,&z.maintenance,&z,&z)&&!z.maintenance.base.result&&a.snapshots==1);a.clean();}
 {RadeonNIAccel a;rdn_user_sleep_resource z{};z.owned_bytes=4096;z.private_connection=1;a.snapshot_ok=false;
  assert(!a.sleepRehearsal(1,50,&z.maintenance.base,&z.maintenance,&z,&z)&&z.maintenance.base.result==RDN_QUIESCE_INVARIANT&&a.snapshots==1);a.clean();}
 {RadeonNIAccel a;rdn_user_sleep_resource z{};z.owned_bytes=4096;z.private_connection=1;a.allocation_ok=false;
  assert(!a.sleepRehearsal(1,50,&z.maintenance.base,&z.maintenance,&z,&z)&&z.maintenance.base.result==RDN_QUIESCE_UNSAFE&&!a.snapshots);a.clean();}
 {RadeonNIAccel a;rdn_user_sleep_resource z{};assert(!a.sleepRehearsal(0,0,&z.maintenance.base,&z.maintenance,&z)&&z.version==1&&z.size==224&&z.inventory_valid&&!a.snapshots);a.clean();}
}
'''
class QuiesceDriverTest(unittest.TestCase):
 def test_all_return_paths_reopen_and_unlock(self):
  s=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text();i=s.index('IOReturn RadeonNIAccel::sleepRehearsal(');body=s[i:s.index('\n}',i)+2]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(PREFIX+body+CASES)
   subprocess.run(['c++','-std=c++11','-I',str(ROOT/'hw'),str(p/'test.cpp'),'-x','c++',str(ROOT/'hw/rdn_quiesce.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
