/* Host-only power-retained coordinator checks. SPDX-License-Identifier: MIT */
#include <assert.h>
#include <stdio.h>
#include "rdn_quiesce.h"
int main(void)
{
 struct rdn_quiesce q;unsigned i;
 rdn_quiesce_init(&q);assert(!q.phase && q.result==RDN_QUIESCE_NEVER);
 assert(rdn_quiesce_begin(&q,100,0)<0 && !q.phase);
 assert(rdn_quiesce_begin(&q,100,101)<0 && !q.phase);
 assert(!rdn_quiesce_begin(&q,100,50) && q.phase==RDN_QUIESCE_DRAINING);
 assert(rdn_quiesce_begin(&q,101,50)<0 && q.generation==1);
 assert(!rdn_quiesce_poll(&q,110,0));
 assert(rdn_quiesce_poll(&q,120,1)==1 && q.phase==RDN_QUIESCE_HELD_POWERED);
 assert(rdn_quiesce_hold_internal(&q,2)<0 && !q.internal_hold);
 assert(!rdn_quiesce_hold_internal(&q,q.generation) && q.internal_hold);
 assert(rdn_quiesce_hold_internal(&q,q.generation)<0);
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(q.phase==RDN_QUIESCE_HELD_POWERED && q.result==RDN_QUIESCE_UNSAFE);
 assert(rdn_quiesce_release_internal(&q,2)<0 && q.internal_hold);
 assert(!rdn_quiesce_release_internal(&q,q.generation) && !q.internal_hold);
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(!q.phase && !q.result);
 assert(!rdn_quiesce_begin(&q,100,50));
 assert(rdn_quiesce_poll(&q,150,1)<0 && !q.phase && q.result==RDN_QUIESCE_TIMEOUT);
 assert(!rdn_quiesce_begin(&q,100,50));
 assert(rdn_quiesce_poll(&q,99,0)<0 && !q.phase && q.result==RDN_QUIESCE_CLOCK);
 assert(!rdn_quiesce_begin(&q,100,50));
 for(i=0;i<60 && q.phase;i++)rdn_quiesce_poll(&q,100,0);
 assert(!q.phase && q.result==RDN_QUIESCE_TIMEOUT);
 for(i=0;i<10000;i++) {
  assert(!rdn_quiesce_begin(&q,1000,100));
  if(i%3==0)assert(rdn_quiesce_poll(&q,1001,1)==1);
  else if(i%3==1)assert(rdn_quiesce_poll(&q,1100,0)<0);
  else assert(rdn_quiesce_poll(&q,999,0)<0);
  rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);assert(!q.phase);
 }
 /* Never let a stale transfer generation become current after wraparound. */
 q.generation=UINT32_MAX-1;
 assert(!rdn_quiesce_begin(&q,2000,50) && q.generation==UINT32_MAX);
 assert(rdn_quiesce_poll(&q,2001,1)==1);
 assert(!rdn_quiesce_hold_internal(&q,UINT32_MAX));
 assert(!rdn_quiesce_release_internal(&q,UINT32_MAX));
 rdn_quiesce_reopen(&q,RDN_QUIESCE_OK);
 assert(rdn_quiesce_begin(&q,2100,50)<0 && q.generation==UINT32_MAX && q.phase==RDN_QUIESCE_RUNNING);
 assert(rdn_quiesce_begin(0,2100,50)<0);
 puts("quiesce model: invalid limits, reentry, held/reopen, timeout, backwards/stalled clock and 10,000 recovery cycles passed");
 return 0;
}
