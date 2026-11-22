/* Bounded powered test sequencing; no GPU, power or memory ownership. MIT */
#ifndef RDN_SLEEP_SEQUENCE_H
#define RDN_SLEEP_SEQUENCE_H
#include "rdn_sleep_guarded.h"
enum {RDN_SEQ_NEW,RDN_SEQ_READY,RDN_SEQ_WAITING,RDN_SEQ_CLEANUP,
      RDN_SEQ_PASSED,RDN_SEQ_FAILED,RDN_SEQ_QUARANTINED};
enum {RDN_SEQ_FILL,RDN_SEQ_GUARD_BEFORE,RDN_SEQ_TARGET,RDN_SEQ_GUARD_AFTER,RDN_SEQ_STEPS};
struct rdn_sleep_sequence {
 uint32_t state,step,generation,verified_mask,mismatches[3],failure,built;
};
struct rdn_sleep_sequence_commands {uint32_t words[RDN_SLEEP_FILL_WORDS],word_count;};
/* Caller serializes, owns the private buffers and applies the actual GPU
 * fence/cache/mapping protections. A submitted timeout is always uncertain. */
int rdn_sleep_sequence_begin(struct rdn_sleep_sequence *);
int rdn_sleep_sequence_build(struct rdn_sleep_sequence *,struct rdn_sleep_guarded *,
 uint64_t base,uint64_t vram,uint64_t aperture,uint64_t staging_gpu,uint64_t ib_gpu,
 struct rdn_sleep_sequence_commands *);
/* Only if publication definitely did not occur. */
int rdn_sleep_sequence_discard(struct rdn_sleep_sequence *);
/* Called only after the built command is actually published with a fence. */
int rdn_sleep_sequence_submitted(struct rdn_sleep_sequence *,uint32_t *generation);
/* Only call verified=1 after a real matching fence AND coherency check.
 * Fill has no bytes; readbacks require exactly one private staging page. */
int rdn_sleep_sequence_complete(struct rdn_sleep_sequence *,uint32_t generation,int verified,
                                const void *bytes,uint32_t length);
/* A submitted operation whose completion is unknown cannot be retried. */
int rdn_sleep_sequence_uncertain(struct rdn_sleep_sequence *,uint32_t generation);
/* Caller must first unmap both stages and release allocations safely. */
int rdn_sleep_sequence_cleanup(struct rdn_sleep_sequence *,int resources_released);
#endif
