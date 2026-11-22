/* Host-tested builders for a bounded test of kernel-owned hidden VRAM. MIT */
#include "rdn_sleep_guarded.h"
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <string.h>
#endif
#define LIMIT (1ull<<40)
static const uint32_t patterns[3]={0x13579bdfu,0x2468ace0u,0x89abcdefu};
static int valid(struct rdn_sleep_guarded *p,uint64_t base,uint64_t vram,uint64_t aperture)
{
 return p && p->active && p->heap && !(p->offset&4095) && base<LIMIT &&
  vram && vram<=LIMIT-base && aperture && aperture<=vram && !(base&4095) &&
  p->offset>=aperture && p->offset<vram && 3u*4096u<=vram-p->offset &&
  rdn_mem_allocation_size(p->heap,p->offset)==3u*4096u;
}
int rdn_sleep_guarded_acquire(struct rdn_sleep_guarded *p,struct rdn_mem *hidden)
{
 uint64_t offset=0;
 if(!p || p->active || !hidden)return -1;
 if(rdn_mem_alloc(hidden,3u*4096u,4096,&offset))return -1;
 p->heap=hidden;p->offset=offset;p->active=1;return 0;
}
int rdn_sleep_guarded_fill(struct rdn_sleep_guarded *p,uint64_t base,uint64_t vram,uint64_t aperture,
                           uint64_t ib,struct rdn_sleep_fill_commands *out)
{
 struct rdn_cp_dma_fill fills[3];struct rdn_cp_dma_span command;
 struct rdn_sleep_fill_commands tmp;uint32_t n=0,i;uintptr_t a=(uintptr_t)p,b=(uintptr_t)out;
 if(!out || !p || a>UINTPTR_MAX-sizeof(*p) || b>UINTPTR_MAX-sizeof(*out) ||
    (a<b+sizeof(*out) && b<a+sizeof(*p)) || !valid(p,base,vram,aperture) ||
    ib>=LIMIT || 4096>LIMIT-ib || (ib&4095) || (ib<base+vram && base<ib+4096))return -1;
 memset(fills,0,sizeof(fills));memset(&tmp,0,sizeof(tmp));
 for(i=0;i<3;i++){fills[i].destination.address=base+p->offset+(uint64_t)i*4096;fills[i].destination.bytes=4096;fills[i].value=patterns[i];}
 command.address=ib;command.bytes=4096;command.reserved=0;
 if(rdn_cp_dma_fill_build_list(fills,3,&command,tmp.words,sizeof(tmp.words),&n) || n!=RDN_SLEEP_FILL_WORDS)return -1;
 tmp.word_count=n;memcpy(out,&tmp,sizeof(tmp));return 0;
}
int rdn_sleep_guarded_readback(struct rdn_sleep_guarded *p,uint32_t page,uint64_t base,uint64_t vram,
                               uint64_t aperture,uint64_t staging,uint64_t ib,struct rdn_sleep_dma_commands *out)
{
 struct rdn_sleep_dma_request req;uintptr_t a=(uintptr_t)p,b=(uintptr_t)out;
 if(page>=3 || !p || !out || a>UINTPTR_MAX-sizeof(*p) || b>UINTPTR_MAX-sizeof(*out) ||
    (a<b+sizeof(*out) && b<a+sizeof(*p)) || !valid(p,base,vram,aperture))return -1;
 req.vram_base=base;req.vram_bytes=vram;req.aperture_bytes=aperture;
 req.owned_offset=p->offset+(uint64_t)page*4096;req.owned_bytes=4096;req.progress=0;
 req.staging_gpu=staging;req.staging_bytes=4096;req.command_gpu=ib;req.command_bytes=4096;
 return rdn_sleep_dma_build_gart_ib(&req,out);
}
int rdn_sleep_guarded_compare(uint32_t page,const void *bytes,uint32_t length,uint32_t *mismatches)
{
 const uint8_t *p=(const uint8_t *)bytes;uint32_t n=0,i;uintptr_t a=(uintptr_t)bytes,b=(uintptr_t)mismatches;
 if(page>=3 || !bytes || !mismatches || length!=4096 || a>UINTPTR_MAX-length ||
    b>UINTPTR_MAX-sizeof(*mismatches) || (b&3) || (a<b+sizeof(*mismatches) && b<a+length))return -1;
 for(i=0;i<length;i++)if(p[i]!=(uint8_t)(patterns[page]>>(8*(i&3))))++n;
 *mismatches=n;return 0;
}
int rdn_sleep_guarded_release(struct rdn_sleep_guarded *p,int safe)
{
 if(!p || !p->active || !p->heap || !safe || rdn_mem_allocation_size(p->heap,p->offset)!=3u*4096u)return -1;
 rdn_mem_free(p->heap,p->offset);p->heap=0;p->offset=0;p->active=0;return 0;
}
