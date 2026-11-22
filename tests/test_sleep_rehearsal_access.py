"""Check the production diagnostic wrapper's privilege and ABI boundaries."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class AccessTest(unittest.TestCase):
 def test_status_is_readonly_run_is_admin_and_sizes_checked(self):
  self.check_wrapper(False)
  self.check_wrapper(True)
 def check_wrapper(self,maintenance):
  text=(ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text();i=text.index('IOReturn RadeonNIUserClient::methodSleep'+('Maintenance' if maintenance else 'Rehearsal')+'(');body=text[i:text.index('\n}',i)+2]
  harness=r'''
#include <cassert>
#include <cstddef>
#include "rdn_user.h"
using UInt32=uint32_t;using IOByteCount=size_t;using IOReturn=int;
enum{kIOReturnSuccess=0,kIOReturnBadArgument=1,kIOReturnNotPrivileged=2};
struct Accel{int calls=0;int sleepRehearsal(UInt32,UInt32,rdn_user_sleep_rehearsal*){++calls;return 0;}};
struct RadeonNIUserClient{bool fUvdAdministrator=false;Accel accel,*fAccel=&accel;
 int methodSleepRehearsal(UInt32,UInt32,rdn_user_sleep_rehearsal*,IOByteCount*);};
'''
  cases=r'''
int main(){RadeonNIUserClient c;rdn_user_sleep_rehearsal r{};size_t n=sizeof(r);
 assert(!c.methodSleepRehearsal(0,0,&r,&n)&&c.accel.calls==1);
 assert(c.methodSleepRehearsal(1,50,&r,&n)==kIOReturnNotPrivileged&&c.accel.calls==1);
 c.fUvdAdministrator=true;assert(!c.methodSleepRehearsal(1,50,&r,&n)&&c.accel.calls==2);
 assert(c.methodSleepRehearsal(2,50,&r,&n)==kIOReturnBadArgument&&c.accel.calls==2);
 --n;assert(c.methodSleepRehearsal(1,50,&r,&n)==kIOReturnBadArgument&&c.accel.calls==2);
 assert(c.methodSleepRehearsal(0,0,nullptr,&n)==kIOReturnBadArgument);
 static_assert(sizeof(r)==92,"fixed PPC report layout");
}
'''
  if maintenance:
   harness=harness.replace('rdn_user_sleep_rehearsal*)','rdn_user_sleep_rehearsal*,rdn_user_sleep_maintenance*)').replace('methodSleepRehearsal','methodSleepMaintenance').replace('rdn_user_sleep_rehearsal*,IOByteCount*','rdn_user_sleep_maintenance*,IOByteCount*')
   cases=cases.replace('methodSleepRehearsal','methodSleepMaintenance').replace('rdn_user_sleep_rehearsal r','rdn_user_sleep_maintenance r').replace('sizeof(r)==92','sizeof(r)==128')
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(harness+body+cases)
   subprocess.run(['c++','-std=c++11','-I',str(ROOT/'hw'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
