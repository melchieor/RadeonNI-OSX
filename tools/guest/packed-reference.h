/* Packed texel reference: numeric GL words, independent of host byte order.
   MIT, kouta-kun and Claude. */
#ifndef RDN_PACKED_REFERENCE_H
#define RDN_PACKED_REFERENCE_H
#include <stdint.h>
#include <string.h>
static inline void packed_source(unsigned kind,unsigned x,unsigned y,unsigned phase,unsigned char rgba[4])
{
 unsigned r=x+phase,g=3*x+5*y+phase,b=7*x+2*y+phase;
 if(kind<2){rgba[0]=((r&31)*255+15)/31;rgba[1]=((g&31)*255+15)/31;rgba[2]=((b&31)*255+15)/31;rgba[3]=((x^y^phase)&1)?255:0;}
 else if(kind==5){rgba[0]=(r&15)*17;rgba[1]=(g&15)*17;rgba[2]=(b&15)*17;rgba[3]=((x+y+phase)&15)*17;}
 else {
  /* Asymmetric edge-bit values, short spatial period keeps result ZIP small. */
  static const unsigned char levels[16]={0,19,11,3,17,1,7,15,31,63,127,128,129,171,254,255};
  rgba[0]=levels[(x+5*y+13*phase)&15];rgba[1]=levels[(2*x+7*y+3*phase)&15];
  rgba[2]=levels[(3*x+11*y+5*phase)&15];rgba[3]=levels[(4*x+y+7*phase)&15];
 }
}
static inline uint32_t packed_word(unsigned kind,const unsigned char p[4])
{
 if(kind<2){unsigned r=(p[0]*31+127)/255,g=(p[1]*31+127)/255,b=(p[2]*31+127)/255;
  return (p[3]?0x8000:0)|(g<<5)|(kind==0?(r<<10)|b:(b<<10)|r);}
 if(kind==2)return ((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];
 if(kind==3)return ((uint32_t)p[2]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[0]<<8)|p[3];
 if(kind==4)return ((uint32_t)p[3]<<24)|((uint32_t)p[0]<<16)|((uint32_t)p[1]<<8)|p[2];
 return ((p[3]/17)<<12)|((p[0]/17)<<8)|((p[1]/17)<<4)|(p[2]/17);
}
static inline void packed_store(unsigned char *dst,uint32_t word,unsigned bpp,int swap)
{
 if(bpp==2){uint16_t short_word=word;memcpy(dst,&short_word,2);}else memcpy(dst,&word,4);
 if(swap)for(unsigned i=0;i<bpp/2;i++){unsigned char t=dst[i];dst[i]=dst[bpp-1-i];dst[bpp-1-i]=t;}
}
#endif
