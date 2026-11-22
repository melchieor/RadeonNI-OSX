#include <assert.h>
#include <string.h>
#include "rdn_sleep_copy.h"
struct fixture { int submit,poll,sync,submits,polls,syncs;uint32_t fence;struct rdn_quiesce *q;int break_gate; };
static int submit(void *p,uint32_t *f){struct fixture *x=p;x->submits++;*f=x->fence;if(x->break_gate)x->q->phase=0;return x->submit;}
static int poll(void *p,uint32_t f){struct fixture *x=p;x->polls++;assert(f==x->fence);return x->poll;}
static int sync_cpu(void *p){struct fixture *x=p;x->syncs++;return x->sync;}
int main(void)
{
 struct rdn_sleep_copy s;struct rdn_quiesce q;struct fixture f;
 const struct rdn_sleep_copy_ops ops={submit,poll,sync_cpu};
#define RESET() do{memset(&s,0,sizeof(s));memset(&q,0,sizeof(q));memset(&f,0,sizeof(f));q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=3;f.q=&q;}while(0)
 RESET();assert(rdn_sleep_copy_start(&s,&q,0,&ops,&f) && !f.submits);
 assert(!rdn_sleep_copy_start(&s,&q,1,&ops,&f)); /* zero is a valid wrapped fence */
 assert(!rdn_sleep_copy_poll(&s,&ops,&f));assert(rdn_sleep_copy_release(&s));
 f.poll=1;assert(rdn_sleep_copy_poll(&s,&ops,&f)==1 && f.syncs==1);
 assert(!rdn_sleep_copy_release(&s) && s.transfer.phase==RDN_TRANSFER_IDLE);
 RESET();f.submit=-1;assert(rdn_sleep_copy_start(&s,&q,1,&ops,&f));assert(s.transfer.phase==RDN_TRANSFER_IDLE);
 RESET();f.submit=1;assert(rdn_sleep_copy_start(&s,&q,1,&ops,&f));assert(s.transfer.phase==RDN_TRANSFER_QUARANTINED);assert(rdn_sleep_copy_release(&s));
 RESET();assert(!rdn_sleep_copy_start(&s,&q,1,&ops,&f));f.poll=-1;assert(rdn_sleep_copy_poll(&s,&ops,&f)==-1);assert(rdn_sleep_copy_release(&s));
 RESET();assert(!rdn_sleep_copy_start(&s,&q,1,&ops,&f));f.poll=1;f.sync=1;assert(rdn_sleep_copy_poll(&s,&ops,&f)==-1);assert(rdn_sleep_copy_release(&s));
 RESET();assert(!rdn_sleep_copy_start(&s,&q,1,&ops,&f));q.generation++;assert(rdn_sleep_copy_poll(&s,&ops,&f)==-1);assert(!f.polls && rdn_sleep_copy_release(&s));
 RESET();f.break_gate=1;assert(rdn_sleep_copy_start(&s,&q,1,&ops,&f));assert(s.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();f.break_gate=1;f.submit=-1;assert(rdn_sleep_copy_start(&s,&q,1,&ops,&f));assert(s.transfer.phase==RDN_TRANSFER_QUARANTINED);
 RESET();assert(!rdn_sleep_copy_start(&s,&q,1,&ops,&f));q.internal_hold=0;f.poll=1;
 assert(rdn_sleep_copy_poll(&s,&ops,&f)==-1 && !f.polls && s.transfer.phase==RDN_TRANSFER_QUARANTINED);
 return 0;
}
