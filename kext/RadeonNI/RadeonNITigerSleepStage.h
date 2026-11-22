/* Experimental standalone Tiger adapter: not wired into RadeonNI. MIT */
#ifndef RADEONNI_TIGER_SLEEP_STAGE_H
#define RADEONNI_TIGER_SLEEP_STAGE_H
#include <IOKit/IOBufferMemoryDescriptor.h>
extern "C" {
#include "rdn_sleep_staging.h"
#include "rdn_sleep_copy.h"
#include "rdn_mem.h"
#include "rdn_gart.h"
}
struct rdn_tiger_sleep_stage {
 IOBufferMemoryDescriptor *memory;
 IOBufferMemoryDescriptor *finished_descriptor;
 struct rdn_mem *space;
 struct rdn_gart *gart;
 struct rdn_stage stage;
 UInt32 size;
 bool prepared,release_pending;
};
struct rdn_tiger_sleep_stage_pair {
 rdn_tiger_sleep_stage *data,*ib;
 IOBufferMemoryDescriptor *data_descriptor,*ib_descriptor;
};
/* Caller zero-initializes the object. prepare/finish may block and MUST run
 * outside the GART/allocator lock. bind/unbind MUST hold that lock. Keep the
 * object and descriptor alive if stage enters quarantine or finish fails. */
int rdn_tiger_sleep_stage_prepare(struct rdn_tiger_sleep_stage *,UInt32);
int rdn_tiger_sleep_stage_bind_locked(struct rdn_tiger_sleep_stage *,struct rdn_mem *,struct rdn_gart *);
int rdn_tiger_sleep_stage_unbind_locked(struct rdn_tiger_sleep_stage *,bool completed_and_synced);
int rdn_tiger_sleep_stage_finish(struct rdn_tiger_sleep_stage *);
/* The caller retains the descriptors and keeps the pair and stages alive. */
int rdn_tiger_sleep_pair_init(rdn_tiger_sleep_stage_pair *,rdn_tiger_sleep_stage *,rdn_tiger_sleep_stage *);
int rdn_tiger_sleep_pair_finished(void *,void *,void *);
int rdn_tiger_sleep_stage_matches(void *,struct rdn_stage *,struct rdn_gart *);
int rdn_tiger_sleep_stage_unstage_copy_locked(struct rdn_tiger_sleep_stage *,struct rdn_sleep_copy *,bool consumed);
int rdn_tiger_sleep_stage_unstage_pair_locked(struct rdn_tiger_sleep_stage *,struct rdn_tiger_sleep_stage *,struct rdn_sleep_copy *,bool consumed);
#endif
