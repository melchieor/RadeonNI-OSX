/* Caller serializes transitions. This code cannot power off a device. SPDX-License-Identifier: MIT */
#include "rdn_quiesce.h"
void rdn_quiesce_init(struct rdn_quiesce *q)
{
 q->phase=RDN_QUIESCE_RUNNING;q->generation=0;q->result=RDN_QUIESCE_NEVER;
 q->polls=0;q->timeout_ms=0;q->started=0;q->internal_hold=0;
}
void rdn_quiesce_reopen(struct rdn_quiesce *q,unsigned result)
{if(q->internal_hold){q->result=RDN_QUIESCE_UNSAFE;return;}q->result=result;q->phase=RDN_QUIESCE_RUNNING;}
int rdn_quiesce_hold_internal(struct rdn_quiesce *q,uint32_t generation)
{
 if(!q || q->phase!=RDN_QUIESCE_HELD_POWERED || !generation || q->generation!=generation || q->internal_hold)return -1;
 q->internal_hold=1;return 0;
}
int rdn_quiesce_release_internal(struct rdn_quiesce *q,uint32_t generation)
{
 if(!q || q->phase!=RDN_QUIESCE_HELD_POWERED || !generation || q->generation!=generation || q->internal_hold!=1)return -1;
 q->internal_hold=0;return 0;
}
int rdn_quiesce_begin(struct rdn_quiesce *q,uint64_t now,unsigned timeout)
{
 /* Generation zero is invalid and a wrapped generation could identify an
  * earlier transfer as current. Exhaustion requires a fresh device lifetime. */
 if(!q || q->phase!=RDN_QUIESCE_RUNNING || q->internal_hold || q->generation==UINT32_MAX ||
    !timeout || timeout>RDN_QUIESCE_MAX_MS)return -1;
 q->started=now;q->timeout_ms=timeout;q->polls=0;++q->generation;
 q->phase=RDN_QUIESCE_DRAINING;return 0;
}
int rdn_quiesce_poll(struct rdn_quiesce *q,uint64_t now,int drained)
{
 if(q->phase==RDN_QUIESCE_HELD_POWERED)return 1;
 if(q->phase!=RDN_QUIESCE_DRAINING)return -1;
 if(now<q->started){rdn_quiesce_reopen(q,RDN_QUIESCE_CLOCK);return -1;}
 /* Iteration cap also guarantees termination if the supplied clock stalls. */
 if(now-q->started>=q->timeout_ms || ++q->polls>q->timeout_ms+1) {
  rdn_quiesce_reopen(q,RDN_QUIESCE_TIMEOUT);return -1;
 }
 if(drained){q->phase=RDN_QUIESCE_HELD_POWERED;return 1;}
 return 0;
}
