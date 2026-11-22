/* Query compositor/renderer status; no configuration changes. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <errno.h>
#include <string.h>
#include <dlfcn.h>
#include <unistd.h>
#include <ApplicationServices/ApplicationServices.h>
#include <OpenGL/OpenGL.h>
static void marker_status(const char *label,const char *path)
{
 if(access(path,F_OK)==0)printf("%s opt-out marker=present\n",label);
 else {
  int error=errno;
  if(error==ENOENT)printf("%s opt-out marker=absent\n",label);
  else printf("%s opt-out marker=access-error errno=%d (%s)\n",label,error,strerror(error));
 }
}
int main(void)
{
 marker_status("CoreImage","/Library/Application Support/RadeonNI/nocoreimage");
 marker_status("Pbuffer","/Library/Application Support/RadeonNI/nopbuffer");
 puts("Marker results describe this process's access, not WindowServer's cached choice.");
 CGDirectDisplayID displays[16];CGDisplayCount count=0,i;
 CGError err=CGGetActiveDisplayList(16,displays,&count);
 if(err || !count){printf("No active Aqua display (error %d); run in Terminal on the G5 desktop.\n",err);return 1;}
 for(i=0;i<count;i++) {
  CGOpenGLDisplayMask mask=CGDisplayIDToOpenGLDisplayMask(displays[i]);
  printf("display %u id=0x%x mask=0x%x QuartzExtreme=%s\n",(unsigned)i,(unsigned)displays[i],mask,
         CGDisplayUsesOpenGLAcceleration(displays[i])?"in-use":"not-in-use");
  CGLRendererInfoObj info=0;GLint n=0,j;
  CGLError e=CGLQueryRendererInfo(mask,&info,&n);
  printf("CGLQueryRendererInfo error=%d count=%d\n",e,(int)n);
  if(!e)for(j=0;j<n;j++) {
   GLint id=0,accel=0,vram=0,window=0;
   CGLDescribeRenderer(info,j,kCGLRPRendererID,&id);
   CGLDescribeRenderer(info,j,kCGLRPAccelerated,&accel);
   CGLDescribeRenderer(info,j,kCGLRPVideoMemory,&vram);
   CGLDescribeRenderer(info,j,kCGLRPWindow,&window);
   printf("renderer id=0x%x accelerated=%d window=%d vram_MB=%u\n",id,accel,window,(unsigned)vram>>20);
  }
  if(info)CGLDestroyRendererInfo(info);
 }
 void *cg=dlopen("/System/Library/Frameworks/ApplicationServices.framework/Frameworks/CoreGraphics.framework/CoreGraphics",RTLD_LAZY|RTLD_LOCAL);
 int (*state)(int)=cg?(int(*)(int))dlsym(cg,"CGSServerOperationState"):0;
 if(state)printf("WindowServer CoreImage capability flag=%d (not a filter-correctness test)\n",state(0xf));
 else puts("WindowServer CoreImage capability query unavailable");
 if(cg)dlclose(cg);
 return 0;
}
