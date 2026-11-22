#include "rdn_sleep_staging.h"
static int valid(const struct rdn_stage_ops *o)
{return o && o->pin && o->reserve && o->bus_page && o->set_page && o->clear_page && o->flush && o->unreserve && o->unpin;}
static int clean(struct rdn_stage *s,const struct rdn_stage_ops *o,void *ctx)
{
 uint32_t i;int failed=0;
 for(i=0;i<s->pages;i++)if(o->clear_page(ctx,s->offset+i*RDN_STAGE_PAGE))failed=1;
 if(s->pages && o->flush(ctx))failed=1;
 if(failed){s->phase=RDN_STAGE_QUARANTINED;return -1;}
 o->unreserve(ctx,s->offset,s->bytes);o->unpin(ctx);
 s->phase=RDN_STAGE_IDLE;s->bytes=s->offset=s->pages=0;return 0;
}
int rdn_stage_bind(struct rdn_stage *s,uint32_t bytes,const struct rdn_stage_ops *o,void *ctx)
{
 uint32_t at,off;uint64_t bus;
 if(!s || s->phase!=RDN_STAGE_IDLE || !valid(o) || !bytes || bytes>RDN_STAGE_MAX || (bytes&(RDN_STAGE_PAGE-1)))return -1;
 if(o->pin(ctx,bytes))return -1;
 s->phase=RDN_STAGE_PINNED;s->bytes=bytes;s->pages=0;
 if(o->reserve(ctx,bytes,&at)){o->unpin(ctx);s->phase=RDN_STAGE_IDLE;s->bytes=0;return -1;}
 s->offset=at;
 if(!at || (at&(RDN_STAGE_PAGE-1)) || at>UINT32_MAX-bytes) {clean(s,o,ctx);return -1;}
 for(off=0;off<bytes;off+=RDN_STAGE_PAGE) {
  bus=0;
  if(o->bus_page(ctx,off,&bus) || !bus || (bus&(RDN_STAGE_PAGE-1)) || bus>(1ull<<40)-RDN_STAGE_PAGE) {clean(s,o,ctx);return -1;}
  ++s->pages; /* set_page failure may still have modified this entry */
  if(o->set_page(ctx,at+off,bus)){clean(s,o,ctx);return -1;}
 }
 if(o->flush(ctx)){s->phase=RDN_STAGE_QUARANTINED;return -1;}
 s->phase=RDN_STAGE_BOUND;return 0;
}
int rdn_stage_unbind(struct rdn_stage *s,int completed,const struct rdn_stage_ops *o,void *ctx)
{
 if(!s || !valid(o) || s->phase!=RDN_STAGE_BOUND || !completed)return -1;
 return clean(s,o,ctx);
}
