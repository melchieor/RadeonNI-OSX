#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_guarded.h"
static void *alloc_mem(void *p,size_t n){(void)p;return calloc(1,n);}
static void free_mem(void *p,void *v){(void)p;free(v);}
int main(void)
{
 struct rdn_os os={0};struct rdn_mem heap,small;struct rdn_sleep_guarded p={0};
 struct rdn_sleep_fill_commands fill,fill_before;struct rdn_sleep_dma_commands read,read_before;
 const uint32_t patterns[]={0x13579bdfu,0x2468ace0u,0x89abcdefu};
 unsigned char bytes[4096];uint32_t mismatches=99,i,j;uint64_t free_before;
 os.alloc=alloc_mem;os.free=free_mem;
 assert(!rdn_mem_init(&heap,&os,0x10000000,0x10000));assert(!rdn_mem_init(&small,&os,0x20000000,4096));
 assert(rdn_sleep_guarded_acquire(&p,&small) && !p.active);
 free_before=rdn_mem_available(&heap);assert(!rdn_sleep_guarded_acquire(&p,&heap) && p.active);
 assert(rdn_sleep_guarded_acquire(&p,&heap));
 memset(&fill,0xa5,sizeof(fill));fill_before=fill;
 assert(rdn_sleep_guarded_fill(&p,0,0x80000000,0x10000000,0x20000,&fill) && !memcmp(&fill,&fill_before,sizeof(fill)));
 assert(!rdn_sleep_guarded_fill(&p,0,0x80000000,0x10000000,0x80002000,&fill));
 assert(fill.word_count==25 && fill.words[6]==patterns[0] && fill.words[8]==0x10000000 &&
        fill.words[12]==patterns[1] && fill.words[14]==0x10001000 && fill.words[18]==patterns[2] && fill.words[20]==0x10002000);
 memset(&read,0xa5,sizeof(read));read_before=read;
 assert(rdn_sleep_guarded_readback(&p,3,0,0x80000000,0x10000000,0x80001000,0x80002000,&read) && !memcmp(&read,&read_before,sizeof(read)));
 for(i=0;i<3;i++) {
  assert(!rdn_sleep_guarded_readback(&p,i,0,0x80000000,0x10000000,0x80001000,0x80002000,&read));
  assert(read.copy_bytes==4096 && read.words[6]==0x10000000+i*4096 && read.words[8]==0x80001000);
  for(j=0;j<4096;j++)bytes[j]=(unsigned char)(patterns[i]>>(8*(j&3)));
  assert(!rdn_sleep_guarded_compare(i,bytes,4096,&mismatches) && !mismatches);
  bytes[3]^=1;bytes[4000]^=1;assert(!rdn_sleep_guarded_compare(i,bytes,4096,&mismatches) && mismatches==2);
 }
 mismatches=7;assert(rdn_sleep_guarded_compare(3,bytes,4096,&mismatches) && mismatches==7);
 assert(rdn_sleep_guarded_compare(0,bytes,4095,&mismatches) && mismatches==7);
 assert(rdn_sleep_guarded_release(&p,0) && p.active && rdn_mem_available(&heap)==free_before-3*4096);
 assert(!rdn_sleep_guarded_release(&p,1) && !p.active && rdn_mem_available(&heap)==free_before);
 rdn_mem_fini(&heap);rdn_mem_fini(&small);return 0;
}
