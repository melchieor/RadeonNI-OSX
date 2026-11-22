/* Independent golden values and padded/packed reference bounds. MIT */
#include <assert.h>
#include <string.h>
#include <stdio.h>
#include "../tools/guest/pixel-reference.h"
int main(void)
{
 unsigned char out[4],src[4]={0,0,0,0};pixel_blend(src,1,out);
 assert(out[0]==37&&out[1]==71&&out[2]==109&&out[3]==255);
 src[0]=src[3]=85;pixel_blend(src,1,out);assert(out[0]==110&&out[1]==47&&out[2]==73&&out[3]==255);
 src[0]=0;src[1]=src[3]=170;pixel_blend(src,1,out);assert(out[0]==12&&out[1]==194&&out[2]==36&&out[3]==255);
 src[1]=0;src[2]=src[3]=255;pixel_blend(src,1,out);assert(out[0]==0&&out[1]==0&&out[2]==255&&out[3]==255);
 pixel_blend(src,0,out);assert(!memcmp(src,out,4));
 unsigned char legacy[4]={23,23,23,85};
 pixel_texture_readback(legacy,0,out);assert(!memcmp(out,legacy,4));
 pixel_texture_readback(legacy,1,out);assert(out[0]==0&&out[1]==0&&out[2]==0&&out[3]==85);
 pixel_texture_readback(legacy,2,out);assert(out[0]==23&&out[1]==0&&out[2]==0&&out[3]==85);
 pixel_texture_readback(legacy,3,out);assert(out[0]==23&&out[1]==0&&out[2]==0&&out[3]==85);
 unsigned char sample[4]={1,2,3,4};assert(pixel_bgra_rev(sample)==0x04010203u);
 for(unsigned p=0;p<16;p++)for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++){
  pixel_source(x,y,p,src);assert(src[3]==0||src[3]==85||src[3]==170||src[3]==255);
  assert(src[0]<=src[3]&&src[1]<=src[3]&&src[2]<=src[3]);
  assert((unsigned)src[0]+src[1]+src[2]==src[3]);
  uint32_t packed=pixel_bgra_rev(src);assert((packed>>24)==src[3]&&((packed>>16)&255)==src[0]&&((packed>>8)&255)==src[1]&&(packed&255)==src[2]);
 }
 puts("reference: golden blend/packed values and 32768 premultiplied glyph pixels passed");
}
