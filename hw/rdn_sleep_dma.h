/* Command preparation only: no DMA submission, pinning or sleep. MIT */
#ifndef RDN_SLEEP_DMA_H
#define RDN_SLEEP_DMA_H
#include "rdn_cp_dma_readback.h"
struct rdn_sleep_dma_request {
 uint64_t vram_base,vram_bytes,aperture_bytes;
 uint64_t owned_offset,owned_bytes,progress;
 uint64_t staging_gpu,command_gpu;
 uint32_t staging_bytes,command_bytes;
};
struct rdn_sleep_dma_commands {
 uint32_t words[RDN_CP_DMA_READBACK_MAX_WORDS];
 uint32_t word_count,copy_bytes;
};
/* Trusted caller must prove exclusive ownership, pinned GART mappings, stable
 * allocation, visibility, synchronization and lock state. Request/output must
 * be separate. No submission, mapping, CPU read or hardware access occurs.
 * On failure the output is unchanged. Only a bounded hidden-VRAM -> staging
 * chunk is built; the caller must not advance progress without a real fence. */
int rdn_sleep_dma_build(const struct rdn_sleep_dma_request *,struct rdn_sleep_dma_commands *);
/* Variant for an independently owned, pinned GART command page. Caller must
 * prove its mapping and ownership; the builder only validates address ranges. */
int rdn_sleep_dma_build_gart_ib(const struct rdn_sleep_dma_request *,struct rdn_sleep_dma_commands *);
#endif
