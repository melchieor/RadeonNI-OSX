/* Experimental fence/flush callbacks; not linked to a driver by default. MIT */
#ifndef RDN_SLEEP_RUNTIME_H
#define RDN_SLEEP_RUNTIME_H
#include "rdn_accel.h"
#include "rdn_quiesce.h"
#include "rdn_sleep_staging.h"
#include "rdn_sleep_copy.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
struct rdn_sleep_runtime {
 struct rdn_accel *accel;
 struct rdn_quiesce *quiesce;
 struct rdn_stage *stage;
 struct rdn_sleep_ib_ticket *ticket;
 struct rdn_sleep_gart_ib_ticket *gart_ticket;
 struct rdn_stage *command_stage;
 struct rdn_sleep_copy *copy;
 struct rdn_gart *gart;
 int (*stage_matches)(void *,struct rdn_stage *,struct rdn_gart *);
 void *stage_cookie;
 void *data_stage_cookie;
 int use_gart_ib;
 uint32_t words,sequence;
 int submitted,saw_fence,timed_out,coherency_verified;
 /* Return 0 only after the platform's documented CPU read barrier succeeds. */
 int (*cpu_read_barrier)(void *);
 void *barrier_cookie;
};
/* Caller serializes all callbacks under the actual driver lock and guarantees
 * power, valid pointers, private IB and stage ownership. A timeout must never
 * be interpreted as completed DMA. coherency_verified is a caller assertion,
 * not a hardware check; no current caller sets it for the G5. */
extern const struct rdn_sleep_copy_ops rdn_sleep_runtime_ops;
#endif
#endif
