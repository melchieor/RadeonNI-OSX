#include <assert.h>
#include <string.h>
#include "rdn_sleep_staging.h"
struct fixture {int pinfail,reservefail,pagefail,setfail,clearfail,flushfail,pinned,reserved,sets,clears,flushes,unpins,frees;};
static int pin(void *c,uint32_t n){struct fixture *f=c;(void)n;if(f->pinfail)return -1;f->pinned=1;return 0;}
static int reserve(void *c,uint32_t n,uint32_t *a){struct fixture *f=c;(void)n;if(f->reservefail)return -1;f->reserved=1;*a=4096;return 0;}
static int page(void *c,uint32_t o,uint64_t *a){struct fixture *f=c;if(f->pagefail && o==4096)return -1;*a=0x100000ull+o;return 0;}
static int set(void *c,uint32_t o,uint64_t a){struct fixture *f=c;(void)o;(void)a;f->sets++;return f->setfail && f->sets==2?-1:0;}
static int clear(void *c,uint32_t o){struct fixture *f=c;(void)o;f->clears++;return f->clearfail?-1:0;}
static int flush(void *c){struct fixture *f=c;f->flushes++;return f->flushfail?-1:0;}
static void unreserve(void *c,uint32_t o,uint32_t n){struct fixture *f=c;(void)o;(void)n;f->reserved=0;f->frees++;}
static void unpin(void *c){struct fixture *f=c;f->pinned=0;f->unpins++;}
int main(void)
{
 struct rdn_stage s;struct fixture f;
 const struct rdn_stage_ops ops={pin,reserve,page,set,clear,flush,unreserve,unpin};
#define RESET() do {memset(&s,0,sizeof(s));memset(&f,0,sizeof(f));} while(0)
 RESET();assert(rdn_stage_bind(&s,0,&ops,&f) && !f.pinned);
 assert(!rdn_stage_bind(&s,8192,&ops,&f) && s.phase==RDN_STAGE_BOUND && f.pinned && f.reserved && f.sets==2);
 assert(rdn_stage_unbind(&s,0,&ops,&f) && f.pinned && f.reserved);
 assert(!rdn_stage_unbind(&s,1,&ops,&f) && !f.pinned && !f.reserved && f.clears==2 && f.flushes==2);
 RESET();f.pinfail=1;assert(rdn_stage_bind(&s,4096,&ops,&f) && !f.reserved && !f.unpins);
 RESET();f.reservefail=1;assert(rdn_stage_bind(&s,4096,&ops,&f) && !f.pinned && f.unpins==1);
 RESET();f.pagefail=1;assert(rdn_stage_bind(&s,8192,&ops,&f) && s.phase==RDN_STAGE_IDLE && f.clears==1 && f.flushes==1 && !f.pinned);
 RESET();f.setfail=1;assert(rdn_stage_bind(&s,8192,&ops,&f) && f.clears==2 && !f.pinned && !f.reserved);
 RESET();f.setfail=1;f.clearfail=1;assert(rdn_stage_bind(&s,8192,&ops,&f) && s.phase==RDN_STAGE_QUARANTINED && f.pinned && f.reserved && !f.frees);
 RESET();f.flushfail=1;assert(rdn_stage_bind(&s,4096,&ops,&f) && s.phase==RDN_STAGE_QUARANTINED && f.pinned && f.reserved && !f.frees);
 RESET();assert(!rdn_stage_bind(&s,4096,&ops,&f));f.flushfail=1;assert(rdn_stage_unbind(&s,1,&ops,&f) && s.phase==RDN_STAGE_QUARANTINED && f.pinned && f.reserved);
 assert(rdn_stage_unbind(&s,1,&ops,&f) && f.pinned && f.reserved);
 return 0;
}
