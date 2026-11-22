/* Experimental integration; no kernel/user-client entry point. MIT */
#ifndef RDN_SLEEP_SEQUENCE_BRIDGE_H
#define RDN_SLEEP_SEQUENCE_BRIDGE_H
#include "rdn_sleep_sequence.h"
#include "rdn_sleep_transaction.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
struct rdn_sleep_sequence_env {
 struct rdn_accel *accel;struct rdn_quiesce *quiesce;struct rdn_gart *gart;
 struct rdn_sleep_guarded *owned;struct rdn_stage *data,*ib;
 int (*matches)(void *,struct rdn_stage *,struct rdn_gart *);void *data_cookie,*ib_cookie;
 int coherent;int (*barrier)(void *);void *barrier_cookie;
 int (*writer)(void *,const uint32_t *,uint32_t);int (*publish)(void *);void *writer_cookie;
};
struct rdn_sleep_sequence_bridge {
 struct rdn_sleep_sequence sequence;struct rdn_sleep_copy copy;
 struct rdn_sleep_runtime runtime;struct rdn_sleep_gart_ib_ticket ticket;
 struct rdn_sleep_guarded *owned;
 uint32_t token,active;
};
/* All methods are prototype-only. Caller holds driver/allocator locks and
 * retains every object; callbacks must honor their real device contracts. */
int rdn_sleep_sequence_bridge_begin(struct rdn_sleep_sequence_bridge *);
int rdn_sleep_sequence_bridge_start(struct rdn_sleep_sequence_bridge *,struct rdn_sleep_sequence_env *);
/* 0 pending, 1 complete, -1 failed/quarantined. Read callback must copy only
 * the synchronized private staging page to the caller-owned output buffer. */
int rdn_sleep_sequence_bridge_poll(struct rdn_sleep_sequence_bridge *,int (*read)(void *,void *,uint32_t),void *,void *);
int rdn_sleep_sequence_bridge_unstage(struct rdn_sleep_sequence_bridge *,struct rdn_sleep_sequence_env *,
 const struct rdn_stage_ops *,void *,const struct rdn_stage_ops *,void *);
/* Caller must complete descriptor teardown outside locks first. */
int rdn_sleep_sequence_bridge_finish(struct rdn_sleep_sequence_bridge *,struct rdn_sleep_guarded *,int descriptors_released);
/* Cancel only between completed operations, after both descriptors finish. */
int rdn_sleep_sequence_bridge_cancel(struct rdn_sleep_sequence_bridge *,struct rdn_sleep_guarded *,
 struct rdn_quiesce *,struct rdn_stage *,struct rdn_stage *,int descriptors_released);
#endif
#endif
