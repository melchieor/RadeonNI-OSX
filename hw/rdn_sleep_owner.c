/* Host-tested reference/retirement policy, not integrated into IOService. */
#include "rdn_sleep_owner.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
int rdn_sleep_owner_arm(struct rdn_sleep_owner *o,void *const objects[RDN_OWNER_REFS],
 const struct rdn_sleep_owner_ops *ops,void *cookie,struct rdn_sleep_sequence_bridge *b,
 struct rdn_sleep_guarded *owned,struct rdn_quiesce *q,struct rdn_stage *data,struct rdn_stage *ib)
{
 uint32_t i,j;
 if(!o || o->state!=RDN_OWNER_NEW || !objects || !ops || !ops->retain || !ops->release || !ops->descriptors_finished ||
    !b || !owned || !owned->active || !q || !data || !ib || data==ib ||
    data->phase!=RDN_STAGE_BOUND || ib->phase!=RDN_STAGE_BOUND ||
    q->phase!=RDN_QUIESCE_HELD_POWERED || !q->generation || q->internal_hold ||
    b->active || b->sequence.state!=RDN_SEQ_READY || (b->owned && b->owned!=owned))return -1;
 for(i=0;i<RDN_OWNER_REFS;i++) {
  if(!objects[i])return -1;
  for(j=0;j<i;j++)if(objects[i]==objects[j])return -1;
 }
 for(i=0;i<RDN_OWNER_REFS;i++) {
  if(ops->retain(cookie,objects[i])) {
   while(i){--i;ops->release(cookie,objects[i]);}
   return -1;
  }
 }
 for(i=0;i<RDN_OWNER_REFS;i++)o->objects[i]=objects[i];
 o->refs=RDN_OWNER_REFS;o->bridge=b;o->owned=owned;o->quiesce=q;o->data=data;o->ib=ib;o->ops=ops;o->ops_cookie=cookie;
 o->client_attached=1;o->generation=q->generation;o->state=RDN_OWNER_ARMED;return 0;
}
int rdn_sleep_owner_may_submit(const struct rdn_sleep_owner *o)
{
 return o && o->state==RDN_OWNER_ARMED && o->client_attached && o->refs==RDN_OWNER_REFS &&
  o->bridge && !o->bridge->active && o->bridge->sequence.state==RDN_SEQ_READY &&
  o->owned && o->owned->active && o->quiesce && o->quiesce->phase==RDN_QUIESCE_HELD_POWERED &&
  o->generation && o->quiesce->generation==o->generation &&
  !o->quiesce->internal_hold && o->data && o->ib &&
  o->data->phase==RDN_STAGE_BOUND && o->ib->phase==RDN_STAGE_BOUND;
}
int rdn_sleep_owner_note_submit(struct rdn_sleep_owner *o)
{
 if(!o || o->state!=RDN_OWNER_ARMED)return -1;
 if(!o->client_attached || o->refs!=RDN_OWNER_REFS || !o->bridge || !o->owned || !o->quiesce || !o->data || !o->ib ||
    o->bridge->owned!=o->owned || !o->owned->active || !o->bridge->active ||
    o->bridge->sequence.state!=RDN_SEQ_WAITING || o->bridge->copy.transfer.phase!=RDN_TRANSFER_INFLIGHT ||
    o->bridge->copy.stage!=o->data || o->bridge->copy.extra_stage!=o->ib ||
    o->data->phase!=RDN_STAGE_BOUND || o->ib->phase!=RDN_STAGE_BOUND ||
    o->bridge->copy.quiesce!=o->quiesce || !o->generation || o->generation!=o->quiesce->generation ||
    o->bridge->copy.generation!=o->quiesce->generation ||
    o->quiesce->phase!=RDN_QUIESCE_HELD_POWERED || o->quiesce->internal_hold!=1) {
  if(o->bridge && o->bridge->active)o->state=RDN_OWNER_QUARANTINED;
  return -1;
 }
 o->state=RDN_OWNER_INFLIGHT;return 0;
}
void rdn_sleep_owner_client_closed(struct rdn_sleep_owner *o)
{if(o && o->state!=RDN_OWNER_NEW && o->state!=RDN_OWNER_RELEASED)o->client_attached=0;}
int rdn_sleep_owner_observe(struct rdn_sleep_owner *o)
{
 struct rdn_sleep_sequence_bridge *b;
 if(!o || !o->bridge || !o->owned || !o->quiesce || !o->data || !o->ib ||
    (o->state!=RDN_OWNER_ARMED && o->state!=RDN_OWNER_INFLIGHT && o->state!=RDN_OWNER_QUARANTINED))return -1;
 b=o->bridge;
 if(o->state==RDN_OWNER_QUARANTINED)return -1;
 if(!o->generation || o->quiesce->generation!=o->generation ||
    b->sequence.state==RDN_SEQ_QUARANTINED || b->copy.transfer.phase==RDN_TRANSFER_QUARANTINED ||
    o->data->phase==RDN_STAGE_QUARANTINED || o->ib->phase==RDN_STAGE_QUARANTINED) {
  o->state=RDN_OWNER_QUARANTINED;return -1;
 }
 if((b->sequence.state==RDN_SEQ_PASSED || b->sequence.state==RDN_SEQ_FAILED) &&
    !b->active && b->copy.transfer.phase==RDN_TRANSFER_IDLE && !b->copy.stage && !b->copy.extra_stage &&
    !o->owned->active && !o->quiesce->internal_hold &&
    o->data->phase==RDN_STAGE_IDLE && o->ib->phase==RDN_STAGE_IDLE) {
  o->state=RDN_OWNER_CLEAN;return 1;
 }
 if(!b->active && b->sequence.state==RDN_SEQ_READY && b->copy.transfer.phase==RDN_TRANSFER_IDLE &&
    !b->copy.stage && !b->copy.extra_stage && !o->quiesce->internal_hold &&
    o->data->phase==RDN_STAGE_IDLE && o->ib->phase==RDN_STAGE_IDLE) {
  o->state=RDN_OWNER_ARMED;return 0;
 }
 return 0;
}
int rdn_sleep_owner_may_retire(const struct rdn_sleep_owner *o)
{return o && o->state==RDN_OWNER_RELEASED;}
int rdn_sleep_owner_release(struct rdn_sleep_owner *o)
{
 uint32_t i;
 const struct rdn_sleep_owner_ops *ops;void *cookie;
 if(!o)return -1;
 ops=o->ops;cookie=o->ops_cookie;
 if(!o || o->state!=RDN_OWNER_CLEAN || o->refs!=RDN_OWNER_REFS || !ops || !ops->release || !ops->descriptors_finished ||
    !o->bridge || o->bridge->active || (o->bridge->sequence.state!=RDN_SEQ_PASSED && o->bridge->sequence.state!=RDN_SEQ_FAILED) ||
    o->bridge->copy.transfer.phase!=RDN_TRANSFER_IDLE || o->bridge->copy.stage || o->bridge->copy.extra_stage ||
    !o->owned || o->owned->active || !o->quiesce || o->quiesce->internal_hold ||
    !o->data || !o->ib || o->data->phase!=RDN_STAGE_IDLE || o->ib->phase!=RDN_STAGE_IDLE ||
    !ops->descriptors_finished(cookie,o->objects[RDN_OWNER_DATA_DESCRIPTOR],o->objects[RDN_OWNER_IB_DESCRIPTOR]))return -1;
 for(i=RDN_OWNER_REFS;i;i--){ops->release(cookie,o->objects[i-1]);o->objects[i-1]=0;}
 o->refs=0;o->state=RDN_OWNER_RELEASED;return 0;
}
#endif
