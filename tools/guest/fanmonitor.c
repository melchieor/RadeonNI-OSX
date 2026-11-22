/* Read-only Leopard PPC fan/temperature telemetry. SPDX-License-Identifier: MIT */
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>
#include "rdn_user.h"

static long property(io_service_t service,const char *key)
{
 CFStringRef name=CFStringCreateWithCString(0,key,kCFStringEncodingASCII);
 CFTypeRef value=IORegistryEntryCreateCFProperty(service,name,0,0);
 long result=-1;
 if(value && CFGetTypeID(value)==CFNumberGetTypeID())CFNumberGetValue(value,kCFNumberLongType,&result);
 if(value)CFRelease(value);CFRelease(name);return result;
}
int main(int argc,char **argv)
{
 unsigned count=10,i;char *end=0;
 if(argc==2){unsigned long n=strtoul(argv[1],&end,10);if(!*argv[1] || *end || n<1 || n>120)return 2;count=(unsigned)n;}
 else if(argc!=1){fprintf(stderr,"usage: fan-monitor [samples: 1..120]\n");return 2;}
 io_iterator_t iterator=0;io_service_t service=0;io_connect_t connection=0;
 if(IOServiceGetMatchingServices(0,IOServiceMatching("RadeonNI"),&iterator))return 1;
 while((service=IOIteratorNext(iterator))) {
  if(IOServiceOpen(service,mach_task_self(),RDN_UC_TELEMETRY,&connection)==KERN_SUCCESS)break;
  IOObjectRelease(service);service=0;
 }
 IOObjectRelease(iterator);
 if(!connection){fprintf(stderr,"No RadeonNI read-only telemetry service available\n");return 1;}
 puts("sample,temp_valid,temp_C,thermal_raw,fan_sensor_status,fan_rpm,bios_min_rpm,bios_max_rpm,requested_percent,safety_reason,tach_period");
 for(i=0;i<count;i++) {
  unsigned raw=0,unused1=0,unused2=0;struct rdn_user_board_sensors board;
  IOByteCount size=sizeof(board);
  kern_return_t a=IOConnectMethodScalarIScalarO(connection,RDN_TELEMETRY_SAMPLE,0,3,&raw,&unused1,&unused2);
  kern_return_t b=IOConnectMethodScalarIStructureO(connection,RDN_TELEMETRY_BOARD,0,&size,&board);
  if(a || b || size!=sizeof(board)) {
   fprintf(stderr,"Telemetry failed: sample=0x%x board=0x%x size=%lu\n",a,b,(unsigned long)size);
   IOServiceClose(connection);IOObjectRelease(service);return 1;
  }
  unsigned sensor=(raw>>16)&0x7ff;
  int half=(sensor&0x100)?(int)(sensor&0x1ff)-0x200:(int)(sensor&255);
  int valid=raw!=0xffffffffu && !(sensor&0x600) && half>=20 && half<=220;
  printf("%u,%d,%.1f,%08x,%u,%u,%u,%u,%ld,%ld,%u\n",i+1,valid,half/2.0,raw,
    board.fan_status,board.fan_rpm,board.fan_min_rpm,board.fan_max_rpm,
    property(service,"FanRequestedPercent"),property(service,"FanSafetyReason"),board.tach_period);
  fflush(stdout);if(i+1<count)sleep(1);
 }
 IOServiceClose(connection);IOObjectRelease(service);return 0;
}
