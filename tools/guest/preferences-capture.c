/* Bounded logging in ONE launched Preferences process. No installed-file writes.
   MIT, kouta-kun and Claude. Private symbols require runner-pinned driver hash. */
#include <CoreFoundation/CoreFoundation.h>
#include <mach-o/dyld.h>
#include <mach-o/loader.h>
#include <mach-o/nlist.h>
#include <mach/vm_prot.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <time.h>
static FILE *status;
static CFRunLoopTimerRef timer;
static const struct mach_header *image;
static int *trace_flag,*all_flag,old_trace,old_all,enabled,stopped;
static void *(*current_mesa)(void);
static void *(*lookup_mesa)(const char *);
static CFAbsoluteTime start,enabled_at;
static unsigned duration=90;
static unsigned ticks,samples;
/* 32-bit address validation, including signed dyld slide and overflow. */
static int capture_range(uint64_t symbol,uint64_t vmaddr,uint64_t size,int64_t slide,unsigned prot,unsigned need)
{
 if(symbol>UINT32_MAX||vmaddr>UINT32_MAX||slide<INT32_MIN||slide>INT32_MAX)return 0;
 int64_t a=(int64_t)symbol+slide,b=(int64_t)vmaddr+slide;
 if(!(prot&need)||a<0||b<0||size>UINT32_MAX||a>UINT32_MAX||b>UINT32_MAX)return 0;
 uint64_t end=(uint64_t)b+size;
 return end<=((uint64_t)UINT32_MAX+1)&&a>=b&&(uint64_t)a+4<=end&&!(a&3);
}
static void *local_symbol(const struct mach_header *header,const char *path,intptr_t slide,const char *name,unsigned prot)
{
 struct nlist names[2];memset(names,0,sizeof(names));names[0].n_un.n_name=(char *)name;
 if(header->magic!=MH_MAGIC||header->ncmds>1024||nlist(path,names)||!names[0].n_value||(names[0].n_type&N_TYPE)!=N_SECT)return NULL;
 const char *at=(const char *)(header+1),*end=at+header->sizeofcmds;
 for(unsigned i=0;i<header->ncmds;i++){
  if(at+sizeof(struct load_command)>end)return NULL;
  const struct load_command *cmd=(const void *)at;
  if(cmd->cmdsize<sizeof(*cmd)||cmd->cmdsize>(unsigned)(end-at))return NULL;
  if(cmd->cmd==LC_SEGMENT&&cmd->cmdsize>=sizeof(struct segment_command)){
   const struct segment_command *seg=(const void *)at;
   if(capture_range(names[0].n_value,seg->vmaddr,seg->vmsize,slide,seg->initprot,prot))return (void *)(uintptr_t)((int64_t)names[0].n_value+slide);
  }
  at+=cmd->cmdsize;
 }
 return NULL;
}
static int still_loaded(void)
{for(unsigned i=0;i<_dyld_image_count();i++)if(_dyld_get_image_header(i)==image)return 1;return 0;}
static void stop_capture(const char *reason)
{
 if(stopped)return;
 stopped=1;
 if(enabled&&still_loaded()){*trace_flag=old_trace;*all_flag=old_all;}
 if(status){fprintf(status,"STOP reason=%s enabled=%d state_samples=%u flags_restored_if_loaded=1\n",reason,enabled,samples);fflush(status);}
 if(timer)CFRunLoopTimerInvalidate(timer);
}
static void step(CFRunLoopTimerRef t,void *unused)
{
 (void)t;(void)unused;
 CFAbsoluteTime now=CFAbsoluteTimeGetCurrent();
 if((enabled&&now-enabled_at>=duration)||(!enabled&&now-start>=90)){stop_capture("time-limit");return;}
 if(!enabled){
  const char *suffix="/RadeonNIGLDriver.bundle/Contents/MacOS/RadeonNIGLDriver";
  for(unsigned i=0;i<_dyld_image_count();i++){
   const char *path=_dyld_get_image_name(i);size_t n=strlen(path),tail=strlen(suffix);
   if(n<tail||strcmp(path+n-tail,suffix))continue;
   const struct mach_header *mh=_dyld_get_image_header(i);intptr_t slide=_dyld_get_image_vmaddr_slide(i);
   int *logging=local_symbol(mh,path,slide,"_rdn_logging",VM_PROT_WRITE);
   int *trace=local_symbol(mh,path,slide,"_rdn_trace",VM_PROT_WRITE);
   int *all=local_symbol(mh,path,slide,"_log_all",VM_PROT_WRITE);
   if(!logging||!trace||!all||*logging!=1)continue;
   if((*trace!=0&&*trace!=1)||(*all!=0&&*all!=1)){stop_capture("unexpected-flag-values");return;}
   image=mh;trace_flag=trace;all_flag=all;old_trace=*trace;old_all=*all;
   current_mesa=local_symbol(mh,path,slide,"_OSMesaGetCurrentContext",VM_PROT_EXECUTE);
   lookup_mesa=local_symbol(mh,path,slide,"_OSMesaGetProcAddress",VM_PROT_EXECUTE);
   *trace_flag=1;*all_flag=1;enabled=1;enabled_at=now;
   fprintf(status,"ENABLED pid-local flags; persistent_driver_unchanged=1 old_trace=%d old_all=%d\n",old_trace,old_all);fflush(status);break;
  }
 }
 if(enabled&&!still_loaded()){stop_capture("driver-unloaded");return;}
 const char *log=getenv("RDN_GLD_LOG");struct stat info;
 if(log&&!stat(log,&info)&&info.st_size>32*1024*1024){stop_capture("32-MiB-log-budget");return;}
 if(enabled&&++ticks%10==0&&current_mesa&&lookup_mesa&&current_mesa()){
  void (*get)(unsigned,int *)=lookup_mesa("glGetIntegerv");if(!get)return;
  const unsigned keys[]={0x84e0,0x8069,0x84f6,0x0be1,0x0be0,0x0cf5,0x0cf2,0x0cf4,0x0cf3,0x0cf0,0x8b8d,0x88ef};
  int values[12]={0},viewport[4]={0},scissor[4]={0};
  for(unsigned i=0;i<12;i++)get(keys[i],&values[i]);
  get(0x0ba2,viewport);get(0x0c10,scissor);
  fprintf(status,"IDLE_STATE sample=%u active=%x tex2d=%d rect=%d blend_src=%x dst=%x unpack_align=%d row=%d skip_x=%d skip_y=%d swap=%d GLSL_program=%d unpack_pbo=%d viewport=%d,%d,%d,%d scissor=%d,%d,%d,%d\n",++samples,values[0],values[1],values[2],values[3],values[4],values[5],values[6],values[7],values[8],values[9],values[10],values[11],viewport[0],viewport[1],viewport[2],viewport[3],scissor[0],scissor[1],scissor[2],scissor[3]);fflush(status);
 }
}
__attribute__((constructor)) static void capture_start(void)
{
 const char *on=getenv("RDN_CAPTURE_ENABLE"),*path=getenv("RDN_CAPTURE_STATUS");
 const char *program=getprogname();
 if(!on||strcmp(on,"1")||!path||!program||(strcmp(program,"System Preferences")&&strcmp(program,"capture-preflight")))return;
 status=fopen(path,"w");if(!status)return;
 fprintf(status,"Own-process capture; tracing can alter timing and binding-cache behavior. Idle snapshots are not per-draw snapshots.\n");fflush(status);
 const char *seconds=getenv("RDN_CAPTURE_SECONDS");
 if(seconds){unsigned requested=atoi(seconds);if(requested>=2&&requested<=90)duration=requested;}
 start=CFAbsoluteTimeGetCurrent();timer=CFRunLoopTimerCreate(NULL,CFAbsoluteTimeGetCurrent()+0.2,0.2,0,0,step,NULL);
 if(timer)CFRunLoopAddTimer(CFRunLoopGetMain(),timer,kCFRunLoopCommonModes);
 else stop_capture("timer-creation-failed");
}
__attribute__((destructor)) static void capture_end(void)
{if(status){stop_capture("process-exit");if(timer)CFRelease(timer);fclose(status);status=NULL;}}
