"""Run actual packed-fill code under ASan/UBSan with atlas/glyph layouts."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class PackedBuffers(unittest.TestCase):
 def test_bounds_prefix_skips_padding_and_swap(self):
  source=(ROOT/'tools/guest/packed-upload-cases.h').read_text();i=source.index('static void packed_fill(');body=source[i:source.index('\nstatic int packed_transfer',i)]
  prefix='''#include <assert.h>
#include <string.h>
#include "packed-reference.h"
#define TW 320
#define TH 320
static unsigned char upload[(TW+16)*(TH+4)*4+64];
'''
  main='''
int main(void){
 for(unsigned kind=0;kind<6;kind++)for(unsigned layout=0;layout<4;layout++)for(unsigned sub=0;sub<2;sub++){
  unsigned bpp=kind<2||kind==5?2:4,w=sub?(layout==1?3:layout==2?14:8):TW,h=sub?(layout==2?16:10):TH;
  unsigned row=w*bpp,sx=0,sy=0,prefix=layout==1?1:layout==3?64:0;
  if(layout==1)row=(w*bpp+3)&~3u;
  if(layout==2){row=(w+8)*bpp;sx=3;sy=2;}
  if(layout==3){row=w*bpp+17;sx=3;sy=2;}
  assert(prefix+(h-1+sy)*row+(w+sx)*bpp<=sizeof(upload));
  packed_fill(kind,0,w,h,row,sx,sy,prefix,layout==2);
  for(unsigned i=0;i<sizeof(upload);i++){
   int active=0;
   if(i>=prefix){unsigned y=(i-prefix)/row,byte=(i-prefix)%row;
    active=y>=sy&&y<h+sy&&byte>=sx*bpp&&byte<(w+sx)*bpp;}
   if(!active)assert(upload[i]==0xc7);
  }
  const uint32_t gold[]={0x8467,0x9c61,0x130b0311,0x030b1311,0x11130b03,0x1137};
  unsigned char want[4];if(bpp==2){uint16_t word=gold[kind];memcpy(want,&word,2);}else memcpy(want,&gold[kind],4);
  unsigned start=prefix+sy*row+(sx+1)*bpp;
  for(unsigned k=0;k<bpp;k++)assert(upload[start+k]==want[layout==2?bpp-1-k:k]);
 }
}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(prefix+body+main)
   subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'tools/guest'),str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
