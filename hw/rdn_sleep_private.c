#include "rdn_sleep_private.h"
int rdn_sleep_private_acquire(struct rdn_sleep_private *p,struct rdn_mem *hidden,struct rdn_mem *commands)
{
 uint64_t h=0,c=0;
 if(!p || p->active || !hidden || !commands || hidden==commands)return -1;
 if(rdn_mem_alloc(hidden,RDN_SLEEP_PRIVATE_PAGE,RDN_SLEEP_PRIVATE_PAGE,&h))return -1;
 if(rdn_mem_alloc(commands,RDN_SLEEP_PRIVATE_PAGE,RDN_SLEEP_PRIVATE_PAGE,&c)) {
  rdn_mem_free(hidden,h);return -1;
 }
 p->hidden=hidden;p->commands=commands;p->hidden_offset=h;p->command_offset=c;p->active=1;
 return 0;
}
int rdn_sleep_private_build(struct rdn_sleep_private *p,uint64_t base,uint64_t size,
                            uint64_t aperture,uint64_t staging,uint32_t staging_bytes,
                            struct rdn_sleep_dma_commands *out)
{
 struct rdn_sleep_dma_request req;
 if(!p || !p->active || !p->hidden || !p->commands || !out || staging_bytes<RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(p->hidden,p->hidden_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(p->commands,p->command_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    base>UINT64_MAX-p->command_offset)return -1;
 req.vram_base=base;req.vram_bytes=size;req.aperture_bytes=aperture;
 req.owned_offset=p->hidden_offset;req.owned_bytes=RDN_SLEEP_PRIVATE_PAGE;req.progress=0;
 req.staging_gpu=staging;req.staging_bytes=staging_bytes;
 req.command_gpu=base+p->command_offset;req.command_bytes=RDN_SLEEP_PRIVATE_PAGE;
 return rdn_sleep_dma_build(&req,out);
}
int rdn_sleep_private_release(struct rdn_sleep_private *p,int safe)
{
 if(!p || !p->active || !safe || !p->hidden || !p->commands || p->hidden==p->commands ||
    rdn_mem_allocation_size(p->hidden,p->hidden_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(p->commands,p->command_offset)!=RDN_SLEEP_PRIVATE_PAGE)return -1;
 rdn_mem_free(p->hidden,p->hidden_offset);rdn_mem_free(p->commands,p->command_offset);
 p->hidden=0;p->commands=0;p->hidden_offset=p->command_offset=0;p->active=0;return 0;
}
int rdn_sleep_private_build_gart_ib(struct rdn_sleep_private *p,uint64_t base,uint64_t size,
 uint64_t aperture,uint64_t staging,uint32_t staging_bytes,uint64_t command,
 struct rdn_sleep_dma_commands *out)
{
 struct rdn_sleep_dma_request req;
 if(!p || !p->active || !p->hidden || !p->commands || !out || staging_bytes<RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(p->hidden,p->hidden_offset)!=RDN_SLEEP_PRIVATE_PAGE ||
    rdn_mem_allocation_size(p->commands,p->command_offset)!=RDN_SLEEP_PRIVATE_PAGE)return -1;
 req.vram_base=base;req.vram_bytes=size;req.aperture_bytes=aperture;
 req.owned_offset=p->hidden_offset;req.owned_bytes=RDN_SLEEP_PRIVATE_PAGE;req.progress=0;
 req.staging_gpu=staging;req.staging_bytes=staging_bytes;
 req.command_gpu=command;req.command_bytes=RDN_SLEEP_PRIVATE_PAGE;
 return rdn_sleep_dma_build_gart_ib(&req,out);
}
