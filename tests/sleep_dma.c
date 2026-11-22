#include <assert.h>
#include <string.h>
#include "rdn_sleep_dma.h"
int main(void)
{
 struct rdn_sleep_dma_request r={0,0x80000000,0x10000000,0x10000000,0x500000,0,0x100000000ull,0x20000,0x200000,4096};
 struct rdn_sleep_dma_commands o,saved;
 memset(&o,0xa5,sizeof(o));saved=o;
 assert(!rdn_sleep_dma_build(&r,&o));
 assert(o.copy_bytes==0x200000 && o.word_count==19);
 assert(o.words[5]==0xc0044100 && o.words[6]==0x10000000 && o.words[7]==0);
 assert(o.words[8]==0 && o.words[9]==1 && o.words[10]==0x100000);
 r.progress=0x400000;assert(!rdn_sleep_dma_build(&r,&o) && o.copy_bytes==0x100000);
 r.progress=0;o=saved;r.staging_gpu=0x1000;assert(rdn_sleep_dma_build(&r,&o));assert(!memcmp(&o,&saved,sizeof(o)));
 r.staging_gpu=0x100000000ull;r.command_gpu=0x10000000;assert(rdn_sleep_dma_build(&r,&o));
 r.command_gpu=0x20000;r.owned_offset=0xffff000;assert(rdn_sleep_dma_build(&r,&o));
 r.owned_offset=0x10000000;r.command_bytes=16;assert(rdn_sleep_dma_build(&r,&o));
 r.command_bytes=4096;r.progress=r.owned_bytes;assert(rdn_sleep_dma_build(&r,&o));
 r.progress=1;assert(rdn_sleep_dma_build(&r,&o));
 r.progress=0;r.owned_bytes=0x80000001;assert(rdn_sleep_dma_build(&r,&o));
 r.owned_bytes=0x500000;r.vram_base=1;assert(rdn_sleep_dma_build(&r,&o));
 r.owned_bytes=0x500000;r.vram_base=(1ull<<40)-4;assert(rdn_sleep_dma_build(&r,&o));
 assert(!memcmp(&o,&saved,sizeof(o)));
 r.vram_base=0;r.command_gpu=0x100400000ull;r.command_bytes=4096;
 assert(!rdn_sleep_dma_build_gart_ib(&r,&o) && o.copy_bytes==0x200000);
 o=saved;r.command_gpu=r.staging_gpu;
 assert(rdn_sleep_dma_build_gart_ib(&r,&o) && !memcmp(&o,&saved,sizeof(o)));
 r.command_gpu=0x20000;assert(rdn_sleep_dma_build_gart_ib(&r,&o));
 r.command_gpu=0x100400001ull;assert(rdn_sleep_dma_build_gart_ib(&r,&o));
 r.command_gpu=0x100400000ull;r.command_bytes=2048;assert(rdn_sleep_dma_build_gart_ib(&r,&o));
 assert(!memcmp(&o,&saved,sizeof(o)));
 return 0;
}
