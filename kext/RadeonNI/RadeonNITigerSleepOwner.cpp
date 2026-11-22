#include "RadeonNITigerSleepOwner.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
static int retain_object(void *,void *object)
{if(!object)return -1;((OSObject *)object)->retain();return 0;}
static void release_object(void *,void *object)
{((OSObject *)object)->release();}
static int descriptors_finished(void *cookie,void *data,void *ib)
{
 rdn_tiger_sleep_owner *owner=(rdn_tiger_sleep_owner *)cookie;
 return owner && owner->pair.data_descriptor && owner->pair.ib_descriptor &&
  data==static_cast<OSObject *>(owner->pair.data_descriptor) &&
  ib==static_cast<OSObject *>(owner->pair.ib_descriptor) &&
  rdn_tiger_sleep_pair_finished(&owner->pair,owner->pair.data_descriptor,owner->pair.ib_descriptor);
}
static const rdn_sleep_owner_ops owner_ops={retain_object,release_object,descriptors_finished};
int rdn_tiger_sleep_owner_arm(rdn_tiger_sleep_owner *owner,OSObject *accel,OSObject *framebuffer,
 rdn_sleep_sequence_bridge *bridge,rdn_sleep_guarded *owned,rdn_quiesce *q,
 rdn_tiger_sleep_stage *data,rdn_tiger_sleep_stage *ib)
{
 void *objects[RDN_OWNER_REFS];
 if(!owner || owner->owner.state!=RDN_OWNER_NEW || !accel || !framebuffer || !data || !ib ||
    !data->gart || data->gart!=ib->gart || !data->space || data->space!=ib->space ||
    !rdn_tiger_sleep_stage_matches(data,&data->stage,data->gart) ||
    !rdn_tiger_sleep_stage_matches(ib,&ib->stage,ib->gart) ||
    rdn_tiger_sleep_pair_init(&owner->pair,data,ib))return -1;
 objects[RDN_OWNER_ACCEL]=accel;objects[RDN_OWNER_FRAMEBUFFER]=framebuffer;
 objects[RDN_OWNER_DATA_DESCRIPTOR]=static_cast<OSObject *>(data->memory);
 objects[RDN_OWNER_IB_DESCRIPTOR]=static_cast<OSObject *>(ib->memory);
 return rdn_sleep_owner_arm(&owner->owner,objects,&owner_ops,owner,bridge,owned,q,&data->stage,&ib->stage);
}
#endif
