/* Prototype callback-driven copy lifecycle; no hardware access here. MIT */
#ifndef RDN_SLEEP_COPY_H
#define RDN_SLEEP_COPY_H
#include "rdn_quiesce.h"
#include "rdn_snapshot_transfer.h"
#include "rdn_sleep_staging.h"
struct rdn_sleep_copy_ops {
 /* 0 published, negative definitely not published, positive uncertain. */
 int (*submit)(void *,uint32_t *);
 /* 1 fence observed, 0 pending, negative uncertain. */
 int (*poll)(void *,uint32_t);
 /* 0 completed CPU/DMA synchronization, nonzero failure. */
 int (*sync)(void *);
};
struct rdn_sleep_copy {
 struct rdn_snapshot_transfer transfer;
 struct rdn_quiesce *quiesce;
 uint32_t generation;
 struct rdn_stage *stage;
 struct rdn_stage *extra_stage;
};
/* Caller owns all required locks, stable quiesce object and staging lifetime.
 * Callback truthfulness, pinning, cache sync and real fence checks are NOT
 * enforced by this host-testable coordinator. The internal hold blocks the
 * normal reopen function while work is active; it is not a lifetime or lock
 * enforcement mechanism against callers that mutate the state directly. */
int rdn_sleep_copy_start(struct rdn_sleep_copy *,struct rdn_quiesce *,int pinned,
                         const struct rdn_sleep_copy_ops *,void *);
int rdn_sleep_copy_start_staged(struct rdn_sleep_copy *,struct rdn_quiesce *,
                                struct rdn_stage *,const struct rdn_sleep_copy_ops *,void *);
int rdn_sleep_copy_start_staged_pair(struct rdn_sleep_copy *,struct rdn_quiesce *,
 struct rdn_stage *,struct rdn_stage *,const struct rdn_sleep_copy_ops *,void *);
/* 1 ready, 0 pending, -1 quarantined or invalid. A timeout must be passed as
 * negative poll result; never retry or free uncertain in-flight resources. */
int rdn_sleep_copy_poll(struct rdn_sleep_copy *,const struct rdn_sleep_copy_ops *,void *);
/* Only after the saved bytes have been consumed; permits caller to unpin and
 * separately reopen the gate. Returns failure for inflight or quarantine. */
int rdn_sleep_copy_release(struct rdn_sleep_copy *);
/* Host prototype: caller proves image bytes were consumed. Unbind only after
 * successful fence+sync. Any unbind uncertainty quarantines both models. */
int rdn_sleep_copy_unstage(struct rdn_sleep_copy *,struct rdn_stage *,int consumed,
                           const struct rdn_stage_ops *,void *);
int rdn_sleep_copy_unstage_pair(struct rdn_sleep_copy *,struct rdn_stage *,struct rdn_stage *,int consumed,
 const struct rdn_stage_ops *,void *,const struct rdn_stage_ops *,void *);
#endif
