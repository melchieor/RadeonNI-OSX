/* Software device model; NEVER executes GPU work. MIT */
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_transaction.h"
#include "rdn_accel_reg.h"
struct machine {uint32_t rptr,fence,aperture[4096],ib[1024],ib_words;unsigned barriers,writes;unsigned char hidden[4096],data[4096];};
struct binding {struct rdn_stage stage;struct rdn_gart *gart;uint32_t offset;int pinned,reserved,mapped;};
static void *alloc_mem(void *p,size_t n){(void)p;return calloc(1,n);}
static void free_mem(void *p,void *v){(void)p;free(v);}
static uint32_t read_reg(void *p,uint32_t r){struct machine *m=p;if(r==CP_RB_RPTR)return m->rptr;if(r==RDN_SCRATCH_REG(1))return m->fence;return 0;}
static void write_reg(void *p,uint32_t r,uint32_t v){struct machine *m=p;(void)r;(void)v;m->writes++;}
void rdn_gpu_init(struct rdn_accel *a){(void)a;}
static int pin(void *p,uint32_t n){struct binding *b=p;assert(n==4096);b->pinned=1;return 0;}
static int reserve(void *p,uint32_t n,uint32_t *o){struct binding *b=p;(void)n;b->reserved=1;*o=b->offset;return 0;}
static int bus(void *p,uint32_t off,uint64_t *a){struct binding *b=p;assert(!off);*a=0x30000000ull+b->offset;return 0;}
static int set(void *p,uint32_t off,uint64_t addr){struct binding *b=p;assert(off==b->offset && addr==0x30000000ull+off);b->mapped=1;return 0;}
static int clear(void *p,uint32_t off){struct binding *b=p;assert(off==b->offset);b->mapped=0;return 0;}
static int flush(void *p){(void)p;return 0;}
static void unreserve(void *p,uint32_t off,uint32_t n){struct binding *b=p;(void)off;(void)n;b->reserved=0;}
static void unpin(void *p){((struct binding *)p)->pinned=0;}
static int matches(void *p,struct rdn_stage *s,struct rdn_gart *g){struct binding *b=p;return &b->stage==s && b->gart==g && b->pinned && b->mapped;}
static int ib_write(void *p,const uint32_t *words,uint32_t n){struct machine *m=p;assert(n==13);memcpy(m->ib,words,n*4);m->ib_words=n;return 0;}
static int barrier(void *p){((struct machine *)p)->barriers++;return 0;}
static int publish_ib(void *p){(void)p;return 0;}
static void run(int timeout)
{
 struct machine m;struct binding data,ib;struct rdn_os os;struct rdn_card card;struct rdn_accel a;
 struct rdn_mem hidden,commands;struct rdn_sleep_private private;struct rdn_quiesce q;
 struct rdn_gart g;struct rdn_sleep_gart_transaction tx;unsigned i;
 const struct rdn_stage_ops stages={pin,reserve,bus,set,clear,flush,unreserve,unpin};
 memset(&m,0,sizeof(m));memset(&data,0,sizeof(data));memset(&ib,0,sizeof(ib));memset(&os,0,sizeof(os));
 memset(&card,0,sizeof(card));memset(&a,0,sizeof(a));memset(&private,0,sizeof(private));memset(&q,0,sizeof(q));
 memset(&g,0,sizeof(g));memset(&tx,0,sizeof(tx));
 os.cookie=&m;os.alloc=alloc_mem;os.free=free_mem;os.mmio_read32=read_reg;os.mmio_write32=write_reg;card.os=&os;
 a.card=&card;a.ready=true;a.aperture=m.aperture;a.aperture_size=sizeof(m.aperture);a.vram_size=0x80000000;
 a.ring_offset=0;a.ring_words=128;a.fence_offset=4096;a.fence_emitted=m.fence=0x1234;a.submission_gate=&q.phase;
 q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=5;g.ready=true;g.accel=&a;
 data.gart=&g;data.offset=4096;ib.gart=&g;ib.offset=8192;
 assert(!rdn_mem_init(&hidden,&os,0x10000000,0x20000));assert(!rdn_mem_init(&commands,&os,8192,4096));
 assert(!rdn_sleep_private_acquire(&private,&hidden,&commands));
 assert(!rdn_stage_bind(&data.stage,4096,&stages,&data));assert(!rdn_stage_bind(&ib.stage,4096,&stages,&ib));
 for(i=0;i<4096;i++)m.hidden[i]=(unsigned char)(i^(i>>4));
 assert(!rdn_sleep_gart_transaction_start(&tx,&private,&a,&q,&data.stage,&ib.stage,&g,matches,&data,&ib,1,barrier,&m,ib_write,publish_ib,&m));
 assert(q.internal_hold && tx.ticket.used && m.ib_words==13 && m.ib[6]==0x10000000 && m.ib[8]==0x80001000);
 assert(rdn_ib_try_submit(&a,0x1000,1,0)<0); /* application gate remains closed */
 assert(!rdn_sleep_copy_poll(&tx.copy,&rdn_sleep_runtime_ops,&tx.runtime));
 if(timeout) {
  tx.runtime.timed_out=1;assert(rdn_sleep_copy_poll(&tx.copy,&rdn_sleep_runtime_ops,&tx.runtime)==-1);
  rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(q.internal_hold && q.phase==RDN_QUIESCE_HELD_POWERED);
  assert(data.pinned && ib.pinned && data.reserved && ib.reserved && private.active);
  /* Fake-model cleanup only; real timed-out resources remain retained. */
  rdn_mem_fini(&hidden);rdn_mem_fini(&commands);return;
 }
 /* The following memcpy and fence are the simulated GPU, not the driver. */
 memcpy(m.data,m.hidden,sizeof(m.data));m.fence=tx.runtime.sequence;
 assert(rdn_sleep_copy_poll(&tx.copy,&rdn_sleep_runtime_ops,&tx.runtime)==1 && m.barriers==1);
 assert(!memcmp(m.data,m.hidden,sizeof(m.data)));
 assert(!rdn_sleep_copy_unstage_pair(&tx.copy,&data.stage,&ib.stage,1,&stages,&data,&stages,&ib));
 assert(!data.pinned && !ib.pinned && !q.internal_hold);
 assert(!rdn_sleep_private_release(&private,1));rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);
 assert(q.phase==RDN_QUIESCE_RUNNING);rdn_mem_fini(&hidden);rdn_mem_fini(&commands);
}
int main(void){run(0);run(1);return 0;}
