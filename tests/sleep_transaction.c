#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_transaction.h"
static int writes,submits,done,flushes,barriers,writer_failure;
static int publish_failure;static struct rdn_stage *mutate_stage;
static struct rdn_quiesce *mutate_generation;
static void *alloc_mem(void *p,size_t n){(void)p;return calloc(1,n);}
static void free_mem(void *p,void *v){(void)p;free(v);}
static uint32_t read_reg(void *p,uint32_t r){(void)p;(void)r;return done?22:21;}
static void write_reg(void *p,uint32_t r,uint32_t v){(void)p;(void)r;(void)v;}
int rdn_ib_try_submit_sleep(struct rdn_accel *a,const struct rdn_quiesce *q,struct rdn_sleep_ib_ticket *t,uint32_t w,uint32_t *seq)
{(void)a;assert(q->internal_hold && w==13 && !t->used);t->used=1;*seq=22;submits++;return 0;}
int rdn_ib_try_submit_sleep_gart(struct rdn_accel *a,const struct rdn_quiesce *q,struct rdn_sleep_gart_ib_ticket *t,struct rdn_stage *s,struct rdn_gart *g,int (*m)(void *,struct rdn_stage *,struct rdn_gart *),void *c,uint32_t w,uint32_t *seq)
{(void)a;assert(q->internal_hold && w==13 && !t->used && m(c,s,g));t->used=1;*seq=22;submits++;return 0;}
bool rdn_fence_done(struct rdn_accel *a,uint32_t seq){(void)a;assert(seq==22);return done;}
void rdn_hdp_flush(struct rdn_accel *a){(void)a;flushes++;}
static int barrier(void *p){(void)p;barriers++;return 0;}
static int stage_matches(void *p,struct rdn_stage *s,struct rdn_gart *g){return p==s && g->ready;}
static int writer(void *p,uint32_t off,const uint32_t *words,uint32_t count)
{(void)p;assert(off==0x20000 && count==13 && words[6]==0x10000000 && words[8]==0x80001000);writes++;if(mutate_stage)mutate_stage->offset+=4096;if(mutate_generation)mutate_generation->generation++;return writer_failure;}
static int writer_gart(void *p,const uint32_t *words,uint32_t count)
{(void)p;assert(count==13 && words[6]==0x10000000 && words[8]==0x80001000);writes++;return 0;}
static int publish_ib(void *p){(void)p;if(mutate_stage)mutate_stage->offset+=4096;return publish_failure?-1:0;}
int main(void)
{
 struct rdn_os os={0};struct rdn_card card={0};struct rdn_accel a={0};
 struct rdn_mem hidden,commands;struct rdn_sleep_private p={0};struct rdn_quiesce q={0};
 struct rdn_stage s={0};struct rdn_gart g={0};struct rdn_sleep_transaction t={0};uint32_t aperture=0;
 os.alloc=alloc_mem;os.free=free_mem;os.mmio_read32=read_reg;os.mmio_write32=write_reg;card.os=&os;
 a.card=&card;a.ready=true;a.aperture=&aperture;a.aperture_size=0x10000000;a.vram_size=0x80000000;
 a.ring_offset=0x1000;a.ring_words=256;a.fence_offset=0x2000;a.fence_emitted=21;a.submission_gate=&q.phase;
 q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=3;g.ready=true;g.accel=&a;
 s.phase=RDN_STAGE_BOUND;s.offset=4096;s.bytes=4096;s.pages=1;
 assert(!rdn_mem_init(&hidden,&os,0x10000000,0x20000));assert(!rdn_mem_init(&commands,&os,0x20000,0x20000));
 assert(!rdn_sleep_private_acquire(&p,&hidden,&commands));
 assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,0,barrier,0,writer,0) && !writes && !submits);
 assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,0,1,barrier,0,writer,0) && !writes);
 a.ring_offset=0x20000;assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,1,barrier,0,writer,0) && !writes);a.ring_offset=0x1000;
 writer_failure=1;assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,1,barrier,0,writer,0) && !submits && !q.internal_hold);
 writer_failure=0;mutate_stage=&s;
 assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,1,barrier,0,writer,0) && !submits && !q.internal_hold && !t.started);
 mutate_stage=0;s.offset=4096;
 mutate_generation=&q;
 assert(rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,1,barrier,0,writer,0) && !submits && !q.internal_hold && !t.started);
 mutate_generation=0;
 assert(!rdn_sleep_transaction_start(&t,&p,&a,&q,&s,&g,stage_matches,&s,1,barrier,0,writer,0) && writes==4 && submits==1 && q.internal_hold);
 assert(!rdn_sleep_copy_poll(&t.copy,&rdn_sleep_runtime_ops,&t.runtime) && !flushes);
 done=1;assert(rdn_sleep_copy_poll(&t.copy,&rdn_sleep_runtime_ops,&t.runtime)==1 && flushes==1 && barriers==1);
 assert(rdn_sleep_copy_release(&t.copy) && q.internal_hold); /* Stage still bound. */
 /* Fresh simulated run only: real cleanup must retain both stages. */
 assert(!rdn_quiesce_release_internal(&q,q.generation));
 {
  struct rdn_sleep_gart_transaction gt={0};struct rdn_stage ib={RDN_STAGE_BOUND,4096,8192,1};
  done=0;
  assert(rdn_sleep_gart_transaction_start(&gt,&p,&a,&q,&s,&s,&g,stage_matches,&s,&s,1,barrier,0,writer_gart,publish_ib,0));
  publish_failure=1;assert(rdn_sleep_gart_transaction_start(&gt,&p,&a,&q,&s,&ib,&g,stage_matches,&s,&ib,1,barrier,0,writer_gart,publish_ib,0) && !q.internal_hold && submits==1);
  publish_failure=0;mutate_stage=&ib;
  assert(rdn_sleep_gart_transaction_start(&gt,&p,&a,&q,&s,&ib,&g,stage_matches,&s,&ib,1,barrier,0,writer_gart,publish_ib,0) && !q.internal_hold && submits==1);
  mutate_stage=0;ib.offset=8192;
  assert(!rdn_sleep_gart_transaction_start(&gt,&p,&a,&q,&s,&ib,&g,stage_matches,&s,&ib,1,barrier,0,writer_gart,publish_ib,0));
  assert(q.internal_hold && gt.copy.stage==&s && gt.copy.extra_stage==&ib);
  done=1;assert(rdn_sleep_copy_poll(&gt.copy,&rdn_sleep_runtime_ops,&gt.runtime)==1);
  assert(rdn_sleep_copy_release(&gt.copy) && q.internal_hold);
  assert(!rdn_quiesce_release_internal(&q,q.generation)); /* Simulation cleanup only. */
 }
 assert(!rdn_sleep_private_release(&p,1));
 rdn_mem_fini(&hidden);rdn_mem_fini(&commands);return 0;
}
