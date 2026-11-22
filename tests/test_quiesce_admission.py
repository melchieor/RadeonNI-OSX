"""Exercise the production CP admission function before any MMIO/power hook."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class AdmissionTest(unittest.TestCase):
 def test_gate_closes_before_mmio_and_power_callback(self):
  text=(ROOT/'hw/rdn_cp.c').read_text();start=text.index('int rdn_ring_begin(');body=text[start:text.index('\n}',start)+2]
  harness=r'''
#include <stdint.h>
#include <assert.h>
#define RDN_RING_ALIGN_MASK 15
#define RDN_USEC_TIMEOUT 5
#define ENOMEM 12
#define EBUSY 16
struct rdn_accel {uint32_t ring_words;const volatile uint32_t *submission_gate;int(*before_submit)(void*);void *submit_cookie;};
static unsigned reads,delays,powers,space=1023;
static uint32_t rdn_ring_free(struct rdn_accel*){++reads;return space;}
static void rdn_udelay(struct rdn_accel*,unsigned){++delays;}
static int power(void*){++powers;return 0;}
'''
  cases=r'''
int main(){volatile uint32_t phase=1;rdn_accel a{1024,&phase,power,nullptr};
 assert(rdn_ring_begin(&a,1)==-EBUSY && !reads && !powers);
 phase=2;assert(rdn_ring_begin(&a,1)==-EBUSY && !reads && !powers);
 phase=0;assert(!rdn_ring_begin(&a,1) && reads==1 && powers==1);
 a.submission_gate=nullptr;assert(!rdn_ring_begin(&a,1));
 space=0;assert(rdn_ring_begin(&a,1)==-EBUSY && delays==5);
}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.cpp').write_text(harness+body+cases)
   subprocess.run(['c++','-std=c++11','-Wall','-Wextra',str(p/'test.cpp'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
