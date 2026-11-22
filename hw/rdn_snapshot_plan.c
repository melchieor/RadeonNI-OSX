/* Allocated-range capture planning, not a suspend implementation. MIT */
#include "rdn_snapshot_plan.h"
int rdn_snapshot_plan(const struct rdn_mem_range *ranges, uint32_t count,
                      uint64_t vram_size, uint64_t aperture_size,
                      uint64_t image_capacity, struct rdn_snapshot_span *out,
                      uint32_t capacity, uint64_t *required_bytes)
{
 uint64_t total=0;uint32_t i,j;
 if (!required_bytes) return -1;
 *required_bytes=0;
 if (!vram_size || aperture_size>vram_size || count>RDN_PLAN_MAX_RANGES ||
     (count && (!ranges || !out)) || capacity<count) return -1;
 for (i=0;i<count;i++) {
  uint64_t start=ranges[i].offset, size=ranges[i].size, end;
  if (!size || start>=vram_size || size>vram_size-start || total>UINT64_MAX-size) return -1;
  end=start+size;
  if (start<aperture_size && end>aperture_size) return -1;
  for (j=0;j<i;j++) {
   uint64_t other=ranges[j].offset, other_end=other+ranges[j].size;
   if (start<other_end && other<end) return -1;
  }
  total+=size;
 }
 *required_bytes=total;
 if (total>image_capacity) return -1;
 total=0;
 for (i=0;i<count;i++) {
  out[i].vram_offset=ranges[i].offset;out[i].size=ranges[i].size;
  out[i].image_offset=total;
  out[i].location=ranges[i].offset<aperture_size?RDN_PLAN_VISIBLE:RDN_PLAN_HIDDEN;
  total+=ranges[i].size;
 }
 return 0;
}
