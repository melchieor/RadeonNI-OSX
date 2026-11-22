#include <assert.h>
#include <string.h>
#include "rdn_sleep_owner.h"
struct fixture {void *expected[4];int fail_at,retains,releases,finished;void *release_order[4];};
static int retain_obj(void *p,void *obj){struct fixture *f=p;int i=f->retains++;assert(i<4 && obj==f->expected[i]);return f->fail_at==i+1?-1:0;}
static void release_obj(void *p,void *obj){struct fixture *f=p;assert(f->releases<4);f->release_order[f->releases++]=obj;}
static int finished(void *p,void *a,void *b){struct fixture *f=p;assert(a==f->expected[2] && b==f->expected[3]);return f->finished;}
int main(void)
{
 struct rdn_sleep_owner owner;struct rdn_sleep_sequence_bridge bridge;struct rdn_sleep_guarded owned;
 struct rdn_quiesce q;struct rdn_stage data,ib;struct fixture f;int objects[4];void *refs[4];unsigned i;
 const struct rdn_sleep_owner_ops ops={retain_obj,release_obj,finished};
#define RESET() do {memset(&owner,0,sizeof(owner));memset(&bridge,0,sizeof(bridge));memset(&owned,0,sizeof(owned));memset(&q,0,sizeof(q));memset(&data,0,sizeof(data));memset(&ib,0,sizeof(ib));memset(&f,0,sizeof(f));for(i=0;i<4;i++){refs[i]=&objects[i];f.expected[i]=refs[i];}owned.active=1;q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=5;data.phase=ib.phase=RDN_STAGE_BOUND;bridge.sequence.state=RDN_SEQ_READY;}while(0)
 RESET();f.fail_at=3;assert(rdn_sleep_owner_arm(&owner,refs,&ops,&f,&bridge,&owned,&q,&data,&ib));
 assert(f.retains==3 && f.releases==2 && f.release_order[0]==refs[1] && f.release_order[1]==refs[0]);
 assert(owner.state==RDN_OWNER_NEW && !owner.refs);
 RESET();assert(!rdn_sleep_owner_arm(&owner,refs,&ops,&f,&bridge,&owned,&q,&data,&ib));
 assert(owner.refs==4 && rdn_sleep_owner_may_submit(&owner) && !rdn_sleep_owner_may_retire(&owner));
 q.generation=6;assert(!rdn_sleep_owner_may_submit(&owner));q.generation=5;
 bridge.owned=&owned;bridge.active=1;bridge.sequence.state=RDN_SEQ_WAITING;
 bridge.copy.transfer.phase=RDN_TRANSFER_INFLIGHT;bridge.copy.stage=&data;bridge.copy.extra_stage=&ib;
 bridge.copy.quiesce=&q;bridge.copy.generation=5;q.internal_hold=1;
 assert(!rdn_sleep_owner_note_submit(&owner));rdn_sleep_owner_client_closed(&owner);
 assert(!owner.client_attached && owner.refs==4 && !f.releases && !rdn_sleep_owner_may_retire(&owner));
 assert(!rdn_sleep_owner_may_submit(&owner));
 assert(!rdn_sleep_owner_observe(&owner) && rdn_sleep_owner_release(&owner));
 bridge.active=0;bridge.sequence.state=RDN_SEQ_READY;q.internal_hold=0;data.phase=ib.phase=RDN_STAGE_IDLE;
 bridge.copy.transfer.phase=RDN_TRANSFER_IDLE;bridge.copy.stage=bridge.copy.extra_stage=0;
 assert(!rdn_sleep_owner_observe(&owner) && owner.state==RDN_OWNER_ARMED);
 assert(!rdn_sleep_owner_may_submit(&owner)); /* Closed client cannot start another operation. */
 bridge.sequence.state=RDN_SEQ_PASSED;owned.active=0;assert(rdn_sleep_owner_observe(&owner)==1);
 assert(rdn_sleep_owner_release(&owner) && !f.releases);f.finished=1;
 assert(!rdn_sleep_owner_release(&owner) && rdn_sleep_owner_may_retire(&owner));
 for(i=0;i<4;i++)assert(f.release_order[i]==refs[3-i]);
 RESET();assert(!rdn_sleep_owner_arm(&owner,refs,&ops,&f,&bridge,&owned,&q,&data,&ib));
 bridge.sequence.state=RDN_SEQ_QUARANTINED;assert(rdn_sleep_owner_observe(&owner)==-1);
 assert(owner.state==RDN_OWNER_QUARANTINED && !rdn_sleep_owner_may_retire(&owner));
 assert(rdn_sleep_owner_release(&owner) && !f.releases && owner.refs==4);
 RESET();assert(!rdn_sleep_owner_arm(&owner,refs,&ops,&f,&bridge,&owned,&q,&data,&ib));
 bridge.owned=&owned;bridge.active=1;bridge.sequence.state=RDN_SEQ_WAITING;
 bridge.copy.transfer.phase=RDN_TRANSFER_INFLIGHT;bridge.copy.stage=&data;bridge.copy.extra_stage=&ib;
 bridge.copy.quiesce=&q;bridge.copy.generation=4;q.internal_hold=1;
 assert(rdn_sleep_owner_note_submit(&owner) && owner.state==RDN_OWNER_QUARANTINED && owner.refs==4);
 RESET();assert(!rdn_sleep_owner_arm(&owner,refs,&ops,&f,&bridge,&owned,&q,&data,&ib));
 q.generation=6;assert(rdn_sleep_owner_observe(&owner)==-1 && owner.state==RDN_OWNER_QUARANTINED && owner.refs==4);
 return 0;
}
