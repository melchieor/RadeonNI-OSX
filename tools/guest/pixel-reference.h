/* Deterministic premultiplied glyph-like pixels; host-independent integer math. MIT */
#ifndef RDN_PIXEL_REFERENCE_H
#define RDN_PIXEL_REFERENCE_H
#include <stdint.h>
static inline void pixel_source(unsigned x,unsigned y,unsigned phase,unsigned char out[4])
{
 static const unsigned char glyph[8]={0x7e,0x40,0x40,0x7c,0x40,0x40,0x7e,0};
 unsigned gx=(x+phase)&7,gy=(y+phase/2)&7;
 unsigned a=(glyph[gy]&(0x80u>>gx))?85u*(1u+(x+y+phase)%3u):0;
 unsigned band=(x/8+y/8+phase)%3;
 out[0]=band==0?a:0;out[1]=band==1?a:0;out[2]=band==2?a:0;out[3]=a;
}
static inline void pixel_blend(const unsigned char src[4],int blend,unsigned char out[4])
{
 static const unsigned bg[3]={37,71,109};
 for(unsigned k=0;k<3;k++)out[k]=blend?src[k]+(bg[k]*(255u-src[3])+127u)/255u:src[k];
 out[3]=blend?255:src[3];
}
static inline uint32_t pixel_bgra_rev(const unsigned char rgba[4])
{
 return (uint32_t)rgba[2]|((uint32_t)rgba[1]<<8)|((uint32_t)rgba[0]<<16)|((uint32_t)rgba[3]<<24);
}
/* GetTexImage legacy base-format expansion differs from texture sampling.
   kind:0=RGB/RGBA,1=ALPHA,2=LUMINANCE,3=LUMINANCE_ALPHA. */
static inline void pixel_texture_readback(const unsigned char sampled[4],unsigned kind,unsigned char out[4])
{
 for(unsigned k=0;k<4;k++)out[k]=sampled[k];
 if(kind==1)out[0]=out[1]=out[2]=0;
 else if(kind==2||kind==3)out[1]=out[2]=0;
}
#endif
