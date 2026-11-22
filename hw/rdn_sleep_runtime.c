/* Real driver primitives behind guarded callbacks; currently no production caller. */
#include "rdn_sleep_runtime.h"
#include "rdn_accel_reg.h"
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
static int valid(struct rdn_sleep_runtime *r)
{
 return r && r->accel && r->accel->ready && r->accel->card && r->accel->card->os &&
  r->accel->card->os->mmio_read32 && r->accel->card->os->mmio_write32 &&
  (!r->accel->fence_memory || (r->accel->aperture && !(r->accel->fence_offset&3) &&
   r->accel->fence_offset<=r->accel->aperture_size && r->accel->aperture_size-r->accel->fence_offset>=4)) &&
  r->quiesce && r->stage &&
  r->stage->phase==RDN_STAGE_BOUND && r->quiesce->phase==RDN_QUIESCE_HELD_POWERED &&
  r->quiesce->internal_hold==1 &&
  (r->use_gart_ib ? (r->gart_ticket && r->copy && r->copy->stage==r->stage &&
   r->copy->extra_stage==r->command_stage && r->command_stage && r->command_stage!=r->stage &&
   r->command_stage->phase==RDN_STAGE_BOUND && r->gart && r->stage_matches &&
   r->stage_matches(r->data_stage_cookie,r->stage,r->gart) &&
   r->stage_matches(r->stage_cookie,r->command_stage,r->gart) &&
   r->gart_ticket->generation==r->quiesce->generation) :
   (r->ticket && r->ticket->generation==r->quiesce->generation)) &&
  r->accel->submission_gate==&r->quiesce->phase;
}
static int submit(void *cookie,uint32_t *fence)
{
 struct rdn_sleep_runtime *r=(struct rdn_sleep_runtime *)cookie;
 uint32_t observed;
 int result;
 if(!valid(r) || !fence || r->submitted || !r->words)return -1;
 /* Require the previous fence to be visible before publishing new work.
  * Refuse the all-ones value and wrap rather than confuse an inaccessible
  * device or a stale completion word with this transfer's fence. */
 if(r->accel->fence_emitted>=UINT32_MAX-1u)return -1;
 observed=r->accel->fence_memory ? rdn_vram_read32(r->accel,r->accel->fence_offset) :
  rdn_rreg(r->accel->card,RDN_SCRATCH_REG(1));
 if(observed==UINT32_MAX || observed!=r->accel->fence_emitted)return -1;
 if(r->use_gart_ib)
  result=rdn_ib_try_submit_sleep_gart(r->accel,r->quiesce,r->gart_ticket,r->command_stage,
      r->gart,r->stage_matches,r->stage_cookie,r->words,fence);
 else result=rdn_ib_try_submit_sleep(r->accel,r->quiesce,r->ticket,r->words,fence);
 if(result)return -1; /* try-submit failures are before publication */
 r->submitted=1;r->sequence=*fence;return 0;
}
static int poll_fence(void *cookie,uint32_t fence)
{
 struct rdn_sleep_runtime *r=(struct rdn_sleep_runtime *)cookie;
 uint32_t observed;
 if(!valid(r) || !r->submitted || fence!=r->sequence)return -1;
 /* A timeout makes ownership uncertain. A later-looking fence value must not
  * reverse that decision or permit this transfer's mappings to be retired. */
 if(r->timed_out)return -1;
 observed=r->accel->fence_memory ? rdn_vram_read32(r->accel,r->accel->fence_offset) :
  rdn_rreg(r->accel->card,RDN_SCRATCH_REG(1));
 /* All ones can mean an inaccessible PCI device. Never treat it as proof,
  * even when the legitimate sequence wraps to that value. The held gate
  * permits only this private submission, so require an exact match. */
 if(observed==UINT32_MAX)return -1;
 if(observed==fence){r->saw_fence=1;return 1;}
 return 0;
}
static int sync_cpu(void *cookie)
{
 struct rdn_sleep_runtime *r=(struct rdn_sleep_runtime *)cookie;
 if(!valid(r) || !r->submitted || !r->saw_fence || !r->coherency_verified || !r->cpu_read_barrier)return -1;
 rdn_hdp_flush(r->accel);
 return r->cpu_read_barrier(r->barrier_cookie);
}
const struct rdn_sleep_copy_ops rdn_sleep_runtime_ops={submit,poll_fence,sync_cpu};
#endif
