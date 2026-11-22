/* Experimental owner policy; no IOKit lifetime enforcement. MIT */
#ifndef RDN_SLEEP_OWNER_H
#define RDN_SLEEP_OWNER_H
#include "rdn_sleep_sequence_bridge.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
enum {RDN_OWNER_NEW,RDN_OWNER_ARMED,RDN_OWNER_INFLIGHT,RDN_OWNER_CLEAN,RDN_OWNER_QUARANTINED,RDN_OWNER_RELEASED};
enum {RDN_OWNER_ACCEL,RDN_OWNER_FRAMEBUFFER,RDN_OWNER_DATA_DESCRIPTOR,RDN_OWNER_IB_DESCRIPTOR,RDN_OWNER_REFS};
struct rdn_sleep_owner_ops {
 /* Failure from retain means no reference was acquired. */
 int (*retain)(void *,void *);void (*release)(void *,void *);
 /* Check both stage descriptors were completed outside the driver lock. */
 int (*descriptors_finished)(void *,void *,void *);
};
struct rdn_sleep_owner {
 uint32_t state,refs,client_attached,generation;
 void *objects[RDN_OWNER_REFS];
 struct rdn_sleep_sequence_bridge *bridge;
 struct rdn_sleep_guarded *owned;
 struct rdn_quiesce *quiesce;
 struct rdn_stage *data,*ib;
 const struct rdn_sleep_owner_ops *ops;void *ops_cookie;
};
/* Caller holds one lifetime/driver lock and supplies real retained objects.
 * Retaining objects does NOT stop their IOService stop/retire callbacks. */
int rdn_sleep_owner_arm(struct rdn_sleep_owner *,void *const objects[RDN_OWNER_REFS],
 const struct rdn_sleep_owner_ops *,void *,struct rdn_sleep_sequence_bridge *,
 struct rdn_sleep_guarded *,struct rdn_quiesce *,struct rdn_stage *,struct rdn_stage *);
int rdn_sleep_owner_may_submit(const struct rdn_sleep_owner *);
/* Called under the same lock immediately after the bridge reports submission. */
int rdn_sleep_owner_note_submit(struct rdn_sleep_owner *);
void rdn_sleep_owner_client_closed(struct rdn_sleep_owner *);
/* Tracks completed/uncertain bridge work; never frees a reference. */
int rdn_sleep_owner_observe(struct rdn_sleep_owner *);
/* Ordinary retirement is allowed only after explicit complete release. This
 * function cannot prevent forced IOKit termination by itself. */
int rdn_sleep_owner_may_retire(const struct rdn_sleep_owner *);
int rdn_sleep_owner_release(struct rdn_sleep_owner *);
#endif
#endif
