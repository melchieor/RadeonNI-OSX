/* Independent synthetic mask/compositing reference. MIT, kouta-kun and Claude. */
#ifndef RDN_MASKED_REFERENCE_H
#define RDN_MASKED_REFERENCE_H
#include <math.h>
#include "pixel-reference.h"
/* format:0 alpha,1 luminance,2 luminance-alpha,3 RGB,4 RGBA. */
static inline void mask_input(unsigned x,unsigned y,unsigned phase,unsigned format,unsigned char m[4])
{
 unsigned char glyph[4];pixel_source(x,y,phase,glyph);unsigned a=glyph[3];
 m[0]=a;m[1]=255-a;m[2]=(x+3*y)&255;m[3]=a;
 if(format==0){m[0]=m[1]=m[2]=0;}
 if(format==1||format==2)m[1]=m[2]=m[0];
 if(format==1||format==3)m[3]=255;
}
static inline void mask_destination(unsigned x,unsigned y,unsigned char p[4])
{p[0]=(17*x+3*y)&255;p[1]=(9*x+7*y)&255;p[2]=64+((x+y)&127);p[3]=255;}
static inline void mask_composite(const unsigned char mask[4],const unsigned char dst[4],unsigned program,unsigned char out[4])
{
 const float fg[3]={128.0f/255,64.0f/255,192.0f/255};
 for(unsigned k=0;k<3;k++){
  float coverage=(float)mask[program==2?k:1]/255;
  if(program==1||program==2)coverage*=coverage;
  float background=(float)dst[k]/255;
  float value=program==2?sqrtf(coverage*fg[k]*fg[k]+(1-coverage)*background*background):coverage*fg[k]+(1-coverage)*background;
  int byte=(int)floorf(value*255+0.5f);out[k]=byte<0?0:byte>255?255:byte;
 }
 out[3]=255;
}
#endif
