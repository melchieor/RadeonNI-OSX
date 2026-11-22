#ifndef PHYSICAL_PROBE_MOCKS_H
#define PHYSICAL_PROBE_MOCKS_H
#include <stdint.h>
typedef uint32_t UInt32;typedef uint64_t addr64_t;typedef uint32_t IOPhysicalAddress;
typedef uint32_t IOByteCount;typedef uint32_t IOOptionBits;typedef uint32_t IOVirtualAddress;typedef void *task_t;
enum { kIOReturnSuccess=0,kIODirectionInOut=3,kIOMapUserOptionsMask=255,kIOMapUnique=0x4000000,kIOMemoryIncoherentIOFlush=1 };
struct IOMemoryMap;
struct IOMemoryDescriptor {
 int refs;static bool physical_fail,map_fail;static int physical_releases;static IOMemoryMap *last;
 IOMemoryDescriptor():refs(1){} virtual ~IOMemoryDescriptor(){}
 static IOMemoryDescriptor *withPhysicalAddress(IOPhysicalAddress,IOByteCount,int);
 virtual void release(){--refs;++physical_releases;}
 IOMemoryMap *map(task_t,IOVirtualAddress,IOOptionBits);
};
struct IOBufferMemoryDescriptor: IOMemoryDescriptor {
 static bool alloc_fail,prepare_fail,complete_fail;static addr64_t address;static IOByteCount length;static int released,completed;static bool flush_fail;
 static IOBufferMemoryDescriptor *withOptions(int,IOByteCount,IOByteCount){return alloc_fail?0:new IOBufferMemoryDescriptor;}
 int prepare(){return prepare_fail?-1:0;}
 int complete(){++completed;return complete_fail?-1:0;}
 void *getBytesNoCopy(){return (void *)0x2000;}
 int performOperation(int,IOByteCount,IOByteCount){return flush_fail?-1:0;}
 addr64_t getPhysicalSegment64(IOByteCount,IOByteCount *n){*n=length;return address;}
 void release(){--refs;++released;}
};
addr64_t kvtophys64(addr64_t);
struct IOMemoryMap {
 int refs;bool fail_enter,fail_exit,fail_unmap;IOMemoryDescriptor *desc;int unmaps;
 IOMemoryMap(IOMemoryDescriptor *d):refs(1),fail_enter(false),fail_exit(false),fail_unmap(false),desc(d),unmaps(0){}
 void retain(){++refs;}void release(){--refs;}
 IOMemoryDescriptor *getMemoryDescriptor(){return desc;}
 int redirect(IOMemoryDescriptor *d,int,int){return ((!d&&fail_enter)||(d&&fail_exit))?-1:0;}
 int unmap(){++unmaps;return fail_unmap?-1:0;}
};
#endif
