/* Metadata-only live VRAM plan check; no GPU-memory read or write. MIT. */
#include <Python/Python.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include "rdn_user.h"
#include "rdn_probe_device.h"
static uint64_t pair(UInt32 lo,UInt32 hi){return ((uint64_t)hi<<32)|lo;}
static PyObject *check(PyObject *self,PyObject *args)
{
 io_service_t service;io_connect_t c=0;struct rdn_user_live_plan p;
 IOByteCount n=sizeof(p);kern_return_t e;uint64_t reserved,visible,command,hidden,image;
 (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
 if(geteuid()!=0){PyErr_SetString(PyExc_RuntimeError,"Run as administrator");return NULL;}
 service=rdn_probe_device("6704");
 if(!service){PyErr_SetString(PyExc_RuntimeError,"V7900 accelerator not found");return NULL;}
 e=IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&c);IOObjectRelease(service);
 if(e){PyErr_SetString(PyExc_RuntimeError,"Open failed");return NULL;}
 memset(&p,0,sizeof(p));e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_LIVE_PLAN,0,&n,&p);
 IOServiceClose(c);
 if(e||n!=sizeof(p)||p.version!=RDN_SLEEP_LIVE_PLAN_VERSION||p.size!=sizeof(p))goto fail;
 reserved=pair(p.reserved_lo,p.reserved_hi);visible=pair(p.visible_lo,p.visible_hi);
 command=pair(p.command_lo,p.command_hi);hidden=pair(p.hidden_lo,p.hidden_hi);image=pair(p.image_lo,p.image_hi);
 if(!reserved||p.range_count!=1+p.visible_allocations+p.command_allocations+p.hidden_allocations||
    p.missing_mask!=(RDN_LIVE_MISSING_CONTENTS|RDN_LIVE_MISSING_GART|
                     RDN_LIVE_MISSING_DEVICE_STATE|RDN_LIVE_MISSING_CLIENT_METADATA)||p.content_saved||
    reserved>UINT64_MAX-visible||reserved+visible>UINT64_MAX-command||
    reserved+visible+command>UINT64_MAX-hidden||image!=reserved+visible+command+hidden)goto fail;
 printf("LIVE_PLAN_OK ranges=%u visible_allocations=%u command_allocations=%u hidden_allocations=%u\n",
        p.range_count,p.visible_allocations,p.command_allocations,p.hidden_allocations);
 printf("bytes_reserved=%llu bytes_visible=%llu bytes_command=%llu bytes_hidden=%llu bytes_image=%llu\n",
        (unsigned long long)reserved,(unsigned long long)visible,(unsigned long long)command,
        (unsigned long long)hidden,(unsigned long long)image);
 printf("missing_mask=0x%x content_saved=%u; no sleep image or wake support claimed.\n",p.missing_mask,p.content_saved);
 fflush(stdout);Py_INCREF(Py_None);return Py_None;
fail:
 fprintf(stderr,"Live plan failed validation: status=0x%x bytes=%lu\n",e,(unsigned long)n);fflush(stderr);
 PyErr_SetString(PyExc_RuntimeError,"Live VRAM plan unavailable or invalid");return NULL;
}
static PyMethodDef methods[]={{"check",check,METH_VARARGS,"Read live VRAM plan metadata."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_live_plan(void){Py_InitModule("rdn_live_plan",methods);}
