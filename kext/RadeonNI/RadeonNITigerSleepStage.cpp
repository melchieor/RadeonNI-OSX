/* Experimental, unconnected Tiger IOKit staging adapter. MIT */
#include "RadeonNITigerSleepStage.h"

static int stage_pin(void *p,uint32_t n)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;
 return s->memory && s->prepared && s->size==n && !s->release_pending?0:-1;
}
static int stage_reserve(void *p,uint32_t n,uint32_t *out)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;uint64_t at=0;
 if(rdn_mem_alloc(s->space,n,RDN_STAGE_PAGE,&at))return -1;
 if(at>UINT32_MAX || n>UINT32_MAX-at){rdn_mem_free(s->space,at);return -1;}
 *out=(uint32_t)at;return 0;
}
static int stage_bus(void *p,uint32_t offset,uint64_t *out)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;IOByteCount length=0;
 IOPhysicalAddress address=s->memory->getPhysicalSegment(offset,&length);
 if(!address || length<RDN_STAGE_PAGE)return -1;
 *out=(uint64_t)address;return 0;
}
static int stage_set(void *p,uint32_t offset,uint64_t bus)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;
 if(!s->gart || !s->gart->ready || (offset&(RDN_STAGE_PAGE-1)))return -1;
 rdn_gart_set_page(s->gart,offset/RDN_STAGE_PAGE,bus);return 0;
}
static int stage_clear(void *p,uint32_t offset)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)p;
 if(!s->gart || !s->gart->ready || (offset&(RDN_STAGE_PAGE-1)))return -1;
 rdn_gart_clear_page(s->gart,offset/RDN_STAGE_PAGE);return 0;
}
static int stage_flush(void *p)
{rdn_gart *gart=((rdn_tiger_sleep_stage *)p)->gart;return gart && gart->ready ? rdn_gart_flush_checked(gart) : -1;}
static void stage_unreserve(void *p,uint32_t offset,uint32_t bytes)
{(void)bytes;rdn_mem_free(((rdn_tiger_sleep_stage *)p)->space,offset);}
/* Defer potentially blocking complete/release until after the caller unlocks. */
static void stage_unpin_deferred(void *p)
{((rdn_tiger_sleep_stage *)p)->release_pending=true;}
static const rdn_stage_ops stage_ops={stage_pin,stage_reserve,stage_bus,stage_set,stage_clear,stage_flush,stage_unreserve,stage_unpin_deferred};

int rdn_tiger_sleep_stage_prepare(rdn_tiger_sleep_stage *s,UInt32 bytes)
{
 if(!s || s->memory || s->prepared || s->stage.phase!=RDN_STAGE_IDLE ||
    !bytes || bytes>RDN_STAGE_MAX || (bytes&(RDN_STAGE_PAGE-1)))return -1;
 s->memory=IOBufferMemoryDescriptor::withOptions(kIODirectionInOut,bytes,RDN_STAGE_PAGE);
 if(!s->memory)return -1;
 s->finished_descriptor=0;
 if(s->memory->prepare()!=kIOReturnSuccess){s->memory->release();s->memory=0;return -1;}
 s->prepared=true;s->size=bytes;s->release_pending=false;return 0;
}
int rdn_tiger_sleep_stage_bind_locked(rdn_tiger_sleep_stage *s,rdn_mem *space,rdn_gart *gart)
{
 if(!s || !space || !gart || !gart->ready || !s->memory || !s->prepared || s->release_pending)return -1;
 s->space=space;s->gart=gart;
 return rdn_stage_bind(&s->stage,s->size,&stage_ops,s);
}
int rdn_tiger_sleep_stage_unbind_locked(rdn_tiger_sleep_stage *s,bool completed_and_synced)
{
 if(!s || !s->space || !s->gart)return -1;
 return rdn_stage_unbind(&s->stage,completed_and_synced,&stage_ops,s);
}
int rdn_tiger_sleep_stage_finish(rdn_tiger_sleep_stage *s)
{
 if(!s || !s->memory || !s->prepared || s->stage.phase!=RDN_STAGE_IDLE)return -1;
 if(s->memory->complete()!=kIOReturnSuccess)return -1;
 s->finished_descriptor=s->memory;
 s->memory->release();s->memory=0;s->prepared=false;s->release_pending=false;
 s->space=0;s->gart=0;s->size=0;return 0;
}
int rdn_tiger_sleep_pair_init(rdn_tiger_sleep_stage_pair *p,rdn_tiger_sleep_stage *data,rdn_tiger_sleep_stage *ib)
{
 if(!p || !data || !ib || data==ib || !data->memory || !ib->memory || data->memory==ib->memory ||
    !data->prepared || !ib->prepared || data->release_pending || ib->release_pending ||
    data->stage.phase!=RDN_STAGE_BOUND || ib->stage.phase!=RDN_STAGE_BOUND)return -1;
 p->data=data;p->ib=ib;p->data_descriptor=data->memory;p->ib_descriptor=ib->memory;return 0;
}
int rdn_tiger_sleep_pair_finished(void *cookie,void *data_descriptor,void *ib_descriptor)
{
 rdn_tiger_sleep_stage_pair *p=(rdn_tiger_sleep_stage_pair *)cookie;
 return p && p->data && p->ib && p->data!=p->ib && p->data_descriptor && p->ib_descriptor &&
  p->data_descriptor!=p->ib_descriptor && data_descriptor==p->data_descriptor && ib_descriptor==p->ib_descriptor &&
  p->data->finished_descriptor==p->data_descriptor && p->ib->finished_descriptor==p->ib_descriptor &&
  !p->data->memory && !p->ib->memory && !p->data->prepared && !p->ib->prepared &&
  !p->data->release_pending && !p->ib->release_pending &&
  p->data->stage.phase==RDN_STAGE_IDLE && p->ib->stage.phase==RDN_STAGE_IDLE;
}
int rdn_tiger_sleep_stage_matches(void *cookie,rdn_stage *stage,rdn_gart *gart)
{
 rdn_tiger_sleep_stage *s=(rdn_tiger_sleep_stage *)cookie;
 return s && gart && gart->ready && &s->stage==stage && s->gart==gart && s->space && s->memory &&
        s->prepared && !s->release_pending && s->stage.phase==RDN_STAGE_BOUND;
}
int rdn_tiger_sleep_stage_unstage_copy_locked(rdn_tiger_sleep_stage *s,rdn_sleep_copy *copy,bool consumed)
{
 if(!s || !copy || !rdn_tiger_sleep_stage_matches(s,&s->stage,s->gart))return -1;
 return rdn_sleep_copy_unstage(copy,&s->stage,consumed,&stage_ops,s);
}
int rdn_tiger_sleep_stage_unstage_pair_locked(rdn_tiger_sleep_stage *s,rdn_tiger_sleep_stage *ib,rdn_sleep_copy *copy,bool consumed)
{
 if(!s || !ib || s==ib || !copy || s->gart!=ib->gart || s->space!=ib->space ||
    !rdn_tiger_sleep_stage_matches(s,&s->stage,s->gart) ||
    !rdn_tiger_sleep_stage_matches(ib,&ib->stage,ib->gart))return -1;
 return rdn_sleep_copy_unstage_pair(copy,&s->stage,&ib->stage,consumed,&stage_ops,s,&stage_ops,ib);
}
