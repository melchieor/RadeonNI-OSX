"""Execute the production power-registration body with captured fake PM states."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class SleepVetoTest(unittest.TestCase):
 def test_all_registered_states_veto_system_sleep(self):
  s=(ROOT/'kext/RadeonNI/RadeonNI.cpp').read_text();i=s.index('IOReturn RadeonNI::enableController(');body=s[i:s.index('\n}',i)+2]
  harness=r'''
#include <cassert>
#include <cstring>
using IOReturn=int;
enum{kIOReturnSuccess=0,kDepth32=2,kRdnPowerSleep=0,kRdnPowerIdle=1,kRdnPowerOn=2,kRdnPowerCount=3};
enum{kIOPMPreventSystemSleep=16,IOPMDeviceUsable=1,IOPMPowerOn=4};
struct IOPMPowerState{unsigned v,flags,in,out,a,b,c,d,e,f,g,h;};
struct RadeonNI{
 bool fModeSet=true,fPowerRegistered=false,supported=true;unsigned fPreferred=1,registrations=0;
 int programMode(unsigned,int){return 0;}
 int registerPowerDriver(RadeonNI*,IOPMPowerState *states,unsigned count){assert(count==3);for(unsigned i=0;i<count;i++)assert(states[i].flags&kIOPMPreventSystemSleep);++registrations;return 0;}
 void temporaryPowerClampOn(){}void changePowerStateTo(unsigned){}
 void setProperty(const char *key,bool value){assert(!strcmp(key,"SystemSleepSupported"));supported=value;}
 int enableController();
};
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(harness+body+'\nint main(){RadeonNI r;assert(!r.enableController()&&!r.supported&&r.registrations==1);assert(!r.enableController()&&r.registrations==1);}')
   subprocess.run(['c++','-std=c++11',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
