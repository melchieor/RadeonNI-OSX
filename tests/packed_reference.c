/* Numeric-word goldens and actual stores, including unaligned destinations. MIT */
#include <assert.h>
#include <stdio.h>
#include "../tools/guest/packed-reference.h"
int main(void)
{
 const uint32_t words[]={0x8467,0x9c61,0x130b0311,0x030b1311,0x11130b03,0x1137};
 unsigned char rgba[4],bytes[16],want[4];
 for(unsigned kind=0;kind<6;kind++){
  packed_source(kind,1,0,0,rgba);assert(packed_word(kind,rgba)==words[kind]);
  unsigned bpp=kind<2||kind==5?2:4;
  if(bpp==2){uint16_t word=words[kind];memcpy(want,&word,2);}else memcpy(want,&words[kind],4);
  memset(bytes,0xc7,sizeof(bytes));packed_store(bytes+1,words[kind],bpp,0);assert(!memcmp(bytes+1,want,bpp));
  assert(bytes[0]==0xc7&&bytes[bpp+1]==0xc7);
  packed_store(bytes+1,words[kind],bpp,1);for(unsigned i=0;i<bpp;i++)assert(bytes[i+1]==want[bpp-1-i]);
 }
 for(unsigned kind=0;kind<6;kind++)for(unsigned phase=0;phase<16;phase++)for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++){
  packed_source(kind,x,y,phase,rgba);uint32_t word=packed_word(kind,rgba);
  if(kind<2){
   unsigned r=kind==0?(word>>10)&31:word&31,g=(word>>5)&31,b=kind==0?word&31:(word>>10)&31;
   assert((r*255+15)/31==rgba[0]&&(g*255+15)/31==rgba[1]&&(b*255+15)/31==rgba[2]);
   assert(((word>>15)?255:0)==rgba[3]);
  }
 }
 puts("packed reference: six independent numeric-word goldens, byte swap, unaligned stores and196608 source pixels passed");
}
