/* Capture a conservative VRAM range plan while the caller holds allocator locks. MIT. */
#ifndef RDN_LIVE_PLAN_H
#define RDN_LIVE_PLAN_H
#include "rdn_snapshot_plan.h"
#ifdef __cplusplus
extern "C" {
#endif

struct rdn_live_plan_summary {
 uint32_t range_count,visible_allocations,command_allocations,hidden_allocations;
 uint64_t reserved_bytes,visible_bytes,command_bytes,hidden_bytes,image_bytes;
};

/* Includes the entire reserved aperture prefix and every used block in the
 * three heaps. The caller owns separate scratch/output arrays and serializes
 * allocator access for the whole call. Success does not cover CPU-side GART
 * backing, metadata, device registers or any GPU power transition. Neither
 * contents nor hardware are read. Failure must never be treated as coverage. */
int rdn_live_plan_build(struct rdn_mem *visible,struct rdn_mem *command,
 struct rdn_mem *hidden,uint64_t vram_bytes,uint64_t aperture_bytes,
 struct rdn_mem_range *scratch,struct rdn_snapshot_span *spans,uint32_t capacity,
 struct rdn_live_plan_summary *summary);
#ifdef __cplusplus
}
#endif
#endif
