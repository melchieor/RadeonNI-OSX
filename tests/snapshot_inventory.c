/* Production inventory and owned-page roundtrip with fault injection. MIT */
#include <assert.h>
#include <stdlib.h>
#include <stdio.h>
#include "../hw/rdn_mem.c"
#include "rdn_snapshot.h"
static void *allocate(void *c,size_t n){(void)c;return calloc(1,n);}
static void release(void *c,void *p){(void)c;free(p);}
struct fixture {unsigned barriers,fault;uint32_t *region;};
static void barrier(void *cookie)
{
 struct fixture *f=cookie;++f->barriers;
 if((f->fault==1 && f->barriers==2) || (f->fault==2 && f->barriers==3))f->region[9]^=1;
}
int main(void)
{
 struct rdn_os os={0};struct rdn_mem mem;struct rdn_mem_inventory before,after;
 uint64_t off1,off2;uint32_t region[1026],backup[1024];unsigned i;
 struct rdn_mem_range ranges[3]={{11,22},{33,44},{55,66}};uint32_t required=99;
 struct rdn_snapshot_result result;struct fixture f={0,0,region+1};
 os.alloc=allocate;os.free=release;
 assert(!rdn_mem_init(&mem,&os,0x2000000,0x100000));
 assert(!rdn_mem_inventory(&mem,&before)&&!before.allocations&&!before.used_bytes);
 assert(!rdn_mem_alloc(&mem,4096,4096,&off1));assert(!rdn_mem_alloc(&mem,8192,4096,&off2));
 assert(!rdn_mem_inventory(&mem,&after)&&after.allocations==2&&after.used_bytes==12288);
 assert(before.fingerprint!=after.fingerprint);before=after;
 assert(rdn_mem_snapshot_ranges(&mem,ranges,1,&required)&&required==2);
 assert(ranges[0].offset==11&&ranges[0].size==22&&ranges[1].offset==33);
 assert(rdn_mem_snapshot_ranges(&mem,NULL,2,&required)&&required==2);
 assert(!rdn_mem_snapshot_ranges(&mem,ranges,3,&required)&&required==2);
 assert(ranges[0].offset==off1&&ranges[0].size==4096);
 assert(ranges[1].offset==off2&&ranges[1].size==8192);
 assert(ranges[2].offset==55&&ranges[2].size==66);
 assert(rdn_mem_snapshot_ranges(&mem,ranges,3,NULL));
 assert(!rdn_mem_inventory(&mem,&after)&&before.fingerprint==after.fingerprint);
 uint64_t old=mem.head->start;mem.head->start++;assert(rdn_mem_inventory(&mem,&after));ranges[0].offset=123;assert(rdn_mem_snapshot_ranges(&mem,ranges,3,&required)&&required==0&&ranges[0].offset==123);mem.head->start=old;
 struct rdn_mem_block *next=mem.head->next;mem.head->next=mem.head;assert(rdn_mem_inventory(&mem,&after));mem.head->next=next;
 rdn_mem_free(&mem,off1);rdn_mem_free(&mem,off2);
 assert(!rdn_mem_inventory(&mem,&after)&&!after.allocations&&after.blocks==1&&!after.used_bytes);
 assert(!rdn_mem_snapshot_ranges(&mem,NULL,0,&required)&&required==0);
 rdn_mem_fini(&mem);
 for(unsigned iteration=0;iteration<1000;iteration++){
  for(i=0;i<1026;i++)region[i]=0xface0000u^i^iteration;
  f.barriers=0;f.fault=0;
  assert(!rdn_snapshot_roundtrip(region+1,backup,1024,barrier,&f,&result));
  assert(result.saved==1024&&result.restored==1024&&f.barriers==3);
  for(i=0;i<1026;i++)assert(region[i]==(0xface0000u^i^iteration));
 }
 f.barriers=0;f.fault=1;
 assert(rdn_snapshot_roundtrip(region+1,backup,1024,barrier,&f,&result));
 assert(result.poison_mismatches==1&&!result.restore_mismatches&&result.restored==1024);
 f.barriers=0;f.fault=2;
 assert(rdn_snapshot_roundtrip(region+1,backup,1024,barrier,&f,&result));
 assert(result.restore_mismatches==1&&result.restored==1024);
 assert(rdn_snapshot_roundtrip(region+1,region+2,1024,barrier,&f,&result));
 assert(!result.saved&&!result.restored);
 assert(rdn_snapshot_roundtrip(region+1,backup,1025,barrier,&f,&result));
 assert(rdn_snapshot_roundtrip(region+1,backup,0,barrier,&f,&result));
 assert(rdn_snapshot_roundtrip(region+1,backup,1024,0,&f,&result));
 puts("inventory partitions and 1000 owned-page save/poison/restore cycles passed; fault/overlap/bounds checks passed");
 return 0;
}
