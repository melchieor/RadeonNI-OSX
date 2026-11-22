/* Bounded multi-page powered hidden VRAM test for the experimental kext. MIT. */
#define rehearse rdn_old_rehearse
#define initrdn_hidden_index_rehearsal rdn_old_module_init
#include "tiger_hidden_index_rehearsal.c"
#undef rehearse
#undef initrdn_hidden_index_rehearsal

#define PAGE_BYTES 4096u
#define PAGE_COUNT 3u
#ifdef RDN_INDEX_TIMED_PROBE
#include <sys/time.h>
static uint64_t wall_us(void)
{
    struct timeval tv;
    if(gettimeofday(&tv,0))return 0;
    return (uint64_t)tv.tv_sec*1000000u+(uint64_t)tv.tv_usec;
}
#endif
#ifdef RDN_INDEX_RESTORE_PROBE
static unsigned char saved_pages[PAGE_COUNT][PAGE_BYTES];
static UInt32 packed(const unsigned char *p)
{return ((UInt32)p[0]<<24)|((UInt32)p[1]<<16)|((UInt32)p[2]<<8)|p[3];}
static kern_return_t restore_chunk(io_connect_t c,UInt32 offset,const unsigned char *p)
{
    kern_return_t e=kIOReturnNotReady;
    for(unsigned attempt=0;attempt<20;attempt++) {
        e=IOConnectMethodScalarIScalarO(c,RDN_UC_SLEEP_INDEX_RESTORE,5,0,offset,
                                      packed(p),packed(p+4),packed(p+8),packed(p+12));
        if(!e)return e;
        if(e!=kIOReturnNotReady && e!=kIOReturnBusy)return e;
        usleep(50000);
    }
    return e;
}
#endif

static unsigned char seed(unsigned page,unsigned byte)
{return (unsigned char)(0x5au^(byte*13u)^(byte>>4)^(page*71u));}
static unsigned char indexed(unsigned byte)
{return (unsigned char)(0xd3u^((byte%16u)*13u)^(byte/16u));}
static kern_return_t index_access(io_connect_t c,UInt32 offset,int write,unsigned char out[16])
{
    IOByteCount n; kern_return_t e=kIOReturnNotReady;
    for(unsigned attempt=0;attempt<20;attempt++) {
        n=16;e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,
                          offset|(write?RDN_SLEEP_INDEX_WRITE:0),out);
        if(!e)return n==16?kIOReturnSuccess:kIOReturnBadArgument;
        if(e!=kIOReturnNotReady && e!=kIOReturnBusy)return e;
        usleep(50000);
    }
    return e;
}
static PyObject *batch(PyObject *self,PyObject *args)
{
    io_service_t service=0;io_connect_t c=0;vm_address_t aperture=0;vm_size_t length=0;
    UInt32 visible=0,hidden[PAGE_COUNT]={0};unsigned count=0;int have_visible=0,mapped=0,ok=0;
    struct rdn_user_info info;IOByteCount n=sizeof(info);kern_return_t e=0;
    unsigned char observed[16];uint64_t base;
    (void)self;if(!PyArg_ParseTuple(args,""))return NULL;
    if(geteuid()!=0){PyErr_SetString(PyExc_RuntimeError,"Run as administrator");return NULL;}
    service=rdn_probe_device("6704");
    if(!service || IOServiceOpen(service,mach_task_self(),RDN_UC_TYPE_V2,&c))goto done;
    IOObjectRelease(service);service=0;memset(&info,0,sizeof(info));
    if(IOConnectMethodScalarIStructureO(c,RDN_UC_GET_INFO,0,&n,&info)||n!=sizeof(info)||info.pci_device_id!=0x6704)goto done;
    if(IOConnectMapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),&aperture,&length,kIOMapAnywhere))goto done;
    mapped=1;
    if(IOConnectMethodScalarIScalarO(c,RDN_UC_ALLOC,2,1,3*PAGE_BYTES,PAGE_BYTES,&visible))goto done;
    have_visible=1;
    if((uint64_t)visible+3*PAGE_BYTES>length)goto done;
    for(count=0;count<PAGE_COUNT;count++) {
        if(IOConnectMethodScalarIScalarO(c,RDN_UC_ALLOC_HIDDEN,2,1,PAGE_BYTES,PAGE_BYTES,&hidden[count]))goto done;
        if(hidden[count]<length||(uint64_t)hidden[count]+PAGE_BYTES>0x7ffffffcULL){count++;goto done;}
        for(unsigned j=0;j<count;j++)if(hidden[j]==hidden[count]){count++;goto done;}
    }
    volatile unsigned char *v=(volatile unsigned char *)(aperture+visible);
    volatile uint32_t *ib=(volatile uint32_t *)v;
    base=((uint64_t)info.vram_gpu_base_hi<<32)|info.vram_gpu_base_lo;
    /* All pages are initialized before checking any, to expose aliasing. */
    for(unsigned p=0;p<PAGE_COUNT;p++) {
        for(unsigned i=0;i<PAGE_BYTES;i++)v[PAGE_BYTES+i]=seed(p,i);
        __sync_synchronize();gpu_copy(c,ib,visible,base+visible+PAGE_BYTES,base+hidden[p],PAGE_BYTES);
    }
