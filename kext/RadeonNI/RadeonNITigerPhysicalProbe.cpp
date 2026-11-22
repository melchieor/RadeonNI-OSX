/* Experimental private system RAM only; never map device memory here. */
#include "RadeonNITigerPhysicalProbe.h"

/* Tiger's kernel.6.0 declares these lower-level page-table symbols. Use the
 * exact Tiger PPC implementation of kvtophys64 as a reference: lookup the
 * page then append its offset. This remains experimental until loader-tested. */
#ifndef RDN_PHYSICAL_PROBE_TEST
extern "C" void *kernel_pmap;
extern "C" UInt32 pmap_find_phys(void *,addr64_t);
static addr64_t physical_witness(addr64_t virtual_address)
{
 UInt32 page=pmap_find_phys(kernel_pmap,virtual_address);
 return page?(((addr64_t)page<<12)|(virtual_address&0xfff)):0;
}
#else
#define physical_witness kvtophys64
#endif
enum { kProbePage=4096 };
int rdn_physical_probe_prepare(rdn_tiger_physical_probe *p)
{
#ifndef RDN_PHYSICAL_PROBE_TEST
 /* Quarantined after the Tiger G5 DART panic. Only mock tests may enter. */
 (void)p;return -1;
#endif
 if(!p || p->owner || p->physical || p->mapping || p->prepared || p->uncertain || p->redirect_active)return -1;
 p->owner=IOBufferMemoryDescriptor::withOptions(kIODirectionInOut,kProbePage,kProbePage);
 if(!p->owner)return -1;
 if(p->owner->prepare()!=kIOReturnSuccess){p->owner->release();p->owner=0;return -1;}
 p->prepared=true;
 IOByteCount length=0;
 addr64_t address=p->owner->getPhysicalSegment64(0,&length);
 void *bytes=p->owner->getBytesNoCopy();
 addr64_t witness=bytes?physical_witness((addr64_t)(uintptr_t)bytes):0;
 if(!address || !witness || witness!=address || (address & (kProbePage-1)) || address>0xfffff000ULL || length<kProbePage ||
    p->owner->performOperation(kIOMemoryIncoherentIOFlush,0,kProbePage)!=kIOReturnSuccess) {
  if(rdn_physical_probe_finish(p))p->uncertain=true;
  return -1;
 }
 p->physical=IOMemoryDescriptor::withPhysicalAddress((IOPhysicalAddress)address,kProbePage,kIODirectionInOut);
 if(!p->physical){if(rdn_physical_probe_finish(p))p->uncertain=true;return -1;}
 return 0;
}
IOMemoryMap *rdn_physical_probe_map(rdn_tiger_physical_probe *p,task_t task,IOOptionBits flags,IOVirtualAddress at)
{
 if(!p || !p->prepared || !p->owner || !p->physical || p->mapping || p->uncertain || !task)return 0;
 IOMemoryMap *m=p->physical->map(task,at,(flags&kIOMapUserOptionsMask)|kIOMapUnique);
 if(!m)return 0;
 p->mapping=m;
 /* IOKit consumes its return reference; this object retains the initial one. */
 m->retain();
 return m;
}
int rdn_physical_probe_redirect(rdn_tiger_physical_probe *p,bool enter)
{
 if(!p || !p->mapping || !p->prepared || !p->owner || !p->physical || p->uncertain || p->redirect_active==enter)return -1;
 IOMemoryDescriptor *restore=enter?0:p->mapping->getMemoryDescriptor();
 if(!enter && !restore){p->uncertain=true;return -1;}
 /* A failed enter may still have partially changed mapping state. */
 if(p->mapping->redirect(restore,0,0)!=kIOReturnSuccess){p->uncertain=true;return -1;}
 p->redirect_active=enter;
 return 0;
}
int rdn_physical_probe_finish(rdn_tiger_physical_probe *p)
{
 if(!p || p->uncertain || p->redirect_active)return -1;
 if(p->mapping){
  if(p->mapping->unmap()!=kIOReturnSuccess){p->uncertain=true;return -1;}
  p->mapping->release();p->mapping=0;
 }
 if(p->physical){p->physical->release();p->physical=0;}
 if(p->prepared){
  if(!p->owner || p->owner->complete()!=kIOReturnSuccess){p->uncertain=true;return -1;}
  p->prepared=false;
 }
 if(p->owner){p->owner->release();p->owner=0;}
 return 0;
}
