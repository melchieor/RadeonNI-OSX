/* Internal copy integration prototype, not a sleep implementation. MIT */
#ifndef RDN_SLEEP_TRANSACTION_H
#define RDN_SLEEP_TRANSACTION_H
#include "rdn_sleep_private.h"
#include "rdn_sleep_runtime.h"
#include "rdn_gart.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
struct rdn_sleep_transaction {
 struct rdn_sleep_copy copy;
 struct rdn_sleep_runtime runtime;
 struct rdn_sleep_ib_ticket ticket;
 uint32_t started;
};
struct rdn_sleep_gart_transaction {
 struct rdn_sleep_copy copy;
 struct rdn_sleep_runtime runtime;
 struct rdn_sleep_gart_ib_ticket ticket;
 uint32_t started;
};
/* Caller owns all relevant locks, the private allocations, stage/descriptor,
 * quiesce object and IB writer. Existing whole-aperture client mappings can
 * still access an aperture IB; the caller must establish isolation. `write_ib`
 * may write only the private command allocation, must not publish work and
 * must preserve the existing hardware-specific byte order. No G5 caller exists.
 * `coherency_verified` is a caller assertion and must NOT be guessed. A failed
 * submission may leave the stage and allocations retained or quarantined. */
int rdn_sleep_transaction_start(struct rdn_sleep_transaction *,struct rdn_sleep_private *,
 struct rdn_accel *,struct rdn_quiesce *,struct rdn_stage *,struct rdn_gart *,
 int (*stage_matches)(void *,struct rdn_stage *,struct rdn_gart *),void *stage_cookie,
 int coherency_verified,int (*barrier)(void *),void *barrier_cookie,
 int (*write_ib)(void *,uint32_t,const uint32_t *,uint32_t),void *writer_cookie);
/* Separate pinned stages: one data destination and one kernel-owned GART IB.
 * Caller provides actual descriptor checks, exclusive locks, verified cache
 * handling, and retains both mappings through fence and safe teardown. */
int rdn_sleep_gart_transaction_start(struct rdn_sleep_gart_transaction *,struct rdn_sleep_private *,
 struct rdn_accel *,struct rdn_quiesce *,struct rdn_stage *data,struct rdn_stage *ib,struct rdn_gart *,
 int (*stage_matches)(void *,struct rdn_stage *,struct rdn_gart *),void *data_cookie,void *ib_cookie,
 int coherent,int (*barrier)(void *),void *barrier_cookie,
 int (*write_ib)(void *,const uint32_t *,uint32_t),int (*publish_ib)(void *),void *writer_cookie);
#endif
#endif
