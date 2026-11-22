/* Fake-device integration, never submits to a GPU. MIT */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_sequence_bridge.h"
struct binding {struct rdn_stage stage;struct rdn_gart *gart;int pinned,reserved,mapped,flush_failure;};
struct fixture {struct rdn_sleep_sequence_bridge *bridge;int fence_done,bad,barriers,writes;uint32_t fence;};
static struct fixture *current;
static void *allocate(void *p,size_t n){(void)p;return calloc(1,n);}
static void release_mem(void *p,void *v){(void)p;free(v);}
static uint32_t read_reg(void *p,uint32_t r){(void)p;(void)r;return (!current->bridge->active || current->fence_done)?current->fence:current->fence-1;}
static void write_reg(void *p,uint32_t r,uint32_t v){(void)p;(void)r;(void)v;}
int rdn_ib_try_submit_sleep(struct rdn_accel *a,const struct rdn_quiesce *q,struct rdn_sleep_ib_ticket *t,uint32_t w,uint32_t *f)
{(void)a;(void)q;(void)t;(void)w;(void)f;return -1;}
int rdn_ib_try_submit_sleep_gart(struct rdn_accel *a,const struct rdn_quiesce *q,struct rdn_sleep_gart_ib_ticket *t,
 struct rdn_stage *s,struct rdn_gart *g,int (*matches)(void *,struct rdn_stage *,struct rdn_gart *),void *cookie,uint32_t words,uint32_t *fence)
{assert(q->internal_hold && !t->used && matches(cookie,s,g));assert(words==(current->bridge->sequence.step?13u:25u));t->used=1;*fence=++current->fence;a->fence_emitted=*fence;return 0;}
bool rdn_fence_done(struct rdn_accel *a,uint32_t fence){(void)a;assert(fence==current->fence);return current->fence_done;}
void rdn_hdp_flush(struct rdn_accel *a){(void)a;}
static int barrier(void *p){((struct fixture *)p)->barriers++;return 0;}
static int writer(void *p,const uint32_t *words,uint32_t count)
{struct fixture *f=p;assert(words && count==(f->bridge->sequence.step?13u:25u));f->writes++;return 0;}
static int publish(void *p){(void)p;return 0;}
static int matches(void *p,struct rdn_stage *stage,struct rdn_gart *gart)
{struct binding *b=p;return b && &b->stage==stage && b->gart==gart && b->pinned && b->mapped;}
static int read_page(void *p,void *out,uint32_t n)
{
 struct fixture *f=p;unsigned i;const uint32_t patterns[]={0x13579bdfu,0x2468ace0u,0x89abcdefu};
 uint32_t page=f->bridge->sequence.step-1;assert(page<3 && n==4096);
 for(i=0;i<n;i++)((unsigned char *)out)[i]=(unsigned char)(patterns[page]>>(8*(i&3)));
 if(f->bad)((unsigned char *)out)[17]^=1;return 0;
}
static int pin(void *p,uint32_t n){struct binding *b=p;(void)n;b->pinned=1;return 0;}
static int reserve(void *p,uint32_t n,uint32_t *out){struct binding *b=p;(void)n;b->reserved=1;*out=b->stage.offset;return 0;}
static int bus(void *p,uint32_t off,uint64_t *out){(void)p;*out=0x30000000ull+off;return 0;}
static int set(void *p,uint32_t off,uint64_t a){struct binding *b=p;(void)off;(void)a;b->mapped=1;return 0;}
static int clear(void *p,uint32_t off){struct binding *b=p;(void)off;b->mapped=0;return 0;}
static int flush(void *p){return ((struct binding *)p)->flush_failure?-1:0;}
static void unreserve(void *p,uint32_t off,uint32_t n){struct binding *b=p;(void)off;(void)n;b->reserved=0;}
static void unpin(void *p){((struct binding *)p)->pinned=0;}
static void make_stage(struct binding *b,struct rdn_gart *g,uint32_t offset)
{memset(b,0,sizeof(*b));b->gart=g;b->stage.phase=RDN_STAGE_BOUND;b->stage.bytes=4096;b->stage.offset=offset;b->stage.pages=1;b->pinned=b->reserved=b->mapped=1;}
static void run(int mode)
{
 struct fixture f;struct rdn_sleep_sequence_bridge b;struct rdn_sleep_sequence_env e;
 struct binding data,ib;struct rdn_os os;struct rdn_card card;struct rdn_accel a;
 struct rdn_quiesce q;struct rdn_gart g;struct rdn_mem heap;struct rdn_sleep_guarded owned;
 unsigned char output[4096];uint32_t aperture=0;unsigned step;
 const struct rdn_stage_ops stages={pin,reserve,bus,set,clear,flush,unreserve,unpin};
 memset(&f,0,sizeof(f));memset(&b,0,sizeof(b));memset(&e,0,sizeof(e));memset(&os,0,sizeof(os));
 memset(&card,0,sizeof(card));memset(&a,0,sizeof(a));memset(&q,0,sizeof(q));memset(&g,0,sizeof(g));memset(&owned,0,sizeof(owned));
 f.bridge=&b;current=&f;os.alloc=allocate;os.free=release_mem;os.mmio_read32=read_reg;os.mmio_write32=write_reg;card.os=&os;
 a.card=&card;a.ready=true;a.aperture=&aperture;a.aperture_size=0x10000000;a.vram_size=0x80000000;
 a.submission_gate=&q.phase;q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=7;g.ready=true;g.accel=&a;
 assert(!rdn_mem_init(&heap,&os,0x10000000,0x10000));assert(!rdn_sleep_guarded_acquire(&owned,&heap));
 e.accel=&a;e.quiesce=&q;e.gart=&g;e.owned=&owned;e.data=&data.stage;e.ib=&ib.stage;
 e.matches=matches;e.data_cookie=&data;e.ib_cookie=&ib;e.coherent=1;e.barrier=barrier;e.barrier_cookie=&f;
 e.writer=writer;e.publish=publish;e.writer_cookie=&f;assert(!rdn_sleep_sequence_bridge_begin(&b));
 for(step=0;step<4;step++) {
  make_stage(&data,&g,4096);make_stage(&ib,&g,8192);f.fence_done=0;
  assert(!rdn_sleep_sequence_bridge_start(&b,&e) && q.internal_hold && b.sequence.state==RDN_SEQ_WAITING);
  if(mode==4)assert(rdn_sleep_sequence_bridge_cancel(&b,&owned,&q,&data.stage,&ib.stage,1) && owned.active && q.internal_hold);
  assert(rdn_sleep_sequence_bridge_start(&b,&e) && b.sequence.state==RDN_SEQ_WAITING);
  assert(!rdn_sleep_sequence_bridge_poll(&b,read_page,&f,output));
  if(mode==2){b.runtime.timed_out=1;assert(rdn_sleep_sequence_bridge_poll(&b,read_page,&f,output)==-1);
   assert(b.sequence.state==RDN_SEQ_QUARANTINED && q.internal_hold && data.pinned && ib.pinned && owned.active);
   rdn_mem_fini(&heap);return; /* fake-device cleanup only */}
  f.fence_done=1;f.bad=(mode==1 && step==1);
  if(f.bad)assert(rdn_sleep_sequence_bridge_poll(&b,read_page,&f,output)==-1 && b.sequence.state==RDN_SEQ_CLEANUP);
  else assert(rdn_sleep_sequence_bridge_poll(&b,read_page,&f,output)==1);
  if(mode==3){ib.flush_failure=1;assert(rdn_sleep_sequence_bridge_unstage(&b,&e,&stages,&data,&stages,&ib));
   assert(b.sequence.state==RDN_SEQ_QUARANTINED && q.internal_hold && ib.pinned && owned.active);
   rdn_mem_fini(&heap);return; /* fake-device cleanup only */}
  assert(!rdn_sleep_sequence_bridge_unstage(&b,&e,&stages,&data,&stages,&ib) && !q.internal_hold && !data.pinned && !ib.pinned);
  if(mode==4 && step==0) {
   assert(rdn_sleep_sequence_bridge_cancel(&b,&owned,&q,&data.stage,&ib.stage,0) && owned.active);
   assert(!rdn_sleep_sequence_bridge_cancel(&b,&owned,&q,&data.stage,&ib.stage,1));
   assert(!owned.active && b.sequence.state==RDN_SEQ_FAILED);
   rdn_mem_fini(&heap);return;
  }
  if(f.bad)break;
 }
 assert(rdn_sleep_sequence_bridge_finish(&b,&owned,0) && owned.active);
 assert(!rdn_sleep_sequence_bridge_finish(&b,&owned,1) && !owned.active);
 assert(b.sequence.state==(mode==1?RDN_SEQ_FAILED:RDN_SEQ_PASSED));rdn_mem_fini(&heap);
}
int main(void){run(0);run(1);run(2);run(3);run(4);return 0;}
