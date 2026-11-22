/* Host-tested VRAM range planning only; no GPU access. SPDX-License-Identifier: MIT */
#ifndef RDN_SNAPSHOT_PLAN_H
#define RDN_SNAPSHOT_PLAN_H
#include <stdint.h>
#include "rdn_mem.h"

#define RDN_PLAN_MAX_RANGES 1024u
enum rdn_snapshot_location { RDN_PLAN_VISIBLE=1, RDN_PLAN_HIDDEN=2 };
struct rdn_snapshot_span {
 uint64_t vram_offset, size, image_offset;
 uint32_t location;
};
/* Input and output must be distinct, nonoverlapping arrays. The caller holds
 * all allocator locks across range capture and plan construction. A successful
 * plan covers ONLY the supplied ranges: never reserved regions or mappings.
 * No output span is written on failure. Image offsets pack ranges without
 * padding. Hidden spans require a future, separately validated transfer path. */
int rdn_snapshot_plan(const struct rdn_mem_range *ranges, uint32_t count,
                      uint64_t vram_size, uint64_t aperture_size,
                      uint64_t image_capacity, struct rdn_snapshot_span *out,
                      uint32_t capacity, uint64_t *required_bytes);
#endif
