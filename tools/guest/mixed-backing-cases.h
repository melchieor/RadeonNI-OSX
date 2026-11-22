/* Owned-backing interleaving experiment. MIT, kouta-kun and Claude. */
#include <sys/stat.h>
static int mixed_backing(CGLContextObj ctx,io_connect_t surface,unsigned char *cpu,
                        unsigned w,unsigned h,unsigned stride,const char *mode,const char *out,
                        int (*attach)(void *,unsigned long),void *producer,unsigned id)
{
 int locked=!strcmp(mode,"mixed-locked"),reattach=!strcmp(mode,"mixed-reattach");
 if(!locked&&!reattach&&strcmp(mode,"mixed-direct"))return 2;
 if(mkdir(out,0755)){perror("new mixed output directory required");return 2;}
 unsigned mismatches=0,api_errors=0;IOAccelSurfaceInformation info;IOByteCount bytes;
 for(unsigned phase=0;phase<4;phase++){
  /* Establish a visible, synchronized base before each independent experiment. */
  glDisable(GL_SCISSOR_TEST);glColorMask(1,1,1,1);glClearColor(1,0,0,1);glClear(GL_COLOR_BUFFER_BIT);glFinish();
  bytes=sizeof(info);CHECK(IOConnectMethodScalarIStructureO(surface,kIOAccelSurfaceReadLockOptions,1,&bytes,0,&info));
  CHECK(IOConnectMethodScalarIScalarO(surface,kIOAccelSurfaceReadUnlockOptions,1,0,0));
  if(locked){bytes=sizeof(info);CHECK(IOConnectMethodScalarIStructureO(surface,kIOAccelSurfaceWriteLockOptions,1,&bytes,0,&info));}
  /* CPU paints a blue tile. Alternate its position to cross cache/row boundaries. */
  unsigned x0=7+phase*3,y0=5+phase*2;
  for(unsigned y=y0;y<y0+13;y++)for(unsigned x=x0;x<x0+17;x++){
   unsigned char *p=cpu+y*stride+x*4;p[0]=255;p[1]=0;p[2]=0;p[3]=255;
  }
  __asm__ volatile("sync":::"memory");
  if(locked)CHECK(IOConnectMethodScalarIScalarO(surface,kIOAccelSurfaceWriteUnlockOptions,1,0,0));
  if(reattach&&!attach(producer,id))return 3;
  /* GPU paints a separate green tile; the CPU tile is outside this scissor. */
  unsigned gx=w/2,gy=h/2;glEnable(GL_SCISSOR_TEST);glScissor(gx,gy,19,11);
  glClearColor(0,1,0,1);glClear(GL_COLOR_BUFFER_BIT);glDisable(GL_SCISSOR_TEST);glFinish();
  bytes=sizeof(info);CHECK(IOConnectMethodScalarIStructureO(surface,kIOAccelSurfaceReadLockOptions,1,&bytes,0,&info));
  char path[1024];snprintf(path,sizeof(path),"%s/phase-%u.rgba",out,phase);FILE *fp=fopen(path,"wb");if(!fp)return 4;
  unsigned bad=0;unsigned char rgba[4];
  for(unsigned y=0;y<h;y++)for(unsigned x=0;x<w;x++){
   unsigned char *p=cpu+y*stride+x*4;unsigned want_r=255,want_g=0,want_b=0;
   if(x>=x0&&x<x0+17&&y>=y0&&y<y0+13){want_r=0;want_b=255;}
   /* Quartz CPU rows top-down; GL scissor origin bottom-left. */
   if(x>=gx&&x<gx+19&&y>=h-gy-11&&y<h-gy){want_r=0;want_g=255;want_b=0;}
   if(p[0]!=255||p[1]!=want_r||p[2]!=want_g||p[3]!=want_b){
    if(bad<4)printf("phase=%u xy=%u,%u expected_ARGB=255,%u,%u,%u actual=%u,%u,%u,%u\n",phase,x,y,want_r,want_g,want_b,p[0],p[1],p[2],p[3]);bad++;
   }
   rgba[0]=p[1];rgba[1]=p[2];rgba[2]=p[3];rgba[3]=p[0];
   if(fwrite(rgba,1,4,fp)!=4){fclose(fp);return 4;}
  }
  if(fclose(fp))return 4;
  CHECK(IOConnectMethodScalarIScalarO(surface,kIOAccelSurfaceReadUnlockOptions,1,0,0));
  GLenum error=glGetError();if(error)api_errors++;
  printf("%s phase=%u mismatched_pixels=%u/%u GL_error=%x\n",mode,phase,bad,w*h,error);mismatches+=bad;
 }
 printf("MIXED_RESULT mode=%s total_mismatches=%u api_errors=%u semantics=%s\n",mode,mismatches,api_errors,
        locked?"explicit-lock-contract":"direct-write-observation-not-contract-qualification");
 (void)ctx;
 /* Direct writes without publication may be unsupported; retain evidence without
    declaring that a mismatch is a driver correctness failure. */
 return api_errors?1:(locked&&mismatches)?1:0;
}
