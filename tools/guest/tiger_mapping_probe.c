/* Isolated user mapping test: never redirects the framebuffer. MIT. */
#include <Python/Python.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <sys/time.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include <CoreFoundation/CoreFoundation.h>
#include "rdn_user.h"
#include "rdn_probe_device.h"
struct gate_call {io_connect_t connection;kern_return_t status;UInt32 outcome;};
static void *gate_thread(void *arg)
{
 struct gate_call *call=(struct gate_call *)arg;
 call->status=IOConnectMethodScalarIScalarO(call->connection,RDN_UC_SLEEP_MAPPING_PROBE,1,1,400,&call->outcome);
 return 0;
}
static int active(io_service_t service)
{
 CFTypeRef value=IORegistryEntryCreateCFProperty(service,CFSTR("RDNMappingProbeActive"),kCFAllocatorDefault,0);
 int result=value&&CFGetTypeID(value)==CFBooleanGetTypeID()&&CFBooleanGetValue((CFBooleanRef)value);
 if(value)CFRelease(value);return result;
}
static uint64_t now_us(void)
{
 struct timeval tv;if(gettimeofday(&tv,0))return 0;
 return (uint64_t)tv.tv_sec*1000000u+(uint64_t)tv.tv_usec;
}
static PyObject *check(PyObject *self,PyObject *args)
{
 io_service_t service=0;io_connect_t connection=0;vm_address_t addr=0;vm_size_t len=0;
 pthread_t thread;int started=0,mapped=0,seen=0,active_after_read=0,ok=0;uint64_t start=0,end=0;
 volatile UInt32 value=0;struct gate_call call;memset(&call,0,sizeof(call));
 (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
 if(geteuid()!=0){PyErr_SetString(PyExc_RuntimeError,"Run as administrator");return NULL;}
 service=rdn_probe_device("6704");if(!service)goto done;
 if(active(service)){fprintf(stderr,"Prior probe is still active; refusing.\n");goto done;}
 if(IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&connection))goto done;
 if(IOConnectMapMemory(connection,RDN_UC_MEMORY_GATE_PROBE,mach_task_self(),&addr,&len,kIOMapAnywhere))goto done;
 mapped=1;if(len<4096||*(volatile UInt32 *)addr!=0x73ac19e5u)goto done;
 call.connection=connection;
 if(pthread_create(&thread,0,gate_thread,&call))goto done;
 started=1;
 for(unsigned i=0;i<1500;i++){if(active(service)){seen=1;break;}usleep(1000);}
 if(!seen){fprintf(stderr,"Did not observe active redirect; result inconclusive.\n");goto done;}
 start=now_us();value=*(volatile UInt32 *)addr;end=now_us();
 /* A second marker read distinguishes a prompt read during an active redirect
    from a test thread that was descheduled until after the redirect ended. */
 active_after_read=active(service);
 if(pthread_join(thread,0))goto done;started=0;
 if(call.status || call.outcome!=7 || !start || end<start || value!=0x73ac19e5u || active(service)) {
  fprintf(stderr,"Mapping probe failed: status=0x%x outcome=%u seen=%d\n",call.status,call.outcome,seen);goto done;
 }
 printf("USER_MAPPING_READ_DELAY_US=%llu\n",(unsigned long long)(end-start));
 printf("REDIRECT_ACTIVE_AFTER_READ=%d\n",active_after_read);
 if(active_after_read) {
  fprintf(stderr,"ISOLATED_MAPPING_GATE_NOT_EFFECTIVE: read completed while redirect marker was active.\n");goto done;
 }
 if(end-start<50000 || end-start>3000000) {
  fprintf(stderr,"Mapping delay outside observation window; result inconclusive.\n");goto done;
 }
 puts("ISOLATED_MAPPING_GATE_PASS: user read waited; kernel buffer stayed readable; mapping resumed.");
 puts("Scope: private RAM descriptor only; no framebuffer, GART, power-loss or sleep test.");ok=1;
done:
 if(started)pthread_join(thread,0);
 if(mapped)IOConnectUnmapMemory(connection,RDN_UC_MEMORY_GATE_PROBE,mach_task_self(),addr);
 if(connection)IOServiceClose(connection);if(service)IOObjectRelease(service);
 fflush(stdout);fflush(stderr);
 if(!ok){PyErr_SetString(PyExc_RuntimeError,"Mapping test failed or inconclusive");return NULL;}
 Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef methods[]={{"check",check,METH_VARARGS,"Test an isolated descriptor redirect."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_mapping_probe(void){Py_InitModule("rdn_mapping_probe",methods);}
