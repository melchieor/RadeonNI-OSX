#include <cassert>
#include "../kext/RadeonNI/RadeonNITigerSleepOwner.h"
int main()
{
 OSObject accel,framebuffer;IOBufferMemoryDescriptor data_descriptor,ib_descriptor;
 rdn_tiger_sleep_owner owner={};rdn_tiger_sleep_stage data={},ib={};
 rdn_sleep_sequence_bridge bridge={};rdn_sleep_guarded owned={};rdn_quiesce q={};rdn_gart gart={};rdn_mem space={};
 data.memory=&data_descriptor;ib.memory=&ib_descriptor;data.prepared=ib.prepared=true;
 gart.ready=true;data.gart=ib.gart=&gart;data.space=ib.space=&space;
 data.stage.phase=ib.stage.phase=RDN_STAGE_BOUND;owned.active=1;
 q.phase=RDN_QUIESCE_HELD_POWERED;q.generation=3;bridge.sequence.state=RDN_SEQ_READY;
 ib.gart=0;assert(rdn_tiger_sleep_owner_arm(&owner,&accel,&framebuffer,&bridge,&owned,&q,&data,&ib));
 assert(accel.references==1 && framebuffer.references==1 && data_descriptor.references==1 && ib_descriptor.references==1);
 ib.gart=&gart;
 assert(!rdn_tiger_sleep_owner_arm(&owner,&accel,&framebuffer,&bridge,&owned,&q,&data,&ib));
 assert(accel.references==2 && framebuffer.references==2 && data_descriptor.references==2 && ib_descriptor.references==2);
 assert(!rdn_sleep_owner_may_retire(&owner.owner));
 rdn_sleep_owner_client_closed(&owner.owner);
 assert(!rdn_sleep_owner_may_submit(&owner.owner) && !rdn_sleep_owner_may_retire(&owner.owner));
 bridge.sequence.state=RDN_SEQ_PASSED;bridge.active=0;owned.active=0;
 data.stage.phase=ib.stage.phase=RDN_STAGE_IDLE;
 assert(rdn_sleep_owner_observe(&owner.owner)==1);
 assert(rdn_sleep_owner_release(&owner.owner));
 assert(!rdn_tiger_sleep_stage_finish(&data));
 ib_descriptor.complete_result=1;assert(rdn_tiger_sleep_stage_finish(&ib));
 assert(rdn_sleep_owner_release(&owner.owner));
 ib_descriptor.complete_result=0;assert(!rdn_tiger_sleep_stage_finish(&ib));
 assert(!rdn_sleep_owner_release(&owner.owner));
 assert(accel.references==1 && framebuffer.references==1 && !data_descriptor.references && !ib_descriptor.references);
 assert(rdn_sleep_owner_may_retire(&owner.owner));
 return 0;
}
