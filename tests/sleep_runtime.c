#include <assert.h>
#include <string.h>
#include "rdn_sleep_runtime.h"
static int submitted,completed,flushes,barriers,barrier_failure,submit_failure,reads;
static uint32_t fake_fence;
static int inaccessible;
static uint32_t fake_read(void *p,uint32_t reg){(void)p;(void)reg;++reads;return inaccessible?UINT32_MAX:(completed?fake_fence:fake_fence-1);}
static void fake_write(void *p,uint32_t reg,uint32_t value){(void)p;(void)reg;(void)value;}
int rdn_ib_try_submit_sleep(struct rdn_accel *a,const struct rdn_quiesce *q,
 struct rdn_sleep_ib_ticket *t,uint32_t words,uint32_t *seq)
{assert(q->internal_hold==1 && words==4 && !t->used);if(submit_failure)return -1;submitted++;t->used=1;*seq=fake_fence;a->fence_emitted=*seq;return 0;}
int rdn_ib_try_submit_sleep_gart(struct rdn_accel *a,const struct rdn_quiesce *q,
 struct rdn_sleep_gart_ib_ticket *t,struct rdn_stage *s,struct rdn_gart *g,
 int (*matches)(void *,struct rdn_stage *,struct rdn_gart *),void *cookie,uint32_t words,uint32_t *seq)
{assert(q->internal_hold && words==4 && !t->used && s && g && matches && cookie==s);if(submit_failure)return -1;submitted++;t->used=1;*seq=fake_fence;a->fence_emitted=*seq;return 0;}
static int stage_match(void *p,struct rdn_stage *s,struct rdn_gart *g){return p==s && g!=0;}
bool rdn_fence_done(struct rdn_accel *a,uint32_t seq){(void)a;assert(seq==fake_fence);return completed;}
void rdn_hdp_flush(struct rdn_accel *a){(void)a;++flushes;}
static int barrier(void *cookie){(void)cookie;++barriers;return barrier_failure?-1:0;}
int main(void)
{
 struct rdn_accel a;struct rdn_card card;struct rdn_os os;struct rdn_quiesce q;struct rdn_stage stage,ibstage;struct rdn_gart *fake_gart;
 struct rdn_sleep_ib_ticket ticket;struct rdn_sleep_runtime r;struct rdn_sleep_copy copy;
 struct rdn_sleep_gart_ib_ticket gticket;
 uint32_t inaccessible_vram=UINT32_MAX;
#define RESET() do{memset(&a,0,sizeof(a));memset(&card,0,sizeof(card));memset(&os,0,sizeof(os));memset(&q,0,sizeof(q));memset(&stage,0,sizeof(stage));memset(&ticket,0,sizeof(ticket));memset(&r,0,sizeof(r));memset(&copy,0,sizeof(copy));submitted=completed=flushes=barriers=barrier_failure=submit_failure=inaccessible=reads=0;fake_fence=42;q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=4;os.mmio_read32=fake_read;os.mmio_write32=fake_write;card.os=&os;a.card=&card;a.ready=true;a.fence_emitted=41;a.submission_gate=&q.phase;stage.phase=RDN_STAGE_BOUND;ticket.generation=4;r.accel=&a;r.quiesce=&q;r.stage=&stage;r.ticket=&ticket;r.words=4;r.cpu_read_barrier=barrier;}while(0)
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));
 assert(submitted==1 && !rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r) && !flushes);
 completed=1;r.coherency_verified=1;assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==1 && flushes==1 && barriers==1);
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));completed=1;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && !flushes && copy.transfer.phase==RDN_TRANSFER_QUARANTINED && q.internal_hold);
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));r.timed_out=1;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && !flushes && q.internal_hold);
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));
 r.timed_out=1;completed=1;r.coherency_verified=1;
 assert(reads==1 && rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && reads==1 && !flushes && !barriers &&
        q.internal_hold && copy.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();fake_fence=0x80000001u;a.fence_emitted=fake_fence-1;assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));inaccessible=1;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && !flushes && q.internal_hold && copy.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();fake_fence=0x80000001u;a.fence_emitted=fake_fence-1;a.fence_memory=true;inaccessible_vram=fake_fence-1;a.aperture=&inaccessible_vram;a.aperture_size=4;
 assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));
 inaccessible_vram=UINT32_MAX;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && !flushes && q.internal_hold && copy.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));completed=1;r.coherency_verified=1;barrier_failure=1;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && flushes==1 && barriers==1 && q.internal_hold);
 RESET();submit_failure=1;assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !q.internal_hold && !submitted);
 RESET();inaccessible=1;assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !q.internal_hold && !submitted);
 RESET();a.fence_emitted=40;assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !q.internal_hold && !submitted);
 RESET();a.fence_emitted=UINT32_MAX-1u;assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !q.internal_hold && !submitted);
 RESET();a.fence_memory=true;assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !q.internal_hold && !submitted);
 RESET();assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r));a.card=0;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && q.internal_hold && !flushes);
 RESET();memset(&ibstage,0,sizeof(ibstage));memset(&gticket,0,sizeof(gticket));ibstage.phase=RDN_STAGE_BOUND;gticket.generation=4;
 fake_gart=(struct rdn_gart *)&a;r.use_gart_ib=1;r.gart_ticket=&gticket;r.command_stage=&ibstage;r.copy=&copy;r.gart=fake_gart;r.stage_matches=stage_match;r.stage_cookie=&ibstage;r.data_stage_cookie=&stage;
 assert(!rdn_sleep_copy_start_staged_pair(&copy,&q,&stage,&ibstage,&rdn_sleep_runtime_ops,&r) && gticket.used && submitted);
 completed=1;r.coherency_verified=1;assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==1 && barriers==1);
 RESET();memset(&ibstage,0,sizeof(ibstage));memset(&gticket,0,sizeof(gticket));ibstage.phase=RDN_STAGE_BOUND;gticket.generation=4;
 r.use_gart_ib=1;r.gart_ticket=&gticket;r.command_stage=&ibstage;r.copy=&copy;r.gart=fake_gart;r.stage_matches=stage_match;r.stage_cookie=&ibstage;r.data_stage_cookie=&stage;
 assert(!rdn_sleep_copy_start_staged_pair(&copy,&q,&stage,&ibstage,&rdn_sleep_runtime_ops,&r));ibstage.phase=RDN_STAGE_IDLE;
 assert(rdn_sleep_copy_poll(&copy,&rdn_sleep_runtime_ops,&r)==-1 && q.internal_hold && copy.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();r.use_gart_ib=1;r.gart_ticket=&gticket;r.command_stage=&stage;r.gart=fake_gart;r.stage_matches=stage_match;r.stage_cookie=&stage;
 assert(rdn_sleep_copy_start_staged(&copy,&q,&stage,&rdn_sleep_runtime_ops,&r) && !submitted && !q.internal_hold);
 return 0;
}
