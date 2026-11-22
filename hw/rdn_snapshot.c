/* Bounded owned-buffer preservation rehearsal; not device restore. MIT */
#include <stddef.h>
#include "rdn_snapshot.h"
int rdn_snapshot_roundtrip(volatile uint32_t *region,uint32_t *backup,unsigned words,
                         void (*barrier)(void *),void *cookie,struct rdn_snapshot_result *out)
{
 unsigned i;uintptr_t a=(uintptr_t)region,b=(uintptr_t)backup;
 if(!out)return -1;
 out->saved=out->restored=out->poison_mismatches=out->restore_mismatches=0;
 if(!region || !backup || !barrier || !words || words>RDN_SNAPSHOT_WORDS ||
    (a&3) || (b&3) || a>UINTPTR_MAX-words*4u || b>UINTPTR_MAX-words*4u ||
    (a<b+words*4u && b<a+words*4u))return -1;
 barrier(cookie);
 for(i=0;i<words;i++){backup[i]=region[i];++out->saved;}
 for(i=0;i<words;i++)region[i]=~backup[i];
 barrier(cookie);
 for(i=0;i<words;i++)if(region[i]!=~backup[i])++out->poison_mismatches;
 /* Restoration is unconditional after mutation, including a failed poison check. */
 for(i=0;i<words;i++){region[i]=backup[i];++out->restored;}
 barrier(cookie);
 for(i=0;i<words;i++)if(region[i]!=backup[i])++out->restore_mismatches;
 return out->poison_mismatches || out->restore_mismatches?-1:0;
}
