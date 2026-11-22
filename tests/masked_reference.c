/* Explicit golden values independent of GPU outputs. MIT */
#include <assert.h>
#include <stdio.h>
#include "../tools/guest/masked-reference.h"
int main(void)
{
 unsigned char m[4]={0,0,0,0},dst[4]={32,64,96,255},out[4];
 for(unsigned p=0;p<3;p++){
  mask_composite(m,dst,p,out);assert(out[0]==32&&out[1]==64&&out[2]==96&&out[3]==255);
 }
 m[0]=m[1]=m[2]=255;
 for(unsigned p=0;p<3;p++){
  mask_composite(m,dst,p,out);assert(out[0]==128&&out[1]==64&&out[2]==192&&out[3]==255);
 }
 m[0]=m[1]=m[2]=128;
 mask_composite(m,dst,0,out);assert(out[0]==80&&out[1]==64&&out[2]==144);
 mask_composite(m,dst,1,out);assert(out[0]==56&&out[1]==64&&out[2]==120);
 mask_composite(m,dst,2,out);assert(out[0]==70&&out[1]==64&&out[2]==127);
 for(unsigned f=0;f<5;f++)for(unsigned phase=0;phase<30;phase++)for(unsigned y=0;y<32;y++)for(unsigned x=0;x<64;x++){
  mask_input(x,y,phase,f,m);
  if(f==0)assert(m[0]==0&&m[1]==0&&m[2]==0);
  if(f==1||f==2)assert(m[0]==m[1]&&m[1]==m[2]);
  if(f==1||f==3)assert(m[3]==255);
  mask_destination(x,y,dst);assert(dst[3]==255);
  for(unsigned p=0;p<3;p++){mask_composite(m,dst,p,out);assert(out[3]==255);}
 }
 puts("mask reference: golden composites and307200 generated mask/destination pixels passed");
}
