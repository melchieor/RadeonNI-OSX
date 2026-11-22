/* Host-only test state machine. All hardware assertions are caller supplied. */
#include "rdn_sleep_sequence.h"
#ifdef KERNEL
#include <libkern/libkern.h>
#else
#include <string.h>
#endif
int rdn_sleep_sequence_begin(struct rdn_sleep_sequence *s)
{
 if(!s || s->state!=RDN_SEQ_NEW)return -1;
 memset(s,0,sizeof(*s));s->state=RDN_SEQ_READY;return 0;
}
int rdn_sleep_sequence_build(struct rdn_sleep_sequence *s,struct rdn_sleep_guarded *p,
 uint64_t base,uint64_t vram,uint64_t aperture,uint64_t staging,uint64_t ib,
 struct rdn_sleep_sequence_commands *out)
{
 struct rdn_sleep_sequence_commands tmp;struct rdn_sleep_fill_commands fill;
 struct rdn_sleep_dma_commands read;uint32_t n;
 uintptr_t a=(uintptr_t)s,b=(uintptr_t)out,c=(uintptr_t)p;
 if(!s || !p || !out || s->state!=RDN_SEQ_READY || s->step>=RDN_SEQ_STEPS || s->built ||
    a>UINTPTR_MAX-sizeof(*s) || b>UINTPTR_MAX-sizeof(*out) || c>UINTPTR_MAX-sizeof(*p) ||
    (a<b+sizeof(*out) && b<a+sizeof(*s)) || (c<b+sizeof(*out) && b<c+sizeof(*p)) ||
    (a<c+sizeof(*p) && c<a+sizeof(*s)))return -1;
 memset(&tmp,0,sizeof(tmp));
 if(s->step==RDN_SEQ_FILL) {
  if(rdn_sleep_guarded_fill(p,base,vram,aperture,ib,&fill))return -1;
  n=fill.word_count;if(n>RDN_SLEEP_FILL_WORDS)return -1;
  memcpy(tmp.words,fill.words,n*sizeof(uint32_t));
 } else {
  if(rdn_sleep_guarded_readback(p,s->step-1,base,vram,aperture,staging,ib,&read))return -1;
  n=read.word_count;if(n>RDN_SLEEP_FILL_WORDS)return -1;
  memcpy(tmp.words,read.words,n*sizeof(uint32_t));
 }
 tmp.word_count=n;memcpy(out,&tmp,sizeof(tmp));s->built=1;return 0;
}
int rdn_sleep_sequence_discard(struct rdn_sleep_sequence *s)
{if(!s || s->state!=RDN_SEQ_READY || !s->built)return -1;s->built=0;return 0;}
int rdn_sleep_sequence_submitted(struct rdn_sleep_sequence *s,uint32_t *generation)
{
 uintptr_t a=(uintptr_t)s,b=(uintptr_t)generation;
 if(!s || !generation || a>UINTPTR_MAX-sizeof(*s) || b>UINTPTR_MAX-sizeof(*generation) || (b&3) ||
    (a<b+sizeof(*generation) && b<a+sizeof(*s)) || s->state!=RDN_SEQ_READY || !s->built ||
    s->step>=RDN_SEQ_STEPS || s->generation==UINT32_MAX)return -1;
 ++s->generation;s->built=0;s->state=RDN_SEQ_WAITING;*generation=s->generation;return 0;
}
int rdn_sleep_sequence_complete(struct rdn_sleep_sequence *s,uint32_t generation,int verified,
                                const void *bytes,uint32_t length)
{
 uint32_t differences=0,page;
 if(!s || s->state!=RDN_SEQ_WAITING || generation!=s->generation)return -1;
 if(!verified){s->failure=1;s->state=RDN_SEQ_QUARANTINED;return -1;}
 if(s->step==RDN_SEQ_FILL) {if(bytes || length)return -1;}
 else {
  uintptr_t a=(uintptr_t)s,b=(uintptr_t)bytes;
  if(!bytes || length!=4096 || a>UINTPTR_MAX-sizeof(*s) || b>UINTPTR_MAX-length ||
     (a<b+length && b<a+sizeof(*s)))return -1;
  page=s->step-1;
  if(rdn_sleep_guarded_compare(page,bytes,length,&differences))return -1;
  s->mismatches[page]=differences;
  if(differences){s->failure=1;s->state=RDN_SEQ_CLEANUP;return -1;}
 }
 s->verified_mask|=1u<<s->step;++s->step;
 s->state=s->step==RDN_SEQ_STEPS?RDN_SEQ_CLEANUP:RDN_SEQ_READY;
 return 0;
}
int rdn_sleep_sequence_uncertain(struct rdn_sleep_sequence *s,uint32_t generation)
{
 if(!s || s->state!=RDN_SEQ_WAITING || generation!=s->generation)return -1;
 s->failure=1;s->state=RDN_SEQ_QUARANTINED;return 0;
}
int rdn_sleep_sequence_cleanup(struct rdn_sleep_sequence *s,int released)
{
 if(!s || s->state!=RDN_SEQ_CLEANUP || !released)return -1;
 s->state=(!s->failure && s->verified_mask==15u)?RDN_SEQ_PASSED:RDN_SEQ_FAILED;
 return 0;
}
