/* No kernel use until actual lock, GART and lifetime integration. */
#include "rdn_sleep_copy.h"
static int held(struct rdn_sleep_copy *s)
{return s && s->quiesce && s->quiesce->phase==RDN_QUIESCE_HELD_POWERED &&
 s->quiesce->generation==s->generation && s->quiesce->internal_hold==1;}
int rdn_sleep_copy_start(struct rdn_sleep_copy *s,struct rdn_quiesce *q,int pinned,
                         const struct rdn_sleep_copy_ops *ops,void *cookie)
{
 uint32_t fence=0;int result;
 if(!s || !q || !ops || !ops->submit || !ops->poll || !ops->sync ||
    q->phase!=RDN_QUIESCE_HELD_POWERED || !q->generation ||
    s->transfer.phase!=RDN_TRANSFER_IDLE || !pinned)return -1;
 s->quiesce=q;s->generation=q->generation;
 if(rdn_transfer_prepare(&s->transfer,pinned,1))return -1;
 if(rdn_quiesce_hold_internal(q,s->generation)){rdn_transfer_abort_before_submit(&s->transfer);return -1;}
 result=ops->submit(cookie,&fence);
 if(result<0){
  /* A failed submit is safe to undo only if the gate and hold are intact.
   * Otherwise callback/lock invariants have been violated. */
  if(!held(s) || rdn_quiesce_release_internal(q,s->generation))rdn_transfer_uncertain(&s->transfer);
  else rdn_transfer_abort_before_submit(&s->transfer);
  return -1;
 }
 if(result>0 || !held(s)){rdn_transfer_uncertain(&s->transfer);return -1;}
 if(rdn_transfer_submitted(&s->transfer,fence)){rdn_transfer_uncertain(&s->transfer);return -1;}
 return 0;
}
int rdn_sleep_copy_poll(struct rdn_sleep_copy *s,const struct rdn_sleep_copy_ops *ops,void *cookie)
{
 int result;
 if(!s || s->transfer.phase!=RDN_TRANSFER_INFLIGHT || !ops || !ops->poll || !ops->sync)return -1;
 if(!held(s)){rdn_transfer_uncertain(&s->transfer);return -1;}
 result=ops->poll(cookie,s->transfer.fence);
 if(!held(s)){rdn_transfer_uncertain(&s->transfer);return -1;}
 if(!result)return 0;
 if(result!=1 || ops->sync(cookie) || !held(s)){rdn_transfer_uncertain(&s->transfer);return -1;}
 if(rdn_transfer_complete(&s->transfer,s->transfer.fence,1)){rdn_transfer_uncertain(&s->transfer);return -1;}
 return 1;
}
int rdn_sleep_copy_start_staged(struct rdn_sleep_copy *s,struct rdn_quiesce *q,
                                struct rdn_stage *stage,const struct rdn_sleep_copy_ops *ops,void *cookie)
{
 int result;
 if(!s || s->stage || s->transfer.phase!=RDN_TRANSFER_IDLE || !stage || stage->phase!=RDN_STAGE_BOUND)return -1;
 s->stage=stage;
 result=rdn_sleep_copy_start(s,q,1,ops,cookie);
 if(result && s->transfer.phase==RDN_TRANSFER_IDLE)s->stage=0;
 return result;
}
int rdn_sleep_copy_release(struct rdn_sleep_copy *s)
{
 if(!held(s) || s->stage || s->extra_stage || s->transfer.phase!=RDN_TRANSFER_READY ||
    rdn_quiesce_release_internal(s->quiesce,s->generation))return -1;
 if(rdn_transfer_release(&s->transfer))return -1;
 s->quiesce=0;s->generation=0;return 0;
}
int rdn_sleep_copy_unstage(struct rdn_sleep_copy *s,struct rdn_stage *stage,int consumed,
                           const struct rdn_stage_ops *ops,void *cookie)
{
 if(!s || !stage || s->stage!=stage || s->extra_stage || !consumed || !held(s) || s->transfer.phase!=RDN_TRANSFER_READY ||
    stage->phase!=RDN_STAGE_BOUND)return -1;
 if(rdn_stage_unbind(stage,1,ops,cookie)) {
  rdn_transfer_uncertain(&s->transfer);
  return -1;
 }
 s->stage=0;
 return rdn_sleep_copy_release(s);
}
int rdn_sleep_copy_start_staged_pair(struct rdn_sleep_copy *s,struct rdn_quiesce *q,
 struct rdn_stage *stage,struct rdn_stage *extra,const struct rdn_sleep_copy_ops *ops,void *cookie)
{
 int result;
 if(!s || s->extra_stage || !stage || !extra || stage==extra || extra->phase!=RDN_STAGE_BOUND)return -1;
 s->extra_stage=extra;
 result=rdn_sleep_copy_start_staged(s,q,stage,ops,cookie);
 if(result && s->transfer.phase==RDN_TRANSFER_IDLE)s->extra_stage=0;
 return result;
}
int rdn_sleep_copy_unstage_pair(struct rdn_sleep_copy *s,struct rdn_stage *stage,struct rdn_stage *extra,int consumed,
 const struct rdn_stage_ops *ops,void *cookie,const struct rdn_stage_ops *extra_ops,void *extra_cookie)
{
 if(!s || !stage || !extra || stage==extra || s->stage!=stage || s->extra_stage!=extra ||
    !consumed || !held(s) || s->transfer.phase!=RDN_TRANSFER_READY ||
    stage->phase!=RDN_STAGE_BOUND || extra->phase!=RDN_STAGE_BOUND)return -1;
 if(rdn_stage_unbind(stage,1,ops,cookie) || rdn_stage_unbind(extra,1,extra_ops,extra_cookie)) {
  rdn_transfer_uncertain(&s->transfer);return -1;
 }
 s->stage=0;s->extra_stage=0;return rdn_sleep_copy_release(s);
}
