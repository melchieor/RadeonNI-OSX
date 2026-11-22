/* Incomplete experiment: no production caller, no hardware validation. */
#include "rdn_sleep_sequence_bridge.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <string.h>
#endif
static void quarantine(struct rdn_sleep_sequence_bridge *b)
{b->sequence.failure=1;b->sequence.state=RDN_SEQ_QUARANTINED;}
int rdn_sleep_sequence_bridge_begin(struct rdn_sleep_sequence_bridge *b)
{
 if(!b || b->active || b->sequence.state!=RDN_SEQ_NEW)return -1;
 return rdn_sleep_sequence_begin(&b->sequence);
}
int rdn_sleep_sequence_bridge_start(struct rdn_sleep_sequence_bridge *b,struct rdn_sleep_sequence_env *e)
{
 struct rdn_sleep_sequence_commands cmd;uint64_t base,dst,ib,owned_offset,vram_base,vram_size;
 uint32_t generation,data_offset,ib_offset,aperture_size;struct rdn_mem *owned_heap;
 struct rdn_sleep_guarded *owned;struct rdn_accel *accel;struct rdn_gart *gart;
 struct rdn_quiesce *quiesce;struct rdn_stage *data,*ib_stage;
 int result;
 if(!b || !e || b->active || (b->owned && b->owned!=e->owned) || b->sequence.state!=RDN_SEQ_READY || b->sequence.built ||
    b->sequence.generation==UINT32_MAX || !e->accel || !e->quiesce || !e->gart || !e->owned ||
    !e->data || !e->ib || e->data==e->ib || !e->matches || !e->coherent || !e->barrier || !e->writer || !e->publish ||
    !e->accel->ready || !e->accel->aperture || e->accel->submission_gate!=&e->quiesce->phase ||
    e->quiesce->phase!=RDN_QUIESCE_HELD_POWERED || !e->quiesce->generation || e->quiesce->internal_hold ||
    !e->gart->ready || e->gart->accel!=e->accel || e->data->phase!=RDN_STAGE_BOUND || e->ib->phase!=RDN_STAGE_BOUND ||
    e->data->bytes!=4096 || e->ib->bytes!=4096 || e->data->pages!=1 || e->ib->pages!=1 ||
    !e->data->offset || !e->ib->offset || (e->data->offset&4095) || (e->ib->offset&4095) || e->data->offset==e->ib->offset ||
    e->accel->vram_base>=(1ull<<40) || !e->accel->vram_size || e->accel->vram_size>(1ull<<40)-e->accel->vram_base ||
    !e->matches(e->data_cookie,e->data,e->gart) || !e->matches(e->ib_cookie,e->ib,e->gart))return -1;
 base=rdn_gart_gpu_start(e->accel);
 if(base>=(1ull<<40) || e->data->offset>(1ull<<40)-base || e->ib->offset>(1ull<<40)-base)return -1;
 dst=base+e->data->offset;ib=base+e->ib->offset;
 if(rdn_sleep_sequence_build(&b->sequence,e->owned,e->accel->vram_base,e->accel->vram_size,
      e->accel->aperture_size,dst,ib,&cmd))return -1;
 generation=e->quiesce->generation;data_offset=e->data->offset;ib_offset=e->ib->offset;
 owned=e->owned;owned_heap=owned->heap;owned_offset=owned->offset;accel=e->accel;gart=e->gart;
 quiesce=e->quiesce;data=e->data;ib_stage=e->ib;vram_base=accel->vram_base;
 vram_size=accel->vram_size;aperture_size=accel->aperture_size;
 if(e->writer(e->writer_cookie,cmd.words,cmd.word_count) || e->publish(e->writer_cookie)) {
  rdn_sleep_sequence_discard(&b->sequence);return -1;
 }
 if(e->owned!=owned || e->accel!=accel || e->gart!=gart || e->quiesce!=quiesce || e->data!=data || e->ib!=ib_stage ||
    accel->vram_base!=vram_base || accel->vram_size!=vram_size || accel->aperture_size!=aperture_size ||
    e->quiesce->phase!=RDN_QUIESCE_HELD_POWERED || e->quiesce->generation!=generation || e->quiesce->internal_hold ||
    !e->gart->ready || e->gart->accel!=e->accel || e->data->offset!=data_offset || e->ib->offset!=ib_offset ||
    e->data->phase!=RDN_STAGE_BOUND || e->ib->phase!=RDN_STAGE_BOUND ||
    !e->matches(e->data_cookie,e->data,e->gart) || !e->matches(e->ib_cookie,e->ib,e->gart) ||
    !owned->active || owned->heap!=owned_heap || owned->offset!=owned_offset || !owned_heap ||
    rdn_mem_allocation_size(owned_heap,owned_offset)!=3u*4096u) {
  rdn_sleep_sequence_discard(&b->sequence);return -1;
 }
 memset(&b->runtime,0,sizeof(b->runtime));memset(&b->ticket,0,sizeof(b->ticket));
 b->ticket.generation=generation;b->runtime.accel=e->accel;b->runtime.quiesce=e->quiesce;
 b->runtime.stage=e->data;b->runtime.command_stage=e->ib;b->runtime.copy=&b->copy;b->runtime.gart=e->gart;
 b->runtime.gart_ticket=&b->ticket;b->runtime.stage_matches=e->matches;b->runtime.stage_cookie=e->ib_cookie;
 b->runtime.data_stage_cookie=e->data_cookie;b->runtime.use_gart_ib=1;b->runtime.words=cmd.word_count;
 b->runtime.coherency_verified=e->coherent;b->runtime.cpu_read_barrier=e->barrier;b->runtime.barrier_cookie=e->barrier_cookie;
 result=rdn_sleep_copy_start_staged_pair(&b->copy,e->quiesce,e->data,e->ib,&rdn_sleep_runtime_ops,&b->runtime);
 if(result){if(b->copy.transfer.phase==RDN_TRANSFER_IDLE)rdn_sleep_sequence_discard(&b->sequence);else {b->owned=owned;quarantine(b);}return -1;}
 b->owned=owned;b->active=1;
 if(rdn_sleep_sequence_submitted(&b->sequence,&b->token)){quarantine(b);return -1;}
 return 0;
}
int rdn_sleep_sequence_bridge_poll(struct rdn_sleep_sequence_bridge *b,int (*read)(void *,void *,uint32_t),void *cookie,void *buffer)
{
 int result;
 if(!b || !b->active || b->sequence.state!=RDN_SEQ_WAITING)return -1;
 result=rdn_sleep_copy_poll(&b->copy,&rdn_sleep_runtime_ops,&b->runtime);
 if(!result)return 0;
 if(result<0){rdn_sleep_sequence_uncertain(&b->sequence,b->token);return -1;}
 if(b->sequence.step==RDN_SEQ_FILL)
  return rdn_sleep_sequence_complete(&b->sequence,b->token,1,0,0)?-1:1;
 if(!read || !buffer || read(cookie,buffer,4096)) {quarantine(b);return -1;}
 return rdn_sleep_sequence_complete(&b->sequence,b->token,1,buffer,4096)?-1:1;
}
int rdn_sleep_sequence_bridge_unstage(struct rdn_sleep_sequence_bridge *b,struct rdn_sleep_sequence_env *e,
 const struct rdn_stage_ops *data_ops,void *data_cookie,const struct rdn_stage_ops *ib_ops,void *ib_cookie)
{
 if(!b || !e || b->owned!=e->owned || !b->active || (b->sequence.state!=RDN_SEQ_READY && b->sequence.state!=RDN_SEQ_CLEANUP) ||
    b->copy.transfer.phase!=RDN_TRANSFER_READY || b->copy.stage!=e->data || b->copy.extra_stage!=e->ib)return -1;
 if(rdn_sleep_copy_unstage_pair(&b->copy,e->data,e->ib,1,data_ops,data_cookie,ib_ops,ib_cookie)){quarantine(b);return -1;}
 b->active=0;return 0;
}
int rdn_sleep_sequence_bridge_finish(struct rdn_sleep_sequence_bridge *b,struct rdn_sleep_guarded *owned,int descriptors_released)
{
 if(!b || !owned || b->owned!=owned || b->active || b->sequence.state!=RDN_SEQ_CLEANUP || !descriptors_released)return -1;
 if(rdn_sleep_guarded_release(owned,1)){quarantine(b);return -1;}
 return rdn_sleep_sequence_cleanup(&b->sequence,1);
}
int rdn_sleep_sequence_bridge_cancel(struct rdn_sleep_sequence_bridge *b,struct rdn_sleep_guarded *owned,
 struct rdn_quiesce *q,struct rdn_stage *data,struct rdn_stage *ib,int descriptors_released)
{
 if(!b || !owned || b->owned!=owned || !owned->active || !q || !data || !ib || data==ib ||
    !descriptors_released || b->active || b->sequence.state!=RDN_SEQ_READY || b->sequence.built ||
    b->copy.transfer.phase!=RDN_TRANSFER_IDLE || b->copy.stage || b->copy.extra_stage ||
    q->phase!=RDN_QUIESCE_HELD_POWERED || q->internal_hold ||
    data->phase!=RDN_STAGE_IDLE || ib->phase!=RDN_STAGE_IDLE)return -1;
 b->sequence.failure=1;b->sequence.state=RDN_SEQ_CLEANUP;
 return rdn_sleep_sequence_bridge_finish(b,owned,descriptors_released);
}
#endif
