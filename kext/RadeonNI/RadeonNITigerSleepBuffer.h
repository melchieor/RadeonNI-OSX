/* Experimental private GART IB writer/readback, not wired to a client. MIT */
#ifndef RADEONNI_TIGER_SLEEP_BUFFER_H
#define RADEONNI_TIGER_SLEEP_BUFFER_H
#include "RadeonNITigerSleepStage.h"
extern "C" {
#include "rdn_sleep_runtime.h"
}
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
struct rdn_tiger_sleep_buffer {
 rdn_tiger_sleep_stage *stage;
 rdn_accel *accel;
};
/* Caller holds the staging and accelerator locks, owns this unpublished
 * descriptor and keeps it pinned until hardware fence completion. */
int rdn_tiger_sleep_write_ib(void *,const uint32_t *,uint32_t);
/* Cache operations fail closed; success alone does not prove PCI coherency.
 * Before GPU writes, the caller must eliminate dirty CPU cache lines and must
 * not touch the data buffer until completion and the subsequent sync. */
int rdn_tiger_sleep_publish_ib(void *);
int rdn_tiger_sleep_sync_data(void *);
/* Full CPU ordering barrier only; does not prove PCI snooping or invalidate
 * caches. Only use if the platform coherence contract is separately known. */
int rdn_tiger_sleep_cpu_barrier(void *);
/* Called only with matching completed/synchronized copy and private output. */
int rdn_tiger_sleep_copy_bytes(rdn_tiger_sleep_stage *,rdn_sleep_copy *,
                               rdn_sleep_runtime *,void *,uint32_t);
#endif
#endif
