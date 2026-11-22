"""Check the experimental framebuffer stop orders admission before cleanup."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_client_cleanup import function

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
#include <cassert>
struct IOService{};enum{kIOServiceSynchronous=1};
static int step,mark,fan,hot,retire,cleanup,superstop;
struct RadeonNIAccel{void beginExperimentalRetirement(){mark=++step;}void prepareToRetire(){++step;}
 void retire(IOService*){::retire=++step;}void release(){++step;}};
struct Head{void terminate(int){++step;}};struct Card{};unsigned rdn_crtc_count(Card*){return 1;}
struct Base{void stop(IOService*){superstop=++step;}};
#define super Base
#define IOLog(...) ((void)0)
struct RadeonNI:Base{RadeonNIAccel *fAccel;RadeonNI *fParent=nullptr;Head *fHeads[1]{};Card fCard;bool fMCFatal=false;
 void stopTemperatureFanControl(){fan=++step;}void stopHotplug(){hot=++step;}void cleanUp(){cleanup=++step;}
 void stop(IOService*);};
'''
MAIN = r'''
int main(){RadeonNIAccel accel;RadeonNI fb;IOService provider;fb.fAccel=&accel;fb.stop(&provider);
assert(mark && mark<fan && mark<hot && mark<retire && mark<superstop && mark<cleanup && !fb.fAccel);}
'''


class StopOrderTest(unittest.TestCase):
    def test_admission_closes_before_cleanup(self):
        source = (ROOT/'kext/RadeonNI/RadeonNI.cpp').read_text()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            (path/'test.cpp').write_text(HARNESS + function(source, 'void RadeonNI::stop(') + MAIN)
            subprocess.run(['clang++', '-std=c++11', '-DRDN_SLEEP_INTERNAL_EXPERIMENT=1',
                            '-fsanitize=address,undefined', str(path/'test.cpp'), '-o', str(path/'test')], check=True)
            subprocess.run([str(path/'test')], check=True)


if __name__ == '__main__':
    unittest.main()
