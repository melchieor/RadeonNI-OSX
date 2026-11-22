/* Callback-driven staging lifecycle, not connected to IOKit or GPU. MIT */
#ifndef RDN_SLEEP_STAGING_H
#define RDN_SLEEP_STAGING_H
#include <stdint.h>
#define RDN_STAGE_PAGE 4096u
#define RDN_STAGE_MAX (4u*1024u*1024u)
enum {RDN_STAGE_IDLE,RDN_STAGE_PINNED,RDN_STAGE_BOUND,RDN_STAGE_QUARANTINED};
struct rdn_stage {uint32_t phase,bytes,offset,pages;};
struct rdn_stage_ops {
 int (*pin)(void *,uint32_t); /* failure leaves nothing pinned */
 int (*reserve)(void *,uint32_t,uint32_t *); /* failure reserves nothing */
 int (*bus_page)(void *,uint32_t,uint64_t *); /* I/O-mapped bus address */
 int (*set_page)(void *,uint32_t,uint64_t); /* failure MAY have written PTE */
 int (*clear_page)(void *,uint32_t); /* 0 only if clear succeeded */
 int (*flush)(void *); /* 0 only if invalidation completed */
 void (*unreserve)(void *,uint32_t,uint32_t);
 void (*unpin)(void *);
};
/* Caller supplies serialization, valid I/O-mapper addresses and a pinned
 * descriptor retained until unpin. Callback contracts must be proven for
 * the real OS. On uncertain PTE cleanup/flush the stage is quarantined and
 * neither mapping nor pages may be reused. No hardware calls are included. */
int rdn_stage_bind(struct rdn_stage *,uint32_t,const struct rdn_stage_ops *,void *);
/* Only after a genuine GPU fence and CPU synchronization; caller proves it. */
int rdn_stage_unbind(struct rdn_stage *,int completed,const struct rdn_stage_ops *,void *);
#endif
