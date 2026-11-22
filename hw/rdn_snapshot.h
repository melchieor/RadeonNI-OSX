/* Bounded owned-buffer preservation rehearsal; not device restore. MIT */
#ifndef RDN_SNAPSHOT_H
#define RDN_SNAPSHOT_H
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define RDN_SNAPSHOT_WORDS 1024u
struct rdn_snapshot_result { uint32_t saved,restored,poison_mismatches,restore_mismatches; };
/* Caller guarantees exclusive ownership, retained power and a valid mapped span.
   backup must not overlap the mapped span; barrier must order device accesses. */
int rdn_snapshot_roundtrip(volatile uint32_t *region,uint32_t *backup,unsigned words,
                         void (*barrier)(void *),void *cookie,struct rdn_snapshot_result *);
#ifdef __cplusplus
}
#endif
#endif
