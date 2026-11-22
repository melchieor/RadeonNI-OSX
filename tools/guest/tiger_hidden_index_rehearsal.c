/* Powered, private hidden-VRAM diagnostic. No suspend or device reset. MIT. */
#include <Python/Python.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <signal.h>
#include <mach/mach.h>
#include <IOKit/IOKitLib.h>
#include "rdn_user.h"
#include "rdn_probe_device.h"

static void retain_until_reboot(void)
{
    /* A timed-out command may still access these VRAM allocations. Keep the
     * connection alive rather than voluntarily releasing them. SIGKILL,
     * process termination or device removal can still defeat this measure. */
    signal(SIGHUP,SIG_IGN);signal(SIGINT,SIG_IGN);signal(SIGTERM,SIG_IGN);
    fprintf(stderr,"GPU completion uncertain: retaining allocations; restart the G5 before further testing.\n");
    fflush(stderr);
    for(;;)sleep(60);
}

static int gpu_copy(io_connect_t c,volatile uint32_t *ib,UInt32 iboff,uint64_t src,uint64_t dst,UInt32 bytes)
{
    UInt32 fence=0,reached=0; kern_return_t e;
    ib[0]=0xc0044100;ib[1]=(uint32_t)src;ib[2]=(uint32_t)(src>>32)|0x80000000u;
    ib[3]=(uint32_t)dst;ib[4]=(uint32_t)(dst>>32);ib[5]=bytes;
    for(unsigned i=6;i<16;i++)ib[i]=0x80000000u;
    __sync_synchronize();
    e=IOConnectMethodScalarIScalarO(c,RDN_UC_SUBMIT,2,1,iboff,16,&fence);
    /* A submission error may occur after publication: treat as uncertain. */
    if(e)retain_until_reboot();
    e=IOConnectMethodScalarIScalarO(c,RDN_UC_FENCE_WAIT,2,1,fence,2000,&reached);
    if(e || !reached)retain_until_reboot();
    e=IOConnectMethodScalarIScalarO(c,RDN_UC_SYNC_FOR_CPU,0,0);
    if(e)retain_until_reboot();
    __sync_synchronize();return 0;
}

static PyObject *rehearse(PyObject *self,PyObject *args)
{
    io_service_t service=0;io_connect_t c=0;vm_address_t aperture=0;vm_size_t length=0;
    UInt32 visible=0,hidden=0;int have_visible=0,have_hidden=0,mapped=0,ok=0;
    struct rdn_user_info info;IOByteCount n=sizeof(info);kern_return_t e=0;
    unsigned char observed[16],expected[16];uint64_t base;
    (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
    if(geteuid()!=0){PyErr_SetString(PyExc_RuntimeError,"Run as administrator");return NULL;}
    service=rdn_probe_device("6704");
    if(!service || IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&c))goto done;
    IOObjectRelease(service);service=0;memset(&info,0,sizeof(info));
    if(IOConnectMethodScalarIStructureO(c,RDN_UC_GET_INFO,0,&n,&info) || n!=sizeof(info) || info.pci_device_id!=0x6704)goto done;
    if(IOConnectMapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),&aperture,&length,kIOMapAnywhere))goto done;
    mapped=1;
#ifdef RDN_INDEX_FULLPAGE_PROBE
    const UInt32 visible_bytes=8192;
#else
    const UInt32 visible_bytes=4096;
#endif
    if(IOConnectMethodScalarIScalarO(c,RDN_UC_ALLOC,2,1,visible_bytes,4096,&visible))goto done;
    have_visible=1;
    if(IOConnectMethodScalarIScalarO(c,RDN_UC_ALLOC_HIDDEN,2,1,4096,4096,&hidden))goto done;
    have_hidden=1;
    if((uint64_t)visible+visible_bytes>length || hidden<length || (uint64_t)hidden+4096>0x7ffffffcULL)goto done;
    volatile uint32_t *page=(volatile uint32_t *)(aperture+visible);
    for(unsigned i=0;i<4;i++)page[i]=0x193ac570u^(i*0x01020408u);
    for(unsigned i=0;i<16;i++)expected[i]=((volatile unsigned char *)page)[i];
    __sync_synchronize();base=((uint64_t)info.vram_gpu_base_hi<<32)|info.vram_gpu_base_lo;
    printf("GPU copying 16 bytes to a connection-owned hidden page; power remains on.\n");fflush(stdout);
    gpu_copy(c,page+64,visible+256,base+visible,base+hidden,16);
    for(unsigned attempt=0;attempt<20;attempt++) {
        n=sizeof(observed);e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,hidden,observed);
        if(!e)break;
        if(e!=kIOReturnNotReady && e!=kIOReturnBusy)break;
        usleep(50000);
    }
    if(e || n!=sizeof(observed) || memcmp(observed,expected,16)) {
        fprintf(stderr,"Hidden indexed comparison failed: status=0x%x bytes=%lu\n",e,(unsigned long)n);goto done;
    }
    printf("HIDDEN_INDEX_COMPARE_PASS: 16 bytes match the GPU-written source.\n");
    gpu_copy(c,page+64,visible+256,base+hidden,base+visible+1024,16);
    for(unsigned i=0;i<16;i++)if(((volatile unsigned char *)page)[1024+i]!=expected[i]) {
        fprintf(stderr,"GPU hidden-to-visible comparison failed at byte %u\n",i);goto done;
    }
    puts("HIDDEN_GPU_READBACK_PASS: 16 bytes match after GPU copy back.");
