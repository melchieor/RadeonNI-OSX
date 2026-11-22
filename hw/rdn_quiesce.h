/* Power-retained graphics admission rehearsal, not suspend. SPDX-License-Identifier: MIT */
#ifndef RDN_QUIESCE_H
#define RDN_QUIESCE_H
#include <stdint.h>
enum {RDN_QUIESCE_RUNNING=0,RDN_QUIESCE_DRAINING=1,RDN_QUIESCE_HELD_POWERED=2};
enum {RDN_QUIESCE_OK=0,RDN_QUIESCE_NEVER=1,RDN_QUIESCE_TIMEOUT=2,
      RDN_QUIESCE_CLOCK=3,RDN_QUIESCE_BUSY=4,RDN_QUIESCE_UNSAFE=5,RDN_QUIESCE_INVARIANT=6};
#define RDN_QUIESCE_MAX_MS 100u
struct rdn_quiesce {
 volatile uint32_t phase;
 uint32_t generation,result,polls,timeout_ms;
 uint64_t started;
 uint32_t internal_hold;
};
void rdn_quiesce_init(struct rdn_quiesce *);
int rdn_quiesce_begin(struct rdn_quiesce *,uint64_t now,unsigned timeout_ms);
/* 0 wait, 1 held, -1 aborted with gate already reopened. */
int rdn_quiesce_poll(struct rdn_quiesce *,uint64_t now,int drained);
void rdn_quiesce_reopen(struct rdn_quiesce *,unsigned result);
/* Caller holds the same lock used by submission and transitions. */
int rdn_quiesce_hold_internal(struct rdn_quiesce *,uint32_t generation);
int rdn_quiesce_release_internal(struct rdn_quiesce *,uint32_t generation);
#endif
