"""Exercise actual upload-buffer filling with padded/packed/PBO-prefix layouts."""
from pathlib import Path
import subprocess,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1]
class PixelBuffers(unittest.TestCase):
 def test_guard_bytes_known_pixels_and_packed_words(self):
  s=(ROOT/'tools/guest/pixel-render-probe.c').read_text();i=s.index('static void fill_upload(');body=s[i:s.index('\n}',i)+2]
  prefix='''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include "pixel-reference.h"
#define TW 64
#define TH 32
static unsigned char upload[(TW+16)*(TH+4)*4+64];
'''
  cases='''
int main(void){
 fill_upload(0,80,3,2,0,64);
 unsigned start=64+(2*80+3)*4;
 assert(upload[start]==0&&upload[start+1]==0&&upload[start+2]==0&&upload[start+3]==0);
 assert(upload[start+4]==170&&upload[start+5]==0&&upload[start+6]==0&&upload[start+7]==170);
 for(unsigned i=0;i<sizeof(upload);i++){
  int active=0;
  if(i>=64){unsigned p=(i-64)/4,y=p/80,x=p%80;active=y>=2&&y<34&&x>=3&&x<67;}
  if(!active)assert(upload[i]==0xc7);
 }
 fill_upload(0,80,3,2,1,64);uint32_t word;memcpy(&word,upload+start+4,4);assert(word==0xaaaa0000u);
 for(unsigned phase=0;phase<16;phase++){
  fill_upload(phase,64,0,0,0,0);fill_upload(phase,80,3,2,0,0);fill_upload(phase,80,3,2,1,64);
 }
}
'''
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);(p/'test.c').write_text(prefix+body+cases)
   subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT/'tools/guest'),str(p/'test.c'),'-o',str(p/'test')],check=True)
   subprocess.run([str(p/'test')],check=True)
   for width,height in [(257,129),(1024,256)]:
    large_prefix=prefix.replace('#define TW 64', '#define TW %d'%width).replace('#define TH 32','#define TH %d'%height)
    large_cases='''
int main(void){
 for(unsigned phase=0;phase<16;phase++)for(unsigned packed=0;packed<2;packed++){
  fill_upload(phase,TW+16,3,2,packed,64);
  for(unsigned i=0;i<sizeof(upload);i++){
   unsigned p=i>=64?(i-64)/4:0,y=p/(TW+16),x=p%(TW+16);
   int active=i>=64&&y>=2&&y<TH+2&&x>=3&&x<TW+3;
   if(!active)assert(upload[i]==0xc7);
   else {unsigned char rgba[4];pixel_source(x-3,y-2,phase,rgba);
    if(packed){uint32_t w=pixel_bgra_rev(rgba);assert(upload[i]==((unsigned char*)&w)[(i-64)%4]);}
    else assert(upload[i]==rgba[(i-64)%4]);}
  }
 }
}
'''
    (p/'test.c').write_text(large_prefix+body+large_cases)
    subprocess.run(['cc','-std=c99','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I',str(ROOT/'tools/guest'),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)
if __name__=='__main__':unittest.main()
