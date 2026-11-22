"""Run production maintenance callbacks against a held framebuffer lock."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include "rdn_user.h"
#include "rdn_fan.h"
using UInt8=uint8_t;using UInt16=uint16_t;using UInt32=uint32_t;using UInt64=uint64_t;
using SInt32=int32_t;using SInt64=int64_t;using IOReturn=int;using IOOptionBits=unsigned;using IOInterruptState=unsigned;
enum{kIOReturnSuccess=0,kIOReturnBusy=1,kIOReturnNotReady=2,kIOReturnIOError=3,kIOReturnBadArgument=4,kDepth8=0,kDepth32=2,kSetCLUTByValue=1};
#define IBNOTE(a,b) ((void)0)
#define IOLog(...) ((void)0)
struct Lock{bool held=false;};
static bool IOLockTryLock(Lock *p){if(p->held)return false;p->held=true;return true;}
static void IOLockLock(Lock *p){assert(!p->held);p->held=true;}
static void IOLockUnlock(Lock *p){assert(p->held);p->held=false;}
static void OSIncrementAtomic(volatile SInt32 *p){++*p;}
static IOInterruptState IOSimpleLockLockDisableInterrupt(Lock *p){IOLockLock(p);return 1;}
static void IOSimpleLockUnlockEnableInterrupt(Lock *p,IOInterruptState){IOLockUnlock(p);}
static Lock *device_lock;static unsigned device_access;
static void access(){assert(device_lock->held);++device_access;}
static bool rdn_output_connected(void*){access();return true;}
static int rdn_pm_temperature(void*){access();return 50000;}
static void rdn_pm_board_sensors(void*,rdn_user_board_sensors *b){access();memset(b,0,sizeof(*b));b->fan_rpm=3000;b->fan_min_rpm=700;}
static int rdn_pm_fan_percent(void*,unsigned){access();return 0;}
static int rdn_pm_fan_full(void*){access();return 0;}
static int rdn_pm_get_clocks(void*,uint32_t *a,uint32_t *b){access();*a=*b=100;return 0;}
static uint64_t now(void*){return 100;}
struct IOColorEntry{UInt16 index,red,green,blue;};
struct Entry{UInt16 red,green,blue;};
struct RadeonNI {
 Lock lock,cursor;Lock *fLock=&lock,*fCursorLock=&cursor;
 bool fParent=false,fCardReady=true,fRegMap=true,fMCFatal=false,fModeSet=true,fOutputRequested=true,fMultiHead=false,fConnected=true,fFanWriteFault=false,fCursorPaused=true;
 int fCard=0,fSenseSteady=0,fSenseLast=1;volatile UInt32 fFanPollExcluded=0,fHotplugPollExcluded=0;
 rdn_fan_policy fFanPolicy{};struct{void *cookie=nullptr;uint64_t(*time_ms)(void*)=now;}fOS;
 Entry fClut[256]{},fGamma[256]{};unsigned fCurrentDepth=kDepth32,color_loads=0;
 RadeonNI(){device_lock=&lock;device_access=0;}
 bool isInactive(){return false;}bool tryPowerLock(){return IOLockTryLock(fLock);}void unlockPower(){IOLockUnlock(fLock);}
 UInt32 readReg(UInt32 r){access();return r==0x740?0x640000:0;}
 template<class... A>void setProperty(A... ){}
 void monitorReturned(){access();}void notifyConnectionChange(){assert(!lock.held);}
 void loadColors(){access();++color_loads;}
 void pollTemperatureFan();void pollHotplug();void probeMaintenanceExclusion(rdn_user_sleep_maintenance*);
 IOReturn readBoardSensors(rdn_user_board_sensors*);IOReturn readTelemetry(bool,UInt32*,UInt32*,UInt32*);
 IOReturn setGammaTable(UInt32,UInt32,UInt32,void*);IOReturn setCLUTWithEntries(IOColorEntry*,UInt32,UInt32,IOOptionBits);
};
'''
CASES=r'''
int main(){RadeonNI a;rdn_user_sleep_maintenance m{};rdn_user_board_sensors b{};UInt32 t,c,r;
 IOLockLock(&a.lock);a.probeMaintenanceExclusion(&m);
 assert(m.cursor_excluded&&m.fan_excluded&&m.hotplug_excluded&&m.telemetry_excluded&&device_access==0&&a.lock.held);
 assert(a.readTelemetry(false,&t,&c,&r)==kIOReturnBusy&&device_access==0);
 IOLockUnlock(&a.lock);a.fCursorPaused=false;
 a.pollTemperatureFan();a.pollHotplug();assert(device_access>0&&!a.lock.held);
 assert(!a.readBoardSensors(&b)&&!a.lock.held);assert(!a.readTelemetry(true,&t,&c,&r)&&!a.lock.held);
 UInt8 gamma[256];for(unsigned i=0;i<256;i++)gamma[i]=i;
 assert(!a.setGammaTable(1,256,8,gamma)&&!a.lock.held&&a.color_loads==1&&a.fGamma[255].red==1020);
 assert(a.setGammaTable(1,0,8,gamma)==kIOReturnBadArgument&&!a.lock.held);
 a.fCurrentDepth=kDepth8;IOColorEntry color{7,65535,0,32768};
 assert(!a.setCLUTWithEntries(&color,0,1,kSetCLUTByValue)&&!a.lock.held&&a.color_loads==2&&a.fClut[7].red==1023);
 for(unsigned i=0;i<1000;i++){IOLockLock(&a.lock);a.fCursorPaused=true;unsigned n=device_access;
  a.probeMaintenanceExclusion(&m);assert(m.fan_excluded&&m.hotplug_excluded&&m.telemetry_excluded&&device_access==n);
  IOLockUnlock(&a.lock);a.fCursorPaused=false;}
}
'''
class MaintenancePaths(unittest.TestCase):
 def test_callbacks_excluded_without_mmio_and_resume_under_lock(self):
  s=(ROOT/'kext/RadeonNI/RadeonNI.cpp').read_text();b=[]
  for kind,n in [('void','pollTemperatureFan'),('void','pollHotplug'),('void','probeMaintenanceExclusion'),('IOReturn','readBoardSensors'),('IOReturn','readTelemetry'),('IOReturn','setGammaTable'),('IOReturn','setCLUTWithEntries')]:
   i=s.index(kind+' RadeonNI::'+n+'(');b.append(s[i:s.index('\n}',i)+2])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(PREFIX+'\n'.join(b)+CASES)
   subprocess.run(['c++','-std=c++11','-I',str(ROOT/'hw'),str(p/'test.cpp'),'-x','c++',str(ROOT/'hw/rdn_fan.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
