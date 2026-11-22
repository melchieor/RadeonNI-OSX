#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_sleep_private.h"
static void *allocate(void *p,size_t n){(void)p;return calloc(1,n);}
static void release(void *p,void *v){(void)p;free(v);}
int main(void)
{
 struct rdn_os os={0};struct rdn_mem hidden,commands,tiny;struct rdn_sleep_private p={0};
 struct rdn_sleep_dma_commands out,before;uint64_t used;
 os.alloc=allocate;os.free=release;
 assert(!rdn_mem_init(&hidden,&os,0x10000000,0x20000));
 assert(!rdn_mem_init(&commands,&os,0x20000,0x20000));
 assert(!rdn_mem_init(&tiny,&os,0x40000,2048));
 used=rdn_mem_available(&hidden);assert(rdn_sleep_private_acquire(&p,&hidden,&tiny));
 assert(rdn_mem_available(&hidden)==used && !p.active);
 assert(rdn_sleep_private_acquire(&p,&hidden,&hidden));
 assert(!rdn_sleep_private_acquire(&p,&hidden,&commands) && p.active);
 assert(rdn_sleep_private_acquire(&p,&hidden,&commands));
 memset(&out,0xa5,sizeof(out));before=out;
 assert(rdn_sleep_private_build(&p,0,0x80000000,0x10000000,0x100000000ull,16,&out));
 assert(!memcmp(&out,&before,sizeof(out)));
 assert(!rdn_sleep_private_build(&p,0,0x80000000,0x10000000,0x100000000ull,4096,&out));
 assert(out.copy_bytes==4096 && out.words[6]==p.hidden_offset && out.words[8]==0 && out.words[9]==1);
 assert(rdn_sleep_private_release(&p,0) && p.active && rdn_mem_available(&hidden)==used-4096);
 assert(!rdn_sleep_private_release(&p,1) && !p.active && rdn_mem_available(&hidden)==used);
 assert(rdn_sleep_private_release(&p,1));
 rdn_mem_fini(&hidden);rdn_mem_fini(&commands);rdn_mem_fini(&tiny);return 0;
}
