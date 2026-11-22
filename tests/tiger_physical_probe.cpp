#include <assert.h>
#include "RadeonNITigerPhysicalProbe.h"
bool IOMemoryDescriptor::physical_fail=false,IOMemoryDescriptor::map_fail=false;
int IOMemoryDescriptor::physical_releases=0;IOMemoryMap *IOMemoryDescriptor::last=0;
bool IOBufferMemoryDescriptor::alloc_fail=false,IOBufferMemoryDescriptor::prepare_fail=false,IOBufferMemoryDescriptor::complete_fail=false;
addr64_t IOBufferMemoryDescriptor::address=0x1000;IOByteCount IOBufferMemoryDescriptor::length=4096;
int IOBufferMemoryDescriptor::released=0,IOBufferMemoryDescriptor::completed=0;
bool IOBufferMemoryDescriptor::flush_fail=false;static addr64_t witness=0x1000;
addr64_t kvtophys64(addr64_t){return witness;}
IOMemoryDescriptor *IOMemoryDescriptor::withPhysicalAddress(IOPhysicalAddress,IOByteCount,int){return physical_fail?0:new IOMemoryDescriptor;}
IOMemoryMap *IOMemoryDescriptor::map(task_t,IOVirtualAddress,IOOptionBits flags){assert(flags&kIOMapUnique);return map_fail?0:(last=new IOMemoryMap(this));}
int main(){
 rdn_tiger_physical_probe p={};
 assert(!rdn_physical_probe_prepare(&p));assert(p.prepared&&p.owner&&p.physical);
 IOMemoryMap *m=rdn_physical_probe_map(&p,(task_t)1,0,0);assert(m&&m->refs==2);
 assert(!rdn_physical_probe_redirect(&p,true));assert(rdn_physical_probe_finish(&p));
 assert(!rdn_physical_probe_redirect(&p,false));assert(!rdn_physical_probe_finish(&p));assert(m->refs==1&&m->unmaps==1&&!p.owner&&!p.physical);
 p=rdn_tiger_physical_probe();assert(!rdn_physical_probe_prepare(&p));m=rdn_physical_probe_map(&p,(task_t)1,0,0);m->fail_enter=true;
 int releases=IOBufferMemoryDescriptor::released;assert(rdn_physical_probe_redirect(&p,true));assert(p.uncertain&&rdn_physical_probe_finish(&p));assert(p.owner&&p.physical&&p.mapping&&IOBufferMemoryDescriptor::released==releases);
 p=rdn_tiger_physical_probe();assert(!rdn_physical_probe_prepare(&p));m=rdn_physical_probe_map(&p,(task_t)1,0,0);m->fail_unmap=true;
 assert(rdn_physical_probe_finish(&p));assert(p.uncertain&&p.owner&&p.physical&&p.mapping);
 p=rdn_tiger_physical_probe();assert(!rdn_physical_probe_prepare(&p));m=rdn_physical_probe_map(&p,(task_t)1,0,0);assert(!rdn_physical_probe_redirect(&p,true));m->fail_exit=true;
 assert(rdn_physical_probe_redirect(&p,false));assert(p.uncertain&&p.redirect_active&&rdn_physical_probe_finish(&p));assert(p.owner&&p.mapping);
 p=rdn_tiger_physical_probe();assert(!rdn_physical_probe_prepare(&p));IOMemoryDescriptor::map_fail=true;assert(!rdn_physical_probe_map(&p,(task_t)1,0,0));assert(!p.mapping&&!rdn_physical_probe_finish(&p));IOMemoryDescriptor::map_fail=false;
 p=rdn_tiger_physical_probe();witness=0x3000;assert(rdn_physical_probe_prepare(&p));assert(!p.owner&&!p.physical);witness=0x1000;
 p=rdn_tiger_physical_probe();IOBufferMemoryDescriptor::flush_fail=true;assert(rdn_physical_probe_prepare(&p));assert(!p.owner&&!p.physical);IOBufferMemoryDescriptor::flush_fail=false;
 p=rdn_tiger_physical_probe();IOBufferMemoryDescriptor::address=0x100000000ULL;assert(rdn_physical_probe_prepare(&p));assert(!p.owner&&!p.prepared);
 p=rdn_tiger_physical_probe();IOBufferMemoryDescriptor::address=0x1001;assert(rdn_physical_probe_prepare(&p));assert(!p.owner&&!p.prepared);
 p=rdn_tiger_physical_probe();IOBufferMemoryDescriptor::address=0x1000;IOMemoryDescriptor::physical_fail=true;IOBufferMemoryDescriptor::complete_fail=true;
 assert(rdn_physical_probe_prepare(&p));assert(p.uncertain&&p.owner&&p.prepared);assert(rdn_physical_probe_finish(&p));
 return 0;
}
