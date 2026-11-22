/* Isolated prototype. No client entry point and no default driver build. */
#include "rdn_sleep_transaction.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
int rdn_sleep_transaction_start(struct rdn_sleep_transaction *t,struct rdn_sleep_private *p,
 struct rdn_accel *a,struct rdn_quiesce *q,struct rdn_stage *s,struct rdn_gart *g,
 int (*stage_matches)(void *,struct rdn_stage *,struct rdn_gart *),void *stage_cookie,
 int coherent,int (*barrier)(void *),void *barrier_cookie,
 int (*writer)(void *,uint32_t,const uint32_t *,uint32_t),void *writer_cookie)
{
 struct rdn_sleep_dma_commands cmd;
 uint64_t begin,end,ring_end,fence_end,gart_base,staging;
 uint64_t hidden_offset,command_offset; uint32_t generation,stage_offset;
 struct rdn_mem *hidden_heap,*command_heap;
 if(!t || !p || !a || !q || !s || !g || !stage_matches || !writer || !barrier || !coherent ||
    t->started || t->copy.stage || t->copy.transfer.phase!=RDN_TRANSFER_IDLE ||
    !p->active || !a->ready || !a->aperture || a->submission_gate!=&q->phase ||
    q->phase!=RDN_QUIESCE_HELD_POWERED || !q->generation || q->internal_hold ||
    !g->ready || g->accel!=a || s->phase!=RDN_STAGE_BOUND || s->bytes!=4096 ||
    s->pages!=1 || !s->offset || (s->offset&4095) || p->command_offset>UINT32_MAX ||
    a->vram_base>=(1ull<<40) || !a->vram_size || a->vram_size>(1ull<<40)-a->vram_base ||
    a->ring_offset>a->aperture_size || a->ring_words>(a->aperture_size-a->ring_offset)/4 ||
    a->fence_offset>a->aperture_size || a->aperture_size-a->fence_offset<4 ||
    p->command_offset>a->aperture_size || 4096>a->aperture_size-p->command_offset ||
    !stage_matches(stage_cookie,s,g))return -1;
 begin=p->command_offset;end=begin+4096;
 ring_end=(uint64_t)a->ring_offset+(uint64_t)a->ring_words*4;fence_end=(uint64_t)a->fence_offset+4;
 if((begin<ring_end && a->ring_offset<end) || (begin<fence_end && a->fence_offset<end))return -1;
 gart_base=rdn_gart_gpu_start(a);
 if(gart_base>=(1ull<<40) || s->offset>(1ull<<40)-gart_base)return -1;
 staging=gart_base+s->offset;
 if(rdn_sleep_private_build(p,a->vram_base,a->vram_size,a->aperture_size,staging,s->bytes,&cmd))return -1;
 generation=q->generation;stage_offset=s->offset;
 hidden_heap=p->hidden;command_heap=p->commands;hidden_offset=p->hidden_offset;command_offset=p->command_offset;
 if(writer(writer_cookie,(uint32_t)begin,cmd.words,cmd.word_count))return -1;
 /* The writer is a callback: never publish commands using stale resources. */
 if(q->phase!=RDN_QUIESCE_HELD_POWERED || q->generation!=generation || q->internal_hold ||
    !a->ready || a->submission_gate!=&q->phase || !g->ready || g->accel!=a ||
    s->phase!=RDN_STAGE_BOUND || s->offset!=stage_offset || s->bytes!=4096 || s->pages!=1 ||
    !stage_matches(stage_cookie,s,g) || !p->active || p->hidden!=hidden_heap || p->commands!=command_heap ||
    p->hidden_offset!=hidden_offset || p->command_offset!=command_offset ||
    rdn_mem_allocation_size(hidden_heap,hidden_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(command_heap,command_offset)!=RDN_SLEEP_PRIVATE_PAGE)return -1;
 t->ticket.generation=q->generation;t->ticket.offset=(uint32_t)begin;t->ticket.bytes=4096;t->ticket.used=0;
 t->runtime.accel=a;t->runtime.quiesce=q;t->runtime.stage=s;t->runtime.ticket=&t->ticket;
 t->runtime.words=cmd.word_count;t->runtime.coherency_verified=coherent;
 t->runtime.cpu_read_barrier=barrier;t->runtime.barrier_cookie=barrier_cookie;
 t->started=1;
 return rdn_sleep_copy_start_staged(&t->copy,q,s,&rdn_sleep_runtime_ops,&t->runtime);
}
int rdn_sleep_gart_transaction_start(struct rdn_sleep_gart_transaction *t,struct rdn_sleep_private *p,
 struct rdn_accel *a,struct rdn_quiesce *q,struct rdn_stage *data,struct rdn_stage *ib,struct rdn_gart *g,
 int (*matches)(void *,struct rdn_stage *,struct rdn_gart *),void *data_cookie,void *ib_cookie,
 int coherent,int (*barrier)(void *),void *barrier_cookie,
 int (*writer)(void *,const uint32_t *,uint32_t),int (*publish_ib)(void *),void *writer_cookie)
{
 struct rdn_sleep_dma_commands cmd;uint64_t base,dst,command,hidden_offset,command_offset;
 struct rdn_mem *hidden_heap,*command_heap;uint32_t generation,data_offset,ib_offset;
 if(!t || !p || !a || !q || !data || !ib || data==ib || !g || !matches || !writer || !publish_ib || !barrier || !coherent ||
    t->started || t->copy.stage || t->copy.transfer.phase!=RDN_TRANSFER_IDLE || !p->active ||
    !a->ready || !a->aperture || a->submission_gate!=&q->phase || q->phase!=RDN_QUIESCE_HELD_POWERED ||
    !q->generation || q->internal_hold || !g->ready || g->accel!=a ||
    data->phase!=RDN_STAGE_BOUND || ib->phase!=RDN_STAGE_BOUND || data->bytes!=4096 || ib->bytes!=4096 ||
    data->pages!=1 || ib->pages!=1 || !data->offset || !ib->offset ||
    (data->offset&4095) || (ib->offset&4095) || data->offset==ib->offset ||
    a->vram_base>=(1ull<<40) || !a->vram_size || a->vram_size>(1ull<<40)-a->vram_base ||
    !matches(data_cookie,data,g) || !matches(ib_cookie,ib,g))return -1;
 base=rdn_gart_gpu_start(a);
 if(base>=(1ull<<40) || data->offset>(1ull<<40)-base || ib->offset>(1ull<<40)-base)return -1;
 dst=base+data->offset;command=base+ib->offset;
 if(rdn_sleep_private_build_gart_ib(p,a->vram_base,a->vram_size,a->aperture_size,dst,data->bytes,command,&cmd))return -1;
 generation=q->generation;data_offset=data->offset;ib_offset=ib->offset;
 hidden_heap=p->hidden;command_heap=p->commands;hidden_offset=p->hidden_offset;command_offset=p->command_offset;
 if(writer(writer_cookie,cmd.words,cmd.word_count) || publish_ib(writer_cookie))return -1;
 if(q->phase!=RDN_QUIESCE_HELD_POWERED || q->generation!=generation || q->internal_hold ||
    !g->ready || g->accel!=a || !matches(data_cookie,data,g) || !matches(ib_cookie,ib,g) ||
    data->phase!=RDN_STAGE_BOUND || ib->phase!=RDN_STAGE_BOUND || data->offset!=data_offset || ib->offset!=ib_offset ||
    data->bytes!=4096 || ib->bytes!=4096 || data->pages!=1 || ib->pages!=1 ||
    !p->active || p->hidden!=hidden_heap || p->commands!=command_heap ||
    p->hidden_offset!=hidden_offset || p->command_offset!=command_offset ||
    rdn_mem_allocation_size(hidden_heap,hidden_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(command_heap,command_offset)!=RDN_SLEEP_PRIVATE_PAGE)return -1;
 t->ticket.generation=q->generation;t->ticket.used=0;
 t->runtime.accel=a;t->runtime.quiesce=q;t->runtime.stage=data;t->runtime.gart_ticket=&t->ticket;
 t->runtime.command_stage=ib;t->runtime.copy=&t->copy;t->runtime.gart=g;t->runtime.stage_matches=matches;t->runtime.stage_cookie=ib_cookie;
 t->runtime.data_stage_cookie=data_cookie;
 t->runtime.use_gart_ib=1;t->runtime.words=cmd.word_count;t->runtime.coherency_verified=coherent;
 t->runtime.cpu_read_barrier=barrier;t->runtime.barrier_cookie=barrier_cookie;t->started=1;
 return rdn_sleep_copy_start_staged_pair(&t->copy,q,data,ib,&rdn_sleep_runtime_ops,&t->runtime);
}
#endif
