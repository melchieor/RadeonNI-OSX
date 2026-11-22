/* Qualify helper activation/restoration in an owned CGL process before Prefs.
   MIT, kouta-kun and Claude. */
#include <CoreFoundation/CoreFoundation.h>
#include <OpenGL/OpenGL.h>
#include <OpenGL/gl.h>
#include <mach-o/dyld.h>
#include <mach-o/nlist.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int *flag(const char *name)
{
 for(unsigned i=0;i<_dyld_image_count();i++){
  const char *path=_dyld_get_image_name(i);
  if(!strstr(path,"/RadeonNIGLDriver.bundle/Contents/MacOS/RadeonNIGLDriver"))continue;
  struct nlist n[2];memset(n,0,sizeof(n));n[0].n_un.n_name=(char *)name;
  if(!nlist(path,n)&&n[0].n_value)return (int *)(n[0].n_value+_dyld_get_image_vmaddr_slide(i));
 }
 return NULL;
}
int main(void)
{
 setbuf(stdout,NULL);CGLPixelFormatAttribute a[]={kCGLPFARendererID,0x21a00,kCGLPFAAccelerated,kCGLPFANoRecovery,0};
 CGLPixelFormatObj pf=NULL;CGLContextObj ctx=NULL;GLint count=0;
 if(CGLChoosePixelFormat(a,&pf,&count)||!pf||!count||CGLCreateContext(pf,NULL,&ctx)||CGLSetCurrentContext(ctx))return 2;
 printf("helper preflight renderer=%s\n",glGetString(GL_RENDERER));
 int *trace=flag("_rdn_trace"),*all=flag("_log_all");if(!trace||!all)return 2;
 int old_trace=*trace,old_all=*all;
 CFRunLoopRunInMode(kCFRunLoopDefaultMode,1.0,false);
 int enabled=*trace==1&&*all==1;
 CFRunLoopRunInMode(kCFRunLoopDefaultMode,3.0,false);
 int restored=*trace==old_trace&&*all==old_all;
 const char *path=getenv("RDN_CAPTURE_STATUS");char text[8192]={0};FILE *fp=path?fopen(path,"r"):NULL;
 if(fp){fread(text,1,sizeof(text)-1,fp);fclose(fp);}
 int witnessed=strstr(text,"ENABLED pid-local flags")&&strstr(text,"STOP reason=time-limit");
 printf("helper preflight timer_witness=%d\n",witnessed);
 printf("helper preflight enabled=%d restored=%d prior=%d,%d final=%d,%d\n",enabled,restored,old_trace,old_all,*trace,*all);
 CGLSetCurrentContext(NULL);CGLDestroyContext(ctx);CGLDestroyPixelFormat(pf);
 return enabled&&restored&&witnessed?0:1;
}
