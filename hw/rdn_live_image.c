/* Chunked CPU-synchronous image storage with fail-closed transitions. MIT. */
#include "rdn_live_image.h"
#include <string.h>

struct rdn_image_chunk {struct rdn_image_chunk *next;uint32_t size;unsigned char data[1];};
static void clear(struct rdn_live_image *image)
{
 struct rdn_image_chunk *p=image->chunks;
 while(p){struct rdn_image_chunk *next=p->next;image->os->free(image->os->cookie,p);p=next;}
 if(image->spans)image->os->free(image->os->cookie,image->spans);
 memset(image,0,sizeof(*image));
}
int rdn_live_image_prepare(struct rdn_live_image *image,struct rdn_os *os,
 const struct rdn_snapshot_span *spans,uint32_t count,uint64_t bytes,
 uint32_t chunk_bytes,uint64_t budget,uint32_t generation)
{
 uint64_t total=0,left,chunks,overhead,plan_bytes;uint32_t i,j;struct rdn_image_chunk **tail;
 if(!image||image->phase!=RDN_IMAGE_EMPTY||!os||!os->alloc||!os->free||
    !spans||!count||count>RDN_PLAN_MAX_RANGES||!bytes||bytes>budget||!generation||
    chunk_bytes<4096||chunk_bytes>65536||(chunk_bytes&4095))return -1;
 for(i=0;i<count;i++) {
  const struct rdn_snapshot_span *s=&spans[i];
  if(!s->size||s->image_offset!=total||s->vram_offset>UINT64_MAX-s->size||
     total>UINT64_MAX-s->size||(s->location!=RDN_PLAN_VISIBLE&&s->location!=RDN_PLAN_HIDDEN))return -1;
  for(j=0;j<i;j++) {
   const struct rdn_snapshot_span *p=&spans[j];
   if(s->vram_offset<p->vram_offset+p->size&&p->vram_offset<s->vram_offset+s->size)return -1;
  }
  total+=s->size;
 }
 if(total!=bytes)return -1;
 chunks=bytes/chunk_bytes;
 if(bytes-chunks*chunk_bytes)++chunks;
 plan_bytes=(uint64_t)count*sizeof(*spans);
 if(chunks>UINT64_MAX/(sizeof(struct rdn_image_chunk)-1u))return -1;
 overhead=chunks*(sizeof(struct rdn_image_chunk)-1u);
 if(plan_bytes>budget-bytes || overhead>budget-bytes-plan_bytes)return -1;
 image->os=os;image->bytes=bytes;image->count=count;image->chunk_bytes=chunk_bytes;image->generation=generation;
 image->spans=(struct rdn_snapshot_span *)os->alloc(os->cookie,(size_t)count*sizeof(*spans));
 if(!image->spans){clear(image);return -1;}
 memcpy(image->spans,spans,(size_t)count*sizeof(*spans));tail=&image->chunks;left=bytes;
 while(left) {
  uint32_t n=left<chunk_bytes?(uint32_t)left:chunk_bytes;
  struct rdn_image_chunk *chunk=(struct rdn_image_chunk *)os->alloc(os->cookie,sizeof(*chunk)-1+n);
  if(!chunk){clear(image);return -1;}
  chunk->next=0;chunk->size=n;*tail=chunk;tail=&chunk->next;left-=n;
 }
 image->phase=RDN_IMAGE_PREPARED;return 0;
}
int rdn_live_image_matches(const struct rdn_live_image *image,const struct rdn_snapshot_span *spans,
 uint32_t count,uint64_t bytes,uint32_t generation)
{
 if(!image||(image->phase!=RDN_IMAGE_PREPARED&&image->phase!=RDN_IMAGE_CAPTURED)||!spans||!image->spans||
    count!=image->count||bytes!=image->bytes||generation!=image->generation)return 0;
 for(uint32_t i=0;i<count;i++)if(spans[i].vram_offset!=image->spans[i].vram_offset||
    spans[i].size!=image->spans[i].size||spans[i].image_offset!=image->spans[i].image_offset||
    spans[i].location!=image->spans[i].location)return 0;
 return 1;
}
static uint32_t hash_image(const struct rdn_live_image *image)
{
 uint32_t h=2166136261u;const struct rdn_image_chunk *c;
 for(c=image->chunks;c;c=c->next)for(uint32_t i=0;i<c->size;i++)h=(h^c->data[i])*16777619u;
 return h;
}
static int transfer(struct rdn_live_image *image,const struct rdn_live_image_ops *ops,void *cookie,int write)
{
 struct rdn_image_chunk *chunk=image->chunks;uint32_t in_chunk=0;
 for(uint32_t i=0;i<image->count;i++) {
  const struct rdn_snapshot_span *s=&image->spans[i];uint64_t done=0;
  while(done<s->size) {
   uint64_t left=s->size-done;uint32_t n;
   if(!chunk||in_chunk>=chunk->size||!ops->stable(cookie,image->generation))return -1;
   n=chunk->size-in_chunk;if(left<n)n=(uint32_t)left;
   if(write ? ops->write(cookie,s->location,s->vram_offset+done,chunk->data+in_chunk,n) :
              ops->read(cookie,s->location,s->vram_offset+done,chunk->data+in_chunk,n))return -1;
   done+=n;in_chunk+=n;if(in_chunk==chunk->size){chunk=chunk->next;in_chunk=0;}
  }
 }
 return chunk||in_chunk||!ops->stable(cookie,image->generation)?-1:0;
}
int rdn_live_image_capture(struct rdn_live_image *image,const struct rdn_live_image_ops *ops,void *cookie,
 const struct rdn_snapshot_span *current,uint32_t count,uint64_t bytes,uint32_t generation)
{
 if(!image||image->phase!=RDN_IMAGE_PREPARED||!rdn_live_image_matches(image,current,count,bytes,generation)||
    !ops||!ops->stable||!ops->read)return -1;
 if(transfer(image,ops,cookie,0)){image->phase=RDN_IMAGE_INVALID;return -1;}
 image->checksum=hash_image(image);image->phase=RDN_IMAGE_CAPTURED;return 0;
}
int rdn_live_image_restore(struct rdn_live_image *image,const struct rdn_live_image_ops *ops,void *cookie,
 const struct rdn_snapshot_span *current,uint32_t count,uint64_t bytes,uint32_t generation)
{
 if(!image||image->phase!=RDN_IMAGE_CAPTURED||!ops||!ops->stable||!ops->write||
    !rdn_live_image_matches(image,current,count,bytes,generation)||
    !ops->stable(cookie,image->generation)||hash_image(image)!=image->checksum)return -1;
 /* Mark dirty before first callback; no failure path may claim restoration. */
 image->phase=RDN_IMAGE_DIRTY;
 if(transfer(image,ops,cookie,1))return -1;
 image->phase=RDN_IMAGE_RESTORED;return 0;
}
int rdn_live_image_dispose(struct rdn_live_image *image,int discard_dirty)
{
 if(!image||image->phase==RDN_IMAGE_EMPTY||!image->os||!image->os->free||
    (image->phase==RDN_IMAGE_DIRTY&&!discard_dirty))return -1;
 clear(image);return 0;
}