#ifdef RDN_INDEX_TIMED_PROBE
    uint64_t read_start=wall_us();
#endif
    for(unsigned p=0;p<PAGE_COUNT;p++)for(unsigned pos=0;pos<PAGE_BYTES;pos+=16) {
        e=index_access(c,hidden[p]+pos,0,observed);
        if(e){fprintf(stderr,"Indexed seed read failed page=%u pos=%u status=0x%x\n",p,pos,e);goto done;}
        for(unsigned j=0;j<16;j++)if(observed[j]!=seed(p,pos+j)) {
            fprintf(stderr,"GPU-to-index mismatch page=%u pos=%u\n",p,pos+j);goto done;
        }
#ifdef RDN_INDEX_RESTORE_PROBE
        memcpy(&saved_pages[p][pos],observed,16);
#endif
    }
#ifdef RDN_INDEX_TIMED_PROBE
    uint64_t read_end=wall_us();
    if(!read_start || read_end<read_start){fprintf(stderr,"Capture timer failed\n");goto done;}
    printf("CAPTURE_12K_USERCALL_US=%llu\n",(unsigned long long)(read_end-read_start));
#endif
    puts("BATCH_GPU_TO_INDEX_PASS: 3 distinct 4 KiB pages, all bytes.");fflush(stdout);
    /* A misaligned address and a page not allocated by this connection must
     * be rejected before reading or writing any register-window bytes. */
    n=16;e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,hidden[0]+1,observed);
    if(e!=kIOReturnBadArgument){fprintf(stderr,"Misaligned request was not rejected: 0x%x\n",e);goto done;}
    UInt32 unowned=hidden[0]+16*PAGE_BYTES;
    for(unsigned p=0;p<PAGE_COUNT;p++)if(unowned==hidden[p])goto done;
    if(unowned>=0x7ffff000u)goto done;
    n=16;e=IOConnectMethodScalarIStructureO(c,RDN_UC_SLEEP_INDEX_HIDDEN,1,&n,unowned|RDN_SLEEP_INDEX_WRITE,observed);
    if(e!=kIOReturnBadArgument){fprintf(stderr,"Unowned request was not rejected: 0x%x\n",e);goto done;}
#ifdef RDN_INDEX_RESTORE_PROBE
    e=IOConnectMethodScalarIScalarO(c,RDN_UC_SLEEP_INDEX_RESTORE,5,0,unowned,1,2,3,4);
    if(e!=kIOReturnBadArgument){fprintf(stderr,"Unowned restore was not rejected: 0x%x\n",e);goto done;}
