/* Experimental reference adapter. It does not stop IOService retirement. */
#ifndef RADEONNI_TIGER_SLEEP_OWNER_H
#define RADEONNI_TIGER_SLEEP_OWNER_H
#include "RadeonNITigerSleepStage.h"
#include <libkern/c++/OSObject.h>
extern "C" {
#include "rdn_sleep_owner.h"
}
#ifdef RDN_SLEEP_INTERNAL_EXPERIMENT
struct rdn_tiger_sleep_owner {
 struct rdn_sleep_owner owner;
 struct rdn_tiger_sleep_stage_pair pair;
};
/* Caller serializes the adapter and guarantees service/stage lifetime while
 * arming. Objects must be actual OSObject-derived instances. */
int rdn_tiger_sleep_owner_arm(rdn_tiger_sleep_owner *,OSObject *,OSObject *,
 struct rdn_sleep_sequence_bridge *,struct rdn_sleep_guarded *,struct rdn_quiesce *,
 rdn_tiger_sleep_stage *,rdn_tiger_sleep_stage *);
#endif
#endif
