/* Prototype private allocations for a powered copy test; MIT. */
#ifndef RDN_SLEEP_PRIVATE_H
#define RDN_SLEEP_PRIVATE_H
#include "rdn_mem.h"
#include "rdn_sleep_dma.h"
#define RDN_SLEEP_PRIVATE_PAGE 4096u
struct rdn_sleep_private {
 struct rdn_mem *hidden,*commands;
 uint64_t hidden_offset,command_offset;
 uint32_t active;
};
/* Caller holds both allocator locks for every operation, retains the returned
 * object, and MUST never publish either buffer to any other client. */
int rdn_sleep_private_acquire(struct rdn_sleep_private *,struct rdn_mem *,struct rdn_mem *);
int rdn_sleep_private_build(struct rdn_sleep_private *,uint64_t vram_base,uint64_t vram_size,
                            uint64_t aperture_size,uint64_t staging_gpu,uint32_t staging_bytes,
                            struct rdn_sleep_dma_commands *);
int rdn_sleep_private_build_gart_ib(struct rdn_sleep_private *,uint64_t vram_base,uint64_t vram_size,
 uint64_t aperture_size,uint64_t staging_gpu,uint32_t staging_bytes,uint64_t command_gpu,
 struct rdn_sleep_dma_commands *);
/* safe requires completed fence, successful sync and safe GART teardown.
 * A false or uncertain value keeps both allocations reserved. */
int rdn_sleep_private_release(struct rdn_sleep_private *,int safe);
#endif
