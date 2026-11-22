/* Transfer lifetime model; not a DMA submitter. SPDX-License-Identifier: MIT */
#ifndef RDN_SNAPSHOT_TRANSFER_H
#define RDN_SNAPSHOT_TRANSFER_H
#include <stdint.h>
enum rdn_transfer_phase { RDN_TRANSFER_IDLE, RDN_TRANSFER_PREPARED,
 RDN_TRANSFER_INFLIGHT, RDN_TRANSFER_READY, RDN_TRANSFER_QUARANTINED };
struct rdn_snapshot_transfer { uint32_t phase; uint32_t fence; };
/* Caller owns the lock. Model only: caller must actually pin mappings and
 * enforce all required barriers; these calls do not provide either. */
int rdn_transfer_prepare(struct rdn_snapshot_transfer *, int mappings_pinned, int gate_closed);
int rdn_transfer_submitted(struct rdn_snapshot_transfer *, uint32_t fence);
int rdn_transfer_complete(struct rdn_snapshot_transfer *, uint32_t fence, int cpu_synchronized);
int rdn_transfer_abort_before_submit(struct rdn_snapshot_transfer *);
/* Ambiguous submission/completion means resources must remain retained. */
int rdn_transfer_uncertain(struct rdn_snapshot_transfer *);
int rdn_transfer_release(struct rdn_snapshot_transfer *);
#endif
