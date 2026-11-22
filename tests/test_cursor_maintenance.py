"""Exercise production cursor callbacks and pause/replay with guarded fake MMIO."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
PREFIX=r'''
#include <cassert>
#include <cstdint>
#include <cstring>
#include <algorithm>
#include "rdn_user.h"
using UInt32=uint32_t;using UInt8=uint8_t;using SInt32=int32_t;
using IOReturn=int;using IOInterruptState=unsigned;
enum {RDN_CURSOR_SIZE=64,kIOReturnSuccess=0,kIOReturnUnsupported=1,kIOReturnBusy=2};
enum {kHardwareCursorDescriptorMajorVersion=1,kHardwareCursorDescriptorMinorVersion=0,kHardwareCursorInfoMajorVersion=1,kHardwareCursorInfoMinorVersion=0};
#define IBNOTE(a,b) ((void)0)
#define IOLog(...) ((void)0)
static void OSSynchronizeIO(){}
static UInt32 OSSwapHostToLittleInt32(UInt32 n){return __builtin_bswap32(n);}
struct IOSimpleLock{bool held=false;};
static IOInterruptState IOSimpleLockLockDisableInterrupt(IOSimpleLock *p){assert(!p->held);p->held=true;return 1;}
static void IOSimpleLockUnlockEnableInterrupt(IOSimpleLock *p,IOInterruptState irq){assert(p->held&&irq==1);p->held=false;}
struct IOHardwareCursorDescriptor{unsigned majorVersion,minorVersion,height,width,bitDepth;};
struct IOHardwareCursorInfo{unsigned majorVersion,minorVersion,cursorWidth,cursorHeight;UInt8 *hardwareCursorData;};
static bool *paused,*held;static unsigned writes;static int last_x,last_y;static bool last_visible;
static void rdn_cursor_set(void*,unsigned,int x,int y,bool v){assert(!*paused&&*held);++writes;last_x=x;last_y=y;last_visible=v;}
struct RadeonNI {
 IOSimpleLock guard,*fCursorLock=&guard;
 bool fHWCursor=true,fCursorLoaded=false,fCursorVisible=false,fCursorLogged=false;
 bool fCursorPaused=false,fCursorImagePending=false,fCursorConverting=false,fCursorHidePending=false;
 UInt32 fCursorDeferred=0,fCursorOffset=0;SInt32 fCursorX=0,fCursorY=0;
 UInt32 fCursorData[4096]{},fCursorUpload[4096]{},vram[4096]{};int fCard=0;
 bool fParent=false,fMultiHead=false,fModeSet=true,fOutputOn=true,fFanTimer=true,fMCFatal=false;
 bool conversion_ok=true;unsigned width=2,height=2,pattern=0x11223344;
 RadeonNI(){paused=&fCursorPaused;held=&guard.held;writes=0;}
 void *aperture(){return vram;}
 bool convertCursorImage(void*,IOHardwareCursorDescriptor*,IOHardwareCursorInfo *i){
  assert(!guard.held);i->cursorWidth=width;i->cursorHeight=height;
  std::fill(fCursorData,fCursorData+4096,pattern);return conversion_ok;
 }
 IOReturn setCursorImage(void*);IOReturn setCursorState(SInt32,SInt32,bool);
 void commitCursorLocked();bool beginMaintenanceRehearsal();
 void endMaintenanceRehearsal(rdn_user_sleep_maintenance*);
};
'''
CASES=r'''
int main(){rdn_user_sleep_maintenance report{};
 {RadeonNI a;assert(!a.setCursorState(4,5,true)&&writes==0);
  assert(!a.setCursorImage(nullptr)&&writes==1&&last_visible&&a.vram[0]==0x44332211&&a.vram[2]==0);
  assert(a.beginMaintenanceRehearsal());unsigned old_writes=writes;UInt32 old_pixel=a.vram[0];
  assert(!a.beginMaintenanceRehearsal());
  a.pattern=0x55667788;assert(!a.setCursorImage(nullptr));assert(!a.setCursorState(-8,42,true));
  assert(writes==old_writes&&a.vram[0]==old_pixel&&a.fCursorDeferred==2&&a.fCursorImagePending);
  a.endMaintenanceRehearsal(&report);
  assert(!a.fCursorPaused&&report.cursor_resumed&&report.cursor_deferred==2);
  assert(writes==old_writes+1&&last_x==-8&&last_y==42&&last_visible&&a.vram[0]==0x88776655);
  assert(!a.fCursorImagePending&&!a.guard.held);
 }
 {RadeonNI a;assert(!a.setCursorImage(nullptr));assert(a.beginMaintenanceRehearsal());unsigned n=writes;
  a.conversion_ok=false;assert(a.setCursorImage(nullptr)==kIOReturnUnsupported&&writes==n);
  a.endMaintenanceRehearsal(&report);assert(writes==n+1&&!last_visible&&!a.fCursorHidePending&&!a.guard.held);
 }
 {RadeonNI a;a.width=65;assert(a.setCursorImage(nullptr)==kIOReturnUnsupported&&!a.fCursorConverting&&!a.guard.held&&writes==0);}
 {RadeonNI a;a.fCursorConverting=true;assert(a.setCursorImage(nullptr)==kIOReturnBusy&&!a.guard.held&&writes==0);}
 {RadeonNI a;a.fMultiHead=true;assert(!a.beginMaintenanceRehearsal()&&!a.fCursorPaused&&!a.guard.held);}
 {RadeonNI a;a.fOutputOn=false;assert(!a.beginMaintenanceRehearsal()&&!a.fCursorPaused&&!a.guard.held);}
 {RadeonNI a;assert(!a.setCursorImage(nullptr));for(unsigned i=0;i<1000;i++){
  assert(a.beginMaintenanceRehearsal());assert(!a.setCursorState(i,i+1,i&1));
  a.endMaintenanceRehearsal(&report);assert(!a.guard.held&&!a.fCursorPaused&&last_x==(int)i&&last_y==(int)i+1);
 }}
}
'''
class CursorMaintenanceTest(unittest.TestCase):
 def test_no_device_access_while_paused_latest_image_and_position_replayed(self):
  source=(ROOT/'kext/RadeonNI/RadeonNI.cpp').read_text();bodies=[]
  for kind,name in [('IOReturn','setCursorImage'),('IOReturn','setCursorState'),('void','commitCursorLocked'),('bool','beginMaintenanceRehearsal'),('void','endMaintenanceRehearsal')]:
   start=source.index(kind+' RadeonNI::'+name+'(');bodies.append(source[start:source.index('\n}',start)+2])
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(PREFIX+'\n'.join(bodies)+CASES)
   subprocess.run(['c++','-std=c++11','-I',str(ROOT/'hw'),str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