#endif
    puts("BATCH_ACCESS_REJECTIONS_PASS: misaligned and unowned requests rejected.");fflush(stdout);
    for(unsigned p=0;p<PAGE_COUNT;p++) {
        for(unsigned pos=0;pos<PAGE_BYTES;pos+=16) {
            e=index_access(c,hidden[p]+pos,1,observed);
            if(e){fprintf(stderr,"Indexed write failed page=%u pos=%u status=0x%x\n",p,pos,e);goto done;}
            for(unsigned j=0;j<16;j++)if(observed[j]!=indexed(pos+j)) {
                fprintf(stderr,"Indexed write/read mismatch page=%u pos=%u\n",p,pos+j);goto done;
            }
        }
        /* Unchanged pages must retain their own GPU-written sentinels. */
        for(unsigned q=p+1;q<PAGE_COUNT;q++)for(unsigned edge=0;edge<2;edge++) {
            unsigned pos=edge?(PAGE_BYTES-16):0;
            e=index_access(c,hidden[q]+pos,0,observed);
            if(e){fprintf(stderr,"Isolation read failed status=0x%x\n",e);goto done;}
            for(unsigned j=0;j<16;j++)if(observed[j]!=seed(q,pos+j)) {
                fprintf(stderr,"Page isolation mismatch after page=%u other=%u pos=%u\n",p,q,pos+j);goto done;
            }
        }
        for(unsigned i=0;i<PAGE_BYTES;i++)v[2*PAGE_BYTES+i]=(unsigned char)~indexed(i);
        __sync_synchronize();gpu_copy(c,ib,visible,base+hidden[p],base+visible+2*PAGE_BYTES,PAGE_BYTES);
        for(unsigned i=0;i<PAGE_BYTES;i++)if(v[2*PAGE_BYTES+i]!=indexed(i)) {
            fprintf(stderr,"Index-to-GPU mismatch page=%u pos=%u\n",p,i);goto done;
        }
    }
    puts("BATCH_INDEX_TO_GPU_PASS: 3 x 4 KiB, all bytes; untouched-page boundaries preserved.");
#ifdef RDN_INDEX_RESTORE_PROBE
    /* Restore the actual captured bytes, not the diagnostic fixed pattern. */
#ifdef RDN_INDEX_TIMED_PROBE
    uint64_t restore_start=wall_us();
#endif
    for(unsigned p=0;p<PAGE_COUNT;p++)for(unsigned pos=0;pos<PAGE_BYTES;pos+=16) {
        e=restore_chunk(c,hidden[p]+pos,&saved_pages[p][pos]);
        if(e){fprintf(stderr,"Restore failed page=%u pos=%u status=0x%x\n",p,pos,e);goto done;}
    }
#ifdef RDN_INDEX_TIMED_PROBE
    uint64_t restore_end=wall_us();
    if(!restore_start || restore_end<restore_start){fprintf(stderr,"Restore timer failed\n");goto done;}
    printf("RESTORE_12K_USERCALL_US=%llu\n",(unsigned long long)(restore_end-restore_start));
#endif
    for(unsigned p=0;p<PAGE_COUNT;p++) {
        for(unsigned i=0;i<PAGE_BYTES;i++)v[2*PAGE_BYTES+i]=(unsigned char)~saved_pages[p][i];
        __sync_synchronize();gpu_copy(c,ib,visible,base+hidden[p],base+visible+2*PAGE_BYTES,PAGE_BYTES);
        for(unsigned i=0;i<PAGE_BYTES;i++)if(v[2*PAGE_BYTES+i]!=saved_pages[p][i]) {
            fprintf(stderr,"Saved-image GPU verification failed page=%u pos=%u\n",p,i);goto done;
        }
    }
    puts("BATCH_SAVED_IMAGE_RESTORE_PASS: GPU verified all 12288 captured bytes after overwrite.");
#endif
    puts("BATCH_DATA_PASS: powered private-page comparisons complete.");ok=1;
done:
    while(count) {
        e=IOConnectMethodScalarIScalarO(c,RDN_UC_FREE,1,0,hidden[--count]);
        if(e){fprintf(stderr,"Hidden allocation release failed: 0x%x\n",e);ok=0;}
    }
    if(have_visible) {
        e=IOConnectMethodScalarIScalarO(c,RDN_UC_FREE,1,0,visible);
        if(e){fprintf(stderr,"Visible allocation release failed: 0x%x\n",e);ok=0;}
    }
    if(mapped && IOConnectUnmapMemory(c,RDN_UC_MEMORY_APERTURE,mach_task_self(),aperture))ok=0;
    if(c && IOServiceClose(c))ok=0;if(service)IOObjectRelease(service);
    if(ok){puts("BATCH_RELEASE_CALLS_PASS: all private allocation release calls succeeded.");
           puts("BATCH_PASS: powered private-page checks complete; sleep remains untested.");}
    fflush(stdout);fflush(stderr);
    if(!ok){PyErr_SetString(PyExc_RuntimeError,"Batch failed or incomplete; inspect output");return NULL;}
    Py_INCREF(Py_None);return Py_None;
}
static PyMethodDef batch_methods[]={{"run",batch,METH_VARARGS,"Run powered hidden VRAM batch."},{0,0,0,0}};
PyMODINIT_FUNC initrdn_hidden_batch(void){Py_InitModule("rdn_hidden_batch",batch_methods);}
