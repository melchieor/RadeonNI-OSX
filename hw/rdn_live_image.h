/* Chunked VRAM snapshot storage. Not a suspend/wake implementation. MIT. */
#ifndef RDN_LIVE_IMAGE_H
#define RDN_LIVE_IMAGE_H
#include "rdn_snapshot_plan.h"
#ifdef __cplusplus
extern "C" {
#endif

enum { RDN_IMAGE_EMPTY=0,RDN_IMAGE_PREPARED=1,RDN_IMAGE_CAPTURED=2,
       RDN_IMAGE_INVALID=3,RDN_IMAGE_DIRTY=4,RDN_IMAGE_RESTORED=5 };
struct rdn_image_chunk;
struct rdn_live_image {
 struct rdn_os *os;
 struct rdn_snapshot_span *spans;
 struct rdn_image_chunk *chunks;
 uint64_t bytes;
 uint32_t count,chunk_bytes,phase,generation,checksum;
};
struct rdn_live_image_ops {
 /* Caller must already exclude allocators, GPU submissions, mappings/writers,
  * timers, and provider termination. This callback is an additional check;
  * it cannot itself establish exclusive access or PCI/MMIO availability. */
 int (*stable)(void *cookie,uint32_t generation);
 /* CPU-synchronous only: callback may not leave device DMA using the buffer. */
 int (*read)(void *cookie,uint32_t location,uint64_t offset,void *dst,uint32_t bytes);
 int (*write)(void *cookie,uint32_t location,uint64_t offset,const void *src,uint32_t bytes);
};
/* Prepare all memory before admission closes. Budget includes image bytes,
 * chunk headers and the copied plan (not allocator overhead). Plan is copied.
 * Caller must rebuild/compare it under the actual exclusive gate. */
int rdn_live_image_prepare(struct rdn_live_image *,struct rdn_os *,
 const struct rdn_snapshot_span *,uint32_t count,uint64_t bytes,
 uint32_t chunk_bytes,uint64_t budget,uint32_t generation);
int rdn_live_image_matches(const struct rdn_live_image *,const struct rdn_snapshot_span *,
 uint32_t count,uint64_t bytes,uint32_t generation);
int rdn_live_image_capture(struct rdn_live_image *,const struct rdn_live_image_ops *,void *cookie,
 const struct rdn_snapshot_span *current,uint32_t count,uint64_t bytes,uint32_t generation);
/* A failed write can leave VRAM partially restored: image remains DIRTY. */
int rdn_live_image_restore(struct rdn_live_image *,const struct rdn_live_image_ops *,void *cookie,
 const struct rdn_snapshot_span *current,uint32_t count,uint64_t bytes,uint32_t generation);
/* DIRTY images require an explicit discard decision by the recovery owner. */
int rdn_live_image_dispose(struct rdn_live_image *,int discard_dirty);
#ifdef __cplusplus
}
#endif
#endif
