/* Conservative allocator range planning; this code never accesses the GPU. MIT. */
#include "rdn_live_plan.h"
#include <string.h>

int rdn_live_plan_build(struct rdn_mem *visible,struct rdn_mem *command,
 struct rdn_mem *hidden,uint64_t vram_bytes,uint64_t aperture_bytes,
 struct rdn_mem_range *scratch,struct rdn_snapshot_span *spans,uint32_t capacity,
 struct rdn_live_plan_summary *summary)
{
 struct rdn_mem_inventory vi,ci,hi;
 struct rdn_live_plan_summary result;
 uint32_t n=1,got=0;uint64_t required=0;
 if(!visible||!command||!scratch||!spans||!summary||!capacity||
    capacity>RDN_PLAN_MAX_RANGES||!vram_bytes||aperture_bytes>vram_bytes||
    !command->base||command->base>aperture_bytes||
    command->size>aperture_bytes-command->base||
    visible->base!=command->base+command->size||
    visible->base>aperture_bytes||visible->size!=aperture_bytes-visible->base)
  return -1;
 if((vram_bytes>aperture_bytes && (!hidden||hidden->base!=aperture_bytes||
      hidden->size!=vram_bytes-aperture_bytes))||
    (vram_bytes==aperture_bytes && hidden))return -1;
 memset(&result,0,sizeof(result));memset(&hi,0,sizeof(hi));
 if(rdn_mem_inventory(visible,&vi)||rdn_mem_inventory(command,&ci)||
    (hidden&&rdn_mem_inventory(hidden,&hi)))return -1;
 if(vi.allocations>capacity-1||ci.allocations>capacity-1-vi.allocations||
    hi.allocations>capacity-1-vi.allocations-ci.allocations)return -1;
 scratch[0].offset=0;scratch[0].size=command->base;
 if(rdn_mem_snapshot_ranges(command,scratch+n,capacity-n,&got)||got!=ci.allocations)return -1;
 n+=got;
 if(rdn_mem_snapshot_ranges(visible,scratch+n,capacity-n,&got)||got!=vi.allocations)return -1;
 n+=got;
 if(hidden){if(rdn_mem_snapshot_ranges(hidden,scratch+n,capacity-n,&got)||got!=hi.allocations)return -1;n+=got;}
 if(rdn_snapshot_plan(scratch,n,vram_bytes,aperture_bytes,UINT64_MAX,spans,capacity,&required))return -1;
 result.range_count=n;result.visible_allocations=vi.allocations;
 result.command_allocations=ci.allocations;result.hidden_allocations=hi.allocations;
 result.reserved_bytes=command->base;result.visible_bytes=vi.used_bytes;
 result.command_bytes=ci.used_bytes;result.hidden_bytes=hi.used_bytes;result.image_bytes=required;
 *summary=result;return 0;
}
