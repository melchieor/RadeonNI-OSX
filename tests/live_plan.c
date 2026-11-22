#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_live_plan.h"
static void *alloc_zero(void *cookie,size_t n){(void)cookie;return calloc(1,n);}
static void free_mem(void *cookie,void *p){(void)cookie;free(p);}
int main(void)
{
 struct rdn_os os;struct rdn_mem v,c,h;struct rdn_mem_range ranges[16];
 struct rdn_snapshot_span spans[16];struct rdn_live_plan_summary s,before;
 uint64_t off;memset(&os,0,sizeof(os));os.alloc=alloc_zero;os.free=free_mem;
 assert(!rdn_mem_init(&c,&os,0x2000,0x2000));
 assert(!rdn_mem_init(&v,&os,0x4000,0x4000));
 assert(!rdn_mem_init(&h,&os,0x8000,0x8000));
 assert(!rdn_mem_alloc(&c,0x1000,0x1000,&off)&&off==0x2000);
 assert(!rdn_mem_alloc(&v,0x2000,0x1000,&off)&&off==0x4000);
 assert(!rdn_mem_alloc(&h,0x1000,0x1000,&off)&&off==0x8000);
 assert(!rdn_mem_alloc(&h,0x1000,0x1000,&off)&&off==0x9000);
 assert(!rdn_live_plan_build(&v,&c,&h,0x10000,0x8000,ranges,spans,16,&s));
 assert(s.range_count==5&&s.reserved_bytes==0x2000&&s.command_bytes==0x1000&&
        s.visible_bytes==0x2000&&s.hidden_bytes==0x2000&&s.image_bytes==0x7000);
 assert(s.command_allocations==1&&s.visible_allocations==1&&s.hidden_allocations==2);
 assert(spans[0].vram_offset==0&&spans[0].size==0x2000&&spans[0].image_offset==0);
 assert(spans[4].vram_offset==0x9000&&spans[4].image_offset==0x6000&&spans[4].location==RDN_PLAN_HIDDEN);
 before=s;
 assert(rdn_live_plan_build(&v,&c,&h,0x10000,0x8000,ranges,spans,4,&s));
 assert(!memcmp(&s,&before,sizeof(s)));
 assert(rdn_live_plan_build(&v,&c,0,0x10000,0x8000,ranges,spans,16,&s));
 assert(rdn_live_plan_build(&v,&c,&h,0x10001,0x8000,ranges,spans,16,&s));
 assert(rdn_live_plan_build(&v,&c,&h,0x10000,0x7000,ranges,spans,16,&s));
 assert(!memcmp(&s,&before,sizeof(s)));
 rdn_mem_fini(&h);rdn_mem_fini(&v);rdn_mem_fini(&c);return 0;
}