#ifdef RDN_INDEX_WRITE_PROBE
    for(unsigned i=0;i<16;i++)expected[i]=(unsigned char)(0xd3u^(i*13u));
    for(unsigned attempt=0;attempt<20;attempt++) {
        n=sizeof(observed);e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,
                                                              hidden|RDN_SLEEP_INDEX_WRITE,observed);
        if(!e)break;
        if(e!=kIOReturnNotReady && e!=kIOReturnBusy)break;
        usleep(50000);
    }
    if(e || n!=sizeof(observed) || memcmp(observed,expected,16)) {
        fprintf(stderr,"Indexed hidden write/read failed: status=0x%x bytes=%lu\n",e,(unsigned long)n);goto done;
    }
    puts("HIDDEN_INDEX_WRITE_READ_PASS: indexed read matches written pattern.");
    for(unsigned i=0;i<16;i++)((volatile unsigned char *)page)[1024+i]=(unsigned char)~expected[i];
    __sync_synchronize();
    gpu_copy(c,page+64,visible+256,base+hidden,base+visible+1024,16);
    for(unsigned i=0;i<16;i++)if(((volatile unsigned char *)page)[1024+i]!=expected[i]) {
        fprintf(stderr,"Indexed write GPU comparison failed at byte %u\n",i);goto done;
    }
    puts("HIDDEN_INDEX_WRITE_GPU_PASS: GPU sees indexed-write pattern.");
#endif
#ifdef RDN_INDEX_RANGE_PROBE
    /* Every selector call stays within the one owned 4 KiB allocation. */
#ifdef RDN_INDEX_FULLPAGE_PROBE
    const unsigned range_bytes=4096;
#else
    const unsigned range_bytes=1024;
#endif
    for(unsigned chunk=0;chunk<range_bytes/16;chunk++) {
        unsigned char chunk_expected[16];
        for(unsigned i=0;i<16;i++)chunk_expected[i]=expected[i]^(unsigned char)chunk;
        for(unsigned attempt=0;attempt<20;attempt++) {
            n=sizeof(observed);e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,
                                                   (hidden+chunk*16)|RDN_SLEEP_INDEX_WRITE,observed);
            if(!e)break;
            if(e!=kIOReturnNotReady && e!=kIOReturnBusy)break;
            usleep(50000);
        }
        if(e || n!=sizeof(observed) || memcmp(observed,chunk_expected,16)) {
            fprintf(stderr,"Indexed hidden range write failed at chunk %u status=0x%x\n",chunk,e);goto done;
        }
    }
    for(unsigned i=0;i<range_bytes;i++)((volatile unsigned char *)page)[1024+i]=(unsigned char)~(expected[i%16]^(i/16));
    __sync_synchronize();
    gpu_copy(c,page+64,visible+256,base+hidden,base+visible+1024,range_bytes);
    for(unsigned i=0;i<range_bytes;i++)if(((volatile unsigned char *)page)[1024+i]!=(unsigned char)(expected[i%16]^(i/16))) {
        fprintf(stderr,"Indexed range GPU comparison failed at byte %u\n",i);goto done;
    }
    printf("HIDDEN_INDEX_RANGE_GPU_PASS: GPU sees all %u indexed-write bytes.\n",range_bytes);
#endif
    ok=1;
done:
    if(have_hidden)IOConnectMethodScalarIScalarO(c,RDN_UC_FREE,1,0,hidden);
    if(have_visible)IOConnectMethodScalarIScalarO(c,RDN_UC_FREE,1,0,visible);
    if(mapped)IOConnectUnmapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),aperture);
    if(c)IOServiceClose(c);if(service)IOObjectRelease(service);
    fflush(stdout);fflush(stderr);
    if(!ok){PyErr_SetString(PyExc_RuntimeError,"Hidden indexed test failed or incomplete");return NULL;}
    Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef methods[]={{"rehearse",rehearse,METH_VARARGS,"Test a private hidden VRAM page."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_hidden_index_rehearsal(void){Py_InitModule("rdn_hidden_index_rehearsal",methods);}
