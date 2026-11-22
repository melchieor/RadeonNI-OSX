/* Host-only first step for bounded VRAM -> GART copies. MIT */
#include <stddef.h>
#include <stdint.h>
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <string.h>
#endif
#include "rdn_sleep_dma.h"
#define RDN_DMA_LIMIT (1ull<<40)
static int span(uint64_t base,uint64_t size)
{ return size && base<RDN_DMA_LIMIT && size<=RDN_DMA_LIMIT-base; }
static int overlap(uint64_t a,uint64_t n,uint64_t b,uint64_t m)
{ return a<b+m && b<a+n; }
int rdn_sleep_dma_build(const struct rdn_sleep_dma_request *r,struct rdn_sleep_dma_commands *out)
{
 struct rdn_sleep_dma_commands tmp;
 struct rdn_cp_dma_span src,dst;
 uint64_t remain,srcaddr,vramend;uint32_t bytes,words=0;
 uintptr_t a=(uintptr_t)r,b=(uintptr_t)out;
 if(!r || !out || a>UINTPTR_MAX-sizeof(*r) || b>UINTPTR_MAX-sizeof(*out) ||
    (a<b+sizeof(*out) && b<a+sizeof(*r)))return -1;
 if(!span(r->vram_base,r->vram_bytes) || !r->aperture_bytes || r->aperture_bytes>r->vram_bytes ||
    r->owned_offset<r->aperture_bytes || r->owned_offset>=r->vram_bytes || !r->owned_bytes ||
    r->owned_bytes>r->vram_bytes-r->owned_offset || r->progress>=r->owned_bytes ||
    !span(r->staging_gpu,r->staging_bytes) || !span(r->command_gpu,r->command_bytes) ||
    r->command_bytes>4096 || (r->command_gpu&63) ||
    ((r->vram_base|r->vram_bytes|r->aperture_bytes|r->owned_offset|r->owned_bytes|
      r->progress|r->staging_gpu|r->staging_bytes|r->command_bytes)&3))return -1;
 vramend=r->vram_base+r->vram_bytes;
 if(r->command_gpu<r->vram_base || r->command_gpu-r->vram_base>=r->aperture_bytes ||
    r->command_bytes>r->aperture_bytes-(r->command_gpu-r->vram_base) ||
    overlap(r->staging_gpu,r->staging_bytes,r->vram_base,r->vram_bytes))return -1;
 remain=r->owned_bytes-r->progress;bytes=r->staging_bytes;
 if(bytes>RDN_CP_DMA_READBACK_MAX_BYTES)bytes=RDN_CP_DMA_READBACK_MAX_BYTES;
 if(remain<bytes)bytes=(uint32_t)remain;
 srcaddr=r->vram_base+r->owned_offset+r->progress;
 if(srcaddr>=vramend || !bytes)return -1;
 src.address=srcaddr;src.bytes=bytes;src.reserved=0;
 dst.address=r->staging_gpu;dst.bytes=bytes;dst.reserved=0;
 memset(&tmp,0,sizeof(tmp));
 if(rdn_cp_dma_readback_build(&src,&dst,bytes,tmp.words,sizeof(tmp.words),&words) ||
    words>r->command_bytes/4)return -1;
 tmp.word_count=words;tmp.copy_bytes=bytes;
 memcpy(out,&tmp,sizeof(tmp));return 0;
}
int rdn_sleep_dma_build_gart_ib(const struct rdn_sleep_dma_request *r,struct rdn_sleep_dma_commands *out)
{
 struct rdn_sleep_dma_request tmp;
 struct rdn_sleep_dma_commands commands;
 uintptr_t a=(uintptr_t)r,b=(uintptr_t)out;
 if(!r || !out || a>UINTPTR_MAX-sizeof(*r) || b>UINTPTR_MAX-sizeof(*out) ||
    (a<b+sizeof(*out) && b<a+sizeof(*r)))return -1;
 if(!span(r->vram_base,r->vram_bytes) || !span(r->staging_gpu,r->staging_bytes) ||
    !span(r->command_gpu,r->command_bytes) || r->command_bytes!=4096 ||
    (r->command_gpu&4095) || (r->vram_base&63) ||
    overlap(r->command_gpu,r->command_bytes,r->vram_base,r->vram_bytes) ||
    overlap(r->command_gpu,r->command_bytes,r->staging_gpu,r->staging_bytes))return -1;
 /* The packet generator doesn't encode the IB address. Reuse its existing
  * visible-IB validation with a placeholder; the real IB was checked above. */
 tmp=*r;tmp.command_gpu=r->vram_base;
 if(rdn_sleep_dma_build(&tmp,&commands))return -1;
 memcpy(out,&commands,sizeof(commands));return 0;
}
