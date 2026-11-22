#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include "rdn_live_image.h"
struct ctx {unsigned char mem[65536],original[65536];int live,reads,writes,fail_read,fail_write,fail_after;
 unsigned allocs,frees;unsigned char *first_read;};
static void *allocate(void *c,size_t n){struct ctx *x=c;if(x->fail_after>=0&&(int)x->allocs>=x->fail_after)return 0;++x->allocs;return calloc(1,n);}
static void release(void *c,void *p){struct ctx *x=c;++x->frees;free(p);}
static int stable(void *c,uint32_t gen){struct ctx *x=c;return x->live&&gen==7;}
static int read_mem(void *c,uint32_t loc,uint64_t off,void *dst,uint32_t n){
 struct ctx *x=c;(void)loc;assert(off+n<=sizeof(x->mem));++x->reads;if(x->fail_read==x->reads)return -1;
 if(!x->first_read)x->first_read=dst;memcpy(dst,x->mem+off,n);return 0;}
static int write_mem(void *c,uint32_t loc,uint64_t off,const void *src,uint32_t n){
 struct ctx *x=c;(void)loc;assert(off+n<=sizeof(x->mem));++x->writes;if(x->fail_write==x->writes)return -1;
 memcpy(x->mem+off,src,n);return 0;}
static void seed(struct ctx *c){for(unsigned i=0;i<sizeof(c->mem);i++)c->mem[i]=(unsigned char)(i*17u^(i>>8));memcpy(c->original,c->mem,sizeof(c->mem));}
int main(void)
{
 struct ctx c;struct rdn_os os;struct rdn_live_image img;struct rdn_snapshot_span plan[3],changed[3];
 struct rdn_live_image_ops ops={stable,read_mem,write_mem};
 memset(&c,0,sizeof(c));c.live=1;c.fail_after=-1;seed(&c);memset(&os,0,sizeof(os));
 os.cookie=&c;os.alloc=allocate;os.free=release;memset(&img,0,sizeof(img));memset(plan,0,sizeof(plan));
 plan[0].vram_offset=0;plan[0].size=5000;plan[0].location=RDN_PLAN_VISIBLE;
 plan[1].vram_offset=20000;plan[1].size=5000;plan[1].image_offset=5000;plan[1].location=RDN_PLAN_VISIBLE;
 plan[2].vram_offset=40000;plan[2].size=7000;plan[2].image_offset=10000;plan[2].location=RDN_PLAN_HIDDEN;
 assert(rdn_live_image_prepare(&img,&os,plan,3,17000,4096,16999,7));
 assert(img.phase==RDN_IMAGE_EMPTY&&!c.allocs);
 assert(rdn_live_image_prepare(&img,&os,plan,3,17000,4096,17000,7));
 assert(img.phase==RDN_IMAGE_EMPTY&&!c.allocs);
 c.fail_after=3;assert(rdn_live_image_prepare(&img,&os,plan,3,17000,4096,30000,7));
 assert(img.phase==RDN_IMAGE_EMPTY&&c.allocs==c.frees);c.fail_after=-1;
 assert(!rdn_live_image_prepare(&img,&os,plan,3,17000,4096,30000,7));
 memcpy(changed,plan,sizeof(plan));changed[1].vram_offset++;
 assert(!rdn_live_image_matches(&img,changed,3,17000,7));
 assert(rdn_live_image_capture(&img,&ops,&c,changed,3,17000,7)&&!c.reads&&img.phase==RDN_IMAGE_PREPARED);
 assert(!rdn_live_image_capture(&img,&ops,&c,plan,3,17000,7)&&img.phase==RDN_IMAGE_CAPTURED);
 memset(c.mem,0x55,sizeof(c.mem));
 assert(rdn_live_image_restore(&img,&ops,&c,changed,3,17000,7)&&!c.writes&&img.phase==RDN_IMAGE_CAPTURED);c.live=0;
 assert(rdn_live_image_restore(&img,&ops,&c,plan,3,17000,7)&&!c.writes&&img.phase==RDN_IMAGE_CAPTURED);c.live=1;
 assert(!rdn_live_image_restore(&img,&ops,&c,plan,3,17000,7)&&img.phase==RDN_IMAGE_RESTORED);
 assert(!memcmp(c.mem,c.original,5000)&&!memcmp(c.mem+20000,c.original+20000,5000)&&!memcmp(c.mem+40000,c.original+40000,7000));
 assert(c.mem[10000]==0x55&&c.mem[30000]==0x55);
 assert(!rdn_live_image_dispose(&img,0)&&c.allocs==c.frees);
 seed(&c);c.reads=c.writes=0;c.first_read=0;
 assert(!rdn_live_image_prepare(&img,&os,plan,3,17000,4096,30000,7));
 assert(!rdn_live_image_capture(&img,&ops,&c,plan,3,17000,7));
 c.first_read[0]^=1;assert(rdn_live_image_restore(&img,&ops,&c,plan,3,17000,7)&&!c.writes&&img.phase==RDN_IMAGE_CAPTURED);
 assert(!rdn_live_image_dispose(&img,0));
 c.first_read=0;c.reads=c.writes=0;c.fail_write=2;
 assert(!rdn_live_image_prepare(&img,&os,plan,3,17000,4096,30000,7));
 assert(!rdn_live_image_capture(&img,&ops,&c,plan,3,17000,7));
 assert(rdn_live_image_restore(&img,&ops,&c,plan,3,17000,7)&&img.phase==RDN_IMAGE_DIRTY&&c.writes==2);
 assert(rdn_live_image_dispose(&img,0)&&img.phase==RDN_IMAGE_DIRTY);
 assert(!rdn_live_image_dispose(&img,1)&&c.allocs==c.frees);
 c.fail_write=0;c.fail_read=2;c.reads=0;
 assert(!rdn_live_image_prepare(&img,&os,plan,3,17000,4096,30000,7));
 assert(rdn_live_image_capture(&img,&ops,&c,plan,3,17000,7)&&img.phase==RDN_IMAGE_INVALID);
 assert(!rdn_live_image_dispose(&img,0)&&c.allocs==c.frees);
 changed[1]=plan[1];changed[1].vram_offset=4000;
 assert(rdn_live_image_prepare(&img,&os,changed,3,17000,4096,30000,7));
 return 0;
}
