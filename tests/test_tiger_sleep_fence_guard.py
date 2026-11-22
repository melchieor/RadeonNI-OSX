"""Exercise the real experimental fence wait across teardown and gate changes."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_client_cleanup import function

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include <cassert>
#include <cstdint>
#include <cstring>
using UInt32=uint32_t;using UInt64=uint64_t;using AbsoluteTime=uint64_t;
enum {kMillisecondScale=1,THREAD_UNINT=0};
static int held,reads,flushes,mode,wakeups;static bool *retiring;static UInt32 *gate;
void IOLockLock(int*){assert(!held);held=1;}void IOLockUnlock(int*){assert(held);held=0;}
void clock_interval_to_deadline(UInt32,int,UInt64 *out){*out=100;}
void clock_get_uptime(UInt64 *out){*out=1;}
void IOLockSleepDeadline(int*,UInt32*,AbsoluteTime,int){assert(held);if(mode==1)*retiring=true;else *gate=1;}
void IOLockWakeup(int*,UInt32*,bool){assert(held);++wakeups;}
void IOSleep(int){assert(!held);if(mode==1)*retiring=true;else *gate=1;}
bool rdn_fence_done(void*,UInt32){++reads;return false;}void rdn_hdp_flush(void*){++flushes;}
struct RadeonNIAccel {
 int lock=0,*fLock=&lock,fAccel=0;bool fEngineUp=true,fRetiring=false,fSurfaceGpuStalled=false,fFenceIRQEnabled=false;
 struct{UInt32 internal_hold=0;}fQuiesce;UInt32 fFenceEvents=0,fFenceFallbacks=0;
 bool fenceWait(UInt32,UInt32);void beginExperimentalRetirement();
};
'''
MAIN = r'''
int main(){for(int irq=0;irq<2;irq++)for(mode=1;mode<=2;mode++){
 RadeonNIAccel a;a.fFenceIRQEnabled=irq;retiring=&a.fRetiring;gate=&a.fQuiesce.internal_hold;reads=flushes=0;
 assert(!a.fenceWait(5,50) && reads==1 && !flushes && !held && !a.fFenceFallbacks);
} RadeonNIAccel a;retiring=&a.fRetiring;gate=&a.fQuiesce.internal_hold;reads=0;wakeups=0;
a.beginExperimentalRetirement();assert(a.fRetiring && wakeups==1 && !held);
assert(!a.fenceWait(5,50) && !reads && !held);}
'''


class FenceGuardTest(unittest.TestCase):
    def test_wait_does_not_touch_gpu_after_gate_or_retirement(self):
        source = (ROOT/'kext/RadeonNI/RadeonNIAccel.cpp').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'test.cpp').write_text(HARNESS + function(source, 'bool RadeonNIAccel::fenceWait(') +
                                        function(source, 'void RadeonNIAccel::beginExperimentalRetirement(') + MAIN)
            subprocess.run(['clang++', '-std=c++11', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-fsanitize=address,undefined', str(path/'test.cpp'), '-o', str(path/'test')], check=True)
            subprocess.run([str(path/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
