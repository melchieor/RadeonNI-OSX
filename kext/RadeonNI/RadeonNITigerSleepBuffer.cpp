/* Experimental and unconnected Tiger GART buffer helpers. MIT */
#include "RadeonNITigerSleepBuffer.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <string.h>
#endif
int rdn_tiger_sleep_write_ib(void *cookie,const uint32_t *words,uint32_t count)
{
 rdn_tiger_sleep_buffer *b=(rdn_tiger_sleep_buffer *)cookie;
 volatile uint32_t *out;uint32_t i;
 if(!b || !b->stage || !b->accel || !words || !count || count>RDN_STAGE_PAGE/4 ||
    b->stage->size!=RDN_STAGE_PAGE || b->stage->stage.bytes!=RDN_STAGE_PAGE ||
    !rdn_tiger_sleep_stage_matches(b->stage,&b->stage->stage,b->stage->gart))return -1;
 out=(volatile uint32_t *)b->stage->memory->getBytesNoCopy();
 if(!out || ((uintptr_t)out&3))return -1;
 /* Match rdn_ib_selftest: swapped CP consumes CPU-order words. */
 for(i=0;i<count;++i)out[i]=b->accel->swapped?words[i]:rdn_swap_le32(words[i]);
 return 0;
}
static int sync_stage(rdn_tiger_sleep_stage *stage,IOOptionBits operation)
{
 if(!stage || stage->size!=RDN_STAGE_PAGE || stage->stage.bytes!=RDN_STAGE_PAGE ||
    !rdn_tiger_sleep_stage_matches(stage,&stage->stage,stage->gart))return -1;
 return stage->memory->performOperation(operation,0,RDN_STAGE_PAGE)==kIOReturnSuccess ? 0 : -1;
}
int rdn_tiger_sleep_publish_ib(void *cookie)
{
 rdn_tiger_sleep_buffer *buffer=(rdn_tiger_sleep_buffer *)cookie;
 return buffer ? sync_stage(buffer->stage,kIOMemoryIncoherentIOStore) : -1;
}
int rdn_tiger_sleep_sync_data(void *cookie)
{return sync_stage((rdn_tiger_sleep_stage *)cookie,kIOMemoryIncoherentIOFlush);}
int rdn_tiger_sleep_cpu_barrier(void *cookie)
{
 (void)cookie;
#if defined(__ppc__) || defined(__ppc64__)
 __asm__ __volatile__("sync" : : : "memory");
#else
 __sync_synchronize();
#endif
 return 0;
}
int rdn_tiger_sleep_copy_bytes(rdn_tiger_sleep_stage *s,rdn_sleep_copy *copy,
                               rdn_sleep_runtime *runtime,void *out,uint32_t bytes)
{
 void *source;uintptr_t a,b;
 if(!s || !copy || !runtime || !out || bytes!=RDN_STAGE_PAGE ||
    s->size!=RDN_STAGE_PAGE || s->stage.bytes!=RDN_STAGE_PAGE ||
    copy->stage!=&s->stage || copy->transfer.phase!=RDN_TRANSFER_READY ||
    !copy->quiesce || copy->quiesce->phase!=RDN_QUIESCE_HELD_POWERED ||
    copy->quiesce->generation!=copy->generation || copy->quiesce->internal_hold!=1 ||
    runtime->stage!=&s->stage || runtime->copy!=copy || runtime->quiesce!=copy->quiesce ||
    !runtime->use_gart_ib || !runtime->submitted || runtime->sequence!=copy->transfer.fence ||
    !runtime->saw_fence || !runtime->coherency_verified ||
    !rdn_tiger_sleep_stage_matches(s,&s->stage,s->gart))return -1;
 source=s->memory->getBytesNoCopy();a=(uintptr_t)source;b=(uintptr_t)out;
 if(!source || a>UINTPTR_MAX-bytes || b>UINTPTR_MAX-bytes ||
    (a<b+bytes && b<a+bytes))return -1;
 memcpy(out,source,bytes);return 0;
}
#endif
