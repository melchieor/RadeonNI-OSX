/* Experimental private-RAM physical mapping owner; not a sleep implementation. */
#ifndef RADEONNI_TIGER_PHYSICAL_PROBE_H
#define RADEONNI_TIGER_PHYSICAL_PROBE_H
#ifdef RDN_PHYSICAL_PROBE_TEST
#include "physical_probe_mocks.h"
#else
#include <IOKit/IOBufferMemoryDescriptor.h>
#endif

struct rdn_tiger_physical_probe {
 IOBufferMemoryDescriptor *owner;
 IOMemoryDescriptor *physical;
 IOMemoryMap *mapping;
 bool prepared, redirect_active, uncertain;
};
/* All operations require the caller's exclusive lock. The structure must be
 * zero-initialized and remain alive while any mapping or redirect exists. */
int rdn_physical_probe_prepare(rdn_tiger_physical_probe *);
/* Return an additional map reference for the IOKit caller. The retained
 * private reference is held until explicit unmap. No device BAR is involved. */
IOMemoryMap *rdn_physical_probe_map(rdn_tiger_physical_probe *,task_t,IOOptionBits,IOVirtualAddress);
int rdn_physical_probe_redirect(rdn_tiger_physical_probe *,bool);
/* Failure retains all remaining objects; caller must quarantine the entire
 * structure until a stronger recovery proof or reboot, never free its owner. */
int rdn_physical_probe_finish(rdn_tiger_physical_probe *);
#endif
