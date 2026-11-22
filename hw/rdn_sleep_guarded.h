/* Private three-page hidden-VRAM test planning; no submission. MIT */
#ifndef RDN_SLEEP_GUARDED_H
#define RDN_SLEEP_GUARDED_H
#include "rdn_mem.h"
#include "rdn_sleep_dma.h"
#define RDN_SLEEP_GUARD_PAGE 4096u
#define RDN_SLEEP_GUARD_PAGES 3u
#define RDN_SLEEP_FILL_WORDS 25u
struct rdn_sleep_guarded {struct rdn_mem *heap;uint64_t offset;uint32_t active;};
struct rdn_sleep_fill_commands {uint32_t words[RDN_SLEEP_FILL_WORDS];uint32_t word_count;};
/* Caller serializes and retains heap/descriptor ownership. This does not
 * protect against mappings or GPU agents outside the caller's control. */
int rdn_sleep_guarded_acquire(struct rdn_sleep_guarded *,struct rdn_mem *);
int rdn_sleep_guarded_fill(struct rdn_sleep_guarded *,uint64_t base,uint64_t vram,uint64_t aperture,
                           uint64_t command_gpu,struct rdn_sleep_fill_commands *);
int rdn_sleep_guarded_readback(struct rdn_sleep_guarded *,uint32_t page,uint64_t base,uint64_t vram,
                               uint64_t aperture,uint64_t staging_gpu,uint64_t command_gpu,
                               struct rdn_sleep_dma_commands *);
/* Only read after a verified fence and CPU coherency step. Pattern bytes are
 * compared as written by little-endian CP_DMA immediate fill. */
int rdn_sleep_guarded_compare(uint32_t page,const void *,uint32_t bytes,uint32_t *mismatches);
int rdn_sleep_guarded_release(struct rdn_sleep_guarded *,int safe);
#endif
