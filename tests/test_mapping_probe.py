"""Exercise the real isolated mapping-probe control and cleanup path."""
from pathlib import Path
import subprocess
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <cassert>
#include <cstdint>
using UInt32=uint32_t;using IOReturn=int;
enum{kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,kIOReturnNotPrivileged=3,
 kIOReturnNotReady=4,kIOReturnBusy=5,kIOReturnIOError=6};
static void *kernel_task=(void*)1;static unsigned sleeps;
static void IOSleep(UInt32 ms){assert(ms==400);++sleeps;}
struct Lock{bool held=false;};static void IOLockLock(Lock *l){assert(!l->held);l->held=true;}
static void IOLockUnlock(Lock *l){assert(l->held);l->held=false;}
struct Memory{UInt32 value=0x73ac19e5u;bool null=false;int enters=0,leaves=0,enter_error=0,leave_error=0;
 void *getBytesNoCopy(){return null?nullptr:&value;}
 int redirect(void *task,bool enter){assert(task==kernel_task);if(enter){enters++;return enter_error;}leaves++;return leave_error;}};
struct Accel{bool reserved=false,active=false,allow=true,poisoned=false;unsigned releases=0;
 bool mappingProbeReserve(){if(!allow||reserved)return false;return reserved=true;}
 void mappingProbeActive(bool v){active=v;}void mappingProbePoison(){poisoned=true;}void mappingProbeRelease(){assert(reserved);reserved=false;++releases;}};
struct RadeonNIUserClient{Lock lock,*fAllocationLock=&lock;Accel accel,*fAccel=&accel;Memory mem,*fMappingProbeMemory=&mem;
 bool fUvdAdministrator=true,fProtocolV2=true,fWindowServerClient=false;
 int methodSleepMappingProbe(UInt32,UInt32*);};
'''
CASES=r'''
int main(){RadeonNIUserClient c;UInt32 out=99;
 assert(c.methodSleepMappingProbe(401,&out)==kIOReturnBadArgument&&!c.lock.held);
 c.fUvdAdministrator=false;assert(c.methodSleepMappingProbe(400,&out)==kIOReturnNotPrivileged);c.fUvdAdministrator=true;
 c.mem.null=true;assert(c.methodSleepMappingProbe(400,&out)==kIOReturnNotReady&&!c.lock.held);c.mem.null=false;
 c.accel.allow=false;assert(c.methodSleepMappingProbe(400,&out)==kIOReturnBusy&&!c.lock.held);c.accel.allow=true;
 assert(!c.methodSleepMappingProbe(400,&out)&&out==7&&c.mem.enters==1&&c.mem.leaves==1&&sleeps==1);
 assert(!c.accel.reserved&&!c.accel.active&&!c.lock.held);
 c.mem.enter_error=1;assert(c.methodSleepMappingProbe(400,&out)==kIOReturnIOError&&out==2&&c.mem.leaves==2);
 assert(!c.accel.reserved&&!c.accel.active&&!c.lock.held);c.mem.enter_error=0;
 c.mem.leave_error=1;assert(c.methodSleepMappingProbe(400,&out)==kIOReturnIOError&&out==5&&c.mem.leaves==3);
 assert(!c.accel.reserved&&!c.accel.active&&!c.lock.held&&c.accel.poisoned);
}
'''
UNIQUE_PREFIX=r'''
#include <cassert>
#include <cstdint>
using UInt32=uint32_t;using IOReturn=int;
enum{kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBadArgument=2,kIOReturnNotPrivileged=3,
 kIOReturnNotReady=4,kIOReturnBusy=5,kIOReturnIOError=6};
static unsigned sleeps;static void IOSleep(UInt32 ms){assert(ms==400);++sleeps;}
struct Lock{bool held=false;};static void IOLockLock(Lock *l){assert(!l->held);l->held=true;}
static void IOLockUnlock(Lock *l){assert(l->held);l->held=false;}
struct Memory{};
struct Map{Memory *backing;int enters=0,leaves=0,enter_error=0,leave_error=0;
 int redirect(Memory *m,int a,int b){assert(!a&&!b);if(!m){++enters;return enter_error;}assert(m==backing);++leaves;return leave_error;}};
struct Accel{bool reserved=false,active=false,allow=true,poisoned=false;
 bool mappingProbeReserve(){if(!allow||reserved)return false;return reserved=true;}
 void mappingProbeActive(bool v){active=v;}void mappingProbePoison(){poisoned=true;}
 void mappingProbeRelease(){assert(reserved);reserved=false;}};
struct RadeonNIUserClient{Lock lock,*fAllocationLock=&lock;Accel accel,*fAccel=&accel;Memory mem,*fMappingProbeMemory=&mem;
 Map map,*fMappingProbeUniqueMap=&map;UInt32 fMappingProbeMode=2;
 bool fUvdAdministrator=true,fProtocolV2=true,fWindowServerClient=false;
 RadeonNIUserClient(){map.backing=&mem;}
 int methodSleepMappingUniqueProbe(UInt32,UInt32*);};
'''
UNIQUE_CASES=r'''
int main(){RadeonNIUserClient c;UInt32 out=99;
 assert(c.methodSleepMappingUniqueProbe(401,&out)==kIOReturnBadArgument);
 c.fUvdAdministrator=false;assert(c.methodSleepMappingUniqueProbe(400,&out)==kIOReturnNotPrivileged);c.fUvdAdministrator=true;
 c.fMappingProbeMode=1;assert(c.methodSleepMappingUniqueProbe(400,&out)==kIOReturnNotReady);c.fMappingProbeMode=2;
 assert(!c.methodSleepMappingUniqueProbe(400,&out)&&out==3&&c.map.enters==1&&c.map.leaves==1&&sleeps==1);
 assert(!c.accel.reserved&&!c.accel.active&&!c.lock.held);
 c.map.enter_error=1;assert(c.methodSleepMappingUniqueProbe(400,&out)==kIOReturnIOError&&out==2&&c.map.leaves==2);
 c.map.enter_error=0;c.map.leave_error=1;assert(c.methodSleepMappingUniqueProbe(400,&out)==kIOReturnIOError&&out==1&&c.accel.poisoned);
 assert(!c.accel.reserved&&!c.accel.active&&!c.lock.held);
}
'''
class MappingProbe(unittest.TestCase):
 def test_control_failures_unredirect_and_unlock(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIUserClient::methodSleepMappingProbe(')
  fn=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(PREFIX+fn+CASES)
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
 def test_unique_mapping_cleanup(self):
  source=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
  start=source.index('IOReturn RadeonNIUserClient::methodSleepMappingUniqueProbe(')
  fn=source[start:source.index('\n}',start)+2]
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(UNIQUE_PREFIX+fn+UNIQUE_CASES)
   subprocess.run(['c++','-std=c++11','-DRDN_SLEEP_INDEX_PROBE=1',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
