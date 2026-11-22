#include <assert.h>
#include <stdint.h>
#include <string.h>
#include "rdn_snapshot_plan.h"
int main(void)
{
 struct rdn_mem_range ranges[]={{0x1000,0x1000},{0x10000000,0x2000},{0x3000,0x1000}};
 struct rdn_snapshot_span out[3], original[3];uint64_t required;
 memset(out,0xa5,sizeof(out));memcpy(original,out,sizeof(out));
 assert(!rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x4000,out,3,&required));
 assert(required==0x4000 && out[0].location==RDN_PLAN_VISIBLE && out[1].location==RDN_PLAN_HIDDEN);
 assert(out[0].image_offset==0 && out[1].image_offset==0x1000 && out[2].image_offset==0x3000);
 memcpy(out,original,sizeof(out));
 assert(rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x3fff,out,3,&required) && required==0x4000);
 assert(!memcmp(out,original,sizeof(out)));
 assert(rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x4000,out,2,&required));
 assert(!memcmp(out,original,sizeof(out)));
 ranges[2].offset=0x1800;assert(rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x4000,out,3,&required));
 ranges[2].offset=0xffff800;assert(rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x4000,out,3,&required));
 ranges[2].offset=UINT64_MAX-3;ranges[2].size=8;assert(rdn_snapshot_plan(ranges,3,UINT64_MAX,0x10000000,UINT64_MAX,out,3,&required));
 ranges[2].offset=0x3000;ranges[2].size=0;assert(rdn_snapshot_plan(ranges,3,0x80000000,0x10000000,0x4000,out,3,&required));
 assert(!memcmp(out,original,sizeof(out)));
 assert(!rdn_snapshot_plan(0,0,0x80000000,0x10000000,0,0,0,&required) && required==0);
 assert(rdn_snapshot_plan(ranges,RDN_PLAN_MAX_RANGES+1,0x80000000,0x10000000,UINT64_MAX,out,3,&required));
 return 0;
}
