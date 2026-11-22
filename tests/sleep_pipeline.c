/* Simulated device: exercises production staging, DMA builder and coordinator. */
#include <assert.h>
#include <string.h>
#include "rdn_sleep_staging.h"
#include "rdn_sleep_copy.h"
#include "rdn_sleep_dma.h"
struct fixture {unsigned pinned,reserved,mapped,flushes,fail_flush,done,synced;
 unsigned char hidden[4096],staging[4096],image[4096];};
static int pin(void *p,uint32_t n){struct fixture *f=p;assert(n==4096);f->pinned=1;return 0;}
static int reserve(void *p,uint32_t n,uint32_t *offset){struct fixture *f=p;(void)n;f->reserved=1;*offset=4096;return 0;}
static int bus(void *p,uint32_t at,uint64_t *address){(void)p;assert(!at);*address=0x30000000;return 0;}
static int set(void *p,uint32_t off,uint64_t addr){struct fixture *f=p;assert(off==4096 && addr==0x30000000);f->mapped=1;return 0;}
static int clear(void *p,uint32_t off){struct fixture *f=p;assert(off==4096 || off==8192);f->mapped=0;return 0;}
static int flush(void *p){struct fixture *f=p;f->flushes++;return f->fail_flush?-1:0;}
static void unreserve(void *p,uint32_t off,uint32_t n){struct fixture *f=p;(void)off;(void)n;f->reserved=0;}
static void unpin(void *p){struct fixture *f=p;f->pinned=0;}
static int submit(void *p,uint32_t *fence)
{
 struct fixture *f=p;struct rdn_sleep_dma_commands c;
 struct rdn_sleep_dma_request r={0,0x80000000,0x10000000,0x10000000,4096,0,0x100000000ull,0x20000,4096,4096};
 assert(f->pinned && f->reserved && f->mapped && !rdn_sleep_dma_build(&r,&c));
 assert(c.copy_bytes==4096 && c.words[6]==0x10000000 && c.words[8]==0 && c.words[9]==1);
 *fence=42;return 0;
}
static int poll(void *p,uint32_t fence)
{struct fixture *f=p;assert(fence==42);if(!f->done)return 0;memcpy(f->staging,f->hidden,4096);return 1;}
static int sync_cpu(void *p){struct fixture *f=p;f->synced=1;return 0;}
int main(void)
{
 struct fixture f;struct rdn_stage stage;struct rdn_sleep_copy copy;struct rdn_quiesce q;
 const struct rdn_stage_ops so={pin,reserve,bus,set,clear,flush,unreserve,unpin};
 const struct rdn_sleep_copy_ops co={submit,poll,sync_cpu};unsigned i;
#define RESET() do{memset(&f,0,sizeof(f));memset(&stage,0,sizeof(stage));memset(&copy,0,sizeof(copy));memset(&q,0,sizeof(q));q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=1;for(i=0;i<4096;i++)f.hidden[i]=(unsigned char)(i^(i>>8));}while(0)
 RESET();assert(!rdn_stage_bind(&stage,4096,&so,&f));
 assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&co,&f));
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);
 assert(q.phase==RDN_QUIESCE_HELD_POWERED && q.internal_hold && q.result==RDN_QUIESCE_UNSAFE);
 assert(!rdn_sleep_copy_poll(&copy,&co,&f));
 assert(rdn_sleep_copy_unstage(&copy,&stage,1,&so,&f) && f.pinned && f.reserved);
 f.done=1;assert(rdn_sleep_copy_poll(&copy,&co,&f)==1 && f.synced);
 assert(rdn_sleep_copy_release(&copy) && f.pinned && f.reserved);
 assert(rdn_sleep_copy_unstage(&copy,&stage,0,&so,&f) && f.pinned);
 memcpy(f.image,f.staging,4096);assert(!memcmp(f.image,f.hidden,4096));
 assert(!rdn_sleep_copy_unstage(&copy,&stage,1,&so,&f));
 assert(!f.pinned && !f.reserved && !f.mapped && q.phase==RDN_QUIESCE_HELD_POWERED);
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(q.phase==RDN_QUIESCE_RUNNING);
 RESET();assert(!rdn_stage_bind(&stage,4096,&so,&f));assert(!rdn_sleep_copy_start_staged(&copy,&q,&stage,&co,&f));
 f.done=1;assert(rdn_sleep_copy_poll(&copy,&co,&f)==1);f.fail_flush=1;
 assert(rdn_sleep_copy_unstage(&copy,&stage,1,&so,&f));
 assert(stage.phase==RDN_STAGE_QUARANTINED && copy.transfer.phase==RDN_TRANSFER_QUARANTINED && f.pinned && f.reserved);
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(q.phase==RDN_QUIESCE_HELD_POWERED && q.internal_hold);
 {
  struct fixture f2;struct rdn_stage ib;
  RESET();memset(&f2,0,sizeof(f2));f2.pinned=f2.reserved=f2.mapped=1;
  ib.phase=RDN_STAGE_BOUND;ib.bytes=4096;ib.offset=8192;ib.pages=1;
  assert(!rdn_stage_bind(&stage,4096,&so,&f));
  assert(!rdn_sleep_copy_start_staged_pair(&copy,&q,&stage,&ib,&co,&f));
  f.done=1;assert(rdn_sleep_copy_poll(&copy,&co,&f)==1);
  assert(rdn_sleep_copy_unstage(&copy,&stage,1,&so,&f) && q.internal_hold);
  assert(!rdn_sleep_copy_unstage_pair(&copy,&stage,&ib,1,&so,&f,&so,&f2));
  assert(!q.internal_hold && !f.pinned && !f2.pinned);
  RESET();memset(&f2,0,sizeof(f2));f2.pinned=f2.reserved=f2.mapped=1;f2.fail_flush=1;
  ib.phase=RDN_STAGE_BOUND;ib.bytes=4096;ib.offset=8192;ib.pages=1;
  assert(!rdn_stage_bind(&stage,4096,&so,&f));assert(!rdn_sleep_copy_start_staged_pair(&copy,&q,&stage,&ib,&co,&f));
  f.done=1;assert(rdn_sleep_copy_poll(&copy,&co,&f)==1);
  assert(rdn_sleep_copy_unstage_pair(&copy,&stage,&ib,1,&so,&f,&so,&f2));
  assert(q.internal_hold && copy.transfer.phase==RDN_TRANSFER_QUARANTINED && ib.phase==RDN_STAGE_QUARANTINED && f2.pinned);
 }
 return 0;
}
